from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.task import LabelTaskCreate, LabelTaskPublic
from app.services.security import get_current_user
from app.services.responses import ok
from app.models import User, LabelTask

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: LabelTaskCreate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = LabelTask(
        dataset_id=payload.dataset_id,
        title=payload.title,
        instructions=payload.instructions,
        label_schema=payload.label_schema,
        num_labelers=payload.num_labelers,
        ai_enabled=payload.ai_enabled,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return ok(LabelTaskPublic.model_validate(task), "Task created")


@router.get("/")
async def list_tasks(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LabelTask))
    tasks = result.scalars().all()
    return ok(
        [LabelTaskPublic.model_validate(t) for t in tasks],
        "Tasks listed",
    )
