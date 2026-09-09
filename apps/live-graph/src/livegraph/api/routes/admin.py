"""Broker and model administration.

Two things need setting up before this app is useful, and neither can be done
from a config file on a machine where the app is already running: Kotak
credentials, which expire into a daily login, and model access through
CLIProxyAPI.

The split between them is deliberate. Kotak credentials are five strings, so
this module takes them. Model access is an OAuth flow against Anthropic and
OpenAI, so this module does not: CLIProxyAPI owns those flows and ships a
control panel that drives them, and the most useful thing to do here is report
whether the proxy is answering and link to it.

Two rules hold throughout:

- Credential values are never returned. Every response says whether a field is
  set and where it came from, never what it holds.
- The whole surface needs the admin passphrase, reads included. Only
  `/session` is open, because a page has to be able to ask whether it is logged
  in and whether a passphrase was ever configured. Gating reads costs a login
  before you can read a status page, and buys one clear rule instead of a
  per-route judgement about which facts are worth protecting.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from ...credentials import KOTAK_FIELDS, NEVER_STORED, sources, write
from ...feed import KotakSettings
from ...feed.config import load_kotak_settings, mobile_digits
from ...feed.totp import TotpError, current_code
from ...llm import control_panel_url, get_llm_settings, probe_cliproxy
from .. import security
from ..deps import get_state
from ..state import AppState

logger = logging.getLogger(__name__)

#: Everything here needs a session. The dependency sits on the router so a new
#: route is protected by default: forgetting to add it should not be the thing
#: that exposes a credential surface.
router = APIRouter(
    prefix="/api/admin", tags=["admin"], dependencies=[Depends(security.require_admin)]
)

#: The one exception. Asking "am I logged in?" cannot itself require being
#: logged in, and "is a passphrase even set?" is what the page shows instead of
#: a login box when the answer is no.
session_router = APIRouter(prefix="/api/admin", tags=["admin"])


class CredentialFieldOut(BaseModel):
    name: str
    label: str
    set: bool
    placeholder: bool
    hint: str
    #: "store" (typed in here), "env" (.env) or "unset". Shown so an operator
    #: editing a field can see they are overriding a deployed value.
    source: str
    #: Why a field that passes every presence check will still not work. Says
    #: what is wrong with the value, never what the value is.
    problem: str | None = None


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


class LoginIn(BaseModel):
    """The values supplied per login rather than kept on disk.

    `mpin` is always one of these: it is never stored, so a login either
    carries it or fails. `totp` is optional, needed only when no usable secret
    is configured to derive a code from.
    """

    totp: str | None = None
    mpin: str | None = None


class LoginResultOut(BaseModel):
    ok: bool
    message: str
    session_since: float | None = None


class CredentialsIn(BaseModel):
    """Only the fields being changed need to be present.

    A blank string clears a field, handing it back to `.env`; an absent field is
    left alone. That distinction is what lets the page submit one edit without
    resending four secrets it never received in the first place.
    """

    values: dict[str, str] = Field(default_factory=dict)


class CredentialsResultOut(BaseModel):
    ok: bool
    changed: list[str]
    message: str
    configured: bool


class ModelAvailabilityOut(BaseModel):
    role: str
    name: str
    available: bool


class ModelStatusOut(BaseModel):
    base_url: str
    reachable: bool
    key_accepted: bool
    key_set: bool
    control_panel_url: str
    detail: str
    #: The two names this app actually asks for, each with whether the proxy
    #: advertises it. A proxy that is up but has no Claude credential loaded
    #: answers /v1/models without them, and that is the failure worth catching.
    models: list[ModelAvailabilityOut]


class SessionIn(BaseModel):
    passphrase: str


class SessionStateOut(BaseModel):
    #: False means LIVEGRAPH_ADMIN_PASSWORD is unset, so writes are refused
    #: outright and the page should say so rather than offer a login box.
    enabled: bool
    authenticated: bool


FIELDS: tuple[tuple[str, str, str], ...] = (
    ("consumer_key", "Consumer key",
     "Neo app or web: Invest tab, Trade API card, generate application."),
    ("mobile_number", "Mobile number", "Registered mobile with country code."),
    ("ucc", "UCC", "Unique Client Code, shown in your Neo profile."),
    ("mpin", "MPIN", "Your Neo MPIN."),
    ("totp_secret", "TOTP secret",
     "Base32 secret from the one-time QR registration. Set once, never daily."),
)


# ---- session ---------------------------------------------------------


@session_router.get("/session", response_model=SessionStateOut)
def session_state(
    token: str | None = Depends(security.optional_token),
) -> SessionStateOut:
    return SessionStateOut(
        enabled=security.configured(),
        authenticated=bool(token and security.token_is_valid(token)),
    )


@session_router.post("/session", response_model=SessionStateOut)
def open_session(body: SessionIn, response: Response) -> SessionStateOut:
    if not security.configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Admin writes are disabled because LIVEGRAPH_ADMIN_PASSWORD is not "
                "set. Set it in .env and restart to enable them."
            ),
        )
    if not security.verify_passphrase(body.passphrase):
        raise HTTPException(status_code=401, detail="Wrong passphrase.")

    response.set_cookie(
        security.COOKIE_NAME,
        security.issue_token(),
        max_age=security.SESSION_TTL_SECONDS,
        httponly=True,
        samesite="strict",
        path="/",
    )
    return SessionStateOut(enabled=True, authenticated=True)


@session_router.delete("/session", response_model=SessionStateOut)
def close_session(response: Response) -> SessionStateOut:
    response.delete_cookie(security.COOKIE_NAME, path="/")
    return SessionStateOut(enabled=security.configured(), authenticated=False)


# ---- broker ----------------------------------------------------------


@router.get("/broker", response_model=BrokerStatusOut)
def broker_status(state: AppState = Depends(get_state)) -> BrokerStatusOut:
    settings = load_kotak_settings()
    missing = set(settings.missing_fields())
    placeholders = set(settings.placeholder_fields())
    #: Blank out anything `missing_fields` rejected, placeholders included, so a
    #: field cannot report "not set" and "from .env" at once. The placeholder
    #: badge is what says .env holds comment text there.
    origin = sources(
        {
            name: "" if name in missing else getattr(settings, name)
            for name in KOTAK_FIELDS
        }
    )
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
                source=origin.get(name, "unset"),
                problem=_problem(name, settings) if name not in missing else None,
            )
            for name, label, hint in FIELDS
        ],
        session_active=bool(session and session.is_active),
        session_since=session.established_at if session else None,
        last_error=session.last_error if session else None,
        totp=_totp(settings),
    )


@router.put("/broker/credentials", response_model=CredentialsResultOut)
def set_credentials(body: CredentialsIn) -> CredentialsResultOut:
    """Store credentials typed into the admin page.

    The feed is not rebuilt here. Swapping a live socket underneath a running
    app is a separate concern, and `login_kotak` already says a restart is what
    picks up working credentials, so the honest thing is to save and say so.
    """
    if refused := sorted(NEVER_STORED & set(body.values)):
        raise HTTPException(
            status_code=400,
            detail=(
                f"{', '.join(refused)} is never stored. It is typed at each login, "
                "so that it is not on disk beside the secret that generates codes."
            ),
        )
    unknown = sorted(set(body.values) - KOTAK_FIELDS)
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown fields: {', '.join(unknown)}")

    changed = write(body.values)
    settings = load_kotak_settings()
    #: Field names only. A value must not reach a log any more than a response.
    logger.info("admin updated Kotak credentials: %s", ", ".join(changed) or "no change")

    if not changed:
        message = "No change."
    elif settings.is_configured:
        message = (
            f"Saved {len(changed)} value(s). All five are present — log in now, or "
            "restart to start the feed."
        )
    else:
        message = (
            f"Saved {len(changed)} value(s). Still missing: "
            f"{', '.join(settings.missing_fields())}."
        )
    return CredentialsResultOut(
        ok=True, changed=changed, message=message, configured=settings.is_configured
    )


@router.get("/broker/totp", response_model=TotpOut)
def totp(state: AppState = Depends(get_state)) -> TotpOut:
    """Polled by the admin page so the code stays current as it rotates."""
    return _totp(load_kotak_settings())


@router.post("/broker/login", response_model=LoginResultOut)
def login(body: LoginIn | None = None, state: AppState = Depends(get_state)) -> LoginResultOut:
    """Establish a Kotak session now, and start the feed if one is not running.

    Sessions expire daily, so this is the first thing done each trading morning.
    """
    totp = (body.totp or "").strip() if body else ""
    mpin = (body.mpin or "").strip() if body else ""
    settings = load_kotak_settings()
    #: A supplied value is what storing it would have provided, so each one
    #: stops being required the moment it is typed in.
    supplied = {"totp_secret": bool(totp), "mpin": bool(mpin)}
    missing = [f for f in settings.missing_fields() if not supplied.get(f)]
    if missing:
        raise HTTPException(
            status_code=400, detail=f"Missing credentials: {', '.join(missing)}",
        )
    if totp and not (totp.isdigit() and len(totp) == 6):
        raise HTTPException(status_code=400, detail="The TOTP code is six digits.")
    ok, message = state.login_kotak(totp=totp or None, mpin=mpin or None)
    if not ok:
        raise HTTPException(status_code=502, detail=message)
    session = state.kotak_session
    return LoginResultOut(
        ok=True, message=message,
        session_since=session.established_at if session else None,
    )


# ---- models ----------------------------------------------------------


@router.get("/models", response_model=ModelStatusOut)
def model_status() -> ModelStatusOut:
    """Whether the agentic half of the app can work, and where to fix it."""
    settings = get_llm_settings()
    probe = probe_cliproxy(settings)
    return ModelStatusOut(
        base_url=probe.base_url,
        reachable=probe.reachable,
        key_accepted=probe.key_accepted,
        key_set=bool(settings.cliproxy_api_key),
        control_panel_url=control_panel_url(settings),
        detail=probe.detail,
        models=[
            ModelAvailabilityOut(
                role=role, name=name, available=probe.resolves(name)
            )
            for role, name in (
                ("Analyst and narration", settings.livegraph_agent_model),
                ("Strategy code", settings.livegraph_coder_model),
            )
        ],
    )


def _problem(name: str, settings: KotakSettings) -> str | None:
    """What is wrong with a field that is set, in words that name no value.

    A stored value passes every presence check and then fails at Kotak, which
    is the worst place to find out. These are the two that go wrong in practice.

    Kept to a short phrase: it is rendered as a badge beside the field, and the
    long form of the TOTP failure is already on the code card below it.
    """
    if name == "mobile_number" and not mobile_digits(settings.mobile_number):
        return "not a ten-digit Indian mobile number"
    if name == "totp_secret":
        try:
            current_code(settings.totp_secret)
        except TotpError:
            return "not a usable base32 secret"
    return None


def _totp(settings: KotakSettings) -> TotpOut:
    try:
        code = current_code(settings.totp_secret)
    except TotpError as exc:
        return TotpOut(available=False, error=str(exc))
    return TotpOut(available=True, code=code.code, expires_in=code.expires_in)
