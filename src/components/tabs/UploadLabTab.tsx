import React, { useEffect, useState } from 'react';
import { TabType, LabPanelData, TokenUsageNotice } from '../../types';
import { INITIAL_BIOMARKERS, PHENOAGE_BIOMARKERS, PRESET_LAB_PANELS } from '../../data/phenoAgeData';
import {
  ExtractRequestError,
  ExtractResult,
  RedactionPreview,
  confirmRedactedFrame,
  discardRedactedFrame,
  extractLabFile,
} from '../../api/uploads';
import { HEALTH_CONSENT_VERSION, fetchOwnConsents } from '../../api/accounts';
import { LabImageCrop, RedactionConfirm } from '../LabImagePrep';
import { TokenUsageBanner } from '../TokenUsageBanner';
import { fill } from '../../i18n/fill';
import { getActiveI18n } from '../../i18n/catalog';
import { useI18n } from '../../i18n/I18nProvider';
import {
  UploadCloud,
  Lock,
  Cpu,
  ShieldCheck,
  ArrowRight,
  FileCheck,
  RefreshCw,
  Sparkles,
} from 'lucide-react';

interface UploadLabTabProps {
  onLoadPanel: (panel: LabPanelData) => void;
  setActiveTab: (tab: TabType) => void;
  accountAddress: string;
  isAuthenticated: boolean;
  onRequestAuth: () => void;
}

