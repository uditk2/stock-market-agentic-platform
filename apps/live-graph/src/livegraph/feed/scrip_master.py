"""Turn what `NeoAPI.scrip_master()` returns into rows.

It does not return rows. Given an exchange segment it returns a *URL string*
pointing at a CSV — see `neo_api_client/api/scrip_master_api.py`, which picks
one entry out of `filesPaths` and hands back the path. Passing that straight to
a row parser iterates the characters of a URL, which is how this surfaced:
`'str' object has no attribute 'get'`.

The SDK also signals failure by returning a dict rather than raising, so three
shapes have to be told apart: a URL to fetch, an error to report, and a list of
rows from a version that already did the work.
"""

from __future__ import annotations

import csv
import io
import logging
import urllib.request

logger = logging.getLogger(__name__)

#: The file is a few MB of text; anything slower than this is a hung download
#: rather than a large one, and it blocks app startup.
DEFAULT_TIMEOUT = 60.0


class ScripMasterError(RuntimeError):
    pass


def load_scrip_master(result, timeout: float = DEFAULT_TIMEOUT) -> list[dict[str, str]]:
    """Rows from whatever `scrip_master()` handed back.

    `result` is passed through rather than fetched here so the caller keeps its
    own session, and so a test can hand over rows directly.
    """
    if isinstance(result, dict):
        raise ScripMasterError(_error_text(result))

    if isinstance(result, str):
        return fetch_csv(result, timeout=timeout)

    if isinstance(result, list):
        #: Already rows. Guard against a list of strings, which would fail far
        #: later inside the parser with nothing pointing back to here.
        if result and not isinstance(result[0], dict):
            raise ScripMasterError(
                f"expected rows or a URL, got a list of {type(result[0]).__name__}"
            )
        return result

    raise ScripMasterError(f"unexpected scrip_master result: {type(result).__name__}")


def fetch_csv(url: str, timeout: float = DEFAULT_TIMEOUT) -> list[dict[str, str]]:
    """Download the scrip master CSV and read it into dicts."""
    if not url.lower().startswith(("http://", "https://")):
        raise ScripMasterError(f"scrip_master returned something that is not a URL: {url[:80]}")

    logger.info("downloading scrip master from %s", url)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001 - URLError, timeouts and decode all read alike
        raise ScripMasterError(f"could not download the scrip master: {exc}") from exc

    rows = list(csv.DictReader(io.StringIO(body)))
    if not rows:
        raise ScripMasterError("the scrip master CSV was empty")

    logger.info("scrip master: %d rows, columns %s", len(rows), ", ".join(rows[0]))
    return rows


def _error_text(payload: dict) -> str:
    """The SDK spells its error key three different ways."""
    for key in ("Error Message", "Error", "error", "message"):
        if value := payload.get(key):
            return str(value)
    return str(payload)
