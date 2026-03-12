from __future__ import annotations

from dataclasses import dataclass

from smap_service.core.config import (
    RuntimeConfig,
    load_config,
    resolve_credentials_key_path,
    resolve_db_path,
)
from smap_service.core.recommendations import RecommendationService
from smap_service.core.registry import PluginRegistry
from smap_service.db.provider_credentials import SQLiteProviderCredentialStore
from smap_service.plugins.llm.claude_adapter import ClaudeAdapter
from smap_service.plugins.llm.codex_adapter import CodexAdapter
from smap_service.plugins.market.kotak_client import KotakMarketFeedClient
from smap_service.plugins.news.announcement_provider import NSEAnnouncementProvider
from smap_service.plugins.news.newsapi_provider import NewsAPIProvider
from smap_service.plugins.news.rss_provider import RSSProvider
from smap_service.plugins.strategy.default_momentum import DefaultMomentumStrategy
from smap_service.scheduler.manager import SchedulerManager


@dataclass
class AppRuntime:
    config: RuntimeConfig
    registry: PluginRegistry
    scheduler: SchedulerManager
    credentials: SQLiteProviderCredentialStore
    recommendations: RecommendationService
    market_client_name: str


def build_runtime() -> AppRuntime:
    config = load_config()
    registry = PluginRegistry()

    registry.register_llm(CodexAdapter())
    registry.register_llm(ClaudeAdapter())

    registry.register_news_provider(NewsAPIProvider())
    registry.register_news_provider(RSSProvider())
    registry.register_news_provider(NSEAnnouncementProvider())

    registry.register_strategy(DefaultMomentumStrategy())

    db_path = resolve_db_path(config)
    credentials = SQLiteProviderCredentialStore(
        db_path=db_path,
        key_path=resolve_credentials_key_path(config),
    )
    market_client = KotakMarketFeedClient(credentials=credentials)
    scheduler = SchedulerManager(
        config=config,
        registry=registry,
        market_client=market_client,
    )
    recommendations = RecommendationService()
    return AppRuntime(
        config=config,
        registry=registry,
        scheduler=scheduler,
        credentials=credentials,
        recommendations=recommendations,
        market_client_name=market_client.name,
    )
