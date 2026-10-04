export interface CohortFacet {
  value: string;
  count: number;
}

export interface CohortFacets {
  sex_at_birth: CohortFacet[];
  age_bands: CohortFacet[];
  countries: CohortFacet[];
  conditions: CohortFacet[];
  markers: CohortFacet[];
}

export interface CohortQueryInput {
  markers: string[];
  sex_at_birth: string[];
  age_bands: string[];
  countries: string[];
  conditions: string[];
  collected_from: string | null;
  collected_to: string | null;
}

export interface CohortMarkerAggregate {
  loinc_code: string;
  canonical_name: string | null;
  n: number | null;
  unit: string | null;
  mean: number | null;
  median: number | null;
  p25: number | null;
  p75: number | null;
}

export interface CohortQueryResult {
  cohort_size: number | null;
  markers: CohortMarkerAggregate[];
  suppressed: boolean;
}

function apiUrl(path: string): string {
  return `${import.meta.env.VITE_API_BASE_URL ?? ''}${path}`;
}

async function readError(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === 'object' && 'detail' in body) {
      const detail = body.detail;
      if (typeof detail === 'string') {
        return detail;
      }
    }
  } catch {
    // Use the status when the server does not return JSON.
  }
  return `Request failed (${response.status})`;
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as T;
}

export function fetchCohortFacets(): Promise<CohortFacets> {
  return requestJson<CohortFacets>('/api/v1/lab/cohorts/facets');
}

export function queryCohort(input: CohortQueryInput): Promise<CohortQueryResult> {
  return requestJson<CohortQueryResult>('/api/v1/lab/cohorts/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}
