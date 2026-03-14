from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


class SchedulerConfig(BaseModel):
    market_bars_interval_seconds: int = Field(default=60, ge=30)
    news_interval_seconds: int = Field(default=300, ge=60)
    announcements_interval_seconds: int = Field(default=300, ge=60)
    signals_interval_seconds: int = Field(default=120, ge=60)


class RuntimeConfig(BaseModel):
    env: str = "dev"
    scheduler: SchedulerConfig = SchedulerConfig()
    llm_adapter: str = "codex"
    news_providers: list[str] = ["newsapi", "rss"]
    strategy_modules: list[str] = ["default_momentum"]
    db_path: str | None = None
    history_retention_days: int | None = None
    credentials_key_path: str | None = None


def load_config() -> RuntimeConfig:
    db_path = os.getenv("SMAP_DB_PATH")
    retention_raw = os.getenv("SMAP_HISTORY_RETENTION_DAYS")
    retention_days: int | None = None
    if retention_raw:
        retention_days = int(retention_raw)
    credentials_key_path = os.getenv("SMAP_CREDENTIALS_KEY_PATH")
    return RuntimeConfig(
        db_path=db_path,
        history_retention_days=retention_days,
        credentials_key_path=credentials_key_path,
    )


def default_app_data_dir(app_name: str = "smap-service") -> Path:
    if os.name == "nt":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif os.uname().sysname == "Darwin":  # type: ignore[attr-defined]
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / app_name


def resolve_db_path(config: RuntimeConfig) -> Path:
    if config.db_path:
        return Path(config.db_path).expanduser().resolve()
    return default_app_data_dir() / "runtime.sqlite3"


def resolve_credentials_key_path(config: RuntimeConfig) -> Path:
    if config.credentials_key_path:
        return Path(config.credentials_key_path).expanduser().resolve()
    return default_app_data_dir() / "credentials.key"
