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
