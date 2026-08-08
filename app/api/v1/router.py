from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.datasets import router as datasets_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.labeling import router as labeling_router

router = APIRouter()

router.include_router(health_router)
router.include_router(auth_router)
router.include_router(datasets_router)
router.include_router(tasks_router)
router.include_router(labeling_router)
