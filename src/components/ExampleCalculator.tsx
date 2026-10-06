import React, { useEffect, useMemo, useState } from 'react';
import { RotateCcw } from 'lucide-react';
import { fetchPhenoAge } from '../api/phenoage';
import { ALEXEI_FOLLOW_UP, ALEXEI_START, type ExampleSnapshot } from '../data/alexeiExample';
import { PHENOAGE_BIOMARKERS } from '../data/phenoAgeData';
import { isBiomarkerId, type BiomarkerId } from '../i18n/biomarkerIds';
import { formatNumber, formatSigned } from '../i18n/format';
import { useI18n } from '../i18n/I18nProvider';

type SnapshotId = 'start' | 'followUp';

const SNAPSHOTS: Record<SnapshotId, ExampleSnapshot> = {
  start: ALEXEI_START,
  followUp: ALEXEI_FOLLOW_UP,
};

function sliderDigits(step: number): number {
  if (step >= 1) {
    return 0;
  }
  return step >= 0.1 ? 1 : 2;
}

interface ExampleCalculatorProps {
  /** `home` shows two plain-language sliders; `method` shows all nine with LOINC codes. */
  variant: 'home' | 'method';
  /** Story paragraphs for each tab, so the text always matches the numbers on screen. */
  story?: Record<SnapshotId, string[]>;
}

/**
 * Alexei's fictional panel, scored by the production API.
 * Local state only: a signed-in participant's own panel never appears here.
 */
