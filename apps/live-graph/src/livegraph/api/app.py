"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import ws
from .logging_filters import install as quiet_polling_logs
from .routes import admin, analyst, graph, market, news, scan, scratchpad
from .static_ui import mount_ui
from .state import AppState

logger = logging.getLogger(__name__)

#: The dev UI picks whichever port is free, so match any localhost origin
#: rather than pinning one. The API binds locally and is not public.
ALLOWED_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"


def create_app(feed=None) -> FastAPI:
    """`feed` is a seam for tests; in normal use the feed comes from .env."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state = AppState(feed=feed)
        app.state.livegraph = state
        state.start()
        logger.info("feed mode=%s (%s)", state.feed_mode, state.feed_detail)
        try:
            yield
        finally:
            state.stop()

    #: Before anything serves: several hundred identical 200s a minute buries
    #: the lines that matter, a dropped feed socket among them.
    quiet_polling_logs()

    app = FastAPI(title="livegraph", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=ALLOWED_ORIGIN_REGEX,
        allow_methods=["*"],
        allow_headers=["*"],
        #: The admin session is a cookie, and the dev UI is a different origin
        #: from the API. Without this the login succeeds and is then forgotten.
        allow_credentials=True,
    )
    for router in (scan.router, admin.router, admin.session_router, market.router, graph.router, news.router, analyst.router, scratchpad.router, ws.router):
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



app = create_app()
