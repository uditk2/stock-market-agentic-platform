"""Regressions guarded here:

- The extracted resolver must tag real headlines identically to the original
  news_feed.py, otherwise the rewrite silently changes which stocks a story
  maps to. Checked by replay against 420 already-tagged items.
- Short all-caps tickers must stay case-sensitive: lowercase "acc" inside
  "according" must not resolve to ACC.
- Atom feeds use namespaced tags, so a namespace-blind parser silently returns
  zero items for Livemint-style feeds.
"""

import json
from pathlib import Path

import pytest

from livegraph.news import parse_feed

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def tagged_sample():
    return json.loads((FIXTURES / "tagged_news_sample.json").read_text())


def test_resolver_matches_original_tagging_on_real_headlines(resolver, tagged_sample):
    mismatches = []
    for item in tagged_sample:
        text = f"{item['title']} {item['summary']}"
        got = set(resolver.resolve(text))
        expected = set(item["entities"])
        if got != expected:
            mismatches.append((item["title"][:60], sorted(expected), sorted(got)))
    assert not mismatches, f"{len(mismatches)}/{len(tagged_sample)} differ: {mismatches[:5]}"


def test_short_ticker_stays_case_sensitive(resolver):
    assert "ACC" not in resolver.resolve("according to the report, prices rose")
    assert "ACC" in resolver.resolve("ACC reports higher cement volumes")


def test_multi_word_alias_is_case_insensitive(resolver):
    hits = resolver.resolve("reliance industries posted a strong quarter")
    assert "RELIANCE" in hits


def test_macro_keyword_resolves(resolver):
    assert "CRUDE" in resolver.resolve("Brent crude climbs past $90 a barrel")


def test_parses_rss_items():
    raw = b"""<?xml version="1.0"?><rss version="2.0"><channel>
      <item><title>Tata Motors gains</title><link>https://x.test/1</link>
      <description>&lt;p&gt;Shares &lt;b&gt;rose&lt;/b&gt; 4%&lt;/p&gt;</description>
      <pubDate>Tue, 02 Sep 2025 10:00:00 +0530</pubDate></item>
    </channel></rss>"""
    items = parse_feed(raw)
    assert len(items) == 1
    assert items[0].title == "Tata Motors gains"
    assert items[0].summary == "Shares  rose  4%"
    assert items[0].link == "https://x.test/1"


def test_parses_namespaced_atom_entries():
    raw = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>Infosys wins deal</title>
      <link href="https://x.test/2"/>
      <summary>Large order</summary>
      <updated>Tue, 02 Sep 2025 10:00:00 +0530</updated></entry>
    </feed>"""
    items = parse_feed(raw)
    assert len(items) == 1
    assert items[0].link == "https://x.test/2"


def test_entry_without_link_is_dropped():
    raw = b"""<?xml version="1.0"?><rss version="2.0"><channel>
      <item><title>No link here</title></item></channel></rss>"""
    assert parse_feed(raw) == []
