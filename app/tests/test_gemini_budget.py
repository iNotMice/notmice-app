"""Gemini token ledger: reserve, refund, missing usage, warning, and the global cap."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from structlog.testing import capture_logs

from app.domain.accounts import UserRecord
from app.domain.uploads import (
    CompletedExtract,
    GeminiBudgetExhaustedError,
    VisionNotConfiguredError,
)
from app.services.extract_sessions import InMemoryExtractSessionStore
from app.services.gemini_budget import GEMINI_MAX_ATTEMPTS, GeminiTokenBudget
from app.services.image_redact import PassthroughImageRedactor
from app.services.uploads import UploadService
from app.services.vision import ProviderExtraction, usage_token_count
from app.tests.test_uploads import FakeVision, InMemoryLabStore, _text_pdf


def _budget(**overrides: int | float) -> GeminiTokenBudget:
    values: dict[str, int | float] = {
        "daily_token_budget": 2_000_000,
        "user_daily_token_budget": 100_000,
        "ip_daily_token_budget": 150_000,
        "call_token_reserve": 10,
        "user_daily_calls": 8,
        "ip_daily_calls": 12,
        "warn_ratio": 0.8,
    }
    values.update(overrides)
    return GeminiTokenBudget(
        daily_token_budget=int(values["daily_token_budget"]),
        user_daily_token_budget=int(values["user_daily_token_budget"]),
        ip_daily_token_budget=int(values["ip_daily_token_budget"]),
        call_token_reserve=int(values["call_token_reserve"]),
        user_daily_calls=int(values["user_daily_calls"]),
        ip_daily_calls=int(values["ip_daily_calls"]),
        warn_ratio=float(values["warn_ratio"]),
    )


def test_second_reserve_does_not_pass() -> None:
    """Two holds cannot share a bucket that only fits one."""
    budget = _budget(
        daily_token_budget=50,
        user_daily_token_budget=50,
        ip_daily_token_budget=50,
    )
    user = uuid4()
    budget.reserve(user, "203.0.113.8")
    with pytest.raises(GeminiBudgetExhaustedError):
        budget.reserve(user, "203.0.113.8")


def test_commit_refunds_unused_reserve() -> None:
    """A measured bill smaller than the hold is written back to the user bucket."""
    budget = _budget(user_daily_token_budget=50, ip_daily_token_budget=50, daily_token_budget=50)
    user = uuid4()
    hold = budget.reserve(user, "203.0.113.8")
    usage = budget.commit(hold, 4)
    assert hold.tokens == 10 * GEMINI_MAX_ATTEMPTS
    assert usage.tokens_used == 4
    assert usage.tokens_limit == 50
    assert usage.warning is False
    budget.reserve(user, "203.0.113.8")


def test_missing_usage_keeps_the_reserve() -> None:
    """Absent usage metadata does not refund the hold."""
    budget = _budget(user_daily_token_budget=50, ip_daily_token_budget=50, daily_token_budget=50)
    hold = budget.reserve(uuid4(), "203.0.113.8")
    usage = budget.commit(hold, None)
    assert usage.tokens_used == hold.tokens


def test_warning_starts_at_eighty_percent() -> None:
    """The personal warning flag flips at the configured ratio."""
    under = _budget(
        user_daily_token_budget=100,
        ip_daily_token_budget=10_000,
        daily_token_budget=10_000,
    )
    under_usage = under.commit(under.reserve(uuid4(), "203.0.113.1"), 79)
    assert under_usage.warning is False
    over = _budget(
        user_daily_token_budget=100,
        ip_daily_token_budget=10_000,
        daily_token_budget=10_000,
    )
    over_usage = over.commit(over.reserve(uuid4(), "203.0.113.1"), 80)
    assert over_usage.warning is True
    assert over_usage.tokens_used == 80
    assert over_usage.tokens_limit == 100


def test_global_bucket_blocks_a_user_who_still_has_room() -> None:
    """A fresh account on a new IP still stops when the process budget is full."""
    budget = _budget(
        daily_token_budget=10 * GEMINI_MAX_ATTEMPTS,
        user_daily_token_budget=100_000,
        ip_daily_token_budget=150_000,
    )
    budget.reserve(uuid4(), "198.51.100.1")
    with pytest.raises(GeminiBudgetExhaustedError) as caught:
        budget.reserve(uuid4(), "198.51.100.2")
    assert caught.value.tokens_limit == 100_000
    assert caught.value.tokens_used == 0


def test_same_ip_shares_a_bucket_across_accounts() -> None:
    """A new seed phrase does not open a fresh IP allowance."""
    budget = _budget(
        daily_token_budget=10_000,
        user_daily_token_budget=10_000,
        ip_daily_token_budget=10 * GEMINI_MAX_ATTEMPTS,
    )
    budget.reserve(uuid4(), "203.0.113.10")
    with pytest.raises(GeminiBudgetExhaustedError):
        budget.reserve(uuid4(), "203.0.113.10")
    budget.reserve(uuid4(), "203.0.113.11")


def test_global_warning_is_logged_once() -> None:
    """Crossing 80% of the process budget emits one warning per UTC day."""
    budget = _budget(
        daily_token_budget=1_000,
        user_daily_token_budget=10_000,
        ip_daily_token_budget=10_000,
        user_daily_calls=20,
        ip_daily_calls=20,
    )
    user = uuid4()
    with capture_logs() as logs:
        budget.commit(budget.reserve(user, "203.0.113.9"), 800)
        budget.commit(budget.reserve(user, "203.0.113.9"), 20)
    warnings = [event for event in logs if event["event"] == "gemini_budget_warning"]
    assert len(warnings) == 1
    assert warnings[0]["tokens_limit"] == 1_000


def test_global_exhaustion_is_logged_once() -> None:
    """Reaching the process budget emits one exhaustion event."""
    budget = _budget(
        daily_token_budget=100,
        user_daily_token_budget=10_000,
        ip_daily_token_budget=10_000,
    )
    with capture_logs() as logs:
        budget.commit(budget.reserve(uuid4(), "203.0.113.9"), 100)
    assert any(event["event"] == "gemini_budget_exhausted" for event in logs)


def test_overage_above_the_reserve_is_charged() -> None:
    """Usage past the hold is added and the personal counter shows the real total."""
    budget = _budget(
        user_daily_token_budget=10_000,
        ip_daily_token_budget=10_000,
        daily_token_budget=10_000,
    )
    with capture_logs() as logs:
        usage = budget.commit(budget.reserve(uuid4(), "203.0.113.4"), 100)
    assert usage.tokens_used == 100
    assert any(
        event["event"] == "gemini_budget_overage" and event["extra_tokens"] == 70 for event in logs
    )


def test_gemini_response_schema_omits_additional_properties() -> None:
    """Gemini Developer API rejects additionalProperties on response_schema."""
    from app.domain.uploads import RawLabExtraction
    from app.services.vision import gemini_response_schema

    dumped = str(gemini_response_schema(RawLabExtraction))
    assert "additionalProperties" not in dumped
    assert "additional_properties" not in dumped


def test_usage_token_count_sums_parts_and_treats_gaps_as_unknown() -> None:
    """Prompt, candidates, and thoughts are the bill. A missing object is unknown."""
    metadata = SimpleNamespace(
        prompt_token_count=10,
        candidates_token_count=4,
        thoughts_token_count=1,
    )
    assert usage_token_count(metadata) == 15
    assert usage_token_count({"total_token_count": 9}) == 9
    assert usage_token_count(None) is None


@pytest.mark.asyncio
async def test_unconfigured_provider_releases_the_hold() -> None:
    """A provider that never calls Gemini returns the reserved calls and tokens."""

    class UnconfiguredVision(FakeVision):
        async def extract_from_media(self, payload: bytes, mime_type: str) -> ProviderExtraction:
            del payload, mime_type
            raise VisionNotConfiguredError("Vision provider is not configured")

    budget = _budget(user_daily_calls=1, ip_daily_calls=1)
    service = UploadService(
        vision=UnconfiguredVision(),
        sessions=InMemoryExtractSessionStore(ttl_seconds=60),
        lab_results=InMemoryLabStore(),
        max_upload_bytes=1_000_000,
        budget=budget,
        image_redactor=PassthroughImageRedactor(),
    )
    user = UserRecord(id=uuid4(), public_id="nmtest", is_public=False, created_at=datetime.now(UTC))
    jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 16
    with pytest.raises(VisionNotConfiguredError):
        await service.extract(user.id, jpeg, client_key="203.0.113.40")
    with pytest.raises(VisionNotConfiguredError):
        await service.extract(user.id, jpeg, client_key="203.0.113.40")


@pytest.mark.asyncio
async def test_text_extract_commits_measured_tokens() -> None:
    """Selectable PDF text still charges the measured Gemini usage."""
    vision = FakeVision(tokens_used=25)
    budget = _budget()
    service = UploadService(
        vision=vision,
        sessions=InMemoryExtractSessionStore(ttl_seconds=60),
        lab_results=InMemoryLabStore(),
        max_upload_bytes=1_000_000,
        budget=budget,
    )
    user = UserRecord(id=uuid4(), public_id="nmtest", is_public=False, created_at=datetime.now(UTC))
    payload = _text_pdf(
        "Serum Albumin 46.2 g/L  Creatinine 0.88 mg/dL  Glucose 84 mg/dL extra padding text"
    )
    completed = await service.extract(user.id, payload, client_key="203.0.113.41")
    assert isinstance(completed, CompletedExtract)
    assert vision.text_calls == 1
    assert completed.tokens_used == 25
    assert completed.warning is False
