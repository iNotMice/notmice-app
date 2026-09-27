import React from 'react';
import { HistoricalTestRecord } from '../types';
import { PHENOAGE_BIOMARKERS } from '../data/phenoAgeData';
import { generateHistoricalReportPDF } from '../utils/pdfReportGenerator';
import {
  FileDown,
  Printer,
  X,
  ShieldCheck,
  Calendar,
  Activity,
  Sparkles,
  TrendingDown,
  CheckCircle,
  FileText,
  Clock,
} from 'lucide-react';
import { isBiomarkerId } from '../i18n/biomarkerIds';
import { fill } from '../i18n/fill';
import { useI18n } from '../i18n/I18nProvider';

interface PrintableReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  history: HistoricalTestRecord[];
}

export const PrintableReportModal: React.FC<PrintableReportModalProps> = ({
  isOpen,
  onClose,
  history,
}) => {
  const { locale, m } = useI18n();
  const copy = m.report;

  if (!isOpen || history.length === 0) return null;

  const sortedHistory = [...history].sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
  );

  const earliest = sortedHistory[0];
  const latest = sortedHistory[sortedHistory.length - 1];
  const netBioChange = Number((latest.phenoAge - earliest.phenoAge).toFixed(1));
  const netChronoChange = Number((latest.chronologicalAge - earliest.chronologicalAge).toFixed(1));
  const agingPace =
    netChronoChange > 0 ? Number((netBioChange / netChronoChange).toFixed(2)) : 0.82;
  const avgDelta = Number(
    (sortedHistory.reduce((acc, h) => acc + h.delta, 0) / sortedHistory.length).toFixed(1)
  );

  const handleDownloadPDF = () => {
    generateHistoricalReportPDF(history);
  };

  const handlePrint = () => {
    window.print();
  };

  const formattedPrintDate = new Date().toLocaleDateString(locale === 'de' ? 'de-DE' : 'en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <div
      id="printable-report-modal-overlay"
      className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 md:p-6 bg-[#0b1c30]/70 backdrop-blur-xs overflow-y-auto"
    >
      <div className="bg-[#ffffff] rounded-2xl border border-[#cbd5e1] shadow-2xl max-w-4xl w-full max-h-[92vh] flex flex-col overflow-hidden my-auto animate-in fade-in zoom-in-95 duration-150">
        {/* Top Control Bar (Hidden on print) */}
        <div className="no-print bg-[#0b1c30] text-white p-4 sm:px-6 flex items-center justify-between border-b border-[#1e293b] shrink-0">
          <div className="flex items-center gap-2.5">
            <FileText className="w-5 h-5 text-[#38bdf8]" />
            <div>
              <h2 className="font-['Inter'] text-sm sm:text-base font-bold">
                {copy.exportTitle}
              </h2>
              <p className="font-['Inter'] text-xs text-[#94a3b8]">
                {copy.exportLead}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleDownloadPDF}
              className="flex items-center gap-1.5 px-3 py-1.5 sm:px-4 sm:py-2 rounded-lg bg-[#006194] hover:bg-[#007bb9] text-white text-xs font-semibold font-['Inter'] transition-colors cursor-pointer shadow-sm"
              title={copy.downloadTitle}
            >
              <FileDown className="w-4 h-4" />
              <span>{copy.downloadPdf}</span>
            </button>

            <button
              onClick={handlePrint}
              className="flex items-center gap-1.5 px-3 py-1.5 sm:px-4 sm:py-2 rounded-lg bg-[#1e293b] hover:bg-[#334155] text-white text-xs font-semibold font-['Inter'] transition-colors cursor-pointer border border-[#475569]"
              title={copy.printTitle}
            >
              <Printer className="w-4 h-4" />
              <span className="hidden sm:inline">{copy.printSave}</span>
              <span className="sm:hidden">{copy.print}</span>
            </button>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-[#94a3b8] hover:text-white hover:bg-[#1e293b] transition-colors cursor-pointer ml-1"
              aria-label={copy.close}
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Printable Report Document Body */}
        <div
          id="printable-report-area"
          className="p-6 sm:p-8 md:p-10 overflow-y-auto font-['Inter'] text-[#0b1c30] space-y-6 bg-white print:p-0 print:m-0 print:overflow-visible"
        >
          {/* Document Header */}
          <div className="border-b-2 border-[#006194] pb-5 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-[#006194] font-['JetBrains_Mono'] text-xs font-bold uppercase tracking-wider mb-1">
                <Activity className="w-4 h-4" />
                {copy.reportKicker}
              </div>
              <h1 className="text-xl sm:text-2xl font-black text-[#0b1c30] tracking-tight">
                {copy.reportTitle}
              </h1>
              <p className="text-xs text-[#565e74] mt-1 max-w-xl">
                {copy.reportLead}
              </p>
            </div>

            <div className="sm:text-right font-['JetBrains_Mono'] text-xs text-[#565e74] space-y-1 bg-[#f8f9ff] p-3 rounded-lg border border-[#e2e8f0] shrink-0">
              <div>
                <span className="font-semibold text-[#0b1c30]">{copy.generated}</span>{' '}
                {formattedPrintDate}
              </div>
              <div>
                <span className="font-semibold text-[#0b1c30]">{copy.panels}</span>{' '}
                {fill(copy.testDates, { count: sortedHistory.length })}
              </div>
              <div className="flex items-center sm:justify-end gap-1 text-[#006947] font-semibold text-[11px]">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>{copy.status}</span>
              </div>
            </div>
          </div>

          {/* Executive Longevity KPI Grid */}
          <div>
            <h3 className="font-['JetBrains_Mono'] text-xs font-bold uppercase tracking-wider text-[#565e74] mb-3">
              {copy.summary}
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3.5 bg-[#f8f9ff] rounded-lg border border-[#e2e8f0]">
                <span className="font-['JetBrains_Mono'] text-[10px] text-[#565e74] uppercase block">
                  {copy.latestPheno}
                </span>
                <div className="flex items-baseline gap-1.5 mt-1">
                  <span className="text-2xl font-bold text-[#006947]">
                    {latest.phenoAge.toFixed(1)}
                  </span>
                  <span className="text-xs text-[#565e74]">{m.shell.yrs}</span>
                </div>
                <span className="text-[10px] font-['JetBrains_Mono'] text-[#565e74]">
                  {fill(copy.chronoAge, { value: latest.chronologicalAge.toFixed(1) })}
                </span>
              </div>

              <div className="p-3.5 bg-[#f8f9ff] rounded-lg border border-[#e2e8f0]">
                <span className="font-['JetBrains_Mono'] text-[10px] text-[#565e74] uppercase block">
                  {copy.variance}
                </span>
                <div className="flex items-baseline gap-1.5 mt-1">
                  <span
                    className={`text-2xl font-bold ${
                      latest.delta <= 0 ? 'text-[#006947]' : 'text-[#ba1a1a]'
                    }`}
                  >
                    {latest.delta > 0 ? `+${latest.delta.toFixed(1)}` : latest.delta.toFixed(1)}
                  </span>
                  <span className="text-xs text-[#565e74]">{m.shell.yrs}</span>
                </div>
                <span className="text-[10px] font-['JetBrains_Mono'] text-[#006947] font-semibold">
                  {latest.delta <= 0 ? copy.decelerated : copy.accelerated}
                </span>
              </div>

              <div className="p-3.5 bg-[#f8f9ff] rounded-lg border border-[#e2e8f0]">
                <span className="font-['JetBrains_Mono'] text-[10px] text-[#565e74] uppercase block">
                  {copy.pace}
                </span>
                <div className="flex items-baseline gap-1.5 mt-1">
                  <span className="text-2xl font-bold text-[#006194]">{agingPace}</span>
                  <span className="text-xs text-[#565e74]">{copy.paceUnit}</span>
                </div>
                <span className="text-[10px] font-['JetBrains_Mono'] text-[#006947] font-semibold">
                  {agingPace < 1.0 ? copy.slowed : copy.standardRate}
                </span>
              </div>

              <div className="p-3.5 bg-[#f8f9ff] rounded-lg border border-[#e2e8f0]">
                <span className="font-['JetBrains_Mono'] text-[10px] text-[#565e74] uppercase block">
                  {copy.avgAdvantage}
                </span>
                <div className="flex items-baseline gap-1.5 mt-1">
                  <span className="text-2xl font-bold text-[#006947]">
                    {Math.abs(avgDelta).toFixed(1)}
                  </span>
                  <span className="text-xs text-[#565e74]">{copy.yrsYounger}</span>
                </div>
                <span className="text-[10px] font-['JetBrains_Mono'] text-[#565e74]">
                  {copy.across}
                </span>
              </div>
            </div>
          </div>

          {/* Historical Test Panels Table */}
          <div>
            <h3 className="font-['JetBrains_Mono'] text-xs font-bold uppercase tracking-wider text-[#565e74] mb-3">
              {copy.panelsTitle}
            </h3>
            <div className="border border-[#cbd5e1] rounded-lg overflow-hidden">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-[#006194] text-white font-['JetBrains_Mono'] text-[11px]">
                    <th className="py-2.5 px-3 font-semibold">{copy.colDate}</th>
                    <th className="py-2.5 px-3 font-semibold">{copy.colFacility}</th>
                    <th className="py-2.5 px-3 font-semibold">{copy.colCalendar}</th>
                    <th className="py-2.5 px-3 font-semibold">{copy.colPheno}</th>
                    <th className="py-2.5 px-3 font-semibold">{copy.colVariance}</th>
                    <th className="py-2.5 px-3 font-semibold">{copy.colStatus}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#e2e8f0]">
                  {sortedHistory.map((item, idx) => {
                    const isDecel = item.delta <= 0;
                    return (
                      <tr
                        key={item.id || idx}
                        className={idx % 2 === 0 ? 'bg-[#ffffff]' : 'bg-[#f8fafc]'}
                      >
                        <td className="py-2.5 px-3 font-['JetBrains_Mono'] font-bold text-[#0b1c30]">
                          {item.date}
                        </td>
                        <td className="py-2.5 px-3 text-[#3f4850]">{item.labSource}</td>
                        <td className="py-2.5 px-3 font-['JetBrains_Mono'] text-[#565e74]">
                          {item.chronologicalAge.toFixed(1)} {m.shell.yrs}
                        </td>
                        <td className="py-2.5 px-3 font-['JetBrains_Mono'] font-bold text-[#006947]">
                          {item.phenoAge.toFixed(1)} {m.shell.yrs}
                        </td>
                        <td className="py-2.5 px-3 font-['JetBrains_Mono'] font-bold">
                          <span
                            className={`px-2 py-0.5 rounded text-[11px] ${
                              isDecel
                                ? 'bg-[#e6f4ea] text-[#006947]'
                                : 'bg-[#ffdad6] text-[#ba1a1a]'
                            }`}
                          >
                            {item.delta > 0
                              ? `+${item.delta.toFixed(1)}`
                              : `${item.delta.toFixed(1)}`}{' '}
                            {m.shell.yrs}
                          </span>
                        </td>
                        <td className="py-2.5 px-3">
                          <span className="inline-flex items-center gap-1 font-medium text-[#006947]">
                            <CheckCircle className="w-3.5 h-3.5" />
                            {isDecel ? copy.deceleratedAging : copy.standardBaseline}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Longitudinal Biomarker Measurements Matrix Table */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-['JetBrains_Mono'] text-xs font-bold uppercase tracking-wider text-[#565e74]">
                {copy.matrixTitle}
              </h3>
              <span className="font-['JetBrains_Mono'] text-[10px] text-[#006194]">
                {copy.matrixMeta}
              </span>
            </div>

            <div className="border border-[#cbd5e1] rounded-lg overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse min-w-[640px]">
                <thead>
                  <tr className="bg-[#0b1c30] text-white font-['JetBrains_Mono'] text-[11px]">
                    <th className="py-2.5 px-3 font-semibold">{copy.colBiomarker}</th>
                    <th className="py-2.5 px-3 font-semibold">{copy.colUnit}</th>
                    <th className="py-2.5 px-3 font-semibold">{copy.colOptimal}</th>
                    {sortedHistory.map((h) => (
                      <th key={h.id} className="py-2.5 px-3 font-semibold text-center">
                        {h.date}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#e2e8f0]">
                  {PHENOAGE_BIOMARKERS.map((bio, bIdx) => (
                    <tr
                      key={bio.id}
                      className={bIdx % 2 === 0 ? 'bg-[#ffffff]' : 'bg-[#f8fafc]'}
                    >
                      <td className="py-2.5 px-3 font-semibold text-[#0b1c30]">
                        {isBiomarkerId(bio.id) ? m.biomarkers[bio.id].name : bio.name}
                      </td>
                      <td className="py-2.5 px-3 font-['JetBrains_Mono'] text-[11px] text-[#565e74]">
                        {bio.unit}
                      </td>
                      <td className="py-2.5 px-3 font-['JetBrains_Mono'] text-[11px] text-[#006947] font-semibold">
                        {bio.optimalRange[0]} – {bio.optimalRange[1]}
                      </td>
                      {sortedHistory.map((h) => {
                        const val = h.biomarkers ? h.biomarkers[bio.id] : undefined;
                        const isOptimal =
                          val !== undefined &&
                          val >= bio.optimalRange[0] &&
                          val <= bio.optimalRange[1];

                        return (
                          <td
                            key={h.id}
                            className="py-2.5 px-3 font-['JetBrains_Mono'] text-center"
                          >
                            {val !== undefined ? (
                              <span
                                className={`font-bold px-1.5 py-0.5 rounded text-[11px] ${
                                  isOptimal
                                    ? 'text-[#006947] bg-[#e6f4ea]'
                                    : 'text-[#0b1c30] bg-[#f1f5f9]'
                                }`}
                              >
                                {val}
                              </span>
                            ) : (
                              <span className="text-[#94a3b8]">—</span>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Clinical Interpretation & Scientific Methodology */}
          <div className="p-4 bg-[#eff4ff] rounded-xl border border-[#dce9ff] text-xs space-y-2">
            <div className="flex items-center gap-2 font-bold text-[#006194] font-['JetBrains_Mono'] text-[11px]">
              <Sparkles className="w-4 h-4" />
              <span>{copy.interpretation}</span>
            </div>
            <p className="text-[#3f4850] leading-relaxed">
              {fill(copy.paceAnalysis, { pace: agingPace })}
            </p>
            <p className="text-[#3f4850] leading-relaxed">
              {copy.hazardRef}
            </p>
            <div className="pt-2 text-[10px] text-[#64748b] border-t border-[#dce9ff] flex flex-col sm:flex-row sm:items-center justify-between gap-1">
              <span>{copy.citation}</span>
              {latest.hash.length === 64 && (
                <span className="font-['JetBrains_Mono'] font-bold text-[#006194]">
                  {fill(copy.documentId, { id: latest.hash.slice(0, 12) })}
                </span>
              )}
            </div>
          </div>

          {/* Physician / Clinical Sign-off Section for Physical Prints */}
          <div className="pt-4 border-t border-[#cbd5e1] grid grid-cols-1 sm:grid-cols-2 gap-8 text-xs text-[#565e74]">
            <div>
              <div className="border-b border-[#94a3b8] pb-8 mb-2"></div>
              <span className="font-semibold block text-[#0b1c30]">{copy.clinician}</span>
              <span className="text-[10px]">{copy.license}</span>
            </div>
            <div>
              <div className="border-b border-[#94a3b8] pb-8 mb-2"></div>
              <span className="font-semibold block text-[#0b1c30]">{copy.participant}</span>
              <span className="text-[10px]">{copy.signature}</span>
            </div>
          </div>
        </div>

        {/* Footer actions bar (Hidden on print) */}
        <div className="no-print bg-[#f8f9ff] px-6 py-3 border-t border-[#e2e8f0] flex items-center justify-between text-xs text-[#565e74] shrink-0">
          <span>{copy.layout}</span>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-[#cbd5e1] text-[#565e74] hover:bg-[#ffffff] font-medium transition-colors cursor-pointer"
            >
              {copy.closeAction}
            </button>
            <button
              onClick={handleDownloadPDF}
              className="px-4 py-2 rounded-lg bg-[#006194] hover:bg-[#007bb9] text-white font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <FileDown className="w-4 h-4" />
              <span>{copy.exportPdf}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
