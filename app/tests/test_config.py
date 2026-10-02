"""Runtime secret checks."""

from __future__ import annotations

import pytest

from app.core.config import (
    InsecureSecretError,
    MailNotConfiguredError,
    Settings,
    get_settings,
    validate_mail_config,
    validate_runtime_secrets,
)
from app.main import create_app, lifespan

_PROD_SEED = "prod-seed-hash-secret-32-characters-min"
_PROD_JWT = "prod-jwt-signing-secret-32-characters!"


def test_development_accepts_distinct_dev_defaults() -> None:
    """Local defaults differ and are allowed when APP_ENV is not production."""
    validate_runtime_secrets(Settings(app_env="development"))


def test_secrets_must_differ_outside_production() -> None:
    """One shared value cannot pepper the seed hash and sign JWTs."""
    settings = Settings(
        app_env="development",
        seed_hash_secret="same-secret-value-used-for-both-purposes",
        jwt_secret="same-secret-value-used-for-both-purposes",
    )
    with pytest.raises(InsecureSecretError, match="different"):
        validate_runtime_secrets(settings)


def test_empty_secret_is_rejected() -> None:
    """A blank pepper or signing key is never acceptable."""
    settings = Settings(app_env="development", seed_hash_secret="   ", jwt_secret=_PROD_JWT)
    with pytest.raises(InsecureSecretError, match="required"):
        validate_runtime_secrets(settings)


def test_production_rejects_dev_insecure_defaults() -> None:
    """The dev-insecure prefix, including the old shared default, cannot boot in production."""
    defaults = Settings(app_env="production")
    with pytest.raises(InsecureSecretError, match="SEED_HASH_SECRET"):
        validate_runtime_secrets(defaults)
    legacy = Settings(
        app_env="production",
        seed_hash_secret="dev-insecure-change-me-not-for-prod",
        jwt_secret=_PROD_JWT,
    )
    with pytest.raises(InsecureSecretError, match="SEED_HASH_SECRET"):
        validate_runtime_secrets(legacy)


def test_production_rejects_short_secret() -> None:
    """Production secrets shorter than 32 characters are refused."""
    settings = Settings(
        app_env="production",
        seed_hash_secret="short-but-not-default",
        jwt_secret=_PROD_JWT,
    )
    with pytest.raises(InsecureSecretError, match="SEED_HASH_SECRET"):
        validate_runtime_secrets(settings)


def test_session_cookie_is_secure_only_in_production() -> None:
    """Local HTTP can store the cookie. Production marks it Secure."""
    assert Settings(app_env="development").session_cookie_secure is False
    assert (
        Settings(
            app_env="production",
            seed_hash_secret=_PROD_SEED,
            jwt_secret=_PROD_JWT,
        ).session_cookie_secure
        is True
    )


def test_production_accepts_distinct_long_secrets() -> None:
    """Two different long secrets are enough for a production boot."""
    validate_runtime_secrets(
        Settings(app_env="production", seed_hash_secret=_PROD_SEED, jwt_secret=_PROD_JWT)
    )


def test_mail_config_allows_non_production_without_smtp() -> None:
    """Development keeps the log sink and never requires SMTP."""
    validate_mail_config(Settings(app_env="development"))


def test_mail_config_requires_smtp_host_in_production() -> None:
    """Production must not boot when outbound mail is unconfigured."""
    settings = Settings(
        app_env="production",
        seed_hash_secret=_PROD_SEED,
        jwt_secret=_PROD_JWT,
        smtp_host="",
        public_app_url="https://notmice.com",
    )
    with pytest.raises(MailNotConfiguredError, match="SMTP_HOST"):
        validate_mail_config(settings)


def test_mail_config_rejects_localhost_app_url_in_production() -> None:
    """A confirmation link must not point at localhost in production."""
    settings = Settings(
        app_env="production",
        seed_hash_secret=_PROD_SEED,
        jwt_secret=_PROD_JWT,
        smtp_host="smtp.example.com",
        public_app_url="http://localhost:8080",
    )
    with pytest.raises(MailNotConfiguredError, match="PUBLIC_APP_URL"):
        validate_mail_config(settings)


def test_mail_config_accepts_configured_production() -> None:
    """A real SMTP host and https origin satisfy the production check."""
    validate_mail_config(
        Settings(
            app_env="production",
            seed_hash_secret=_PROD_SEED,
            jwt_secret=_PROD_JWT,
            smtp_host="smtp.example.com",
            public_app_url="https://notmice.com",
        )
    )


async def test_lifespan_refuses_insecure_production_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The process does not start when production is configured with dev secrets."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SEED_HASH_SECRET", "dev-insecure-seed-hash-change-me-not-for-prod")
    monkeypatch.setenv("JWT_SECRET", "dev-insecure-jwt-signing-change-me-not-for-prod")
    get_settings.cache_clear()
    application = create_app()
    try:
        with pytest.raises(InsecureSecretError):
            async with lifespan(application):
                pass
    finally:
        get_settings.cache_clear()
