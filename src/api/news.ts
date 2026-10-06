/** Research-news client. Article pages are not downloaded in the browser. */

export type NewsKind = 'paper' | 'biohacking';

export interface NewsCard {
  id: string;
  title: string;
  source: string;
  publishedAt: string | null;
  snippet: string;
  url: string;
  kind: NewsKind;
  /** Title and snippet are a machine translation into the requested language. */
  translated: boolean;
  /** Source text; equal to title and snippet when nothing was translated. */
  originalTitle: string;
  originalSnippet: string;
}

export interface NewsFeed {
  items: NewsCard[];
  fetchedAt: string | null;
  stale: boolean;
  error: 'unavailable' | null;
  /** Some cards are still being translated; reading again shortly returns more. */
  translationPending: boolean;
}

interface NewsCardPayload {
  id?: unknown;
  title?: unknown;
  source?: unknown;
  published_at?: unknown;
  snippet?: unknown;
  url?: unknown;
  kind?: unknown;
  translated?: unknown;
  original_title?: unknown;
  original_snippet?: unknown;
}

interface NewsPayload {
  items?: unknown;
  fetched_at?: unknown;
  stale?: unknown;
  error?: unknown;
  translation_pending?: unknown;
}

function apiUrl(path: string): string {
  const base = import.meta.env.VITE_API_BASE_URL ?? '';
  return `${base}${path}`;
}

function isKind(value: unknown): value is NewsKind {
  return value === 'paper' || value === 'biohacking';
}

function httpUrl(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  try {
    const parsed = new URL(value);
    if (parsed.protocol === 'https:' || parsed.protocol === 'http:') {
      return value;
    }
  } catch {
    return null;
  }
  return null;
}

function asCard(value: NewsCardPayload): NewsCard | null {
  const url = httpUrl(value.url);
  if (typeof value.id !== 'string' || typeof value.title !== 'string' || !url || !isKind(value.kind)) {
    return null;
  }
  const publishedAt = typeof value.published_at === 'string' ? value.published_at : null;
  const snippet = typeof value.snippet === 'string' ? value.snippet : '';
  const translated = value.translated === true && typeof value.original_title === 'string';
  return {
    id: value.id,
    title: value.title,
    source: typeof value.source === 'string' ? value.source : '',
    publishedAt,
    snippet,
    url,
    kind: value.kind,
    translated,
    originalTitle: translated ? (value.original_title as string) : value.title,
    originalSnippet: translated && typeof value.original_snippet === 'string' ? value.original_snippet : snippet,
  };
}

/** Cards with titles and snippets machine-translated into ``language`` where possible. */
export async function fetchNews(language: string, signal?: AbortSignal): Promise<NewsFeed> {
  const query = new URLSearchParams({ lang: language });
  const response = await fetch(apiUrl(`/api/v1/news?${query.toString()}`), { signal });
  if (!response.ok) {
    throw new Error(`News request failed (${response.status})`);
  }
  const payload = (await response.json()) as NewsPayload;
  const items = Array.isArray(payload.items)
    ? payload.items.flatMap((item) => {
        const card = asCard(item as NewsCardPayload);
        return card ? [card] : [];
      })
    : [];
  return {
    items,
    fetchedAt: typeof payload.fetched_at === 'string' ? payload.fetched_at : null,
    stale: payload.stale === true,
    error: payload.error === 'unavailable' ? 'unavailable' : null,
    translationPending: payload.translation_pending === true,
  };
}
