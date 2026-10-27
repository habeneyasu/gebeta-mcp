"""Typed settings read from the environment (and `.env`) by every entry point."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from gebeta.domain.models import DEFAULT_MAX_DROPS, DEFAULT_MAX_MOVES_WITHOUT_CAPTURE, Limits


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GEBETA_", env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    max_drops: int = Field(default=DEFAULT_MAX_DROPS, ge=1)
    max_moves_without_capture: int = Field(default=DEFAULT_MAX_MOVES_WITHOUT_CAPTURE, ge=1)
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    claude_model: str = "claude-opus-5-5"
    anthropic_api_key: SecretStr | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")

    @property
    def limits(self) -> Limits:
        return Limits(
            max_drops=self.max_drops, max_moves_without_capture=self.max_moves_without_capture
        )
