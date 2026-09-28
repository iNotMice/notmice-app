"""Account HTTP surface."""

from __future__ import annotations

import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.deps import (
    get_account_identity_rate_limiter,
    get_account_rate_limiter,
    get_account_service,
)
from app.core.rate_limit import SlidingWindowRateLimiter, resolve_client_key
from app.core.security import normalize_mnemonic
from app.domain.accounts import (
    AccountError,
    AccountNotFoundError,
    AuthenticatedSession,
    ConsentRequiredError,
    ConsentVersionError,
    InvalidAuthTokenError,
    InvalidCredentialsError,
    InvalidMnemonicError,
    UnauthenticatedError,
    UserRecord,
    normalize_email,
)
from app.domain.consents import ConsentChoice
from app.domain.pii import PIIValidationError, reject_pii
from app.domain.schemas import (
    AccountLoginRequest,
    AccountRegisterRequest,
    AccountRegisterResponse,
    AccountSessionResponse,
    AccountView,
    AuthTokenRequest,
    ConsentInput,
    ConsentListResponse,
    ConsentView,
    EmailLoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    ShareSettingsUpdate,
)
from app.services.accounts import AccountService

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])
_bearer = HTTPBearer(auto_error=False)


async def enforce_account_rate_limit(
    request: Request,
    response: Response,
    limiter: Annotated[SlidingWindowRateLimiter, Depends(get_account_rate_limiter)],
) -> None:
    """Limit account creation and login by client IP. Argon2 makes each login expensive."""
    settings = get_settings()
    key = resolve_client_key(
        real_ip=request.headers.get("x-real-ip"),
        client_host=request.client.host if request.client is not None else None,
        trust_proxy=settings.trust_proxy_headers,
    )
    decision = await limiter.hit(key)
    response.headers["X-RateLimit-Limit"] = str(decision.limit)
    response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(decision.retry_after_seconds),
                "X-RateLimit-Limit": str(decision.limit),
                "X-RateLimit-Remaining": "0",
            },
        )


def _identity_key(kind: str, value: str) -> str:
    """Bucket key that does not keep the raw address or phrase in the limiter."""
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"{kind}:{digest}"


async def _charge_identity(
    limiter: SlidingWindowRateLimiter,
    key: str,
    response: Response,
) -> None:
    """Count one attempt against an account bucket. The status does not identify the account."""
    decision = await limiter.hit(key)
    if decision.allowed:
        return
    response.headers["Retry-After"] = str(decision.retry_after_seconds)
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Rate limit exceeded",
        headers={"Retry-After": str(decision.retry_after_seconds)},
    )


def _choices(rows: list[ConsentInput]) -> tuple[ConsentChoice, ...]:
    """Map API consent rows onto the domain catalogue."""
    return tuple(
        ConsentChoice(consent_type=row.type, text_version=row.version, accepted=row.accepted)
        for row in rows
    )


def _parse_email(value: str) -> str:
    """Return a normalized address or a 422 that does not say whether it is registered."""
    try:
        return normalize_email(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid email address",
        ) from exc


def _session_response(session: AuthenticatedSession) -> AccountSessionResponse:
    """Map a service session onto the bearer response."""
    return AccountSessionResponse(
        public_id=session.user.public_id,
        is_public=session.user.is_public,
        created_at=session.user.created_at,
        access_token=session.access_token,
    )


def _email_http_for(exc: AccountError) -> HTTPException:
    """Map email-login failures onto one response."""
    if isinstance(exc, InvalidCredentialsError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return _http_for(exc)


def _http_for(exc: AccountError) -> HTTPException:
    """Map domain errors to HTTP responses without leaking identifiers.

    A malformed phrase and a valid unknown phrase share one status and one detail
    so the response does not say whether the checksum passed.
    """
    if isinstance(exc, InvalidAuthTokenError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )
    if isinstance(exc, ConsentRequiredError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Required consent is missing",
        )
    if isinstance(exc, ConsentVersionError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent version is not current",
        )
    if isinstance(exc, (InvalidMnemonicError, InvalidCredentialsError)):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid recovery phrase",
        )
    if isinstance(exc, (UnauthenticatedError, AccountNotFoundError)):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account request failed")


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> UserRecord:
    """Require a valid bearer token and return the current user."""
    token = credentials.credentials if credentials is not None else None
    try:
        return await account_service.authenticate(token)
    except AccountError as exc:
        raise _http_for(exc) from exc


@router.post(
    "",
    response_model=AccountRegisterResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def register_account(
    payload: AccountRegisterRequest,
    response: Response,
    account_service: Annotated[AccountService, Depends(get_account_service)],
    identity_limiter: Annotated[
        SlidingWindowRateLimiter, Depends(get_account_identity_rate_limiter)
    ],
    _: Annotated[None, Depends(enforce_account_rate_limit)],
) -> AccountRegisterResponse:
    """Register with email and password. The body does not say whether the address exists."""
    email = _parse_email(payload.email)
    await _charge_identity(identity_limiter, _identity_key("register", email), response)
    try:
        await account_service.register(
            email=email,
            password=payload.password,
            consents=_choices(payload.consents),
        )
    except AccountError as exc:
        raise _http_for(exc) from exc
    return AccountRegisterResponse()


@router.post("/confirm", response_model=AccountSessionResponse)
async def confirm_email(
    payload: AuthTokenRequest,
    account_service: Annotated[AccountService, Depends(get_account_service)],
    _: Annotated[None, Depends(enforce_account_rate_limit)],
) -> AccountSessionResponse:
    """Consume a one-time confirmation token and return a bearer token."""
    try:
        session = await account_service.confirm_email(payload.token)
    except AccountError as exc:
        raise _http_for(exc) from exc
    return _session_response(session)


@router.post("/login", response_model=AccountSessionResponse)
async def login(
    payload: AccountLoginRequest,
    response: Response,
    account_service: Annotated[AccountService, Depends(get_account_service)],
    identity_limiter: Annotated[
        SlidingWindowRateLimiter, Depends(get_account_identity_rate_limiter)
    ],
    _: Annotated[None, Depends(enforce_account_rate_limit)],
) -> AccountSessionResponse:
    """Sign in with the 12-word recovery phrase when seed login is enabled."""
    try:
        reject_pii(payload.model_dump())
        phrase = normalize_mnemonic(payload.mnemonic)
        await _charge_identity(identity_limiter, _identity_key("seed", phrase), response)
        session = await account_service.login(payload.mnemonic)
    except PIIValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Forbidden field",
        ) from exc
    except AccountError as exc:
        raise _http_for(exc) from exc
    return _session_response(session)


