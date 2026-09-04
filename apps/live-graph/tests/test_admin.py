"""Regressions guarded here:

- Credential values must never leave the process. The admin endpoint reports
  presence only; leaking an MPIN or a TOTP secret into a browser payload would
  be the worst defect in this app.
- A half-filled .env must read as unconfigured. python-dotenv keeps an inline
  "# comment" as part of the value, so a placeholder is a non-empty string that
  is plainly not a credential; treating it as configured sends comment text to
  Kotak and fails at login instead of here.
- A malformed TOTP secret must fail with an explanation, not a bare pyotp error
  surfaced from inside a login attempt.
"""

import time

import pytest
from fastapi.testclient import TestClient

from livegraph.api import create_app
from livegraph.feed.config import KotakSettings
from livegraph.feed.totp import TOTP_PERIOD_SECONDS, TotpError, current_code

SECRET = "JBSWY3DPEHPK3PXP"


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app(simulate=True)) as c:
        yield c


# ---- TOTP ------------------------------------------------------------


def test_code_is_six_digits_and_rotates_every_thirty_seconds():
    first = current_code(SECRET, at=1_000_000)
    assert first.code.isdigit() and len(first.code) == 6
    assert current_code(SECRET, at=1_000_000 + 5).code == first.code
    assert current_code(SECRET, at=1_000_000 + TOTP_PERIOD_SECONDS).code != first.code


def test_expiry_counts_down_within_the_window():
    #: Derive the window boundary rather than guessing an instant near it.
    window_start = 1_000_000 - (1_000_000 % TOTP_PERIOD_SECONDS)
    assert current_code(SECRET, at=window_start).expires_in == TOTP_PERIOD_SECONDS
    assert current_code(SECRET, at=window_start + 28).expires_in == 2
    assert current_code(SECRET, at=window_start + 28).about_to_rotate
    assert not current_code(SECRET, at=window_start + 10).about_to_rotate


def test_a_malformed_secret_explains_itself():
    with pytest.raises(TotpError, match="base32"):
        current_code("not base32 !!")


def test_a_missing_secret_is_not_a_crash():
    with pytest.raises(TotpError, match="No TOTP secret"):
        current_code("")


def test_spaces_in_a_pasted_secret_are_tolerated():
    """Authenticator apps display the secret in spaced groups."""
    spaced = "JBSW Y3DP EHPK 3PXP"
    assert current_code(spaced, at=1_000_000).code == current_code(SECRET, at=1_000_000).code


# ---- credential validation -------------------------------------------


def test_an_inline_comment_counts_as_missing():
    settings = KotakSettings(
        consumer_key="real", mobile_number="# with country code",
        ucc="real", mpin="real", totp_secret=SECRET,
    )
    assert not settings.is_configured
    assert "mobile_number" in settings.missing_fields()
    assert settings.placeholder_fields() == ["mobile_number"]


def test_a_fully_filled_env_is_configured():
    settings = KotakSettings(
        consumer_key="k", mobile_number="+919876543210",
        ucc="ABC12", mpin="1234", totp_secret=SECRET,
    )
    assert settings.is_configured
    assert settings.missing_fields() == []


# ---- the endpoint ----------------------------------------------------


def test_broker_status_never_returns_credential_values(client):
    body = client.get("/api/admin/broker").json()
    raw = client.get("/api/admin/broker").text

    assert set(body["credentials"][0]) == {"name", "label", "set", "placeholder", "hint"}
    #: Whatever the local .env holds, none of it may appear in the payload.
    settings = KotakSettings()
    for field in KotakSettings.REQUIRED:
        value = getattr(settings, field)
        if value and len(value) > 6:
            assert value not in raw, f"{field} value leaked into the response"


def test_broker_status_reports_the_feed_mode(client):
    body = client.get("/api/admin/broker").json()
    assert body["feed_mode"] == "simulated"
    assert body["session_active"] is False


def test_login_is_refused_while_credentials_are_missing(client):
    response = client.post("/api/admin/broker/login")
    assert response.status_code == 400
    assert "Missing credentials" in response.json()["detail"]


def test_totp_endpoint_reports_the_absence_rather_than_erroring(client):
    body = client.get("/api/admin/broker/totp").json()
    assert body["available"] is False
    assert body["error"]
    assert body["code"] is None
