/** Account API client. Maps snake_case payloads to camelCase for the UI. */

export interface Account {
  publicId: string;
  isPublic: boolean;
  createdAt: string;
}

export interface AccountWithToken extends Account {
  accessToken: string;
}

const TOKEN_KEY = 'notmice.access_token';

interface AccountViewPayload {
  public_id: string;
  is_public: boolean;
  created_at: string;
}

interface SessionPayload extends AccountViewPayload {
  access_token: string;
  token_type: string;
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
  const response = await fetch(apiUrl(path), init);
  if (response.status === 204) {
    return undefined as T;
  }
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as T;
}

function jsonHeaders(token?: string): HeadersInit {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

export function readStoredToken(): string | null {
  try {
    const lasting = localStorage.getItem(TOKEN_KEY);
    if (lasting) {
      return lasting;
    }
    const legacy = sessionStorage.getItem(TOKEN_KEY);
    if (!legacy) {
      return null;
    }
    localStorage.setItem(TOKEN_KEY, legacy);
    sessionStorage.removeItem(TOKEN_KEY);
    return legacy;
  } catch {
    return null;
  }
}

export function storeToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  sessionStorage.removeItem(TOKEN_KEY);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
}

export const HEALTH_CONSENT_VERSION = '2026-09-28';
export const RESEARCH_CONSENT_VERSION = '2026-09-28';

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

export async function loginWithEmail(email: string, password: string): Promise<AccountWithToken> {
  const payload = await requestJson<SessionPayload>('/api/v1/accounts/login/email', {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ email, password }),
  });
  return {
    ...mapAccount(payload),
    accessToken: payload.access_token,
  };
}

export async function confirmEmail(token: string): Promise<AccountWithToken> {
  const payload = await requestJson<SessionPayload>('/api/v1/accounts/confirm', {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ token }),
  });
  return {
    ...mapAccount(payload),
    accessToken: payload.access_token,
  };
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

export async function downloadOwnExport(token: string, kind: 'json' | 'csv'): Promise<void> {
  const path = kind === 'json' ? '/api/v1/accounts/me/export.json' : '/api/v1/accounts/me/export.csv';
  const response = await fetch(apiUrl(path), { headers: jsonHeaders(token) });
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

export async function deleteOwnAccount(token: string): Promise<void> {
  await requestJson<void>('/api/v1/accounts/me', {
    method: 'DELETE',
    headers: jsonHeaders(token),
  });
}

export async function loginWithMnemonic(mnemonic: string): Promise<AccountWithToken> {
  const payload = await requestJson<SessionPayload>('/api/v1/accounts/login', {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ mnemonic }),
  });
  return {
    ...mapAccount(payload),
    accessToken: payload.access_token,
  };
}

export async function logoutAccount(token: string): Promise<void> {
  await requestJson<void>('/api/v1/accounts/logout', {
    method: 'POST',
    headers: jsonHeaders(token),
  });
}

export async function fetchCurrentAccount(token: string): Promise<Account> {
  const payload = await requestJson<AccountViewPayload>('/api/v1/accounts/me', {
    method: 'GET',
    headers: jsonHeaders(token),
  });
  return mapAccount(payload);
}

export async function updateShareSettings(
  token: string,
  isPublic: boolean
): Promise<Account> {
  const payload = await requestJson<AccountViewPayload>('/api/v1/accounts/me/share', {
    method: 'PATCH',
    headers: jsonHeaders(token),
    body: JSON.stringify({ is_public: isPublic }),
  });
  return mapAccount(payload);
}
