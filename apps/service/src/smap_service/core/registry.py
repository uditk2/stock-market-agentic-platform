from __future__ import annotations

from dataclasses import dataclass, field

from smap_service.core.interfaces import LLMAdapter, NewsProvider, StrategyModule


@dataclass
class PluginRegistry:
    llm_adapters: dict[str, LLMAdapter] = field(default_factory=dict)
    news_providers: dict[str, NewsProvider] = field(default_factory=dict)
    strategy_modules: dict[str, StrategyModule] = field(default_factory=dict)

    def register_llm(self, adapter: LLMAdapter) -> None:
        self.llm_adapters[adapter.name] = adapter

    def register_news_provider(self, provider: NewsProvider) -> None:
        self.news_providers[provider.name] = provider

    def register_strategy(self, strategy: StrategyModule) -> None:
        self.strategy_modules[strategy.name] = strategy
