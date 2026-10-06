"""Pydantic schemas shared across API and services."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.lab_accounts import LabOrganizationRecord
from app.domain.protocol import ProtocolKindName
from app.domain.survey import Activity, Alcohol, SexAtBirth, Smoking


class HealthStatus(BaseModel):
    """Public /healthz payload."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(description="ok when the process and database are reachable.")
    database: str = Field(description="ok or unavailable.")


class ConsentInput(BaseModel):
    """One consent checkbox. Optional consents are omitted when they are off."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["health_data", "research_reuse", "participant_profile", "public_sharing"]
    version: str = Field(min_length=1, max_length=64)
    accepted: bool


class AccountRegisterRequest(BaseModel):
    """Email registration. The password is at least 12 characters."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)
    consents: list[ConsentInput] = Field(min_length=1, max_length=4)


class AccountRegisterResponse(BaseModel):
    """Same body whether or not the address already exists."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["accepted"] = "accepted"


class EmailLoginRequest(BaseModel):
    """Email and password. The response does not say which part failed."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class AuthTokenRequest(BaseModel):
    """A one-time confirmation or reset token from an email link."""

    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=20, max_length=128)


class PasswordResetRequest(BaseModel):
    """Ask for a reset link. The response does not say whether the address exists."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)


class PasswordResetConfirmRequest(BaseModel):
    """Set a new password with a one-time token."""

    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=20, max_length=128)
    password: str = Field(min_length=12, max_length=128)


class AccountLoginRequest(BaseModel):
    """Login with a BIP-39 recovery phrase. No email or phone."""

    model_config = ConfigDict(extra="forbid")

    mnemonic: str = Field(
        min_length=1,
        max_length=500,
        description="12-word English BIP-39 recovery phrase.",
    )


class ShareSettingsUpdate(BaseModel):
    """Opt-in public sharing flag, version-bound to its separate consent."""

    model_config = ConfigDict(extra="forbid")

    is_public: bool = Field(description="True when the profile may appear in the public dataset.")
    consent_version: str | None = Field(default=None, min_length=1, max_length=64)


class AccountView(BaseModel):
    """Public representation of a pseudonymous account. No phrase, no hash."""

    model_config = ConfigDict(extra="forbid")

    public_id: str
    is_public: bool
    created_at: datetime


class ConsentView(BaseModel):
    """One stored consent. Withdrawal is null until the person turns it off."""

    model_config = ConfigDict(extra="forbid")

    type: str
    version: str
    granted_at: datetime
    withdrawn_at: datetime | None


class ConsentListResponse(BaseModel):
    """Consents for the signed-in participant."""

    model_config = ConfigDict(extra="forbid")

    consents: list[ConsentView]


class ParticipantProfileView(BaseModel):
    """Owner's profile survey answers; never part of the public profile."""

    model_config = ConfigDict(extra="forbid")

    sex_at_birth: SexAtBirth | None
    year_of_birth: int | None
    country: str | None
    height_cm: int | None
    weight_kg: Decimal | None
    smoking: Smoking | None
    alcohol: Alcohol | None
    activity: Activity | None
    conditions: list[str]
    updated_at: datetime | None


class SurveyCatalogView(BaseModel):
    """Survey vocabulary plus its explicit rollout state."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    health_data_consent_version: str
    research_reuse_consent_version: str
    profile_consent_version: str | None
    public_sharing_consent_version: str
    country_code_pattern: str
    countries: list[str]
    sex_at_birth: list[SexAtBirth]
    smoking: list[Smoking]
    alcohol: list[Alcohol]
    activity: list[Activity]
    conditions: list[str]
    goals: list[str]


class LabRegisterRequest(BaseModel):
    """Register a pending laboratory organization and its first owner."""

    model_config = ConfigDict(extra="forbid")

    organization_name: str = Field(min_length=1, max_length=200)
    organization_type: Literal["laboratory", "university", "research_institute", "company", "other"]
    country: str = Field(pattern=r"^[A-Z]{2}$")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)


class LabLoginRequest(BaseModel):
    """Laboratory email and password."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class LabConfirmRequest(BaseModel):
    """One-time laboratory email confirmation token."""

    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=20, max_length=128)


class LabDuaAcceptRequest(BaseModel):
    """Explicit acceptance of the current organization DUA."""

    model_config = ConfigDict(extra="forbid")

    accepted: Literal[True]


