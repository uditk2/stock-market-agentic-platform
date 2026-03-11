from fastapi.testclient import TestClient

from smap_service.main import app


def test_health_route_shape() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "llm_adapters" in payload
