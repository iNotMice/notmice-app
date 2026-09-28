"""Shared domain enumerations."""

from enum import StrEnum


class MappingStatus(StrEnum):
    """Whether a biomarker name resolved to a LOINC code."""

    MAPPED = "mapped"
    UNMAPPED = "unmapped"


class ProtocolKind(StrEnum):
    """A free-text journal row. There is no drug dictionary in this version."""

    DRUG = "drug"
    SUPPLEMENT = "supplement"
    NUTRITION = "nutrition"
    ACTIVITY = "activity"
    SLEEP = "sleep"
    OTHER = "other"
