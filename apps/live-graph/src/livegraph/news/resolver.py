"""Resolve free news text to graph node ids.

Takes node names as a plain mapping rather than importing the graph module, so
`news` stays independent of `graph`; the API layer wires the two together.

Alias matching rules are carried over from the original news_feed.py:
- multi-word aliases match as a case-insensitive substring
- short all-caps tickers (ACC, BEL, HAL) match case-sensitively on a word
  boundary, otherwise "acc" hits every "according"
- other single-word aliases need >= 3 chars and a word boundary
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

#: Short all-caps symbols that are also common English fragments.
RISKY_SHORT = re.compile(r"^[A-Z&]{2,4}$")
_MIN_SINGLE_WORD_ALIAS = 3
_MIN_AUTO_ALIAS_LENGTH = 8
_SUFFIX_RE = re.compile(r"\s+(ltd\.?|limited)\s*$", re.I)
_INDIA_RE = re.compile(r"\s*\(india\)\s*", re.I)


class EntityResolver:
    def __init__(
        self,
        aliases: dict[str, set[str]],
        macro_keys: dict[str, str],
        known_nodes: frozenset[str],
    ):
        self._aliases = aliases
        self._macro_keys = macro_keys
        self._known = known_nodes

    @classmethod
    def from_file(
        cls, path: Path, stock_names: dict[str, str], known_nodes: frozenset[str]
    ) -> "EntityResolver":
        raw = json.loads(path.read_text(encoding="utf-8"))
        builder = _AliasBuilder(known_nodes)
        builder.add_auto_aliases(stock_names)
        builder.add_manual_aliases(raw.get("manual_aliases", {}))
        return cls(
            aliases=builder.result(),
            macro_keys=dict(raw.get("macro_keys", {})),
            known_nodes=known_nodes,
        )

    def resolve(self, text: str) -> dict[str, str]:
        """Return {node_id: matched_alias} for every stock and macro node in `text`."""
        found: dict[str, str] = {}
        haystack = f" {text.lower()} "
        for alias, node_ids in self._aliases.items():
            if not self._alias_matches(alias, text, haystack):
                continue
            for node_id in node_ids:
                found[node_id] = alias
        found.update(self._resolve_macros(haystack))
        return found

    def _alias_matches(self, alias: str, text: str, haystack: str) -> bool:
        if " " in alias:
            return alias in haystack
        upper = alias.upper()
        if RISKY_SHORT.match(upper):
            return _word_match(upper, text)
        return len(alias) >= _MIN_SINGLE_WORD_ALIAS and _word_match(alias, haystack)

    def _resolve_macros(self, haystack: str) -> dict[str, str]:
        hits: dict[str, str] = {}
        for keyword, node_id in self._macro_keys.items():
            if node_id not in self._known:
                continue
            matched = keyword in haystack if " " in keyword else _word_match(keyword, haystack)
            if matched:
                hits[node_id] = keyword
        return hits

    @property
    def alias_count(self) -> int:
        return len(self._aliases)


class _AliasBuilder:
    def __init__(self, known_nodes: frozenset[str]):
        self._known = known_nodes
        self._aliases: dict[str, set[str]] = defaultdict(set)

    def add_auto_aliases(self, stock_names: dict[str, str]) -> None:
        """Derive aliases from company names, multi-word only to stay safe."""
        for symbol, name in stock_names.items():
            base = _SUFFIX_RE.sub("", _INDIA_RE.sub(" ", name)).strip()
            if " " in base and len(base) >= _MIN_AUTO_ALIAS_LENGTH:
                self._add(base, [symbol])
                self._add(name, [symbol])

    def add_manual_aliases(self, manual: dict[str, object]) -> None:
        for alias, node_ids in manual.items():
            ids = [node_ids] if isinstance(node_ids, str) else list(node_ids or [])
            self._add(alias, [str(i) for i in ids])

    def _add(self, alias: str, node_ids: list[str]) -> None:
        valid = [node_id for node_id in node_ids if node_id in self._known]
        if not valid:
            return
        key = alias.lower().strip()
        if key:
            self._aliases[key].update(valid)

    def result(self) -> dict[str, set[str]]:
        return dict(self._aliases)


def _word_match(needle: str, haystack: str) -> bool:
    return re.search(rf"\b{re.escape(needle)}\b", haystack) is not None
