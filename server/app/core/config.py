from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]
SERVER_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "AION"
    app_version: str = "0.1.0"
    environment: str = Field(default="development")
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    log_level: str = "INFO"
    request_timeout_seconds: int = 30
    google_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_API_KEY", "AION_GOOGLE_API_KEY"),
    )
    tavily_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TAVILY_API_KEY", "AION_TAVILY_API_KEY"),
    )
    firecrawl_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("FIRECRAWL_API_KEY", "AION_FIRECRAWL_API_KEY"),
    )
    llm_provider: str = Field(
        default="gemini",
        validation_alias=AliasChoices("LLM_PROVIDER", "AION_LLM_PROVIDER"),
    )
    llm_model: str = Field(
        default="gemini-2.5-flash-lite",
        validation_alias=AliasChoices("LLM_MODEL", "AION_LLM_MODEL"),
    )
    supabase_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SUPABASE_URL", "AION_SUPABASE_URL"),
    )
    supabase_service_role_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SUPABASE_SERVICE_ROLE_KEY", "AION_SUPABASE_SERVICE_ROLE_KEY"),
    )
    hindsight_api_url: str | None = Field(default=None, validation_alias=AliasChoices("HINDSIGHT_API_URL", "AION_HINDSIGHT_API_URL"))
    hindsight_api_key: str | None = Field(default=None, validation_alias=AliasChoices("HINDSIGHT_API_KEY", "AION_HINDSIGHT_API_KEY"))
    hindsight_bank_id: str | None = Field(default=None, validation_alias=AliasChoices("HINDSIGHT_BANK_ID", "AION_HINDSIGHT_BANK_ID"))

    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", SERVER_DIR / ".env", ".env"),
        env_prefix="",
        extra="ignore",
    )

    @property
    def SUPABASE_URL(self) -> str | None:
        return self.supabase_url

    @property
    def SUPABASE_SERVICE_ROLE_KEY(self) -> str | None:
        return self.supabase_service_role_key


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
