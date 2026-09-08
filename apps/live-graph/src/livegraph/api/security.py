"""The passphrase gate on admin writes.

The app binds to localhost, so the threat this answers is narrow and worth
naming: anything else running on the same machine — another container with a
published port, a browser tab on a hostile page, a stray `--host 0.0.0.0` — can
reach the API. Reads are already safe, because no endpoint returns a credential
value. Writes are not, so they are gated.

One shared passphrase, not accounts. There is exactly one operator here, and a
user table would be more code guarding the same secret.

Three decisions worth stating, because each is the opposite of a plausible one:

- With no passphrase set, admin writes are **refused**, not opened. Failing
  closed makes a missing setting a locked door rather than a silent hole.
- The cookie is signed, not stored. Sessions are the only thing a restart may
  reasonably drop, and keeping a server-side table would outlive its usefulness.
- The signing key is derived from the passphrase, so changing the passphrase
  invalidates every outstanding cookie without any revocation machinery.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from functools import lru_cache

from fastapi import Cookie, HTTPException
from pydantic_settings import BaseSettings, SettingsConfigDict

COOKIE_NAME = "livegraph_admin"
#: A trading day, so an operator who logs in at the open is still in at the close.
SESSION_TTL_SECONDS = 12 * 60 * 60

_ENV_VAR = "LIVEGRAPH_ADMIN_PASSWORD"
#: Domain separation: the signing key must not be the passphrase itself, so a
#: leaked cookie cannot be walked back into the value the operator types.
_KEY_SALT = b"livegraph-admin-session-v1"


def configured() -> bool:
    return bool(_passphrase())


def verify_passphrase(candidate: str) -> bool:
    """Constant-time comparison; a timing oracle on a short secret is real."""
    expected = _passphrase()
    if not expected:
        return False
    return hmac.compare_digest(candidate.encode(), expected.encode())


def issue_token(now: float | None = None) -> str:
    """A signed `payload.signature`, both base64url, no padding."""
    expires = int(now if now is not None else time.time()) + SESSION_TTL_SECONDS
    payload = _b64encode(json.dumps({"exp": expires}, separators=(",", ":")).encode())
    return f"{payload}.{_b64encode(_sign(payload.encode()))}"


def token_is_valid(token: str, now: float | None = None) -> bool:
    payload, _, signature = token.partition(".")
    if not payload or not signature:
        return False
    if not hmac.compare_digest(signature, _b64encode(_sign(payload.encode()))):
        return False
    try:
        expires = json.loads(_b64decode(payload))["exp"]
    except (ValueError, KeyError, TypeError):
        return False
    return float(expires) > (now if now is not None else time.time())


def optional_token(token: str | None = Cookie(default=None, alias=COOKIE_NAME)) -> str | None:
    """The cookie, unvalidated. For the status endpoint, which reports rather
    than enforces: it must answer "not logged in" instead of raising 401."""
    return token


def require_admin(token: str | None = Cookie(default=None, alias=COOKIE_NAME)) -> None:
    """Dependency for every route that writes. Reads stay open by design."""
    if not configured():
        raise HTTPException(
            status_code=503,
            detail=(
                f"Admin writes are disabled because {_ENV_VAR} is not set. "
                "Set it in .env and restart to enable them."
            ),
        )
    if not token or not token_is_valid(token):
        raise HTTPException(status_code=401, detail="Admin session required.")


class AdminSettings(BaseSettings):
    """Read like every other setting here, which means `.env` counts.

    Reaching into `os.environ` instead was a bug worth naming: pydantic-settings
    loads `.env` itself without exporting it, so the passphrase worked under
    compose — which injects real environment variables — and was invisible when
    running from source, where `.env` is the documented place to put it.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    livegraph_admin_password: str = ""


def _passphrase() -> str:
    """Read per call, not at import: an edited `.env` should take effect on a
    restart of the process, not of the interpreter, and tests change it too."""
    return AdminSettings().livegraph_admin_password.strip()


def _sign(payload: bytes) -> bytes:
    return hmac.new(_signing_key(_passphrase()), payload, hashlib.sha256).digest()


@lru_cache(maxsize=4)
def _signing_key(passphrase: str) -> bytes:
    """Cached on the passphrase: 100k PBKDF2 rounds per request would be absurd.

    The stretching is here to make the *derived key* expensive to work back to
    the passphrase, not to slow down a login. Caching keeps a signature check
    at HMAC cost, and a changed passphrase simply derives under a new key.
    """
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode(), _KEY_SALT, 100_000)


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
