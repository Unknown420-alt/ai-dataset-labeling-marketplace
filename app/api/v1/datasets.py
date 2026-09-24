from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.schemas.dataset import DatasetCreate, DatasetPublic, DatasetUpdate
from app.services.security import get_current_user
from app.services.responses import ok
from app.services.audit import log_action
from app.services.training import (
    train_model,
    predict_with_model,
    MIN_LABELED_ROWS,
)
from app.models import User, Dataset, LabelTask, DataItem

class PredictRequest(BaseModel):
    text: str


class SuggestLLMRequest(BaseModel):
    limit: int = 100
    model: Optional[str] = None


class TrainResult(BaseModel):
    accuracy: float
    labeled_count: int
    total_items: int
    task_type: str = "single"
    evaluation: str = ""


class PredictResult(BaseModel):
    label: str
    confidence: float
    labels: Optional[list] = None

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
    await log_action(db, current.id, "dataset_delete", "dataset", dataset_id)
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

    await log_action(
        db, current.id, "model_train", "dataset", dataset_id,
        f"accuracy={info['accuracy']} rows={info['labeled_count']}",
    )
    await db.commit()
    return ok(
        TrainResult(
            accuracy=info["accuracy"],
            labeled_count=info["labeled_count"],
            total_items=len(items),
            task_type=info.get("task_type", "single"),
            evaluation=info.get("evaluation", ""),
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
        PredictResult(
            label=pred["label"],
            confidence=pred["confidence"],
            labels=pred.get("labels"),
        ),
        "Prediction",
    )


@router.post("/{dataset_id}/suggest")
async def suggest_labels(
    dataset_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run the trained model over every unlabeled item and store AI suggestions.

    This closes the loop: label a few by hand -> train -> the model
    pre-labels the rest -> labelers confirm or correct.
    """
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
    unlabeled = [
        d for d in items_result.scalars().all() if not d.final_label
    ]
    if not unlabeled:
        return ok({"suggested": 0}, "Nothing to suggest — everything is labeled")

    done = 0
    try:
        for item in unlabeled:
            text = (item.content_json or {}).get("text", "")
            if not text:
                continue
            pred = predict_with_model(dataset_id, text)
            if "labels" in pred:
                item.ai_suggestion = {"labels": pred["labels"]}
            else:
                item.ai_suggestion = {"label": pred["label"]}
            item.ai_confidence = pred["confidence"]
            done += 1
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    await db.commit()
    return ok({"suggested": done}, f"AI suggestions generated for {done} items")


@router.post("/{dataset_id}/suggest-llm")
async def suggest_llm(
    dataset_id: int,
    payload: SuggestLLMRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ask an LLM to pre-label unlabeled items. Needs OPENAI_API_KEY.

    Fails closed with 422 when no key is configured — never fakes output.
    Single-label tasks only; multilabel stays on the local model for now.
    """
    from app.services import llm as llm_svc

    if not settings.openai_api_key:
        raise HTTPException(
            status_code=422,
            detail="LLM suggestions need OPENAI_API_KEY. Set it in .env (or the backend env) to enable.",
        )
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
        select(LabelTask).where(
            LabelTask.dataset_id == dataset_id, LabelTask.is_multilabel == 0
        )
    )
    tasks = tasks_result.scalars().all()
    if not tasks:
        raise HTTPException(
            status_code=422, detail="LLM suggestions support single-label tasks only"
        )
    task_ids = [t.id for t in tasks]
    schema_keys: list[str] = []
    instructions = ""
    for t in tasks:
        for k in (t.label_schema or {}).keys():
            if k not in schema_keys:
                schema_keys.append(k)
        if not instructions:
            instructions = t.instructions or ""
    if not schema_keys:
        raise HTTPException(status_code=422, detail="Task has no labels defined")

    items_result = await db.execute(
        select(DataItem).where(DataItem.task_id.in_(task_ids))
    )
    unlabeled = [d for d in items_result.scalars().all() if not d.final_label][
        : max(payload.limit, 1)
    ]
    if not unlabeled:
        return ok({"suggested": 0}, "Nothing to suggest — everything is labeled")

    model = payload.model or settings.openai_model
    texts = [(i.content_json or {}).get("text", "") for i in unlabeled]
    try:
        mapping = llm_svc.suggest_batch(
            settings.openai_api_key, model, instructions, schema_keys, texts
        )
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    done = 0
    for idx, label in mapping.items():
        if 0 <= idx < len(unlabeled):
            unlabeled[idx].ai_suggestion = {"label": label}
            unlabeled[idx].ai_confidence = None
            done += 1
    await db.commit()
    return ok({"suggested": done, "model": model}, f"LLM suggestions written for {done} items")
