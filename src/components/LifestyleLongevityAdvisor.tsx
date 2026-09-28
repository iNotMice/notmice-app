import React from 'react';
import { BIOMARKER_IDS } from '../i18n/biomarkerIds';
import { useI18n } from '../i18n/I18nProvider';
import { BookOpen } from 'lucide-react';

/**
 * Static educational cards for the nine PhenoAge markers.
 * The copy is prepared in advance and does not depend on a person's results.
 */
export const LifestyleLongevityAdvisor: React.FC = () => {
  const { m } = useI18n();
  const copy = m.lifestyleUi;

  return (
    <section
      id="lifestyle-longevity-advisor-root"
      aria-labelledby="marker-cards-title"
      className="bg-[#ffffff] rounded-xl border border-[#cbd5e1] shadow-xs p-6 lg:p-7 flex flex-col gap-6"
    >
      <div className="flex flex-col gap-2 border-b border-[#f1f5f9] pb-5">
        <div className="flex flex-wrap items-center gap-2">
          <h2
            id="marker-cards-title"
            className="font-['Inter'] text-lg font-bold text-[#0b1c30] flex items-center gap-2"
          >
            <BookOpen className="w-5 h-5 text-[#006194]" aria-hidden="true" />
            {copy.title}
          </h2>
          <span className="font-['JetBrains_Mono'] text-[11px] bg-[#eff4ff] text-[#004b73] border border-[#dce9ff] px-2 py-0.5 rounded font-semibold">
            {copy.badge}
          </span>
        </div>
        <p className="font-['Inter'] text-xs text-[#565e74] max-w-3xl leading-relaxed">{copy.lead}</p>
        <p className="font-['Inter'] text-xs text-[#3f4850] max-w-3xl leading-relaxed">{copy.interval}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3.5">
        {BIOMARKER_IDS.map((id) => (
          <article
            key={id}
            id={`marker-card-${id}`}
            className="rounded-xl border border-[#cbd5e1] bg-[#f8f9ff] p-4 flex flex-col gap-3"
          >
            <div>
              <span className="font-['JetBrains_Mono'] text-[10px] uppercase tracking-wide text-[#565e74]">
                {m.biomarkers[id].shortName}
              </span>
              <h3 className="font-['Inter'] text-sm font-bold text-[#0b1c30] mt-1">
                {m.biomarkers[id].name}
              </h3>
            </div>
            <p className="font-['Inter'] text-xs text-[#3f4850] leading-relaxed">{copy.cards[id]}</p>
            <p className="font-['Inter'] text-xs text-[#3f4850] leading-relaxed">{copy.indexRole}</p>
            <a
              href={copy.studyHref}
              className="font-['Inter'] text-xs font-semibold text-[#006194] underline underline-offset-2 mt-auto"
            >
              {copy.studyLabel}: {copy.studyCitation}
            </a>
          </article>
        ))}
      </div>

      <p className="p-4 bg-[#eff4ff] rounded-xl border border-[#dce9ff] text-xs text-[#3f4850] leading-relaxed">
        <strong>{copy.disclaimerTitle}</strong> {copy.disclaimer}
      </p>
    </section>
  );
};
