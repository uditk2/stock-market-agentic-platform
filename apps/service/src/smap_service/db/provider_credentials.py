from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from cryptography.fernet import Fernet

SUPPORTED_BROKER_PROVIDERS = ("kotak_neo", "upstox", "kite")
REQUIRED_CREDENTIAL_FIELDS: dict[str, tuple[str, ...]] = {
    "kotak_neo": ("access_token",),
    "upstox": ("api_key", "api_secret"),
    "kite": ("api_key", "access_token"),
}


@dataclass
class ProviderSelection:
    provider: str | None
    has_credentials: bool
    updated_at: str | None


class SQLiteProviderCredentialStore:
    def __init__(self, db_path: Path, key_path: Path):
        self._db_path = db_path
        self._key_path = key_path
        self._lock = Lock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(self._load_or_create_key())
        self._init_schema()

    def save_selection(self, provider: str, credentials: dict[str, str]) -> None:
        if provider not in SUPPORTED_BROKER_PROVIDERS:
            raise ValueError(f"unsupported provider: {provider}")
        ciphertext = self._fernet.encrypt(
            json.dumps(credentials, sort_keys=True).encode("utf-8")
        ).decode("utf-8")
        updated_at = now_utc().isoformat()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO provider_credentials (provider, credential_blob, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(provider) DO UPDATE SET
                    credential_blob = excluded.credential_blob,
                    updated_at = excluded.updated_at
                """,
                (provider, ciphertext, updated_at),
            )
            conn.execute(
                """
                INSERT INTO provider_selection (id, provider, updated_at)
                VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    provider = excluded.provider,
                    updated_at = excluded.updated_at
                """,
                (provider, updated_at),
            )
            conn.commit()

    def missing_required_fields(self, provider: str, credentials: dict[str, str]) -> list[str]:
        required = REQUIRED_CREDENTIAL_FIELDS.get(provider, ())
        missing: list[str] = []
        for field in required:
            value = credentials.get(field, "")
            if not str(value).strip():
                missing.append(field)
        return missing

    def get_selection(self) -> ProviderSelection:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT provider, updated_at FROM provider_selection WHERE id = 1"
            ).fetchone()
            if row is None:
                return ProviderSelection(provider=None, has_credentials=False, updated_at=None)
            provider = row[0]
            cred = conn.execute(
                "SELECT 1 FROM provider_credentials WHERE provider = ? LIMIT 1",
                (provider,),
            ).fetchone()
        return ProviderSelection(
            provider=provider,
            has_credentials=cred is not None,
            updated_at=row[1],
        )

    def get_credentials(self, provider: str) -> dict[str, str] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT credential_blob FROM provider_credentials WHERE provider = ?",
                (provider,),
            ).fetchone()
        if row is None:
            return None
        plaintext = self._fernet.decrypt(row[0].encode("utf-8")).decode("utf-8")
        loaded = json.loads(plaintext)
        if not isinstance(loaded, dict):
            return None
        return {str(k): str(v) for k, v in loaded.items()}

    def db_path(self) -> Path:
        return self._db_path

    def _load_or_create_key(self) -> bytes:
        self._key_path.parent.mkdir(parents=True, exist_ok=True)
        if self._key_path.exists():
            return self._key_path.read_bytes()
        key = Fernet.generate_key()
        self._key_path.write_bytes(key)
        try:
            self._key_path.chmod(0o600)
        except OSError:
            pass
        return key

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS provider_credentials (
                    provider TEXT PRIMARY KEY,
                    credential_blob TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS provider_selection (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    provider TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()


def now_utc() -> datetime:
    return datetime.now(UTC)
