"""Runtime settings loaded from environment variables."""

from functools import lru_cache
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AliasChoices, Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

NonEmptyStr = Annotated[str, Field(min_length=1)]
NonNegativeFloat = Annotated[float, Field(ge=0.0)]
PositiveInt = Annotated[int, Field(gt=0)]
HourOfDayInt = Annotated[int, Field(ge=0, le=23)]
TemperatureFloat = Annotated[float, Field(ge=0.0, le=2.0)]


class Settings(BaseSettings):
    """Environment-driven application settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    room1_id: NonEmptyStr = Field(validation_alias="ROOM1_ID")
    room2_id: NonEmptyStr = Field(validation_alias="ROOM2_ID")
    room3_id: NonEmptyStr = Field(validation_alias="ROOM3_ID")
    room4_id: NonEmptyStr = Field(validation_alias="ROOM4_ID")
    matrix_homeserver_url: HttpUrl = Field(validation_alias="MATRIX_HOMESERVER_URL")
    matrix_bot_user_id: NonEmptyStr = Field(validation_alias="MATRIX_BOT_USER_ID")
    matrix_access_token: NonEmptyStr = Field(validation_alias="MATRIX_ACCESS_TOKEN")
    matrix_sync_timeout_ms: PositiveInt = Field(
        default=30_000,
        validation_alias="MATRIX_SYNC_TIMEOUT_MS",
    )
    matrix_poll_interval_seconds: NonNegativeFloat = Field(
        default=1.0,
        validation_alias="MATRIX_POLL_INTERVAL_SECONDS",
    )
    worker_poll_interval_seconds: NonNegativeFloat = Field(
        default=1.0,
        validation_alias="WORKER_POLL_INTERVAL_SECONDS",
    )
    supervisor_summary_timezone: NonEmptyStr = Field(
        default="America/Bahia",
        validation_alias="SUPERVISOR_SUMMARY_TIMEZONE",
    )
    supervisor_summary_morning_hour: HourOfDayInt = Field(
        default=7,
        validation_alias="SUPERVISOR_SUMMARY_MORNING_HOUR",
    )
    supervisor_summary_evening_hour: HourOfDayInt = Field(
        default=19,
        validation_alias="SUPERVISOR_SUMMARY_EVENING_HOUR",
    )
    webhook_public_url: HttpUrl = Field(validation_alias="WEBHOOK_PUBLIC_URL")
    widget_public_url: HttpUrl = Field(
        validation_alias=AliasChoices("WIDGET_PUBLIC_URL", "WEBHOOK_PUBLIC_URL"),
    )
    database_url: NonEmptyStr = Field(validation_alias="DATABASE_URL")
    webhook_hmac_secret: NonEmptyStr = Field(validation_alias="WEBHOOK_HMAC_SECRET")
    llm_runtime_mode: Literal["deterministic", "provider"] = Field(
        default="deterministic",
        validation_alias="LLM_RUNTIME_MODE",
    )
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model_llm1: NonEmptyStr = Field(
        default="gpt-4o-mini",
        validation_alias="OPENAI_MODEL_LLM1",
    )
    openai_model_llm2: NonEmptyStr = Field(
        default="gpt-4o-mini",
        validation_alias="OPENAI_MODEL_LLM2",
    )
    openai_temperature: TemperatureFloat | None = Field(
        default=None,
        validation_alias="OPENAI_TEMPERATURE",
    )
    openai_timeout_seconds: NonNegativeFloat = Field(
        default=60.0,
        validation_alias="OPENAI_TIMEOUT_SECONDS",
    )
    bootstrap_admin_email: NonEmptyStr | None = Field(
        default=None,
        validation_alias="BOOTSTRAP_ADMIN_EMAIL",
    )
    bootstrap_admin_password: NonEmptyStr | None = Field(
        default=None,
        validation_alias="BOOTSTRAP_ADMIN_PASSWORD",
    )
    bootstrap_admin_password_file: NonEmptyStr | None = Field(
        default=None,
        validation_alias="BOOTSTRAP_ADMIN_PASSWORD_FILE",
    )
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    @field_validator("supervisor_summary_timezone")
    @classmethod
    def validate_supervisor_summary_timezone(cls, value: str) -> str:
        """Ensure summary timezone is a valid IANA timezone name."""

        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"invalid timezone: {value}") from exc
        return value


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    """Load and cache application settings."""

    return Settings()  # type: ignore[call-arg]
