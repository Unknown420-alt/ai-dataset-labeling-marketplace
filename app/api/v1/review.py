"""Owner review queue, consensus report, and result export."""

import csv
import io
import json
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Dataset, DataItem, LabelSubmission, LabelTask, TaskClaim, User
from app.schemas.review import (
    AnalyticsOverview,
    ConsensusItem,
    ConsensusReport,
    GoldSet,
    LeaderboardEntry,
    MyProgress,
    ReviewDecision,
    SubmissionReviewPublic,
    TaskStats,
)
from app.schemas.labeling import SubmissionPublic
from app.services.responses import ok
from app.services.audit import log_action
from app.services.security import get_current_user

router = APIRouter(tags=["review"])


async def _get_task_or_404(db: AsyncSession, task_id: int) -> LabelTask:
    result = await db.execute(select(LabelTask).where(LabelTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


async def _require_task_owner(db: AsyncSession, task: LabelTask, current: User) -> None:
    ds = await db.execute(select(Dataset).where(Dataset.id == task.dataset_id))
    dataset = ds.scalar_one_or_none()
    if dataset is None or dataset.owner_id != current.id:
        raise HTTPException(status_code=403, detail="Not authorized")


def _label_key(label_value: dict) -> str:
    return json.dumps(label_value, sort_keys=True)


@router.get("/tasks/{task_id}/submissions")
async def list_submissions(
    task_id: int,
    review_status: str | None = Query(default=None, alias="status"),
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(db, task_id)
    items_res = await db.execute(
        select(DataItem).where(DataItem.task_id == task_id).order_by(DataItem.row_index)
    )
    items = items_res.scalars().all()
    item_ids = [i.id for i in items]
    if not item_ids:
        return ok([], "Submissions listed")

    stmt = (
        select(LabelSubmission, DataItem, User)
        .join(DataItem, DataItem.id == LabelSubmission.item_id)
        .join(User, User.id == LabelSubmission.labeler_id)
        .where(LabelSubmission.item_id.in_(item_ids))
        .order_by(DataItem.row_index, LabelSubmission.created_at)
    )
    if review_status:
        stmt = stmt.where(LabelSubmission.status == review_status)
    # Labelers only see their own submissions; owners see everything.
    ds = await db.execute(select(Dataset).where(Dataset.id == task.dataset_id))
    dataset = ds.scalar_one_or_none()
    if dataset is None or dataset.owner_id != current.id:
        stmt = stmt.where(LabelSubmission.labeler_id == current.id)

    rows = (await db.execute(stmt)).all()
    out = [
        SubmissionReviewPublic(
            id=sub.id,
            item_id=sub.item_id,
            row_index=item.row_index,
            item_text=(item.content_json or {}).get("text"),
            labeler_id=sub.labeler_id,
            labeler_email=user.email,
            label_value=sub.label_value,
            source=sub.source,
            status=sub.status,
            is_gold=item.gold_label is not None,
            created_at=sub.created_at,
        )
        for sub, item, user in rows
    ]
    return ok(out, "Submissions listed")


@router.post("/submissions/{submission_id}/review")
async def review_submission(
    submission_id: int,
    payload: ReviewDecision,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub_res = await db.execute(
        select(LabelSubmission).where(LabelSubmission.id == submission_id)
    )
    sub = sub_res.scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    item_res = await db.execute(select(DataItem).where(DataItem.id == sub.item_id))
    item = item_res.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    task = await _get_task_or_404(db, item.task_id)
    await _require_task_owner(db, task, current)

    sub.status = payload.decision
    if payload.decision == "accepted":
        item.final_label = sub.label_value
    else:
        # Fall back to the newest still-accepted submission, if any.
        acc = await db.execute(
            select(LabelSubmission)
            .where(
                LabelSubmission.item_id == item.id,
                LabelSubmission.status == "accepted",
            )
            .order_by(LabelSubmission.created_at.desc())
        )
        newest = acc.scalars().first()
        item.final_label = newest.label_value if newest else None

    await db.commit()
    await db.refresh(sub)
    await log_action(
        db, current.id, f"submission_{payload.decision}", "submission", sub.id
    )
    await db.commit()
    return ok(SubmissionPublic.model_validate(sub), f"Submission {payload.decision}")


@router.get("/tasks/{task_id}/consensus")
async def task_consensus(
    task_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(db, task_id)
    items_res = await db.execute(
        select(DataItem).where(DataItem.task_id == task_id).order_by(DataItem.row_index)
    )
    items = items_res.scalars().all()
    report_items: list[ConsensusItem] = []
    agreements: list[float] = []
    for item in items:
        subs_res = await db.execute(
            select(LabelSubmission).where(LabelSubmission.item_id == item.id)
        )
        subs = subs_res.scalars().all()
        votes = Counter(_label_key(s.label_value) for s in subs)
        if votes:
            top_key, top_count = votes.most_common(1)[0]
            agreement = top_count / len(subs)
            majority = json.loads(top_key)
        else:
            agreement, majority = 0.0, None
        agreements.append(agreement)
        report_items.append(
            ConsensusItem(
                item_id=item.id,
                row_index=item.row_index,
                item_text=(item.content_json or {}).get("text"),
                majority_label=majority,
                votes=dict(votes),
                agreement=round(agreement, 3),
                submission_count=len(subs),
                is_gold=item.gold_label is not None,
            )
        )
    overall = round(sum(agreements) / len(agreements), 3) if agreements else 0.0
    labeled = sum(1 for i in items if i.final_label)
    return ok(
        ConsensusReport(
            task_id=task_id,
            items=report_items,
            overall_agreement=overall,
            labeled_count=labeled,
            total_items=len(items),
        ),
        "Consensus computed",
    )


@router.get("/tasks/{task_id}/export")
async def export_task(
    task_id: int,
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(db, task_id)
    await _require_task_owner(db, task, current)
    items_res = await db.execute(
        select(DataItem).where(DataItem.task_id == task_id).order_by(DataItem.row_index)
    )
    items = items_res.scalars().all()
    await log_action(db, current.id, f"export_{format}", "task", task_id)
    await db.commit()

    if format == "json":
        payload = [
            {
                "item_id": i.id,
                "row_index": i.row_index,
                "text": (i.content_json or {}).get("text"),
                "final_label": i.final_label,
                "ai_suggestion": i.ai_suggestion,
            }
            for i in items
        ]
        return Response(
            content=json.dumps(payload, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=task_{task_id}_labels.json"
            },
        )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["item_id", "row_index", "text", "final_label", "ai_suggestion"])
    for i in items:
        writer.writerow(
            [
                i.id,
                i.row_index,
                (i.content_json or {}).get("text", ""),
                json.dumps(i.final_label) if i.final_label else "",
                json.dumps(i.ai_suggestion) if i.ai_suggestion else "",
            ]
        )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=task_{task_id}_labels.csv"
        },
    )


@router.post("/data_items/{item_id}/gold")
async def set_gold_label(
    item_id: int,
    payload: GoldSet,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark an item as a gold (attention-check) item. Pass {"gold_label": null} to clear."""
    item_res = await db.execute(select(DataItem).where(DataItem.id == item_id))
    item = item_res.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    task = await _get_task_or_404(db, item.task_id)
    await _require_task_owner(db, task, current)
    item.gold_label = payload.gold_label
    await db.commit()
    return ok({"item_id": item.id, "gold_label": item.gold_label}, "Gold label updated")


@router.get("/tasks/{task_id}/leaderboard")
async def task_leaderboard(
    task_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(db, task_id)
    await _require_task_owner(db, task, current)
    items_res = await db.execute(select(DataItem).where(DataItem.task_id == task_id))
    items = items_res.scalars().all()
    item_ids = [i.id for i in items]
    gold_by_item = {i.id: i.gold_label for i in items if i.gold_label}
    if not item_ids:
        return ok([], "Leaderboard computed")

    subs_res = await db.execute(
        select(LabelSubmission, User)
        .join(User, User.id == LabelSubmission.labeler_id)
        .where(LabelSubmission.item_id.in_(item_ids))
    )
    per_labeler: dict[int, dict] = {}
    for sub, user in subs_res.all():
        entry = per_labeler.setdefault(
            sub.labeler_id, {"email": user.email, "subs": []}
        )
        entry["subs"].append(sub)

    board: list[LeaderboardEntry] = []
    for labeler_id, entry in per_labeler.items():
        subs = entry["subs"]
        accepted = sum(1 for s in subs if s.status == "accepted")
        rejected = sum(1 for s in subs if s.status == "rejected")
        reviewed = accepted + rejected
        gold_subs = [s for s in subs if s.item_id in gold_by_item]
        gold_ok = sum(
            1
            for s in gold_subs
            if _label_key(s.label_value) == _label_key(gold_by_item[s.item_id])
        )
        board.append(
            LeaderboardEntry(
                labeler_id=labeler_id,
                labeler_email=entry["email"],
                submitted=len(subs),
                accepted=accepted,
                rejected=rejected,
                review_accuracy=round(accepted / reviewed, 3) if reviewed else None,
                gold_answered=len(gold_subs),
                gold_correct=gold_ok,
                gold_accuracy=round(gold_ok / len(gold_subs), 3) if gold_subs else None,
            )
        )
    board.sort(
        key=lambda e: (e.gold_accuracy or 0, e.review_accuracy or 0), reverse=True
    )
    return ok(board, "Leaderboard computed")


@router.get("/analytics/overview")
async def analytics_overview(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import date, timedelta

    ds_res = await db.execute(select(Dataset).where(Dataset.owner_id == current.id))
    datasets = ds_res.scalars().all()
    ds_ids = [d.id for d in datasets]
    if not ds_ids:
        return ok(
            AnalyticsOverview(
                datasets=0,
                tasks=0,
                items=0,
                labeled=0,
                submissions=0,
                overall_agreement=0.0,
                per_task=[],
                daily_submissions=[],
                label_distribution={},
            ),
            "Analytics computed",
        )

    tasks_res = await db.execute(
        select(LabelTask).where(LabelTask.dataset_id.in_(ds_ids))
    )
    tasks = tasks_res.scalars().all()
    task_ids = [t.id for t in tasks]
    items_res = await db.execute(
        select(DataItem).where(DataItem.task_id.in_(task_ids))
        if task_ids
        else select(DataItem).where(False)
    )
    items = items_res.scalars().all() if task_ids else []
    item_ids = [i.id for i in items]

    subs_res = await db.execute(
        select(LabelSubmission).where(LabelSubmission.item_id.in_(item_ids))
        if item_ids
        else select(LabelSubmission).where(False)
    )
    subs = subs_res.scalars().all() if item_ids else []

    by_task: dict[int, list] = {}
    for i in items:
        by_task.setdefault(i.task_id, []).append(i)
    subs_by_item: dict[int, list] = {}
    for s in subs:
        subs_by_item.setdefault(s.item_id, []).append(s)

    per_task: list[TaskStats] = []
    agreements: list[float] = []
    label_dist: Counter = Counter()
    for t in tasks:
        t_items = by_task.get(t.id, [])
        labeled = sum(1 for i in t_items if i.final_label)
        for i in t_items:
            if i.final_label:
                label_dist[_label_key(i.final_label)] += 1
        task_agrs = []
        for i in t_items:
            votes = Counter(
                _label_key(s.label_value) for s in subs_by_item.get(i.id, [])
            )
            if votes:
                task_agrs.append(votes.most_common(1)[0][1] / sum(votes.values()))
        agr = round(sum(task_agrs) / len(task_agrs), 3) if task_agrs else 0.0
        agreements.append(agr)
        per_task.append(
            TaskStats(
                task_id=t.id,
                title=t.title,
                status=t.status.value,
                labeled=labeled,
                total=len(t_items),
                agreement=agr,
                gold_items=sum(1 for i in t_items if i.gold_label),
            )
        )

    today = date.today()
    days = [today - timedelta(days=d) for d in range(13, -1, -1)]
    per_day = {str(d): 0 for d in days}
    for s in subs:
        key = str(s.created_at.date()) if s.created_at else None
        if key in per_day:
            per_day[key] += 1

    gold_items = [i for i in items if i.gold_label]
    gold_subs = [s for s in subs if s.item_id in {i.id for i in gold_items}]
    gold_ok = sum(
        1
        for s in gold_subs
        if _label_key(s.label_value)
        == _label_key(next(i.gold_label for i in items if i.id == s.item_id))
    )

    return ok(
        AnalyticsOverview(
            datasets=len(datasets),
            tasks=len(tasks),
            items=len(items),
            labeled=sum(1 for i in items if i.final_label),
            submissions=len(subs),
            overall_agreement=(
                round(sum(agreements) / len(agreements), 3) if agreements else 0.0
            ),
            gold_coverage=round(len(gold_items) / len(items), 3) if items else 0.0,
            gold_accuracy=round(gold_ok / len(gold_subs), 3) if gold_subs else None,
            per_task=per_task,
            daily_submissions=[{"date": d, "count": c} for d, c in per_day.items()],
            label_distribution=dict(label_dist.most_common(10)),
        ),
        "Analytics computed",
    )


@router.get("/analytics/mine")
async def my_progress(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import date, timedelta

    from app.models import TaskClaim

    subs_res = await db.execute(
        select(LabelSubmission).where(LabelSubmission.labeler_id == current.id)
    )
    mine = subs_res.scalars().all()
    accepted = sum(1 for s in mine if s.status == "accepted")
    rejected = sum(1 for s in mine if s.status == "rejected")
    reviewed = accepted + rejected

    item_ids = list({s.item_id for s in mine})
    gold_map: dict[int, object] = {}
    if item_ids:
        items_res = await db.execute(select(DataItem).where(DataItem.id.in_(item_ids)))
        gold_map = {
            i.id: i.gold_label for i in items_res.scalars().all() if i.gold_label
        }
    gold_subs = [s for s in mine if s.item_id in gold_map]
    gold_ok = sum(
        1
        for s in gold_subs
        if _label_key(s.label_value) == _label_key(gold_map[s.item_id])
    )

    claims_res = await db.execute(
        select(TaskClaim).where(TaskClaim.labeler_id == current.id)
    )
    claimed = len(claims_res.scalars().all())

    today = date.today()
    days = [today - timedelta(days=d) for d in range(13, -1, -1)]
    per_day = {str(d): 0 for d in days}
    for s in mine:
        key = str(s.created_at.date()) if s.created_at else None
        if key in per_day:
            per_day[key] += 1

    return ok(
        MyProgress(
            submitted=len(mine),
            accepted=accepted,
            rejected=rejected,
            review_accuracy=round(accepted / reviewed, 3) if reviewed else None,
            gold_answered=len(gold_subs),
            gold_correct=gold_ok,
            gold_accuracy=round(gold_ok / len(gold_subs), 3) if gold_subs else None,
            daily_submissions=[{"date": d, "count": c} for d, c in per_day.items()],
            tasks_claimed=claimed,
        ),
        "Progress computed",
    )