class LabOrganizationView(BaseModel):
    """Organization state visible only to its authenticated users."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str
    organization_type: str
    country: str
    verification_status: Literal["pending", "verified", "rejected"]
    dua_version: str | None
    current_dua_version: str | None
    dua_accepted_at: datetime | None
    verified_at: datetime | None
    verification_reviewed_at: datetime | None


class LabAccountView(BaseModel):
    """Authenticated laboratory account and access status."""

    model_config = ConfigDict(extra="forbid")

    email: str
    role: str
    email_confirmed_at: datetime
    organization: LabOrganizationView


class CohortMarkerAggregate(BaseModel):
    """Aggregate for a marker with enough participants to publish statistics."""

    model_config = ConfigDict(extra="forbid")

    loinc_code: str
    canonical_name: str | None
    n: int | None
    unit: str | None
    mean: float | None
    median: float | None
    p25: float | None
    p75: float | None


class CohortQueryResponse(BaseModel):
    """Suppressed aggregate-only cohort result."""

    model_config = ConfigDict(extra="forbid")

    cohort_size: int | None
    markers: list[CohortMarkerAggregate]
    suppressed: bool


class CohortFacet(BaseModel):
    """One k-anonymous value in a filter facet."""

    model_config = ConfigDict(extra="forbid")

    value: str
    count: int


class CohortFacetsResponse(BaseModel):
    """Filter values whose participant counts meet the publication threshold."""

    model_config = ConfigDict(extra="forbid")

    sex_at_birth: list[CohortFacet]
    age_bands: list[CohortFacet]
    countries: list[CohortFacet]
    conditions: list[CohortFacet]
    markers: list[CohortFacet]


def lab_account_view(
    email: str,
    role: str,
    email_confirmed_at: datetime,
    organization: LabOrganizationRecord,
    current_dua_version: str | None = None,
) -> LabAccountView:
    """Map internal laboratory account state to its owner-only response."""
    return LabAccountView(
        email=email,
        role=role,
        email_confirmed_at=email_confirmed_at,
        organization=LabOrganizationView(
            id=organization.id,
            name=organization.name,
            organization_type=organization.org_type,
            country=organization.country,
            verification_status=organization.verification_status,
            dua_version=organization.dua_version,
            current_dua_version=current_dua_version,
            dua_accepted_at=organization.dua_accepted_at,
            verified_at=organization.verified_at,
            verification_reviewed_at=organization.verification_reviewed_at,
        ),
    )


class ExtractedMarkerView(BaseModel):
    """One analyte returned to the review UI."""

    model_config = ConfigDict(extra="forbid")

    raw_name: str
    canonical_id: str | None
    loinc_code: str | None
    value: float
    unit: str
    confidence: float
    mapping_status: str
    within_range: bool | None = Field(
        description="False when a mapped value sits outside the dictionary typo window.",
    )
    reported_value: float | None = None
    reported_unit: str | None = None
    reference_low: float | None = None
    reference_high: float | None = None
    reference_text: str | None = None
    lab_flag: str | None = None


class ExtractResponse(BaseModel):
    """Extract result. The original file is not included."""

    model_config = ConfigDict(extra="forbid")

    extract_token: str
    document_sha256: str
    parser_version: str
    lab_name: str | None
    collected_at: date | None
    chronological_age: float | None
    markers: list[ExtractedMarkerView]
    tokens_used: int = Field(ge=0)
    tokens_limit: int = Field(ge=1)
    warning: bool


class RedactionPreviewResponse(BaseModel):
    """Painted pages the caller must accept before extraction runs.

    ``preview_png`` is base64 of the painted PNG, not the original upload.
    """

    model_config = ConfigDict(extra="forbid")

    redaction_token: str
    document_sha256: str
    region_count: int = Field(ge=0)
    preview_png: str


class RedactionConfirmRequest(BaseModel):
    """Accept or drop a painted frame. The token is the preview token."""

    model_config = ConfigDict(extra="forbid")

    redaction_token: str = Field(min_length=8, max_length=128)


class ConfirmedMarkerInput(BaseModel):
    """Human-edited analyte row from the review UI."""

    model_config = ConfigDict(extra="forbid")

    raw_name: str = Field(min_length=1, max_length=255)
    value: float
    unit: str = Field(min_length=1, max_length=32)
    reported_value: float | None = None
    reported_unit: str | None = Field(default=None, max_length=32)
    reference_low: float | None = None
    reference_high: float | None = None
    reference_text: str | None = Field(default=None, max_length=64)
    lab_flag: str | None = Field(default=None, max_length=16)


class ConfirmRequest(BaseModel):
    """Confirm payload. Hash and parser version are taken from the extract session."""

    model_config = ConfigDict(extra="forbid")

    extract_token: str = Field(min_length=8, max_length=128)
    lab_name: str | None = Field(default=None, max_length=255)
    collected_at: date | None = None
    chronological_age: float | None = None
    markers: list[ConfirmedMarkerInput] = Field(min_length=1, max_length=40)


class OwnedMarkerView(BaseModel):
    """One analyte on a panel the signed-in account confirmed."""

    model_config = ConfigDict(extra="forbid")

    raw_name: str
    canonical_id: str | None
    loinc_code: str | None
    value: float
    unit: str
    reported_value: float | None = None
    reported_unit: str | None = None
    reference_low: float | None = None
    reference_high: float | None = None
    reference_text: str | None = None
    lab_flag: str | None = None
    outside_interval: bool = Field(
        description=(
            "True only when the value leaves the printed laboratory interval "
            "or the laboratory mark is H, L, or *."
        ),
    )


class OwnedLabResultView(BaseModel):
    """A confirmed panel returned only to its owner."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    collected_at: date | None
    lab_name: str | None
    chronological_age: float | None
    confirmed_at: datetime
    document_sha256: str
    marker_count: int = Field(ge=0)
    status: Literal["confirmed"]
    pheno_age: float | None = Field(
        description="Levine 2018 index when all nine markers and an age are present.",
    )
    age_delta: float | None = Field(
        description="Index minus calendar age. Null when the panel is not scored.",
    )
    missing_markers: list[str] = Field(
        description="Levine marker ids absent from this panel, in dictionary order.",
    )
    phenoage_disclaimer: str
    markers: list[OwnedMarkerView]


