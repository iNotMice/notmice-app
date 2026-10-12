"""A provider quota answer is reported as "temporarily unavailable" and is not retried."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import HTTPException

from app.api.uploads import _http_for
from app.domain.uploads import VisionQuotaError
from app.services.provider_errors import is_quota_error
from app.services.vision import GeminiExtractionProvider

_GEMINI_429 = "429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'quota'}}"


def test_quota_text_is_recognized() -> None:
    """The google-genai 429 text is a quota error; other provider errors are not."""
    assert is_quota_error(RuntimeError(_GEMINI_429))
    assert not is_quota_error(RuntimeError("503 UNAVAILABLE. The model is overloaded."))


async def test_lab_report_reading_stops_at_the_first_quota_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One call, then a quota error; the remaining quota is not spent on retries."""
    provider = GeminiExtractionProvider(api_key="test-key", model="gemini-3.8-flash")
    calls: list[int] = []

    async def refuse(*_args: Any, **_kwargs: Any) -> Any:
        calls.append(1)
        raise RuntimeError(_GEMINI_429)

    monkeypatch.setattr(provider, "_once", refuse)
    with pytest.raises(VisionQuotaError):
        await provider.extract_from_text("Albumin 45 g/L")
    assert calls == [1]


def test_quota_error_maps_to_temporarily_unavailable() -> None:
    """The screen gets a fixed sentence it can translate, with a 503 status."""
    error = _http_for(VisionQuotaError("Gemini quota exhausted"))
    assert isinstance(error, HTTPException)
    assert error.status_code == 503
    assert error.detail == "Recognition is temporarily unavailable"
