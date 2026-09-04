"""FastAPI application factory."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import ws
from .routes import admin, analyst, graph, market, news, scan, scratchpad
from .static_ui import mount_ui
from .state import AppState

logger = logging.getLogger(__name__)

#: The dev UI picks whichever port is free, so match any localhost origin
#: rather than pinning one. The API binds locally and is not public.
ALLOWED_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"


def create_app(simulate: bool | None = None) -> FastAPI:
    resolved = _resolve_simulate(simulate)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state = AppState(simulate=resolved)
        app.state.livegraph = state
        state.start()
        logger.info("feed mode=%s (%s)", state.feed_mode, state.feed_detail)
        try:
            yield
        finally:
            state.stop()

    app = FastAPI(title="livegraph", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=ALLOWED_ORIGIN_REGEX,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for router in (scan.router, admin.router, market.router, graph.router, news.router, analyst.router, scratchpad.router, ws.router):
        app.include_router(router)

    @app.get("/api/health")
    def health() -> dict:
        state: AppState = app.state.livegraph
        return {
            "ok": True,
            "feed": asdict(state.status()),
            "graph": {"nodes": state.repo.node_count, "edges": state.repo.edge_count},
            "sandbox": {
                "runtime": state.sandbox.name,
                "available": state.sandbox.is_available(),
            },
        }

    #: Mounted last: the catch-all route would otherwise shadow /api and /ws.
    mount_ui(app)
    return app


def _resolve_simulate(simulate: bool | None) -> bool:
    if simulate is not None:
        return simulate
    return os.environ.get("LIVEGRAPH_SIMULATE", "").lower() in {"1", "true", "yes"}


app = create_app()