@router.post("/login/email", response_model=AccountSessionResponse)
async def login_email(
    payload: EmailLoginRequest,
    response: Response,
    account_service: Annotated[AccountService, Depends(get_account_service)],
    identity_limiter: Annotated[
        SlidingWindowRateLimiter, Depends(get_account_identity_rate_limiter)
    ],
    _: Annotated[None, Depends(enforce_account_rate_limit)],
) -> AccountSessionResponse:
    """Sign in with email and password. Failures share one response."""
    email = _parse_email(payload.email)
    await _charge_identity(identity_limiter, _identity_key("login", email), response)
    try:
        session = await account_service.login_email(email, payload.password)
    except AccountError as exc:
        raise _email_http_for(exc) from exc
    return _session_response(session)


@router.post(
    "/password-reset",
    response_model=AccountRegisterResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_password_reset(
    payload: PasswordResetRequest,
    response: Response,
    account_service: Annotated[AccountService, Depends(get_account_service)],
    identity_limiter: Annotated[
        SlidingWindowRateLimiter, Depends(get_account_identity_rate_limiter)
    ],
    _: Annotated[None, Depends(enforce_account_rate_limit)],
) -> AccountRegisterResponse:
    """Send a reset link when the address is confirmed. The body does not say which."""
    email = _parse_email(payload.email)
    await _charge_identity(identity_limiter, _identity_key("reset", email), response)
    await account_service.request_password_reset(email)
    return AccountRegisterResponse()


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    account_service: Annotated[AccountService, Depends(get_account_service)],
    _: Annotated[None, Depends(enforce_account_rate_limit)],
) -> None:
    """Set a new password with a one-time token."""
    try:
        await account_service.reset_password(payload.token, payload.password)
    except AccountError as exc:
        raise _http_for(exc) from exc
    return None


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    _current: Annotated[UserRecord, Depends(get_current_user)],
) -> None:
    """Acknowledge logout. Tokens are stateless; the client must discard them."""
    return None


@router.get("/me", response_model=AccountView)
async def read_me(
    current: Annotated[UserRecord, Depends(get_current_user)],
) -> AccountView:
    """Return the current account. Never includes the recovery phrase."""
    return AccountView(
        public_id=current.public_id,
        is_public=current.is_public,
        created_at=current.created_at,
    )


@router.get("/me/consents", response_model=ConsentListResponse)
async def read_consents(
    current: Annotated[UserRecord, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> ConsentListResponse:
    """Return consent rows for the signed-in participant."""
    rows = await account_service.list_consents(current.id)
    return ConsentListResponse(
        consents=[
            ConsentView(
                type=row.consent_type,
                version=row.text_version,
                granted_at=row.granted_at,
                withdrawn_at=row.withdrawn_at,
            )
            for row in rows
        ]
    )


@router.post("/me/consents", response_model=ConsentView)
async def update_consent(
    payload: ConsentInput,
    current: Annotated[UserRecord, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> ConsentView:
    """Grant or withdraw one consent at the current text version."""
    try:
        row = await account_service.set_consent(current.id, _choices([payload])[0])
    except AccountError as exc:
        raise _http_for(exc) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Consent is not granted"
        )
    return ConsentView(
        type=row.consent_type,
        version=row.text_version,
        granted_at=row.granted_at,
        withdrawn_at=row.withdrawn_at,
    )


@router.get("/me/export.json")
async def export_account_json(
    current: Annotated[UserRecord, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> Response:
    """Download the signed-in account as JSON."""
    try:
        body = await account_service.export_json(current.id)
    except AccountError as exc:
        raise _http_for(exc) from exc
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="notmice-account.json"'},
    )


@router.get("/me/export.csv")
async def export_account_csv(
    current: Annotated[UserRecord, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> Response:
    """Download the signed-in analytes as CSV."""
    try:
        body = await account_service.export_csv(current.id)
    except AccountError as exc:
        raise _http_for(exc) from exc
    return Response(
        content=body,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="notmice-account.csv"'},
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    current: Annotated[UserRecord, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> None:
    """Delete the signed-in account and the rows that cascade from it."""
    try:
        await account_service.delete_account(current.id)
    except AccountError as exc:
        raise _http_for(exc) from exc
    return None


@router.patch("/me/share", response_model=AccountView)
async def update_share(
    payload: ShareSettingsUpdate,
    current: Annotated[UserRecord, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> AccountView:
    """Set the opt-in public sharing flag in ``share_settings``."""
    try:
        reject_pii(payload.model_dump())
        updated = await account_service.set_public(current.id, payload.is_public)
    except PIIValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Forbidden field",
        ) from exc
    except AccountError as exc:
        raise _http_for(exc) from exc
    return AccountView(
        public_id=updated.public_id,
        is_public=updated.is_public,
        created_at=updated.created_at,
    )
