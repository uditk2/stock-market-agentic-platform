"""Kotak Neo authentication.

Two-step TOTP flow per the Neo v2 SDK: `totp_login` yields the view token and
session id, `totp_validate` exchanges the MPIN for the trade token. Both must
succeed before the socket will accept a subscribe.
"""

from __future__ import annotations

import logging
import re
import time

from .config import KotakSettings, mobile_spellings
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

    def login(self, totp: str | None = None, mpin: str | None = None):
        """Establish a trading session, with the two per-login values optional.

        `totp` is the six-digit code and `mpin` the trading PIN. Both can be
        stored, and neither has to be: supplying one satisfies the requirement
        that storing it would have met. That is what lets a person log in from
        the Admin tab reading their authenticator, with the MPIN typed and
        never written down, while an unattended deployment keeps both in .env.
        """
        supplied = {"totp_secret": bool(totp), "mpin": bool(mpin)}
        missing = [
            field
            for field in self._settings.missing_fields()
            if not supplied.get(field)
        ]
        if missing:
            raise KotakAuthError(f"Missing Kotak credentials: {', '.join(missing)}")

        client = self._client_factory(self._settings)
        try:
            code = totp or generate_totp(self._settings.totp_secret)
        except TotpError as exc:
            raise KotakAuthError(str(exc)) from exc
        self._totp_login(client, code)
        self._call(
            client.totp_validate, "totp_validate", mpin=mpin or self._settings.mpin
        )
        self._client = client
        self._established_at = time.time()
        self._last_error = None
        logger.info("Kotak session established for ucc=%s", self._settings.ucc)
        return client

    def _totp_login(self, client, code: str) -> None:
        """Log in, trying each spelling of the mobile number Kotak may want.

        Kotak checks `mobileNumber` as a field before it checks the credentials
        behind it, so the wrong spelling of a correct number fails exactly like
        a wrong number. The same code serves every attempt: it is one 30-second
        window, and a field rejection never reaches the check that would spend
        it. Any other error is final and is raised where it happened.
        """
        spellings = mobile_spellings(self._settings.mobile_number)
        for attempt, mobile in enumerate(spellings, start=1):
            try:
                self._call(
                    client.totp_login,
                    "totp_login",
                    mobile_number=mobile,
                    ucc=self._settings.ucc,
                    totp=code,
                )
            except KotakAuthError as exc:
                if not _is_mobile_rejection(str(exc)):
                    raise
                if attempt == len(spellings) == 1:
                    #: One form, because `mobile_spellings` could not read the
                    #: value as a mobile number at all. The reasoning below
                    #: does not apply: a malformed number is precisely what the
                    #: field check refuses, so this is not rate limiting and
                    #: waiting will not help.
                    raise KotakAuthError(
                        "Kotak refused the mobile number, and it is not in a shape "
                        "this app can read as a ten-digit Indian mobile number. "
                        f"Kotak said: {exc}"
                    ) from exc
                if attempt == len(spellings):
                    #: Every form refused. Do not conclude the number is wrong:
                    #: measured against the live API, a malformed number is
                    #: refused on the field and a well-formed one reaches the
                    #: code check, which answers "Invalid TOTP" instead. A
                    #: well-formed number refused on the field is therefore
                    #: something other than its spelling, and saying otherwise
                    #: sends someone to correct a value that is already right.
                    raise KotakAuthError(
                        "Kotak refused the mobile number in every form it accepts "
                        f"({', '.join(spellings)}). A number in this shape normally "
                        "gets as far as the code check, so this is usually either "
                        "the wrong number for this UCC or too many attempts in quick "
                        f"succession — wait a minute and retry before changing it. "
                        f"Kotak said: {exc}"
                    ) from exc
                logger.info(
                    "Kotak refused the mobile number's spelling (%d of %d); retrying",
                    attempt, len(spellings),
                )
                #: Kotak rate-limits bursts, and three rejected logins inside a
                #: second is a burst. Pacing them keeps a format retry from
                #: turning into the throttling it then reports as a bad number.
                time.sleep(_RETRY_PAUSE_SECONDS)
                continue
            if attempt > 1:
                #: Worth knowing: the stored value needs rewriting to stop
                #: paying for two rejected round trips every morning.
                logger.info("Kotak accepted the mobile number on spelling %d", attempt)
            return

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


#: Long enough to leave a burst, short enough that three attempts still
#: finish inside one 30-second TOTP window.
_RETRY_PAUSE_SECONDS = 1.5

#: Kotak names the field it refused: "Invalid field 'MobileNumber'".
_MOBILE_FIELD = re.compile(r"mobile\s*number", re.I)


def _is_mobile_rejection(message: str) -> bool:
    return bool(_MOBILE_FIELD.search(message))


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
