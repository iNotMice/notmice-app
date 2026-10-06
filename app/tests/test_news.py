"""News feed tests. Fixtures stand in for PubMed and RSS; nothing is fetched live."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.deps import get_news_rate_limiter, get_news_service, get_news_translation
from app.core.rate_limit import SlidingWindowRateLimiter
from app.domain.news import (
    NewsCard,
    NewsFetchError,
    assert_public_https,
    clip_snippet,
    parse_pubmed_articles,
    parse_rss,
    same_feed_host,
)
from app.main import create_app
from app.services.news import NewsMemoryCache, NewsService
from app.services.news_translation import (
    NewsLanguage,
    NewsTranslationError,
    NewsTranslationService,
    TranslatedText,
    TranslationBatch,
)

_ESEARCH = '{"esearchresult":{"idlist":["12345678"]}}'
_EFETCH = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <Journal>
          <Title>Aging Cell</Title>
          <JournalIssue>
            <PubDate><Year>2026</Year><Month>Jan</Month><Day>15</Day></PubDate>
          </JournalIssue>
        </Journal>
        <ArticleTitle>Senescence and <i>longevity</i></ArticleTitle>
        <Abstract>
          <AbstractText>
            Albumin and CRP were discussed. Second sentence stays. Third sentence drops.
          </AbstractText>
        </Abstract>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="doi">10.1000/xyz</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""
_RSS = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Fight Aging</title>
    <item>
      <title>Commentary on &lt;i&gt;glucose&lt;/i&gt; control</title>
      <link>https://www.fightaging.org/archives/example/</link>
      <pubDate>Mon, 02 Mar 2026 00:00:00 GMT</pubDate>
      <description><![CDATA[
        <p>First note. <b>Second note.</b> Third note.</p><script>alert(1)</script>
      ]]></description>
    </item>
  </channel>
</rss>
"""
_ATOM = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Example Atom</title>
  <entry>
    <title>Atom item</title>
    <link href="https://example.com/atom-post" rel="alternate"/>
    <updated>2026-02-01T00:00:00Z</updated>
    <summary>Only one sentence</summary>
  </entry>