class OwnedLabResultsResponse(BaseModel):
    """Confirmed panels for the signed-in account, oldest first."""

    model_config = ConfigDict(extra="forbid")

    results: list[OwnedLabResultView]


class ConfirmResponse(BaseModel):
    """Persisted lab result after sign-off."""

    model_config = ConfigDict(extra="forbid")

    lab_result_id: UUID
    document_sha256: str
    parser_version: str
    confirmed_at: datetime
    marker_count: int


class PhenoAgeMarkers(BaseModel):
    """Nine PhenoAge analytes in LOINC-dictionary canonical units."""

    model_config = ConfigDict(extra="forbid")

    albumin: float = Field(gt=0, description="Serum albumin, g/L (LOINC 1751-7).")
    creatinine: float = Field(gt=0, description="Serum creatinine, mg/dL (LOINC 2160-0).")
    glucose: float = Field(gt=0, description="Fasting glucose, mg/dL (LOINC 2345-7).")
    crp: float = Field(gt=0, description="hs-CRP, mg/L (LOINC 30522-7).")
    lymphocyte: float = Field(gt=0, le=100, description="Lymphocyte percent (LOINC 26474-7).")
    mcv: float = Field(gt=0, description="Mean corpuscular volume, fL (LOINC 787-2).")
    rdw: float = Field(gt=0, description="Red cell distribution width, % (LOINC 788-0).")
    alp: float = Field(gt=0, description="Alkaline phosphatase, U/L (LOINC 6768-6).")
    wbc: float = Field(gt=0, description="White blood cell count, 10^3/µL (LOINC 6690-2).")


class PhenoAgeRequest(BaseModel):
    """Chronological age plus the nine Levine biomarkers. No identity fields."""

    model_config = ConfigDict(extra="forbid")

    chronological_age: float = Field(ge=0, le=120, description="Age in years.")
    markers: PhenoAgeMarkers


class PhenoAgeResponse(BaseModel):
    """Research index. ``disclaimer`` states this is not a medical service."""

    model_config = ConfigDict(extra="forbid")

    chronological_age: float
    pheno_age: float
    age_delta: float
    disclaimer: str


class PublicBiomarkerView(BaseModel):
    """One anonymized analyte row. No internal ids and no personal identifiers."""

    model_config = ConfigDict(extra="forbid")

    public_id: str
    collected_at: date | None
    chronological_age: float | None
    loinc_code: str | None
    canonical_name: str | None
    raw_name: str
    value: float
    unit: str
    mapping_status: str


class DatasetResponse(BaseModel):
    """Page of confirmed biomarker rows from profiles that opted in."""

    model_config = ConfigDict(extra="forbid")

    rows: list[PublicBiomarkerView]
    total: int
    limit: int
    offset: int


class TimeseriesMarkerView(BaseModel):
    """One analyte inside a public profile's time series."""

    model_config = ConfigDict(extra="forbid")

    loinc_code: str | None
    canonical_name: str | None
    raw_name: str
    value: float
    unit: str
    mapping_status: str


class TimeseriesPointView(BaseModel):
    """Markers that share one collection date on a public profile."""

    model_config = ConfigDict(extra="forbid")

    collected_at: date | None
    chronological_age: float | None
    markers: list[TimeseriesMarkerView]


class TimeseriesResponse(BaseModel):
    """Confirmed biomarker history for one opted-in profile."""

    model_config = ConfigDict(extra="forbid")

    public_id: str
    points: list[TimeseriesPointView]


