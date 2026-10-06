/** Personal cabinet API client: overview, password change, other sessions. */

export interface CabinetIndexPoint {
  panelId: string;
  observedOn: string;
  phenoAge: number;
  ageDelta: number;
  chronologicalAge: number | null;
}

export interface CabinetMarker {
  canonicalId: string;
  measurements: number;
  latestValue: number;
  latestUnit: string;
  latestOn: string;
  latestOutsideInterval: boolean;
  inPhenoage: boolean;
}

export interface CabinetOverview {
  account: {
    publicId: string;
    createdAt: string;
    email: string | null;
    signInMethod: 'email' | 'phrase';
    activeSessions: number;
  };
  consents: {
    healthData: boolean;
    researchReuse: boolean;
    publicSharing: boolean;
    sharingEnabled: boolean;
  };
  history: {
    panelCount: number;
    firstObservedOn: string | null;
    lastObservedOn: string | null;
    laboratoryCount: number;
    scoredCount: number;
    repeatMarkerCount: number;
    unmappedMarkerCount: number;
    latestMissingMarkers: string[];
  };
  latestIndex: CabinetIndexPoint | null;
  previousIndex: CabinetIndexPoint | null;
  markers: CabinetMarker[];
  journal: { total: number; open: number };
}

interface IndexPointPayload {
  panel_id: string;
  observed_on: string;
  pheno_age: number;
  age_delta: number;
  chronological_age: number | null;
}

interface CabinetPayload {
  account: {
    public_id: string;
    created_at: string;
    email: string | null;
    sign_in_method: 'email' | 'phrase';
    active_sessions: number;
  };
  consents: {
    health_data: boolean;
    research_reuse: boolean;
    public_sharing: boolean;
    sharing_enabled: boolean;
  };
  history: {
    panel_count: number;
    first_observed_on: string | null;
    last_observed_on: string | null;
    laboratory_count: number;
    scored_count: number;
    repeat_marker_count: number;
    unmapped_marker_count: number;
    latest_missing_markers: string[];
  };
  latest_index: IndexPointPayload | null;
  previous_index: IndexPointPayload | null;
  markers: {
    canonical_id: string;
    measurements: number;
    latest_value: number;
    latest_unit: string;
    latest_on: string;
    latest_outside_interval: boolean;
    in_phenoage: boolean;
  }[];
  journal: { total: number; open: number };
}

/** HTTP failure with its status, so a form can say what went wrong. */
export class CabinetRequestError extends Error {
  readonly status: number;

  constructor(status: number) {
    super(`Cabinet request failed (${status})`);
    this.status = status;
  }
}

function apiUrl(path: string): string {
  const base = import.meta.env.VITE_API_BASE_URL ?? '';
  return `${base}${path}`;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(apiUrl(path), { ...init, credentials: 'include' });
  if (!response.ok) {
    throw new CabinetRequestError(response.status);
  }
  return (await response.json()) as T;
}

function point(payload: IndexPointPayload | null): CabinetIndexPoint | null {
  if (!payload) {
    return null;
  }
  return {
    panelId: payload.panel_id,
    observedOn: payload.observed_on,
    phenoAge: payload.pheno_age,
    ageDelta: payload.age_delta,
    chronologicalAge: payload.chronological_age,
  };
}

export async function fetchCabinet(signal?: AbortSignal): Promise<CabinetOverview> {
  const body = await request<CabinetPayload>('/api/v1/accounts/me/cabinet', { signal });
  return {
    account: {
      publicId: body.account.public_id,
      createdAt: body.account.created_at,
      email: body.account.email,
      signInMethod: body.account.sign_in_method,
      activeSessions: body.account.active_sessions,
    },
    consents: {
      healthData: body.consents.health_data,
      researchReuse: body.consents.research_reuse,
      publicSharing: body.consents.public_sharing,
      sharingEnabled: body.consents.sharing_enabled,
    },
    history: {
      panelCount: body.history.panel_count,
      firstObservedOn: body.history.first_observed_on,
      lastObservedOn: body.history.last_observed_on,
      laboratoryCount: body.history.laboratory_count,
      scoredCount: body.history.scored_count,
      repeatMarkerCount: body.history.repeat_marker_count,
      unmappedMarkerCount: body.history.unmapped_marker_count,
      latestMissingMarkers: body.history.latest_missing_markers,
    },
    latestIndex: point(body.latest_index),
    previousIndex: point(body.previous_index),
    markers: body.markers.map((marker) => ({
      canonicalId: marker.canonical_id,
      measurements: marker.measurements,
      latestValue: marker.latest_value,
      latestUnit: marker.latest_unit,
      latestOn: marker.latest_on,
      latestOutsideInterval: marker.latest_outside_interval,
      inPhenoage: marker.in_phenoage,
    })),
    journal: body.journal,
  };
}

/** Change the password. Returns how many other devices were signed out. */
export async function changePassword(currentPassword: string, newPassword: string): Promise<number> {
  const body = await request<{ revoked_sessions: number }>('/api/v1/accounts/me/password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
  return body.revoked_sessions;
}

/** Sign out every other device. Returns how many sessions were closed. */
export async function revokeOtherSessions(): Promise<number> {
  const body = await request<{ revoked_sessions: number }>(
    '/api/v1/accounts/me/sessions/revoke-others',
    { method: 'POST' },
  );
  return body.revoked_sessions;
}
