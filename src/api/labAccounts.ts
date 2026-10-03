export type LabVerificationStatus = 'pending' | 'verified' | 'rejected';
export type LabOrganizationType =
  | 'laboratory'
  | 'university'
  | 'research_institute'
  | 'company'
  | 'other';

export interface LabOrganization {
  id: string;
  name: string;
  organization_type: LabOrganizationType;
  country: string;
  verification_status: LabVerificationStatus;
  dua_version: string | null;
  current_dua_version: string | null;
  dua_accepted_at: string | null;
  verified_at: string | null;
  verification_reviewed_at: string | null;
}

export interface LabAccount {
  email: string;
  role: string;
  email_confirmed_at: string;
  organization: LabOrganization;
}

export interface LabRegistrationInput {
  organizationName: string;
  organizationType: LabOrganizationType;
  country: string;
  email: string;
  password: string;
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

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    credentials: 'include',
    headers: {
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...init.headers,
    },
  });
  if (response.status === 204) {
    return undefined as T;
  }
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as T;
}

export async function registerLab(input: LabRegistrationInput): Promise<void> {
  await request('/api/v1/lab/register', {
    method: 'POST',
    body: JSON.stringify({
      organization_name: input.organizationName,
      organization_type: input.organizationType,
      country: input.country,
      email: input.email,
      password: input.password,
    }),
  });
}

export async function loginLab(email: string, password: string): Promise<LabAccount> {
  return request<LabAccount>('/api/v1/lab/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function fetchLabAccount(): Promise<LabAccount | null> {
  const response = await fetch(apiUrl('/api/v1/lab/me'), {
    credentials: 'include',
  });
  if (response.status === 401) {
    return null;
  }
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as LabAccount;
}

export async function logoutLab(): Promise<void> {
  await request<void>('/api/v1/lab/logout', { method: 'POST' });
}

export async function acceptLabDua(): Promise<LabAccount> {
  return request<LabAccount>('/api/v1/lab/dua/accept', {
    method: 'POST',
    body: JSON.stringify({ accepted: true }),
  });
}
