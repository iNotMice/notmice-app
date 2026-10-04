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
