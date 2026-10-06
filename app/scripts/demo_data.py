"""Synthetic demonstration data, clearly marked and removable in one command.

Usage (inside the api container):
    python -m app.scripts.demo_data seed --participants 60
    python -m app.scripts.demo_data attach --email person@example.org --panels 3
    python -m app.scripts.demo_data grant-lab --org UUID
    python -m app.scripts.demo_data remove

Every synthetic participant has a public ID starting with ``nmdemo`` and no
login. Every synthetic panel has parser version ``demo-seed`` and a laboratory
name starting with ``DEMO``. ``remove`` deletes all of them and withdraws the
demo agreement from laboratories. No real person's data is generated or read,
except that ``attach`` adds synthetic panels to an existing account by email.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
import secrets
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from importlib.resources import files
from uuid import UUID, uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.domain.conditions import CONDITION_CODES
from app.domain.consents import (
    HEALTH_DATA,
    HEALTH_DATA_VERSION,
    PARTICIPANT_PROFILE,
    PARTICIPANT_PROFILE_VERSION,
    RESEARCH_REUSE,
    RESEARCH_REUSE_VERSION,
)
from app.domain.enums import MappingStatus
from app.domain.uploads import MappedMarker
from app.repositories.lab_results import LabResultRepository
from app.repositories.models import (
    Consent,
    Credential,
    LabResult,
    Organization,
    ParticipantProfileRow,
    ProfileCondition,
    ShareSettings,
    User,
)
from app.services.lab_accounts import DEMO_DUA_VERSION

DEMO_PUBLIC_ID_PREFIX = "nmdemo"
DEMO_PARSER_VERSION = "demo-seed"
DEMO_LAB_NAMES = (
    "DEMO · Лаборатория 1 (вымышленные данные)",
    "DEMO · Лаборатория 2 (вымышленные данные)",
)
_COUNTRIES = ("BY", "PL", "DE", "RU", "KZ", "LT", "FR", "UA")
_COUNTRY_WEIGHTS = (30, 20, 12, 12, 8, 7, 6, 5)


@dataclass(frozen=True, slots=True)
class _Marker:
    mean: float
    sd: float
    low: float
    high: float
    digits: int
    reference: tuple[float | None, float | None]
    age_slope: float = 0.0
    lognormal: bool = False


# Values in the dictionary canonical units. Typical adult distributions,
# loosely shaped; they are illustrations, not reference data.
_MARKERS: dict[str, _Marker] = {
    "albumin": _Marker(44, 2.8, 34, 52, 1, (35, 52), age_slope=-0.06),
    "creatinine": _Marker(0.92, 0.17, 0.5, 1.6, 2, (0.6, 1.2), age_slope=0.003),
    "glucose": _Marker(91, 10, 66, 150, 0, (70, 99), age_slope=0.25),
    "crp": _Marker(1.1, 0.8, 0.1, 15, 1, (None, 5), age_slope=0.01, lognormal=True),
    "lymphocyte": _Marker(31, 7, 12, 50, 1, (19, 37), age_slope=-0.08),
    "mcv": _Marker(89, 4, 78, 102, 1, (80, 100), age_slope=0.05),
    "rdw": _Marker(12.9, 0.8, 11, 17, 1, (11.5, 14.5), age_slope=0.02),
    "alp": _Marker(68, 17, 30, 140, 0, (40, 130), age_slope=0.2),
    "wbc": _Marker(6.1, 1.4, 3.5, 11, 1, (4, 9)),
    "hemoglobin": _Marker(142, 12, 110, 175, 0, (120, 170)),
    "hematocrit": _Marker(42, 3.5, 34, 52, 1, (36, 50)),
    "platelets": _Marker(245, 50, 140, 420, 0, (150, 400)),
    "alt": _Marker(24, 10, 7, 80, 0, (None, 41)),
    "ast": _Marker(23, 7, 10, 70, 0, (None, 40)),
    "cholesterol": _Marker(198, 34, 120, 320, 0, (None, 200), age_slope=0.6),
    "hdl": _Marker(55, 13, 28, 100, 0, (40, None)),
    "triglycerides": _Marker(118, 50, 40, 380, 0, (None, 150), age_slope=0.5),
    "hba1c": _Marker(5.4, 0.35, 4.5, 7.5, 1, (None, 5.7), age_slope=0.01),
    "tsh": _Marker(1.9, 0.9, 0.3, 6, 2, (0.4, 4.0)),
    "ferritin": _Marker(105, 65, 10, 400, 0, (20, 250)),
}


def _dictionary() -> dict[str, tuple[str, str]]:
    """Canonical id to (LOINC code, canonical unit) from the shipped dictionary."""
    raw = files("app.data").joinpath("loinc/dictionary.v1.json").read_text(encoding="utf-8")
    entries = json.loads(raw)["markers"]
    return {entry["id"]: (entry["loinc"], entry["canonical_unit"]) for entry in entries}


def _value(rng: random.Random, marker: _Marker, age: float, sex: str) -> Decimal:
    if marker.lognormal:
        value = math.exp(rng.gauss(math.log(marker.mean), marker.sd))
    else:
        value = rng.gauss(marker.mean, marker.sd)
    value += marker.age_slope * (age - 45)
    if sex == "female" and marker is _MARKERS["hemoglobin"]:
        value -= 14
    value = min(max(value, marker.low), marker.high)
    return Decimal(str(round(value, marker.digits)))


def _panel_markers(
    rng: random.Random, age: float, sex: str, full: bool
) -> tuple[MappedMarker, ...]:
    dictionary = _dictionary()
    chosen = list(_MARKERS)
    if not full:
        drop = rng.choice(["crp", "lymphocyte", "alp"])
        chosen = [marker_id for marker_id in chosen if marker_id != drop]
    markers: list[MappedMarker] = []
    for marker_id in chosen:
        spec = _MARKERS[marker_id]
        loinc, unit = dictionary[marker_id]
        value = _value(rng, spec, age, sex)
        low, high = spec.reference
        markers.append(
            MappedMarker(
                raw_name=marker_id.upper(),
                value=value,
                unit=unit,
                confidence=1.0,
                canonical_id=marker_id,
                loinc_code=loinc,
                mapping_status=MappingStatus.MAPPED,
                within_range=None,
                reported_value=value,
                reported_unit=unit,
                reference_low=None if low is None else Decimal(str(low)),
                reference_high=None if high is None else Decimal(str(high)),
            )
        )
    return tuple(markers)


async def _save_panels(
    session: AsyncSession,
    rng: random.Random,
    *,
    user_id: UUID,
    year_of_birth: int,
    sex: str,
    count: int,
) -> None:
    labs = LabResultRepository(session)
    start = date(2025, 1, 15) + timedelta(days=rng.randint(0, 200))
    for index in range(count):
        collected = start + timedelta(days=index * rng.randint(90, 160))
        collected = min(collected, date(2026, 9, 30))
        age = collected.year - year_of_birth + collected.timetuple().tm_yday / 365
        await labs.save_confirmed(
            user_id=user_id,
            collected_at=collected,
            lab_name=rng.choice(DEMO_LAB_NAMES),
            chronological_age=Decimal(str(round(age, 1))),
            parser_version=DEMO_PARSER_VERSION,
            confirmed_at=datetime.now(UTC),
            document_sha256=secrets.token_hex(32),
            markers=_panel_markers(rng, age, sex, full=rng.random() > 0.15),
        )


def _consent(user_id: UUID, consent_type: str, version: str) -> Consent:
    return Consent(
        id=uuid4(),
        user_id=user_id,
        consent_type=consent_type,
        text_version=version,
        granted_at=datetime.now(UTC),
        withdrawn_at=None,
    )


async def seed(session: AsyncSession, participants: int, seed_value: int) -> int:
    """Create synthetic participants with consents, a questionnaire and panels."""
    rng = random.Random(seed_value)
    conditions = sorted(CONDITION_CODES)
    created = 0
    for _ in range(participants):
        user = User(id=uuid4(), public_id=f"{DEMO_PUBLIC_ID_PREFIX}{secrets.token_hex(6)}")
        session.add(user)
        await session.flush()
        session.add(ShareSettings(id=uuid4(), user_id=user.id, is_public=False))
        for consent_type, version in (
            (HEALTH_DATA, HEALTH_DATA_VERSION),
            (RESEARCH_REUSE, RESEARCH_REUSE_VERSION),
            (PARTICIPANT_PROFILE, PARTICIPANT_PROFILE_VERSION),
        ):
            if version is not None:
                session.add(_consent(user.id, consent_type, version))
        sex = rng.choices(("female", "male", "undisclosed"), weights=(52, 45, 3))[0]
        year_of_birth = rng.randint(1950, 2000)
        session.add(
            ParticipantProfileRow(
                id=uuid4(),
                user_id=user.id,
                sex_at_birth=sex,
                year_of_birth=year_of_birth,
                country=rng.choices(_COUNTRIES, weights=_COUNTRY_WEIGHTS)[0],
                height_cm=rng.randint(155, 192),
                weight_kg=Decimal(str(round(rng.uniform(52, 105), 1))),
                smoking=rng.choices(("never", "former", "current"), weights=(60, 25, 15))[0],
                alcohol=rng.choice(("none", "light", "moderate", "heavy")),
                activity=rng.choice(("sedentary", "light", "moderate", "high")),
                updated_at=datetime.now(UTC),
            )
        )
        for code in rng.sample(conditions, k=rng.choices((0, 1, 2), weights=(55, 35, 10))[0]):
            session.add(ProfileCondition(id=uuid4(), user_id=user.id, code=code))
        await _save_panels(
            session,
            rng,
            user_id=user.id,
            year_of_birth=year_of_birth,
            sex=sex,
            count=rng.randint(1, 3),
        )
        created += 1
    return created


async def attach(session: AsyncSession, email: str, panels: int, seed_value: int) -> int:
    """Add synthetic panels to an existing participant account found by email."""
    result = await session.execute(
        select(Credential).where(Credential.email == email.strip().casefold())
    )
    credential = result.scalar_one_or_none()
    if credential is None:
        raise SystemExit(f"No participant account with email {email}")
    profile = (
        await session.execute(
            select(ParticipantProfileRow).where(ParticipantProfileRow.user_id == credential.user_id)
        )
    ).scalar_one_or_none()
    year_of_birth = profile.year_of_birth if profile and profile.year_of_birth else 1981
    sex = profile.sex_at_birth if profile and profile.sex_at_birth else "female"
    rng = random.Random(seed_value)
    await _save_panels(
        session, rng, user_id=credential.user_id, year_of_birth=year_of_birth, sex=sex, count=panels
    )
    return panels


async def grant_lab(session: AsyncSession, organization_id: UUID) -> None:
    """Open the cohort explorer for one verified organization on the demo agreement."""
    organization = await session.get(Organization, organization_id)
    if organization is None:
        raise SystemExit(f"No organization {organization_id}")
    if organization.verification_status != "verified":
        raise SystemExit("Verify the organization first (app.scripts.verify_organization)")
    organization.dua_version = DEMO_DUA_VERSION
    organization.dua_accepted_at = datetime.now(UTC)


async def remove(session: AsyncSession) -> tuple[int, int, int]:
    """Delete every synthetic participant and panel, withdraw demo lab access."""
    users = await session.execute(
        delete(User).where(User.public_id.like(f"{DEMO_PUBLIC_ID_PREFIX}%")).returning(User.id)
    )
    panels = await session.execute(
        delete(LabResult)
        .where(LabResult.parser_version == DEMO_PARSER_VERSION)
        .returning(LabResult.id)
    )
    labs = await session.execute(
        update(Organization)
        .where(Organization.dua_version == DEMO_DUA_VERSION)
        .values(dua_version=None, dua_accepted_at=None)
        .returning(Organization.id)
    )
    return len(users.all()), len(panels.all()), len(labs.all())


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    commands = parser.add_subparsers(dest="command", required=True)
    seed_parser = commands.add_parser("seed", help="create synthetic participants")
    seed_parser.add_argument("--participants", type=int, default=60)
    seed_parser.add_argument("--seed", type=int, default=20261006)
    attach_parser = commands.add_parser("attach", help="add synthetic panels to an account")
    attach_parser.add_argument("--email", required=True)
    attach_parser.add_argument("--panels", type=int, default=3)
    attach_parser.add_argument("--seed", type=int, default=7)
    grant_parser = commands.add_parser("grant-lab", help="demo cohort access for one organization")
    grant_parser.add_argument("--org", required=True, type=UUID)
    commands.add_parser("remove", help="delete all synthetic data and demo access")
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> None:
    engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session, session.begin():
            if args.command == "seed":
                if not 1 <= args.participants <= 500:
                    raise SystemExit("--participants must be 1-500")
                count = await seed(session, args.participants, args.seed)
                print(
                    f"Created {count} synthetic participants "
                    f"(public ID {DEMO_PUBLIC_ID_PREFIX}...)."
                )
            elif args.command == "attach":
                if not 1 <= args.panels <= 6:
                    raise SystemExit("--panels must be 1-6")
                count = await attach(session, args.email, args.panels, args.seed)
                print(f"Added {count} synthetic panels marked DEMO to {args.email}.")
            elif args.command == "grant-lab":
                await grant_lab(session, args.org)
                print(
                    f"Organization {args.org}: demo access on synthetic data ({DEMO_DUA_VERSION})."
                )
            else:
                users, panels, labs = await remove(session)
                print(
                    f"Removed {users} synthetic participants, {panels} DEMO panels, "
                    f"demo access for {labs} labs."
                )
    finally:
        await engine.dispose()


def main() -> None:
    asyncio.run(_run(_arguments()))


if __name__ == "__main__":
    main()
