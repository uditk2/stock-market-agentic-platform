from fastapi.testclient import TestClient

from smap_service.main import app, runtime


def test_health_route_shape() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "llm_adapters" in payload
    assert "runtime_db_path" in payload
    assert payload["market_connector"] == "kotak_neo"


def test_recommendations_and_provider_routes_shape() -> None:
    client = TestClient(app)

    providers = client.get("/providers/brokers")
    assert providers.status_code == 200
    providers_payload = providers.json()
    assert "items" in providers_payload
    assert "kotak_neo" in providers_payload["items"]

    recs = client.get("/recommendations")
    assert recs.status_code == 200
    rec_payload = recs.json()
    assert rec_payload["sort"] == "confidence_desc"
    assert len(rec_payload["items"]) >= 1

    schema = client.get("/providers/brokers/schema/kotak_neo")
    assert schema.status_code == 200
    assert "access_token" in schema.json()["required_fields"]

    diagnostics = client.get("/connectors/diagnostics")
    assert diagnostics.status_code == 200
    diag_payload = diagnostics.json()
    assert "market" in diag_payload
    assert "news" in diag_payload
    assert "scheduler_observability" in diag_payload
    assert "failure_count" in diag_payload["scheduler_observability"]

    observability = client.get("/connectors/observability")
    assert observability.status_code == 200
    observability_payload = observability.json()
    assert "summary" in observability_payload
    assert "recent" in observability_payload


def test_provider_selection_validation_rejects_missing_required_fields() -> None:
    client = TestClient(app)
    response = client.put(
        "/providers/brokers/selection",
        json={"provider": "kotak_neo", "credentials": {}},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["detail"]["error"] == "missing_required_fields"


def test_provider_selection_rejects_kotak_credentials_when_live_verification_fails(monkeypatch) -> None:
    client = TestClient(app)

    def _fail(_: dict[str, str]) -> dict[str, object]:
        return {"ok": False, "code": "verify_failed", "message": "token rejected"}

    monkeypatch.setattr(runtime.market_client, "verify_credentials_payload", _fail)

    response = client.put(
        "/providers/brokers/selection",
        json={"provider": "kotak_neo", "credentials": {"access_token": "bad-token"}},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["detail"]["error"] == "credential_verification_failed"
    assert payload["detail"]["verification"]["code"] == "verify_failed"


def test_provider_selection_saves_kotak_credentials_when_live_verification_passes(monkeypatch) -> None:
    client = TestClient(app)

    def _ok(_: dict[str, str]) -> dict[str, object]:
        return {"ok": True, "code": "verified", "message": "ok"}

    monkeypatch.setattr(runtime.market_client, "verify_credentials_payload", _ok)

    response = client.put(
        "/providers/brokers/selection",
        json={"provider": "kotak_neo", "credentials": {"access_token": "good-token"}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["selected_provider"] == "kotak_neo"
