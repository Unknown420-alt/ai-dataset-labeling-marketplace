from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.dataset import DatasetCreate, DatasetPublic, DatasetUpdate
from app.services.security import get_current_user
from app.services.responses import ok
from app.services.training import train_model, predict_with_model, MIN_LABELED_ROWS
from app.models import User, Dataset, LabelTask, DataItem

class PredictRequest(BaseModel):
    text: str


class TrainResult(BaseModel):
    accuracy: float
    labeled_count: int
    total_items: int


class PredictResult(BaseModel):
    label: str
    confidence: float

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_dataset(
    payload: DatasetCreate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    dataset = Dataset(
        name=payload.name,
        description=payload.description,
        owner_id=current.id,
        storage_url="pending://",
        file_type=payload.file_type,
        total_items=0,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return ok(DatasetPublic.model_validate(dataset), "Dataset created")


@router.get("/")
async def list_datasets(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Dataset).where(Dataset.owner_id == current.id))
    datasets = result.scalars().all()
    return ok(
        [DatasetPublic.model_validate(d) for d in datasets],
        "Datasets listed",
    )


@router.get("/{dataset_id}")
async def get_dataset(
    dataset_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.owner_id == current.id)
    )
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ok(DatasetPublic.model_validate(dataset), "Dataset fetched")


@router.patch("/{dataset_id}")
async def update_dataset(
    dataset_id: int,
    payload: DatasetUpdate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.owner_id == current.id)
    )
    dataset = result.scalar_one_or_none()
    if dataset is None:
        # Distinguish 403 from 404: check if dataset exists but belongs to someone else
        exists = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
        if exists.scalar_one_or_none() is not None:
            raise HTTPException(status_code=403, detail="Not authorized")
        raise HTTPException(status_code=404, detail="Dataset not found")
    if payload.name is not None:
        dataset.name = payload.name
    await db.commit()
    await db.refresh(dataset)
    return ok(DatasetPublic.model_validate(dataset), "Dataset updated")


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.owner_id == current.id)
    )
    dataset = result.scalar_one_or_none()
    if dataset is None:
        exists = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
        if exists.scalar_one_or_none() is not None:
            raise HTTPException(status_code=403, detail="Not authorized")
        raise HTTPException(status_code=404, detail="Dataset not found")
    # Check for blocking label_tasks
    tasks_result = await db.execute(
        select(LabelTask).where(LabelTask.dataset_id == dataset_id)
    )
    if tasks_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete dataset: label tasks still reference it",
        )
    await db.delete(dataset)
    await db.commit()
    return ok(None, "Dataset deleted")


@router.post("/{dataset_id}/train")
async def train_dataset(
    dataset_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.owner_id == current.id)
    )
    dataset = result.scalar_one_or_none()
    if dataset is None:
        exists = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
        if exists.scalar_one_or_none() is not None:
            raise HTTPException(status_code=403, detail="Not authorized")
        raise HTTPException(status_code=404, detail="Dataset not found")

    tasks_result = await db.execute(
        select(LabelTask).where(LabelTask.dataset_id == dataset_id)
    )
    task_ids = [t.id for t in tasks_result.scalars().all()]

    if not task_ids:
        raise HTTPException(
            status_code=422, detail="No label tasks found for this dataset"
        )

    items_result = await db.execute(
        select(DataItem).where(DataItem.task_id.in_(task_ids))
    )
    items = [
        {
            "content_json": d.content_json,
            "final_label": d.final_label,
        }
        for d in items_result.scalars().all()
    ]

    labeled = [i for i in items if i.get("final_label")]
    if len(labeled) < MIN_LABELED_ROWS:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least {MIN_LABELED_ROWS} labeled rows, got {len(labeled)}",
        )

    try:
        info = train_model(dataset_id, labeled)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return ok(
        TrainResult(
            accuracy=info["accuracy"],
            labeled_count=info["labeled_count"],
            total_items=len(items),
        ),
        "Model trained",
    )


@router.post("/{dataset_id}/predict")
async def predict_dataset(
    dataset_id: int,
    payload: PredictRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.owner_id == current.id)
    )
    dataset = result.scalar_one_or_none()
    if dataset is None:
        exists = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
        if exists.scalar_one_or_none() is not None:
            raise HTTPException(status_code=403, detail="Not authorized")
        raise HTTPException(status_code=404, detail="Dataset not found")

    try:
        pred = predict_with_model(dataset_id, payload.text)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return ok(
        PredictResult(label=pred["label"], confidence=pred["confidence"]),
        "Prediction",
    )