export const ExampleCalculator: React.FC<ExampleCalculatorProps> = ({ variant, story }) => {
  const { m, locale } = useI18n();
  const copy = m.home.example;
  const [snapshot, setSnapshot] = useState<SnapshotId>('start');
  const [markers, setMarkers] = useState<Record<string, number>>({ ...ALEXEI_START.biomarkers });
  const [phenoAge, setPhenoAge] = useState<number | null>(null);
  const [failed, setFailed] = useState(false);

  const age = SNAPSHOTS[snapshot].chronologicalAge;
  const edited = useMemo(
    () =>
      Object.entries(SNAPSHOTS[snapshot].biomarkers).some(([id, value]) => markers[id] !== value),
    [markers, snapshot],
  );

  useEffect(() => {
    const controller = new AbortController();
    setFailed(false);
    const timer = window.setTimeout(() => {
      void fetchPhenoAge(age, markers, controller.signal)
        .then((score) => {
          if (!controller.signal.aborted) {
            setPhenoAge(score.phenoAge);
          }
        })
        .catch((err: unknown) => {
          if (controller.signal.aborted || (err instanceof DOMException && err.name === 'AbortError')) {
            return;
          }
          setPhenoAge(null);
          setFailed(true);
        });
    }, 200);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [age, markers]);

  const selectSnapshot = (next: SnapshotId) => {
    setSnapshot(next);
    setMarkers({ ...SNAPSHOTS[next].biomarkers });
  };

  // Both variants show all nine markers so the example never implies that a
  // smaller subset is enough. Home uses plain names; the method page adds LOINC.
  const sliders = PHENOAGE_BIOMARKERS.filter((marker) => isBiomarkerId(marker.id)).map((marker) => ({
    id: marker.id as BiomarkerId,
    min: marker.clinicalRange[0],
    max: marker.clinicalRange[1],
    step: marker.step,
    digits: sliderDigits(marker.step),
  }));

  const loincFor = (id: BiomarkerId) => PHENOAGE_BIOMARKERS.find((marker) => marker.id === id)?.loinc;
  const sliderLabel = (id: BiomarkerId) =>
    variant === 'home'
      ? m.biomarkers[id].name
      : `${m.biomarkers[id].name} · LOINC ${loincFor(id) ?? ''}`;

  const delta = phenoAge === null ? null : phenoAge - age;

  return (
    <div className="flex flex-col gap-4">
      <div role="tablist" aria-label={copy.title} className="grid grid-cols-2 gap-1 rounded-lg bg-[#eff4ff] p-1">
        {(['start', 'followUp'] as const).map((id) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={snapshot === id}
            onClick={() => selectSnapshot(id)}
            className={`rounded-md px-3 py-2 text-[15px] font-semibold transition-colors cursor-pointer ${
              snapshot === id ? 'bg-[#ffffff] text-[#0b1c30] shadow-sm' : 'text-[#3f4850] hover:text-[#0b1c30]'
            }`}
          >
            {id === 'start' ? copy.startTab : copy.followUpTab}
          </button>
        ))}
      </div>

      {story && (
        <div className="flex flex-col gap-2.5" role="tabpanel">
          {story[snapshot].map((paragraph) => (
            <p key={paragraph} className="text-[15px] leading-relaxed text-[#3f4850]">
              {paragraph}
            </p>
          ))}
        </div>
      )}

      <dl className="grid grid-cols-3 gap-2 rounded-lg border border-[#dce9ff] bg-[#f8fbff] p-3" aria-live="polite">
        <div className="flex flex-col">
          <dt className="text-[13px] text-[#3f4850]">{copy.passportAge}</dt>
          <dd className="text-2xl font-bold text-[#0b1c30]">{formatNumber(age, locale)}</dd>
        </div>
        <div className="flex flex-col">
          <dt className="text-[13px] text-[#3f4850]">{copy.indexAge}</dt>
          <dd className="text-2xl font-bold text-[#006194]">
            {phenoAge === null ? (failed ? '—' : '…') : formatNumber(phenoAge, locale)}
          </dd>
        </div>
        <div className="flex flex-col">
          <dt className="text-[13px] text-[#3f4850]">{copy.difference}</dt>
          <dd className="text-2xl font-bold text-[#0b1c30]">
            {delta === null ? '…' : formatSigned(delta, locale)}
          </dd>
        </div>
      </dl>
      {phenoAge === null && !failed && <p className="sr-only">{copy.calculating}</p>}
      {failed && (
        <p className="text-sm text-[#ba1a1a]" role="alert">
          {copy.unavailable}
        </p>
      )}

      <div className="flex flex-col gap-3">
        <div>
          <p className="text-[15px] font-semibold text-[#0b1c30]">
            {variant === 'home' ? copy.slidersTitle : m.specialists.method.slidersTitle}
          </p>
          <p className="text-sm text-[#3f4850]">{copy.slidersLead}</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {sliders.map((slider) => {
            const value = markers[slider.id] ?? slider.min;
            const unit = m.biomarkers[slider.id].unit;
            const inputId = `example-${variant}-${slider.id}`;
            return (
              <div key={slider.id} className="rounded-lg border border-[#dce9ff] bg-[#ffffff] p-3 flex flex-col gap-1.5">
                <div className="flex items-baseline justify-between gap-2">
                  <label htmlFor={inputId} className="text-sm font-medium text-[#0b1c30]">
                    {sliderLabel(slider.id)}
                  </label>
                  <span className="shrink-0 font-['JetBrains_Mono'] text-sm font-semibold text-[#006194]">
                    {formatNumber(value, locale, slider.digits)} {unit}
                  </span>
                </div>
                <input
                  id={inputId}
                  type="range"
                  min={slider.min}
                  max={slider.max}
                  step={slider.step}
                  value={value}
                  aria-valuetext={`${formatNumber(value, locale, slider.digits)} ${unit}`}
                  onChange={(event) =>
                    setMarkers((current) => ({ ...current, [slider.id]: parseFloat(event.target.value) }))
                  }
                  className="w-full accent-[#006194] cursor-pointer"
                />
              </div>
            );
          })}
        </div>
        {edited && (
          <button
            type="button"
            onClick={() => setMarkers({ ...SNAPSHOTS[snapshot].biomarkers })}
            className="self-start inline-flex items-center gap-1.5 text-sm font-semibold text-[#006194] hover:underline cursor-pointer"
          >
            <RotateCcw className="w-4 h-4" aria-hidden="true" />
            {copy.reset}
          </button>
        )}
      </div>
    </div>
  );
};
