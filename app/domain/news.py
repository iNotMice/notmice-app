"""Pure news-feed parsing. Article HTML is never fetched or stored."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Literal
from urllib.parse import urlencode, urlsplit
from xml.etree import ElementTree

NewsKind = Literal["paper", "biohacking"]

PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PUBMED_TERM = (
    '("longevity"[tiab] OR "biological aging"[tiab] OR "healthspan"[tiab] OR "senescence"[tiab])'
)

_TITLE_MAX = 300
_SNIPPET_FLOOR = 8
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_MARKUP_BLOCK = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_MARKUP_TAG = re.compile(r"<[^>]+>")
_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


class NewsFetchError(Exception):
    """A configured source could not be read or parsed."""


@dataclass(frozen=True, slots=True)
class NewsCard:
    """One card ready for the API. ``snippet`` is clipped publisher text."""

    id: str
    title: str
    source: str
    published_at: date | None
    snippet: str
    url: str
    kind: NewsKind


def same_feed_host(started: str | None, final: str | None) -> bool:
    """True when a redirect stays on the same site, including a www prefix change."""
    left = _apex_host(started)
    right = _apex_host(final)
    return bool(left) and left == right


def assert_public_https(url: str) -> None:
    """Refuse non-HTTPS and loopback, link-local, or private addresses.

    Args:
        url: Absolute URL about to be requested or followed.

    Raises:
        NewsFetchError: If the URL is not a public HTTPS address.
    """
    parsed = urlsplit(url.strip())
    if parsed.scheme != "https" or not parsed.hostname:
        raise NewsFetchError("url must be https")
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "metadata.google.internal"} or host.endswith(".local"):
        raise NewsFetchError("host is not public")
    if _is_blocked_ip(host):
        raise NewsFetchError("host is not public")


def pubmed_esearch_url(*, retmax: int, tool: str, email: str) -> str:
    """Build the PubMed search URL for the longevity query."""
    query = {
        "db": "pubmed",
        "term": PUBMED_TERM,
        "retmode": "json",
        "retmax": str(retmax),
        "sort": "pub_date",
        "datetype": "pdat",
        "reldate": "90",
        "tool": tool,
    }
    if email.strip():
        query["email"] = email.strip()
    return f"{PUBMED_ESEARCH}?{urlencode(query)}"


def pubmed_efetch_url(pmids: list[str], *, tool: str, email: str) -> str:
    """Build the PubMed abstract fetch URL for already chosen ids."""
    query = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract",
        "tool": tool,
    }
    if email.strip():
        query["email"] = email.strip()
    return f"{PUBMED_EFETCH}?{urlencode(query)}"


def parse_esearch_ids(payload: str, limit: int) -> list[str]:
    """Return numeric PubMed ids from an esearch JSON body."""
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise NewsFetchError("esearch json") from exc
    if not isinstance(data, dict):
        raise NewsFetchError("esearch json")
    result = data.get("esearchresult")
    if not isinstance(result, dict) or result.get("ERROR"):
        raise NewsFetchError("esearch json")
    raw_ids = result.get("idlist", [])
    if not isinstance(raw_ids, list):
        raise NewsFetchError("esearch json")
    ids: list[str] = []
    for item in raw_ids:
        if isinstance(item, str) and item.isdigit():
            ids.append(item)
        if len(ids) >= limit:
            break
    return ids


def parse_pubmed_articles(xml_text: str, *, snippet_max_chars: int) -> list[NewsCard]:
    """Turn an efetch XML body into paper cards. Publisher HTML is not requested."""
    root = _parse_xml(xml_text)
    cards: list[NewsCard] = []
    for node in root.iter():
        if _local(node.tag) != "PubmedArticle":
            continue
        card = _pubmed_article(node, snippet_max_chars)
        if card is not None:
            cards.append(card)
    return cards


def parse_rss(
    xml_text: str,
    *,
    feed_url: str,
    snippet_max_chars: int,
    limit: int,
) -> list[NewsCard]:
    """Turn an RSS or Atom document into commentary cards."""
    root = _parse_xml(xml_text)
    source = _feed_title(root, feed_url)
    cards: list[NewsCard] = []
    for node in root.iter():
        if _local(node.tag) not in {"item", "entry"}:
            continue
        card = _rss_entry(node, source=source, snippet_max_chars=snippet_max_chars)
        if card is None:
            continue
        cards.append(card)
        if len(cards) >= limit:
            break
    return cards


def clip_snippet(text: str, max_chars: int) -> str:
    """Keep the first two sentences of publisher text, then a hard character cap."""
    limit = max_chars if max_chars >= _SNIPPET_FLOOR else _SNIPPET_FLOOR
    cleaned = re.sub(r"\s+", " ", _strip_markup(text)).strip()
    if not cleaned:
        return ""
    sentences = [part.strip() for part in _SENTENCE_SPLIT.split(cleaned) if part.strip()]
    chosen = " ".join(sentences[:2]) if sentences else cleaned
    if len(chosen) <= limit:
        return chosen
    trimmed = chosen[: limit - 1].rstrip(" ,;:")
    return f"{trimmed}…"


def clip_title(text: str) -> str:
    """Collapse a title to a single line and cap its length."""
    cleaned = re.sub(r"\s+", " ", _strip_markup(text)).strip()
    if len(cleaned) <= _TITLE_MAX:
        return cleaned
    return f"{cleaned[: _TITLE_MAX - 1].rstrip()}…"


def merge_cards(cards: list[NewsCard], limit: int) -> list[NewsCard]:
    """Sort newest first, drop duplicate URLs, and cap the list."""
    ordered = sorted(cards, key=lambda card: card.published_at or date.min, reverse=True)
    seen: set[str] = set()
    unique: list[NewsCard] = []
    for card in ordered:
        if card.url in seen:
            continue
        seen.add(card.url)
        unique.append(card)
        if len(unique) >= limit:
            break
    return unique


def _parse_xml(payload: str) -> ElementTree.Element:
    try:
        return ElementTree.fromstring(payload)
    except ElementTree.ParseError as exc:
        raise NewsFetchError("xml") from exc


def _pubmed_article(article: ElementTree.Element, snippet_max_chars: int) -> NewsCard | None:
    pmid = ""
    doi = ""
    for node in article.iter():
        local = _local(node.tag)
        if local == "PMID" and not pmid:
            pmid = (node.text or "").strip()
        if local == "ArticleId" and node.attrib.get("IdType") == "doi" and not doi:
            doi = (node.text or "").strip()
    if not pmid.isdigit():
        return None
    title = clip_title(_descendant_text(article, "ArticleTitle"))
    if not title:
        return None
    journal = clip_title(_descendant_text(article, "Title")) or "PubMed"
    abstract_parts: list[str] = []
    for node in article.iter():
        if _local(node.tag) == "AbstractText":
            piece = _text(node)
            if piece:
                abstract_parts.append(piece)
    published = _publication_date(article)
    url = _doi_url(doi) or f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    return NewsCard(
        id=f"pubmed:{pmid}",
        title=title,
        source=journal,
        published_at=published,
        snippet=clip_snippet(" ".join(abstract_parts), snippet_max_chars),
        url=url,
        kind="paper",
    )


def _rss_entry(
    entry: ElementTree.Element,
    *,
    source: str,
    snippet_max_chars: int,
) -> NewsCard | None:
    title = clip_title(_child_text(entry, "title"))
    url = _entry_link(entry)
    if not title or not url:
        return None
    body = (
        _child_text(entry, "description")
        or _child_text(entry, "summary")
        or _child_text(entry, "content")
    )
    published = _entry_date(entry)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return NewsCard(
        id=f"rss:{digest}",
        title=title,
        source=source,
        published_at=published,
        snippet=clip_snippet(body, snippet_max_chars),
        url=url,
        kind="biohacking",
    )


def _feed_title(root: ElementTree.Element, feed_url: str) -> str:
    for parent in root.iter():
        if _local(parent.tag) not in {"channel", "feed"}:
            continue
        for child in list(parent):
            if _local(child.tag) != "title":
                continue
            title = clip_title(_text(child))
            if title:
                return title
    host = urlsplit(feed_url).hostname or "RSS"
    return host


def _entry_link(entry: ElementTree.Element) -> str:
    alternate = ""
    fallback = ""
    for child in list(entry):
        if _local(child.tag) != "link":
            continue
        href = (child.attrib.get("href") or child.text or "").strip()
        if not href:
            continue
        rel = child.attrib.get("rel", "alternate")
        if rel == "alternate" and not alternate:
            alternate = href
        elif not fallback:
            fallback = href
    return _safe_http_url(alternate or fallback)


def _publication_date(article: ElementTree.Element) -> date | None:
    """Return when the paper appeared, not the journal issue it was assigned to.

    ``PubDate`` is the issue date. For online-first articles that issue is often
    the next calendar year, while ``ArticleDate`` is the day the paper went live.
    """
    body = _article_body(article)
    electronic: date | None = None
    printed: date | None = None
    for node in body.iter():
        if _local(node.tag) != "ArticleDate":
            continue
        parsed = _read_pub_date(node)
        if parsed is None:
            continue
        if node.attrib.get("DateType") == "Electronic":
            electronic = electronic or parsed
        else:
            printed = printed or parsed
    if electronic is not None:
        return electronic
    if printed is not None:
        return printed
    for node in body.iter():
        if _local(node.tag) == "PubDate":
            return _read_pub_date(node)
    return None


def _article_body(article: ElementTree.Element) -> ElementTree.Element:
    """Return the paper ``Article`` node, ignoring structured citations."""
    for node in article.iter():
        if _local(node.tag) == "Article":
            return node
    return article


def _entry_date(entry: ElementTree.Element) -> date | None:
    for name in ("pubDate", "published", "updated", "date"):
        raw = _child_text(entry, name)
        if not raw:
            continue
        parsed = _parse_feed_date(raw)
        if parsed is not None:
            return parsed
    return None


def _read_pub_date(node: ElementTree.Element) -> date | None:
    year_text = _child_text(node, "Year")
    month_text = _child_text(node, "Month")
    day_text = _child_text(node, "Day")
    if year_text.isdigit():
        month = _month_number(month_text) or 1
        day = int(day_text) if day_text.isdigit() else 1
        return _assemble_date(int(year_text), month, day)
    medline = _child_text(node, "MedlineDate")
    if not medline:
        return None
    year_match = re.search(r"(19|20)\d{2}", medline)
    if year_match is None:
        return None
    month_match = re.search(r"[A-Za-z]+", medline)
    parsed_month = _month_number(month_match.group(0)) if month_match else 1
    return _assemble_date(int(year_match.group(0)), parsed_month or 1, 1)


def _parse_feed_date(value: str) -> date | None:
    try:
        return parsedate_to_datetime(value).date()
    except (TypeError, ValueError, IndexError, OverflowError):
        pass
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _doi_url(doi: str) -> str | None:
    cleaned = doi.strip()
    if cleaned.lower().startswith("doi:"):
        cleaned = cleaned[4:].strip()
    if not cleaned or any(char.isspace() for char in cleaned) or "://" in cleaned:
        return None
    return f"https://doi.org/{cleaned}"


def _safe_http_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return url.strip()
    return ""


def _descendant_text(element: ElementTree.Element, name: str) -> str:
    for node in element.iter():
        if node is not element and _local(node.tag) == name:
            return _text(node)
    return ""


def _child_text(element: ElementTree.Element, name: str) -> str:
    for child in list(element):
        if _local(child.tag) == name:
            return _text(child)
    return ""


def _text(element: ElementTree.Element | None) -> str:
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def _local(tag: str) -> str:
    if tag.startswith("{"):
        return tag.rsplit("}", 1)[-1]
    return tag


def _strip_markup(value: str) -> str:
    without_blocks = _MARKUP_BLOCK.sub(" ", value)
    return unescape(_MARKUP_TAG.sub(" ", without_blocks))


def _month_number(value: str) -> int | None:
    if not value:
        return None
    if value.isdigit():
        number = int(value)
        if 1 <= number <= 12:
            return number
        return None
    return _MONTHS.get(value.casefold())


def _assemble_date(year: int, month: int, day: int) -> date | None:
    if year < 1900 or year > 2100:
        return None
    try:
        return date(year, month, day)
    except ValueError:
        try:
            return date(year, month, 1)
        except ValueError:
            return None


def _apex_host(hostname: str | None) -> str:
    host = (hostname or "").lower().rstrip(".")
    if host.startswith("www."):
        return host[4:]
    return host


def _is_blocked_ip(host: str) -> bool:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    )
