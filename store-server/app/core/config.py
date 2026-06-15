from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"
    edge_secret_key: str = "dev-edge-secret-key-change-in-production"

    edge_database_url: str = (
        "postgresql+asyncpg://griltek_edge:changeme_edge@localhost:5432/griltek_edge"
    )
    edge_redis_url: str = "redis://localhost:6379/0"

    cloud_api_url: str = "http://localhost:8000/api/v1"
    location_id: str = ""
    tenant_id: str = ""

    sync_interval_seconds: int = 30
    sync_push_batch_size: int = 100

    mtls_cert_path: str = ""
    mtls_key_path: str = ""
    mtls_ca_path: str = ""

    furs_env: str = "mock"


settings = Settings()
