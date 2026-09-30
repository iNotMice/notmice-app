import React from 'react';
import { TabType } from '../../types';
import {
  Dna,
  Key,
  ShieldCheck,
  FileText,
  Cpu,
  Lock,
  Zap,
  CheckSquare,
  Share2,
  AlertCircle,
  Activity,
  Calculator,
  Database,
  ArrowRight,
  FlaskConical,
} from 'lucide-react';
import logo from '../../assets/images/logo.jpg';
import { PHENOAGE_BIOMARKERS } from '../../data/phenoAgeData';
import { isBiomarkerId } from '../../i18n/biomarkerIds';
import { useI18n } from '../../i18n/I18nProvider';

interface OverviewTabProps {
  setActiveTab: (tab: TabType) => void;
  onOpenSeedPhrase: () => void;
  onOpenProofModal: () => void;
  biomarkers: Record<string, number>;
  onUpdateBiomarkers: (updated: Record<string, number>) => void;
  phenoAge: number | null;
  chronologicalAge: number;
  disclaimer: string;
  isAuthenticated: boolean;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({
  setActiveTab,
  onOpenSeedPhrase,
  onOpenProofModal,
  biomarkers,
  onUpdateBiomarkers,
  phenoAge,
  chronologicalAge,
  disclaimer,
  isAuthenticated,
}) => {
  const { m } = useI18n();
  const copy = m.overview;
  const alb = biomarkers['albumin'] ?? 46.0;
  const crp = biomarkers['crp'] ?? 0.8;

  const handleAlbuminChange = (val: number) => {
    onUpdateBiomarkers({ ...biomarkers, albumin: val });
  };

  const handleCrpChange = (val: number) => {
    onUpdateBiomarkers({ ...biomarkers, crp: val });
  };

  return (
    <div className="flex flex-col w-full">
      {/* Hero Section with Dual Column Layout & Interactive Engine Preview */}
      <section className="w-full max-w-[1440px] mx-auto px-4 lg:px-8 pt-8 pb-10">
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 items-start">
          {/* Left Column: Scientific Positioning & CTA */}
          <div className="xl:col-span-7 flex flex-col items-start gap-4">
            {/* Subhead Badge */}
            <div className="inline-flex items-center gap-1.5 bg-[#cce5ff] text-[#004b73] px-3 py-1 rounded font-['JetBrains_Mono'] text-xs font-semibold uppercase tracking-wider">
              <Dna className="w-3.5 h-3.5" />
              <span>{copy.badge}</span>
            </div>

            {/* Headline */}
            <h1 className="font-['Inter'] text-3xl sm:text-4xl lg:text-[44px] leading-tight lg:leading-[52px] text-[#0b1c30] tracking-tight font-bold">
              {copy.headline}{' '}
              <span className="text-[#006194] underline decoration-[#006194]/30 underline-offset-8">
                {copy.headlineAccent}
              </span>
            </h1>

            {/* Value Proposition */}
            <p className="font-['Inter'] text-base text-[#3f4850] max-w-2xl leading-relaxed">
              {copy.valueProp}
            </p>

            {/* CTA Cluster */}
            <div className="flex flex-wrap items-center gap-4 pt-1 w-full sm:w-auto">
              <button
                onClick={onOpenSeedPhrase}
                className="w-full sm:w-auto bg-[#006194] hover:bg-[#007bb9] text-[#ffffff] px-6 py-3 rounded font-['Inter'] text-sm font-semibold transition-all shadow-sm flex items-center justify-center gap-2 cursor-pointer"
                id="btn-seed"
              >
                <Key className="w-4 h-4" />
                <span>{isAuthenticated ? copy.openAccount : copy.getStarted}</span>
              </button>
              <button
                onClick={() => setActiveTab('data-sovereignty-public-sharing')}
                className="w-full sm:w-auto bg-[#eff4ff] hover:bg-[#e5eeff] text-[#0b1c30] px-6 py-3 rounded font-['Inter'] text-sm font-medium transition-colors flex items-center justify-center gap-2 border border-[#dce9ff] cursor-pointer"
                id="btn-charter"
              >
                <FileText className="w-4 h-4 text-[#006194]" />
                <span>{copy.exploreCharter}</span>
              </button>
            </div>

            {/* System Architecture Metadata */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 w-full pt-4">
              <div className="bg-[#ffffff] p-3.5 rounded border border-[#e2e8f0] shadow-xs flex flex-col gap-0.5">
                <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74] uppercase">
                  {copy.runtime}
                </span>
                <span className="font-['JetBrains_Mono'] text-xs text-[#006947] font-bold flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5" /> {copy.serverExtract}
                </span>
              </div>
              <div className="bg-[#ffffff] p-3.5 rounded border border-[#e2e8f0] shadow-xs flex flex-col gap-0.5">
                <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74] uppercase">
                  {copy.biomarkerStandard}
                </span>
                <span className="font-['JetBrains_Mono'] text-xs text-[#0b1c30] font-semibold flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-[#006194]" /> {copy.loincDictionary}
                </span>
              </div>
              <div className="bg-[#ffffff] p-3.5 rounded border border-[#e2e8f0] shadow-xs flex flex-col gap-0.5 col-span-2 sm:col-span-1">
                <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74] uppercase">
                  {copy.indexLabel}
                </span>
                <span className="font-['JetBrains_Mono'] text-xs text-[#006194] font-semibold flex items-center gap-1.5">
                  <FlaskConical className="w-3.5 h-3.5" /> {copy.levineModel}
                </span>
              </div>
            </div>
          </div>

