/**
 * Copy gate for the public interface (acceptance criteria 2, 6 and 7 of the
 * October 2026 home-page brief).
 *
 *   npm run check:copy
 *
 * 1. Banned claims: words that turn a research index into a medical promise,
 *    unverifiable superlatives, FDA, an unsourced "92%", a trademark sign.
 *    "Diagnosis" is allowed only next to a negation.
 * 2. The home page uses no technical terms (LOINC, pdfplumber, SHA-256, API, DUA).
 * 3. No empty strings; every translation keeps the English placeholders;
 *    Russian strings are not left in English.
 */
import { deMessages } from '../src/i18n/messages/de/index.ts';
import { enMessages } from '../src/i18n/messages/en/index.ts';
import { frMessages } from '../src/i18n/messages/fr/index.ts';
import { ruMessages } from '../src/i18n/messages/ru/index.ts';

type Entry = { path: string; value: string };

function flatten(node: unknown, prefix = ''): Entry[] {
  if (typeof node === 'string') {
    return [{ path: prefix, value: node }];
  }
  if (Array.isArray(node)) {
    return node.flatMap((item, index) => flatten(item, `${prefix}[${index}]`));
  }
  if (node && typeof node === 'object') {
    return Object.entries(node).flatMap(([key, value]) => flatten(value, prefix ? `${prefix}.${key}` : key));
  }
  return [];
}

const locales = { en: enMessages, de: deMessages, ru: ruMessages, fr: frMessages } as const;
type Locale = keyof typeof locales;

