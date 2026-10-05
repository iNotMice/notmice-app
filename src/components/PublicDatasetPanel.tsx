import React, { useEffect, useState } from 'react';
import { Download, FileCode } from 'lucide-react';
import {
  DatasetRequestError,
  downloadPublicDatasetExport,
  fetchPublicDataset,
  PublicDatasetPage,
  PublicExportKind,
} from '../api/dataset';
import { getActiveI18n } from '../i18n/catalog';
import { fill } from '../i18n/fill';
import { useI18n } from '../i18n/I18nProvider';

/** Public CC0 dataset: honest row count, exports and the first rows. Read-only, no sign-in. */
export const PublicDatasetPanel: React.FC = () => {
  const { m } = useI18n();
  const copy = m.sovereignty;
  const [exportKind, setExportKind] = useState<PublicExportKind | null>(null);
  const [exportSuccess, setExportSuccess] = useState<PublicExportKind | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [page, setPage] = useState<PublicDatasetPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    void fetchPublicDataset({ limit: 20, signal: controller.signal })
      .then((result) => {
        setPage(result);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') {
          return;
        }
        setPage(null);
        const messages = getActiveI18n().messages.sovereignty;
        setError(
          err instanceof DatasetRequestError
            ? fill(messages.datasetFailed, { status: err.status })
            : messages.datasetSilent,
        );
        setLoading(false);
      });
    return () => controller.abort();
  }, [reload]);

  const downloadExport = (kind: PublicExportKind) => {
    setExportError(null);
    setExportKind(kind);
    void downloadPublicDatasetExport(kind)
      .then(() => {
        setExportSuccess(kind);
        setExportKind(null);
        window.setTimeout(() => {
          setExportSuccess((current) => (current === kind ? null : current));
        }, 3000);
      })
      .catch((err: unknown) => {
        setExportKind(null);
        setExportSuccess(null);
        const messages = getActiveI18n().messages.sovereignty;
        setExportError(
          err instanceof DatasetRequestError
            ? fill(messages.exportFailed, { status: err.status })
            : messages.exportSilent,
        );
      });
  };

  const exports: { kind: PublicExportKind; label: string; hint: string; action: string }[] = [
    { kind: 'csv', label: 'CSV', hint: copy.csvHint, action: copy.csvAction },
    { kind: 'parquet', label: 'Parquet', hint: copy.parquetHint, action: copy.parquetAction },
    { kind: 'datasheet', label: copy.datasheet, hint: copy.datasheetHint, action: copy.datasheetAction },
  ];

  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-xl border border-[#cbd5e1] bg-[#ffffff] p-5 flex flex-col gap-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="flex items-center gap-2 text-lg font-bold text-[#0b1c30]">
            <Download className="w-5 h-5 text-[#006194]" aria-hidden="true" />
            {copy.exportTitle}
          </h3>
          <span className="rounded bg-[#eff4ff] px-2 py-0.5 font-['JetBrains_Mono'] text-xs font-semibold text-[#006194]">
            CC0-1.0
          </span>
        </div>
        <p className="text-[15px] leading-relaxed text-[#3f4850]">{copy.exportLead}</p>
        {exportError && (
          <p className="text-sm text-[#ba1a1a]" role="alert">
            {exportError}
          </p>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {exports.map((item) => (
            <button
              key={item.kind}
              type="button"
              onClick={() => downloadExport(item.kind)}
              disabled={exportKind !== null}
              className="group flex flex-col gap-1 rounded-lg border border-[#e2e8f0] p-4 text-left transition-all hover:border-[#006194] hover:bg-[#eff4ff] disabled:opacity-60 cursor-pointer"
            >
              <span className="flex items-center justify-between text-sm font-bold text-[#0b1c30] group-hover:text-[#006194]">
                {item.label}
                {item.kind === 'datasheet' ? (
                  <FileCode className="w-4 h-4 text-[#006194]" aria-hidden="true" />
                ) : (
                  <Download className="w-4 h-4 text-[#006947]" aria-hidden="true" />
                )}
              </span>
              <span className="text-sm text-[#3f4850]">{item.hint}</span>
              <span className="mt-2 text-sm font-semibold text-[#006947]">
                {exportSuccess === item.kind ? copy.downloaded : item.action}
              </span>
            </button>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-[#cbd5e1] bg-[#ffffff] p-5 flex flex-col gap-3" aria-live="polite">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-lg font-bold text-[#0b1c30]">{copy.datasetTitle}</h3>
          <button
            type="button"
            onClick={() => setReload((value) => value + 1)}
            className="text-sm font-semibold text-[#006194] hover:underline cursor-pointer"
          >
            {copy.reload}
          </button>
        </div>
        <p className="text-[15px] leading-relaxed text-[#3f4850]">{copy.datasetLead}</p>
        {loading && <p className="text-sm text-[#3f4850]">{copy.datasetLoading}</p>}
        {error && (
          <p className="text-sm text-[#ba1a1a]" role="alert">
            {error}
          </p>
        )}
        {page && !loading && (
          <p className="text-base font-semibold text-[#0b1c30]">{fill(copy.datasetCount, { total: page.total })}</p>
        )}
        {page && !loading && page.total === 0 && <p className="text-sm text-[#3f4850]">{copy.datasetEmpty}</p>}
        {page && !loading && page.rows.length > 0 && (
          <div className="overflow-x-auto">
            <p className="mb-2 font-['JetBrains_Mono'] text-xs text-[#3f4850]">
              {fill(copy.showing, { shown: page.rows.length, total: page.total })}
            </p>
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[#e2e8f0] text-[#3f4850]">
                  <th className="py-2 pr-3 font-semibold">{copy.colPublicId}</th>
                  <th className="py-2 pr-3 font-semibold">{copy.colCollected}</th>
                  <th className="py-2 pr-3 font-semibold">{copy.colLoinc}</th>
                  <th className="py-2 pr-3 font-semibold">{copy.colMarker}</th>
                  <th className="py-2 pr-3 font-semibold">{copy.colValue}</th>
                </tr>
              </thead>
              <tbody>
                {page.rows.map((row, index) => (
                  <tr
                    key={`${row.publicId}-${row.loincCode ?? row.rawName}-${row.collectedAt ?? 'na'}-${index}`}
                    className="border-b border-[#f1f5f9] font-['JetBrains_Mono'] text-[#0b1c30]"
                  >
                    <td className="py-2 pr-3">{row.publicId}</td>
                    <td className="py-2 pr-3">{row.collectedAt ?? '—'}</td>
                    <td className="py-2 pr-3">{row.loincCode ?? '—'}</td>
                    <td className="py-2 pr-3">{row.canonicalName ?? row.rawName}</td>
                    <td className="py-2 pr-3">
                      {row.value} {row.unit}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};
