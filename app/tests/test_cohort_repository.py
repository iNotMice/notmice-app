"""Tests for the current research-consent cohort gate."""

from __future__ import annotations

from sqlalchemy.orm import configure_mappers

from app.repositories.cohort import eligible_participant_count_select
from app.repositories.models import Base


def test_lab_identity_tables_are_registered_with_separate_foreign_keys() -> None:
    """Lab identity metadata stays independent of participant credential tables."""
    configure_mappers()
    expected = {
        "organizations",
        "lab_users",
        "lab_sessions",
        "lab_auth_tokens",
        "lab_query_audit",
    }
    assert expected.issubset(Base.metadata.tables)
    lab_user_fks = Base.metadata.tables["lab_users"].foreign_keys
    assert {foreign_key.target_fullname for foreign_key in lab_user_fks} == {
        "organizations.id"
    }


def test_aggregate_eligibility_requires_current_unwithdrawn_research_consent() -> None:
    """The cohort count never uses public-sharing state as research consent."""
    statement = eligible_participant_count_select()
    query = str(statement)

    assert "consents.consent_type" in query
    assert "consents.text_version" in query
    assert "consents.withdrawn_at IS NULL" in query
    assert "lab_results.confirmed_at IS NOT NULL" in query
    assert "share_settings" not in query
