import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import User, LabelTask, DataItem, LabelSubmission, TaskClaim
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


@router.post("/tasks/{task_id}/items/upload", status_code=status.HTTP_201_CREATED)
async def upload_task_items(
    task_id: int,
    file: UploadFile = File(...),
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(db, task_id)

    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 5 MB")

    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = [row for row in reader if row and row[0].strip()]

    if not rows:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    if rows[0][0].strip().lower() in ("text", "content", "sentence"):
        rows = rows[1:]

    for idx, row in enumerate(rows, start=1):
        content = row[0].strip()
        suggestion = row[1].strip() if len(row) > 1 and row[1].strip() else None
        item = DataItem(
            task_id=task_id,
            row_index=idx,
            content_json={"text": content},
            ai_suggestion={"label": suggestion} if suggestion else None,
            ai_confidence=1.0 if suggestion else 0.0,
        )
        db.add(item)

    if task.status == TaskStatus.DRAFT:
        task.status = TaskStatus.OPEN
    await db.commit()
    return ok({"uploaded": len(rows)}, f"Uploaded {len(rows)} items")


@router.get("/tasks/{task_id}/items")
async def list_task_items(
    task_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(db, task_id)

    result = await db.execute(select(DataItem).where(DataItem.task_id == task_id))
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

    submission = LabelSubmission(
        item_id=item_id,
        labeler_id=current.id,
        label_value=payload.label_value,
        source="human",
    )
    item.final_label = payload.label_value

    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return ok(SubmissionPublic.model_validate(submission), "Label submitted")


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(db, task_id)
    return ok(LabelTaskPublic.model_validate(task), "Task fetched")
