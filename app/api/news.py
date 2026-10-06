"""Live research cards from PubMed and the RSS allowlist."""

from __future__ import annotations

from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.core.config import get_settings
from app.core.deps import get_news_rate_limiter, get_news_service, get_news_translation
from app.core.rate_limit import SlidingWindowRateLimiter, resolve_client_key
from app.domain.schemas import NewsCardView, NewsResponse
from app.services.news import NewsService, NewsSnapshot
from app.services.news_translation import (
    LocalizedCard,
    NewsLanguage,
    NewsTranslationService,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["news"])


def _card_view(localized: LocalizedCard) -> NewsCardView:
    card = localized.card
    translation = localized.translation
    if translation is None:
        return NewsCardView(
            id=card.id,
            title=card.title,
            source=card.source,
            published_at=card.published_at,
            snippet=card.snippet,
            url=card.url,
            kind=card.kind,
        )
    return NewsCardView(
        id=card.id,
        title=translation.title,
        source=card.source,
        published_at=card.published_at,
        snippet=translation.snippet,
        url=card.url,
        kind=card.kind,
        translated=True,
        original_title=card.title,
        original_snippet=card.snippet,
    )


def _response(snapshot: NewsSnapshot, cards: list[LocalizedCard]) -> NewsResponse:
    error: Literal["unavailable"] | None = None
    if snapshot.error == "unavailable":
        error = "unavailable"
    return NewsResponse(
        items=[_card_view(card) for card in cards],
        fetched_at=snapshot.fetched_at,
        stale=snapshot.stale,
        error=error,
    )


async def enforce_news_rate_limit(
    request: Request,
    response: Response,
    limiter: Annotated[SlidingWindowRateLimiter, Depends(get_news_rate_limiter)],
) -> None:
    """Limit news reads by client IP. The bucket is not the dataset bucket."""
    settings = get_settings()
    real_ip = request.headers.get("x-real-ip")
    client_host = request.client.host if request.client is not None else None
    key = resolve_client_key(
        real_ip=real_ip,
        client_host=client_host,
        trust_proxy=settings.trust_proxy_headers,
    )
    decision = await limiter.hit(key)
    response.headers["X-RateLimit-Limit"] = str(decision.limit)
    response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
    if not decision.allowed:
        logger.info("news_rate_limited")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(decision.retry_after_seconds),
                "X-RateLimit-Limit": str(decision.limit),
                "X-RateLimit-Remaining": "0",
            },
        )


@router.get(
    "/news",
    response_model=NewsResponse,
    summary="Recent longevity research and biohacking commentary",
    responses={status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Per-IP rate limit exceeded"}},
)
async def read_news(
    news_service: Annotated[NewsService, Depends(get_news_service)],
    translation: Annotated[NewsTranslationService, Depends(get_news_translation)],
    _: Annotated[None, Depends(enforce_news_rate_limit)],
    lang: Annotated[
        NewsLanguage,
        Query(description="Interface language; titles and snippets are machine-translated into it"),
    ] = "en",
) -> NewsResponse:
    """Return clipped cards from PubMed and the configured RSS feeds.

    The handler does not download article pages. When a source fails, the last
    cached copy of that source is returned with ``stale`` set. For a language
    other than English, titles and snippets are machine-translated and cached;
    if translation fails, the original text is returned with ``translated`` false.
    """
    snapshot = await news_service.read()
    cards = await translation.localize(snapshot.items, lang)
    return _response(snapshot, cards)
