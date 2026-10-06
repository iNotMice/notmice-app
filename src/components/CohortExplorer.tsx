import { useCallback, useEffect, useState } from 'react';
import { LoaderCircle, Search, ShieldCheck } from 'lucide-react';
import {
  fetchCohortFacets,
  queryCohort,
  type CohortFacet,
  type CohortFacets,
  type CohortQueryInput,
  type CohortQueryResult,
} from '../api/labCohorts';
import { LOINC_TO_MARKER } from '../data/loincIndex';
import { getActiveI18n } from '../i18n/catalog';
import { markerLabel } from '../i18n/markerLabels';
import type { AppMessages } from '../i18n/messages/en';

type CohortCopy = AppMessages['laboratory']['explorer'];

/** Marker name in the interface language, then its LOINC code. */
function loincLabel(code: string): string {
  const markerId = LOINC_TO_MARKER[code];
  return markerId ? `${markerLabel(markerId, getActiveI18n().messages)} · ${code}` : code;
}

function countryLabel(code: string): string {
  try {
    return new Intl.DisplayNames([getActiveI18n().locale], { type: 'region' }).of(code) ?? code;
  } catch {
    return code;
  }
}

const selectionLimits = {
  markers: 5,
  countries: 20,
  conditions: 10,
} as const;

function displayCode(value: string): string {
  return value.replaceAll('_', ' ');
}

function initialQuery(): CohortQueryInput {
  return {
    markers: [],
    sex_at_birth: [],
    age_bands: [],
    countries: [],
    conditions: [],
    collected_from: null,
    collected_to: null,
  };
}

function CheckboxFacet({
  title,
  options,
  selected,
  limit,
  disabled,
  onToggle,
  label,
}: {
  title: string;
  options: CohortFacet[];
  selected: string[];
  limit?: number;
  disabled?: boolean;
  onToggle: (value: string) => void;
  label: (value: string) => string;
}) {
  return (
    <fieldset disabled={disabled}>
      <legend className="mb-2 text-sm font-semibold text-[#31465b]">{title}</legend>
      {options.length === 0 ? (
        <p className="text-xs text-[#8190a0]">—</p>
      ) : (
        <div className="max-h-44 space-y-1.5 overflow-y-auto pr-1">
          {options.map((option) => {
            const checked = selected.includes(option.value);
            const atLimit = limit !== undefined && selected.length >= limit && !checked;
            return (
              <label
                key={option.value}
                className={`flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-sm ${
                  atLimit ? 'text-[#9aa7b4]' : 'text-[#465b70] hover:bg-[#f2f7fb]'
                }`}
              >
                <span className="flex min-w-0 items-center gap-2">
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={atLimit}
                    onChange={() => onToggle(option.value)}
                    className="h-4 w-4 rounded border-[#bdcbd8] text-[#006194] focus:ring-[#1673a5]"
                  />
                  <span className="truncate">{label(option.value)}</span>
                </span>
                <span className="shrink-0 text-xs text-[#8493a3]">{option.count}+</span>
              </label>
            );
          })}
        </div>
      )}
      {limit !== undefined && (
        <p className="mt-1.5 text-xs text-[#8190a0]">{selected.length}/{limit}</p>
      )}
    </fieldset>
  );
}

