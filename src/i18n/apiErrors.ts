import { getActiveI18n } from './catalog';
import type { AppMessages } from './messages/en';

type ApiErrorKey = keyof AppMessages['shell']['apiErrors'];

/** Fixed `detail` strings the API returns, mapped to a translated message. */
const KNOWN_DETAILS: Record<string, ApiErrorKey> = {
  'Invalid email or password': 'invalidCredentials',
  'Invalid laboratory authentication': 'invalidCredentials',
  'Invalid or expired token': 'linkExpired',
  'Invalid or expired confirmation token': 'linkExpired',
  'Rate limit exceeded': 'rateLimited',
  'Invalid email address': 'invalidEmail',
  'Required consent is missing': 'consentMissing',
  'Consent version is not current': 'consentOutdated',
  'Invalid recovery phrase': 'invalidPhrase',
  'Not authenticated': 'notSignedIn',
  'Current health-data consent is required': 'healthConsentRequired',
  'Laboratory email confirmation is required': 'labConfirmRequired',
  'The current laboratory agreement has not been approved': 'dataAccessClosed',
  'Organization verification and current DUA acceptance are required': 'dataAccessClosed',
  'Unsupported file type': 'unsupportedFile',
  'File too large': 'fileTooLarge',
  'Empty file': 'emptyFile',
  'Could not read image': 'unreadableImage',
  'No numeric markers found': 'noMarkers',
  'Extract session expired': 'sessionExpired',
  'Upload not found': 'sessionExpired',
  'Vision provider is not configured': 'recognitionUnavailable',
  'Local redaction engine is not available': 'recognitionUnavailable',
  'Extraction timed out': 'recognitionTimeout',
  'Extraction failed': 'recognitionFailed',
};

const STATUS_ONLY = /^Request failed \((\d{3})\)$/;

/**
 * Turn an error thrown by an API client into text for the current language.
 *
 * Known API messages are translated. A bare status becomes a rate-limit or
 * server message. Anything else falls back to `fallback`, except in English,
 * where the API's own sentence is already readable.
 */
export function localizeApiError(error: unknown, fallback: string): string {
  const { locale, messages } = getActiveI18n();
  const copy = messages.shell.apiErrors;
  if (!(error instanceof Error) || !error.message) {
    return fallback;
  }
  const known = KNOWN_DETAILS[error.message];
  if (known) {
    return copy[known];
  }
  const status = STATUS_ONLY.exec(error.message);
  if (status) {
    const code = Number(status[1]);
    if (code === 429) {
      return copy.rateLimited;
    }
    return code >= 500 ? copy.serverUnavailable : fallback;
  }
  if (error instanceof TypeError) {
    return copy.serverUnavailable;
  }
  return locale === 'en' ? error.message : fallback;
}
