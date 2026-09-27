"""PII validator tests."""

import pytest

from app.domain.pii import PIIValidationError, reject_pii, reject_sensitive_output


def test_reject_pii_allows_biomarker_payload() -> None:
    """Lab names and LOINC fields are not treated as personal names."""
    reject_pii(
        {
            "lab_name": "Quest Diagnostics",
            "raw_name": "Serum Albumin",
            "loinc_code": "1751-7",
            "value": 46.2,
        }
    )


def test_reject_pii_blocks_date_of_birth() -> None:
    """Date of birth is forbidden at any nesting level."""
    with pytest.raises(PIIValidationError, match="date_of_birth"):
        reject_pii({"patient": {"date_of_birth": "1984-01-01"}})


def test_reject_pii_blocks_patient_number_in_list() -> None:
    """Patient numbers in lists are rejected."""
    with pytest.raises(PIIValidationError, match="patient_number"):
        reject_pii([{"patient_number": "A-1"}])


def test_reject_pii_blocks_email_inside_raw_name() -> None:
    """An email written into a free-text analyte name is still personal data."""
    with pytest.raises(PIIValidationError, match="email"):
        reject_pii({"raw_name": "result for patient@example.com"})


def test_reject_pii_blocks_phone_inside_raw_name() -> None:
    """A phone number written into a free-text analyte name is rejected."""
    with pytest.raises(PIIValidationError, match="phone"):
        reject_pii({"raw_name": "call +7 999 123-45-67"})
    with pytest.raises(PIIValidationError, match="phone"):
        reject_pii({"raw_name": "+79991234567"})
    with pytest.raises(PIIValidationError, match="phone"):
        reject_pii({"lab_name": "8 (999) 123-45-67"})
    with pytest.raises(PIIValidationError, match="phone"):
        reject_pii({"raw_name": "415-555-2671"})


def test_reject_pii_blocks_person_name_in_free_text() -> None:
    """Two or three capitalized words in a free-text field are treated as a name."""
    with pytest.raises(PIIValidationError, match="person name"):
        reject_pii({"raw_name": "Ivan Petrov"})
    with pytest.raises(PIIValidationError, match="person name"):
        reject_pii({"lab_name": "Иван Петров"})
    with pytest.raises(PIIValidationError, match="person name"):
        reject_pii({"notes": "John Michael Smith"})


def test_reject_pii_allows_dates_codes_and_extract_tokens() -> None:
    """Dates, LOINC codes, and hyphenated tokens are not phone numbers."""
    reject_pii(
        {
            "extract_token": "ab1234-5678-9012cdEF_xyz123456789012",
            "loinc_code": "1751-7",
            "collected_at": "1984-01-01",
            "raw_name": "Vitamin D",
            "notes": "Fasting Serum Glucose",
        }
    )


def test_reject_sensitive_output_blocks_internal_ids() -> None:
    """Public responses cannot carry internal foreign keys or the document hash."""
    with pytest.raises(PIIValidationError, match="user_id"):
        reject_sensitive_output({"rows": [{"user_id": "secret", "value": 1}]})
    with pytest.raises(PIIValidationError, match="document_sha256"):
        reject_sensitive_output({"document_sha256": "a" * 64})


def test_reject_sensitive_output_blocks_email_in_a_value() -> None:
    """Public rows are scanned for emails, not only forbidden key names."""
    with pytest.raises(PIIValidationError, match="email"):
        reject_sensitive_output({"raw_name": "patient@example.com", "value": 1.0})
    reject_sensitive_output(
        {
            "raw_name": "Serum Albumin",
            "lab_name": "Quest Diagnostics",
            "value": 46.2,
            "unit": "g/L",
        }
    )


def test_reject_sensitive_output_allows_public_id() -> None:
    """The pseudonymous public id is the identifier the dataset is allowed to show."""
    reject_sensitive_output(
        {
            "public_id": "nm0123456789abcd",
            "loinc_code": "1751-7",
            "value": 46.2,
            "unit": "g/L",
        }
    )
