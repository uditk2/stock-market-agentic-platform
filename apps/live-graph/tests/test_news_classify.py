"""Regressions guarded here:

- A round-up names companies that share nothing but an editor's list. Tagging
  every one of them is right; pairing them is not. If the classifier stops
  marking these, the co-occurrence flows into the drill-down, the narration and
  the analyst as though a relationship existed.
- The counted-name pattern must read the noun it counts. "in 4 sessions" and
  "10 key things to know" are not lists of stocks, and a headline wrongly
  marked a round-up loses its stock-level standing in the feed.
- One tagged name is a story about that name, whatever the headline shape,
  because there is no co-occurrence to guard against.
"""

import pytest

from livegraph.news import NewsKind, NewsPoller, classify
from livegraph.news.parser import parse_feed

#: The headline that prompted this: an eyewear retailer, a pharma API maker and
#: an explosives maker, together only because a screener returned all three.
LENSKART = "Lenskart Solutions among 4 stocks to hit 52-week highs & rallied up to 22% in a month"

ROUNDUPS = [
    (LENSKART, ["LENSKART", "LAURUSLABS", "SOLARINDS", "BSE"]),
    ("Stocks in news: Lenskart, GNG Electronics, Vedanta, Infosys, RIL", ["LENSKART", "VEDL"]),
    ("Hot Stocks: 3 stocks that may give returns between 11-36%", ["TITAN", "INFY"]),
    ("Infosys, TCS, Wipro, other IT stocks fall up to 3%", ["INFY", "TCS"]),
    ("Breakout stocks to buy or sell: Sumeet Bagadia recommends five shares", ["KPRMILL", "NYKAA"]),
    ("Bharat Forge, GE Vernova among 10 midcap stocks that hit 52-week highs", ["BHARATFORG", "BEL"]),
    #: No list wording at all, but more names than one story carries.
    ("Sensex jumps over 300 pts, Nifty above 23,300", ["RELIANCE", "HINDUNILVR", "TCS", "SBIN"]),
]

SINGLES = [
    ("Reliance Industries share price jumps over 2% on Meta data centre tie-up", ["RELIANCE"]),
    ("Cyient shares crash 6% as stock turns ex-record date for Rs 720 crore buyback", ["CYIENT"]),
    ("Nifty 50 surges 4.5% in 4 sessions as crude oil prices tumble", ["RELIANCE"]),
    ("NSE IPO: Financials, dividend track record - 10 key things to know", ["BSE"]),
    ("Why Tata Motors and Ashok Leyland are racing ahead of the auto pack", ["TATAMOTORS", "ASHOKLEY"]),
    #: A list column that resolved to one name only: still that name's story.
    ("Stocks in news: Emcure Pharma, Dixon Technologies, Ajanta Pharma", ["DIXON"]),
]


@pytest.mark.parametrize("title,tags", ROUNDUPS, ids=[t[:40] for t, _ in ROUNDUPS])
def test_lists_are_roundups(title, tags):
    assert classify(title, tags) is NewsKind.ROUNDUP


@pytest.mark.parametrize("title,tags", SINGLES, ids=[t[:40] for t, _ in SINGLES])
def test_single_company_stories_are_not(title, tags):
    assert classify(title, tags) is NewsKind.SINGLE


def test_macro_tags_do_not_make_a_list(resolver):
    """Crude and the rupee are conditions, not names listed beside one another."""
    title = "Rupee hits six-week high on offshore flows as crude slips"
    entities = resolver.resolve(title)
    companies = [node for node in entities if node not in resolver.macro_nodes]
    assert classify(title, companies) is NewsKind.SINGLE


def test_poller_marks_the_item(resolver, monkeypatch):
    """End to end: the shape the feed and the API actually read."""
    feed = f"""<?xml version="1.0"?><rss version="2.0"><channel>
      <item><title>{LENSKART.replace("&", "&amp;")}</title><link>https://x.test/roundup</link>
      <description>Laurus Labs and Solar Industries also featured.</description></item>
      <item><title>Laurus Labs wins USFDA nod for its Vizag plant</title>
      <link>https://x.test/single</link><description>Approval cleared.</description></item>
    </channel></rss>""".encode()

    poller = NewsPoller(resolver=resolver, is_fo=lambda _: False)
    monkeypatch.setattr(poller, "_fetch", lambda url: feed)
    added = {item.link: item for item in poller.poll_once()}

    assert len(parse_feed(feed)) == 2
    assert added["https://x.test/roundup"].is_roundup
    assert not added["https://x.test/single"].is_roundup
    #: The tags are kept either way. Marking the item is what changes, not the
    #: tagging: the round-up is still news for every name it lists.
    assert "LAURUSLABS" in added["https://x.test/roundup"].entities
