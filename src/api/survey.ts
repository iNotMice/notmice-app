export interface SurveyCatalog {
  enabled: boolean;
  health_data_consent_version: string;
  research_reuse_consent_version: string;
  profile_consent_version: string | null;
  public_sharing_consent_version: string;
  country_code_pattern: string;
  countries: string[];
  sex_at_birth: string[];
  smoking: string[];
  alcohol: string[];
  activity: string[];
  conditions: string[];
  goals: string[];
}

export class SurveyCatalogRequestError extends Error {
  constructor(readonly status: number) {
    super(`Survey catalog request failed (${status})`);
    this.name = 'SurveyCatalogRequestError';
  }
}

export async function fetchSurveyCatalog(signal?: AbortSignal): Promise<SurveyCatalog> {
  const base = import.meta.env.VITE_API_BASE_URL ?? '';
  const response = await fetch(`${base}/api/v1/survey/catalog`, {
    credentials: 'include',
    signal,
  });
  if (!response.ok) {
    throw new SurveyCatalogRequestError(response.status);
  }
  return (await response.json()) as SurveyCatalog;
}

/** The owner's optional questionnaire answers. Every field may be empty. */
export interface ParticipantProfile {
  sex_at_birth: string | null;
  year_of_birth: number | null;
  country: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  smoking: string | null;
  alcohol: string | null;
  activity: string | null;
  conditions: string[];
  updated_at?: string | null;
}

export class ProfileRequestError extends Error {
  constructor(readonly status: number) {
    super(`Profile request failed (${status})`);
    this.name = 'ProfileRequestError';
  }
}

function profileUrl(): string {
  const base = import.meta.env.VITE_API_BASE_URL ?? '';
  return `${base}/api/v1/accounts/me/profile`;
}

/** Null when nothing has been saved yet. */
export async function fetchProfile(signal?: AbortSignal): Promise<ParticipantProfile | null> {
  const response = await fetch(profileUrl(), { credentials: 'include', signal });
  if (!response.ok) {
    throw new ProfileRequestError(response.status);
  }
  const body = (await response.json()) as ParticipantProfile;
  const empty =
    body.updated_at == null &&
    body.sex_at_birth === null &&
    body.year_of_birth === null &&
    body.country === null &&
    body.height_cm === null &&
    body.weight_kg === null;
  return empty ? null : body;
}

export async function saveProfile(profile: ParticipantProfile): Promise<ParticipantProfile> {
  const { updated_at: _ignored, ...payload } = profile;
  const response = await fetch(profileUrl(), {
    method: 'PUT',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new ProfileRequestError(response.status);
  }
  return (await response.json()) as ParticipantProfile;
}

export async function deleteProfile(): Promise<void> {
  const response = await fetch(profileUrl(), { method: 'DELETE', credentials: 'include' });
  if (!response.ok) {
    throw new ProfileRequestError(response.status);
  }
}
