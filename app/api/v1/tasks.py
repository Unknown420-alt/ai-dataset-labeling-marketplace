from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.schemas.task import LabelTaskCreate, LabelTaskPublic
from app.models import LabelTask

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=LabelTaskPublic, status_code=status.HTTP_201_CREATED)
async def create_task(payload: LabelTaskCreate, db: AsyncSession = Depends(get_db)):
    # TODO: dispatch AI suggestions, init data items in Week 2
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
    return task


@router.get("/", response_model=list[LabelTaskPublic])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LabelTask))
    return result.scalars().all()
