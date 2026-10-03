"""Draft condition codes for the cohort query.

Leonid has not set the scientific vocabulary. These tokens exist so a query
can name a code from one closed list. Keep the list inside the query
contract: the survey catalog and the grant application stay without it.
"""

from typing import Final

CONDITION_CODES: Final[frozenset[str]] = frozenset(
    {
        "anemia",
        "asthma",
        "dyslipidemia",
        "gout",
        "hypertension",
        "hyperthyroidism",
        "hypothyroidism",
        "iron_deficiency",
        "migraine",
        "prediabetes",
        "type_2_diabetes",
        "vitamin_d_deficiency",
    }
)