</feed>
"""
_FEED = "https://example.com/feed/"


class _Clock:
    def __init__(self) -> None:
        self.value = 1_000.0

    def __call__(self) -> float:
        return self.value


class _MapFetcher:
    def __init__(self) -> None:
        self.pages: dict[str, str] = {}
        self.fail: set[str] = set()
        self.calls: list[str] = []

    async def get_text(self, url: str) -> str:
        self.calls.append(url)
        for key in self.fail:
            if key in url:
                raise NewsFetchError("down")
        for key, body in self.pages.items():
            if key in url:
                return body
        raise NewsFetchError("missing")


def _service(
    fetcher: _MapFetcher,
    *,
    ttl: int = 3600,
    feeds: list[str] | None = None,
    now: _Clock | None = None,
) -> NewsService:
    return NewsService(
        fetcher,
        NewsMemoryCache(ttl),
        rss_feeds=[_FEED] if feeds is None else feeds,
        now=now,
    )


def _loaded(fetcher: _MapFetcher) -> None:
    fetcher.pages["esearch.fcgi"] = _ESEARCH
    fetcher.pages["efetch.fcgi"] = _EFETCH
    fetcher.pages[_FEED] = _RSS


def test_clip_snippet_keeps_two_sentences_and_drops_markup() -> None:
    """Publisher HTML and later sentences do not become the card body."""
    raw = "<p>First sentence. <b>Second</b> sentence. Third sentence.</p><script>alert(1)</script>"
    assert clip_snippet(raw, max_chars=420) == "First sentence. Second sentence."


def test_clip_snippet_truncates_a_long_sentence() -> None:
    """A single run-on sentence still respects the character cap."""
    clipped = clip_snippet("A" * 500, max_chars=40)
    assert len(clipped) == 40
    assert clipped.endswith("…")


def test_www_redirect_stays_on_the_feed_host() -> None:
    """A publisher that drops www is still the allowlisted feed."""
    assert same_feed_host("www.lifespan.io", "lifespan.io")
    assert same_feed_host("www.fightaging.org", "www.fightaging.org")
    assert not same_feed_host("www.lifespan.io", "evil.example")
    assert not same_feed_host("www.lifespan.io", None)


def test_public_https_rejects_insecure_and_local_hosts() -> None:
    """The fetcher may not call plain HTTP or loopback addresses."""
    with pytest.raises(NewsFetchError):
        assert_public_https("http://example.com/feed")
    with pytest.raises(NewsFetchError):
        assert_public_https("https://127.0.0.1/feed")
    with pytest.raises(NewsFetchError):
        assert_public_https("https://10.0.0.8/feed")
    assert_public_https("https://example.com/feed")


_AHEAD_OF_ISSUE = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>42741701</PMID>
      <Article>
        <Journal>
          <Title>Bioactive materials</Title>
          <JournalIssue>
            <PubDate><Year>2027</Year><Month>Feb</Month></PubDate>
          </JournalIssue>
        </Journal>
        <ArticleTitle>Context-dependent vesicles</ArticleTitle>
        <Abstract>
          <AbstractText>Electronic publication is the news date.</AbstractText>
        </Abstract>
        <ArticleDate DateType="Print">
          <Year>2027</Year><Month>02</Month><Day>01</Day>
        </ArticleDate>
        <ArticleDate DateType="Electronic">
          <Year>2026</Year><Month>09</Month><Day>08</Day>
        </ArticleDate>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""


def test_pubmed_prefers_electronic_date_over_future_issue() -> None:
    """A 2027 journal issue must not replace the 2026 electronic publication date."""
    cards = parse_pubmed_articles(_AHEAD_OF_ISSUE, snippet_max_chars=420)
    assert len(cards) == 1
    assert cards[0].published_at == date(2026, 9, 8)


def test_parse_rss_reads_atom_links() -> None:
    """Atom href links become cards without fetching the entry page."""
    cards = parse_rss(_ATOM, feed_url=_FEED, snippet_max_chars=420, limit=5)
    assert len(cards) == 1
    assert cards[0].url == "https://example.com/atom-post"
    assert cards[0].kind == "biohacking"
    assert cards[0].published_at == date(2026, 2, 1)
    assert cards[0].source == "Example Atom"


async def test_read_builds_cards_from_fixtures_and_caches() -> None:
    """PubMed and RSS fixtures become clipped cards. A second read does not refetch."""
    fetcher = _MapFetcher()
    _loaded(fetcher)
    clock = _Clock()
    service = _service(fetcher, ttl=10, now=clock)
    first = await service.read()
    assert first.error is None
    assert first.stale is False
    assert [card.kind for card in first.items] == ["biohacking", "paper"]
    paper = first.items[1]
    commentary = first.items[0]
    assert paper.source == "Aging Cell"
    assert paper.published_at == date(2026, 1, 15)
    assert paper.url == "https://doi.org/10.1000/xyz"
    assert paper.snippet == "Albumin and CRP were discussed. Second sentence stays."
    assert "Third sentence" not in paper.snippet
    assert commentary.snippet == "First note. Second note."
    assert "alert" not in commentary.snippet
    assert commentary.title == "Commentary on glucose control"
    assert all("eutils.ncbi.nlm.nih.gov" in url or url == _FEED for url in fetcher.calls)
    assert not any("pubmed.ncbi.nlm.nih.gov" in url for url in fetcher.calls)
    calls = len(fetcher.calls)
    clock.value += 5
    second = await service.read()
    assert len(fetcher.calls) == calls
    assert second.stale is False
    assert [card.id for card in second.items] == [card.id for card in first.items]


async def test_expired_source_falls_back_to_cache() -> None:
    """A failed refresh keeps the previous cards and marks the payload stale."""
    fetcher = _MapFetcher()
    _loaded(fetcher)
    clock = _Clock()
    service = _service(fetcher, ttl=10, now=clock)
    first = await service.read()
    clock.value += 20
    fetcher.fail.update({"esearch.fcgi", _FEED})
    stale = await service.read()
    assert stale.stale is True
    assert stale.error is None
    assert [card.id for card in stale.items] == [card.id for card in first.items]


async def test_total_failure_without_cache_is_unavailable() -> None:
    """No cache and no live source yields an empty error, not an exception."""
    fetcher = _MapFetcher()
    fetcher.fail.update({"esearch.fcgi", _FEED})
    snapshot = await _service(fetcher).read()
    assert snapshot.items == ()
    assert snapshot.error == "unavailable"
    assert snapshot.stale is False


async def test_insecure_feed_url_is_not_requested() -> None:
    """An http allowlist entry is a source failure and is never passed to the fetcher."""
    fetcher = _MapFetcher()
    fetcher.pages["esearch.fcgi"] = '{"esearchresult":{"idlist":[]}}'
    service = _service(fetcher, feeds=["http://example.com/feed"])
    snapshot = await service.read()
    assert snapshot.error is None
    assert snapshot.items == ()
    assert fetcher.calls
    assert all(url.startswith("https://") for url in fetcher.calls)


def _application(
    service: NewsService,
    limiter: SlidingWindowRateLimiter,
    translation: NewsTranslationService | None = None,
) -> FastAPI:
    application = create_app()
    translator = translation or NewsTranslationService(None, daily_token_budget=0)

    def override_translation() -> NewsTranslationService:
        return translator

    def override_service() -> NewsService:
        return service

    def override_limiter() -> SlidingWindowRateLimiter:
        return limiter

    application.dependency_overrides[get_news_service] = override_service
    application.dependency_overrides[get_news_rate_limiter] = override_limiter
    application.dependency_overrides[get_news_translation] = override_translation
    return application


async def test_get_news_returns_cards() -> None:
    """GET /api/v1/news maps fixture cards and does not expose a write method."""
    fetcher = _MapFetcher()
    _loaded(fetcher)
    application = _application(
        _service(fetcher),
        SlidingWindowRateLimiter(limit=20, window_seconds=60),
    )
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/news")
        spec = await client.get("/openapi.json")
    assert response.status_code == 200
    body = response.json()
    assert body["stale"] is False
    assert body["error"] is None
    assert body["items"][0]["kind"] == "biohacking"
    assert body["items"][1]["url"] == "https://doi.org/10.1000/xyz"
    news_ops = spec.json()["paths"]["/api/v1/news"]
    assert "get" in news_ops
    for method in ("post", "put", "patch", "delete"):
        assert method not in news_ops


async def test_news_rate_limit_is_per_ip() -> None:
    """The third request from one address is 429. Another address still reads."""
    fetcher = _MapFetcher()
    _loaded(fetcher)
    application = _application(
        _service(fetcher),
        SlidingWindowRateLimiter(limit=2, window_seconds=60),
    )
    transport = ASGITransport(app=application)
    headers = {"X-Real-IP": "203.0.113.20"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/api/v1/news", headers=headers)
        second = await client.get("/api/v1/news", headers=headers)
        third = await client.get("/api/v1/news", headers=headers)
        other = await client.get("/api/v1/news", headers={"X-Real-IP": "203.0.113.21"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["detail"] == "Rate limit exceeded"
    assert int(third.headers["retry-after"]) >= 1
    assert other.status_code == 200


class _FakeTranslator:
    """Prefixes text with the language code. Can fail or answer for unknown ids."""

    def __init__(self, *, fail: bool = False, extra_id: bool = False, tokens: int = 100) -> None:
        self.calls: list[tuple[list[str], str]] = []
        self.fail = fail
        self.extra_id = extra_id
        self.tokens = tokens

    async def translate(
        self, cards: Sequence[NewsCard], language: NewsLanguage
    ) -> TranslationBatch:
        self.calls.append(([card.id for card in cards], language))
        if self.fail:
            raise NewsTranslationError("boom", tokens_used=50)
        items = {
            card.id: TranslatedText(
                title=f"[{language}] {card.title}", snippet=f"[{language}] {card.snippet}"
            )
            for card in cards
        }
        if self.extra_id:
            items["not-requested"] = TranslatedText(title="x", snippet="y")
        return TranslationBatch(items=items, tokens=self.tokens)


def _card(card_id: str, title: str = "Senescence and longevity") -> NewsCard:
    return NewsCard(
        id=card_id,
        title=title,
        source="Fight Aging!",
        published_at=date(2026, 10, 5),
        snippet="Albumin and CRP were discussed.",
        url="https://example.org/a",
        kind="biohacking",
    )


async def test_english_cards_are_not_sent_for_translation() -> None:
    """The source language passes through without a provider call."""
    translator = _FakeTranslator()
    service = NewsTranslationService(translator, daily_token_budget=10_000)
    result = await service.localize([_card("a")], "en")
    assert result[0].translation is None
    assert translator.calls == []


async def test_translation_is_cached_per_card_and_language() -> None:
    """A second read of the same cards does not call the provider again."""
    translator = _FakeTranslator()
    service = NewsTranslationService(translator, daily_token_budget=10_000)
    first = await service.localize([_card("a"), _card("b")], "ru")
    second = await service.localize([_card("a"), _card("b")], "ru")
    assert len(translator.calls) == 1
    assert first[0].translation == TranslatedText(
        title="[ru] Senescence and longevity", snippet="[ru] Albumin and CRP were discussed."
    )
    assert second == first
    await service.localize([_card("a")], "fr")
    assert translator.calls[-1] == (["a"], "fr")


async def test_changed_card_text_is_translated_again() -> None:
    """The cache key includes the text, so an edited title is not served stale."""
    translator = _FakeTranslator()
    service = NewsTranslationService(translator, daily_token_budget=10_000)
    await service.localize([_card("a")], "de")
    updated = await service.localize([_card("a", title="Edited title")], "de")
    assert len(translator.calls) == 2
    assert updated[0].translation is not None
    assert updated[0].translation.title == "[de] Edited title"


async def test_failed_translation_falls_back_to_original() -> None:
    """Provider errors leave the card untranslated instead of failing the feed."""
    service = NewsTranslationService(_FakeTranslator(fail=True), daily_token_budget=10_000)
    result = await service.localize([_card("a")], "ru")
    assert result[0].translation is None
    assert result[0].card.title == "Senescence and longevity"


async def test_unrequested_ids_are_ignored() -> None:
    """Only ids that were sent can come back."""
    service = NewsTranslationService(_FakeTranslator(extra_id=True), daily_token_budget=10_000)
    result = await service.localize([_card("a")], "ru")
    assert [item.card.id for item in result] == ["a"]
    assert service._cache  # the requested card is cached
    assert all(key[0] != "not-requested" for key in service._cache)


async def test_daily_budget_stops_new_translations() -> None:
    """Once the day's tokens are spent, new cards show the original text."""
    translator = _FakeTranslator(tokens=600)
    service = NewsTranslationService(
        translator, daily_token_budget=500, today=lambda: date(2026, 10, 6)
    )
    await service.localize([_card("a")], "ru")
    result = await service.localize([_card("b")], "ru")
    assert len(translator.calls) == 1
    assert result[0].translation is None


async def test_get_news_translates_into_requested_language() -> None:
    """lang=ru returns translated text plus the originals; tags can still use the source."""
    fetcher = _MapFetcher()
    _loaded(fetcher)
    translation = NewsTranslationService(_FakeTranslator(), daily_token_budget=10_000)
    application = _application(
        _service(fetcher),
        SlidingWindowRateLimiter(limit=20, window_seconds=60),
        translation,
    )
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        translated = await client.get("/api/v1/news", params={"lang": "ru"})
        english = await client.get("/api/v1/news", params={"lang": "en"})
        unsupported = await client.get("/api/v1/news", params={"lang": "xx"})
    item = translated.json()["items"][0]
    assert item["translated"] is True
    assert item["title"] == f"[ru] {item['original_title']}"
    assert item["original_snippet"] is not None
    plain = english.json()["items"][0]
    assert plain["translated"] is False
    assert plain["original_title"] is None
    assert unsupported.status_code == 422
