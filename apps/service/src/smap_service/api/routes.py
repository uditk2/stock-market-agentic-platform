from __future__ import annotations

from fastapi import APIRouter

from smap_service.app_runtime import AppRuntime


def build_router(runtime: AppRuntime) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, object]:
        scheduler_runtime = runtime.scheduler.runtime()
        return {
            "status": "ok",
            "scheduler_running": scheduler_runtime.scheduler.running,
            "active_jobs": len(scheduler_runtime.scheduler.get_jobs()),
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
                }
                for row in rows
            ]
        }

    return router
