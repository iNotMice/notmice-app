"""FastAPI dependencies. Wiring only — no business logic."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.rate_limit import SlidingWindowRateLimiter
from app.core.security import Argon2SeedHasher, JwtTokenIssuer
from app.repositories.dataset import DatasetRepository
from app.repositories.health import HealthRepository
from app.repositories.lab_results import LabResultRepository
from app.repositories.users import UserRepository
from app.services.accounts import AccountService
from app.services.dataset import DatasetService
from app.services.export import ExportService
from app.services.extract_sessions import InMemoryExtractSessionStore
from app.services.gemini_budget import GeminiTokenBudget
from app.services.health import HealthService
from app.services.news import HttpxTextFetcher, NewsMemoryCache, NewsService
from app.services.uploads import UploadService
from app.services.vision import ExtractionProvider, build_extraction_provider

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_extract_sessions: InMemoryExtractSessionStore | None = None
_vision_provider: ExtractionProvider | None = None
_public_rate_limiter: SlidingWindowRateLimiter | None = None
_account_rate_limiter: SlidingWindowRateLimiter | None = None
_news_rate_limiter: SlidingWindowRateLimiter | None = None
_news_service: NewsService | None = None
_gemini_budget: GeminiTokenBudget | None = None


def get_engine() -> AsyncEngine:
    """Return a process-wide async engine, created on first use."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            get_settings().database_url,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory bound to the process engine."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped async session and commit on success."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_health_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> HealthService:
    """Build the health service for a request."""
    return HealthService(HealthRepository(session))


async def get_account_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AccountService:
    """Build the account service for a request."""
    settings = get_settings()
    return AccountService(
        users=UserRepository(session),
        hasher=Argon2SeedHasher(settings.seed_hash_secret),
        tokens=JwtTokenIssuer(settings.jwt_secret, settings.access_token_ttl_seconds),
    )


def get_extract_sessions() -> InMemoryExtractSessionStore:
    """Return the process-wide in-memory extract session store."""
    global _extract_sessions
    if _extract_sessions is None:
        _extract_sessions = InMemoryExtractSessionStore(get_settings().extract_session_ttl_seconds)
    return _extract_sessions


def get_vision_provider() -> ExtractionProvider:
    """Return the configured Vision provider (Gemini by default)."""
    global _vision_provider
    if _vision_provider is None:
        settings = get_settings()
        _vision_provider = build_extraction_provider(
            provider=settings.vision_provider,
            gemini_api_key=settings.gemini_api_key,
            gemini_model=settings.gemini_model,
            claude_api_key=settings.claude_api_key,
            claude_model=settings.claude_model,
            gemini_timeout_seconds=settings.gemini_timeout_seconds,
        )
    return _vision_provider


def get_gemini_budget() -> GeminiTokenBudget:
    """Return the process-wide Gemini token ledger."""
    global _gemini_budget
    if _gemini_budget is None:
        settings = get_settings()
        _gemini_budget = GeminiTokenBudget(
            daily_token_budget=settings.gemini_daily_token_budget,
            user_daily_token_budget=settings.gemini_user_daily_token_budget,
            ip_daily_token_budget=settings.gemini_ip_daily_token_budget,
            call_token_reserve=settings.gemini_call_token_reserve,
            user_daily_calls=settings.gemini_user_daily_calls,
            ip_daily_calls=settings.gemini_ip_daily_calls,
            warn_ratio=settings.gemini_budget_warn_ratio,
        )
    return _gemini_budget


def get_news_service() -> NewsService:
    """Return the process-wide news reader. External calls are cached in memory."""
    global _news_service
    if _news_service is None:
        settings = get_settings()
        _news_service = NewsService(
            HttpxTextFetcher(),
            NewsMemoryCache(settings.news_cache_ttl_seconds),
            rss_feeds=settings.news_rss_feed_list,
            pubmed_retmax=settings.news_pubmed_retmax,
            snippet_max_chars=settings.news_snippet_max_chars,
            email=settings.news_contact_email,
        )
    return _news_service


def get_news_rate_limiter() -> SlidingWindowRateLimiter:
    """Return the process-wide limiter for the news route."""
    global _news_rate_limiter
    if _news_rate_limiter is None:
        settings = get_settings()
        _news_rate_limiter = SlidingWindowRateLimiter(
            limit=settings.news_rate_limit,
            window_seconds=settings.news_rate_limit_window_seconds,
        )
    return _news_rate_limiter


def get_account_rate_limiter() -> SlidingWindowRateLimiter:
    """Return the process-wide limiter for account create and login."""
    global _account_rate_limiter
    if _account_rate_limiter is None:
        settings = get_settings()
        _account_rate_limiter = SlidingWindowRateLimiter(
            limit=settings.account_rate_limit,
            window_seconds=settings.account_rate_limit_window_seconds,
        )
    return _account_rate_limiter


def get_public_rate_limiter() -> SlidingWindowRateLimiter:
    """Return the process-wide limiter for the public dataset routes."""
    global _public_rate_limiter
    if _public_rate_limiter is None:
        settings = get_settings()
        _public_rate_limiter = SlidingWindowRateLimiter(
            limit=settings.dataset_rate_limit,
            window_seconds=settings.dataset_rate_limit_window_seconds,
        )
    return _public_rate_limiter


async def get_dataset_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DatasetService:
    """Build the public dataset service for a request."""
    return DatasetService(DatasetRepository(session))


async def get_export_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ExportService:
    """Build the CC0 export service for a request. It reads the same public store."""
    return ExportService(DatasetRepository(session))


async def get_upload_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UploadService:
    """Build the upload service for a request."""
    settings = get_settings()
    return UploadService(
        vision=get_vision_provider(),
        sessions=get_extract_sessions(),
        lab_results=LabResultRepository(session),
        max_upload_bytes=settings.max_upload_bytes,
        budget=get_gemini_budget(),
    )


async def dispose_engine() -> None:
    """Dispose the engine, RAM extract sessions, rate limiters, news cache, and Gemini budget."""
    global _engine, _session_factory, _extract_sessions, _vision_provider, _public_rate_limiter
    global _gemini_budget, _news_service, _news_rate_limiter
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
    if _extract_sessions is not None:
        _extract_sessions.clear()
    _extract_sessions = None
    _vision_provider = None
    _public_rate_limiter = None
    _news_rate_limiter = None
    if _news_service is not None:
        _news_service.clear()
    _news_service = None
    _gemini_budget = None
