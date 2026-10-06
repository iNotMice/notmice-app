import type { LocaleId } from './locales';

/** Locale-aware number with a fixed number of decimals, e.g. 51,3 in Russian. */
export function formatNumber(value: number, locale: LocaleId, digits = 1): string {
  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

/** Signed difference in years: +6,3 or −2,0. */
export function formatSigned(value: number, locale: LocaleId, digits = 1): string {
  const body = formatNumber(Math.abs(value), locale, digits);
  if (value > 0) {
    return `+${body}`;
  }
  if (value < 0) {
    return `\u2212${body}`;
  }
  return body;
}

/** Up to two decimals, no trailing zeros: 1,5 or 104 in Russian. */
export function formatValue(value: number, locale: LocaleId): string {
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(value);
}

/**
 * A calendar date such as "1 марта 2026 г." from "2026-03-01" or an ISO timestamp.
 * Date-only strings are read as local dates so they never shift by a day.
 */
export function formatDate(value: string, locale: LocaleId, style: 'long' | 'short' = 'long'): string {
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  const parsed = dateOnly
    ? new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]))
    : new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  const options: Intl.DateTimeFormatOptions =
    style === 'short'
      ? { day: '2-digit', month: '2-digit', year: 'numeric' }
      : { day: 'numeric', month: 'long', year: 'numeric' };
  return new Intl.DateTimeFormat(locale, options).format(parsed);
}