export const UploadLabTab: React.FC<UploadLabTabProps> = ({
  onLoadPanel,
  setActiveTab,
  accountAddress,
  isAuthenticated,
  onRequestAuth,
}) => {
  const { m } = useI18n();
  const copy = m.upload;
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progressStep, setProgressStep] = useState(0);
  const [progressMsg, setProgressMsg] = useState('');
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [tokenNotice, setTokenNotice] = useState<TokenUsageNotice | null>(null);
  const [cropFile, setCropFile] = useState<File | null>(null);
  const [redactionPreview, setRedactionPreview] = useState<RedactionPreview | null>(null);
  /** The current health-data consent is not active, so the server will refuse a file. */
  const [consentMissing, setConsentMissing] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      setConsentMissing(false);
      return;
    }
    let cancelled = false;
    void fetchOwnConsents()
      .then((rows) => {
        if (!cancelled) {
          setConsentMissing(
            !rows.some(
              (row) =>
                row.type === 'health_data' &&
                row.version === HEALTH_CONSENT_VERSION &&
                row.withdrawn_at === null,
            ),
          );
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  /** Turn the API's consent refusal into the prompt; other errors stay as they are. */
  const showUploadError = (err: unknown) => {
    if (err instanceof Error && err.message === 'Current health-data consent is required') {
      setConsentMissing(true);
      setUploadError(null);
      return;
    }
    setUploadError(err instanceof Error ? err.message : getActiveI18n().messages.shell.extractionFailed);
  };

  const loadPresetPanel = (
    fileName: string,
    presetKey: 'quest' | 'labcorp' | 'nhs' = 'quest'
  ) => {
    setUploadError(null);
    setTokenNotice(null);
    setIsProcessing(true);
    setSelectedFileName(fileName);
    setProgressStep(5);
    setProgressMsg(getActiveI18n().messages.upload.loadingDemo);

    const preset = PRESET_LAB_PANELS[presetKey];
    const newPanel: LabPanelData = {
      id: `panel-${Date.now()}`,
      labName: preset.source,
      testDate: preset.date,
      sourceType: 'demo',
      fileName: fileName,
      chronologicalAge: preset.age,
      gender: 'male',
      biomarkers: { ...preset.values },
      confidenceScores: { ...preset.confidence },
      verified: false,
      hash: `demo-${presetKey}`,
      focusMarkerIds: Object.keys(preset.values),
    };

    onLoadPanel(newPanel);
    setIsProcessing(false);
    setActiveTab('review-extraction');
  };

  const openReview = (fileName: string, extracted: ExtractResult) => {
    setTokenNotice(extracted.tokenUsage);
    setProgressStep(5);
    setProgressMsg(getActiveI18n().messages.upload.ready);

      const biomarkers: Record<string, number> = { ...INITIAL_BIOMARKERS };
      const confidenceScores: Record<string, number> = {};
      PHENOAGE_BIOMARKERS.forEach((item) => {
        confidenceScores[item.id] = 0;
      });
      const focusMarkerIds: string[] = [];
      for (const marker of extracted.markers) {
        if (marker.canonicalId) {
          biomarkers[marker.canonicalId] = marker.value;
          confidenceScores[marker.canonicalId] = marker.confidence;
          focusMarkerIds.push(marker.canonicalId);
        }
      }

      const newPanel: LabPanelData = {
        id: `panel-${Date.now()}`,
        labName: extracted.labName ?? getActiveI18n().messages.shell.unknownLaboratory,
        testDate: extracted.collectedAt ?? new Date().toISOString().slice(0, 10),
        sourceType: 'pdf',
        fileName,
        chronologicalAge: extracted.chronologicalAge ?? 42,
        gender: 'male',
        biomarkers,
        confidenceScores,
        verified: false,
        hash: extracted.documentSha256,
        extractToken: extracted.extractToken,
        parserVersion: extracted.parserVersion,
        extractedMarkers: extracted.markers,
        tokenUsage: extracted.tokenUsage,
        focusMarkerIds,
      };
      onLoadPanel(newPanel);
      setActiveTab('review-extraction');
  };

  const processLabFile = async (file: File) => {
    if (!isAuthenticated) {
      onRequestAuth();
      return;
    }
    setUploadError(null);
    setTokenNotice(null);
    setCropFile(null);
    setIsProcessing(true);
    setSelectedFileName(file.name);
    setProgressStep(1);
    setProgressMsg(getActiveI18n().messages.upload.uploading);
    try {
      setProgressStep(2);
      setProgressMsg(getActiveI18n().messages.upload.masking);
      const outcome = await extractLabFile(file);
      if (outcome.kind === 'confirm-redaction') {
        setRedactionPreview(outcome.preview);
        setProgressMsg(getActiveI18n().messages.upload.redactionTitle);
        return;
      }
      openReview(file.name, outcome.result);
    } catch (err) {
      if (err instanceof ExtractRequestError && err.usage) {
        setTokenNotice(err.usage);
        setUploadError(null);
      } else {
        setTokenNotice(null);
        showUploadError(err);
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const beginFile = (file: File) => {
    if (!isAuthenticated) {
      onRequestAuth();
      return;
    }
    if (file.type.startsWith('image/')) {
      setUploadError(null);
      setRedactionPreview(null);
      setCropFile(file);
      return;
    }
    void processLabFile(file);
  };

  const acceptPaintedFrame = async () => {
    if (!redactionPreview) {
      return;
    }
    setUploadError(null);
    setIsProcessing(true);
    setProgressMsg(getActiveI18n().messages.upload.hashing);
    try {
      const extracted = await confirmRedactedFrame(redactionPreview.redactionToken);
      const name = selectedFileName ?? 'lab-photo.png';
      setRedactionPreview(null);
      openReview(name, extracted);
    } catch (err) {
      if (err instanceof ExtractRequestError && err.usage) {
        setTokenNotice(err.usage);
        setUploadError(null);
      } else {
        showUploadError(err);
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const cancelPaintedFrame = () => {
    if (redactionPreview) {
      void discardRedactedFrame(redactionPreview.redactionToken).catch(() => undefined);
    }
    setRedactionPreview(null);
    setIsProcessing(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      beginFile(files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      beginFile(e.target.files[0]);
      e.target.value = '';
    }
  };

  return (
    <div className="w-full max-w-[1440px] mx-auto px-4 lg:px-8 py-8 flex flex-col gap-8">
      {/* Header and Step Info */}
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
        </div>

        {/* Security badge */}
        <div className="bg-[#ffffff] border border-[#dce9ff] p-3 rounded-lg shadow-xs flex items-center gap-3 shrink-0">
          <div className="w-8 h-8 rounded-full bg-[#4edea3]/20 flex items-center justify-center text-[#006947]">
            <Lock className="w-4 h-4" />
          </div>
          <div className="flex flex-col">
            <span className="font-['JetBrains_Mono'] text-xs font-bold text-[#0b1c30]">
              {copy.originalNotStored}
            </span>
            <span className="font-['JetBrains_Mono'] text-[11px] text-[#006947]">
              {!isAuthenticated ? copy.signInToExtract : fill(copy.session, { id: accountAddress })}
            </span>
          </div>
        </div>
      </div>

      {/* Main Grid: Upload Dropzone & Preset Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Dropzone & Progress */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          {cropFile && (
            <LabImageCrop
              file={cropFile}
              title={copy.cropTitle}
              lead={copy.cropLead}
              hint={copy.cropHint}
              sendCrop={copy.cropSend}
              sendWhole={copy.cropWhole}
              cancel={copy.cropCancel}
              onCancel={() => setCropFile(null)}
              onSubmit={(file) => {
                void processLabFile(file);
              }}
            />
          )}
          {redactionPreview && (
            <RedactionConfirm
              previewPng={redactionPreview.previewPng}
              title={copy.redactionTitle}
              body={fill(copy.redactionBody, { count: redactionPreview.regionCount })}
              confirm={copy.redactionConfirm}
              cancel={copy.redactionCancel}
              busy={isProcessing}
              onConfirm={() => {
                void acceptPaintedFrame();
              }}
              onCancel={cancelPaintedFrame}
            />
          )}
          {/* Dropzone container */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-xl p-8 lg:p-12 text-center transition-all bg-[#ffffff] flex flex-col items-center justify-center gap-4 ${
              cropFile || redactionPreview ? 'hidden' : ''
            } ${
              isDragging
                ? 'border-[#006194] bg-[#eff4ff]'
                : 'border-[#cbd5e1] hover:border-[#006194]'
            }`}
          >
            <div className="w-16 h-16 rounded-full bg-[#eff4ff] border border-[#dce9ff] flex items-center justify-center text-[#006194]">
              <UploadCloud className="w-8 h-8" />
            </div>

            <div className="flex flex-col gap-1 max-w-md">
              <span className="font-['Inter'] text-base font-bold text-[#0b1c30]">
                {copy.dropTitle}
              </span>
              <span className="font-['Inter'] text-xs text-[#565e74]">
                {copy.dropHint}
              </span>
            </div>

            <div className="flex items-center gap-3">
              <label className="bg-[#006194] hover:bg-[#007bb9] text-[#ffffff] px-5 py-2.5 rounded font-['Inter'] text-xs font-semibold transition-colors cursor-pointer shadow-xs">
                {copy.selectFile}
                <input
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg,.tiff"
                  onChange={handleFileSelect}
                  className="hidden"
                  disabled={isProcessing}
                />
              </label>
              <span className="text-xs text-[#94a3b8] font-mono">{copy.demoAside}</span>
            </div>

            <div className="pt-4 mt-2 border-t border-[#f1f5f9] w-full flex items-center justify-center gap-6 text-xs text-[#565e74] font-['JetBrains_Mono']">
              <span className="flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-[#006947]" /> {copy.parser}
              </span>
              <span className="flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-[#006194]" /> {copy.ramOnly}
              </span>
            </div>
          </div>

          {tokenNotice && <TokenUsageBanner usage={tokenNotice} />}

          {consentMissing && (
            <div
              className="bg-[#fff6e0] p-4 rounded-xl border border-[#f5c97a] flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
              role="alert"
            >
              <p className="font-['Inter'] text-[15px] text-[#5c3a00]">{copy.consentMissing}</p>
              <button
                type="button"
                onClick={() => setActiveTab('data-sovereignty-public-sharing')}
                className="shrink-0 rounded-md bg-[#006194] px-4 py-2 font-['Inter'] text-[15px] font-semibold text-[#ffffff] hover:bg-[#004b73] cursor-pointer"
              >
                {copy.consentAction}
              </button>
            </div>
          )}

          {uploadError && (
            <div className="bg-[#fff1f2] p-4 rounded-xl border border-[#fecdd3] text-xs text-[#9f1239] font-['Inter']">
              {uploadError}
            </div>
          )}

          {/* Processing Simulation Animation */}
          {isProcessing && (
            <div className="bg-[#ffffff] p-5 rounded-xl border border-[#cbd5e1] shadow-md flex flex-col gap-3 animate-in fade-in">
              <div className="flex items-center justify-between text-xs">
                <span className="font-['JetBrains_Mono'] text-[#006194] font-bold flex items-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin text-[#006194]" />
                  {fill(copy.parsing, { file: selectedFileName ?? '' })}
                </span>
                <span className="font-['JetBrains_Mono'] text-[#565e74]">{fill(copy.step, { current: progressStep })}</span>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-[#eff4ff] h-2 rounded-full overflow-hidden">
                <div
                  className="bg-[#006194] h-full transition-all duration-300"
                  style={{ width: `${(progressStep / 5) * 100}%` }}
                ></div>
              </div>

              <span className="font-['JetBrains_Mono'] text-xs text-[#0b1c30] font-medium bg-[#f8f9ff] p-2.5 rounded border border-[#e2e8f0]">
                {progressMsg}
              </span>
            </div>
          )}

          {/* Verification Protocol Info Box */}
          <div className="bg-[#eff4ff] p-4 rounded-xl border border-[#dce9ff] flex items-start gap-3 text-xs text-[#3f4850]">
            <FileCheck className="w-5 h-5 text-[#006194] shrink-0 mt-0.5" />
            <div className="leading-relaxed">
              <strong className="text-[#0b1c30] block mb-0.5">
                {copy.safeguardTitle}
              </strong>
              {copy.safeguardBody}
            </div>
          </div>
        </div>

        {/* Demo fixtures. These buttons do not upload a file. */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          <div className="bg-[#f8f9ff] p-6 rounded-xl border border-dashed border-[#94a3b8] flex flex-col gap-4">
            <div className="flex items-center justify-between gap-3">
              <span className="font-['Inter'] text-sm font-bold text-[#0b1c30] flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[#565e74]" />
                {copy.demoTitle}
              </span>
              <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74] bg-[#ffffff] border border-[#e2e8f0] px-1.5 py-0.5 rounded">
                {copy.demoBadge}
              </span>
            </div>
            <p className="font-['Inter'] text-xs text-[#565e74] leading-relaxed">
              {copy.demoLead}
            </p>

            {/* Presets List */}
            <div className="flex flex-col gap-3">
              {/* Preset 1: Quest */}
              <button
                onClick={() => loadPresetPanel('Quest sample', 'quest')}
                disabled={isProcessing}
                className="text-left p-3.5 rounded-lg border border-[#e2e8f0] hover:border-[#006194] hover:bg-[#ffffff] transition-all bg-[#ffffff] group cursor-pointer flex flex-col gap-1"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-['Inter'] text-xs font-bold text-[#0b1c30] group-hover:text-[#006194]">
                    {copy.questTitle}
                  </span>
                  <span className="font-['JetBrains_Mono'] text-[10px] bg-[#4edea3]/20 text-[#006947] font-semibold px-1.5 py-0.5 rounded">
                    {copy.questBadge}
                  </span>
                </div>
                <div className="text-[11px] text-[#565e74] flex items-center justify-between">
                  <span>{copy.questMeta}</span>
                  <ArrowRight className="w-3.5 h-3.5 text-[#006194] opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              </button>

              {/* Preset 2: LabCorp */}
              <button
                onClick={() => loadPresetPanel('LabCorp sample', 'labcorp')}
                disabled={isProcessing}
                className="text-left p-3.5 rounded-lg border border-[#e2e8f0] hover:border-[#006194] hover:bg-[#ffffff] transition-all bg-[#ffffff] group cursor-pointer flex flex-col gap-1"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-['Inter'] text-xs font-bold text-[#0b1c30] group-hover:text-[#006194]">
                    {copy.labcorpTitle}
                  </span>
                  <span className="font-['JetBrains_Mono'] text-[10px] bg-[#eff4ff] text-[#006194] font-semibold px-1.5 py-0.5 rounded">
                    {copy.labcorpBadge}
                  </span>
                </div>
                <div className="text-[11px] text-[#565e74] flex items-center justify-between">
                  <span>{copy.labcorpMeta}</span>
                  <ArrowRight className="w-3.5 h-3.5 text-[#006194] opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              </button>

              {/* Preset 3: NHS */}
              <button
                onClick={() => loadPresetPanel('NHS sample', 'nhs')}
                disabled={isProcessing}
                className="text-left p-3.5 rounded-lg border border-[#e2e8f0] hover:border-[#006194] hover:bg-[#ffffff] transition-all bg-[#ffffff] group cursor-pointer flex flex-col gap-1"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-['Inter'] text-xs font-bold text-[#0b1c30] group-hover:text-[#006194]">
                    {copy.nhsTitle}
                  </span>
                  <span className="font-['JetBrains_Mono'] text-[10px] bg-[#fff1f2] text-[#ba1a1a] font-semibold px-1.5 py-0.5 rounded">
                    {copy.nhsBadge}
                  </span>
                </div>
                <div className="text-[11px] text-[#565e74] flex items-center justify-between">
                  <span>{copy.nhsMeta}</span>
                  <ArrowRight className="w-3.5 h-3.5 text-[#006194] opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              </button>
            </div>
          </div>

          {/* Supported Format Specifications Card */}
          <div className="bg-[#ffffff] p-5 rounded-xl border border-[#e2e8f0] flex flex-col gap-2.5 text-xs text-[#3f4850]">
            <span className="font-['Inter'] font-bold text-[#0b1c30]">
              {copy.coverageTitle}
            </span>
            <div className="grid grid-cols-2 gap-2 text-[11px] text-[#565e74] font-['JetBrains_Mono']">
              <div>✓ {copy.coverageCbc}</div>
              <div>✓ {copy.coverageCmp}</div>
              <div>✓ {copy.coverageCrp}</div>
              <div>✓ {copy.coverageAlp}</div>
              <div>✓ {copy.coverageGlucose}</div>
              <div>✓ {copy.coverageRdw}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