          {/* Right Column: Interactive Biological Age Engine Showcase Card */}
          <div className="xl:col-span-5 w-full flex flex-col gap-4">
            {/* Main PhenoAge Showcase Deck */}
            <div className="bg-[#ffffff] p-6 rounded-xl border border-[#cbd5e1] shadow-md flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded bg-[#cce5ff] flex items-center justify-center text-[#006194]">
                    <Activity className="w-5 h-5 text-[#006194]" />
                  </div>
                  <div>
                    <span className="font-['Inter'] text-sm font-bold text-[#0b1c30] block">
                      {copy.engineScore}
                    </span>
                    <span className="font-['JetBrains_Mono'] text-xs text-[#565e74]">
                      {copy.tutorialCalculated}
                    </span>
                  </div>
                </div>
                <span className="bg-[#eff4ff] text-[#004b73] font-['JetBrains_Mono'] text-xs px-2 py-1 rounded font-bold">
                  {copy.workedExample}
                </span>
              </div>

              {/* Chrono vs Biological Gauge Comparison */}
              <div className="grid grid-cols-2 gap-4 p-4 bg-[#eff4ff] rounded-lg border border-[#dce9ff]">
                <div className="flex flex-col">
                  <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74] uppercase font-medium">
                    {copy.chronological}
                  </span>
                  <span className="font-['Inter'] text-3xl sm:text-4xl font-bold text-[#0b1c30] mt-1">
                    {chronologicalAge.toFixed(1)}
                  </span>
                  <span className="font-['Inter'] text-xs text-[#565e74]">
                    {copy.baselineYears}
                  </span>
                </div>
                <div className="flex flex-col">
                  <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74] uppercase font-medium">
                    {copy.biological}
                  </span>
                  <span
                    className="font-['Inter'] text-3xl sm:text-4xl font-bold text-[#006194] mt-1"
                    id="bio-age-val"
                  >
                    {phenoAge === null ? '…' : phenoAge.toFixed(1)}
                  </span>
                  <span className="font-['Inter'] text-xs text-[#565e74]">
                    {copy.researchIndex}
                  </span>
                </div>
              </div>
              <p className="font-['Inter'] text-xs text-[#3f4850] border-l-2 border-[#006194] pl-3">
                {disclaimer}
              </p>

              {/* Dynamic Biomarker Interactive Sliders */}
              <div className="flex flex-col gap-3 pt-1">
                <div className="flex items-center justify-between">
                  <span className="font-['Inter'] text-xs font-semibold text-[#0b1c30]">
                    {copy.sensitivity}
                  </span>
                  <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74]">
                    {copy.adjustDelta}
                  </span>
                </div>

                {/* Biomarker Micro Row 1: Albumin */}
                <div className="bg-[#eff4ff]/70 p-3 rounded border border-[#dce9ff] flex flex-col gap-1.5">
                  <div className="flex justify-between items-center font-['Inter'] text-xs">
                    <span className="font-medium text-[#0b1c30]">
                      {copy.albuminLabel}
                    </span>
                    <span
                      className="font-['JetBrains_Mono'] text-xs font-bold text-[#006194]"
                      id="val-alb"
                    >
                      {alb.toFixed(1)} g/L
                    </span>
                  </div>
                  <div className="relative w-full flex items-center">
                    <input
                      className="w-full accent-[#006194] h-1.5 bg-[#dce9ff] rounded cursor-pointer"
                      id="slider-alb"
                      max="52"
                      min="30"
                      step="0.5"
                      type="range"
                      value={alb}
                      onChange={(e) => handleAlbuminChange(parseFloat(e.target.value))}
                    />
                  </div>
                  <div className="flex justify-between text-[#565e74] font-['JetBrains_Mono'] text-[10px]">
                    <span>{copy.albuminLow}</span>
                    <span>{copy.albuminMid}</span>
                    <span>52.0</span>
                  </div>
                </div>

                {/* Biomarker Micro Row 2: hs-CRP */}
                <div className="bg-[#eff4ff]/70 p-3 rounded border border-[#dce9ff] flex flex-col gap-1.5">
                  <div className="flex justify-between items-center font-['Inter'] text-xs">
                    <span className="font-medium text-[#0b1c30]">
                      {copy.crpLabel}
                    </span>
                    <span
                      className="font-['JetBrains_Mono'] text-xs font-bold text-[#006194]"
                      id="val-crp"
                    >
                      {crp.toFixed(2)} mg/L
                    </span>
                  </div>
                  <div className="relative w-full flex items-center">
                    <input
                      className="w-full accent-[#006194] h-1.5 bg-[#dce9ff] rounded cursor-pointer"
                      id="slider-crp"
                      max="6.0"
                      min="0.1"
                      step="0.1"
                      type="range"
                      value={crp}
                      onChange={(e) => handleCrpChange(parseFloat(e.target.value))}
                    />
                  </div>
                  <div className="flex justify-between text-[#565e74] font-['JetBrains_Mono'] text-[10px]">
                    <span>{copy.crpLow}</span>
                    <span>{copy.crpMid}</span>
                    <span>{copy.crpHigh}</span>
                  </div>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-[#eff4ff] p-2.5 rounded border border-[#dce9ff] text-[#3f4850] font-['JetBrains_Mono'] text-xs">
                <div className="flex items-center gap-1.5 truncate">
                  <ShieldCheck className="w-4 h-4 text-[#006947] shrink-0" />
                  <span className="truncate">{copy.noLabFile}</span>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <button
                    onClick={() => setActiveTab('phenoage-engine')}
                    className="text-[#006947] hover:underline font-['Inter'] text-xs font-semibold flex items-center gap-1 cursor-pointer"
                  >
                    <span>{copy.longevityAdvice}</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                  <button
                    onClick={onOpenProofModal}
                    className="text-[#006194] hover:text-[#007bb9] font-['Inter'] text-xs font-semibold shrink-0 cursor-pointer"
                  >
                    {copy.inspectProof}
                  </button>
                </div>
              </div>
            </div>

            {/* Comparative Mouse vs Human Research Callout Card */}
            <div className="bg-[#007bb9] text-[#ffffff] p-5 rounded-xl flex items-center gap-4 shadow-sm">
              <div className="w-12 h-12 rounded-full bg-white/20 p-1 flex items-center justify-center shrink-0 ring-2 ring-white/30">
                <img
                  alt="Logo"
                  className="w-full h-full rounded-full object-cover"
                  src={logo}
                  referrerPolicy="no-referrer"
                />
              </div>
              <div className="flex flex-col">
                <span className="font-['Inter'] text-lg font-bold leading-snug">
                  {copy.whyNotMice}
                </span>
                <span className="font-['Inter'] text-xs opacity-90 mt-0.5 leading-relaxed">
                  {copy.whyBody}
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Method & Scientific Architecture Preview (4-Step Pipeline) */}
      <section className="w-full bg-[#eff4ff] py-12 border-y border-[#dce9ff]">
        <div className="max-w-[1440px] mx-auto px-4 lg:px-8 flex flex-col gap-8">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div className="flex flex-col gap-1">
              <span className="font-['JetBrains_Mono'] text-xs text-[#006194] font-bold uppercase tracking-widest">
                {copy.pipelineKicker}
              </span>
              <h2 className="font-['Inter'] text-2xl lg:text-3xl text-[#0b1c30] font-bold tracking-tight">
                {copy.pipelineTitle}
              </h2>
            </div>
            <p className="font-['Inter'] text-sm text-[#3f4850] max-w-xl">
              {copy.pipelineLead}
            </p>
          </div>

          {/* Diagrammatic 4-Step Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {/* Step 1 */}
            <div className="bg-[#ffffff] p-6 rounded-xl border border-[#e2e8f0] shadow-xs flex flex-col gap-3 relative">
              <div className="flex items-center justify-between">
                <div className="w-9 h-9 rounded bg-[#eff4ff] flex items-center justify-center text-[#006194] font-['Inter'] text-lg font-bold">
                  01
                </div>
                <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74] uppercase bg-[#eff4ff] px-2 py-0.5 rounded font-medium">
                  {copy.stepInput}
                </span>
              </div>
              <div className="flex flex-col gap-1 mt-1">
                <span className="font-['Inter'] text-base font-bold text-[#0b1c30]">
                  {copy.step1Title}
                </span>
                <p className="font-['Inter'] text-xs text-[#3f4850] leading-relaxed">
                  {copy.step1Body}
                </p>
              </div>
              <div className="mt-auto pt-3 flex items-center gap-1.5 text-[#565e74] font-['JetBrains_Mono'] text-[11px]">
                <Lock className="w-3.5 h-3.5 text-[#006947]" />
                <span>{copy.step1Foot}</span>
              </div>
            </div>

            {/* Step 2 */}
            <div className="bg-[#ffffff] p-6 rounded-xl border border-[#e2e8f0] shadow-xs flex flex-col gap-3 relative">
              <div className="flex items-center justify-between">
                <div className="w-9 h-9 rounded bg-[#eff4ff] flex items-center justify-center text-[#006194] font-['Inter'] text-lg font-bold">
                  02
                </div>
                <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74] uppercase bg-[#eff4ff] px-2 py-0.5 rounded font-medium">
                  {copy.stepProcess}
                </span>
              </div>
              <div className="flex flex-col gap-1 mt-1">
                <span className="font-['Inter'] text-base font-bold text-[#0b1c30]">
                  {copy.step2Title}
                </span>
                <p className="font-['Inter'] text-xs text-[#3f4850] leading-relaxed">
                  {copy.step2Body}
                </p>
              </div>
              <div className="mt-auto pt-3 flex items-center gap-1.5 text-[#565e74] font-['JetBrains_Mono'] text-[11px]">
                <Zap className="w-3.5 h-3.5 text-[#006947]" />
                <span>{copy.step2Foot}</span>
              </div>
            </div>

            {/* Step 3 */}
            <div className="bg-[#ffffff] p-6 rounded-xl border border-[#e2e8f0] shadow-xs flex flex-col gap-3 relative">
              <div className="flex items-center justify-between">
                <div className="w-9 h-9 rounded bg-[#eff4ff] flex items-center justify-center text-[#006194] font-['Inter'] text-lg font-bold">
                  03
                </div>
                <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74] uppercase bg-[#eff4ff] px-2 py-0.5 rounded font-medium">
                  {copy.stepVerify}
                </span>
              </div>
              <div className="flex flex-col gap-1 mt-1">
                <span className="font-['Inter'] text-base font-bold text-[#0b1c30]">
                  {copy.step3Title}
                </span>
                <p className="font-['Inter'] text-xs text-[#3f4850] leading-relaxed">
                  {copy.step3Body}
                </p>
              </div>
              <div className="mt-auto pt-3 flex items-center gap-1.5 text-[#565e74] font-['JetBrains_Mono'] text-[11px]">
                <CheckSquare className="w-3.5 h-3.5 text-[#006947]" />
                <span>{copy.step3Foot}</span>
              </div>
            </div>

            {/* Step 4 */}
            <div className="bg-[#ffffff] p-6 rounded-xl border border-[#e2e8f0] shadow-xs flex flex-col gap-3 relative">
              <div className="flex items-center justify-between">
                <div className="w-9 h-9 rounded bg-[#eff4ff] flex items-center justify-center text-[#006194] font-['Inter'] text-lg font-bold">
                  04
                </div>
                <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74] uppercase bg-[#eff4ff] px-2 py-0.5 rounded font-medium">
                  {copy.stepCompute}
                </span>
              </div>
              <div className="flex flex-col gap-1 mt-1">
                <span className="font-['Inter'] text-base font-bold text-[#0b1c30]">
                  {copy.step4Title}
                </span>
                <p className="font-['Inter'] text-xs text-[#3f4850] leading-relaxed">
                  {copy.step4Body}
                </p>
              </div>
              <div className="mt-auto pt-3 flex items-center gap-1.5 text-[#565e74] font-['JetBrains_Mono'] text-[11px]">
                <Share2 className="w-3.5 h-3.5 text-[#006947]" />
                <span>{copy.step4Foot}</span>
              </div>
            </div>
          </div>

          {/* Scientific Disclaimer Banner */}
          <div className="w-full bg-[#ffffff] p-4 rounded-lg border border-[#cbd5e1] flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-[#565e74] shrink-0 mt-0.5" />
            <div className="flex flex-col gap-0.5">
              <span className="font-['Inter'] text-xs font-bold text-[#0b1c30]">
                {copy.noticeTitle}
              </span>
              <p className="font-['Inter'] text-xs text-[#3f4850] leading-relaxed">
                {copy.noticeBody}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Trust & Verification Protocol (3 Deep-Dive Cards) */}
      <section className="w-full max-w-[1440px] mx-auto px-4 lg:px-8 py-12">
        <div className="flex flex-col gap-1 mb-6">
          <span className="font-['JetBrains_Mono'] text-xs text-[#006194] font-bold uppercase tracking-wider">
            {copy.privacyKicker}
          </span>
          <h2 className="font-['Inter'] text-2xl lg:text-3xl text-[#0b1c30] font-bold">
            {copy.privacyTitle}
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1 */}
          <div className="bg-[#ffffff] p-6 rounded-xl border border-[#e2e8f0] shadow-xs flex flex-col justify-between">
            <div className="flex flex-col gap-3">
              <div className="w-11 h-11 rounded bg-[#4edea3]/20 text-[#006947] flex items-center justify-center">
                <Cpu className="w-6 h-6 text-[#006947]" />
              </div>
              <h3 className="font-['Inter'] text-xl text-[#0b1c30] font-bold">
                {copy.card1Title}
              </h3>
              <p className="font-['Inter'] text-sm text-[#3f4850] leading-relaxed">
                {copy.card1Body}
              </p>
            </div>
            <div className="pt-4 mt-6 bg-[#eff4ff] p-3 rounded flex flex-col gap-1 border border-[#dce9ff]">
              <span className="font-['JetBrains_Mono'] text-[10px] text-[#565e74] uppercase font-medium">
                {copy.card1Kept}
              </span>
              <span className="font-['JetBrains_Mono'] text-xs text-[#0b1c30] font-semibold">
                {copy.card1KeptValue}
              </span>
            </div>
          </div>

          {/* Card 2 */}
          <div className="bg-[#ffffff] p-6 rounded-xl border border-[#e2e8f0] shadow-xs flex flex-col justify-between">
            <div className="flex flex-col gap-3">
              <div className="w-11 h-11 rounded bg-[#cce5ff] text-[#006194] flex items-center justify-center">
                <Calculator className="w-6 h-6 text-[#006194]" />
              </div>
              <h3 className="font-['Inter'] text-xl text-[#0b1c30] font-bold">
                {copy.card2Title}
              </h3>
              <p className="font-['Inter'] text-sm text-[#3f4850] leading-relaxed">
                {copy.card2Body}
              </p>
            </div>
            <div className="pt-4 mt-6 bg-[#eff4ff] p-3 rounded flex flex-col gap-1 border border-[#dce9ff]">
              <span className="font-['JetBrains_Mono'] text-[10px] text-[#565e74] uppercase font-medium">
                {copy.card2Cite}
              </span>
              <span className="font-['JetBrains_Mono'] text-xs text-[#0b1c30] font-semibold">
                {copy.card2CiteValue}
              </span>
            </div>
          </div>

          {/* Card 3 */}
          <div className="bg-[#ffffff] p-6 rounded-xl border border-[#e2e8f0] shadow-xs flex flex-col justify-between">
            <div className="flex flex-col gap-3">
              <div className="w-11 h-11 rounded bg-[#dae2fd] text-[#565e74] flex items-center justify-center">
                <Database className="w-6 h-6 text-[#006194]" />
              </div>
              <h3 className="font-['Inter'] text-xl text-[#0b1c30] font-bold">
                {copy.card3Title}
              </h3>
              <p className="font-['Inter'] text-sm text-[#3f4850] leading-relaxed">
                {copy.card3Body}
              </p>
            </div>
            <div className="pt-4 mt-6 bg-[#eff4ff] p-3 rounded flex flex-col gap-1 border border-[#dce9ff]">
              <span className="font-['JetBrains_Mono'] text-[10px] text-[#565e74] uppercase font-medium">
                {copy.card3Export}
              </span>
              <span className="font-['JetBrains_Mono'] text-xs text-[#0b1c30] font-semibold">
                {copy.card3ExportValue}
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Complete 9-Biomarker Scientific Roster Preview Table */}
      <section className="w-full max-w-[1440px] mx-auto px-4 lg:px-8 pb-12">
        <div className="bg-[#ffffff] p-6 rounded-xl border border-[#cbd5e1] shadow-xs flex flex-col gap-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h3 className="font-['Inter'] text-xl font-bold text-[#0b1c30]">
                {copy.matrixTitle}
              </h3>
              <p className="font-['Inter'] text-xs text-[#3f4850]">
                {copy.matrixLead}
              </p>
            </div>
            <span className="font-['JetBrains_Mono'] text-xs bg-[#eff4ff] border border-[#dce9ff] px-2.5 py-1 rounded text-[#0b1c30] font-medium self-start sm:self-auto">
              {copy.matrixActive}
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-['Inter'] text-xs">
              <thead>
                <tr className="bg-[#eff4ff] text-[#565e74] font-['JetBrains_Mono'] text-[11px] uppercase tracking-wider border-b border-[#dce9ff]">
                  <th className="py-2.5 px-3">{copy.colBiomarker}</th>
                  <th className="py-2.5 px-3">{copy.colLoinc}</th>
                  <th className="py-2.5 px-3">{copy.colDomain}</th>
                </tr>
              </thead>
              <tbody className="text-[#0b1c30] divide-y divide-[#f1f5f9]">
                {PHENOAGE_BIOMARKERS.map((bio) => {
                  const label = isBiomarkerId(bio.id) ? m.biomarkers[bio.id] : null;
                  return (
                    <tr key={bio.id} className="hover:bg-[#f8f9ff] transition-colors">
                      <td className="py-3 px-3 font-semibold">{label?.name ?? bio.name}</td>
                      <td className="py-3 px-3 font-['JetBrains_Mono'] text-[#565e74]">{bio.loinc}</td>
                      <td className="py-3 px-3">{label?.domain ?? bio.domain}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Bottom CTA / Activation Strip */}
      <section className="w-full bg-[#006194] py-8 text-[#ffffff]">
        <div className="max-w-[1440px] mx-auto px-4 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex flex-col gap-1 text-center md:text-left">
            <span className="font-['Inter'] text-xl lg:text-2xl font-bold">
              {copy.ctaTitle}
            </span>
            <span className="font-['Inter'] text-xs opacity-90">
              {copy.ctaBody}
            </span>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={() => setActiveTab('upload-lab')}
              className="bg-[#ffffff] text-[#006194] hover:bg-[#eff4ff] font-['Inter'] text-sm px-6 py-3 rounded font-bold transition-colors shadow-sm flex items-center gap-2 cursor-pointer"
              id="btn-bottom-start"
            >
              <span>{copy.ctaUpload}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};
