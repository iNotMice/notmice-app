"""Public dataset reads: opt-in filtering, anonymized payloads, rate limit, OpenAPI 3.1."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.deps import get_dataset_service, get_public_rate_limiter
from app.core.rate_limit import SlidingWindowRateLimiter, resolve_client_key
from app.domain.dataset import ProfileNotPublicError, PublicBiomarkerRow
from app.domain.pii import SENSITIVE_OUTPUT_KEYS
from app.main import create_app
from app.repositories.dataset import public_biomarker_select
from app.services.dataset import DatasetService

_PUBLIC = "nmpublic0000000001"
_PRIVATE = "nmprivate000000001"
_ALBUMIN = Decimal("46.2")
_PRIVATE_GLUCOSE = Decimal("99.5")


def _row(
    public_id: str,
    *,
    collected_at: date | None,
    loinc_code: str,
    raw_name: str,
    value: Decimal,
    canonical_name: str | None = None,
    chronological_age: Decimal | None = Decimal("42.00"),
) -> PublicBiomarkerRow:
    return PublicBiomarkerRow(
        public_id=public_id,
        collected_at=collected_at,
        chronological_age=chronological_age,
        loinc_code=loinc_code,
        canonical_name=canonical_name,
        raw_name=raw_name,
        value=value,
        unit="g/L" if loinc_code == "1751-7" else "mg/dL",
        mapping_status="mapped",
    )


class InMemoryDatasetStore:
    """Opt-in filter used by service tests. Private and unconfirmed rows stay hidden."""

    def __init__(self) -> None:
        self.public_ids: dict[str, bool] = {}
        self.rows: list[tuple[bool, PublicBiomarkerRow]] = []

    def add_profile(self, public_id: str, *, is_public: bool) -> None:
        self.public_ids[public_id] = is_public

    def add_row(self, row: PublicBiomarkerRow, *, confirmed: bool) -> None:
        self.rows.append((confirmed, row))

    def _visible(self, public_id: str | None = None) -> list[PublicBiomarkerRow]:
        visible: list[PublicBiomarkerRow] = []
        for confirmed, row in self.rows:
            if not confirmed or not self.public_ids.get(row.public_id, False):
                continue
            if public_id is not None and row.public_id != public_id:
                continue
            visible.append(row)
        return visible

    async def count_public_biomarkers(self) -> int:
        return len(self._visible())

    async def list_public_biomarkers(
        self,
        *,
        limit: int,
        offset: int,
    ) -> tuple[PublicBiomarkerRow, ...]:
        return tuple(self._visible()[offset : offset + limit])

    async def public_profile_exists(self, public_id: str) -> bool:
        return self.public_ids.get(public_id, False)

    async def list_public_profile_biomarkers(
        self,
        public_id: str,
    ) -> tuple[PublicBiomarkerRow, ...]:
        return tuple(self._visible(public_id))


def _store() -> InMemoryDatasetStore:
    store = InMemoryDatasetStore()
    store.add_profile(_PUBLIC, is_public=True)
    store.add_profile(_PRIVATE, is_public=False)
    store.add_row(
        _row(
            _PUBLIC,
            collected_at=date(2025, 8, 12),
            loinc_code="1751-7",
            canonical_name="albumin",
            raw_name="Serum Albumin",
            value=_ALBUMIN,
        ),
        confirmed=True,
    )
    store.add_row(
        _row(
            _PUBLIC,
            collected_at=date(2025, 8, 12),
            loinc_code="2345-7",
            canonical_name="glucose",
            raw_name="Glucose",
            value=Decimal("90"),
        ),
        confirmed=True,
    )
    store.add_row(
        _row(
            _PUBLIC,
            collected_at=date(2024, 1, 2),
            loinc_code="1751-7",
            canonical_name="albumin",
            raw_name="Serum Albumin",
            value=Decimal("44"),
        ),
        confirmed=False,
    )
    store.add_row(
        _row(
            _PRIVATE,
            collected_at=date(2025, 8, 12),
            loinc_code="2345-7",
            canonical_name="glucose",
            raw_name="Glucose",
            value=_PRIVATE_GLUCOSE,
        ),
        confirmed=True,
    )
    return store


def _keys(payload: object) -> set[str]:
    found: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            found.add(str(key))
            found.update(_keys(value))
    elif isinstance(payload, list):
        for item in payload:
            found.update(_keys(item))
    return found


def test_public_select_omits_internal_identifiers() -> None:
    """The SQL projection is the anonymized column set, not the full tables."""
    names = {column.key for column in public_biomarker_select().selected_columns}
    assert names == {
        "public_id",
        "collected_at",
        "chronological_age",
        "loinc_code",
        "canonical_name",
        "raw_name",
        "value",
        "unit",
        "mapping_status",
    }
    compiled = str(
        public_biomarker_select().compile(compile_kwargs={"literal_binds": True})
    ).lower()
    assert "is_public" in compiled
    assert "public_sharing" in compiled
    assert "consents.text_version" in compiled
    assert "consents.withdrawn_at is null" in compiled
    assert "confirmed_at" in compiled
    assert "seed_phrase_hash" not in compiled
    assert "document_sha256" not in compiled


def test_resolve_client_key_ignores_forwarded_for() -> None:
    """Only X-Real-IP from the trusted proxy selects a bucket."""
    assert (
        resolve_client_key(real_ip="203.0.113.10", client_host="10.0.0.8", trust_proxy=True)
        == "203.0.113.10"
    )
    assert resolve_client_key(real_ip=None, client_host="10.0.0.8", trust_proxy=True) == "10.0.0.8"
    assert (
        resolve_client_key(real_ip="203.0.113.10", client_host="10.0.0.8", trust_proxy=False)
        == "10.0.0.8"
    )


async def test_rate_limiter_blocks_then_resets() -> None:
    """The third hit inside the window is refused; a later window is allowed."""
    clock = {"now": 1_000.0}

    def now() -> float:
        return clock["now"]

    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60, now=now)
    assert (await limiter.hit("203.0.113.10")).allowed is True
    assert (await limiter.hit("203.0.113.10")).allowed is True
    blocked = await limiter.hit("203.0.113.10")
    assert blocked.allowed is False
    assert blocked.retry_after_seconds >= 1
    assert (await limiter.hit("203.0.113.11")).allowed is True
    clock["now"] = 1_061.0
    assert (await limiter.hit("203.0.113.10")).allowed is True


async def test_dataset_hides_private_and_unconfirmed_rows() -> None:
    """Opt-out and unconfirmed analytes never enter the page."""
    page = await DatasetService(_store()).read_dataset(limit=100, offset=0)
    ids = {row.public_id for row in page.rows}
    values = {row.value for row in page.rows}
    assert ids == {_PUBLIC}
    assert _ALBUMIN in values
    assert _PRIVATE_GLUCOSE not in values
    assert Decimal("44") not in values
    assert page.total == 2


async def test_timeseries_groups_same_day_and_hides_private_profile() -> None:
    """Same-day markers share one point. A private id is indistinguishable from a missing one."""
    service = DatasetService(_store())
    series = await service.read_timeseries(_PUBLIC)
    assert series.public_id == _PUBLIC
    assert len(series.points) == 1
    assert len(series.points[0].markers) == 2
    with pytest.raises(ProfileNotPublicError):
        await service.read_timeseries(_PRIVATE)
    with pytest.raises(ProfileNotPublicError):
        await service.read_timeseries("nmdoesnotexist0001")


async def test_empty_public_profile_returns_no_points() -> None:
    """An opted-in profile with nothing confirmed is public and empty."""
    store = InMemoryDatasetStore()
    store.add_profile("nmempty00000000001", is_public=True)
    series = await DatasetService(store).read_timeseries("nmempty00000000001")
    assert series.points == ()


def _application(store: InMemoryDatasetStore, limiter: SlidingWindowRateLimiter) -> FastAPI:
    application = create_app()
    service = DatasetService(store)

    async def override_service() -> DatasetService:
        return service

    def override_limiter() -> SlidingWindowRateLimiter:
        return limiter

    application.dependency_overrides[get_dataset_service] = override_service
    application.dependency_overrides[get_public_rate_limiter] = override_limiter
    return application


async def test_get_dataset_is_anonymized_and_read_only() -> None:
    """DoD: opt-in appears, opt-out does not, and the JSON has no sensitive keys."""
    application = _application(
        _store(),
        SlidingWindowRateLimiter(limit=20, window_seconds=60),
    )
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/dataset")
        post = await client.post("/api/v1/dataset", json={"rows": []})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {row["public_id"] for row in body["rows"]} == {_PUBLIC}
    rendered = response.text
    assert "99.5" not in rendered
    assert "46.2" in rendered
    assert _keys(body).isdisjoint(SENSITIVE_OUTPUT_KEYS)
    assert "user_id" not in rendered
    assert "document_sha256" not in rendered
    assert post.status_code == 405


async def test_timeseries_private_and_unknown_share_one_404() -> None:
    """A private profile and a missing id return the same not-found body."""
    application = _application(
        _store(),
        SlidingWindowRateLimiter(limit=20, window_seconds=60),
    )
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        private = await client.get(f"/api/v1/profiles/{_PRIVATE}/timeseries")
        missing = await client.get("/api/v1/profiles/nmdoesnotexist0001/timeseries")
        public = await client.get(f"/api/v1/profiles/{_PUBLIC}/timeseries")
    assert private.status_code == 404
    assert missing.status_code == 404
    assert private.json() == missing.json()
    assert public.status_code == 200
    payload = public.json()
    assert payload["public_id"] == _PUBLIC
    assert len(payload["points"]) == 1
    assert len(payload["points"][0]["markers"]) == 2
    assert _keys(payload).isdisjoint(SENSITIVE_OUTPUT_KEYS)


async def test_dataset_rate_limit_is_per_ip() -> None:
    """The third request from one address is 429. Another address still reads."""
    application = _application(_store(), SlidingWindowRateLimiter(limit=2, window_seconds=60))
    transport = ASGITransport(app=application)
    headers = {"X-Real-IP": "203.0.113.10"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/api/v1/dataset", headers=headers)
        second = await client.get("/api/v1/dataset", headers=headers)
        third = await client.get("/api/v1/dataset", headers=headers)
        other = await client.get("/api/v1/dataset", headers={"X-Real-IP": "203.0.113.11"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["detail"] == "Rate limit exceeded"
    assert int(third.headers["retry-after"]) >= 1
    assert other.status_code == 200


async def test_openapi_is_3_1_and_dataset_is_get_only() -> None:
    """The published contract is OpenAPI 3.1 and the public routes do not write."""
    application = create_app()
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert spec["openapi"] == "3.1.0"
    dataset_ops = spec["paths"]["/api/v1/dataset"]
    series_ops = spec["paths"]["/api/v1/profiles/{public_id}/timeseries"]
    csv_ops = spec["paths"]["/api/v1/dataset.csv"]
    parquet_ops = spec["paths"]["/api/v1/dataset.parquet"]
    datasheet_ops = spec["paths"]["/api/v1/dataset/datasheet"]
    for operations in (dataset_ops, series_ops, csv_ops, parquet_ops, datasheet_ops):
        assert "get" in operations
        for method in ("post", "put", "patch", "delete"):
            assert method not in operations
