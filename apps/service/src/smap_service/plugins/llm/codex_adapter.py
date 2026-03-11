from smap_service.core.interfaces import LLMAdapter


class CodexAdapter(LLMAdapter):
    @property
    def name(self) -> str:
        return "codex"

    def health_check(self) -> bool:
        return True

    def summarize(self, text: str) -> str:
        return f"[codex-summary] {text[:120]}"
