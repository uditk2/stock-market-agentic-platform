from smap_service.core.interfaces import LLMAdapter


class ClaudeAdapter(LLMAdapter):
    @property
    def name(self) -> str:
        return "claude"

    def health_check(self) -> bool:
        return True

    def summarize(self, text: str) -> str:
        return f"[claude-summary] {text[:120]}"
