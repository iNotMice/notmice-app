"""Laboratory-only registration, sessions, and verified-organization gates."""

from __future__ import annotations

import hashlib
from html import escape
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse

from app.api.accounts import _charge_identity, enforce_account_rate_limit
from app.core.config import get_settings
from app.core.deps import get_account_identity_rate_limiter, get_lab_account_service
from app.core.rate_limit import SlidingWindowRateLimiter
from app.domain.lab_accounts import (
    LabAccountError,
    LabAuthTokenError,
    LabDuaUnavailableError,
    LabInvalidCredentialsError,
    LabOrganizationAccessError,
    LabUnauthenticatedError,
    LabUserRecord,
    normalized_lab_email,
)
from app.domain.schemas import (
    AccountRegisterResponse,
    LabAccountView,
    LabConfirmRequest,
    LabDuaAcceptRequest,
    LabLoginRequest,
    LabRegisterRequest,
    lab_account_view,
)
from app.services.lab_accounts import LabAccountService

router = APIRouter(prefix="/api/v1/lab", tags=["laboratory accounts"])
LAB_SESSION_COOKIE_NAME = "notmice_lab_session"


def _set_lab_session_cookie(response: Response, token: str) -> None:
    """Set a host-only HttpOnly laboratory cookie."""
    settings = get_settings()
    response.set_cookie(
        key=LAB_SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.access_token_ttl_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
        path="/",
    )


def _clear_lab_session_cookie(response: Response) -> None:
    """Clear the laboratory cookie with matching security flags."""
    settings = get_settings()
    response.delete_cookie(
        key=LAB_SESSION_COOKIE_NAME,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
        path="/",
    )


def _lab_view(user: LabUserRecord) -> LabAccountView:
    """Convert an authenticated lab identity to its private API representation."""
    if user.email_confirmed_at is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Laboratory email confirmation is required",
        )
    return lab_account_view(
        email=user.email,
        role=user.role,
        email_confirmed_at=user.email_confirmed_at,
        organization=user.organization,
    )


def _confirmation_page(token: str) -> HTMLResponse:
    """Render a same-origin button page; mail scanners cannot consume the token."""
    escaped_token = escape(token, quote=True)
    body = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Confirm laboratory email</title>
