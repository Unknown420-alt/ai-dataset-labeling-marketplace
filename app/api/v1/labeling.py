import csv
import io
import json
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import User, Dataset, LabelTask, DataItem, LabelSubmission, TaskClaim
from app.models.task import TaskStatus
from app.schemas.labeling import (
    DataItemPublic,
    SubmissionCreate,
    SubmissionPublic,
    TaskClaimPublic,
)
from app.schemas.task import LabelTaskPublic
from app.services.responses import ok
from app.services.security import get_current_user

router = APIRouter(tags=["labeling"])


async def _get_task_or_404(db: AsyncSession, task_id: int) -> LabelTask:
    result = await db.execute(select(LabelTask).where(LabelTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/tasks/{task_id}/claim", status_code=status.HTTP_201_CREATED)
async def claim_task(
    task_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(db, task_id)

    existing = await db.execute(
        select(TaskClaim).where(
            TaskClaim.task_id == task_id, TaskClaim.labeler_id == current.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Task already claimed by you")

    claim = TaskClaim(
        task_id=task_id,
        labeler_id=current.id,
        assigned_count=task.num_labelers,
        status="claimed",
    )
    if task.status == TaskStatus.DRAFT:
        task.status = TaskStatus.IN_PROGRESS

    db.add(claim)
    await db.commit()
    await db.refresh(claim)
    return ok(TaskClaimPublic.model_validate(claim), "Task claimed")


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_UPLOAD_ROWS = 10000


def _upload_limit() -> tuple[int, str]:
    if os.environ.get("VERCEL") == "1":
        return 4 * 1024 * 1024, "File exceeds 4 MB (Vercel serverless limit)"
    return MAX_UPLOAD_BYTES, "File exceeds 10 MB"


def _parse_bulk_items(raw: bytes, filename: str) -> list[tuple[str, str | None]]:
    """Parse CSV, JSON, or JSONL upload into (text, suggested_label) pairs."""
    name = (filename or "").lower()
    limit, limit_msg = _upload_limit()
    if len(raw) > limit:
        raise HTTPException(status_code=400, detail=limit_msg)

    if name.endswith(".json"):
        try:
            data = json.loads(raw.decode("utf-8-sig"))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON file")
        records = data if isinstance(data, list) else data.get("items", [])
        pairs = []
        for rec in records:
            if isinstance(rec, str):
                pairs.append((rec.strip(), None))
            elif isinstance(rec, dict):
                text = str(rec.get("text", "")).strip()
                label = rec.get("label")
                pairs.append((text, str(label).strip() if label else None))
        rows = [(t, s) for t, s in pairs if t]
    elif name.endswith(".jsonl"):
        rows = []
        for line in raw.decode("utf-8-sig").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSONL line")
            if isinstance(rec, str):
                rows.append((rec.strip(), None))
            elif isinstance(rec, dict):
                text = str(rec.get("text", "")).strip()
                label = rec.get("label")
                rows.append((text, str(label).strip() if label else None))
        rows = [(t, s) for t, s in rows if t[0]]
    else:  # CSV (default)
        text = raw.decode("utf-8-sig", errors="replace")
        reader = csv.reader(io.StringIO(text))
        csv_rows = [row for row in reader if row and row[0].strip()]
        if not csv_rows:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        if csv_rows[0][0].strip().lower() in ("text", "content", "sentence"):
            csv_rows = csv_rows[1:]
        rows = [
            (
                row[0].strip(),
                row[1].strip() if len(row) > 1 and row[1].strip() else None,
            )
            for row in csv_rows
        ]

    if not rows:
        raise HTTPException(status_code=400, detail="No usable rows found in file")
    if len(rows) > MAX_UPLOAD_ROWS:
        raise HTTPException(
            status_code=400,
            detail=f"Too many rows ({len(rows)}); max is {MAX_UPLOAD_ROWS}",
        )
    return rows


@router.post("/tasks/{task_id}/items/upload", status_code=status.HTTP_201_CREATED)
async def upload_task_items(
    task_id: int,
    file: UploadFile = File(...),
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(db, task_id)

    raw = await file.read()
    rows = _parse_bulk_items(raw, file.filename or "")

    existing_res = await db.execute(select(DataItem).where(DataItem.task_id == task_id))
    start_idx = len(existing_res.scalars().all())
    for offset, (content, suggestion) in enumerate(rows, start=1):
        item = DataItem(
            task_id=task_id,
            row_index=start_idx + offset,
            content_json={"text": content},
            ai_suggestion={"label": suggestion} if suggestion else None,
            ai_confidence=1.0 if suggestion else 0.0,
        )
        db.add(item)

    if task.status == TaskStatus.DRAFT:
        task.status = TaskStatus.OPEN
    ds_res = await db.execute(select(Dataset).where(Dataset.id == task.dataset_id))
    dataset = ds_res.scalar_one_or_none()
    if dataset is not None:
        dataset.total_items = start_idx + len(rows)
    await db.commit()
    return ok({"uploaded": len(rows)}, f"Uploaded {len(rows)} items")


@router.get("/tasks/{task_id}/items")
async def list_task_items(
    task_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(db, task_id)

    result = await db.execute(
        select(DataItem)
        .where(DataItem.task_id == task_id)
        .order_by(DataItem.final_label.is_not(None), DataItem.row_index)
    )
    items = result.scalars().all()
    return ok(
        [DataItemPublic.model_validate(i) for i in items],
        "Items listed",
    )


@router.post("/data_items/{item_id}/submission", status_code=status.HTTP_201_CREATED)
async def submit_label(
    item_id: int,
    payload: SubmissionCreate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item_result = await db.execute(select(DataItem).where(DataItem.id == item_id))
    item = item_result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    task_res = await db.execute(select(LabelTask).where(LabelTask.id == item.task_id))
    item_task = task_res.scalar_one_or_none()
    is_multi = bool(item_task and item_task.is_multilabel)
    label_value = payload.label_value
    if is_multi:
        picked = label_value.get("labels")
        if not isinstance(picked, list) or not picked:
            raise HTTPException(
                status_code=422,
                detail="Multilabel task needs {labels: [...]} with at least one label",
            )
        schema_keys = set((item_task.label_schema or {}).keys())
        unknown = [l for l in picked if l not in schema_keys]
        if unknown:
            raise HTTPException(
                status_code=422, detail=f"Unknown labels: {', '.join(unknown)}"
            )
        label_value = {"labels": sorted(set(picked))}
    elif "label" not in label_value:
        raise HTTPException(status_code=422, detail="Missing label value")

    submission = LabelSubmission(
        item_id=item_id,
        labeler_id=current.id,
        label_value=label_value,
        source="human",
    )
    dup = await db.execute(
        select(LabelSubmission).where(
            LabelSubmission.item_id == item_id,
            LabelSubmission.labeler_id == current.id,
        )
    )
    if dup.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="You already labeled this item")
    item.final_label = label_value

    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    body = SubmissionPublic.model_validate(submission).model_dump()
    if item.gold_label is not None:
        import json as _json

        body["gold_correct"] = _json.dumps(label_value, sort_keys=True) == _json.dumps(
            item.gold_label, sort_keys=True
        )
    else:
        body["gold_correct"] = None
    return ok(body, "Label submitted")


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(db, task_id)
    return ok(LabelTaskPublic.model_validate(task), "Task fetched")
