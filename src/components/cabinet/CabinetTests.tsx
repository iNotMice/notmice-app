import React, { useEffect, useState } from 'react';
import { ChevronDown, FlaskConical, Trash2 } from 'lucide-react';
import { fetchOwnLabResults, type OwnLabResult } from '../../api/uploads';
import { fill } from '../../i18n/fill';
import { formatDate, formatNumber, formatValue } from '../../i18n/format';
import { useI18n } from '../../i18n/I18nProvider';
import { markerLabel, markerUnit } from '../../i18n/markerLabels';

interface CabinetTestsProps {
  /** Delete one confirmed panel; the caller keeps the rest of the app in step. */
  onDelete: (panelId: string) => Promise<void>;
  /** Show this panel in the PhenoAge index screen. */
  onOpenIndex: (panelId: string) => void;
}

function sortKey(result: OwnLabResult): string {
  return `${result.collectedAt ?? result.confirmedAt.slice(0, 10)}|${result.confirmedAt}`;
}

function interval(low: number | null, high: number | null, text: string | null, format: (v: number) => string): string {
  if (low !== null && high !== null) {
    return `${format(low)}–${format(high)}`;
  }
  if (high !== null) {
    return `< ${format(high)}`;
  }
  if (low !== null) {
    return `> ${format(low)}`;
  }
  return text ?? '—';
}

