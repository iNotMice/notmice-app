"""FastAPI dependencies. Wiring only — no business logic."""

from collections.abc import AsyncIterator
from datetime import timedelta
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
from app.core.security import Argon2PasswordHasher, Argon2SeedHasher
from app.repositories.dataset import DatasetRepository
from app.repositories.health import HealthRepository
from app.repositories.lab_results import LabResultRepository
from app.repositories.protocol import ProtocolRepository
from app.repositories.users import UserRepository
from app.services.accounts import AccountService
from app.services.dataset import DatasetService
from app.services.export import ExportService
from app.services.extract_sessions import InMemoryExtractSessionStore
from app.services.gemini_budget import GeminiTokenBudget
from app.services.health import HealthService
from app.services.image_redact import TesseractImageRedactor
from app.services.mailer import DevLoggingMailer, Mailer, SmtpMailer
from app.services.news import HttpxTextFetcher, NewsMemoryCache, NewsService
from app.services.protocol import ProtocolService
from app.services.redaction_holds import RedactionHoldStore
from app.services.uploads import UploadService
from app.services.vision import ExtractionProvider, build_extraction_provider

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_extract_sessions: InMemoryExtractSessionStore | None = None
_redaction_holds: RedactionHoldStore | None = None
_image_redactor: TesseractImageRedactor | None = None
_vision_provider: ExtractionProvider | None = None
_public_rate_limiter: SlidingWindowRateLimiter | None = None
_account_rate_limiter: SlidingWindowRateLimiter | None = None
_account_identity_rate_limiter: SlidingWindowRateLimiter | None = None
_password_hasher: Argon2PasswordHasher | None = None
_mailer: Mailer | None = None
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
        passwords=get_password_hasher(),
        mailer=get_mailer(),
        auth_seed_enabled=settings.auth_seed_enabled,
        app_url=settings.public_app_url,
        token_ttl=timedelta(seconds=settings.auth_token_ttl_seconds),
        session_ttl=timedelta(seconds=settings.access_token_ttl_seconds),
    )


def get_extract_sessions() -> InMemoryExtractSessionStore:
    """Return the process-wide in-memory extract session store."""
    global _extract_sessions
    if _extract_sessions is None:
        _extract_sessions = InMemoryExtractSessionStore(get_settings().extract_session_ttl_seconds)
    return _extract_sessions


def get_redaction_holds() -> RedactionHoldStore:
    """Return the process-wide store of painted frames waiting on a person."""
    global _redaction_holds
    if _redaction_holds is None:
        _redaction_holds = RedactionHoldStore(get_settings().extract_session_ttl_seconds)
    return _redaction_holds


def get_image_redactor() -> TesseractImageRedactor:
    """Return the process-wide local painter. It does not call Gemini."""
    global _image_redactor
    if _image_redactor is None:
        _image_redactor = TesseractImageRedactor()
    return _image_redactor


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
    """Return the process-wide limiter for account routes, 20 hits per IP."""
    global _account_rate_limiter
    if _account_rate_limiter is None:
        settings = get_settings()
        _account_rate_limiter = SlidingWindowRateLimiter(
            limit=settings.account_rate_limit,
            window_seconds=settings.account_rate_limit_window_seconds,
        )
    return _account_rate_limiter


def get_account_identity_rate_limiter() -> SlidingWindowRateLimiter:
    """Return the process-wide limiter for one account, 5 hits per window."""
    global _account_identity_rate_limiter
    if _account_identity_rate_limiter is None:
        settings = get_settings()
        _account_identity_rate_limiter = SlidingWindowRateLimiter(
            limit=settings.account_identity_rate_limit,
            window_seconds=settings.account_identity_rate_limit_window_seconds,
        )
    return _account_identity_rate_limiter


def get_password_hasher() -> Argon2PasswordHasher:
    """Return the process-wide password hasher. The dummy hash is built on first use."""
    global _password_hasher
    if _password_hasher is None:
        _password_hasher = Argon2PasswordHasher()
    return _password_hasher


def get_mailer() -> Mailer:
    """Return SMTP when it is configured, otherwise a log sink."""
    global _mailer
    if _mailer is None:
        settings = get_settings()
        if settings.smtp_host.strip():
            _mailer = SmtpMailer(
                host=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username,
                password=settings.smtp_password,
                sender=settings.smtp_from or settings.smtp_username,
                use_tls=settings.smtp_use_tls,
            )
        else:
            _mailer = DevLoggingMailer(
                reveal_link=settings.app_env.strip().casefold() != "production"
            )
    return _mailer


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


async def get_protocol_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProtocolService:
    """Build the protocol journal service for a request."""
    return ProtocolService(ProtocolRepository(session))


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
        image_redactor=get_image_redactor(),
        redaction_holds=get_redaction_holds(),
    )


async def dispose_engine() -> None:
    """Dispose the engine, RAM extract sessions, rate limiters, news cache, and Gemini budget."""
    global _engine, _session_factory, _extract_sessions, _vision_provider, _public_rate_limiter
    global _gemini_budget, _news_service, _news_rate_limiter, _redaction_holds, _image_redactor
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
    if _extract_sessions is not None:
        _extract_sessions.clear()
    _extract_sessions = None
    if _redaction_holds is not None:
        _redaction_holds.clear()
    _redaction_holds = None
    _image_redactor = None
    _vision_provider = None
    _public_rate_limiter = None
    _news_rate_limiter = None
    if _news_service is not None:
        _news_service.clear()
    _news_service = None
    _gemini_budget = None
