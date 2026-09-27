import React from 'react';
import { X, CheckCircle, ShieldCheck, Binary, Cpu, FileCheck } from 'lucide-react';
import { fill } from '../i18n/fill';
import { useI18n } from '../i18n/I18nProvider';

interface ProofModalProps {
  isOpen: boolean;
  onClose: () => void;
  biomarkers: Record<string, number>;
  phenoAge: number;
  chronologicalAge: number;
}

export const ProofModal: React.FC<ProofModalProps> = ({
  isOpen,
  onClose,
  biomarkers,
  phenoAge,
  chronologicalAge,
}) => {
  const { m } = useI18n();
  const copy = m.modals;
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#0b1c30]/50 backdrop-blur-xs animate-in fade-in">
      <div className="bg-[#ffffff] rounded-xl border border-[#cbd5e1] shadow-2xl max-w-2xl w-full overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-[#e2e8f0] flex items-center justify-between bg-[#eff4ff]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded bg-[#cce5ff] flex items-center justify-center text-[#006194]">
              <ShieldCheck className="w-5 h-5 text-[#006194]" />
            </div>
            <div>
              <h3 className="font-['Inter'] text-base font-bold text-[#0b1c30]">
                {copy.proofTitle}
              </h3>
              <p className="font-['JetBrains_Mono'] text-xs text-[#565e74]">
                {copy.proofSubtitle}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#565e74] hover:bg-[#e2e8f0] hover:text-[#0b1c30] transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-4">
          {/* Status banner */}
          <div className="bg-[#eff4ff] border border-[#bbf7d0] p-3.5 rounded-lg flex items-start gap-3">
            <CheckCircle className="w-5 h-5 text-[#006947] shrink-0 mt-0.5" />
            <div className="text-sm">
              <span className="font-bold text-[#0b1c30] block">
                {copy.proofBanner}
              </span>
              <span className="text-[#3f4850] text-xs leading-relaxed">
                {copy.proofBannerBody}
              </span>
            </div>
          </div>

          <div className="space-y-2">
            <label className="font-['Inter'] text-xs font-semibold text-[#0b1c30] uppercase tracking-wider block">
              {copy.method}
            </label>
            <div className="bg-[#f8f9ff] border border-[#e2e8f0] p-3 rounded font-['JetBrains_Mono'] text-xs space-y-2 text-[#3f4850]">
              <div className="flex justify-between items-center gap-4">
                <span className="text-[#565e74]">{copy.citation}</span>
                <span className="text-[#0b1c30] text-right">{copy.citationValue}</span>
              </div>
              <div className="flex justify-between items-center gap-4">
                <span className="text-[#565e74]">{copy.inputs}</span>
                <span className="text-[#0b1c30]">{copy.inputsValue}</span>
              </div>
            </div>
          </div>

          {/* Provenance Tree */}
          <div className="space-y-2">
            <label className="font-['Inter'] text-xs font-semibold text-[#0b1c30] uppercase tracking-wider block">
              {copy.trace}
            </label>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-3 bg-[#f8f9ff] rounded border border-[#e2e8f0]">
                <div className="flex items-center gap-1.5 font-semibold text-[#0b1c30] mb-1">
                  <Binary className="w-4 h-4 text-[#006194]" />
                  <span>{copy.inputVector}</span>
                </div>
                <div className="text-[#565e74] space-y-0.5 font-mono text-[11px]">
                  <p>{fill(copy.chronological, { value: chronologicalAge.toFixed(1) })}</p>
                  <p>{copy.markerCount}</p>
                  <p>{fill(copy.albuminLine, { value: biomarkers['albumin'] ?? 46.0 })}</p>
                  <p>{fill(copy.crpLine, { value: biomarkers['crp'] ?? 0.8 })}</p>
                </div>
              </div>
              <div className="p-3 bg-[#f8f9ff] rounded border border-[#e2e8f0]">
                <div className="flex items-center gap-1.5 font-semibold text-[#0b1c30] mb-1">
                  <Cpu className="w-4 h-4 text-[#006947]" />
                  <span>{copy.computedHazard}</span>
                </div>
                <div className="text-[#565e74] space-y-0.5 font-mono text-[11px]">
                  <p>{fill(copy.biologicalLine, { value: phenoAge.toFixed(1) })}</p>
                  <p>{fill(copy.differenceLine, { value: (phenoAge - chronologicalAge).toFixed(1) })}</p>
                  <p>{copy.whereLine}</p>
                  <p>{copy.useLine}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-[#eff4ff] p-3 rounded text-xs text-[#3f4850] flex items-center gap-2">
            <FileCheck className="w-4 h-4 text-[#006194] shrink-0" />
            <span>
              {copy.loincNote}
            </span>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-[#e2e8f0] bg-[#f8f9ff] flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded font-['Inter'] text-sm font-semibold bg-[#006194] text-[#ffffff] hover:bg-[#007bb9] transition-colors cursor-pointer"
          >
            {copy.closeInspector}
          </button>
        </div>
      </div>
    </div>
  );
};
