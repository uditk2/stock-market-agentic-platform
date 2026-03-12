from fastapi.testclient import TestClient

from smap_service.main import app, runtime


def test_scheduler_runs_are_attributed_in_observability_payload() -> None:
    runtime.scheduler._run_market_job()  # type: ignore[attr-defined]
    runtime.scheduler._run_news_job()  # type: ignore[attr-defined]
    runtime.scheduler._run_announcement_job()  # type: ignore[attr-defined]

    client = TestClient(app)

    history = client.get("/jobs/history", params={"limit": 10})
    assert history.status_code == 200
    history_payload = history.json()
    assert len(history_payload["items"]) >= 1
    assert "connector" in history_payload["items"][0]
    assert "duration_ms" in history_payload["items"][0]
    assert "attribution" in history_payload["items"][0]

    diagnostics = client.get("/connectors/diagnostics")
    assert diagnostics.status_code == 200
    diagnostics_payload = diagnostics.json()
    assert diagnostics_payload["market"]["last_run"] is not None
    assert diagnostics_payload["news"]["last_news_run"] is not None

    observability = client.get("/connectors/observability", params={"limit": 20})
    assert observability.status_code == 200
    observability_payload = observability.json()
    assert observability_payload["summary"]["total_runs_considered"] >= 1
    assert "latest_by_job" in observability_payload["summary"]
