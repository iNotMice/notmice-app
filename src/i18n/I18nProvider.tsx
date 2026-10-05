import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { BRAND_NAME } from '../config/site';
import { setActiveI18n } from './catalog';
import { fill } from './fill';
import {
  DEFAULT_LOCALE,
  isLocaleId,
  localeFromBrowser,
  LOCALE_STORAGE_KEY,
  SUPPORTED_LOCALES,
  type LocaleId,
} from './locales';
import { enMessages, type AppMessages } from './messages/en';
import { deMessages } from './messages/de';
import { ruMessages } from './messages/ru';

const dictionaries: Record<LocaleId, AppMessages> = {
  en: enMessages,
  de: deMessages,
  ru: ruMessages,
};

function readStoredLocale(): LocaleId {
  try {
    const raw = localStorage.getItem(LOCALE_STORAGE_KEY);
    if (isLocaleId(raw)) {
      return raw;
    }
  } catch {
    // Storage can be blocked. The browser language decides below.
  }
  try {
    return localeFromBrowser(navigator.languages ?? [navigator.language]) ?? DEFAULT_LOCALE;
  } catch {
    return DEFAULT_LOCALE;
  }
}

type I18nValue = {
  locale: LocaleId;
  setLocale: (locale: LocaleId) => void;
  m: AppMessages;
  locales: typeof SUPPORTED_LOCALES;
};

const I18nContext = createContext<I18nValue | null>(null);

export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [locale, setLocaleState] = useState<LocaleId>(() => {
    const initial = readStoredLocale();
    setActiveI18n(initial, dictionaries[initial]);
    return initial;
  });

  const m = dictionaries[locale];

  useEffect(() => {
    setActiveI18n(locale, m);
    document.documentElement.lang = locale;
    document.title = fill(m.shell.documentTitle, { brand: BRAND_NAME });
  }, [locale, m]);

  const setLocale = (next: LocaleId) => {
    try {
      localStorage.setItem(LOCALE_STORAGE_KEY, next);
    } catch {
      // The choice still applies for this visit.
    }
    setLocaleState(next);
  };

  const value = useMemo(
    () => ({ locale, setLocale, m, locales: SUPPORTED_LOCALES }),
    [locale, m],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
};

export function useI18n(): I18nValue {
  const value = useContext(I18nContext);
  if (!value) {
    throw new Error('useI18n must be used within I18nProvider');
  }
  return value;
}
