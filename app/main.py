"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.accounts import router as accounts_router
from app.api.dataset import router as dataset_router
from app.api.exports import router as exports_router
from app.api.health import router as health_router
from app.api.news import router as news_router
from app.api.phenoage import router as phenoage_router
from app.api.protocol import router as protocol_router
from app.api.uploads import gemini_budget_exhausted_handler
from app.api.uploads import router as uploads_router
from app.core.config import get_settings, validate_mail_config, validate_runtime_secrets
from app.core.deps import dispose_engine
from app.core.logging import configure_logging
from app.domain.uploads import GeminiBudgetExhaustedError

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Configure logging on startup and dispose the database engine on shutdown."""
    settings = get_settings()
    configure_logging(settings.log_level)
    validate_runtime_secrets(settings)
    validate_mail_config(settings)
    logger.info("api_start")
    yield
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
    application.include_router(uploads_router)
    application.include_router(protocol_router)
    application.include_router(phenoage_router)
    application.include_router(dataset_router)
    application.include_router(exports_router)
    return application


app = create_app()
