/** Supported UI languages. Polish joins this list only after its dictionary exists. */
export const SUPPORTED_LOCALES = [
  { id: 'en', code: 'EN', label: 'English' },
  { id: 'de', code: 'DE', label: 'Deutsch' },
  { id: 'ru', code: 'RU', label: 'Русский' },
  { id: 'fr', code: 'FR', label: 'Français' },
] as const;

export type LocaleId = (typeof SUPPORTED_LOCALES)[number]['id'];

export const DEFAULT_LOCALE: LocaleId = 'en';

export const LOCALE_STORAGE_KEY = 'notmice.locale';

export function isLocaleId(value: string | null): value is LocaleId {
  return SUPPORTED_LOCALES.some((locale) => locale.id === value);
}

/** First supported language the browser asks for, by its primary subtag. */
export function localeFromBrowser(languages: readonly string[]): LocaleId | null {
  for (const tag of languages) {
    const primary = tag.toLowerCase().split('-')[0] ?? '';
    if (isLocaleId(primary)) {
      return primary;
    }
  }
  return null;
}

/** Sections a locale still shows in English, until their translation exists. */
const ENGLISH_FALLBACK: Partial<Record<LocaleId, readonly string[]>> = {
  de: ['home', 'specialists', 'instructions', 'cabinet'],
};

/** `lang` for a section root: "en" when the locale shows that section in English. */
export function sectionLang(locale: LocaleId, namespace: string): 'en' | undefined {
  return ENGLISH_FALLBACK[locale]?.includes(namespace) ? 'en' : undefined;
}
