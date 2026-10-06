"""Translate the news feed ahead of readers so a request rarely waits on the model."""

from __future__ import annotations

import asyncio
import contextlib
from typing import get_args

import structlog

from app.services.news import NewsService
from app.services.news_translation import SOURCE_LANGUAGE, NewsLanguage, NewsTranslationService

logger = structlog.get_logger(__name__)

WARM_LANGUAGES: tuple[NewsLanguage, ...] = tuple(
    language for language in get_args(NewsLanguage) if language != SOURCE_LANGUAGE
)


async def warm_once(news: NewsService, translation: NewsTranslationService) -> None:
    """Read the feed and start translation jobs for every non-source language."""
    snapshot = await news.read()
    for language in WARM_LANGUAGES:
        await translation.localize(snapshot.items, language, wait=False)
    await translation.wait_idle()


async def run_prewarm(
    news: NewsService,
    translation: NewsTranslationService,
    *,
    interval_seconds: float,
    stop: asyncio.Event,
) -> None:
    """Warm translations now and then every ``interval_seconds`` until ``stop`` is set."""
    while not stop.is_set():
        try:
            await warm_once(news, translation)
        except Exception:  # a failed warm-up must never stop the API
            logger.exception("news_prewarm_failed")
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=interval_seconds)
