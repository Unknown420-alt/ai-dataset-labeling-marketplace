from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.dataset import DatasetCreate, DatasetPublic
from app.services.security import get_current_user
from app.services.responses import ok
from app.models import User, Dataset

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
