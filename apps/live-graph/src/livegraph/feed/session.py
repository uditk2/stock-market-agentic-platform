"""Kotak Neo authentication.

Two-step TOTP flow per the Neo v2 SDK: `totp_login` yields the view token and
session id, `totp_validate` exchanges the MPIN for the trade token. Both must
succeed before the socket will accept a subscribe.
"""

from __future__ import annotations

import logging
import time

from .config import KotakSettings
from .totp import TotpError, current_code

logger = logging.getLogger(__name__)


class KotakAuthError(RuntimeError):
    pass


class KotakSession:
    def __init__(self, settings: KotakSettings, client_factory=None):
        self._settings = settings
        self._client_factory = client_factory or _default_client_factory
        self._client = None
        self._established_at: float | None = None
        self._last_error: str | None = None

    @property
    def client(self):
        if self._client is None:
            raise KotakAuthError("Session not established; call login() first.")
        return self._client

    @property
    def is_active(self) -> bool:
        return self._client is not None

    def login(self, totp: str | None = None):
        """Establish a trading session. Pass `totp` to override the generated code."""
        missing = self._settings.missing_fields()
        if missing:
            raise KotakAuthError(f"Missing Kotak credentials: {', '.join(missing)}")

        client = self._client_factory(self._settings)
        try:
            code = totp or generate_totp(self._settings.totp_secret)
        except TotpError as exc:
            raise KotakAuthError(str(exc)) from exc
        self._call(
            client.totp_login,
            "totp_login",
            mobile_number=self._settings.mobile_number,
            ucc=self._settings.ucc,
            totp=code,
        )
        self._call(client.totp_validate, "totp_validate", mpin=self._settings.mpin)
        self._client = client
        self._established_at = time.time()
        self._last_error = None
        logger.info("Kotak session established for ucc=%s", self._settings.ucc)
        return client

    @property
    def established_at(self) -> float | None:
        return self._established_at

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def record_failure(self, message: str) -> None:
        self._last_error = message

    def logout(self) -> None:
        if self._client is None:
            return
        try:
            self._client.logout()
        except Exception as exc:  # noqa: BLE001 - teardown must not mask real errors
            logger.warning("Kotak logout failed: %s", exc)
        finally:
            self._client = None
            self._established_at = None

    @staticmethod
    def _call(fn, label: str, **kwargs):
        """The SDK signals failure by returning an error dict, not by raising."""
        try:
            response = fn(**kwargs)
        except Exception as exc:  # noqa: BLE001 - SDK raises bare Exception
            raise KotakAuthError(f"{label} failed: {exc}") from exc
        if isinstance(response, dict) and _is_error(response):
            raise KotakAuthError(f"{label} rejected: {_error_text(response)}")
        return response


def generate_totp(secret: str) -> str:
    return current_code(secret).code


def _default_client_factory(settings: KotakSettings):
    from neo_api_client import NeoAPI

    return NeoAPI(
        environment=settings.environment,
        access_token=None,
        neo_fin_key=None,
        consumer_key=settings.consumer_key,
    )


def _is_error(response: dict) -> bool:
    if "error" in response or "Error" in response:
        return True
    status = str(response.get("stat", response.get("status", ""))).lower()
    return status in {"not_ok", "error", "failure"}


def _error_text(response: dict) -> str:
    for key in ("error", "Error", "emsg", "message", "errMsg"):
        if value := response.get(key):
            return str(value)[:200]
    return str(response)[:200]
