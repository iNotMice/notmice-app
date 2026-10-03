"""Set a laboratory organization's manual verification decision.

Usage:
    python -m app.scripts.verify_organization --org UUID --status verified \
        --operator "operator-id" --evidence "Registry and corporate-domain verified"
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.repositories.lab_accounts import LabAccountRepository


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org", required=True, type=UUID, help="Organization UUID")
    parser.add_argument(
        "--status",
        required=True,
        choices=("verified", "rejected"),
        help="Manual verification outcome",
    )
    parser.add_argument("--operator", required=True, help="Internal operator identifier")
    parser.add_argument("--evidence", required=True, help="Summary of the verification evidence")
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> None:
    if not args.operator.strip() or len(args.operator) > 120:
        raise ValueError("--operator must contain 1-120 characters")
    if not args.evidence.strip() or len(args.evidence) > 1000:
        raise ValueError("--evidence must contain 1-1000 characters")
    engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    try:
        factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
        async with factory() as session:
            async with session.begin():
                updated = await LabAccountRepository(session).verify_organization(
                    args.org,
                    status=args.status,
                    operator=args.operator.strip(),
                    evidence=args.evidence.strip(),
                    verified_at=datetime.now(UTC),
                )
                if not updated:
                    raise ValueError(f"Organization {args.org} does not exist")
    finally:
        await engine.dispose()
    print(f"Organization {args.org}: {args.status}")


def main() -> None:
    args = _arguments()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
