"""Runtime configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Local and CI defaults. Production startup rejects this prefix and anything shorter than 32.
_DEV_SEED_HASH_SECRET = "dev-insecure-seed-hash-change-me-not-for-prod"
_DEV_JWT_SECRET = "dev-insecure-jwt-signing-change-me-not-for-prod"
_INSECURE_SECRET_PREFIX = "dev-insecure"
_MIN_PRODUCTION_SECRET_LENGTH = 32


class InsecureSecretError(RuntimeError):
    """Raised when seed-hash and JWT secrets are missing, shared, or unsafe to boot."""


class MailNotConfiguredError(RuntimeError):
    """Raised when production boots without usable outbound mail configuration."""


class Settings(BaseSettings):
    """Process settings. Unknown env keys are ignored so frontend secrets do not break boot."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://notmice:notmice@localhost:5432/notmice"
    cors_origins: str = "http://localhost:3000,http://localhost:8080"
    log_level: str = "INFO"
    seed_hash_secret: str = _DEV_SEED_HASH_SECRET
    jwt_secret: str = _DEV_JWT_SECRET
    access_token_ttl_seconds: int = 43_200
    vision_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_daily_token_budget: int = 2_000_000
    gemini_user_daily_token_budget: int = 100_000
    gemini_ip_daily_token_budget: int = 150_000
    gemini_call_token_reserve: int = 16_000
    gemini_user_daily_calls: int = 8
    gemini_ip_daily_calls: int = 12
    gemini_budget_warn_ratio: float = 0.8
    gemini_timeout_seconds: int = 60
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-5"
    max_upload_bytes: int = 15_728_640
    extract_session_ttl_seconds: int = 1_800
    auth_seed_enabled: bool = True
    survey_enabled: bool = False
    auth_token_ttl_seconds: int = 88_200
    public_app_url: str = "http://localhost:8080"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    account_rate_limit: int = 20
    account_rate_limit_window_seconds: int = 900
    account_identity_rate_limit: int = 5
    account_identity_rate_limit_window_seconds: int = 900
    dataset_rate_limit: int = 60
    dataset_rate_limit_window_seconds: int = 60
    news_rate_limit: int = 30
    news_rate_limit_window_seconds: int = 60
    news_cache_ttl_seconds: int = 3600
    news_pubmed_retmax: int = 12
    news_snippet_max_chars: int = 420
    news_contact_email: str = ""
    news_rss_feeds: str = "https://www.fightaging.org/feed/,https://www.lifespan.io/feed/"
    trust_proxy_headers: bool = True

    @property
    def session_cookie_secure(self) -> bool:
        """Return True when the session cookie must be Secure.

        Production is served over HTTPS. Local compose is HTTP, and a Secure
        cookie would never be stored by the browser there.
        """
        return self.app_env.strip().casefold() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        """Return CORS origins as a stripped list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def news_rss_feed_list(self) -> list[str]:
        """Return the publisher RSS allowlist. Empty entries are dropped."""
        return [feed.strip() for feed in self.news_rss_feeds.split(",") if feed.strip()]


def validate_runtime_secrets(settings: Settings) -> None:
    """Refuse to boot when the seed pepper and JWT secret are missing or interchangeable.

    Both values are always required and must differ. ``APP_ENV=production`` also rejects
    an empty value, a value shorter than 32 characters, and any value that still uses the
    ``dev-insecure`` prefix (including ``dev-insecure-change-me-not-for-prod``).
    Local compose and CI stay on a non-production ``APP_ENV`` and may keep the dev defaults.

    Args:
        settings: Process settings already loaded from the environment.

    Raises:
        InsecureSecretError: If the secrets cannot be used for this environment.
    """
    seed = settings.seed_hash_secret
    token = settings.jwt_secret
    if not seed.strip() or not token.strip():
        raise InsecureSecretError("SEED_HASH_SECRET and JWT_SECRET are required")
    if seed == token:
        raise InsecureSecretError("SEED_HASH_SECRET and JWT_SECRET must be different")
    if settings.app_env.strip().casefold() != "production":
        return
    for name, value in (("SEED_HASH_SECRET", seed), ("JWT_SECRET", token)):
        insecure_default = value.startswith(_INSECURE_SECRET_PREFIX) or (
            value == "dev-insecure-change-me-not-for-prod"
        )
        if len(value) < _MIN_PRODUCTION_SECRET_LENGTH or insecure_default:
            raise InsecureSecretError(
                f"{name} must be at least 32 characters and must not use a dev-insecure default"
            )


def validate_mail_config(settings: Settings) -> None:
    """Refuse to boot in production unless confirmation mail can actually be sent.

    Non-production environments keep the development mail sink and are left untouched.
    Production requires ``SMTP_HOST`` and an https ``PUBLIC_APP_URL`` that is not localhost.
    A localhost or http link would be written into the confirmation message.

    Args:
        settings: Process settings already loaded from the environment.

    Raises:
        MailNotConfiguredError: Production is missing SMTP_HOST or a real https PUBLIC_APP_URL.
    """
    if settings.app_env.strip().casefold() != "production":
        return
    if not settings.smtp_host.strip():
        raise MailNotConfiguredError(
            "SMTP_HOST is required in production so confirmation mail is sent"
        )
    app_url = settings.public_app_url.strip()
    if not app_url or "localhost" in app_url or app_url.startswith("http://"):
        raise MailNotConfiguredError("PUBLIC_APP_URL must be the real https origin in production")


def validate_survey_config(settings: Settings) -> None:
    """Keep participant survey collection disabled until its consent is approved.

    Args:
        settings: Process settings already loaded from the environment.

    Raises:
        RuntimeError: Survey collection is enabled before a current consent version exists.
    """
    if not settings.survey_enabled:
        return
    from app.domain.consents import PARTICIPANT_PROFILE_VERSION

    if PARTICIPANT_PROFILE_VERSION is None:
        raise RuntimeError("SURVEY_ENABLED requires an approved PARTICIPANT_PROFILE_VERSION")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
