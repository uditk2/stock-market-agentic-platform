from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from smap_service.app_runtime import AppRuntime
from smap_service.db.job_history import JobRun
from smap_service.db.provider_credentials import (
    REQUIRED_CREDENTIAL_FIELDS,
    SUPPORTED_BROKER_PROVIDERS,
)


class BrokerSelectionRequest(BaseModel):
    provider: str = Field(min_length=1)
    credentials: dict[str, str]


def build_router(runtime: AppRuntime) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, object]:
        scheduler_runtime = runtime.scheduler.runtime()
        return {
            "status": "ok",
            "scheduler_running": scheduler_runtime.scheduler.running,
            "active_jobs": len(scheduler_runtime.scheduler.get_jobs()),
            "runtime_db_path": str(scheduler_runtime.history.db_path()),
            "last_scheduler_start_utc": scheduler_runtime.history.get_runtime_state("last_scheduler_start_utc"),
            "last_scheduler_stop_utc": scheduler_runtime.history.get_runtime_state("last_scheduler_stop_utc"),
            "market_connector": runtime.market_client_name,
            "llm_adapters": sorted(runtime.registry.llm_adapters.keys()),
            "news_providers": sorted(runtime.registry.news_providers.keys()),
            "strategy_modules": sorted(runtime.registry.strategy_modules.keys()),
        }

    @router.get("/jobs/history")
    def jobs_history(limit: int = 20) -> dict[str, object]:
        rows = runtime.scheduler.runtime().history.recent(limit=limit)
        return {
            "items": [
                {
                    "job_name": row.job_name,
                    "started_at": row.started_at.isoformat(),
                    "finished_at": row.finished_at.isoformat(),
                    "status": row.status,
                    "records_processed": row.records_processed,
                    "error": row.error,
                    "connector": row.connector,
                    "duration_ms": row.duration_ms,
                    "attribution": row.attribution or {},
                }
                for row in rows
            ]
        }

    @router.get("/providers/brokers")
    def providers_brokers() -> dict[str, Any]:
        selection = runtime.credentials.get_selection()
        return {
            "items": list(SUPPORTED_BROKER_PROVIDERS),
            "selected_provider": selection.provider,
            "has_credentials": selection.has_credentials,
            "updated_at": selection.updated_at,
        }

    @router.put("/providers/brokers/selection")
    def providers_selection(request: BrokerSelectionRequest) -> dict[str, Any]:
        missing = runtime.credentials.missing_required_fields(
            provider=request.provider,
            credentials=request.credentials,
        )
        if missing:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "missing_required_fields",
                    "provider": request.provider,
                    "missing_fields": missing,
                },
            )
        if request.provider == "kotak_neo":
            verification = _verify_kotak_credentials_before_save(runtime=runtime, credentials=request.credentials)
            if not verification.get("ok"):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "credential_verification_failed",
                        "provider": request.provider,
                        "verification": verification,
                    },
                )
        runtime.credentials.save_selection(
            provider=request.provider,
            credentials=request.credentials,
        )
        selection = runtime.credentials.get_selection()
        return {
            "ok": True,
            "selected_provider": selection.provider,
            "has_credentials": selection.has_credentials,
            "updated_at": selection.updated_at,
        }

    @router.get("/providers/brokers/schema/{provider}")
    def providers_schema(provider: str) -> dict[str, Any]:
        if provider not in SUPPORTED_BROKER_PROVIDERS:
            raise HTTPException(status_code=404, detail="unknown_provider")
        return {
            "provider": provider,
            "required_fields": list(REQUIRED_CREDENTIAL_FIELDS.get(provider, ())),
        }

    @router.get("/connectors/diagnostics")
    def connectors_diagnostics() -> dict[str, Any]:
        history_rows = runtime.scheduler.runtime().history.recent(limit=100)
        selection = runtime.credentials.get_selection()
        selected = selection.provider
        selected_credentials = runtime.credentials.get_credentials(selected) if selected else {}
        missing = (
            runtime.credentials.missing_required_fields(selected, selected_credentials or {})
            if selected
            else []
        )
        rss_provider = runtime.registry.news_providers.get("rss")
        rss_feed_count = len(getattr(rss_provider, "_feeds", [])) if rss_provider else 0
        market_last = _latest_for_job(history_rows, "ingest_market_bars")
        news_last = _latest_for_job(history_rows, "ingest_news")
        announcements_last = _latest_for_job(history_rows, "ingest_announcements")
        signals_last = _latest_for_job(history_rows, "compute_signals")
        verification: dict[str, Any] = {"ok": None, "code": "not_supported", "message": "verification not supported"}
        if hasattr(runtime.market_client, "verify_credentials"):
            try:
                verification = runtime.market_client.verify_credentials()
            except Exception as exc:  # pragma: no cover - runtime wrapper
                verification = {"ok": False, "code": "verify_exception", "message": str(exc)}
        return {
            "market": {
                "active_connector": runtime.market_client_name,
                "selected_provider": selected,
                "has_credentials": selection.has_credentials,
                "missing_required_fields": missing,
                "credential_verification": verification,
                "last_run": _run_to_summary(market_last),
            },
            "news": {
                "newsapi_key_configured": bool(os.getenv("SMAP_NEWSAPI_KEY")),
                "rss_feed_count": rss_feed_count,
                "announcements_adapter_enabled": "nse_announcements" in runtime.registry.news_providers,
                "last_news_run": _run_to_summary(news_last),
                "last_announcements_run": _run_to_summary(announcements_last),
            },
            "scheduler_observability": _build_observability(history_rows),
            "signals": {
                "last_run": _run_to_summary(signals_last),
            },
        }

    @router.get("/connectors/observability")
    def connectors_observability(limit: int = 100) -> dict[str, Any]:
        rows = runtime.scheduler.runtime().history.recent(limit=limit)
        return {
            "limit": limit,
            "summary": _build_observability(rows),
            "recent": [
                {
                    "job_name": row.job_name,
                    "status": row.status,
                    "connector": row.connector,
                    "records_processed": row.records_processed,
                    "duration_ms": row.duration_ms,
                    "finished_at": row.finished_at.isoformat(),
                    "attribution": row.attribution or {},
                }
                for row in rows
            ],
        }

    @router.get("/recommendations")
    def recommendations(query: str | None = None) -> dict[str, Any]:
        items = runtime.recommendations.list(query=query)
        return {
            "sort": "confidence_desc",
            "items": [
                {
                    "recommendation_id": item.recommendation_id,
                    "symbol": item.symbol,
                    "confidence": item.confidence,
                    "direction": item.direction,
                    "summary": item.summary,
                }
                for item in items
            ],
        }

    @router.get("/recommendations/{recommendation_id}")
    def recommendation_detail(recommendation_id: str) -> dict[str, Any]:
        item = runtime.recommendations.get(recommendation_id)
        if item is None:
            return {"ok": False, "error": "not_found"}
        payload = runtime.recommendations.to_dict(item)
        payload["ok"] = True
        return payload

    return router


