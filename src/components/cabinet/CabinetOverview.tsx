import React, { useCallback, useEffect, useState } from 'react';
import { ArrowRight, CalendarDays, Download, FileUp, NotebookPen, ShieldCheck } from 'lucide-react';
import { CabinetOverview as Overview, fetchCabinet } from '../../api/cabinet';
import { downloadOwnExport } from '../../api/accounts';
import { TabType } from '../../types';
import { fill } from '../../i18n/fill';
import { formatDate, formatNumber, formatSigned, formatValue } from '../../i18n/format';
import { useI18n } from '../../i18n/I18nProvider';
import { markerLabel, markerUnit } from '../../i18n/markerLabels';

interface CabinetOverviewProps {
  navigate: (tab: TabType) => void;
}

const card = 'rounded-xl border border-[#e2e8f0] bg-[#ffffff] p-5 flex flex-col gap-3';
const h2 = "font-['Inter'] text-lg font-bold text-[#0b1c30]";

/** First page of the personal account: what is stored, in counts and dates. */
export const CabinetOverview: React.FC<CabinetOverviewProps> = ({ navigate }) => {
  const { m, locale } = useI18n();
  const copy = m.cabinet.overview;
  const [data, setData] = useState<Overview | null>(null);
  const [failed, setFailed] = useState(false);
  const [exportError, setExportError] = useState(false);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setFailed(false);
    void fetchCabinet(controller.signal)
      .then(setData)
      .catch((err: unknown) => {
        if (!(err instanceof DOMException && err.name === 'AbortError')) {
          setFailed(true);
        }
      });
    return () => controller.abort();
  }, [reload]);

  const download = useCallback((kind: 'json' | 'csv') => {
    setExportError(false);
    void downloadOwnExport(kind).catch(() => setExportError(true));
  }, []);

  if (failed) {
    return (
      <div className={card} role="alert">
        <p className="text-base text-[#ba1a1a]">{copy.failed}</p>
        <button
          type="button"
          onClick={() => setReload((value) => value + 1)}
          className="self-start text-base font-semibold text-[#006194] underline cursor-pointer"
        >
          {copy.retry}
        </button>
      </div>
    );
  }
  if (!data) {
    return <p className="text-base text-[#3f4850]">{copy.loading}</p>;
  }

  const { account, history, latestIndex, previousIndex, markers, journal, consents } = data;
  const status = (on: boolean) => (
    <span className={`font-semibold ${on ? 'text-[#006947]' : 'text-[#3f4850]'}`}>{on ? copy.on : copy.off}</span>
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 items-start">
      <div className="lg:col-span-2 flex flex-col gap-5">
        {history.panelCount === 0 ? (
          <section className={card}>
            <h2 className={h2}>{copy.emptyTitle}</h2>
            <p className="text-base text-[#3f4850]">{copy.emptyBody}</p>
            <button
              type="button"
              onClick={() => navigate('upload-lab')}
              className="self-start inline-flex items-center gap-2 rounded-md bg-[#006194] px-5 py-2.5 text-base font-semibold text-[#ffffff] hover:bg-[#004b73] cursor-pointer"
            >
              <FileUp className="w-5 h-5" aria-hidden="true" />
              {copy.upload}
            </button>
          </section>
        ) : (
          <section className={card} aria-labelledby="cabinet-history">
            <h2 id="cabinet-history" className={h2}>
              {copy.historyTitle}
            </h2>
            <dl className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                [copy.panels, String(history.panelCount)],
                [
                  copy.period,
                  history.firstObservedOn && history.lastObservedOn
                    ? fill(copy.periodValue, {
                        from: formatDate(history.firstObservedOn, locale, 'short'),
                        to: formatDate(history.lastObservedOn, locale, 'short'),
                      })
                    : '—',
                ],
                [copy.laboratories, String(history.laboratoryCount)],
                [copy.repeat, String(history.repeatMarkerCount)],
              ].map(([label, value]) => (
                <div key={label} className="rounded-lg bg-[#f8f9ff] p-3">
                  <dt className="text-sm text-[#3f4850]">{label}</dt>
                  <dd className="mt-1 text-lg font-bold text-[#0b1c30]">{value}</dd>
                </div>
              ))}
            </dl>
            {history.unmappedMarkerCount > 0 && (
              <p className="text-sm text-[#3f4850]">
                {copy.unmapped}: {history.unmappedMarkerCount}
              </p>
            )}
          </section>
        )}

        {history.panelCount > 0 && (
          <section className={card} aria-labelledby="cabinet-index">
            <h2 id="cabinet-index" className={h2}>
              {copy.indexTitle}
            </h2>
            {latestIndex ? (
              <>
                <p className="inline-flex items-center gap-2 text-sm text-[#3f4850]">
                  <CalendarDays className="w-4 h-4" aria-hidden="true" />
                  {fill(copy.fromTest, { date: formatDate(latestIndex.observedOn, locale) })}
                </p>
                <dl className="grid grid-cols-3 gap-3 rounded-lg border border-[#dce9ff] bg-[#f8fbff] p-3">
                  <div>
                    <dt className="text-sm text-[#3f4850]">{copy.passportAge}</dt>
                    <dd className="text-2xl font-bold text-[#0b1c30]">
                      {latestIndex.chronologicalAge === null ? '—' : formatNumber(latestIndex.chronologicalAge, locale)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm text-[#3f4850]">{copy.indexAge}</dt>
                    <dd className="text-2xl font-bold text-[#006194]">{formatNumber(latestIndex.phenoAge, locale)}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-[#3f4850]">{copy.difference}</dt>
                    <dd className="text-2xl font-bold text-[#0b1c30]">{formatSigned(latestIndex.ageDelta, locale)}</dd>
                  </div>
                </dl>
                {previousIndex && (
                  <p className="text-[15px] text-[#3f4850]">
                    {fill(copy.previousChange, {
                      date: formatDate(previousIndex.observedOn, locale),
                      change: formatSigned(latestIndex.phenoAge - previousIndex.phenoAge, locale),
                    })}
                  </p>
                )}
                <p className="text-sm text-[#3f4850]">{m.shell.disclaimer}</p>
              </>
            ) : (
              <p className="text-[15px] text-[#3f4850]">{copy.noIndex}</p>
            )}
            <div className="rounded-lg bg-[#f8f9ff] p-3">
              {history.latestMissingMarkers.length === 0 ? (
                <p className="text-[15px] text-[#006947]">{copy.allPresent}</p>
              ) : (
                <>
                  <p className="text-[15px] font-semibold text-[#0b1c30]">{copy.missingTitle}</p>
                  <p className="text-[15px] text-[#3f4850]">
                    {history.latestMissingMarkers.map((id) => markerLabel(id, m)).join(', ')}
                  </p>
                </>
              )}
            </div>
          </section>
        )}

        {markers.length > 0 && (
          <section className={card} aria-labelledby="cabinet-markers">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 id="cabinet-markers" className={h2}>
                {copy.markersTitle}
              </h2>
              <button
                type="button"
                onClick={() => navigate('biomarker-history')}
                className="inline-flex items-center gap-1 text-[15px] font-semibold text-[#006194] hover:underline cursor-pointer"
              >
                {copy.openMarkers}
                <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] text-left text-[15px]">
                <thead>
                  <tr className="border-b border-[#e2e8f0] text-sm text-[#3f4850]">
                    <th className="py-2 pr-3 font-semibold">{copy.colMarker}</th>
                    <th className="py-2 pr-3 font-semibold">{copy.colValue}</th>
                    <th className="py-2 pr-3 font-semibold">{copy.colDate}</th>
                    <th className="py-2 font-semibold">{copy.colCount}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#f1f5f9]">
                  {markers.map((marker) => (
                    <tr key={marker.canonicalId}>
                      <td className="py-2 pr-3 font-medium text-[#0b1c30]">{markerLabel(marker.canonicalId, m)}</td>
                      <td className="py-2 pr-3 text-[#0b1c30]">
                        {formatValue(marker.latestValue, locale)} {markerUnit(marker.canonicalId, marker.latestUnit, m)}
                        {marker.latestOutsideInterval && (
                          <span className="ml-2 inline-block rounded bg-[#fff6e0] px-1.5 py-0.5 text-xs font-semibold text-[#7a4b00]">
                            {copy.outside}
                          </span>
                        )}
                      </td>
                      <td className="py-2 pr-3 whitespace-nowrap text-[#3f4850]">{formatDate(marker.latestOn, locale, 'short')}</td>
                      <td className="py-2 text-[#3f4850]">{marker.measurements}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-sm text-[#3f4850]">{copy.markersNote}</p>
          </section>
        )}
      </div>

      <aside className="flex flex-col gap-5">
        <section className={card} aria-labelledby="cabinet-account">
          <h2 id="cabinet-account" className={h2}>
            {copy.accountTitle}
          </h2>
          <ul className="flex flex-col gap-1.5 text-[15px] text-[#3f4850]">
            <li>{fill(copy.since, { date: formatDate(account.createdAt, locale) })}</li>
            <li className="break-all">
              {account.signInMethod === 'email' && account.email
                ? fill(copy.signInEmail, { email: account.email })
                : copy.signInPhrase}
            </li>
            <li>{fill(copy.sessions, { count: account.activeSessions })}</li>
          </ul>
          <button
            type="button"
            onClick={() => navigate('cabinet-security')}
            className="self-start inline-flex items-center gap-1 text-[15px] font-semibold text-[#006194] hover:underline cursor-pointer"
          >
            {m.cabinet.nav.security}
            <ArrowRight className="w-4 h-4" aria-hidden="true" />
          </button>
        </section>

        <section className={card} aria-labelledby="cabinet-privacy">
          <h2 id="cabinet-privacy" className={`${h2} inline-flex items-center gap-2`}>
            <ShieldCheck className="w-5 h-5 text-[#006947]" aria-hidden="true" />
            {copy.privacyTitle}
          </h2>
          <dl className="flex flex-col gap-1.5 text-[15px]">
            {[
              [copy.healthData, consents.healthData],
              [copy.researchReuse, consents.researchReuse],
              [copy.publicSharing, consents.sharingEnabled],
            ].map(([label, on]) => (
              <div key={String(label)} className="flex items-start justify-between gap-3">
                <dt className="text-[#3f4850]">{label}</dt>
                <dd>{status(Boolean(on))}</dd>
              </div>
            ))}
          </dl>
          <button
            type="button"
            onClick={() => navigate('data-sovereignty-public-sharing')}
            className="self-start inline-flex items-center gap-1 text-[15px] font-semibold text-[#006194] hover:underline cursor-pointer"
          >
            {copy.manage}
            <ArrowRight className="w-4 h-4" aria-hidden="true" />
          </button>
        </section>

        <section className={card} aria-labelledby="cabinet-journal">
          <h2 id="cabinet-journal" className={`${h2} inline-flex items-center gap-2`}>
            <NotebookPen className="w-5 h-5 text-[#006194]" aria-hidden="true" />
            {copy.journalTitle}
          </h2>
          <p className="text-[15px] text-[#3f4850]">{fill(copy.journalCount, { total: journal.total, open: journal.open })}</p>
          <button
            type="button"
            onClick={() => navigate('protocol-journal')}
            className="self-start inline-flex items-center gap-1 text-[15px] font-semibold text-[#006194] hover:underline cursor-pointer"
          >
            {copy.openJournal}
            <ArrowRight className="w-4 h-4" aria-hidden="true" />
          </button>
        </section>

        <section className={card} aria-labelledby="cabinet-copy">
          <h2 id="cabinet-copy" className={`${h2} inline-flex items-center gap-2`}>
            <Download className="w-5 h-5 text-[#006194]" aria-hidden="true" />
            {copy.actionsTitle}
          </h2>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => download('json')}
              className="rounded-md border border-[#cbd5e1] px-3 py-2 text-[15px] font-semibold text-[#0b1c30] hover:bg-[#eff4ff] cursor-pointer"
            >
              {copy.exportJson}
            </button>
            <button
              type="button"
              onClick={() => download('csv')}
              className="rounded-md border border-[#cbd5e1] px-3 py-2 text-[15px] font-semibold text-[#0b1c30] hover:bg-[#eff4ff] cursor-pointer"
            >
              {copy.exportCsv}
            </button>
          </div>
          {exportError && (
            <p className="text-sm text-[#ba1a1a]" role="alert">
              {copy.exportFailed}
            </p>
          )}
        </section>
      </aside>
    </div>
  );
};
