import React, { useEffect, useState } from 'react';
import { TabType, LabPanelData } from '../../types';
import { PHENOAGE_BIOMARKERS } from '../../data/phenoAgeData';
import { confirmLabExtraction } from '../../api/uploads';
import { TokenUsageBanner } from '../TokenUsageBanner';
import { isBiomarkerId } from '../../i18n/biomarkerIds';
import { fill } from '../../i18n/fill';
import { getActiveI18n } from '../../i18n/catalog';
import { useI18n } from '../../i18n/I18nProvider';
import {
  CheckSquare,
  CheckCircle2,
  AlertTriangle,
  FileSearch,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  RotateCcw,
  Eye,
  Sliders,
} from 'lucide-react';

interface ReviewExtractionTabProps {
  currentPanel: LabPanelData;
  onUpdateBiomarkers: (biomarkers: Record<string, number>) => void;
  setActiveTab: (tab: TabType) => void;
  accessToken: string | null;
  onSaved?: () => Promise<void>;
}

export const ReviewExtractionTab: React.FC<ReviewExtractionTabProps> = ({
  currentPanel,
  onUpdateBiomarkers,
  setActiveTab,
  accessToken,
  onSaved,
}) => {
  const { m } = useI18n();
  const copy = m.review;
  const [localValues, setLocalValues] = useState<Record<string, number>>({
    ...currentPanel.biomarkers,
  });
  const [activeSnippetKey, setActiveSnippetKey] = useState<string>('albumin');
  const [verifiedMap, setVerifiedMap] = useState<Record<string, boolean>>({
    albumin: true,
    creatinine: true,
    glucose: true,
    crp: true,
    lymphocyte: true,
    mcv: true,
    rdw: true,
    alp: true,
    wbc: true,
  });

  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [confirmBusy, setConfirmBusy] = useState(false);

  useEffect(() => {
    setLocalValues({ ...currentPanel.biomarkers });
    setVerifiedMap({
      albumin: true,
      creatinine: true,
      glucose: true,
      crp: true,
      lymphocyte: true,
      mcv: true,
      rdw: true,
      alp: true,
      wbc: true,
    });
    setConfirmError(null);
  }, [currentPanel]);

  const confirmedMarkers = PHENOAGE_BIOMARKERS.map((bio) => ({
    rawName: bio.name,
    value: localValues[bio.id] ?? bio.optimalRange[0],
    unit: bio.unit,
  }));

  const handleValueChange = (id: string, val: number) => {
    const next = { ...localValues, [id]: val };
    setLocalValues(next);
    onUpdateBiomarkers(next);
  };

  const toggleVerify = (id: string) => {
    setVerifiedMap((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleVerifyAll = () => {
    void (async () => {
      const allTrue: Record<string, boolean> = {};
      PHENOAGE_BIOMARKERS.forEach((b) => (allTrue[b.id] = true));
      setVerifiedMap(allTrue);
      onUpdateBiomarkers(localValues);
      if (currentPanel.extractToken && accessToken) {
        setConfirmBusy(true);
        setConfirmError(null);
        try {
          const age = currentPanel.chronologicalAge;
          await confirmLabExtraction(accessToken, {
            extractToken: currentPanel.extractToken,
            labName: currentPanel.labName,
            collectedAt: currentPanel.testDate,
            chronologicalAge: age >= 1 && age <= 120 ? age : null,
            markers: confirmedMarkers,
          });
          if (onSaved) {
            await onSaved();
          }
        } catch (err) {
          const shell = getActiveI18n().messages.shell;
          const rejected = err instanceof Error && err.message === 'Forbidden field';
          setConfirmError(
            rejected ? shell.confirmRejected : err instanceof Error ? err.message : shell.confirmFailed,
          );
          setConfirmBusy(false);
          return;
        }
        setConfirmBusy(false);
      }
      setActiveTab('phenoage-engine');
    })();
  };

  const activeBio = PHENOAGE_BIOMARKERS.find((b) => b.id === activeSnippetKey);

  return (
    <div className="w-full max-w-[1440px] mx-auto px-4 lg:px-8 py-8 flex flex-col gap-6">
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
          <p className="font-['Inter'] text-sm text-[#3f4850] mt-1">
            {currentPanel.sourceType === 'demo' ? copy.tutorialPrefix : copy.sourcePrefix}
            <strong className="text-[#0b1c30]">
              {currentPanel.fileName ?? copy.untitled}
            </strong>{' '}
            • {fill(copy.labDate, { lab: currentPanel.labName, date: currentPanel.testDate })}
            {currentPanel.hash.length === 64 ? ` • ${fill(copy.sha, { prefix: currentPanel.hash.slice(0, 12) })}` : ''}
          </p>
          {currentPanel.sourceType === 'demo' && (
            <p className="font-['Inter'] text-xs text-[#565e74] mt-2">
              {copy.demoNote}
            </p>
          )}
          {currentPanel.tokenUsage && (
            <div className="mt-3">
              <TokenUsageBanner usage={currentPanel.tokenUsage} />
            </div>
          )}
          {confirmError && (
            <p className="font-['Inter'] text-xs text-[#9f1239] mt-2">{confirmError}</p>
          )}
        </div>

        {/* Global Action */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setActiveTab('upload-lab')}
            className="flex items-center gap-1.5 px-3 py-2 rounded text-xs font-semibold text-[#3f4850] hover:bg-[#eff4ff] border border-[#cbd5e1] transition-colors cursor-pointer"
          >
            <RotateCcw className="w-4 h-4" />
            <span>{copy.reupload}</span>
          </button>
          <button
            onClick={handleVerifyAll}
            disabled={confirmBusy}
            className="flex items-center gap-2 px-5 py-2.5 rounded font-['Inter'] text-xs font-bold bg-[#006194] hover:bg-[#007bb9] text-[#ffffff] shadow-sm transition-all cursor-pointer disabled:opacity-60"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>{copy.verifyAll}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Dual-Pane: preview follows the edited values; table comes first on a phone */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        <div className="order-2 lg:order-1 lg:col-span-4 flex flex-col gap-4 lg:sticky lg:top-24">
          <div className="bg-[#ffffff] p-5 rounded-xl border border-[#cbd5e1] shadow-xs flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="font-['Inter'] text-xs font-bold text-[#0b1c30] flex items-center gap-1.5">
                <FileSearch className="w-4 h-4 text-[#006194]" />
                {copy.cropTitle}
              </span>
              <span className="font-['JetBrains_Mono'] text-[10px] bg-[#eff4ff] text-[#006194] px-1.5 py-0.5 rounded font-semibold">
                {copy.canvas}
              </span>
            </div>

            <div className="bg-[#f8f9ff] border border-[#dce9ff] rounded-lg p-4 font-['JetBrains_Mono'] text-xs space-y-3 relative shadow-inner">
              <div className="text-[10px] text-[#565e74] border-b border-[#e2e8f0] pb-2 flex justify-between gap-3">
                <span className="truncate">{currentPanel.labName}</span>
                <span className="shrink-0">{fill(copy.collected, { date: currentPanel.testDate })}</span>
              </div>

              <div className="space-y-1 text-[11px]">
                {PHENOAGE_BIOMARKERS.map((bio) => {
                  const currentVal = localValues[bio.id] ?? bio.optimalRange[0];
                  const isActive = activeSnippetKey === bio.id;
                  const label = isBiomarkerId(bio.id) ? m.biomarkers[bio.id].name : bio.name;
                  return (
                    <div
                      key={bio.id}
                      onClick={() => setActiveSnippetKey(bio.id)}
                      className={`p-1.5 rounded cursor-pointer transition-colors flex justify-between items-center gap-2 ${
                        isActive
                          ? 'bg-[#cce5ff] border border-[#006194] text-[#001d31] font-bold'
                          : 'hover:bg-[#e2e8f0]/60 text-[#3f4850]'
                      }`}
                    >
                      <span className="min-w-0">{label}</span>
                      <span className="shrink-0">
                        {currentVal} {bio.unit}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Focused Marker Detail Note */}
            {activeBio && isBiomarkerId(activeBio.id) && (
              <div className="p-3 bg-[#eff4ff] rounded border border-[#dce9ff] text-xs space-y-1">
                <div className="flex justify-between font-bold text-[#0b1c30]">
                  <span>{fill(copy.focused, { name: m.biomarkers[activeBio.id].name })}</span>
                  <span className="font-mono text-[#006194]">{fill(copy.loinc, { code: activeBio.loinc })}</span>
                </div>
                <p className="text-[#3f4850] text-[11px] leading-relaxed">
                  {m.biomarkers[activeBio.id].weight}
                </p>
                <div className="text-[10px] text-[#006947] font-semibold pt-1">
                  {fill(copy.optimalInterval, {
                    min: activeBio.optimalRange[0],
                    max: activeBio.optimalRange[1],
                    unit: activeBio.unit,
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="order-1 lg:order-2 lg:col-span-8 flex flex-col gap-4">
          <div className="bg-[#ffffff] rounded-xl border border-[#cbd5e1] shadow-xs overflow-hidden">
            <div className="px-5 py-4 bg-[#eff4ff] border-b border-[#dce9ff] flex items-center justify-between">
              <div>
                <span className="font-['Inter'] text-sm font-bold text-[#0b1c30] block">
                  {copy.matrixTitle}
                </span>
                <span className="font-['Inter'] text-xs text-[#565e74]">
                  {currentPanel.sourceType === 'demo' ? copy.demoMatrix : copy.realMatrix}
                </span>
              </div>
              <span className="font-['JetBrains_Mono'] text-xs bg-[#ffffff] border border-[#dce9ff] px-2.5 py-1 rounded text-[#006947] font-bold">
                {currentPanel.sourceType === 'demo' ? copy.tutorialBadge : copy.extractedBadge}
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left font-['Inter'] text-xs">
                <thead>
                  <tr className="bg-[#f8f9ff] text-[#565e74] font-['JetBrains_Mono'] text-[11px] uppercase tracking-wider border-b border-[#e2e8f0]">
                    <th className="py-3 px-4">{copy.colMarker}</th>
                    <th className="py-3 px-3">{copy.colValue}</th>
                    <th className="py-3 px-3">{copy.colTarget}</th>
                    <th className="py-3 px-3">{copy.colConfidence}</th>
                    <th className="py-3 px-3 text-right">{copy.colSignoff}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#f1f5f9]">
                  {PHENOAGE_BIOMARKERS.map((bio) => {
                    const currentVal = localValues[bio.id] ?? bio.optimalRange[0];
                    const isOptimal =
                      currentVal >= bio.optimalRange[0] && currentVal <= bio.optimalRange[1];
                    const isVerified = verifiedMap[bio.id];

                    return (
                      <tr
                        key={bio.id}
                        onClick={() => setActiveSnippetKey(bio.id)}
                        className={`transition-colors cursor-pointer ${
                          activeSnippetKey === bio.id ? 'bg-[#eff4ff]/60' : 'hover:bg-[#f8f9ff]'
                        }`}
                      >
                        {/* Biomarker and LOINC */}
                        <td className="py-3.5 px-4">
                          <div className="flex flex-col">
                            <span className="font-bold text-[#0b1c30]">
                              {isBiomarkerId(bio.id) ? m.biomarkers[bio.id].name : bio.name}
                            </span>
                            <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74]">
                              {fill(copy.loinc, { code: bio.loinc })} •{' '}
                              {isBiomarkerId(bio.id) ? m.biomarkers[bio.id].domain : bio.domain}
                            </span>
                          </div>
                        </td>

                        {/* Editable Value */}
                        <td className="py-3.5 px-3">
                          <div className="flex items-center gap-1.5">
                            <input
                              type="number"
                              step={bio.step}
                              value={currentVal}
                              onChange={(e) =>
                                handleValueChange(bio.id, parseFloat(e.target.value) || 0)
                              }
                              className="w-20 px-2 py-1 bg-[#ffffff] border border-[#cbd5e1] rounded font-['JetBrains_Mono'] text-xs font-bold text-[#0b1c30] focus:border-[#006194] focus:outline-none"
                            />
                            <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74]">
                              {bio.unit}
                            </span>
                          </div>
                        </td>

                        {/* Optimal Target */}
                        <td className="py-3.5 px-3 font-['JetBrains_Mono'] text-[11px]">
                          <span
                            className={
                              isOptimal ? 'text-[#006947] font-semibold' : 'text-[#3f4850]'
                            }
                          >
                            {bio.optimalRange[0]} - {bio.optimalRange[1]} {bio.unit}
                          </span>
                        </td>

                        {/* Confidence Score */}
                        <td className="py-3.5 px-3 font-['JetBrains_Mono'] text-[11px]">
                          {typeof currentPanel.confidenceScores[bio.id] === 'number' ? (
                            <span className="bg-[#4edea3]/20 text-[#006947] px-1.5 py-0.5 rounded font-semibold">
                              {currentPanel.confidenceScores[bio.id]}%
                            </span>
                          ) : (
                            <span className="text-[#94a3b8]">—</span>
                          )}
                        </td>

                        {/* Verification Toggle */}
                        <td className="py-3.5 px-3 text-right">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleVerify(bio.id);
                            }}
                            className={`p-1.5 rounded transition-colors cursor-pointer ${
                              isVerified
                                ? 'bg-[#cce5ff] text-[#006194]'
                                : 'bg-[#e2e8f0] text-[#565e74] hover:bg-[#cbd5e1]'
                            }`}
                          >
                            <CheckSquare className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Bottom Confirmation Bar */}
          <div className="bg-[#eff4ff] p-4 rounded-xl border border-[#dce9ff] flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-xs text-[#3f4850]">
              <ShieldCheck className="w-5 h-5 text-[#006947]" />
              <span>
                {copy.readyBar}
              </span>
            </div>

            <button
              onClick={handleVerifyAll}
              disabled={confirmBusy}
              className="w-full sm:w-auto px-6 py-2.5 bg-[#006194] hover:bg-[#007bb9] text-white font-['Inter'] text-xs font-bold rounded shadow-sm flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-60"
            >
              <span>{copy.verifyAll}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
