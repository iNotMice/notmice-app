"""FastAPI application factory."""

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.accounts import router as accounts_router
from app.api.cabinet import router as cabinet_router
from app.api.dataset import router as dataset_router
from app.api.exports import router as exports_router
from app.api.health import router as health_router
from app.api.lab_accounts import router as lab_accounts_router
from app.api.lab_cohorts import router as lab_cohorts_router
from app.api.news import router as news_router
from app.api.phenoage import router as phenoage_router
from app.api.protocol import router as protocol_router
from app.api.survey import router as survey_router
from app.api.uploads import gemini_budget_exhausted_handler
from app.api.uploads import router as uploads_router
from app.core.config import (
    get_settings,
    validate_mail_config,
    validate_runtime_secrets,
    validate_survey_config,
)
from app.core.deps import dispose_engine, get_news_service, get_news_translation
from app.core.logging import configure_logging
from app.domain.uploads import GeminiBudgetExhaustedError
from app.services.news_prewarm import run_prewarm

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Configure logging, warm news translations, dispose the database engine on shutdown."""
    settings = get_settings()
    configure_logging(settings.log_level)
    validate_runtime_secrets(settings)
    validate_mail_config(settings)
    validate_survey_config(settings)
    logger.info("api_start")
    stop = asyncio.Event()
    prewarm: asyncio.Task[None] | None = None
    translation = get_news_translation()
    if translation.enabled:
        prewarm = asyncio.create_task(
            run_prewarm(
                get_news_service(),
                translation,
                interval_seconds=settings.news_prewarm_interval_seconds,
                stop=stop,
            )
        )
    yield
    stop.set()
    if prewarm is not None:
        prewarm.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await prewarm
    await dispose_engine()
    logger.info("api_stop")


def create_app() -> FastAPI:
    """Build the ASGI application."""
    settings = get_settings()
    application = FastAPI(
        title="NotMice API",
        version="0.1.0",
        openapi_version="3.1.0",
        lifespan=lifespan,
        license_info={"name": "AGPL-3.0-or-later"},
        description=(
            "Read-only public dataset routes return anonymized opt-in biomarker rows. "
            "CSV, Parquet, and the datasheet are CC0-1.0 snapshots of those rows. "
            "These routes do not accept writes."
        ),
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_exception_handler(
        GeminiBudgetExhaustedError,
        gemini_budget_exhausted_handler,
    )
    application.include_router(health_router)
    application.include_router(news_router)
    application.include_router(accounts_router)
    application.include_router(cabinet_router)
    application.include_router(lab_accounts_router)
    application.include_router(lab_cohorts_router)
    application.include_router(uploads_router)
    application.include_router(protocol_router)
    application.include_router(survey_router)
    application.include_router(phenoage_router)
    application.include_router(dataset_router)
    application.include_router(exports_router)
    return application


app = create_app()
