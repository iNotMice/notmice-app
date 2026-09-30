import React, { useState } from 'react';
import { TabType, PhenoAgeCalculation } from '../../types';
import { PHENOAGE_BIOMARKERS } from '../../data/phenoAgeData';
import { isBiomarkerId } from '../../i18n/biomarkerIds';
import { fill } from '../../i18n/fill';
import { useI18n } from '../../i18n/I18nProvider';
import { LifestyleLongevityAdvisor } from '../LifestyleLongevityAdvisor';
import { ShieldCheck, Save, RotateCcw } from 'lucide-react';

interface PhenoAgeEngineTabProps {
  calculation: PhenoAgeCalculation;
  scoreError: string | null;
  biomarkers: Record<string, number>;
  onUpdateBiomarkers: (biomarkers: Record<string, number>) => void;
  chronologicalAge: number;
  onUpdateChronologicalAge: (age: number) => void;
  onSaveToHistory: () => void;
  setActiveTab: (tab: TabType) => void;
  onOpenProofModal: () => void;
}

export const PhenoAgeEngineTab: React.FC<PhenoAgeEngineTabProps> = ({
  calculation,
  scoreError,
  biomarkers,
  onUpdateBiomarkers,
  chronologicalAge,
  onUpdateChronologicalAge,
  onSaveToHistory,
  setActiveTab,
  onOpenProofModal,
}) => {
  const { m } = useI18n();
  const copy = m.phenoage;
  const [savedNotification, setSavedNotification] = useState(false);

  const handleSliderChange = (id: string, val: number) => {
    onUpdateBiomarkers({
      ...biomarkers,
      [id]: val,
    });
  };

  const handleSave = () => {
    if (!calculation.isValid) {
      return;
    }
    onSaveToHistory();
    setSavedNotification(true);
    setTimeout(() => setSavedNotification(false), 3000);
  };

  const handleResetToBaseline = () => {
    onUpdateBiomarkers({
      albumin: 46.2,
      creatinine: 0.85,
      glucose: 84.0,
      crp: 0.80,
      lymphocyte: 33.2,
      mcv: 88.0,
      rdw: 12.0,
      alp: 58.0,
      wbc: 5.2,
    });
  };

  return (
    <div className="w-full max-w-[1440px] mx-auto px-4 lg:px-8 py-8 flex flex-col gap-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#e2e8f0] pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="bg-[#cce5ff] text-[#004b73] font-['JetBrains_Mono'] text-xs font-semibold px-2 py-0.5 rounded">
              {copy.stage}
            </span>
            <span className="font-['JetBrains_Mono'] text-xs text-[#565e74]">
              {copy.stageMeta}
            </span>
          </div>
          <h1 className="font-['Inter'] text-2xl lg:text-3xl font-bold text-[#0b1c30]">
            {copy.title}
          </h1>
          <p className="font-['Inter'] text-sm text-[#3f4850] mt-1 max-w-2xl">
            {copy.lead}
          </p>
          <p className="font-['Inter'] text-xs text-[#3f4850] mt-3 max-w-2xl border-l-2 border-[#006194] pl-3">
            {calculation.disclaimer}
          </p>
          {scoreError && (
            <p className="font-['Inter'] text-xs text-[#ba1a1a] mt-2">{scoreError}</p>
          )}
        </div>

        {/* Global actions */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={handleResetToBaseline}
            className="flex items-center gap-1.5 px-3 py-2 rounded text-xs font-semibold text-[#3f4850] hover:bg-[#eff4ff] border border-[#cbd5e1] transition-colors cursor-pointer"
          >
            <RotateCcw className="w-4 h-4" />
            <span>{copy.reset}</span>
          </button>

          <button
            onClick={handleSave}
            disabled={!calculation.isValid}
            className="flex items-center gap-2 px-4 py-2 rounded font-['Inter'] text-xs font-bold bg-[#006947] hover:bg-[#00855b] text-[#ffffff] shadow-sm transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save className="w-4 h-4" />
            <span>{savedNotification ? copy.saved : copy.save}</span>
          </button>

          <button
            onClick={onOpenProofModal}
            className="flex items-center gap-2 px-4 py-2 rounded font-['Inter'] text-xs font-bold bg-[#006194] hover:bg-[#007bb9] text-[#ffffff] shadow-sm transition-all cursor-pointer"
          >
            <ShieldCheck className="w-4 h-4" />
            <span>{copy.indexDetails}</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Chronological Age Card */}
        <div className="bg-[#ffffff] p-5 rounded-xl border border-[#cbd5e1] shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-center text-[#565e74] text-xs mb-1 font-['JetBrains_Mono']">
              <span>{copy.chronoLabel}</span>
              <span>{copy.calendarYrs}</span>
            </div>
            <div className="flex items-baseline gap-2 mt-2">
              <span className="font-['Inter'] text-3xl font-bold text-[#0b1c30]">
                {chronologicalAge.toFixed(1)}
              </span>
              <span className="text-xs text-[#565e74]">{m.shell.years}</span>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-[#f1f5f9] flex items-center justify-between">
            <span className="text-xs text-[#565e74]">{copy.adjustAge}</span>
            <input
              type="number"
              min="18"
              max="95"
              step="0.5"
              value={chronologicalAge}
              onChange={(e) => onUpdateChronologicalAge(parseFloat(e.target.value) || 40)}
              className="w-16 px-2 py-1 bg-[#eff4ff] border border-[#cbd5e1] rounded font-['JetBrains_Mono'] text-xs font-bold text-[#0b1c30] text-right"
            />
          </div>
        </div>

        {/* Biological PhenoAge Card */}
        <div className="bg-[#ffffff] p-5 rounded-xl border border-[#cbd5e1] shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-center text-[#006194] text-xs mb-1 font-['JetBrains_Mono'] font-bold">
              <span>{copy.bioLabel}</span>
              <span>{copy.levine}</span>
            </div>
            <div className="flex items-baseline gap-2 mt-2">
              <span className="font-['Inter'] text-4xl font-bold text-[#006194]">
                {calculation.isValid ? calculation.phenoAge.toFixed(1) : '…'}
              </span>
              <span className="text-xs text-[#565e74]">{m.shell.years}</span>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-[#f1f5f9]">
            <span className="text-xs text-[#565e74]">{copy.researchIndex}</span>
          </div>
        </div>
      </div>

      {/* Main Section: Interactive 9-Biomarker Sliders & Contribution Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: All 9 Interactive Sliders */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          <div className="bg-[#ffffff] p-6 rounded-xl border border-[#cbd5e1] shadow-xs flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div>
                <span className="font-['Inter'] text-base font-bold text-[#0b1c30] block">
                  {copy.slidersTitle}
                </span>
                <span className="font-['Inter'] text-xs text-[#565e74]">
                  {copy.slidersLead}
                </span>
              </div>
              <span className="font-['JetBrains_Mono'] text-xs bg-[#eff4ff] text-[#006194] px-2.5 py-1 rounded font-bold">
                {copy.active}
              </span>
            </div>

            {/* Biomarker Sliders List */}
            <div className="flex flex-col gap-4">
              {PHENOAGE_BIOMARKERS.map((bio) => {
                const val = biomarkers[bio.id] ?? bio.optimalRange[0];

                return (
                  <div
                    key={bio.id}
                    className="p-3.5 bg-[#eff4ff]/60 rounded-lg border border-[#dce9ff] flex flex-col gap-2"
                  >
                    <div className="flex justify-between items-center text-xs">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-[#0b1c30]">
                          {isBiomarkerId(bio.id) ? m.biomarkers[bio.id].name : bio.name}
                        </span>
                        <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74]">
                          ({bio.loinc})
                        </span>
                      </div>
                      <span className="font-['JetBrains_Mono'] text-xs font-bold text-[#0b1c30]">
                        {val.toFixed(bio.step < 0.1 ? 2 : 1)} {bio.unit}
                      </span>
                    </div>

                    {/* Range Slider */}
                    <input
                      type="range"
                      min={bio.clinicalRange[0]}
                      max={bio.clinicalRange[1]}
                      step={bio.step}
                      value={val}
                      onChange={(e) => handleSliderChange(bio.id, parseFloat(e.target.value))}
                      className="w-full accent-[#006194] h-1.5 bg-[#dce9ff] rounded cursor-pointer"
                    />

                    <div className="flex justify-between text-[#565e74] font-['JetBrains_Mono'] text-[10px]">
                      <span>{fill(copy.min, { value: bio.clinicalRange[0] })}</span>
                      <span>{fill(copy.max, { value: bio.clinicalRange[1] })}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Biomarker Impact Waterfall & Longevity Directives */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          {/* Biomarker Risk/Protection Breakdown */}
          <div className="bg-[#ffffff] p-6 rounded-xl border border-[#cbd5e1] shadow-xs flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <span className="font-['Inter'] text-sm font-bold text-[#0b1c30]">
                {copy.contributions}
              </span>
              <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74]">
                {copy.weightImpact}
              </span>
            </div>

            <p className="font-['Inter'] text-xs text-[#565e74]">
              {copy.contributionLead}
            </p>

            <div className="space-y-3 pt-2">
              {calculation.biomarkerScores.map((score) => {
                return (
                  <div key={score.id} className="flex flex-col gap-1 text-xs">
                    <div className="flex justify-between items-center">
                      <span className="font-semibold text-[#0b1c30]">
                        {isBiomarkerId(score.id) ? m.biomarkers[score.id].name : score.name}
                      </span>
                      <span className="font-['JetBrains_Mono'] font-bold text-[#0b1c30]">
                        {fill(copy.yearsSigned, {
                          sign: score.contribution > 0 ? '+' : '',
                          value: score.contribution.toFixed(1),
                        })}
                      </span>
                    </div>
                    <div className="w-full bg-[#f1f5f9] h-1.5 rounded-full overflow-hidden">
                      <div
                        className="bg-[#006194] h-full rounded-full"
                        style={{
                          width: `${Math.min(100, Math.abs(score.contribution) * 25)}%`,
                        }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      <LifestyleLongevityAdvisor />
    </div>
  );
};
