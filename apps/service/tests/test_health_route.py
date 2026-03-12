from fastapi.testclient import TestClient

from smap_service.main import app


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
