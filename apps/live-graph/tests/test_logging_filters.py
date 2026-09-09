"""The access log has to stay readable while the dashboard polls.

Several hundred identical 200 lines a minute is not information, and it hid a
dropped Kotak socket from someone who was watching the log for exactly that.
What must never be dropped is a failure, because a 500 on a polling route is
the thing most worth seeing.
"""

import logging

from livegraph.api.logging_filters import QuietPolling


def record(method: str, path: str, status: int) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.access", level=logging.INFO, pathname="", lineno=0,
        msg='%s - "%s %s HTTP/%s" %d', exc_info=None,
        args=("127.0.0.1:1", method, path, "1.1", status),
    )


def test_successful_polls_are_dropped():
    quiet = QuietPolling()
    for path in ("/api/market/status", "/api/scan/movers?per_side=10", "/api/health"):
        assert not quiet.filter(record("GET", path, 200)), path


def test_a_failure_on_a_polled_route_is_always_kept():
    quiet = QuietPolling()
    assert quiet.filter(record("GET", "/api/market/status", 500))
    assert quiet.filter(record("GET", "/api/scan/movers?per_side=10", 401))


def test_writes_are_kept_even_on_a_polled_prefix():
    """A login POSTs to /api/admin/broker/login, which shares the prefix."""
    assert QuietPolling().filter(record("POST", "/api/admin/broker/login", 200))


def test_routes_that_are_not_polled_are_kept():
    assert QuietPolling().filter(record("GET", "/api/graph", 200))


def test_a_record_that_is_not_an_access_line_passes_through():
    """Other loggers share the handler; this must not eat their messages."""
    other = logging.LogRecord(
        name="uvicorn.error", level=logging.WARNING, pathname="", lineno=0,
        msg="Kotak socket closed", args=(), exc_info=None,
    )
    assert QuietPolling().filter(other)
