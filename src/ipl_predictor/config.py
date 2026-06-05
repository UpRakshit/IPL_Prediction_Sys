from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    live_provider: str = "cricapi"
    cricapi_base_url: str = "https://api.cricapi.com/v1"
    cricapi_api_key: str = ""
    entitysport_base_url: str = "https://rest.entitysport.com/v2"
    entitysport_api_key: str = ""
    database_url: str = ""
    redis_url: str = ""
    cache_ttl_live_seconds: int = 15
    cache_ttl_season_seconds: int = 300
    live_poll_seconds: int = 20
    model_path: str = "models/baseline.joblib"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
