from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    cors_origins: str = "http://localhost:5173"
    environment: str = "development"
    workspace_dir: str = "workspaces"
    clone_timeout_seconds: int = 120
    max_repo_mb: int = 200
    access_token_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
