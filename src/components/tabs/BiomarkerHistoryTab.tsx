import React, { useState, useMemo } from 'react';
import { TabType, HistoricalTestRecord } from '../../types';
import { PHENOAGE_BIOMARKERS } from '../../data/phenoAgeData';
import {
  Calendar,
  TrendingDown,
  Trash2,
  ExternalLink,
  LineChart as LineChartIcon,
  Activity,
  ShieldCheck,
  CheckCircle,
  Sparkles,
  Zap,
  ArrowDownRight,
  TrendingUp,
  FileDown,
  FileText,
  Printer,
} from 'lucide-react';
import { PrintableReportModal } from '../PrintableReportModal';
import { generateHistoricalReportPDF } from '../../utils/pdfReportGenerator';
import { isBiomarkerId } from '../../i18n/biomarkerIds';
import { fill } from '../../i18n/fill';
import { useI18n } from '../../i18n/I18nProvider';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend as RechartsLegend,
  ReferenceLine,
} from 'recharts';

interface BiomarkerHistoryTabProps {
  history: HistoricalTestRecord[];
  onDeleteHistory: (id: string) => void;
  onSelectRecord: (record: HistoricalTestRecord) => void;
  setActiveTab: (tab: TabType) => void;
}

export const BiomarkerHistoryTab: React.FC<BiomarkerHistoryTabProps> = ({
  history,
  onDeleteHistory,
  onSelectRecord,
  setActiveTab,
}) => {
  const { m } = useI18n();
  const copy = m.history;
  const [selectedBiomarker, setSelectedBiomarker] = useState<string>('crp');
  const [chartViewMode, setChartViewMode] = useState<'both' | 'delta'>('both');
  const [showReportModal, setShowReportModal] = useState(false);

  const activeBioDef = PHENOAGE_BIOMARKERS.find((b) => b.id === selectedBiomarker);

  // Recharts data transformation
  const rechartsData = useMemo(() => {
    return history.map((record) => {
      const parts = record.date.split('-');
      const year = parts[0];
      const month = parts[1] || '01';
      const monthNames = copy.months;
      const mIdx = parseInt(month, 10) - 1;
      const formattedDate = `${monthNames[mIdx] || month} ${year}`;

      return {
        id: record.id,
        rawDate: record.date,
        formattedDate,
        chronologicalAge: Number(record.chronologicalAge.toFixed(1)),
        phenoAge: Number(record.phenoAge.toFixed(1)),
        delta: Number(record.delta.toFixed(1)),
        advantage: Number(Math.max(0, -record.delta).toFixed(1)),
        labSource: record.labSource,
        crp: record.biomarkers?.crp ?? 0,
        albumin: record.biomarkers?.albumin ?? 0,
        glucose: record.biomarkers?.glucose ?? 0,
        rdw: record.biomarkers?.rdw ?? 0,
      };
    });
  }, [copy.months, history]);

  // Derived trajectory statistics
  const trajectoryStats = useMemo(() => {
    if (history.length === 0) {
      return {
        initialPheno: 0,
        latestPheno: 0,
        totalDelta: 0,
        netBioChange: 0,
        netChronoChange: 0,
        agingPace: 1,
        avgDelta: 0,
      };
    }
    const earliest = history[0];
    const latest = history[history.length - 1];
    const netBioChange = Number((latest.phenoAge - earliest.phenoAge).toFixed(1));
    const netChronoChange = Number(
      (latest.chronologicalAge - earliest.chronologicalAge).toFixed(1)
    );
    const agingPace =
      netChronoChange > 0 ? Number((netBioChange / netChronoChange).toFixed(2)) : 0.82;
    const avgDelta = Number(
      (history.reduce((acc, h) => acc + h.delta, 0) / history.length).toFixed(1)
    );

    return {
      initialPheno: earliest.phenoAge,
      latestPheno: latest.phenoAge,
      totalDelta: latest.delta,
      netBioChange,
      netChronoChange,
      agingPace,
      avgDelta,
    };
  }, [history]);

  // SVG Chart Dimensions
  const chartWidth = 720;
  const chartHeight = 220;
  const padding = { top: 20, right: 30, bottom: 40, left: 45 };

  // Calculate points for Biological Age vs Chrono Age chart
  const hasHistory = history.length > 0;
  const minAge = hasHistory
    ? Math.min(...history.map((h) => Math.min(h.chronologicalAge, h.phenoAge))) - 1
    : 0;
  const maxAge = hasHistory
    ? Math.max(...history.map((h) => Math.max(h.chronologicalAge, h.phenoAge))) + 1
    : 1;

  const getX = (index: number) => {
    if (history.length <= 1) return padding.left;
    return (
      padding.left +
      (index / (history.length - 1)) * (chartWidth - padding.left - padding.right)
    );
  };

  const getY = (val: number) => {
    const range = maxAge - minAge || 1;
    return (
      chartHeight -
      padding.bottom -
      ((val - minAge) / range) * (chartHeight - padding.top - padding.bottom)
    );
  };

  // Biomarker specific chart calculations
  const bioValues = hasHistory ? history.map((h) => h.biomarkers[selectedBiomarker] ?? 0) : [];
  const minBio = hasHistory ? Math.min(...bioValues) * 0.85 : 0;
  const maxBio = hasHistory ? Math.max(...bioValues) * 1.15 || 1 : 1;
  const getBioY = (val: number) => {
    const range = maxBio - minBio || 1;
    return (
      chartHeight -
      padding.bottom -
      ((val - minBio) / range) * (chartHeight - padding.top - padding.bottom)
    );
  };

  const hasSessionSnapshot = history.some((row) => row.sessionOnly);
  const hasConfirmed = history.some((row) => !row.sessionOnly);

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
            {history.length === 0
              ? copy.emptyLead
              : hasSessionSnapshot
                ? copy.sessionSnapshotLead
                : copy.sessionLead}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setShowReportModal(true)}
            className="flex items-center gap-2 px-3.5 py-2.5 rounded-lg font-['Inter'] text-xs font-semibold bg-[#ffffff] hover:bg-[#f8fafc] text-[#0b1c30] border border-[#cbd5e1] shadow-2xs hover:border-[#94a3b8] transition-all cursor-pointer"
            title={copy.exportTitle}
          >
            <FileDown className="w-4 h-4 text-[#006194]" />
            <span>{copy.export}</span>
          </button>
        </div>
      </div>

      {/* NEW SECTION: Recharts Longitudinal PhenoAge Trend Visualizer */}
      <div className="bg-[#ffffff] p-6 lg:p-7 rounded-xl border border-[#cbd5e1] shadow-xs flex flex-col gap-6">
        {/* Section Header with Controls */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#f1f5f9] pb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-['Inter'] text-base font-bold text-[#0b1c30] flex items-center gap-2">
                <LineChartIcon className="w-5 h-5 text-[#006194]" />
                {copy.chartTitle}
              </span>
              <span className="font-['JetBrains_Mono'] text-[11px] bg-[#eff4ff] text-[#006194] border border-[#dce9ff] px-2 py-0.5 rounded font-semibold">
                {copy.interactive}
              </span>
            </div>
            <p className="font-['Inter'] text-xs text-[#565e74]">
              {copy.chartLead}
            </p>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-1.5 bg-[#eff4ff] p-1 rounded-lg border border-[#dce9ff] shrink-0 self-start md:self-auto">
            <button
              onClick={() => setChartViewMode('both')}
              className={`px-3 py-1.5 rounded text-xs font-['Inter'] font-semibold transition-all cursor-pointer ${
                chartViewMode === 'both'
                  ? 'bg-[#006194] text-white shadow-xs'
                  : 'text-[#3f4850] hover:text-[#0b1c30]'
              }`}
            >
              {copy.vsChrono}
            </button>
            <button
              onClick={() => setChartViewMode('delta')}
              className={`px-3 py-1.5 rounded text-xs font-['Inter'] font-semibold transition-all cursor-pointer ${
                chartViewMode === 'delta'
                  ? 'bg-[#006194] text-white shadow-xs'
                  : 'text-[#3f4850] hover:text-[#0b1c30]'
              }`}
            >
              {copy.variance}
            </button>
          </div>
        </div>

        {/* Analytical KPI Cards Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
          <div className="p-3.5 bg-[#f8f9ff] rounded-lg border border-[#e2e8f0] flex flex-col justify-between">
            <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74]">{copy.latestPheno}</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="font-['Inter'] text-2xl font-bold text-[#006947]">
                {history.length === 0 ? '—' : trajectoryStats.latestPheno.toFixed(1)}
              </span>
              <span className="text-[11px] text-[#565e74]">{m.shell.yrs}</span>
            </div>
            <span className="font-['JetBrains_Mono'] text-[10px] text-[#565e74] font-semibold mt-1">
              {history.length === 0
                ? copy.noPanels
                : trajectoryStats.totalDelta <= 0
                  ? copy.deceleratedProfile
                  : copy.accelerated}
            </span>
          </div>

          <div className="p-3.5 bg-[#f8f9ff] rounded-lg border border-[#e2e8f0] flex flex-col justify-between">
            <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74]">{copy.pace}</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="font-['Inter'] text-2xl font-bold text-[#006194]">
                {history.length === 0 ? '—' : trajectoryStats.agingPace}
              </span>
              <span className="text-[11px] text-[#565e74]">{copy.paceUnit}</span>
            </div>
            <span className="font-['JetBrains_Mono'] text-[10px] text-[#565e74] font-semibold mt-1">
              {history.length === 0
                ? copy.noPanels
                : trajectoryStats.agingPace < 1.0
                  ? copy.slowed
                  : copy.baselinePace}
            </span>
          </div>

          <div className="p-3.5 bg-[#f8f9ff] rounded-lg border border-[#e2e8f0] flex flex-col justify-between">
            <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74]">{copy.avgAdvantage}</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="font-['Inter'] text-2xl font-bold text-[#006947]">
                {history.length === 0 ? '—' : Math.abs(trajectoryStats.avgDelta).toFixed(1)}
              </span>
              <span className="text-[11px] text-[#565e74]">
                {history.length === 0 ? m.shell.years : copy.yearsYounger}
              </span>
            </div>
            <span className="font-['JetBrains_Mono'] text-[10px] text-[#565e74] mt-1">
              {history.length === 0
                ? copy.noPanels
                : fill(copy.acrossPoints, { count: history.length })}
            </span>
          </div>

          <div className="p-3.5 bg-[#f8f9ff] rounded-lg border border-[#e2e8f0] flex flex-col justify-between">
            <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74]">{copy.netChange}</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span
                className={`font-['Inter'] text-2xl font-bold ${
                  trajectoryStats.netBioChange <= 0 ? 'text-[#006947]' : 'text-[#ba1a1a]'
                }`}
              >
                {history.length === 0
                  ? '—'
                  : trajectoryStats.netBioChange > 0
                    ? `+${trajectoryStats.netBioChange}`
                    : trajectoryStats.netBioChange}
              </span>
              <span className="text-[11px] text-[#565e74]">{copy.yrsNet}</span>
            </div>
            <span className="font-['JetBrains_Mono'] text-[10px] text-[#565e74] mt-1">
              {history.length === 0 ? copy.noPanels : copy.fromBaseline}
            </span>
          </div>
        </div>

        {/* Recharts Canvas Container */}
        <div className="w-full h-80 min-w-0">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={rechartsData}
              margin={{ top: 15, right: 30, left: 10, bottom: 10 }}
            >
              <defs>
                <linearGradient id="phenoFillGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00855b" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#00855b" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="deltaFillGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#006194" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#006194" stopOpacity={0.02} />
                </linearGradient>
              </defs>

              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />

              <XAxis
                dataKey="formattedDate"
                tick={{ fill: '#565e74', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                tickLine={{ stroke: '#cbd5e1' }}
                axisLine={{ stroke: '#cbd5e1' }}
              />

              <YAxis
                domain={['auto', 'auto']}
                tick={{ fill: '#565e74', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                tickLine={{ stroke: '#cbd5e1' }}
                axisLine={{ stroke: '#cbd5e1' }}
                unit="y"
              />

              <RechartsTooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    const isDecelerated = data.delta <= 0;
                    return (
                      <div className="bg-[#ffffff] border border-[#cbd5e1] rounded-xl shadow-xl p-4 text-xs font-['Inter'] min-w-[230px]">
                        <div className="flex items-center justify-between border-b border-[#e2e8f0] pb-2 mb-2 font-['JetBrains_Mono']">
                          <span className="font-bold text-[#0b1c30]">{data.rawDate}</span>
                          <span className="text-[10px] bg-[#eff4ff] text-[#006194] px-2 py-0.5 rounded font-semibold border border-[#dce9ff]">
                            {data.labSource}
                          </span>
                        </div>
                        <div className="space-y-1.5 font-['JetBrains_Mono']">
                          <div className="flex justify-between items-center text-[#565e74]">
                            <span>{copy.chronoAge}</span>
                            <span className="font-bold text-[#0b1c30]">
                              {data.chronologicalAge.toFixed(1)} yrs
                            </span>
                          </div>
                          <div className="flex justify-between items-center text-[#006947]">
                            <span className="font-bold">{copy.biologicalPheno}</span>
                            <span className="font-extrabold text-[#006947] text-sm">
                              {data.phenoAge.toFixed(1)} yrs
                            </span>
                          </div>
                          <div className="flex justify-between items-center pt-1.5 border-t border-[#f1f5f9]">
                            <span className="text-[#565e74]">{copy.agingVariance}</span>
                            <span
                              className={`font-bold px-2 py-0.5 rounded text-[11px] ${
                                isDecelerated
                                  ? 'bg-[#4edea3]/25 text-[#006947]'
                                  : 'bg-[#ffdad6] text-[#ba1a1a]'
                              }`}
                            >
                              {data.delta > 0
                                ? `+${data.delta.toFixed(1)}`
                                : `${data.delta.toFixed(1)}`}{' '}
                              yrs
                            </span>
                          </div>
                          <div className="pt-2 mt-1 border-t border-[#f1f5f9] text-[10px] text-[#565e74] flex justify-between">
                            <span>{fill(copy.hsCrp, { value: data.crp })}</span>
                            <span>{fill(copy.alb, { value: data.albumin })}</span>
                            <span>{fill(copy.rdw, { value: data.rdw })}</span>
                          </div>
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />

              <RechartsLegend
                wrapperStyle={{
                  paddingTop: '12px',
                  fontFamily: 'Inter',
                  fontSize: '12px',
                }}
              />

              {chartViewMode === 'both' ? (
                <>
                  <Area
                    type="monotone"
                    dataKey="phenoAge"
                    fill="url(#phenoFillGradient)"
                    stroke="none"
                    name={copy.youthZone}
                  />
                  <Line
                    type="monotone"
                    dataKey="chronologicalAge"
                    stroke="#94a3b8"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={{ r: 4, fill: '#64748b' }}
                    name={copy.calendarAge}
                  />
                  <Line
                    type="monotone"
                    dataKey="phenoAge"
                    stroke="#00855b"
                    strokeWidth={3.5}
                    dot={{ r: 5, fill: '#00855b', stroke: '#ffffff', strokeWidth: 2 }}
                    activeDot={{ r: 7, fill: '#00855b', stroke: '#ffffff', strokeWidth: 3 }}
                    name={copy.phenoSeries}
                  />
                </>
              ) : (
                <>
                  <ReferenceLine
                    y={0}
                    stroke="#94a3b8"
                    strokeDasharray="4 4"
                    label={{
                      value: copy.zeroDelta,
                      fill: '#64748b',
                      fontSize: 11,
                      position: 'top',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="delta"
                    fill="url(#deltaFillGradient)"
                    stroke="none"
                    name={copy.varianceArea}
                  />
                  <Line
                    type="monotone"
                    dataKey="delta"
                    stroke="#006194"
                    strokeWidth={3}
                    dot={{ r: 5, fill: '#006194', stroke: '#ffffff', strokeWidth: 2 }}
                    activeDot={{ r: 7, fill: '#006194', stroke: '#ffffff', strokeWidth: 3 }}
                    name={copy.varianceSeries}
                  />
                </>
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* Scientific Context Footer in Section */}
        <div className="p-3.5 bg-[#eff4ff] rounded-lg border border-[#dce9ff] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs text-[#3f4850]">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-[#006194] shrink-0" />
            <span>
              <strong>{copy.trajectory}</strong>
            </span>
          </div>
          <span className="font-['JetBrains_Mono'] text-[11px] text-[#006194] font-semibold shrink-0">
            {copy.pValue}
          </span>
        </div>
      </div>

      {/* Dual Charts: PhenoAge Divergence Chart + Biomarker Specific Track */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Main Chart: Biological vs Chronological Trajectory */}
        <div className="lg:col-span-7 bg-[#ffffff] p-6 rounded-xl border border-[#cbd5e1] shadow-xs flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div>
              <span className="font-['Inter'] text-sm font-bold text-[#0b1c30] block">
                {copy.vectorTitle}
              </span>
              <span className="font-['Inter'] text-xs text-[#565e74]">
                {copy.vectorLead}
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs font-['JetBrains_Mono']">
              <span className="flex items-center gap-1.5 text-[#0b1c30]">
                <span className="w-3 h-0.5 bg-[#565e74] inline-block"></span> {copy.chronoLegend}
              </span>
              <span className="flex items-center gap-1.5 text-[#006947] font-bold">
                <span className="w-3 h-0.5 bg-[#006947] inline-block"></span> {copy.phenoLegend}
              </span>
            </div>
          </div>

          {/* SVG Chart Container */}
          <div className="w-full overflow-x-auto">
            {hasHistory ? (
            <svg
              viewBox={`0 0 ${chartWidth} ${chartHeight}`}
              className="w-full h-auto min-w-[500px]"
            >
              {/* Grid lines */}
              {[minAge, (minAge + maxAge) / 2, maxAge].map((tick, i) => {
                const y = getY(tick);
                return (
                  <g key={i}>
                    <line
                      x1={padding.left}
                      y1={y}
                      x2={chartWidth - padding.right}
                      y2={y}
                      stroke="#e2e8f0"
                      strokeDasharray="4 4"
                    />
                    <text
                      x={padding.left - 8}
                      y={y + 4}
                      textAnchor="end"
                      fontSize="10"
                      fill="#94a3b8"
                      fontFamily="JetBrains Mono"
                    >
                      {tick.toFixed(0)}y
                    </text>
                  </g>
                );
              })}

              {/* Chronological Age Line (Dashed) */}
              <polyline
                fill="none"
                stroke="#94a3b8"
                strokeWidth="2"
                strokeDasharray="5 5"
                points={history.map((h, i) => `${getX(i)},${getY(h.chronologicalAge)}`).join(' ')}
              />

              {/* Biological PhenoAge Line (Solid Green) */}
              <polyline
                fill="none"
                stroke="#006947"
                strokeWidth="3.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={history.map((h, i) => `${getX(i)},${getY(h.phenoAge)}`).join(' ')}
              />

              {/* Points and Labels */}
              {history.map((h, i) => {
                const cx = getX(i);
                const cyBio = getY(h.phenoAge);
                const cyChrono = getY(h.chronologicalAge);
                return (
                  <g key={h.id}>
                    {/* Date label */}
                    <text
                      x={cx}
                      y={chartHeight - 12}
                      textAnchor="middle"
                      fontSize="10"
                      fill="#565e74"
                      fontFamily="JetBrains Mono"
                    >
                      {h.date.slice(0, 7)}
                    </text>

                    {/* Chrono dot */}
                    <circle cx={cx} cy={cyChrono} r="4" fill="#565e74" />

                    {/* Bio dot */}
                    <circle cx={cx} cy={cyBio} r="6" fill="#006947" stroke="#ffffff" strokeWidth="2" />

                    {/* Delta label above dot */}
                    <text
                      x={cx}
                      y={cyBio - 10}
                      textAnchor="middle"
                      fontSize="10"
                      fontWeight="bold"
                      fill="#006947"
                      fontFamily="JetBrains Mono"
                    >
                      {h.delta}y
                    </text>
                  </g>
                );
              })}
            </svg>
            ) : (
              <p className="font-['Inter'] text-sm text-[#565e74] py-8">{copy.noPanels}</p>
            )}
          </div>
        </div>

        {/* Individual Biomarker Trend Track */}
        <div className="lg:col-span-5 bg-[#ffffff] p-6 rounded-xl border border-[#cbd5e1] shadow-xs flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <span className="font-['Inter'] text-sm font-bold text-[#0b1c30]">
              {copy.markerTrack}
            </span>
            <select
              value={selectedBiomarker}
              onChange={(e) => setSelectedBiomarker(e.target.value)}
              className="px-2.5 py-1 bg-[#eff4ff] border border-[#cbd5e1] rounded text-xs font-['JetBrains_Mono'] text-[#0b1c30] focus:outline-none cursor-pointer"
            >
              {PHENOAGE_BIOMARKERS.map((b) => (
                <option key={b.id} value={b.id}>
                  {isBiomarkerId(b.id) ? m.biomarkers[b.id].name : b.name} ({b.unit})
                </option>
              ))}
            </select>
          </div>

          {activeBioDef && (
            <div className="text-xs text-[#565e74] flex justify-between bg-[#f8f9ff] p-2.5 rounded border border-[#e2e8f0] font-['JetBrains_Mono']">
              <span>{fill(copy.loinc, { code: activeBioDef.loinc })}</span>
              <span className="text-[#006947] font-semibold">
                {fill(copy.targetRange, {
                  min: activeBioDef.optimalRange[0],
                  max: activeBioDef.optimalRange[1],
                  unit: activeBioDef.unit,
                })}
              </span>
            </div>
          )}

          {/* SVG for Specific Biomarker */}
          <div className="w-full">
            {hasHistory ? (
            <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="w-full h-auto">
              {/* Line */}
              <polyline
                fill="none"
                stroke="#006194"
                strokeWidth="3"
                points={history
                  .map((h, i) => `${getX(i)},${getBioY(h.biomarkers[selectedBiomarker] ?? 0)}`)
                  .join(' ')}
              />
              {/* Nodes */}
              {history.map((h, i) => {
                const val = h.biomarkers[selectedBiomarker] ?? 0;
                const cx = getX(i);
                const cy = getBioY(val);
                return (
                  <g key={h.id}>
                    <circle cx={cx} cy={cy} r="5" fill="#006194" stroke="#ffffff" strokeWidth="2" />
                    <text
                      x={cx}
                      y={cy - 10}
                      textAnchor="middle"
                      fontSize="10"
                      fontWeight="bold"
                      fill="#006194"
                      fontFamily="JetBrains Mono"
                    >
                      {val.toFixed(1)}
                    </text>
                    <text
                      x={cx}
                      y={chartHeight - 12}
                      textAnchor="middle"
                      fontSize="10"
                      fill="#565e74"
                      fontFamily="JetBrains Mono"
                    >
                      {h.date.slice(0, 7)}
                    </text>
                  </g>
                );
              })}
            </svg>
            ) : (
              <p className="font-['Inter'] text-sm text-[#565e74] py-8">{copy.noPanels}</p>
            )}
          </div>
        </div>
      </div>

      {/* Historical Records Table */}
      <div className="bg-[#ffffff] rounded-xl border border-[#cbd5e1] shadow-xs overflow-hidden">
        <div className="px-5 py-4 bg-[#eff4ff] border-b border-[#dce9ff] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-['Inter'] text-sm font-bold text-[#0b1c30]">
              {fill(copy.registry, { count: history.length })}
            </span>
            {hasConfirmed && (
              <span className="font-['JetBrains_Mono'] text-xs text-[#006947] font-semibold bg-[#e6f4ea] px-2 py-0.5 rounded border border-[#b7e1cd]">
                {copy.confirmedBadge}
              </span>
            )}
            {hasSessionSnapshot && (
              <span className="font-['JetBrains_Mono'] text-xs text-[#004b73] font-semibold bg-[#cce5ff] px-2 py-0.5 rounded border border-[#dce9ff]">
                {copy.sessionOnly}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowReportModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#ffffff] hover:bg-[#f8fafc] text-[#006194] border border-[#cbd5e1] text-xs font-semibold transition-colors cursor-pointer shadow-2xs"
            >
              <FileDown className="w-3.5 h-3.5" />
              <span>{copy.printable}</span>
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-['Inter'] text-xs">
            <thead>
              <tr className="bg-[#f8f9ff] text-[#565e74] font-['JetBrains_Mono'] text-[11px] uppercase tracking-wider border-b border-[#e2e8f0]">
                <th className="py-3 px-4">{copy.colDate}</th>
                <th className="py-3 px-3">{copy.colLab}</th>
                <th className="py-3 px-3">{copy.colChrono}</th>
                <th className="py-3 px-3">{copy.colPheno}</th>
                <th className="py-3 px-3">{copy.colVariance}</th>
                <th className="py-3 px-4 text-right">{copy.colActions}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f1f5f9]">
              {history.map((record) => (
                <tr key={record.id} className="hover:bg-[#f8f9ff] transition-colors">
                  <td className="py-3.5 px-4 font-bold text-[#0b1c30] flex items-center gap-2">
                    <Calendar className="w-3.5 h-3.5 text-[#006194]" />
                    <span>{record.date}</span>
                  </td>
                  <td className="py-3.5 px-3 text-[#3f4850]">
                    <div className="flex flex-col gap-1">
                      <span>{record.labSource}</span>
                      {record.sessionOnly && (
                        <span className="font-['JetBrains_Mono'] text-[10px] text-[#004b73] font-semibold">
                          {copy.sessionOnly}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-3.5 px-3 font-['JetBrains_Mono'] text-[#565e74]">
                    {record.chronologicalAge.toFixed(1)}y
                  </td>
                  <td className="py-3.5 px-3 font-['JetBrains_Mono'] font-bold text-[#006194]">
                    {record.phenoAge.toFixed(1)}y
                  </td>
                  <td className="py-3.5 px-3">
                    <span
                      className={`font-['JetBrains_Mono'] text-xs font-bold px-2 py-0.5 rounded ${
                        record.delta <= 0
                          ? 'bg-[#4edea3]/25 text-[#006947]'
                          : 'bg-[#ffdad6] text-[#ba1a1a]'
                      }`}
                    >
                      {record.delta > 0 ? `+${record.delta}` : record.delta} yrs
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => {
                          onSelectRecord(record);
                          setActiveTab('phenoage-engine');
                        }}
                        className="px-2.5 py-1 rounded bg-[#eff4ff] hover:bg-[#e5eeff] text-[#006194] font-semibold text-[11px] transition-colors cursor-pointer"
                      >
                        {copy.loadEngine}
                      </button>
                      {(record.sessionOnly || history.length > 1) && (
                        <button
                          onClick={() => onDeleteHistory(record.id)}
                          className="p-1 rounded text-[#ba1a1a] hover:bg-[#fff1f2] transition-colors cursor-pointer"
                          title={copy.deleteEntry}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Printable Clinical PDF Report Modal */}
      <PrintableReportModal
        isOpen={showReportModal}
        onClose={() => setShowReportModal(false)}
        history={history}
      />
    </div>
  );
};
