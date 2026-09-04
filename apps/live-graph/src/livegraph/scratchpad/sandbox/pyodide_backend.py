"""Run generated strategy code in an in-process WASM sandbox.

A single long-lived Node process hosts Pyodide with numpy, pandas, scipy and
matplotlib preloaded. Strategies execute inside the WASM boundary, so they
cannot reach the host filesystem, the host environment (where the Kotak and
CLIProxy credentials live), the network, or a subprocess.

The worker is warm between runs, which keeps a run in the tens of milliseconds
instead of paying the multi-second Pyodide boot each time. A run that overruns
is enforced by killing the worker outright; the next run respawns it.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path

from ...paths import sandbox_worker_dir
from ..models import MarketSnapshot, RunStatus, StrategyRun
from ..validator import validate

logger = logging.getLogger(__name__)

WORKER_DIR = sandbox_worker_dir()
WORKER_SCRIPT = WORKER_DIR / "sandbox_worker.mjs"

DEFAULT_TIMEOUT_SECONDS = 30
#: Pyodide has to boot and load four wheels before the first run.
STARTUP_TIMEOUT_SECONDS = 180


class SandboxUnavailable(RuntimeError):
    pass


class PyodideSandbox:
    name = "pyodide"

    def __init__(
        self,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        node_binary: str | None = None,
    ):
        self._timeout = timeout_seconds
        self._node = node_binary or os.environ.get("LIVEGRAPH_NODE_BIN") or "node"
        self._process: subprocess.Popen | None = None
        self._replies: queue.Queue = queue.Queue()
        self._reader: threading.Thread | None = None
        #: One worker, so runs are serialised. This is a single-user local tool.
        self._lock = threading.Lock()
        self._next_id = 0

    # ---- availability ------------------------------------------------

    def is_available(self) -> bool:
        if shutil.which(self._node) is None:
            return False
        if not WORKER_SCRIPT.exists():
            return False
        return (WORKER_DIR / "node_modules" / "pyodide").exists()

    def unavailable_reason(self) -> str:
        if shutil.which(self._node) is None:
            return f"node binary '{self._node}' not found"
        if not WORKER_SCRIPT.exists():
            return f"sandbox worker missing at {WORKER_SCRIPT}"
        if not (WORKER_DIR / "node_modules" / "pyodide").exists():
            return f"pyodide not installed; run `npm install` in {WORKER_DIR}"
        return ""

    # ---- lifecycle ---------------------------------------------------

    def start(self) -> None:
        """Boot the worker and block until Pyodide is ready."""
        with self._lock:
            self._ensure_worker()

    def stop(self) -> None:
        with self._lock:
            self._kill_worker()

    def _ensure_worker(self) -> None:
        if self._process is not None and self._process.poll() is None:
            return
        if not self.is_available():
            raise SandboxUnavailable(self.unavailable_reason())

        logger.info("starting Pyodide sandbox worker")
        self._process = subprocess.Popen(
            [self._node, str(WORKER_SCRIPT)],
            cwd=WORKER_DIR,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._replies = queue.Queue()
        self._reader = threading.Thread(
            target=self._read_replies, args=(self._process,), daemon=True
        )
        self._reader.start()
        self._await_ready()

    def _await_ready(self) -> None:
        try:
            message = self._replies.get(timeout=STARTUP_TIMEOUT_SECONDS)
        except queue.Empty:
            self._kill_worker()
            raise SandboxUnavailable(
                f"sandbox worker did not become ready within {STARTUP_TIMEOUT_SECONDS}s"
            ) from None
        if message.get("type") != "ready":
            self._kill_worker()
            raise SandboxUnavailable(f"sandbox worker failed: {message.get('error')}")
        logger.info("Pyodide sandbox ready (%s)", ", ".join(message.get("packages", [])))

    def _read_replies(self, process: subprocess.Popen) -> None:
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                self._replies.put(json.loads(line))
            except json.JSONDecodeError:
                logger.debug("sandbox worker noise: %s", line[:200])

    def _kill_worker(self) -> None:
        process, self._process = self._process, None
        if process is None:
            return
        process.kill()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - kill should suffice
            logger.error("sandbox worker did not die after kill")

    # ---- execution ---------------------------------------------------

    def run(self, code: str, snapshot: MarketSnapshot) -> StrategyRun:
        verdict = validate(code)
        if not verdict.ok:
            return StrategyRun(status=RunStatus.REJECTED, error=verdict.message)

        with self._lock:
            try:
                self._ensure_worker()
            except SandboxUnavailable as exc:
                return StrategyRun(status=RunStatus.ERROR, error=str(exc))
            return self._dispatch(code, snapshot)

    def _dispatch(self, code: str, snapshot: MarketSnapshot) -> StrategyRun:
        self._next_id += 1
        request = {"id": self._next_id, "code": code, "snapshot": snapshot.to_payload()}
        started = time.monotonic()
        try:
            self._process.stdin.write(json.dumps(request) + "\n")
            self._process.stdin.flush()
        except (BrokenPipeError, ValueError, AttributeError):
            self._kill_worker()
            return StrategyRun(status=RunStatus.ERROR, error="sandbox worker died mid-request")

        try:
            message = self._replies.get(timeout=self._timeout)
        except queue.Empty:
            #: WASM runs on the worker's own thread with no interrupt hook, so a
            #: runaway loop can only be stopped by killing the process.
            self._kill_worker()
            return StrategyRun(
                status=RunStatus.TIMEOUT,
                error=f"strategy exceeded {self._timeout}s and the sandbox was restarted",
                duration_ms=_elapsed_ms(started),
            )
        return _to_result(message.get("payload", {}), _elapsed_ms(started))


def _to_result(payload: dict, duration_ms: int) -> StrategyRun:
    if "error" in payload:
        return StrategyRun(
            status=RunStatus.ERROR,
            error=str(payload["error"])[:2000],
            traceback=str(payload.get("traceback", ""))[:3000],
            stdout=str(payload.get("stdout", ""))[:4000],
            duration_ms=duration_ms,
        )
    return StrategyRun(
        status=RunStatus.OK,
        output=payload.get("output"),
        figures=tuple(payload.get("figures") or ()),
        stdout=str(payload.get("stdout", ""))[:4000],
        duration_ms=duration_ms,
    )


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)
