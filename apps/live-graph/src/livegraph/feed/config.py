from __future__ import annotations

from typing import ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _looks_real(value: str) -> bool:
    text = (value or "").strip()
    return bool(text) and not text.startswith("#")


class KotakSettings(BaseSettings):
    """Credentials for the Neo API. Never hardcode these; they come from .env."""

    model_config = SettingsConfigDict(
        env_prefix="KOTAK_", env_file=".env", extra="ignore"
    )

    consumer_key: str = ""
    mobile_number: str = ""
    ucc: str = ""
    mpin: str = ""
    #: Base32 secret from the one-time TOTP registration on Kotak's site.
    totp_secret: str = ""
    environment: str = "prod"
    max_subscriptions: int = Field(default=1000, ge=1)

    #: ClassVar, not a settings field: pydantic treats a bare attribute as one.
    REQUIRED: ClassVar[tuple[str, ...]] = (
        "consumer_key", "mobile_number", "ucc", "mpin", "totp_secret",
    )

    @property
    def is_configured(self) -> bool:
        return not self.missing_fields()

    def missing_fields(self) -> list[str]:
        """Blank and placeholder values both count as missing.

        python-dotenv keeps an inline `# comment` as part of the value, so a
        half-filled .env yields a non-empty string that is plainly not a
        credential. Treating that as configured sends the app at Kotak with
        comment text and fails at login instead of here.
        """
        return [name for name in self.REQUIRED if not _looks_real(getattr(self, name))]

    def placeholder_fields(self) -> list[str]:
        """Fields that hold something, but something that is obviously not a value."""
        return [
            name
            for name in self.REQUIRED
            if (value := getattr(self, name)) and not _looks_real(value)
        ]
