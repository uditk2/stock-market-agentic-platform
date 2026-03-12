from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from smap_service.api.routes import build_router
from smap_service.app_runtime import build_runtime
from smap_service.core.logging import configure_logging

configure_logging()
runtime = build_runtime()


@asynccontextmanager
async def lifespan(_: FastAPI):
    runtime.scheduler.start()
    try:
        yield
    finally:
        runtime.scheduler.stop()


app = FastAPI(title="SMAP Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(build_router(runtime))