/** Negation words that may stand before "diagnosis" in the same sentence. */
const NEGATION: Record<Locale, RegExp> = {
  en: /\b(not|no|nor|never|without)\b|n't\b/i,
  de: /\b(kein\w*|nicht|ohne|weder)\b/i,
  ru: /(^|[^а-яё])(не|нет|без|ни)([^а-яё]|$)/i,
  fr: /(^|[^a-zà-ÿ])(ne|n['’]|pas|sans|aucun\w*|ni|non)([^a-zà-ÿ]|$)/i,
};

const DIAGNOSIS: Record<Locale, RegExp> = {
  en: /diagnos\w*/gi,
  de: /diagnos\w*/gi,
  ru: /диагноз\w*/gi,
  fr: /diagnosti\w*/gi,
};

/** Lists whose heading already says "what you will not get" / "is this ...?". */
const DIAGNOSIS_CONTEXT_ALLOWED = [/^instructions\.get\.notItems\[\d+\]$/, /^instructions\.faq\[\d+\]\.q$/];

const BANNED: { pattern: RegExp; reason: string }[] = [
  { pattern: /\bFDA\b/, reason: 'FDA reference (the company is in the EU)' },
  { pattern: /92\s?%/, reason: '"92%" without a source' },
  { pattern: /™/, reason: 'trademark sign without grounds' },
  { pattern: /угроз|\bthreat|bedrohung/i, reason: 'promise of early threat detection' },
  { pattern: /обнаружил|\bsystem detected|\bdetects? (a |the )?(risk|disease)/i, reason: '"the system detected" style claim' },
  { pattern: /крупнейш|\blargest\b|größte/i, reason: 'unverifiable "largest"' },
  { pattern: /самы[хй] точн|\bmost accurate\b|genaueste/i, reason: 'unverifiable "most accurate"' },
  { pattern: /полностью обезличен|fully anonymi[sz]ed|vollständig anonym/i, reason: 'rows are pseudonymous, not anonymous' },
  { pattern: /anonymi[sz]ed (rows|cohorts)|anonymisierte zeilen|обезличенн\w* строк/i, reason: 'rows are pseudonymous, not anonymous' },
  { pattern: /бесплатн|free of charge|\bfor free\b|\bfree tool\b|kostenlos/i, reason: '"free" is not decided yet' },
  { pattern: /биохакинг|biohacking/i, reason: 'word removed from the external vocabulary' },
  { pattern: /победить старение|defeat(ing)? aging|beat(ing)? aging|altern besiegen|vaincre le vieillissement/i, reason: 'decision 05.10.2026: "understand aging"' },
  { pattern: /супер-?ген|super-?gene/i, reason: 'the platform does not collect genetics' },
  { pattern: /лекарств\w* от старости|anti-aging drugs?/i, reason: 'reads as a promise of therapy' },
  { pattern: /скорост\w* старения|rate of (biological )?aging/i, reason: 'the index is an age at one test, not a rate' },
];

const HOME_TECH_TERMS = /\b(LOINC|pdfplumber|SHA-?256|API|DUA)\b/i;
/** Namespaces rendered on the home page itself (header and footer included). */
const HOME_PATHS = [/^home\./, /^nav\./, /^shell\.(footer\w*|dataDisclaimer)$/];
/** Footer strings that are defined but intentionally not rendered on any page. */
const HOME_UNUSED = [/^shell\.footerLoinc$/];

const PLACEHOLDER = /\{(\w+)\}/g;
const CYRILLIC = /[А-Яа-яЁё]/;
const LATIN_PHRASE = /[A-Za-z]{2,}(?:[ \-][A-Za-z]{2,}){2,}/;
/** Russian strings that are rightly Latin-only: citations, codes, file formats. */
const RU_LATIN_ALLOWED = [
  /^lifestyleUi\.(studyCitation|studyHref)$/,
  /^report\.citation$/,
  /^modals\.citationValue$/,
  /^upload\.parser$/,
  /^shell\.footerCitation$/,
  /^specialists\.data\.licenses\[\d+\]\.name$/,
];

const problems: string[] = [];
const enIndex = new Map(flatten(enMessages).map((entry) => [entry.path, entry.value]));

for (const [locale, messages] of Object.entries(locales) as [Locale, (typeof locales)[Locale]][]) {
  for (const { path, value } of flatten(messages)) {
    const where = `${locale}:${path}`;

    if (value.trim() === '') {
      problems.push(`${where} is empty`);
    }

    for (const { pattern, reason } of BANNED) {
      if (pattern.test(value)) {
        problems.push(`${where}: ${reason} → "${value}"`);
      }
    }

    if (!DIAGNOSIS_CONTEXT_ALLOWED.some((rule) => rule.test(path))) {
      for (const match of value.matchAll(DIAGNOSIS[locale])) {
        const index = match.index ?? 0;
        const sentenceStart = Math.max(
          value.lastIndexOf('.', index - 1),
          value.lastIndexOf('?', index - 1),
          value.lastIndexOf('!', index - 1),
          value.lastIndexOf(':', index - 1),
        );
        const before = value.slice(sentenceStart + 1, index);
        // German still shows the English text of sections rewritten in October 2026.
        const negations = locale === 'de' ? [NEGATION.de, NEGATION.en] : [NEGATION[locale]];
        if (!negations.some((negation) => negation.test(before))) {
          problems.push(`${where}: "${match[0]}" without a negation → "${value}"`);
        }
      }
    }

    if (HOME_PATHS.some((rule) => rule.test(path)) && !HOME_UNUSED.some((rule) => rule.test(path))) {
      const term = value.match(HOME_TECH_TERMS);
      if (term) {
        problems.push(`${where}: technical term "${term[0]}" on the home page`);
      }
    }

    if (locale !== 'en') {
      const english = enIndex.get(path);
      if (english !== undefined) {
        // Russian plural forms do not fit "{count} {unit}", so that one string may drop {unit}.
        const optional = path === 'sovereignty.collectionDates' && locale === 'ru' ? ['unit'] : [];
        const keys = (text: string) =>
          [...new Set([...text.matchAll(PLACEHOLDER)].map((m) => m[1]))].filter((key) => !optional.includes(key)).sort().join(',');
        const expected = keys(english);
        const actual = keys(value);
        if (expected !== actual) {
          problems.push(`${where}: placeholders {${actual}} differ from English {${expected}}`);
        }
      }
    }

    if (
      locale === 'ru' &&
      !CYRILLIC.test(value) &&
      LATIN_PHRASE.test(value.replace(PLACEHOLDER, '')) &&
      !RU_LATIN_ALLOWED.some((rule) => rule.test(path))
    ) {
      problems.push(`${where}: looks untranslated → "${value}"`);
    }
  }
}

if (problems.length > 0) {
  console.error(`check:copy found ${problems.length} problem(s):`);
  for (const problem of problems) {
    console.error(`  - ${problem}`);
  }
  process.exit(1);
}
console.log('check:copy: all locales pass (banned claims, home-page terms, empty strings, placeholders).');