function AggregateResult({
  result,
  copy,
}: {
  result: CohortQueryResult;
  copy: CohortCopy;
}) {
  if (result.suppressed) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900" role="status">
        {copy.suppressed}
      </div>
    );
  }

  return (
    <div className="space-y-4" aria-live="polite">
      <div className="rounded-xl border border-[#dce5ef] bg-white p-4">
        <p className="text-sm text-[#607286]">{copy.cohortSize}</p>
        <p className="mt-1 text-3xl font-bold text-[#0b1c30]">
          {result.cohort_size?.toLocaleString() ?? '—'}
        </p>
        <p className="mt-1 text-xs text-[#8190a0]">{copy.roundedCount}</p>
      </div>

      {result.markers.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[#cbd8e4] p-5 text-sm leading-6 text-[#62758a]">
          {copy.noMarkers}
        </div>
      ) : (
        <div className="space-y-3">
          {result.markers.map((marker, index) => (
            <article
              key={`${marker.loinc_code}:${marker.unit ?? 'unknown'}:${index}`}
              className="rounded-xl border border-[#dce5ef] bg-white p-4"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h4 className="font-semibold text-[#18334b]">
                  {LOINC_TO_MARKER[marker.loinc_code]
                    ? markerLabel(LOINC_TO_MARKER[marker.loinc_code], getActiveI18n().messages)
                    : (marker.canonical_name ?? marker.loinc_code)}
                </h4>
                <span className="font-mono text-xs text-[#74869a]">{marker.loinc_code}</span>
              </div>
              {marker.n === null ? (
                <p className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
                  {copy.markerSuppressed}
                </p>
              ) : (
                <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
                  {[
                    [copy.sampleSize, `${marker.n}+`],
                    [copy.mean, marker.mean?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? '—'],
                    [copy.median, marker.median?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? '—'],
                    [copy.percentile25, marker.p25?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? '—'],
                    [copy.percentile75, marker.p75?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? '—'],
                  ].map(([labelText, value]) => (
                    <div key={labelText} className="rounded-lg bg-[#f5f8fb] px-3 py-2">
                      <p className="text-xs text-[#718398]">{labelText}</p>
                      <p className="mt-1 font-semibold tabular-nums text-[#203d56]">{value}</p>
                    </div>
                  ))}
                </div>
              )}
              {marker.unit && <p className="mt-2 text-xs text-[#8190a0]">{copy.unit}: {marker.unit}</p>}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

export function CohortExplorer({
  copy,
}: {
  copy: CohortCopy;
}) {
  const [facets, setFacets] = useState<CohortFacets | null>(null);
  const [query, setQuery] = useState<CohortQueryInput>(initialQuery);
  const [result, setResult] = useState<CohortQueryResult | null>(null);
  const [loadingFacets, setLoadingFacets] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadFacets = useCallback(async () => {
    setLoadingFacets(true);
    setError(null);
    try {
      setFacets(await fetchCohortFacets());
    } catch (err) {
      setError(err instanceof Error ? err.message : copy.loadFacetsFailed);
    } finally {
      setLoadingFacets(false);
    }
  }, [copy.loadFacetsFailed]);

  useEffect(() => {
    void loadFacets();
  }, [loadFacets]);

  const toggle = (key: 'markers' | 'countries' | 'conditions', value: string) => {
    setResult(null);
    setQuery((current) => {
      const selected = current[key];
      return {
        ...current,
        [key]: selected.includes(value)
          ? selected.filter((item) => item !== value)
          : [...selected, value],
      };
    });
  };

  const toggleProfile = (key: 'sex_at_birth' | 'age_bands', value: string) => {
    setResult(null);
    setQuery((current) => {
      const selected = current[key];
      return {
        ...current,
        [key]: selected.includes(value)
          ? selected.filter((item) => item !== value)
          : [...selected, value],
      };
    });
  };

  const submitQuery = async () => {
    setSearching(true);
    setError(null);
    setResult(null);
    try {
      const nextResult = await queryCohort(query);
      setResult(nextResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : copy.queryFailed);
    } finally {
      setSearching(false);
    }
  };

  const canSubmit = !loadingFacets && facets !== null && !searching;

  return (
    <section className="mt-6 rounded-2xl border border-[#dce5ef] bg-[#f8fbfd] p-4 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 text-[#006194]">
            <Search className="h-5 w-5" />
            <h3 className="text-lg font-bold text-[#18334b]">{copy.title}</h3>
          </div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[#62758a]">{copy.description}</p>
        </div>
        <div className="inline-flex items-start gap-2 rounded-lg border border-[#d6e5ef] bg-white px-3 py-2 text-xs leading-5 text-[#607286]">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#1673a5]" />
          <span>{copy.privacy}</span>
        </div>
      </div>

      {error && (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800" role="alert">
          <span>{error}</span>
          {facets === null && (
            <button type="button" onClick={() => void loadFacets()} className="font-semibold underline">
              {copy.retry}
            </button>
          )}
        </div>
      )}

      {loadingFacets ? (
        <div className="flex min-h-32 items-center justify-center text-sm text-[#62758a]" role="status">
          <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
          {copy.loadingFacets}
        </div>
      ) : facets ? (
        <>
          <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            <CheckboxFacet
              title={copy.markers}
              options={facets.markers}
              selected={query.markers}
              limit={selectionLimits.markers}
              disabled={searching}
              onToggle={(value) => toggle('markers', value)}
              label={loincLabel}
            />
            <CheckboxFacet
              title={copy.sexAtBirth}
              options={facets.sex_at_birth}
              selected={query.sex_at_birth}
              disabled={searching}
              onToggle={(value) => toggleProfile('sex_at_birth', value)}
              label={(value) => copy.sexLabels[value as keyof typeof copy.sexLabels]}
            />
            <CheckboxFacet
              title={copy.ageBands}
              options={facets.age_bands}
              selected={query.age_bands}
              disabled={searching}
              onToggle={(value) => toggleProfile('age_bands', value)}
              label={(value) => copy.ageLabels[value as keyof typeof copy.ageLabels]}
            />
            <CheckboxFacet
              title={copy.countries}
              options={facets.countries}
              selected={query.countries}
              limit={selectionLimits.countries}
              disabled={searching}
              onToggle={(value) => toggle('countries', value)}
              label={countryLabel}
            />
            <CheckboxFacet
              title={copy.conditions}
              options={facets.conditions}
              selected={query.conditions}
              limit={selectionLimits.conditions}
              disabled={searching}
              onToggle={(value) => toggle('conditions', value)}
              label={(value) => copy.conditionLabels[value as keyof typeof copy.conditionLabels] ?? displayCode(value)}
            />
          </div>
          <fieldset disabled={searching} className="mt-6 grid gap-4 rounded-xl border border-[#e1e8ef] bg-white p-4 sm:grid-cols-2">
            <label className="text-sm font-medium text-[#31465b]">
              {copy.collectedFrom}
              <input
                type="date"
                value={query.collected_from ?? ''}
                max={query.collected_to || undefined}
                onChange={(event) => {
                  setResult(null);
                  setQuery((current) => ({ ...current, collected_from: event.target.value || null }));
                }}
                className="mt-1.5 block w-full rounded-lg border border-[#ccd8e3] px-3 py-2 text-sm outline-none focus:border-[#1673a5] focus:ring-2 focus:ring-[#1673a5]/15"
              />
            </label>
            <label className="text-sm font-medium text-[#31465b]">
              {copy.collectedTo}
              <input
                type="date"
                value={query.collected_to ?? ''}
                min={query.collected_from || undefined}
                onChange={(event) => {
                  setResult(null);
                  setQuery((current) => ({ ...current, collected_to: event.target.value || null }));
                }}
                className="mt-1.5 block w-full rounded-lg border border-[#ccd8e3] px-3 py-2 text-sm outline-none focus:border-[#1673a5] focus:ring-2 focus:ring-[#1673a5]/15"
              />
            </label>
            <p className="text-xs leading-5 text-[#8190a0] sm:col-span-2">{copy.periodHelp}</p>
          </fieldset>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => void submitQuery()}
              disabled={!canSubmit}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#006194] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#004e78] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {searching ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              {searching ? copy.searching : copy.search}
            </button>
            <button
              type="button"
              onClick={() => {
                setQuery(initialQuery());
                setResult(null);
                setError(null);
              }}
              disabled={searching}
              className="rounded-lg border border-[#ccd8e3] bg-white px-4 py-2.5 text-sm font-semibold text-[#526579] hover:bg-[#f5f8fb] disabled:opacity-60"
            >
              {copy.clearFilters}
            </button>
            <p className="text-xs text-[#8190a0]">{copy.queryBudget}</p>
          </div>
        </>
      ) : null}

      {result && (
        <div className="mt-6 border-t border-[#dce5ef] pt-5">
          <h4 className="mb-3 text-base font-bold text-[#18334b]">{copy.results}</h4>
          <AggregateResult result={result} copy={copy} />
        </div>
      )}
    </section>
  );
}
