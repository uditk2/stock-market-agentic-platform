"""Keep the access log readable while the UI polls.

The dashboard re-reads its panels every second or two, so a running app writes
several hundred identical 200 lines a minute. That is not information, and it
is actively harmful: it pushed the line that mattered — a dropped Kotak socket —
off the top of the terminal while someone was watching for exactly that.

Only successful polls of the known polling routes are dropped. Anything that
failed, and anything to a route not listed here, still gets a line: a 500 on a
polling route is the one thing you would most want to see.
"""

from __future__ import annotations

import logging

#: Routes the dashboard re-reads on a timer. Prefixes, because several carry
#: query strings (`/api/scan/movers?per_side=10`).
POLLED_PREFIXES: tuple[str, ...] = (
    "/api/market/status",
    "/api/market/quotes",
    "/api/scan/movers",
    "/api/admin/broker",
    "/api/admin/session",
    "/api/admin/models",
    "/api/health",
    "/api/news",
)


class QuietPolling(logging.Filter):
    """Drop successful GETs to polling routes; keep everything else."""

    def filter(self, record: logging.LogRecord) -> bool:
        #: uvicorn.access formats with args (client, method, path, version, status).
        args = record.args
        if not isinstance(args, tuple) or len(args) < 5:
            return True
        _, method, path, _, status = args[:5]
        if method != "GET":
            return True
        try:
            failed = int(status) >= 400
        except (TypeError, ValueError):
            return True
        if failed:
            return True
        return not str(path).startswith(POLLED_PREFIXES)


def install() -> None:
    """Attach the filter to uvicorn's access logger.

    Done here rather than through a logging config file so it applies however
    the app is started — `uvicorn` on the command line, the container's CMD, or
    a TestClient — none of which share a config.
    """
    logging.getLogger("uvicorn.access").addFilter(QuietPolling())
