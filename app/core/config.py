import sys

from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SECRET = "dev-secret-key-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Dataset Labeling Marketplace"
    secret_key: str = _DEV_SECRET
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/marketplace"
    )
    environment: str = "development"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""


settings = Settings()

# ── Production guard ──────────────────────────────────────────────────────
# On Render (ENVIRONMENT=production) SECRET_KEY must come from the env var,
# never from the committed dev fallback.  Abort loud instead of running with
# a guessable signing key.
if settings.environment == "production" and settings.secret_key == _DEV_SECRET:
    print(
        "[FATAL] SECRET_KEY is still the dev default. "
        "Set the SECRET_KEY environment variable on Render.",
        file=sys.stderr,
    )
    sys.exit(1)
