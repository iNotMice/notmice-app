import React from 'react';
import { useI18n } from '../i18n/I18nProvider';

interface StatusRibbonProps {
  biomarkers: Record<string, number>;
  tutorial: boolean;
  labName: string;
}

export const StatusRibbon: React.FC<StatusRibbonProps> = ({ biomarkers, tutorial, labName }) => {
  const { m } = useI18n();
  const crp = biomarkers['crp'] ?? 0.8;
  const alb = biomarkers['albumin'] ?? 46.2;
  const glu = biomarkers['glucose'] ?? 84;
  const alp = biomarkers['alp'] ?? 58;
  const rdw = biomarkers['rdw'] ?? 12.0;

  return (
    <section className="w-full bg-[#eff4ff] border-b border-[#dce9ff] px-4 lg:px-6 py-2 shadow-xs">
      <div className="max-w-[1440px] mx-auto flex flex-wrap items-center justify-between gap-y-2 gap-x-4">
        {/* Stream label */}
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#006194]"></span>
          <span className="font-['JetBrains_Mono'] text-[11px] text-[#3f4850] font-semibold uppercase tracking-wider">
            {tutorial ? m.shell.tutorialExample : labName}
          </span>
          <span className="text-[#3f4850] font-mono text-[11px]">•</span>
          <span className="font-['Inter'] text-[12px] text-[#0b1c30] font-semibold">
            {tutorial ? m.shell.notPatientPanel : m.shell.levineWeights}
          </span>
        </div>

        {/* Live Biomarkers Chips */}
        <div className="flex items-center gap-3 overflow-x-auto py-0.5">
          {/* hs-CRP */}
          <div className="flex items-center gap-1.5 bg-[#ffffff] px-2.5 py-1 rounded shadow-xs border border-[#e2e8f0] shrink-0">
            <span className="font-['JetBrains_Mono'] text-[11px] text-[#3f4850]">{m.biomarkers.crp.shortName}</span>
            <span className="font-['JetBrains_Mono'] text-[11px] text-[#006947] font-bold">
              {crp.toFixed(1)} mg/L
            </span>
            <span className="bg-[#4edea3]/20 text-[#006947] text-[10px] px-1 py-0.2 rounded font-semibold">
              {crp < 1.0 ? m.shell.optimal : crp < 3.0 ? m.shell.normal : m.shell.elevated}
            </span>
          </div>

          {/* Albumin */}
          <div className="flex items-center gap-1.5 bg-[#ffffff] px-2.5 py-1 rounded shadow-xs border border-[#e2e8f0] shrink-0">
            <span className="font-['JetBrains_Mono'] text-[11px] text-[#3f4850]">{m.biomarkers.albumin.shortName}</span>
            <span className="font-['JetBrains_Mono'] text-[11px] text-[#0b1c30] font-semibold">
              {alb.toFixed(1)} g/L
            </span>
            <span className="bg-[#e5eeff] text-[#3f4850] text-[10px] px-1 py-0.2 rounded font-medium">
              {m.shell.refPrefix} 35-50
            </span>
          </div>

          {/* Fasting Glucose */}
          <div className="flex items-center gap-1.5 bg-[#ffffff] px-2.5 py-1 rounded shadow-xs border border-[#e2e8f0] shrink-0">
            <span className="font-['JetBrains_Mono'] text-[11px] text-[#3f4850]">{m.biomarkers.glucose.shortName}</span>
            <span className="font-['JetBrains_Mono'] text-[11px] text-[#006947] font-bold">
              {Math.round(glu)} mg/dL
            </span>
            <span className="bg-[#4edea3]/20 text-[#006947] text-[10px] px-1 py-0.2 rounded font-semibold">
              {glu < 90 ? m.shell.euglycemic : glu < 100 ? m.shell.normal : m.shell.impaired}
            </span>
          </div>

          {/* Alk Phos */}
          <div className="hidden lg:flex items-center gap-1.5 bg-[#ffffff] px-2.5 py-1 rounded shadow-xs border border-[#e2e8f0] shrink-0">
            <span className="font-['JetBrains_Mono'] text-[11px] text-[#3f4850]">{m.biomarkers.alp.shortName}</span>
            <span className="font-['JetBrains_Mono'] text-[11px] text-[#0b1c30] font-semibold">
              {Math.round(alp)} U/L
            </span>
            <span className="bg-[#e5eeff] text-[#3f4850] text-[10px] px-1 py-0.2 rounded font-medium">
              {m.shell.normal}
            </span>
          </div>

          {/* RDW */}
          <div className="hidden xl:flex items-center gap-1.5 bg-[#ffffff] px-2.5 py-1 rounded shadow-xs border border-[#e2e8f0] shrink-0">
            <span className="font-['JetBrains_Mono'] text-[11px] text-[#3f4850]">{m.biomarkers.rdw.shortName}</span>
            <span className="font-['JetBrains_Mono'] text-[11px] text-[#006947] font-bold">
              {rdw.toFixed(1)}%
            </span>
            <span className="bg-[#4edea3]/20 text-[#006947] text-[10px] px-1 py-0.2 rounded font-semibold">
              {m.shell.optimal}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
};