/** Every confirmed panel with all its values, newest first. */
export const CabinetTests: React.FC<CabinetTestsProps> = ({ onDelete, onOpenIndex }) => {
  const { m, locale } = useI18n();
  const copy = m.cabinet.tests;
  const [results, setResults] = useState<OwnLabResult[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState(false);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setFailed(false);
    void fetchOwnLabResults()
      .then((rows) => {
        if (!cancelled) {
          setResults([...rows].sort((a, b) => sortKey(b).localeCompare(sortKey(a))));
        }
      })
      .catch(() => {
        if (!cancelled) {
          setFailed(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [reload]);

  const remove = async (panelId: string) => {
    if (!window.confirm(copy.deleteConfirm)) {
      return;
    }
    setBusy(panelId);
    setDeleteError(false);
    try {
      await onDelete(panelId);
      setReload((value) => value + 1);
    } catch {
      setDeleteError(true);
    } finally {
      setBusy(null);
    }
  };

  const format = (value: number) => formatValue(value, locale);

  return (
    <section className="flex flex-col gap-4" aria-labelledby="cabinet-tests-title">
      <div>
        <h2 id="cabinet-tests-title" className="text-xl font-bold text-[#0b1c30]">
          {copy.title}
        </h2>
        <p className="mt-1 max-w-3xl text-base text-[#3f4850]">{copy.lead}</p>
      </div>
      {failed && (
        <p className="text-base text-[#ba1a1a]" role="alert">
          {copy.failed}
        </p>
      )}
      {deleteError && (
        <p className="text-base text-[#ba1a1a]" role="alert">
          {copy.deleteFailed}
        </p>
      )}
      {!results && !failed && <p className="text-base text-[#3f4850]">{copy.loading}</p>}
      {results && results.length === 0 && <p className="text-base text-[#3f4850]">{copy.empty}</p>}
      {results && results.length > 0 && (
        <ol className="flex flex-col gap-3">
          {results.map((result) => {
            const expanded = open === result.id;
            return (
              <li key={result.id} className="rounded-xl border border-[#e2e8f0] bg-[#ffffff]">
                <div className="flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between">
                  <div className="flex flex-col gap-1">
                    <p className="text-base font-semibold text-[#0b1c30]">
                      {result.collectedAt
                        ? fill(copy.collected, { date: formatDate(result.collectedAt, locale) })
                        : fill(copy.confirmed, { date: formatDate(result.confirmedAt, locale) })}
                      {' · '}
                      {result.labName ?? copy.unknownLab}
                    </p>
                    <p className="text-[15px] text-[#3f4850]">
                      {fill(copy.markerCount, { count: result.markerCount })}
                      {' · '}
                      {result.phenoAge === null
                        ? copy.notScored
                        : fill(copy.index, { value: formatNumber(result.phenoAge, locale) })}
                    </p>
                    {result.missingMarkers.length > 0 && (
                      <p className="text-sm text-[#3f4850]">
                        {fill(copy.missing, {
                          markers: result.missingMarkers.map((id) => markerLabel(id, m)).join(', '),
                        })}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      aria-expanded={expanded}
                      aria-controls={`panel-${result.id}`}
                      onClick={() => setOpen(expanded ? null : result.id)}
                      className="inline-flex items-center gap-1 rounded-md border border-[#cbd5e1] px-3 py-2 text-[15px] font-semibold text-[#0b1c30] hover:bg-[#eff4ff] cursor-pointer"
                    >
                      {expanded ? copy.hideValues : copy.showValues}
                      <ChevronDown className={`w-4 h-4 transition-transform ${expanded ? 'rotate-180' : ''}`} aria-hidden="true" />
                    </button>
                    {result.phenoAge !== null && (
                      <button
                        type="button"
                        onClick={() => onOpenIndex(result.id)}
                        className="inline-flex items-center gap-1 rounded-md border border-[#cbd5e1] px-3 py-2 text-[15px] font-semibold text-[#006194] hover:bg-[#eff4ff] cursor-pointer"
                      >
                        <FlaskConical className="w-4 h-4" aria-hidden="true" />
                        {copy.openIndex}
                      </button>
                    )}
                    <button
                      type="button"
                      disabled={busy === result.id}
                      onClick={() => void remove(result.id)}
                      className="inline-flex items-center gap-1 rounded-md border border-[#fecdd3] bg-[#fff1f2] px-3 py-2 text-[15px] font-semibold text-[#ba1a1a] hover:bg-[#ffe4e6] disabled:opacity-60 cursor-pointer"
                    >
                      <Trash2 className="w-4 h-4" aria-hidden="true" />
                      {copy.deleteAction}
                    </button>
                  </div>
                </div>
                {expanded && (
                  <div id={`panel-${result.id}`} className="overflow-x-auto border-t border-[#e2e8f0] px-4 pb-4">
                    <table className="mt-3 w-full min-w-[640px] text-left text-[15px]">
                      <thead>
                        <tr className="border-b border-[#e2e8f0] text-sm text-[#3f4850]">
                          <th className="py-2 pr-3 font-semibold">{copy.colMarker}</th>
                          <th className="py-2 pr-3 font-semibold">{copy.colPrinted}</th>
                          <th className="py-2 pr-3 font-semibold">{copy.colValue}</th>
                          <th className="py-2 pr-3 font-semibold">{copy.colReported}</th>
                          <th className="py-2 font-semibold">{copy.colInterval}</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#f1f5f9]">
                        {result.markers.map((marker, index) => (
                          <tr key={`${marker.rawName}-${index}`}>
                            <td className="py-2 pr-3 font-medium text-[#0b1c30]">
                              {marker.canonicalId ? (
                                markerLabel(marker.canonicalId, m)
                              ) : (
                                <span className="text-[#3f4850] italic">{copy.notMatched}</span>
                              )}
                            </td>
                            <td className="py-2 pr-3 text-[#3f4850]">{marker.rawName}</td>
                            <td className="py-2 pr-3 text-[#0b1c30]">
                              {format(marker.value)} {markerUnit(marker.canonicalId, marker.unit, m)}
                              {marker.outsideInterval && (
                                <span className="ml-2 inline-block rounded bg-[#fff6e0] px-1.5 py-0.5 text-xs font-semibold text-[#7a4b00]">
                                  {copy.outside}
                                </span>
                              )}
                            </td>
                            <td className="py-2 pr-3 text-[#3f4850]">
                              {marker.reportedValue === null
                                ? '—'
                                : `${format(marker.reportedValue)} ${marker.reportedUnit ?? ''}`.trim()}
                            </td>
                            <td className="py-2 text-[#3f4850]">
                              {interval(marker.referenceLow, marker.referenceHigh, marker.referenceText, format)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
};
