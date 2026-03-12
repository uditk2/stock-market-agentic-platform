from smap_service.app_runtime import build_runtime


def test_runtime_registers_plugins() -> None:
    runtime = build_runtime()
    assert "codex" in runtime.registry.llm_adapters
    assert "claude" in runtime.registry.llm_adapters
    assert "newsapi" in runtime.registry.news_providers
    assert "rss" in runtime.registry.news_providers
    assert "default_momentum" in runtime.registry.strategy_modules
    assert runtime.market_client_name == "kotak_neo"
