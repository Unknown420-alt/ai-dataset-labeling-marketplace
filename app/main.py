"""AI Dataset Labeling Marketplace - FastAPI backend"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import router as api_router

app = FastAPI(
    title="AI Dataset Labeling Marketplace API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "success": True,
        "data": {"name": "AI Dataset Labeling Marketplace", "version": "0.1.0"},
        "message": "API is running. Check /docs for endpoints.",
    }
