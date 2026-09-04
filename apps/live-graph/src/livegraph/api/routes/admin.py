"""Broker session administration.

Kotak sessions expire daily, so the one operation this exposes is a login. The
TOTP code is derived from the registered secret and rotates every 30 seconds;
it is shown only so a login can be confirmed or performed by hand if needed.

Credential values are never returned. The page reports whether each field is
set, never what it holds.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...feed import KotakSettings
from ...feed.totp import TotpError, current_code
from ..deps import get_state
from ..state import AppState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


class CredentialFieldOut(BaseModel):
    name: str
    label: str
    set: bool
    placeholder: bool
    hint: str


class TotpOut(BaseModel):
    available: bool
    code: str | None = None
    expires_in: int | None = None
    error: str | None = None


class BrokerStatusOut(BaseModel):
    feed_mode: str
    feed_detail: str
    configured: bool
    credentials: list[CredentialFieldOut]
    session_active: bool
    session_since: float | None = None
    last_error: str | None = None
    totp: TotpOut


class LoginResultOut(BaseModel):
    ok: bool
    message: str
    session_since: float | None = None


FIELDS: tuple[tuple[str, str, str], ...] = (
    ("consumer_key", "Consumer key",
     "Neo app or web: Invest tab, Trade API card, generate application."),
    ("mobile_number", "Mobile number", "Registered mobile with country code."),
    ("ucc", "UCC", "Unique Client Code, shown in your Neo profile."),
    ("mpin", "MPIN", "Your Neo MPIN."),
    ("totp_secret", "TOTP secret",
     "Base32 secret from the one-time QR registration. Set once, never daily."),
)


@router.get("/broker", response_model=BrokerStatusOut)
def broker_status(state: AppState = Depends(get_state)) -> BrokerStatusOut:
    settings = KotakSettings()
    missing = set(settings.missing_fields())
    placeholders = set(settings.placeholder_fields())
    session = state.kotak_session

    return BrokerStatusOut(
        feed_mode=state.feed_mode,
        feed_detail=state.feed_detail,
        configured=settings.is_configured,
        credentials=[
            CredentialFieldOut(
                name=name, label=label,
                set=name not in missing,
                placeholder=name in placeholders,
                hint=hint,
            )
            for name, label, hint in FIELDS
        ],
        session_active=bool(session and session.is_active),
        session_since=session.established_at if session else None,
        last_error=session.last_error if session else None,
        totp=_totp(settings),
    )


@router.get("/broker/totp", response_model=TotpOut)
def totp(state: AppState = Depends(get_state)) -> TotpOut:
    """Polled by the admin page so the code stays current as it rotates."""
    return _totp(KotakSettings())


@router.post("/broker/login", response_model=LoginResultOut)
def login(state: AppState = Depends(get_state)) -> LoginResultOut:
    """Establish a Kotak session now. Sessions expire daily."""
    settings = KotakSettings()
    if not settings.is_configured:
        raise HTTPException(
            status_code=400,
            detail=f"Missing credentials: {', '.join(settings.missing_fields())}",
        )
    ok, message = state.login_kotak()
    if not ok:
        raise HTTPException(status_code=502, detail=message)
    session = state.kotak_session
    return LoginResultOut(
        ok=True, message=message,
        session_since=session.established_at if session else None,
    )


def _totp(settings: KotakSettings) -> TotpOut:
    try:
        code = current_code(settings.totp_secret)
    except TotpError as exc:
        return TotpOut(available=False, error=str(exc))
    return TotpOut(available=True, code=code.code, expires_in=code.expires_in)
