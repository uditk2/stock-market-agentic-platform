from __future__ import annotations

import re
from typing import ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PUNCTUATION = re.compile(r"[\s()\-.]")
_INDIA_CODE = "91"


def _looks_real(value: str) -> bool:
    text = (value or "").strip()
    return bool(text) and not text.startswith("#")


def mobile_digits(value: str) -> str:
    """The ten subscriber digits, without punctuation, country code or trunk 0.

    Empty when the value cannot be read as an Indian mobile number at all — a
    number no spelling will rescue, which the admin page says so rather than
    letting Kotak be the one to discover it.
    """
    digits = _PUNCTUATION.sub("", (value or "").strip()).lstrip("+")
    if not digits.isdigit():
        return ""
    if len(digits) == 12 and digits.startswith(_INDIA_CODE):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits if len(digits) == 10 else ""


def mobile_spellings(value: str) -> tuple[str, ...]:
    """Every spelling of the number Kotak might take, most likely first.

    `totp_login` validates `mobileNumber` as a field before it looks at the
    credentials behind it, and rejects the spelling it does not want with
    "Invalid field 'MobileNumber'; must be a valid mobile number" — without
    saying which one it wanted. The same ten digits are correct in all three
    forms, so the login tries them in turn rather than making an operator guess
    at a format their broker never documented.
    """
    digits = mobile_digits(value)
    if not digits:
        #: Unreadable. Send what was typed, so Kotak's own words come back
        #: rather than this module inventing a failure of its own.
        return ((value or "").strip(),)
    return (f"+{_INDIA_CODE}{digits}", f"{_INDIA_CODE}{digits}", digits)


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


def load_kotak_settings() -> "KotakSettings":
    """Credentials as the app should see them: the admin store over `.env`.

    Import is local because `livegraph.credentials` touches the filesystem, and
    `KotakSettings` itself must stay constructible in a test with no state
    directory. Values passed to the constructor beat environment variables in
    pydantic-settings, which is exactly the precedence documented on the store.
    """
    from ..credentials import read

    return KotakSettings(**read())
