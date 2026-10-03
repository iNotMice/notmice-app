import React, { useEffect, useMemo, useState } from 'react';
import { TabType, HistoricalTestRecord, PrintedLabInterval } from '../../types';
import { PHENOAGE_BIOMARKERS } from '../../data/phenoAgeData';
import { Calendar, Trash2, LineChart as LineChartIcon, FileDown } from 'lucide-react';
import { PrintableReportModal } from '../PrintableReportModal';
import { listProtocolEntries, type ProtocolEntry } from '../../api/protocol';
import { isBiomarkerId } from '../../i18n/biomarkerIds';
import { fill } from '../../i18n/fill';
import { useI18n } from '../../i18n/I18nProvider';
import {
  dayMs,
  fractionOnAxis,
  layoutPeriodBands,
  localIsoDate,
  periodDrawEnd,
} from '../../utils/protocolBands';
import { missingMarkerText, scoredRecords } from '../../utils/phenoTrend';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend as RechartsLegend,
} from 'recharts';

function formatBound(value: number): string {
  return value.toFixed(3).replace(/\.?0+$/, '');
}

function printedSpan(interval: PrintedLabInterval | null): {
  low: number | null;
  high: number | null;
} {
  if (!interval) {
    return { low: null, high: null };
  }
  const low = interval.referenceLow;
  const high = interval.referenceHigh;
  if (low != null && high != null && low > high) {
    return { low: null, high: null };
  }
  return { low, high };
}

function signedYears(value: number): string {
  const text = value.toFixed(1);
  return value > 0 ? `+${text}` : text;
}

interface BiomarkerHistoryTabProps {
  history: HistoricalTestRecord[];
  isAuthenticated: boolean;
  onDeleteHistory: (id: string) => void | Promise<void>;
  onSelectRecord: (record: HistoricalTestRecord) => void;
  setActiveTab: (tab: TabType) => void;
}

