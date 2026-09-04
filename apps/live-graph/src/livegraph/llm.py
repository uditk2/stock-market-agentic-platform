"""Model access via CLIProxyAPI.

CLIProxyAPI fronts your Claude Code / Codex / Gemini OAuth subscriptions with
an OpenAI-compatible surface, so every agent in this app talks OpenAI protocol
to a local base URL and no provider API key is involved.

Shared by `agent` and `scratchpad` so the endpoint is configured in one place.

Backend caveat, measured against a live proxy: the Claude backends replace the
system prompt with Claude Code's own, so a system-only instruction reaches the
GPT/Codex backend but is silently dropped for Claude. Anything that must hold
on every backend belongs in the first user message, not in `system_prompt`.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cliproxy_base_url: str = "http://localhost:8317/v1"
    cliproxy_api_key: str = ""
    #: Model for graph reasoning and narration.
    livegraph_agent_model: str = "claude-sonnet-5"
    #: Model for writing strategy code; a coding-strong model pays off here.
    livegraph_coder_model: str = "claude-opus-5"

    @property
    def is_configured(self) -> bool:
        return bool(self.cliproxy_base_url and self.cliproxy_api_key)


@lru_cache(maxsize=1)
def get_llm_settings() -> LLMSettings:
    return LLMSettings()


def build_model(model_name: str, settings: LLMSettings | None = None):
    """An OpenAI-protocol model pointed at CLIProxyAPI."""
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    resolved = settings or get_llm_settings()
    provider = OpenAIProvider(
        base_url=resolved.cliproxy_base_url,
        #: CLIProxyAPI rejects an empty key outright, so send a placeholder when
        #: the proxy was started without `api-keys` configured.
        api_key=resolved.cliproxy_api_key or "cliproxy-local",
    )
    return OpenAIChatModel(model_name, provider=provider)


def build_analyst_model(settings: LLMSettings | None = None):
    resolved = settings or get_llm_settings()
    return build_model(resolved.livegraph_agent_model, resolved)


def build_coder_model(settings: LLMSettings | None = None):
    resolved = settings or get_llm_settings()
    return build_model(resolved.livegraph_coder_model, resolved)
