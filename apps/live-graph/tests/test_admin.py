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
- Every admin route except the session handshake must need a session. A new
  route added without the gate is the failure this file is here to catch.
"""

import os
import stat
import time
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from fake_feed import FakeFeed

from livegraph import credentials
from livegraph.api import create_app, security
from livegraph.feed.config import KotakSettings, load_kotak_settings
from livegraph.feed.totp import TOTP_PERIOD_SECONDS, TotpError, current_code
from livegraph.llm import LLMSettings, control_panel_url, probe_cliproxy
from livegraph.paths import state_dir

SECRET = "JBSWY3DPEHPK3PXP"
PASSPHRASE = "open-sesame"


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app(feed=FakeFeed([("INFY", 1500.0, -1.0)]))) as c:
        yield c


@pytest.fixture(scope="module", autouse=True)
def admin_passphrase():
    """A passphrase for the whole module, so tests can choose to log in or not.

    Set at module scope rather than per test because most of these exercise the
    endpoints behind the gate; the few that check the unconfigured case delete
    it again with monkeypatch.
    """
    os.environ["LIVEGRAPH_ADMIN_PASSWORD"] = PASSPHRASE
    yield
    os.environ.pop("LIVEGRAPH_ADMIN_PASSWORD", None)


@pytest.fixture
def unlocked(client):
    """A client holding a valid admin session. Every read here needs one."""
    client.cookies.clear()
    assert client.post("/api/admin/session", json={"passphrase": PASSPHRASE}).status_code == 200
    yield client
    client.cookies.clear()


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


def test_broker_status_never_returns_credential_values(unlocked):
    body = unlocked.get("/api/admin/broker").json()
    raw = unlocked.get("/api/admin/broker").text

    #: Pinned, so a field added to this payload has to be considered here
    #: before it can carry a value out of the process.
    assert set(body["credentials"][0]) == {
        "name", "label", "set", "placeholder", "hint", "source", "problem",
    }
    #: Whatever the local .env holds, none of it may appear in the payload.
    settings = KotakSettings()
    for field in KotakSettings.REQUIRED:
        value = getattr(settings, field)
        if value and len(value) > 6:
            assert value not in raw, f"{field} value leaked into the response"


def test_broker_status_reports_the_feed_mode(unlocked):
    body = unlocked.get("/api/admin/broker").json()
    assert body["feed_mode"] == "injected"
    assert body["session_active"] is False


def test_login_is_refused_while_credentials_are_missing(client, monkeypatch):
    """Unlocked, so the 400 is about the credentials rather than the gate."""
    monkeypatch.setenv("LIVEGRAPH_ADMIN_PASSWORD", "open-sesame")
    client.cookies.clear()
    client.post("/api/admin/session", json={"passphrase": "open-sesame"})

    response = client.post("/api/admin/broker/login")
    assert response.status_code == 400
    assert "Missing credentials" in response.json()["detail"]


def test_totp_endpoint_reports_the_absence_rather_than_erroring(unlocked):
    body = unlocked.get("/api/admin/broker/totp").json()
    assert body["available"] is False
    assert body["error"]
    assert body["code"] is None


# ---- the credential store --------------------------------------------


def test_a_stored_value_overrides_the_environment(monkeypatch):
    """The admin page is the more recent statement of intent, so it wins.

    A UI whose edits silently lose to an older .env would be worse than one
    with no edits at all: the operator would see the value they typed reported
    as set, and the app would go on using the other one.
    """
    monkeypatch.setenv("KOTAK_UCC", "from-env")
    assert KotakSettings().ucc == "from-env"

    credentials.write({"ucc": "from-store"})
    try:
        assert load_kotak_settings().ucc == "from-store"
    finally:
        credentials.write({"ucc": ""})
    assert load_kotak_settings().ucc == "from-env"


def test_clearing_a_field_hands_it_back_to_the_environment(monkeypatch):
    monkeypatch.setenv("KOTAK_MPIN", "env-value")
    credentials.write({"mpin": "typed"})
    assert credentials.sources({"mpin": "typed"})["mpin"] == "store"

    credentials.write({"mpin": ""})
    assert credentials.sources({"mpin": "env-value"})["mpin"] == "env"
    assert credentials.sources({"mpin": ""})["mpin"] == "unset"


def test_the_store_is_written_readable_only_by_its_owner():
    """It holds an MPIN and a TOTP secret in plain text; 0600 is the floor."""
    credentials.write({"consumer_key": "k"})
    path = state_dir() / "credentials.json"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    credentials.write({"consumer_key": ""})


def test_unwritable_junk_in_the_store_does_not_take_the_app_down():
    path = state_dir() / "credentials.json"
    path.write_text("{ not json")
    try:
        assert credentials.read() == {}
    finally:
        path.unlink()


def test_only_known_fields_can_be_written():
    """The store must not become a way to set arbitrary configuration."""
    assert credentials.write({"LIVEGRAPH_UI_DIR": "/tmp/evil"}) == []
    assert credentials.read() == {}


# ---- the passphrase gate ---------------------------------------------


def test_writes_are_refused_when_no_passphrase_is_configured(client, monkeypatch):
    """Failing closed: a missing setting is a locked door, not an open one.

    Set empty rather than deleted. The passphrase is read through
    pydantic-settings, so an unset variable falls through to whatever the
    developer's own `.env` holds and this would pass or fail by machine; an
    empty environment variable takes precedence over the file.
    """
    monkeypatch.setenv("LIVEGRAPH_ADMIN_PASSWORD", "")
    assert client.get("/api/admin/session").json() == {
        "enabled": False, "authenticated": False,
    }
    assert client.put("/api/admin/broker/credentials", json={"values": {}}).status_code == 503
    assert client.post("/api/admin/broker/login").status_code == 503


def test_writes_need_a_session_even_once_a_passphrase_exists(client, monkeypatch):
    monkeypatch.setenv("LIVEGRAPH_ADMIN_PASSWORD", "open-sesame")
    client.cookies.clear()
    assert client.get("/api/admin/session").json()["enabled"] is True
    response = client.put("/api/admin/broker/credentials", json={"values": {"ucc": "X"}})
    assert response.status_code == 401


def test_the_wrong_passphrase_is_refused(client, monkeypatch):
    monkeypatch.setenv("LIVEGRAPH_ADMIN_PASSWORD", "open-sesame")
    client.cookies.clear()
    assert client.post("/api/admin/session", json={"passphrase": "guess"}).status_code == 401
    assert client.get("/api/admin/session").json()["authenticated"] is False


def test_a_session_unlocks_writes_and_logging_out_relocks_them(client, monkeypatch):
    monkeypatch.setenv("LIVEGRAPH_ADMIN_PASSWORD", "open-sesame")
    client.cookies.clear()

    assert client.post("/api/admin/session", json={"passphrase": "open-sesame"}).status_code == 200
    assert client.get("/api/admin/session").json()["authenticated"] is True

    saved = client.put("/api/admin/broker/credentials", json={"values": {"ucc": "ABC12"}})
    assert saved.status_code == 200
    assert saved.json()["changed"] == ["ucc"]

    client.delete("/api/admin/session")
    assert client.get("/api/admin/session").json()["authenticated"] is False
    assert client.put("/api/admin/broker/credentials", json={"values": {}}).status_code == 401
    credentials.write({"ucc": ""})


def test_changing_the_passphrase_invalidates_outstanding_sessions(monkeypatch):
    """The signing key is derived from the passphrase, so this is free."""
    monkeypatch.setenv("LIVEGRAPH_ADMIN_PASSWORD", "first")
    token = security.issue_token()
    assert security.token_is_valid(token)

    monkeypatch.setenv("LIVEGRAPH_ADMIN_PASSWORD", "second")
    assert not security.token_is_valid(token)


def test_an_expired_token_is_rejected(monkeypatch):
    monkeypatch.setenv("LIVEGRAPH_ADMIN_PASSWORD", "first")
    issued_at = time.time() - security.SESSION_TTL_SECONDS - 60
    assert not security.token_is_valid(security.issue_token(now=issued_at))


def test_a_tampered_token_is_rejected(monkeypatch):
    monkeypatch.setenv("LIVEGRAPH_ADMIN_PASSWORD", "first")
    payload, _, signature = security.issue_token().partition(".")
    assert not security.token_is_valid(f"{payload}x.{signature}")
    assert not security.token_is_valid(f"{payload}.{signature[:-2]}ab")
    assert not security.token_is_valid("no-dot-at-all")


def test_a_credential_write_never_echoes_the_value_back(client, monkeypatch):
    monkeypatch.setenv("LIVEGRAPH_ADMIN_PASSWORD", "open-sesame")
    client.cookies.clear()
    client.post("/api/admin/session", json={"passphrase": "open-sesame"})

    secret = "super-secret-mpin-value"
    response = client.put("/api/admin/broker/credentials", json={"values": {"mpin": secret}})
    assert secret not in response.text
    assert secret not in client.get("/api/admin/broker").text
    credentials.write({"mpin": ""})


def test_unknown_credential_names_are_rejected_at_the_edge(client, monkeypatch):
    monkeypatch.setenv("LIVEGRAPH_ADMIN_PASSWORD", "open-sesame")
    client.cookies.clear()
    client.post("/api/admin/session", json={"passphrase": "open-sesame"})

    response = client.put(
        "/api/admin/broker/credentials", json={"values": {"ucc": "ok", "shell": "rm -rf /"}}
    )
    assert response.status_code == 400
    assert "shell" in response.json()["detail"]
    #: Rejected outright, so the valid half of the payload must not be applied.
    assert credentials.read() == {}


# ---- model access ----------------------------------------------------


def test_model_status_reports_an_unreachable_proxy_without_raising(unlocked, monkeypatch):
    """The page must render when the proxy is down; that is when it is needed."""
    monkeypatch.setattr(
        "livegraph.api.routes.admin.get_llm_settings",
        lambda: LLMSettings(cliproxy_base_url="http://127.0.0.1:9/v1", cliproxy_api_key="k"),
    )
    body = unlocked.get("/api/admin/models").json()

    assert body["reachable"] is False
    assert body["control_panel_url"] == "http://127.0.0.1:9/management.html"
    #: Not "unavailable": an unreachable proxy cannot report on a model at all.
    assert [m["available"] for m in body["models"]] == [False, False]
    assert "127.0.0.1:9" in body["detail"]


def test_a_rejected_key_is_told_apart_from_a_dead_proxy():
    """Three states the page must distinguish, and only one of them is 'down'."""
    import urllib.error

    def unauthorised(*args, **kwargs):
        raise urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)

    with mock.patch("urllib.request.urlopen", unauthorised):
        probe = probe_cliproxy(LLMSettings(cliproxy_api_key="wrong"))

    assert probe.reachable is True
    assert probe.key_accepted is False
    assert "rejected" in probe.detail.lower()


def test_the_control_panel_sits_above_the_openai_prefix():
    """/v1 is the OpenAI-compatible surface; the panel is served at the root."""
    settings = LLMSettings(cliproxy_base_url="http://proxy.internal:8317/v1")
    assert control_panel_url(settings) == "http://proxy.internal:8317/management.html"


def test_a_placeholder_reports_as_unset_rather_than_as_coming_from_env(unlocked):
    """Three signals about one field must agree, not contradict each other."""
    body = unlocked.get("/api/admin/broker").json()
    for field in body["credentials"]:
        if field["placeholder"]:
            assert field["set"] is False
            assert field["source"] == "unset", (
                f"{field['name']} says it came from .env while reporting itself unset"
            )


def test_every_admin_route_but_the_session_handshake_needs_a_session(client):
    """Enumerated from the app, not hand-listed, so a new route cannot be missed.

    The router carries the dependency, so this passes by construction today.
    It exists for the change that adds a route to a fresh APIRouter and wires
    it up without one.
    """
    client.cookies.clear()
    paths = [p for p in client.app.openapi()["paths"] if p.startswith("/api/admin")]
    assert len(paths) > 1, "expected the admin surface to be discoverable"

    for path in paths:
        for method in client.app.openapi()["paths"][path]:
            response = client.request(method.upper(), path, json={"values": {}})
            if path == "/api/admin/session":
                assert response.status_code != 401, f"{method} {path} must stay reachable"
            else:
                assert response.status_code == 401, (
                    f"{method} {path} answered {response.status_code} without a session"
                )


# ---- the daily login -------------------------------------------------


def test_a_typed_code_removes_the_need_for_a_stored_secret(unlocked, monkeypatch):
    """The morning path: four credentials stored, the code read off a phone."""
    credentials.write({
        "consumer_key": "k", "mobile_number": "+919876543210",
        "ucc": "ABC12", "mpin": "1234",
    })
    seen = {}

    def fake_login(totp=None):
        seen["totp"] = totp
        return True, "Session established."

    monkeypatch.setattr(
        "livegraph.api.state.AppState.login_kotak", lambda self, totp=None: fake_login(totp)
    )
    try:
        response = unlocked.post("/api/admin/broker/login", json={"totp": "123456"})
        assert response.status_code == 200
        assert seen["totp"] == "123456"
    finally:
        for field in ("consumer_key", "mobile_number", "ucc", "mpin"):
            credentials.write({field: ""})


def test_without_a_code_the_missing_secret_is_still_refused(unlocked):
    credentials.write({
        "consumer_key": "k", "mobile_number": "+919876543210",
        "ucc": "ABC12", "mpin": "1234",
    })
    try:
        response = unlocked.post("/api/admin/broker/login", json={})
        assert response.status_code == 400
        assert "totp_secret" in response.json()["detail"]
    finally:
        for field in ("consumer_key", "mobile_number", "ucc", "mpin"):
            credentials.write({field: ""})


def test_a_malformed_code_is_rejected_before_reaching_kotak(unlocked):
    credentials.write({
        "consumer_key": "k", "mobile_number": "+919876543210",
        "ucc": "ABC12", "mpin": "1234",
    })
    try:
        for bad in ("12345", "1234567", "abcdef"):
            response = unlocked.post("/api/admin/broker/login", json={"totp": bad})
            assert response.status_code == 400, bad
            assert "six digits" in response.json()["detail"]
    finally:
        for field in ("consumer_key", "mobile_number", "ucc", "mpin"):
            credentials.write({field: ""})


# ---- a value that is set and still cannot work -----------------------
#
# Presence is not usability. A mobile number in a shape Kotak refuses and a
# TOTP secret that is not base32 both pass every check the page had, and then
# fail at the broker — the worst place to find out. The API says which field is
# wrong and why, in words that never quote the value.


def test_a_malformed_mobile_number_is_named(unlocked, monkeypatch):
    from livegraph.feed.config import KotakSettings

    monkeypatch.setattr(
        "livegraph.api.routes.admin.load_kotak_settings",
        lambda: KotakSettings(
            consumer_key="k", mobile_number="98765", ucc="ABC12", mpin="1234",
            totp_secret="JBSWY3DPEHPK3PXP",
        ),
    )
    fields = {f["name"]: f for f in unlocked.get("/api/admin/broker").json()["credentials"]}

    assert fields["mobile_number"]["problem"] == "not a ten-digit Indian mobile number"
    assert fields["ucc"]["problem"] is None
    #: The value itself must not travel, whatever is wrong with it.
    assert "98765" not in unlocked.get("/api/admin/broker").text


def test_a_usable_mobile_number_has_no_problem(unlocked, monkeypatch):
    from livegraph.feed.config import KotakSettings

    monkeypatch.setattr(
        "livegraph.api.routes.admin.load_kotak_settings",
        lambda: KotakSettings(
            consumer_key="k", mobile_number="+919876543210", ucc="ABC12", mpin="1234",
            totp_secret="123456",
        ),
    )
    fields = {f["name"]: f for f in unlocked.get("/api/admin/broker").json()["credentials"]}

    assert fields["mobile_number"]["problem"] is None
    #: Six digits is a code, not a base32 secret, and it will never derive one.
    assert fields["totp_secret"]["problem"] == "not a usable base32 secret"
