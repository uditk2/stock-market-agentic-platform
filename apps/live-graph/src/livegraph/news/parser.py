"""RSS/Atom parsing. Pure: bytes in, NewsItem list out."""

from __future__ import annotations

import html as htmllib
import re
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from .models import NewsItem

_TAG_RE = re.compile(r"<[^>]+>")
_SUMMARY_LIMIT = 400


def strip_html(value: str | None) -> str:
    return _TAG_RE.sub(" ", htmllib.unescape(value or "")).strip()


def parse_feed(raw: bytes) -> list[NewsItem]:
    root = ET.fromstring(raw)
    entries = root.findall(".//item") + [
        e for e in root.iter() if e.tag.endswith("}entry")
    ]
    items = (_parse_entry(entry) for entry in entries)
    return [item for item in items if item is not None]


def _parse_entry(entry: ET.Element) -> NewsItem | None:
    title = strip_html(_text(entry, "title"))
    link = _link(entry)
    if not title or not link:
        return None
    summary = strip_html(_text(entry, "description") or _text(entry, "summary"))
    return NewsItem(
        title=title,
        link=link,
        summary=summary[:_SUMMARY_LIMIT],
        ts=_timestamp(entry),
    )


def _child(entry: ET.Element, tag: str) -> ET.Element | None:
    """Match on local name so both namespaced Atom and plain RSS work."""
    for child in entry:
        if child.tag == tag or child.tag.endswith(f"}}{tag}"):
            return child
    return None


def _text(entry: ET.Element, tag: str) -> str:
    child = _child(entry, tag)
    return (child.text or "") if child is not None else ""


def _link(entry: ET.Element) -> str:
    child = _child(entry, "link")
    if child is None:
        return ""
    return (child.text or child.get("href") or "").strip()


def _timestamp(entry: ET.Element) -> float:
    for tag in ("pubDate", "updated", "published"):
        raw = _text(entry, tag)
        if not raw:
            continue
        try:
            return parsedate_to_datetime(raw).timestamp()
        except (TypeError, ValueError):
            continue
    return time.time()
