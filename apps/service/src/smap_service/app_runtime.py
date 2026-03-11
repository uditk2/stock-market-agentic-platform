from __future__ import annotations

from dataclasses import dataclass

from smap_service.core.config import RuntimeConfig, load_config
from smap_service.core.registry import PluginRegistry
from smap_service.plugins.llm.claude_adapter import ClaudeAdapter
from smap_service.plugins.llm.codex_adapter import CodexAdapter
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


def build_runtime() -> AppRuntime:
    config = load_config()
    registry = PluginRegistry()

    registry.register_llm(CodexAdapter())
    registry.register_llm(ClaudeAdapter())

    registry.register_news_provider(NewsAPIProvider())
    registry.register_news_provider(RSSProvider())
    registry.register_news_provider(NSEAnnouncementProvider())

    registry.register_strategy(DefaultMomentumStrategy())

    scheduler = SchedulerManager(config=config, registry=registry)
    return AppRuntime(config=config, registry=registry, scheduler=scheduler)
