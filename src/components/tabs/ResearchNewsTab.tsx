import React, { useEffect, useState } from 'react';
import { ExternalLink, Languages, Newspaper } from 'lucide-react';
import { fetchNews, type NewsFeed, type NewsKind } from '../../api/news';
import { useI18n } from '../../i18n/I18nProvider';
import { cardMatchesPanel, markerTags } from '../../utils/newsMarkers';

type NewsFilter = 'all' | NewsKind | 'mine';
type LoadStatus = 'loading' | 'ready' | 'failed';

/** While the server is still translating, read again quietly a few times. */
const TRANSLATION_POLL_MS = 4000;
const TRANSLATION_POLL_LIMIT = 8;

interface ResearchNewsTabProps {
  markerIds: readonly string[];
}

function formatPublished(value: string | null, locale: string): string | null {
  if (!value) {
    return null;
  }
  const parsed = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return new Intl.DateTimeFormat(locale, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(parsed);
}

export const ResearchNewsTab: React.FC<ResearchNewsTabProps> = ({ markerIds }) => {
  const { locale, m } = useI18n();
  const copy = m.news;
  const [feed, setFeed] = useState<NewsFeed | null>(null);
  const [status, setStatus] = useState<LoadStatus>('loading');
  const [filter, setFilter] = useState<NewsFilter>('all');
  const [reloadKey, setReloadKey] = useState(0);
  const [showOriginal, setShowOriginal] = useState<ReadonlySet<string>>(new Set());
  const [polls, setPolls] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setStatus('loading');
    void fetchNews(locale, controller.signal)
      .then((next) => {
        setFeed(next);
        setShowOriginal(new Set());
        setPolls(0);
        setStatus('ready');
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') {
          return;
        }
        setFeed(null);
        setStatus('failed');
      });
    return () => controller.abort();
  }, [reloadKey, locale]);

  useEffect(() => {
    if (!feed?.translationPending || polls >= TRANSLATION_POLL_LIMIT) {
      return undefined;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      // Quiet refresh: the cards stay on screen and only their text changes.
      void fetchNews(locale, controller.signal)
        .then((next) => {
          setFeed(next);
          setPolls((count) => count + 1);
        })
        .catch(() => setPolls(TRANSLATION_POLL_LIMIT));
    }, TRANSLATION_POLL_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [feed, polls, locale]);

  const toggleOriginal = (id: string) => {
    setShowOriginal((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const filters: { id: NewsFilter; label: string }[] = [
    { id: 'all', label: copy.filterAll },
    { id: 'paper', label: copy.filterPapers },
    { id: 'biohacking', label: copy.filterBiohacking },
    { id: 'mine', label: copy.filterMine },
  ];

  const decorated = (feed?.items ?? []).map((card) => ({
    card,
    // Marker tags match source-language terms, so they read the original text.
    tags: markerTags(card.originalTitle, card.originalSnippet),
  }));
  const visible = decorated.filter(({ card, tags }) => {
    if ((filter === 'paper' || filter === 'biohacking') && card.kind !== filter) {
      return false;
    }
    if (filter === 'mine' && !cardMatchesPanel(tags, markerIds)) {
      return false;
    }
    return true;
  });

  const unavailable = status === 'failed' || feed?.error === 'unavailable';

  return (
    <div className="w-full max-w-[1440px] mx-auto px-4 lg:px-8 py-8 flex flex-col gap-6">
      <div className="border-b border-[#e2e8f0] pb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="bg-[#cce5ff] text-[#004b73] font-['JetBrains_Mono'] text-xs font-semibold px-2 py-0.5 rounded">
            {copy.stage}
          </span>
          <span className="font-['JetBrains_Mono'] text-xs text-[#565e74]">{copy.stageMeta}</span>
        </div>
        <h1 className="font-['Inter'] text-2xl lg:text-3xl font-bold text-[#0b1c30]">{copy.title}</h1>
        <p className="font-['Inter'] text-sm text-[#3f4850] mt-1 max-w-2xl">{copy.lead}</p>
      </div>

      <p className="font-['Inter'] text-sm text-[#3f4850] bg-[#eff4ff] border border-[#dce9ff] rounded-lg px-4 py-3">
        {copy.disclaimer}
      </p>

      <div className="flex flex-wrap gap-2" role="group" aria-label={copy.title}>
        {filters.map((item) => {
          const selected = filter === item.id;
          return (
            <button
              key={item.id}
              type="button"
              aria-pressed={selected}
              onClick={() => setFilter(item.id)}
              className={`font-['Inter'] text-[13px] font-medium px-3 py-1.5 rounded cursor-pointer ${
                selected
                  ? 'bg-[#007bb9] text-[#ffffff]'
                  : 'bg-[#ffffff] text-[#3f4850] border border-[#e2e8f0] hover:bg-[#e5eeff]'
              }`}
            >
              {item.label}
            </button>
          );
        })}
      </div>

      {feed?.stale && status === 'ready' && !unavailable && (
        <p className="font-['Inter'] text-sm text-[#3f4850]">{copy.stale}</p>
      )}

      {status === 'loading' && (
        <p className="font-['Inter'] text-sm text-[#565e74]">{copy.loading}</p>
      )}

      {unavailable && status !== 'loading' && (
        <div className="bg-[#ffffff] border border-[#e2e8f0] rounded-lg p-5 flex flex-col items-start gap-3">
          <p className="font-['Inter'] text-sm text-[#3f4850]">{copy.unavailable}</p>
          <button
            type="button"
            onClick={() => setReloadKey((value) => value + 1)}
            className="font-['Inter'] text-sm font-medium text-[#006194] hover:underline cursor-pointer"
          >
            {copy.retry}
          </button>
        </div>
      )}

      {status === 'ready' && !unavailable && visible.length === 0 && (
        <p className="font-['Inter'] text-sm text-[#565e74]">
          {feed && feed.items.length === 0 ? copy.emptyFeed : copy.emptyFilter}
        </p>
      )}

      {status === 'ready' && !unavailable && visible.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {visible.map(({ card, tags }) => {
            const published = formatPublished(card.publishedAt, locale);
            const original = card.translated && showOriginal.has(card.id);
            const title = original ? card.originalTitle : card.title;
            const snippet = original ? card.originalSnippet : card.snippet;
            // Feeds are English; the original is marked so screen readers switch voice.
            const textLang = card.translated && !original ? undefined : 'en';
            return (
              <article
                key={card.id}
                className="bg-[#ffffff] border border-[#e2e8f0] rounded-lg p-4 flex flex-col gap-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="inline-flex items-center gap-1 font-['JetBrains_Mono'] text-[11px] uppercase tracking-wide text-[#004b73] bg-[#cce5ff] px-2 py-0.5 rounded">
                    <Newspaper className="w-3 h-3" />
                    {card.kind === 'paper' ? copy.kindPaper : copy.kindBiohacking}
                  </span>
                  {published && (
                    <time className="font-['JetBrains_Mono'] text-[11px] text-[#565e74]" dateTime={card.publishedAt ?? undefined}>
                      {published}
                    </time>
                  )}
                </div>
                <h2 lang={textLang} className="font-['Inter'] text-base font-semibold text-[#0b1c30] leading-snug">
                  {title}
                </h2>
                {snippet && (
                  <p lang={textLang} className="font-['Inter'] text-sm text-[#3f4850] leading-relaxed">
                    {snippet}
                  </p>
                )}
                {card.translated && (
                  <p className="flex flex-wrap items-center gap-x-2 gap-y-1 font-['Inter'] text-xs text-[#565e74]">
                    <span className="inline-flex items-center gap-1">
                      <Languages className="w-3.5 h-3.5" aria-hidden="true" />
                      {original ? copy.originalLabel : copy.machineTranslation}
                    </span>
                    <button
                      type="button"
                      onClick={() => toggleOriginal(card.id)}
                      aria-pressed={original}
                      className="font-medium text-[#006194] hover:underline cursor-pointer"
                    >
                      {original ? copy.showTranslation : copy.showOriginal}
                    </button>
                  </p>
                )}
                {card.source && (
                  <p className="font-['Inter'] text-xs text-[#565e74]">{card.source}</p>
                )}
                {tags.length > 0 && (
                  <ul className="flex flex-wrap gap-1.5">
                    {tags.map((id) => (
                      <li
                        key={id}
                        className="font-['JetBrains_Mono'] text-[11px] text-[#006194] bg-[#eff4ff] border border-[#dce9ff] px-1.5 py-0.5 rounded"
                      >
                        {m.biomarkers[id].shortName}
                      </li>
                    ))}
                  </ul>
                )}
                <a
                  href={card.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-auto inline-flex items-center gap-1 text-sm font-medium text-[#006194] hover:underline"
                >
                  {copy.openArticle}
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
};
