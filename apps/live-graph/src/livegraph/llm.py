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

import json
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ProxyProbe:
    """What the admin page needs to know about the proxy, and nothing more."""

    base_url: str
    reachable: bool
    key_accepted: bool
    models: tuple[str, ...]
    detail: str

    def resolves(self, model_name: str) -> bool:
        #: An unreachable proxy cannot say a model is missing, only that it is
        #: unknown. Reporting "not available" then would blame the wrong thing.
        return model_name in self.models


def probe_cliproxy(settings: LLMSettings | None = None, timeout: float = 4.0) -> ProxyProbe:
    """Ask the proxy for its model list, and interpret the failure if it fails.

    Three states a page has to tell apart: nothing is listening, something is
    listening but rejects the key, and it works. `/v1/models` distinguishes all
    three in one call, which is why it is the probe rather than a chat request.
    """
    import urllib.error
    import urllib.request

    resolved = settings or get_llm_settings()
    base = resolved.cliproxy_base_url.rstrip("/")
    request = urllib.request.Request(
        f"{base}/models",
        headers={"Authorization": f"Bearer {resolved.cliproxy_api_key or 'cliproxy-local'}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        unauthorised = exc.code in (401, 403)
        return ProxyProbe(
            base_url=base, reachable=True, key_accepted=not unauthorised, models=(),
            detail=(
                "Proxy rejected CLIPROXY_API_KEY."
                if unauthorised
                else f"Proxy answered HTTP {exc.code}."
            ),
        )
    except Exception as exc:  # noqa: BLE001 - URLError, timeouts, bad JSON all read the same
        return ProxyProbe(
            base_url=base, reachable=False, key_accepted=False, models=(),
            detail=f"No proxy reachable at {base}: {exc}",
        )

    models = tuple(
        sorted(str(entry["id"]) for entry in payload.get("data", []) if entry.get("id"))
    )
    return ProxyProbe(
        base_url=base, reachable=True, key_accepted=True, models=models,
        detail=f"{len(models)} models available.",
    )


def control_panel_url(settings: LLMSettings | None = None) -> str:
    """CLIProxyAPI serves its own management UI; model logins happen there.

    Deliberately not reimplemented here. The OAuth flows belong to the proxy
    (`-claude-login`, `-codex-device-login`), it ships a panel that drives them,
    and a second copy in this app would be one more thing to break on upgrade.
    """
    #: The panel sits at the server root, a level above the OpenAI-compatible
    #: `/v1` prefix that every other call in this module uses.
    resolved = settings or get_llm_settings()
    base = resolved.cliproxy_base_url.rstrip("/")
    return f"{base.removesuffix('/v1')}/management.html"
