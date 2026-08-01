import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AI Dataset Labeling Marketplace"
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/marketplace"
    )

    model_config = {"env_file": ".env"}


settings = Settings()
