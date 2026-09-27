"""Pseudonymous account HTTP surface."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.deps import get_account_rate_limiter, get_account_service
from app.core.rate_limit import SlidingWindowRateLimiter, resolve_client_key
from app.domain.accounts import (
    AccountError,
    AccountNotFoundError,
    InvalidCredentialsError,
    InvalidMnemonicError,
    UnauthenticatedError,
    UserRecord,
)
from app.domain.pii import PIIValidationError, reject_pii
from app.domain.schemas import (
    AccountCreatedResponse,
    AccountCreateRequest,
    AccountLoginRequest,
    AccountSessionResponse,
    AccountView,
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


def _http_for(exc: AccountError) -> HTTPException:
    """Map domain errors to HTTP responses without leaking identifiers.

    A malformed phrase and a valid unknown phrase share one status and one detail
    so the response does not say whether the checksum passed.
    """
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
    response_model=AccountCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_account(
    account_service: Annotated[AccountService, Depends(get_account_service)],
    _: Annotated[None, Depends(enforce_account_rate_limit)],
    payload: Annotated[AccountCreateRequest | None, Body()] = None,
) -> AccountCreatedResponse:
    """Create a pseudonymous participant. The BIP-39 phrase is returned once."""
    body = payload if payload is not None else AccountCreateRequest()
    try:
        reject_pii(body.model_dump())
    except PIIValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Forbidden field",
        ) from exc
    created = await account_service.create()
    return AccountCreatedResponse(
        public_id=created.user.public_id,
        is_public=created.user.is_public,
        created_at=created.user.created_at,
        access_token=created.access_token,
        mnemonic=created.mnemonic,
    )


@router.post("/login", response_model=AccountSessionResponse)
async def login(
    payload: AccountLoginRequest,
    account_service: Annotated[AccountService, Depends(get_account_service)],
    _: Annotated[None, Depends(enforce_account_rate_limit)],
) -> AccountSessionResponse:
    """Sign in with the 12-word recovery phrase."""
    try:
        reject_pii(payload.model_dump())
        session = await account_service.login(payload.mnemonic)
    except PIIValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Forbidden field",
        ) from exc
    except AccountError as exc:
        raise _http_for(exc) from exc
    return AccountSessionResponse(
        public_id=session.user.public_id,
        is_public=session.user.is_public,
        created_at=session.user.created_at,
        access_token=session.access_token,
    )


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
