from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "CallAgent Backend"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    port: int = Field(default=8000, alias="PORT")
    api_v1_prefix: str = "/api/v1"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    database_url: str = Field(default="sqlite:///./callagent.db", alias="DATABASE_URL")
    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_key: str | None = Field(default=None, alias="SUPABASE_KEY")
    supabase_service_role_key: str | None = Field(default=None, alias="SUPABASE_SERVICE_ROLE_KEY")
    tenant_api_key: str | None = Field(default=None, alias="TENANT_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    vapi_api_key: str | None = Field(default=None, alias="VAPI_API_KEY")
    vapi_assistant_id: str | None = Field(default=None, alias="VAPI_ASSISTANT_ID")
    vapi_phone_number_id: str | None = Field(default=None, alias="VAPI_PHONE_NUMBER_ID")
    vapi_webhook_secret: str | None = Field(default=None, alias="VAPI_WEBHOOK_SECRET")
    vapi_base_url: str = Field(default="https://api.vapi.ai", alias="VAPI_BASE_URL")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
