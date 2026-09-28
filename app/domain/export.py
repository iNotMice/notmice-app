"""Public dataset export contract. Columns and license only — no rendering."""

from __future__ import annotations

from typing import Final

DATASET_LICENSE_ID: Final[str] = "CC0-1.0"
DATASET_LICENSE_NAME: Final[str] = "Creative Commons Zero 1.0 Universal"
DATASET_LICENSE_URL: Final[str] = "https://creativecommons.org/publicdomain/zero/1.0/legalcode"

# The protocol journal is not a column of this file. It stays on the account export.
EXPORT_COLUMNS: Final[tuple[str, ...]] = (
    "public_id",
    "collected_at",
    "chronological_age",
    "loinc_code",
    "canonical_name",
    "raw_name",
    "value",
    "unit",
    "mapping_status",
)