<body style="font:16px system-ui,sans-serif;max-width:36rem;margin:10vh auto;padding:1rem">
<h1>Confirm laboratory email</h1>
<p id="message">Select the button to confirm this address. The link is single-use.</p>
<button id="confirm" type="button" data-token="{escaped_token}">Confirm email</button>
<script>
history.replaceState(null, "", location.pathname);
const button = document.getElementById("confirm");
button.addEventListener("click", async () => {{
  button.disabled = true;
  try {{
    const response = await fetch(location.pathname, {{
      method: "POST",
      credentials: "same-origin",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{ token: button.dataset.token }})
    }});
    document.getElementById("message").textContent = response.ok
      ? "Email confirmed. Manual verification and an approved DUA are still required."
      : "This confirmation link is invalid, expired, or already used.";
    button.remove();
  }} catch {{
    button.disabled = false;
    document.getElementById("message").textContent = "Server unavailable. Try confirmation again.";
  }}
}});
</script>
</body>
</html>"""
    return HTMLResponse(
        content=body,
        headers={
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": (
                "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
            ),
        },
    )


def _http_for(exc: LabAccountError) -> HTTPException:
    """Map lab auth and organization-gate failures to explicit HTTP responses."""
    if isinstance(exc, (LabUnauthenticatedError, LabInvalidCredentialsError)):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid laboratory authentication",
        )
    if isinstance(exc, LabAuthTokenError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired confirmation token",
        )
    if isinstance(exc, LabDuaUnavailableError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The current laboratory agreement has not been approved",
        )
    if isinstance(exc, LabOrganizationAccessError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization verification and current DUA acceptance are required",
        )
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Laboratory account request failed",
    )


async def get_current_lab_user(
    request: Request,
    service: Annotated[LabAccountService, Depends(get_lab_account_service)],
) -> LabUserRecord:
    """Authenticate the laboratory cookie without granting data access."""
    try:
        return await service.authenticate(request.cookies.get(LAB_SESSION_COOKIE_NAME))
    except LabAccountError as exc:
        raise _http_for(exc) from exc


async def require_verified_lab(
    user: Annotated[LabUserRecord, Depends(get_current_lab_user)],
    service: Annotated[LabAccountService, Depends(get_lab_account_service)],
) -> LabUserRecord:
    """Require confirmed email, manually verified organization, and current DUA."""
    try:
        return await service.require_verified_dua(user)
    except LabAccountError as exc:
        raise _http_for(exc) from exc


@router.post(
    "/register",
    response_model=AccountRegisterResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(enforce_account_rate_limit)],
)
async def register_lab(
    payload: LabRegisterRequest,
    response: Response,
    service: Annotated[LabAccountService, Depends(get_lab_account_service)],
    identity_limiter: Annotated[
        SlidingWindowRateLimiter, Depends(get_account_identity_rate_limiter)
    ],
) -> AccountRegisterResponse:
    """Register a pending lab organization and email its first owner a confirmation link."""
    try:
        email = normalized_lab_email(payload.email)
        identity = hashlib.sha256(email.encode("utf-8")).hexdigest()
        await _charge_identity(identity_limiter, f"lab-register:{identity}", response)
        await service.register(
            name=payload.organization_name,
            org_type=payload.organization_type,
            country=payload.country,
            email=email,
            password=payload.password,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid laboratory registration values",
        ) from exc
    return AccountRegisterResponse()


@router.get("/confirm", response_class=HTMLResponse)
async def lab_confirmation_page(
    token: Annotated[str, Query(min_length=20, max_length=128)],
) -> HTMLResponse:
    """Present explicit confirmation without consuming tokens on email-link prefetch."""
    return _confirmation_page(token)


@router.post(
    "/confirm",
    response_model=LabAccountView,
    dependencies=[Depends(enforce_account_rate_limit)],
)
async def confirm_lab_email(
    payload: LabConfirmRequest,
    response: Response,
    service: Annotated[LabAccountService, Depends(get_lab_account_service)],
) -> LabAccountView:
    """Consume an email token and start the separate lab session."""
    try:
        user, token = await service.confirm_email(payload.token)
    except LabAccountError as exc:
        raise _http_for(exc) from exc
    _set_lab_session_cookie(response, token)
    return _lab_view(user)


@router.post(
    "/login",
    response_model=LabAccountView,
    dependencies=[Depends(enforce_account_rate_limit)],
)
async def login_lab(
    payload: LabLoginRequest,
    response: Response,
    service: Annotated[LabAccountService, Depends(get_lab_account_service)],
    identity_limiter: Annotated[
        SlidingWindowRateLimiter, Depends(get_account_identity_rate_limiter)
    ],
) -> LabAccountView:
    """Authenticate a lab member; verification/DUA is checked on data routes."""
    try:
        email = normalized_lab_email(payload.email)
        identity = hashlib.sha256(email.encode("utf-8")).hexdigest()
        await _charge_identity(identity_limiter, f"lab-login:{identity}", response)
        user, token = await service.login(email, payload.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid email address",
        ) from exc
    except LabAccountError as exc:
        raise _http_for(exc) from exc
    _set_lab_session_cookie(response, token)
    return _lab_view(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_lab(
    request: Request,
    response: Response,
    service: Annotated[LabAccountService, Depends(get_lab_account_service)],
) -> Response:
    """Revoke the lab session without affecting participant sessions."""
    await service.logout(request.cookies.get(LAB_SESSION_COOKIE_NAME))
    _clear_lab_session_cookie(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=LabAccountView)
async def read_lab_me(
    user: Annotated[LabUserRecord, Depends(get_current_lab_user)],
) -> LabAccountView:
    """Return only the authenticated lab user's organization and access state."""
    return _lab_view(user)


@router.post("/dua/accept", response_model=LabAccountView)
async def accept_lab_dua(
    payload: LabDuaAcceptRequest,
    user: Annotated[LabUserRecord, Depends(get_current_lab_user)],
    service: Annotated[LabAccountService, Depends(get_lab_account_service)],
) -> LabAccountView:
    """Record explicit DUA acceptance after the organization has been verified."""
    del payload
    try:
        updated = await service.accept_current_dua(user)
    except LabAccountError as exc:
        raise _http_for(exc) from exc
    return _lab_view(updated)
