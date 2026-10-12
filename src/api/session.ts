/**
 * Notice when the server stops accepting the participant session.
 *
 * Sessions end after 12 hours, on sign-out elsewhere or after a password
 * change, while an open tab still shows "signed in". A 401 from a private
 * participant endpoint is turned into one window event; the app then signs
 * the screen out and opens sign-in instead of showing a generic load error.
 */

export const SESSION_EXPIRED_EVENT = 'notmice:session-expired';

/** Endpoints that answer 401 only because the participant session is gone. */
const PRIVATE_PATHS = ['/api/v1/accounts/me', '/api/v1/uploads', '/api/v1/protocol'];

function pathOf(input: RequestInfo | URL): string {
  const raw = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
  try {
    return new URL(raw, window.location.origin).pathname;
  } catch {
    return raw;
  }
}

/** True for a 401 that means "the participant session ended". */
export function isSessionExpiry(path: string, status: number): boolean {
  return status === 401 && PRIVATE_PATHS.some((prefix) => path.startsWith(prefix));
}

let installed = false;

/** Wrap fetch once so every API client reports an ended session the same way. */
export function installSessionWatch(): void {
  if (installed || typeof window === 'undefined') {
    return;
  }
  installed = true;
  const original = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const response = await original(input, init);
    if (isSessionExpiry(pathOf(input), response.status)) {
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    }
    return response;
  };
}
