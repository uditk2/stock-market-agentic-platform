"""Serve the exported UI from the backend.

The UI is a static export, so the backend hosts it directly and the whole app
is one process on one port. Mounted last so it never shadows /api or /ws, and
absent silently when the UI has not been built.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..paths import ui_dir as resolve_ui_dir

logger = logging.getLogger(__name__)

def mount_ui(app: FastAPI, ui_dir: Path | None = None) -> bool:
    ui_dir = ui_dir or resolve_ui_dir()
    if not (ui_dir / "index.html").exists():
        logger.warning(
            "UI not built at %s; API is still served. Run `npm run build` in web/.", ui_dir
        )
        return False

    app.mount("/_next", StaticFiles(directory=ui_dir / "_next"), name="next-assets")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(ui_dir / "index.html")

    @app.get("/{path:path}", include_in_schema=False)
    def asset(path: str) -> FileResponse:
        """Serve a real file if it exists, else the SPA shell."""
        candidate = (ui_dir / path).resolve()
        #: Never serve outside the export directory, whatever the path contains.
        if candidate.is_file() and candidate.is_relative_to(ui_dir.resolve()):
            return FileResponse(candidate)
        return FileResponse(ui_dir / "index.html")

    logger.info("serving UI from %s", ui_dir)
    return True
