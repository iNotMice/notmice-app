/** Account API client. Maps snake_case payloads to camelCase for the UI. */

export interface Account {
  publicId: string;
  isPublic: boolean;
  createdAt: string;
}

const LEGACY_TOKEN_KEY = 'notmice.access_token';

interface AccountViewPayload {
  public_id: string;
  is_public: boolean;
  created_at: string;
}

function apiUrl(path: string): string {
  const base = import.meta.env.VITE_API_BASE_URL ?? '';
  return `${base}${path}`;
}

function mapAccount(payload: AccountViewPayload): Account {
  return {
    publicId: payload.public_id,
    isPublic: payload.is_public,
    createdAt: payload.created_at,
  };
}

async function readError(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === 'object' && 'detail' in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === 'string') {
        return detail;
      }
    }
  } catch {
    // Fall through to status text.
  }
  return `Request failed (${response.status})`;
}

async function requestJson<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), { ...init, credentials: 'include' });
  if (response.status === 204) {
    return undefined as T;
  }
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as T;
}

function jsonHeaders(): HeadersInit {
  return { 'Content-Type': 'application/json' };
}

export function forgetLegacyToken(): void {
  try {
    localStorage.removeItem(LEGACY_TOKEN_KEY);
    sessionStorage.removeItem(LEGACY_TOKEN_KEY);
  } catch {
    // Storage can be blocked. The cookie is the session either way.
  }
}

export const HEALTH_CONSENT_VERSION = '2026-10-03';
export const RESEARCH_CONSENT_VERSION = '2026-10-03';

export type ConsentType =
  | 'health_data'
  | 'research_reuse'
  | 'participant_profile'
  | 'public_sharing';

export interface ConsentRecord {
  type: ConsentType;
  version: string;
  granted_at: string;
  withdrawn_at: string | null;
}

export async function fetchOwnConsents(): Promise<ConsentRecord[]> {
  const payload = await requestJson<{ consents: ConsentRecord[] }>('/api/v1/accounts/me/consents', {
    method: 'GET',
  });
  return payload.consents;
}

export async function updateOwnConsent(
  type: ConsentType,
  version: string,
  accepted: boolean,
): Promise<ConsentRecord | null> {
  try {
    return await requestJson<ConsentRecord>('/api/v1/accounts/me/consents', {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify({ type, version, accepted }),
    });
  } catch (error) {
    if (!accepted && error instanceof Error && error.message === 'Consent is not granted') {
      return null;
    }
    throw error;
  }
}

export interface RegisterInput {
  email: string;
  password: string;
  researchReuse: boolean;
}

export async function registerAccount(input: RegisterInput): Promise<void> {
  const consents: { type: string; version: string; accepted: boolean }[] = [
    { type: 'health_data', version: HEALTH_CONSENT_VERSION, accepted: true },
  ];
  if (input.researchReuse) {
    consents.push({
      type: 'research_reuse',
      version: RESEARCH_CONSENT_VERSION,
      accepted: true,
    });
  }
  await requestJson<{ status: string }>('/api/v1/accounts', {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({
      email: input.email,
      password: input.password,
      consents,
    }),
  });
}

export async function loginWithEmail(email: string, password: string): Promise<Account> {
  const payload = await requestJson<AccountViewPayload>('/api/v1/accounts/login/email', {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ email, password }),
  });
  return mapAccount(payload);
}

export async function confirmEmail(token: string): Promise<Account> {
  const payload = await requestJson<AccountViewPayload>('/api/v1/accounts/confirm', {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ token }),
  });
  return mapAccount(payload);
}

export async function requestPasswordReset(email: string): Promise<void> {
  await requestJson<{ status: string }>('/api/v1/accounts/password-reset', {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ email }),
  });
}

export async function confirmPasswordReset(token: string, password: string): Promise<void> {
  await requestJson<void>('/api/v1/accounts/password-reset/confirm', {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ token, password }),
  });
}

export async function downloadOwnExport(kind: 'json' | 'csv'): Promise<void> {
  const path = kind === 'json' ? '/api/v1/accounts/me/export.json' : '/api/v1/accounts/me/export.csv';
  const response = await fetch(apiUrl(path), { credentials: 'include' });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = kind === 'json' ? 'notmice-account.json' : 'notmice-account.csv';
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export async function deleteOwnAccount(): Promise<void> {
  await requestJson<void>('/api/v1/accounts/me', {
    method: 'DELETE',
    headers: jsonHeaders(),
  });
}

export async function loginWithMnemonic(mnemonic: string): Promise<Account> {
  const payload = await requestJson<AccountViewPayload>('/api/v1/accounts/login', {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ mnemonic }),
  });
  return mapAccount(payload);
}

export async function logoutAccount(): Promise<void> {
  await requestJson<void>('/api/v1/accounts/logout', {
    method: 'POST',
    headers: jsonHeaders(),
  });
}

export async function fetchCurrentAccount(): Promise<Account | null> {
  const response = await fetch(apiUrl('/api/v1/accounts/me'), {
    method: 'GET',
    credentials: 'include',
  });
  if (response.status === 401) {
    return null;
  }
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return mapAccount((await response.json()) as AccountViewPayload);
}

export async function updateShareSettings(
  isPublic: boolean,
  consentVersion: string,
): Promise<Account> {
  const payload = await requestJson<AccountViewPayload>('/api/v1/accounts/me/share', {
    method: 'PATCH',
    headers: jsonHeaders(),
    body: JSON.stringify({ is_public: isPublic, consent_version: consentVersion }),
  });
  return mapAccount(payload);
}