export const BiomarkerHistoryTab: React.FC<BiomarkerHistoryTabProps> = ({
  history,
  isAuthenticated,
  onDeleteHistory,
  onSelectRecord,
  setActiveTab,
}) => {
  const { m } = useI18n();
  const copy = m.history;
  const [selectedBiomarker, setSelectedBiomarker] = useState<string>('crp');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [selectedLab, setSelectedLab] = useState('');
  const [showReportModal, setShowReportModal] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [journalEntries, setJournalEntries] = useState<ProtocolEntry[]>([]);

  useEffect(() => {
    if (!isAuthenticated) {
      setJournalEntries([]);
      return;
    }
    let cancelled = false;
    void listProtocolEntries()
      .then((rows) => {
        if (!cancelled) {
          setJournalEntries(rows);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setJournalEntries([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  const removeUpload = (id: string) => {
    setDeleteError(null);
    void Promise.resolve(onDeleteHistory(id)).catch((err: unknown) => {
      setDeleteError(err instanceof Error ? err.message : copy.deleteFailed);
    });
  };

  const laboratoryOptions = useMemo(
    () => Array.from(new Set(history.map((record) => record.labSource))).sort((a, b) => a.localeCompare(b)),
    [history],
  );
  const filteredHistory = useMemo(
    () =>
      history
        .filter((record) => {
          const date = (record.collectedAt ?? record.date).slice(0, 10);
          return (
            (!dateFrom || date >= dateFrom) &&
            (!dateTo || date <= dateTo) &&
            (!selectedLab || record.labSource === selectedLab)
          );
        })
        .sort((left, right) =>
          (left.collectedAt ?? left.date).localeCompare(right.collectedAt ?? right.date),
        ),
    [dateFrom, dateTo, history, selectedLab],
  );
  const activeBioDef = PHENOAGE_BIOMARKERS.find((b) => b.id === selectedBiomarker);
  const scored = scoredRecords(filteredHistory);
  const latestScored = scored.length > 0 ? scored[scored.length - 1] : null;
  const unscored = filteredHistory.filter((record) => record.phenoAge === null);
  const trendRows = scored.map((record) => {
    const parts = record.date.split('-');
    const year = parts[0];
    const month = parts[1] || '01';
    const monthIndex = parseInt(month, 10) - 1;
    const chronologicalAge = record.chronologicalAge ?? 0;
    const phenoAge = record.phenoAge ?? 0;
    return {
      id: record.id,
      rawDate: record.collectedAt ?? record.date,
      formattedDate: `${copy.months[monthIndex] || month} ${year}`,
      chronologicalAge: Number(chronologicalAge.toFixed(1)),
      phenoAge: Number(phenoAge.toFixed(1)),
      delta: Number(((record.delta ?? phenoAge - chronologicalAge)).toFixed(1)),
      labSource: record.labSource,
    };
  });

  const chartWidth = 720;
  const padding = { top: 20, right: 30, bottom: 40, left: 45 };

  const markerPoints = filteredHistory.flatMap((record) => {
    const measuredIds =
      record.sessionOnly && record.markerIds.length === 0
        ? Object.keys(record.biomarkers)
        : record.markerIds;
    if (!measuredIds.includes(selectedBiomarker)) {
      return [];
    }
    const value = record.biomarkers[selectedBiomarker];
    if (value === undefined || Number.isNaN(value)) {
      return [];
    }
    return [
      {
        record,
        value,
        interval: record.printedIntervals[selectedBiomarker] ?? null,
      },
    ];
  });
  const scaleNumbers = markerPoints.flatMap((point) => {
    const span = printedSpan(point.interval);
    const nums = [point.value];
    if (span.low != null) nums.push(span.low);
    if (span.high != null) nums.push(span.high);
    return nums;
  });
  const periodLayout = layoutPeriodBands(
    markerPoints.map((point) => point.record.collectedAt ?? point.record.date),
    journalEntries.map((entry) => ({
      id: entry.id,
      title: entry.title,
      startedOn: entry.startedOn,
      endedOn: entry.endedOn,
    })),
    localIsoDate(),
  );
  const laneCount = periodLayout.periods.reduce((max, band) => Math.max(max, band.lane + 1), 0);
  const laneHeight = 18;
  const laneGap = 6;
  const plotWidth = chartWidth - padding.left - padding.right;
  const plotTop = padding.top;
  const plotBottom = plotTop + 160;
  const laneBlock = laneCount === 0 ? 0 : laneCount * laneHeight + (laneCount - 1) * laneGap;
  const dateLabelY = laneCount === 0 ? plotBottom + 28 : plotBottom + 8 + laneBlock + 16;
  const svgHeight = laneCount === 0 ? 220 : dateLabelY + 12;
  const useDateAxis = periodLayout.periods.length > 0;
  const minRaw = scaleNumbers.length > 0 ? Math.min(...scaleNumbers) : 0;
  const maxRaw = scaleNumbers.length > 0 ? Math.max(...scaleNumbers) : 1;
  const axisSpan = maxRaw - minRaw || Math.abs(maxRaw) || 1;
  const minBio = minRaw - axisSpan * 0.12;
  const maxBio = maxRaw + axisSpan * 0.12;
  const getBioY = (val: number) => {
    const range = maxBio - minBio || 1;
    return plotBottom - ((val - minBio) / range) * (plotBottom - plotTop);
  };
  const getMarkerX = (index: number) => {
    if (useDateAxis) {
      const ms = dayMs(markerPoints[index].record.collectedAt ?? markerPoints[index].record.date);
      if (ms == null) {
        return padding.left;
      }
      return padding.left + fractionOnAxis(ms, periodLayout.axis) * plotWidth;
    }
    if (markerPoints.length <= 1) return padding.left;
    return padding.left + (index / (markerPoints.length - 1)) * plotWidth;
  };
  const intervalLabel = (interval: PrintedLabInterval | null): string | null => {
    const bounds = printedSpan(interval);
    const unit = activeBioDef?.unit ?? '';
    if (bounds.low != null && bounds.high != null) {
      return fill(copy.intervalClosed, {
        min: formatBound(bounds.low),
        max: formatBound(bounds.high),
        unit,
      });
    }
    if (bounds.high != null) {
      return fill(copy.intervalUpper, { max: formatBound(bounds.high), unit });
    }
    if (bounds.low != null) {
      return fill(copy.intervalLower, { min: formatBound(bounds.low), unit });
    }
    return null;
  };
  const bandRect = (interval: PrintedLabInterval | null, cx: number) => {
    const bounds = printedSpan(interval);
    if (bounds.low == null && bounds.high == null) {
      return null;
    }
    const width = 22;
    const x = cx - width / 2;
    if (bounds.low != null && bounds.high != null) {
      const y = getBioY(bounds.high);
      return { x, y, width, height: Math.max(getBioY(bounds.low) - y, 1) };
    }
    if (bounds.high != null) {
      const y = getBioY(bounds.high);
      return { x, y, width, height: Math.max(plotBottom - y, 1) };
    }
    const y = plotTop;
    return { x, y, width, height: Math.max(getBioY(bounds.low ?? minBio) - y, 1) };
  };

  const hasSessionSnapshot = filteredHistory.some((row) => row.sessionOnly);
  const hasConfirmed = filteredHistory.some((row) => !row.sessionOnly);
  const hasHistory = filteredHistory.length > 0;
  const hasActiveFilters = Boolean(dateFrom || dateTo || selectedLab);

  const panelWhen = (record: HistoricalTestRecord): string =>
    record.sessionOnly ? record.date : (record.collectedAt ?? copy.dateMissing);

  const openRecord = (record: HistoricalTestRecord) => {
    onSelectRecord(record);
    setActiveTab('phenoage-engine');
  };

  const panelNote = (record: HistoricalTestRecord): string => {
    const date = panelWhen(record);
    const lab = record.labSource;
    if (record.missingMarkers.length > 0) {
      return fill(copy.missingLine, {
        date,
        lab,
        markers: missingMarkerText(record, m.biomarkers),
      });
    }
    if (record.chronologicalAge === null) {
      return fill(copy.ageMissingLine, { date, lab });
    }
    return fill(copy.notScoredLine, { date, lab });
  };

  return (
    <div className="w-full max-w-[1440px] mx-auto px-4 lg:px-8 py-8 flex flex-col gap-8">
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
            disabled={history.length === 0}
            className="flex items-center gap-2 px-3.5 py-2.5 rounded-lg font-['Inter'] text-xs font-semibold bg-[#ffffff] hover:bg-[#f8fafc] text-[#0b1c30] border border-[#cbd5e1] shadow-2xs hover:border-[#94a3b8] transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            title={copy.exportTitle}
          >
            <FileDown className="w-4 h-4 text-[#006194]" />
            <span>{copy.export}</span>
          </button>
        </div>
      </div>

      <div className="bg-[#ffffff] p-4 lg:p-5 rounded-xl border border-[#cbd5e1] shadow-xs">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <label className="flex flex-col gap-1 font-['Inter'] text-xs font-semibold text-[#3f4850]">
            {copy.filterFrom}
            <input
              type="date"
              value={dateFrom}
              max={dateTo || undefined}
              onChange={(event) => setDateFrom(event.target.value)}
              className="min-h-10 rounded-lg border border-[#cbd5e1] px-3 font-normal text-[#0b1c30] focus:outline-none focus:ring-2 focus:ring-[#006194]/30"
            />
          </label>
          <label className="flex flex-col gap-1 font-['Inter'] text-xs font-semibold text-[#3f4850]">
            {copy.filterTo}
            <input
              type="date"
              value={dateTo}
              min={dateFrom || undefined}
              onChange={(event) => setDateTo(event.target.value)}
              className="min-h-10 rounded-lg border border-[#cbd5e1] px-3 font-normal text-[#0b1c30] focus:outline-none focus:ring-2 focus:ring-[#006194]/30"
            />
          </label>
          <label className="flex flex-col gap-1 font-['Inter'] text-xs font-semibold text-[#3f4850]">
            {copy.filterLab}
            <select
              value={selectedLab}
              onChange={(event) => setSelectedLab(event.target.value)}
              className="min-h-10 rounded-lg border border-[#cbd5e1] px-3 font-normal text-[#0b1c30] focus:outline-none focus:ring-2 focus:ring-[#006194]/30"
            >
              <option value="">{copy.allLabs}</option>
              {laboratoryOptions.map((lab) => (
                <option key={lab} value={lab}>
                  {lab}
                </option>
              ))}
            </select>
          </label>
        </div>
        {hasActiveFilters && (
          <button
            type="button"
            onClick={() => {
              setDateFrom('');
              setDateTo('');
              setSelectedLab('');
            }}
            className="mt-3 text-xs font-semibold text-[#006194] hover:underline cursor-pointer"
          >
            {copy.clearFilters}
          </button>
        )}
      </div>

      <div className="bg-[#ffffff] p-6 lg:p-7 rounded-xl border border-[#cbd5e1] shadow-xs flex flex-col gap-6">
        <div className="border-b border-[#f1f5f9] pb-4">
          <span className="font-['Inter'] text-base font-bold text-[#0b1c30] flex items-center gap-2">
            <LineChartIcon className="w-5 h-5 text-[#006194]" />
            {copy.chartTitle}
          </span>
          <p className="font-['Inter'] text-xs text-[#565e74] mt-1 max-w-3xl">
            {copy.chartLead}
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
          <div className="p-3.5 bg-[#f8f9ff] rounded-lg border border-[#e2e8f0]">
            <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74]">{copy.latestIndex}</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="font-['Inter'] text-2xl font-bold text-[#0b1c30]">
                {latestScored?.phenoAge == null ? '—' : latestScored.phenoAge.toFixed(1)}
              </span>
              <span className="text-[11px] text-[#565e74]">{m.shell.yrs}</span>
            </div>
            <span className="font-['JetBrains_Mono'] text-[10px] text-[#565e74] mt-1 block">
              {latestScored?.chronologicalAge == null
                ? copy.noPanels
                : `${copy.calendarAge}: ${latestScored.chronologicalAge.toFixed(1)}`}
            </span>
          </div>
          <div className="p-3.5 bg-[#f8f9ff] rounded-lg border border-[#e2e8f0]">
            <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74]">{copy.scoredCount}</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="font-['Inter'] text-2xl font-bold text-[#006194]">{scored.length}</span>
              <span className="text-[11px] text-[#565e74]">{copy.panelsUnit}</span>
            </div>
          </div>
          <div className="p-3.5 bg-[#f8f9ff] rounded-lg border border-[#e2e8f0]">
            <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74]">{copy.notOnTrend}</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="font-['Inter'] text-2xl font-bold text-[#0b1c30]">{unscored.length}</span>
              <span className="text-[11px] text-[#565e74]">{copy.panelsUnit}</span>
            </div>
          </div>
        </div>

        <div className="w-full h-80 min-w-0">
          {trendRows.length === 0 ? (
            <p className="font-['Inter'] text-sm text-[#565e74] py-8">{copy.noScored}</p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendRows} margin={{ top: 15, right: 30, left: 10, bottom: 10 }}>
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
                />
                <RechartsTooltip
                  content={({ active, payload }) => {
                    if (!active || !payload || payload.length === 0) {
                      return null;
                    }
                    const data = payload[0].payload as (typeof trendRows)[number];
                    return (
                      <div className="bg-[#ffffff] border border-[#cbd5e1] rounded-xl shadow-xl p-4 text-xs font-['Inter'] min-w-[220px]">
                        <div className="flex items-center justify-between border-b border-[#e2e8f0] pb-2 mb-2 font-['JetBrains_Mono']">
                          <span className="font-bold text-[#0b1c30]">{data.rawDate}</span>
                          <span className="text-[10px] bg-[#eff4ff] text-[#006194] px-2 py-0.5 rounded font-semibold border border-[#dce9ff]">
                            {data.labSource}
                          </span>
                        </div>
                        <div className="space-y-1.5 font-['JetBrains_Mono'] text-[#3f4850]">
                          <div className="flex justify-between gap-4">
                            <span>{copy.calendarAge}</span>
                            <span className="font-bold text-[#0b1c30]">{data.chronologicalAge.toFixed(1)}</span>
                          </div>
                          <div className="flex justify-between gap-4">
                            <span>{copy.phenoSeries}</span>
                            <span className="font-bold text-[#0b1c30]">{data.phenoAge.toFixed(1)}</span>
                          </div>
                          <div className="flex justify-between gap-4 pt-1.5 border-t border-[#f1f5f9]">
                            <span>{copy.indexMinusAge}</span>
                            <span className="font-bold text-[#0b1c30]">{signedYears(data.delta)}</span>
                          </div>
                        </div>
                      </div>
                    );
                  }}
                />
                <RechartsLegend wrapperStyle={{ paddingTop: '12px', fontFamily: 'Inter', fontSize: '12px' }} />
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
                  stroke="#006194"
                  strokeWidth={3}
                  dot={{ r: 5, fill: '#006194', stroke: '#ffffff', strokeWidth: 2 }}
                  activeDot={{ r: 7, fill: '#006194', stroke: '#ffffff', strokeWidth: 3 }}
                  name={copy.phenoSeries}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        <p className="font-['Inter'] text-xs text-[#3f4850] bg-[#f8f9ff] border border-[#e2e8f0] rounded-lg px-3.5 py-3">
          {m.shell.disclaimer}
        </p>

        {unscored.length > 0 && (
          <div>
            <p className="font-['Inter'] text-sm font-bold text-[#0b1c30] mb-2">{copy.missingTitle}</p>
            <ul className="flex flex-col gap-1.5">
              {unscored.map((record) => (
                <li key={record.id} className="font-['Inter'] text-xs text-[#3f4850]">
                  {panelNote(record)}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="bg-[#ffffff] p-6 rounded-xl border border-[#cbd5e1] shadow-xs flex flex-col gap-4">
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
          <div className="text-xs text-[#565e74] flex justify-between items-center gap-3 bg-[#f8f9ff] p-2.5 rounded border border-[#e2e8f0] font-['JetBrains_Mono']">
            <span>{fill(copy.loinc, { code: activeBioDef.loinc })}</span>
            <span className="inline-flex flex-wrap items-center gap-x-3 gap-y-1 text-[#3f4850]">
              <span className="inline-flex items-center gap-1.5">
                <span
                  className="inline-block w-3 h-3 rounded-sm bg-[#e7eef6] border border-[#94a3b8]"
                  aria-hidden
                />
                {copy.labInterval}
              </span>
              {laneCount > 0 && markerPoints.length > 0 && (
                <span className="inline-flex items-center gap-1.5">
                  <span
                    className="inline-block w-6 h-2.5 rounded-sm bg-[#d7e6f5] border border-[#6d8eae]"
                    aria-hidden
                  />
                  {copy.journalPeriod}
                </span>
              )}
            </span>
          </div>
        )}

        <div className="w-full">
          {!hasHistory ? (
            <p className="font-['Inter'] text-sm text-[#565e74] py-8">
              {history.length > 0 ? copy.noFilteredPanels : copy.noPanels}
            </p>
          ) : markerPoints.length === 0 ? (
            <p className="font-['Inter'] text-sm text-[#565e74] py-8">{copy.markerNotOnReports}</p>
          ) : (
            <>
              <svg
                viewBox={`0 0 ${chartWidth} ${svgHeight}`}
                className="w-full h-auto"
                role="img"
                aria-label={copy.markerTrack}
              >
                {markerPoints.map((point, index) => {
                  const band = bandRect(point.interval, getMarkerX(index));
                  if (!band) {
                    return null;
                  }
                  const label = intervalLabel(point.interval);
                  return (
                    <rect
                      key={`${point.record.id}-band`}
                      x={band.x}
                      y={band.y}
                      width={band.width}
                      height={band.height}
                      fill="#e7eef6"
                      stroke="#94a3b8"
                      strokeWidth="1"
                      rx="2"
                    >
                      {label && <title>{label}</title>}
                    </rect>
                  );
                })}
                <polyline
                  fill="none"
                  stroke="#006194"
                  strokeWidth="3"
                  points={markerPoints
                    .map((point, index) => `${getMarkerX(index)},${getBioY(point.value)}`)
                    .join(' ')}
                />
                {markerPoints.map((point, index) => {
                  const cx = getMarkerX(index);
                  const cy = getBioY(point.value);
                  const flagged = point.interval?.outsideInterval === true;
                  return (
                    <g key={point.record.id}>
                      <circle
                        cx={cx}
                        cy={cy}
                        r="5"
                        fill={flagged ? '#f8f9ff' : '#006194'}
                        stroke={flagged ? '#3f4850' : '#ffffff'}
                        strokeWidth="2"
                        role="button"
                        tabIndex={0}
                        aria-label={fill(copy.openPoint, {
                          date: panelWhen(point.record),
                          lab: point.record.labSource,
                          value: `${formatBound(point.value)} ${activeBioDef?.unit ?? ''}`,
                        })}
                        className="cursor-pointer outline-none focus-visible:stroke-[#0b1c30] focus-visible:stroke-[3px]"
                        onClick={() => openRecord(point.record)}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault();
                            openRecord(point.record);
                          }
                        }}
                      >
                        {flagged && <title>{copy.outsideInterval}</title>}
                      </circle>
                      <text
                        x={cx}
                        y={cy - 10}
                        textAnchor="middle"
                        fontSize="10"
                        fontWeight="bold"
                        fill={flagged ? '#3f4850' : '#006194'}
                        fontFamily="JetBrains Mono"
                      >
                        {point.value.toFixed(1)}
                      </text>
                      <text
                        x={cx}
                        y={dateLabelY}
                        textAnchor="middle"
                        fontSize="10"
                        fill="#565e74"
                        fontFamily="JetBrains Mono"
                      >
                        {(point.record.collectedAt ?? point.record.date).slice(0, 7)}
                      </text>
                    </g>
                  );
                })}
                {periodLayout.periods.map((band) => {
                  const x0 = padding.left + fractionOnAxis(band.start, periodLayout.axis) * plotWidth;
                  const x1 =
                    padding.left + fractionOnAxis(periodDrawEnd(band), periodLayout.axis) * plotWidth;
                  const x = Math.min(x0, x1);
                  const width = Math.max(x1 - x0, 2);
                  const y = plotBottom + 8 + band.lane * (laneHeight + laneGap);
                  const clipId = `period-${band.id}`;
                  const labelWidth = band.title.length * 6.4 + 8;
                  const inside = width >= labelWidth;
                  const roomRight = chartWidth - padding.right - (x + width);
                  const textX = inside ? x + 4 : roomRight >= labelWidth ? x + width + 4 : x - 4;
                  const textAnchor = inside || roomRight >= labelWidth ? 'start' : 'end';
                  return (
                    <g key={`period-${band.id}`} data-period-band={band.title}>
                      <rect
                        x={x}
                        y={y}
                        width={width}
                        height={laneHeight}
                        fill="#d7e6f5"
                        stroke="#6d8eae"
                        strokeWidth="1"
                        rx="2"
                      >
                        <title>{band.title}</title>
                      </rect>
                      {inside && (
                        <clipPath id={clipId}>
                          <rect x={x + 3} y={y} width={Math.max(width - 6, 0)} height={laneHeight} />
                        </clipPath>
                      )}
                      <text
                        x={textX}
                        y={y + laneHeight / 2}
                        clipPath={inside ? `url(#${clipId})` : undefined}
                        textAnchor={textAnchor}
                        dominantBaseline="central"
                        fontSize="10"
                        fill="#0b1c30"
                        fontFamily="Inter, sans-serif"
                      >
                        {band.title}
                      </text>
                    </g>
                  );
                })}
              </svg>
              <ul className="mt-3 flex flex-col gap-2">
                {markerPoints.map((point) => {
                  const label = intervalLabel(point.interval);
                  const flagged = point.interval?.outsideInterval === true;
                  const when = panelWhen(point.record);
                  return (
                    <li
                      key={`${point.record.id}-caption`}
                      className="font-['Inter'] text-xs text-[#3f4850]"
                    >
                      <div className="flex flex-wrap items-baseline gap-x-2">
                        <span className="font-['JetBrains_Mono']">{when}</span>
                        <span className="font-['JetBrains_Mono']">
                          {formatBound(point.value)} {activeBioDef?.unit}
                          {point.interval?.labFlag ? ` ${point.interval.labFlag}` : ''}
                        </span>
                        {!point.record.sessionOnly && (
                          <span className="font-['JetBrains_Mono'] text-[#565e74]">
                            {label ?? copy.intervalNotPrinted}
                          </span>
                        )}
                      </div>
                      {point.interval?.referenceText && (
                        <p className="text-[#565e74] mt-0.5">
                          {fill(copy.asPrinted, { text: point.interval.referenceText })}
                        </p>
                      )}
                      {flagged && (
                        <p className="mt-1 text-[#3f4850] bg-[#f8f9ff] border border-[#cbd5e1] rounded px-2.5 py-1.5">
                          {copy.outsideInterval}
                        </p>
                      )}
                    </li>
                  );
                })}
              </ul>
            </>
          )}
        </div>
      </div>

      <div className="bg-[#ffffff] rounded-xl border border-[#cbd5e1] shadow-xs overflow-hidden">
        <div className="px-5 py-4 bg-[#eff4ff] border-b border-[#dce9ff] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-['Inter'] text-sm font-bold text-[#0b1c30]">
              {fill(copy.registry, { count: filteredHistory.length })}
            </span>
            {hasConfirmed && (
              <span className="font-['JetBrains_Mono'] text-xs text-[#3f4850] font-semibold bg-[#f8f9ff] px-2 py-0.5 rounded border border-[#cbd5e1]">
                {copy.confirmedBadge}
              </span>
            )}
            {hasSessionSnapshot && (
              <span className="font-['JetBrains_Mono'] text-xs text-[#004b73] font-semibold bg-[#cce5ff] px-2 py-0.5 rounded border border-[#dce9ff]">
                {copy.sessionOnly}
              </span>
            )}
          </div>
          <button
            onClick={() => setShowReportModal(true)}
            disabled={history.length === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#ffffff] hover:bg-[#f8fafc] text-[#006194] border border-[#cbd5e1] text-xs font-semibold transition-colors cursor-pointer shadow-2xs disabled:opacity-50"
          >
            <FileDown className="w-3.5 h-3.5" />
            <span>{copy.printable}</span>
          </button>
        </div>

        {deleteError && (
          <p className="px-5 py-2 font-['Inter'] text-xs text-[#3f4850] bg-[#f8f9ff] border-b border-[#e2e8f0]">
            {deleteError}
          </p>
        )}
        <div className="overflow-x-auto">
          <table className="w-full text-left font-['Inter'] text-xs">
            <thead>
              <tr className="bg-[#f8f9ff] text-[#565e74] font-['JetBrains_Mono'] text-[11px] uppercase tracking-wider border-b border-[#e2e8f0]">
                <th className="py-3 px-4">{copy.colDate}</th>
                <th className="py-3 px-3">{copy.colLab}</th>
                <th className="py-3 px-3">{copy.colMarkers}</th>
                <th className="py-3 px-3">{copy.colStatus}</th>
                <th className="py-3 px-3">{copy.colChrono}</th>
                <th className="py-3 px-3">{copy.colPheno}</th>
                <th className="py-3 px-3">{copy.colMissing}</th>
                <th className="py-3 px-4 text-right">{copy.colActions}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f1f5f9]">
              {filteredHistory.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-[#565e74]">
                    {history.length > 0 ? copy.noFilteredPanels : copy.noPanels}
                  </td>
                </tr>
              ) : [...filteredHistory].reverse().map((record) => (
                <tr key={record.id} className="hover:bg-[#f8f9ff] transition-colors">
                  <td className="py-3.5 px-4 font-bold text-[#0b1c30]">
                    <span className="inline-flex items-center gap-2">
                      <Calendar className="w-3.5 h-3.5 text-[#006194]" />
                      {panelWhen(record)}
                    </span>
                  </td>
                  <td className="py-3.5 px-3 text-[#3f4850]">{record.labSource}</td>
                  <td className="py-3.5 px-3 font-['JetBrains_Mono'] text-[#0b1c30]">
                    {record.markerCount}
                  </td>
                  <td className="py-3.5 px-3">
                    <span className="font-['JetBrains_Mono'] text-[10px] font-semibold text-[#3f4850]">
                      {record.sessionOnly ? copy.sessionOnly : copy.confirmedStatus}
                    </span>
                  </td>
                  <td className="py-3.5 px-3 font-['JetBrains_Mono'] text-[#565e74]">
                    {record.chronologicalAge === null ? copy.ageMissing : `${record.chronologicalAge.toFixed(1)}y`}
                  </td>
                  <td className="py-3.5 px-3 font-['JetBrains_Mono'] text-[#0b1c30]">
                    {record.phenoAge === null ? '—' : `${record.phenoAge.toFixed(1)}y`}
                  </td>
                  <td className="py-3.5 px-3 text-[#3f4850] max-w-[240px]">
                    {record.phenoAge !== null
                      ? '—'
                      : record.missingMarkers.length > 0
                        ? missingMarkerText(record, m.biomarkers)
                        : record.chronologicalAge === null
                          ? copy.ageMissing
                          : '—'}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => {
                          openRecord(record);
                        }}
                        className="px-2.5 py-1 rounded bg-[#eff4ff] hover:bg-[#e5eeff] text-[#006194] font-semibold text-[11px] transition-colors cursor-pointer"
                      >
                        {copy.loadEngine}
                      </button>
                      <button
                        onClick={() => removeUpload(record.id)}
                        className="p-1 rounded text-[#565e74] hover:bg-[#f1f5f9] transition-colors cursor-pointer"
                        title={copy.deleteEntry}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <PrintableReportModal
        isOpen={showReportModal}
        onClose={() => setShowReportModal(false)}
        history={history}
      />
    </div>
  );
};
