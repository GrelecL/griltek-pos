from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    database_url: str = "postgresql+asyncpg://griltek:changeme@localhost:5432/griltek_pos"
    redis_url: str = "redis://localhost:6379/0"

    furs_env: str = "mock"   # mock | test | production
    furs_cert_path: str = ""
    furs_cert_password: str = ""

    sumup_env: str = "mock"  # mock | real
    sumup_api_key: str = ""


settings = Settings()
