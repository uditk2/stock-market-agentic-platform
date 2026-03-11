from pydantic import BaseModel, Field


class SchedulerConfig(BaseModel):
    market_bars_interval_seconds: int = Field(default=60, ge=30)
    news_interval_seconds: int = Field(default=300, ge=60)
    announcements_interval_seconds: int = Field(default=300, ge=60)


class RuntimeConfig(BaseModel):
    env: str = "dev"
    scheduler: SchedulerConfig = SchedulerConfig()
    llm_adapter: str = "codex"
    news_providers: list[str] = ["newsapi", "rss"]
    strategy_modules: list[str] = ["default_momentum"]


def load_config() -> RuntimeConfig:
    # Placeholder for file/env-driven loading.
    return RuntimeConfig()
