"""Regressions guarded here:

- A screener round-up that happens to name one of a stock's sector peers is not
  news about that sector. Scoping it SECTOR puts an unrelated company's 52-week
  high into the drill-down as context for this one, and into the narration
  prompt as something to explain the move with.
- A round-up that *is* concentrated in one sector — a rally across defence
  names — is still sector news, so the guard must key on where the names sit,
  not on the item being a list.
- `matched_node` is shown as "tagged X". For a round-up the first tag is not a
  stand-in for the rest, so it has to be a name actually in the sector, or
  nothing at all.
"""

from livegraph.news import NewsItem, NewsKind
from livegraph.scan import NewsScope
from livegraph.scan.scoping import scope_for, to_scoped

PHARMA = {"LAURUSLABS", "SUNPHARMA", "CIPLA"}
IS_MACRO = frozenset({"MARKET_ACTIVITY", "CRUDE"}).__contains__


def item(entities, kind=NewsKind.ROUNDUP, title="headline"):
    return NewsItem(
        title=title,
        link=f"https://x.test/{abs(hash(tuple(entities)))}",
        summary="",
        ts=0.0,
        entities={node: node.lower() for node in entities},
        kind=kind,
    )


def scope(entities, symbol="SUNPHARMA", **kwargs):
    return scope_for(item(entities, **kwargs), symbol, PHARMA - {symbol}, IS_MACRO)


def test_named_stock_always_wins():
    """A round-up is genuine news for each name it lists, including this one."""
    assert scope(["SUNPHARMA", "LENSKART", "SOLARINDS"]) is NewsScope.STOCK


def test_scattered_roundup_naming_a_peer_is_not_sector_news():
    assert scope(["LENSKART", "LAURUSLABS", "SOLARINDS", "BSE"]) is NewsScope.MARKET


def test_roundup_concentrated_in_the_sector_still_is():
    assert scope(["LAURUSLABS", "CIPLA", "LENSKART"]) is NewsScope.SECTOR


def test_a_single_story_about_a_peer_is_sector_news():
    assert scope(["LAURUSLABS", "LENSKART"], kind=NewsKind.SINGLE) is NewsScope.SECTOR


def test_sector_match_names_a_name_in_the_sector():
    entry = to_scoped(
        item(["LENSKART", "LAURUSLABS", "CIPLA"]), NewsScope.SECTOR, "SUNPHARMA", PHARMA
    )
    assert entry.matched_node in {"LAURUSLABS", "CIPLA"}
    assert entry.roundup


def test_market_scoped_roundup_names_nobody():
    """No one company in a list speaks for the rest of it."""
    entry = to_scoped(item(["LENSKART", "SOLARINDS"]), NewsScope.MARKET, "SUNPHARMA", PHARMA)
    assert entry.matched_node is None


def test_market_scoped_single_story_still_names_its_tag():
    entry = to_scoped(
        item(["LENSKART"], kind=NewsKind.SINGLE), NewsScope.MARKET, "SUNPHARMA", PHARMA
    )
    assert entry.matched_node == "LENSKART"
