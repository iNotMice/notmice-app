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

  const chips: { label: string; value: string; hiddenBelow?: 'lg' | 'xl' }[] = [
    { label: m.biomarkers.crp.shortName, value: `${crp.toFixed(1)} mg/L` },
    { label: m.biomarkers.albumin.shortName, value: `${alb.toFixed(1)} g/L` },
    { label: m.biomarkers.glucose.shortName, value: `${Math.round(glu)} mg/dL` },
    { label: m.biomarkers.alp.shortName, value: `${Math.round(alp)} U/L`, hiddenBelow: 'lg' },
    { label: m.biomarkers.rdw.shortName, value: `${rdw.toFixed(1)}%`, hiddenBelow: 'xl' },
  ];

  return (
    <section className="w-full bg-[#eff4ff] border-b border-[#dce9ff] px-4 lg:px-6 py-2 shadow-xs">
      <div className="max-w-[1440px] mx-auto flex flex-wrap items-center justify-between gap-y-2 gap-x-4">
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

        <div className="flex items-center gap-3 overflow-x-auto py-0.5">
          {chips.map((chip) => (
            <div
              key={chip.label}
              className={`items-center gap-1.5 bg-[#ffffff] px-2.5 py-1 rounded shadow-xs border border-[#e2e8f0] shrink-0 ${
                chip.hiddenBelow === 'xl'
                  ? 'hidden xl:flex'
                  : chip.hiddenBelow === 'lg'
                    ? 'hidden lg:flex'
                    : 'flex'
              }`}
            >
              <span className="font-['JetBrains_Mono'] text-[11px] text-[#3f4850]">{chip.label}</span>
              <span className="font-['JetBrains_Mono'] text-[11px] text-[#0b1c30] font-semibold">
                {chip.value}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
