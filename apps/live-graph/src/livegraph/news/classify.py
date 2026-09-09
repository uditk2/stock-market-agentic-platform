"""Tell a story about one company apart from a list of several.

A round-up names companies that share nothing but an editor's list: "Lenskart
Solutions among 4 stocks to hit 52-week highs" puts an eyewear retailer, a
pharma API maker and an explosives maker in one item. Tagging every one of them
is right — it is genuine news for each — but the co-occurrence is not evidence
of a link between them, and anything that reads pairs off a tag set would
invent one. Marking the item lets consumers keep the tags and drop the pairing.

The rules are deliberately shallow, because the headline is all there is to go
on: a counted list of names ("4 stocks", "three intraday stocks"), a list
column's standing marker ("Stocks in news:", "Hot Stocks"), or simply more
names than a story about one company plausibly carries.
"""

from __future__ import annotations

import re
from collections.abc import Collection
from enum import StrEnum


class NewsKind(StrEnum):
    SINGLE = "single"
    ROUNDUP = "roundup"


#: Below this many company tags there is no co-occurrence to guard against, so
#: even an obvious list column is treated as the story of the one name in it.
MIN_ROUNDUP_NAMES = 2

#: More names than a story about one company carries, whatever the headline
#: says. Takes over from the headline patterns for feeds that write plainly.
MANY_NAMES = 4

_NUMBER_WORD = "two|three|four|five|six|seven|eight|nine|ten|eleven|twelve"
_COLLECTIVE = r"stocks?|shares|scrips?|counters?|picks?|smallcaps?|midcaps?|largecaps?"

#: "4 stocks", "10 midcap stocks", "three intraday stocks", "five shares".
#: The optional words in between carry the qualifier, so a count that belongs
#: to something else ("in 4 sessions", "10 key things") never reaches the noun.
_COUNTED = re.compile(
    rf"\b(?:\d{{1,3}}|{_NUMBER_WORD})\s+(?:[a-z&.-]+\s+){{0,2}}(?:{_COLLECTIVE})\b",
    re.I,
)

#: "Infosys, TCS, Wipro, other IT stocks fall up to 3%".
_AND_OTHERS = re.compile(rf"\b(?:other|more)\s+(?:[a-z&.-]+\s+){{0,2}}(?:{_COLLECTIVE})\b", re.I)

#: Standing list columns. Every one of these is a page of separate items.
_LIST_MARKERS = (
    "stocks in news",
    "stocks in focus",
    "stocks to buy",
    "stocks to sell",
    "stocks to watch",
    "shares to buy",
    "shares to sell",
    "hot stocks",
    "buzzing stocks",
    "breakout stocks",
    "stock picks",
    "top picks",
    "stock recommendations",
    "top gainers",
    "top losers",
    "gainers and losers",
    "f&o talk",
    "volume shocker",
    "dividend alert",
    "market wrap",
    "closing bell",
)


def classify(title: str, company_tags: Collection[str]) -> NewsKind:
    """Is this one story, or several filed under one headline?

    `company_tags` is the resolved stock nodes only. Macro nodes are conditions
    the story happens under, not names listed beside one another.
    """
    if len(set(company_tags)) < MIN_ROUNDUP_NAMES:
        return NewsKind.SINGLE
    if len(set(company_tags)) >= MANY_NAMES or _reads_as_a_list(title):
        return NewsKind.ROUNDUP
    return NewsKind.SINGLE


def _reads_as_a_list(title: str) -> bool:
    lowered = title.lower()
    if any(marker in lowered for marker in _LIST_MARKERS):
        return True
    return bool(_COUNTED.search(title) or _AND_OTHERS.search(title))