def _latest_for_job(rows: list[JobRun], job_name: str) -> JobRun | None:
    for row in rows:
        if row.job_name == job_name:
            return row
    return None


def _run_to_summary(row: JobRun | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "status": row.status,
        "finished_at": row.finished_at.isoformat(),
        "records_processed": row.records_processed,
        "duration_ms": row.duration_ms,
        "connector": row.connector,
        "attribution": row.attribution or {},
        "error": row.error,
    }


def _build_observability(rows: list[JobRun]) -> dict[str, Any]:
    latest_by_job: dict[str, dict[str, Any]] = {}
    failures = 0
    for row in rows:
        if row.status != "success":
            failures += 1
        if row.job_name not in latest_by_job:
            latest_by_job[row.job_name] = {
                "status": row.status,
                "finished_at": row.finished_at.isoformat(),
                "duration_ms": row.duration_ms,
                "connector": row.connector,
                "records_processed": row.records_processed,
            }
    return {
        "total_runs_considered": len(rows),
        "failure_count": failures,
        "latest_by_job": latest_by_job,
    }


def _verify_kotak_credentials_before_save(runtime: AppRuntime, credentials: dict[str, str]) -> dict[str, Any]:
    verifier = getattr(runtime.market_client, "verify_credentials_payload", None)
    if callable(verifier):
        try:
            return verifier(credentials)
        except Exception as exc:  # pragma: no cover - runtime wrapper
            return {"ok": False, "code": "verify_exception", "message": str(exc)}
    return {"ok": False, "code": "verify_not_supported", "message": "Kotak verification is not available in runtime."}
