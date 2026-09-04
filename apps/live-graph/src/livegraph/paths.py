"""Locate the graph data and the built UI.

Resolving these relative to `__file__` only works from a source checkout; once
the package is installed into site-packages the parent walk lands outside the
project. Each location is therefore an explicit environment variable first,
with the source layout and the container layout as fallbacks.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

#: Source checkout: src/livegraph/paths.py -> repo root.
_SOURCE_ROOT = Path(__file__).resolve().parents[2]
_CONTAINER_ROOT = Path("/app")


def data_dir() -> Path:
    return _resolve(
        env_var="LIVEGRAPH_DATA_DIR",
        candidates=(_SOURCE_ROOT / "data", _CONTAINER_ROOT / "data", Path.cwd() / "data"),
        marker="stock_graph.json",
        label="graph data",
    )


def ui_dir() -> Path:
    return _resolve(
        env_var="LIVEGRAPH_UI_DIR",
        candidates=(_SOURCE_ROOT / "web" / "out", _CONTAINER_ROOT / "web" / "out"),
        marker="index.html",
        label="built UI",
    )


def sandbox_worker_dir() -> Path:
    return _resolve(
        env_var="LIVEGRAPH_SANDBOX_WORKER_DIR",
        candidates=(
            Path(__file__).resolve().parent / "scratchpad" / "sandbox" / "worker",
            _CONTAINER_ROOT / "sandbox-worker",
        ),
        marker="sandbox_worker.mjs",
        label="sandbox worker",
    )


def _resolve(env_var: str, candidates: tuple[Path, ...], marker: str, label: str) -> Path:
    """First candidate containing `marker` wins; the env var always wins outright."""
    override = os.environ.get(env_var)
    if override:
        return Path(override)
    for candidate in candidates:
        if (candidate / marker).exists():
            return candidate
    logger.warning(
        "%s not found; looked for %s in %s. Set %s to override.",
        label, marker, ", ".join(str(c) for c in candidates), env_var,
    )
    return candidates[0]
