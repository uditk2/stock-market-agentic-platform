"""Credentials entered through the admin page, stored outside the image.

`.env` remains the way to deploy a configured app: it is explicit, reviewable
and needs no running process. This store exists for the other case, where the
app is already running and somebody has to type a credential into it — after a
`docker compose up` on a fresh machine, or when a value was got wrong.

Two rules hold everywhere below:

- A stored value overrides the matching environment variable. The admin page is
  the more recent statement of intent, and a UI whose edits silently lose to an
  older `.env` is worse than one that has no edits at all. `sources()` reports
  which of the two a field came from so the page can say.
- Values go out to nobody. `read()` is for the process; the API layer answers
  with presence, never content. The file is written 0600 and lives in a
  directory the container mounts as a volume rather than bakes into the image.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Literal

from .paths import state_dir

logger = logging.getLogger(__name__)

Source = Literal["store", "env", "unset"]

#: Only these may be written. An admin page that can set arbitrary keys is an
#: admin page that can set LIVEGRAPH_SANDBOX_WORKER_DIR.
KOTAK_FIELDS: frozenset[str] = frozenset(
    {"consumer_key", "mobile_number", "ucc", "mpin", "totp_secret"}
)


def _path() -> Path:
    return state_dir() / "credentials.json"


def read() -> dict[str, str]:
    """Stored Kotak credentials, or an empty mapping.

    A corrupt file is reported and treated as empty rather than raised: the
    store is a convenience, and failing startup over it would take down an app
    that `.env` alone could have run.
    """
    path = _path()
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Ignoring unreadable credential store at %s: %s", path, exc)
        return {}

    kotak = loaded.get("kotak") if isinstance(loaded, dict) else None
    if not isinstance(kotak, dict):
        return {}
    return {
        name: value
        for name, value in kotak.items()
        if name in KOTAK_FIELDS and isinstance(value, str) and value.strip()
    }


def write(values: dict[str, str]) -> list[str]:
    """Merge `values` into the store. Returns the field names actually changed.

    A blank value clears the field rather than storing an empty string, so the
    page has a way to hand a field back to `.env`. Unknown names are dropped,
    not rejected: the caller has already validated, and this is the last guard.
    """
    current = read()
    updated = dict(current)
    changed: list[str] = []

    for name, value in values.items():
        if name not in KOTAK_FIELDS:
            continue
        cleaned = value.strip()
        if cleaned:
            if current.get(name) != cleaned:
                changed.append(name)
            updated[name] = cleaned
        elif name in updated:
            changed.append(name)
            del updated[name]

    if changed:
        _write_atomically({"kotak": updated})
    return changed


def sources(resolved: dict[str, str]) -> dict[str, Source]:
    """Where each field's value came from, for the admin page to show.

    `resolved` is the settings object's own view, which already has the store
    layered over `.env`. Deducing "env" from `os.environ` instead would be
    wrong: pydantic-settings reads `.env` off disk without exporting it, so a
    fully configured deployment would report every field as unset.
    """
    stored = read()
    return {
        name: (
            "store"
            if name in stored
            else "env"
            if (resolved.get(name) or "").strip()
            else "unset"
        )
        for name in sorted(KOTAK_FIELDS)
    }


def _write_atomically(payload: dict[str, dict[str, str]]) -> None:
    """Write 0600, and never leave a half-written file behind.

    The mode is set on the temporary file before the rename, so the credentials
    are never briefly world-readable under their final name.
    """
    directory = state_dir()
    handle, temporary = tempfile.mkstemp(dir=directory, prefix=".credentials-")
    try:
        with os.fdopen(handle, "w") as file:
            json.dump(payload, file, indent=2, sort_keys=True)
        os.chmod(temporary, 0o600)
        os.replace(temporary, _path())
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
