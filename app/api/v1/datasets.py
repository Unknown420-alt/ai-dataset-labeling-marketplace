from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.schemas.dataset import DatasetCreate, DatasetPublic
from app.models import Dataset

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/", response_model=DatasetPublic, status_code=status.HTTP_201_CREATED)
async def create_dataset(payload: DatasetCreate, db: AsyncSession = Depends(get_db)):
    # TODO: hook up real file upload + storage in Week 2
    dataset = Dataset(
        name=payload.name,
        description=payload.description,
        owner_id=1,  # FIXME: get from JWT token
        storage_url="pending://",
        file_type=payload.file_type,
        total_items=0,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return dataset


@router.get("/", response_model=list[DatasetPublic])
async def list_datasets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dataset))
    return result.scalars().all()