class NewsCardView(BaseModel):
    """One research or commentary card. The snippet is the publisher's text, clipped."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    source: str
    published_at: date | None
    snippet: str
    url: str
    kind: Literal["paper", "biohacking"]
    translated: bool = Field(
        default=False,
        description=(
            "True when title and snippet are machine-translated into the requested language"
        ),
    )
    original_title: str | None = Field(default=None, description="Source title when translated")
    original_snippet: str | None = Field(default=None, description="Source snippet when translated")


class NewsResponse(BaseModel):
    """Live feed assembled from PubMed and the RSS allowlist."""

    model_config = ConfigDict(extra="forbid")

    items: list[NewsCardView]
    fetched_at: datetime | None
    stale: bool
    error: Literal["unavailable"] | None
    translation_pending: bool = Field(
        default=False,
        description="True while some cards are still being translated; read again shortly",
    )


class ProtocolEntryInput(BaseModel):
    """One journal row. Extra keys, including a catalog id, are rejected."""

    model_config = ConfigDict(extra="forbid")

    kind: ProtocolKindName
    title: str = Field(min_length=1, max_length=120)
    dose: str | None = Field(default=None, max_length=80)
    started_on: date
    ended_on: date | None = None
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def end_is_not_before_start(self) -> "ProtocolEntryInput":
        """Reject a period that finishes before it starts."""
        if self.ended_on is not None and self.ended_on < self.started_on:
            raise ValueError("End date is before the start date")
        return self


class ProtocolEntryView(BaseModel):
    """One journal row returned to its owner."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    kind: ProtocolKindName
    title: str
    dose: str | None
    started_on: date
    ended_on: date | None
    note: str | None


class ProtocolListResponse(BaseModel):
    """Journal rows for the signed-in participant."""

    model_config = ConfigDict(extra="forbid")

    entries: list[ProtocolEntryView]


class PasswordChangeRequest(BaseModel):
    """Change the password from the cabinet. The current one proves it is the owner."""

    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class SessionsRevokedResponse(BaseModel):
    """How many other devices were signed out."""

    model_config = ConfigDict(extra="forbid")

    revoked_sessions: int = Field(ge=0)


class CabinetAccountView(BaseModel):
    """The owner's own account card. No hash, no session digest, no internal id."""

    model_config = ConfigDict(extra="forbid")

    public_id: str
    created_at: datetime
    email: str | None
    sign_in_method: Literal["email", "phrase"]
    active_sessions: int = Field(ge=0)


class CabinetConsentsView(BaseModel):
    """Whether the current text version of each consent is active."""

    model_config = ConfigDict(extra="forbid")

    health_data: bool
    research_reuse: bool
    public_sharing: bool
    sharing_enabled: bool = Field(
        description="Public sharing is on and its current consent is active.",
    )


class CabinetIndexPointView(BaseModel):
    """One scored panel on the research-index timeline."""

    model_config = ConfigDict(extra="forbid")

    panel_id: UUID
    observed_on: date
    pheno_age: float
    age_delta: float
    chronological_age: float | None


class CabinetMarkerView(BaseModel):
    """Latest confirmed value of one canonical marker and how often it was measured."""

    model_config = ConfigDict(extra="forbid")

    canonical_id: str
    measurements: int = Field(ge=1)
    latest_value: float
    latest_unit: str
    latest_on: date
    latest_outside_interval: bool = Field(
        description="The latest value leaves the interval printed on its own report.",
    )
    in_phenoage: bool


class CabinetHistoryView(BaseModel):
    """Counts and dates of the confirmed history."""

    model_config = ConfigDict(extra="forbid")

    panel_count: int = Field(ge=0)
    first_observed_on: date | None
    last_observed_on: date | None
    laboratory_count: int = Field(ge=0)
    scored_count: int = Field(ge=0)
    repeat_marker_count: int = Field(ge=0)
    unmapped_marker_count: int = Field(ge=0)
    latest_missing_markers: list[str]


class CabinetJournalView(BaseModel):
    """Journal size. Entry text stays on the journal page."""

    model_config = ConfigDict(extra="forbid")

    total: int = Field(ge=0)
    open: int = Field(ge=0)


class CabinetView(BaseModel):
    """Personal cabinet overview, returned only to the signed-in owner."""

    model_config = ConfigDict(extra="forbid")

    account: CabinetAccountView
    consents: CabinetConsentsView
    history: CabinetHistoryView
    latest_index: CabinetIndexPointView | None
    previous_index: CabinetIndexPointView | None
    markers: list[CabinetMarkerView]
    journal: CabinetJournalView
    disclaimer: str
