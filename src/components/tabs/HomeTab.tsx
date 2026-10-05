import React from 'react';
import { ArrowRight, ChevronDown, ExternalLink, FileUp, ListChecks, ShieldCheck, Sparkles } from 'lucide-react';
import { TabType } from '../../types';
import { ExampleCalculator } from '../ExampleCalculator';
import { LEVINE_2018_DOI_URL } from '../../config/site';
import { BIOMARKER_IDS } from '../../i18n/biomarkerIds';
import { useI18n } from '../../i18n/I18nProvider';
import { sectionLang } from '../../i18n/locales';
import { pathForTab, type SpecialistPage } from '../../routes';

interface HomeTabProps {
  navigate: (tab: TabType, page?: SpecialistPage) => void;
  onOpenAccount: () => void;
  isAuthenticated: boolean;
}

const sectionTitle = "font-['Inter'] text-2xl lg:text-[28px] font-bold tracking-tight text-[#0b1c30]";
const kicker = "font-['Inter'] text-sm font-semibold uppercase tracking-wider text-[#006194]";
const body = "font-['Inter'] text-base leading-relaxed text-[#3f4850]";

/** Plain-language home page: what this is, why it matters to you and to science, what happens to the file. */
export const HomeTab: React.FC<HomeTabProps> = ({ navigate, onOpenAccount, isAuthenticated }) => {
  const { m, locale } = useI18n();
  const copy = m.home;

  const link =
    (tab: TabType, page?: SpecialistPage) =>
    (event: React.MouseEvent<HTMLAnchorElement>) => {
      event.preventDefault();
      navigate(tab, page);
    };
  const href = (tab: TabType, page?: SpecialistPage) => `${pathForTab(tab)}${page ? `#${page}` : ''}`;

  const primaryCta = isAuthenticated ? (
    <button
      type="button"
      onClick={() => navigate('upload-lab')}
      className="inline-flex items-center justify-center gap-2 rounded-md bg-[#006194] px-6 py-3 text-base font-semibold text-[#ffffff] shadow-sm transition-colors hover:bg-[#004b73] cursor-pointer"
    >
      <FileUp className="w-5 h-5" aria-hidden="true" />
      {copy.ctaUpload}
    </button>
  ) : (
    <button
      type="button"
      onClick={onOpenAccount}
      className="inline-flex items-center justify-center gap-2 rounded-md bg-[#006194] px-6 py-3 text-base font-semibold text-[#ffffff] shadow-sm transition-colors hover:bg-[#004b73] cursor-pointer"
    >
      {copy.ctaCreate}
      <ArrowRight className="w-5 h-5" aria-hidden="true" />
    </button>
  );

  return (
    <div className="flex flex-col w-full" lang={sectionLang(locale, 'home')}>
      {/* 2. First screen */}
      <section className="w-full max-w-[1200px] mx-auto px-4 lg:px-8 pt-10 pb-12 lg:pt-16 lg:pb-16">
        <div className="flex max-w-3xl flex-col items-start gap-5">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[#e0efff] px-3 py-1 text-sm font-semibold text-[#004b73]">
            <Sparkles className="w-4 h-4" aria-hidden="true" />
            {copy.kicker}
          </span>
          <h1 className="font-['Inter'] text-[32px] leading-[1.15] sm:text-[40px] lg:text-[48px] font-bold tracking-tight text-[#0b1c30]">
            {copy.headline} <span className="text-[#006194]">{copy.headlineAccent}</span>
          </h1>
          <p className="font-['Inter'] text-lg leading-relaxed text-[#3f4850]">{copy.subhead}</p>
          <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
            {primaryCta}
            <a
              href="#how-it-works"
              className="inline-flex items-center justify-center gap-2 rounded-md border border-[#cbd5e1] bg-[#ffffff] px-6 py-3 text-base font-semibold text-[#0b1c30] transition-colors hover:bg-[#eff4ff]"
            >
              {copy.ctaHow}
              <ChevronDown className="w-5 h-5" aria-hidden="true" />
            </a>
          </div>
          <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[15px] text-[#3f4850]">
            <ShieldCheck className="w-5 h-5 text-[#006947]" aria-hidden="true" />
            <span>{copy.trustLine}</span>
            <a
              href={href('user-instructions')}
              onClick={link('user-instructions')}
              className="font-semibold text-[#006194] underline underline-offset-2"
            >
              {copy.trustLink}
            </a>
          </p>
        </div>
      </section>

      {/* 3–7. Mission, index, for you, for science, with Alexei alongside */}
      <section className="w-full border-t border-[#e2e8f0] bg-[#ffffff]">
        <div className="max-w-[1200px] mx-auto px-4 lg:px-8 py-12 lg:py-16 grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-start">
          <div className="lg:col-span-7 flex flex-col gap-14">
            <article className="flex flex-col gap-3" aria-labelledby="home-mission">
              <span className={kicker}>{copy.missionKicker}</span>
              <h2 id="home-mission" className={sectionTitle}>
                {copy.missionTitle}
              </h2>
              {copy.missionBody.map((paragraph) => (
                <p key={paragraph} className={body}>
                  {paragraph}
                </p>
              ))}
              <p className="rounded-lg border-l-4 border-[#006194] bg-[#eff4ff] px-4 py-3 text-base text-[#0b1c30]">
                {copy.missionStatus}
              </p>
            </article>

            <article className="flex flex-col gap-3" aria-labelledby="home-index">
              <span className={kicker}>{copy.indexKicker}</span>
              <h2 id="home-index" className={sectionTitle}>
                {copy.indexTitle}
              </h2>
              {copy.indexBody.map((paragraph) => (
                <p key={paragraph} className={body}>
                  {paragraph}
                </p>
              ))}
              <details className="group rounded-lg border border-[#dce9ff] bg-[#f8fbff]">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-base font-semibold text-[#0b1c30]">
                  <span className="inline-flex items-center gap-2">
                    <ListChecks className="w-5 h-5 text-[#006194]" aria-hidden="true" />
                    {copy.markersToggle}
                  </span>
                  <ChevronDown className="w-5 h-5 transition-transform group-open:rotate-180" aria-hidden="true" />
                </summary>
                <div className="px-4 pb-4">
                  <ul className="flex flex-col gap-2.5">
                    {BIOMARKER_IDS.map((id) => (
                      <li key={id} className="text-[15px] leading-relaxed text-[#3f4850]">
                        <span className="font-semibold text-[#0b1c30]">{m.biomarkers[id].name}.</span>{' '}
                        {m.biomarkers[id].weight}
                      </li>
                    ))}
                  </ul>
                  <p className="mt-3 text-[15px] text-[#3f4850]">{copy.markersNote}</p>
                </div>
              </details>
              <div className="flex flex-wrap gap-x-5 gap-y-2 text-[15px]">
                <a
                  href={LEVINE_2018_DOI_URL}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 font-semibold text-[#006194] underline underline-offset-2"
                >
                  {copy.paperLink}
                  <ExternalLink className="w-4 h-4" aria-hidden="true" />
                </a>
                <a
                  href={href('specialists', 'method')}
                  onClick={link('specialists', 'method')}
                  className="font-semibold text-[#006194] underline underline-offset-2"
                >
                  {copy.matrixLink}
                </a>
              </div>
            </article>

            <article className="flex flex-col gap-4" aria-labelledby="home-for-you">
              <span className={kicker}>{copy.forYouKicker}</span>
              <h2 id="home-for-you" className={sectionTitle}>
                {copy.forYouTitle}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-1 gap-3">
                {copy.forYou.map((card) => (
                  <div key={card.title} className="rounded-xl border border-[#e2e8f0] bg-[#f8f9ff] p-5">
                    <h3 className="text-lg font-bold text-[#0b1c30]">{card.title}</h3>
                    <p className="mt-2 text-[15px] leading-relaxed text-[#3f4850]">{card.body}</p>
                  </div>
                ))}
              </div>
            </article>

            <article className="flex flex-col gap-4" aria-labelledby="home-for-science">
              <span className={kicker}>{copy.forScienceKicker}</span>
              <h2 id="home-for-science" className={sectionTitle}>
                {copy.forScienceTitle}
              </h2>
              <p className={body}>{copy.forScienceLead}</p>
              <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-1 gap-3">
                {copy.forScience.map((card) => (
                  <div key={card.title} className="rounded-xl border border-[#e2e8f0] bg-[#f8f9ff] p-5">
                    <h3 className="text-lg font-bold text-[#0b1c30]">{card.title}</h3>
                    <p className="mt-2 text-[15px] leading-relaxed text-[#3f4850]">{card.body}</p>
                  </div>
                ))}
              </div>
            </article>
          </div>

          {/* 7. Alexei: sticky beside blocks 3–6 from 1024 px, after block 6 below that */}
          <aside className="lg:col-span-5 lg:sticky lg:top-24" aria-labelledby="home-example">
            <div className="rounded-2xl border border-[#cbd5e1] bg-[#ffffff] p-5 shadow-md flex flex-col gap-3 lg:max-h-[calc(100vh-7rem)] lg:overflow-y-auto">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 id="home-example" className="text-xl font-bold text-[#0b1c30]">
                  {copy.example.title}
                </h2>
                <span className="rounded-full border border-[#f5c97a] bg-[#fff6e0] px-3 py-1 text-sm font-semibold text-[#7a4b00]">
                  {copy.example.badge}
                </span>
              </div>
              <ExampleCalculator
                variant="home"
                story={{ start: copy.example.storyStart, followUp: copy.example.storyFollowUp }}
              />
              <p className="border-t border-[#e2e8f0] pt-3 text-sm text-[#3f4850]">{copy.example.footnote}</p>
            </div>
          </aside>
        </div>
      </section>

      {/* 8. How it works */}
      <section id="how-it-works" className="w-full scroll-mt-24 border-t border-[#dce9ff] bg-[#eff4ff]">
        <div className="max-w-[1200px] mx-auto px-4 lg:px-8 py-12 lg:py-16 flex flex-col gap-8">
          <div className="flex flex-col gap-2">
            <span className={kicker}>{copy.howKicker}</span>
            <h2 className={sectionTitle}>{copy.howTitle}</h2>
          </div>
          <ol className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {copy.howSteps.map((step, index) => (
              <li key={step.title} className="rounded-xl border border-[#dce9ff] bg-[#ffffff] p-5 flex gap-4">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#006194] text-base font-bold text-[#ffffff]">
                  {index + 1}
                </span>
                <div>
                  <h3 className="text-lg font-bold text-[#0b1c30]">{step.title}</h3>
                  <p className="mt-1 text-[15px] leading-relaxed text-[#3f4850]">{step.body}</p>
                </div>
              </li>
            ))}
          </ol>
          <div className="rounded-xl border border-[#dce9ff] bg-[#ffffff] p-5 flex flex-col gap-3">
            <h3 className="inline-flex items-center gap-2 text-lg font-bold text-[#0b1c30]">
              <ShieldCheck className="w-5 h-5 text-[#006947]" aria-hidden="true" />
              {copy.privacyTitle}
            </h3>
            <ul className="flex flex-col gap-2">
              {copy.privacyLines.map((line) => (
                <li key={line} className="flex gap-2 text-base text-[#3f4850]">
                  <span aria-hidden="true" className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[#006947]" />
                  {line}
                </li>
              ))}
            </ul>
            <a
              href={href('user-instructions')}
              onClick={link('user-instructions')}
              className="self-start inline-flex items-center gap-1 text-base font-semibold text-[#006194] underline underline-offset-2"
            >
              {copy.guideLink}
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </a>
          </div>
        </div>
      </section>

      {/* 9. Final call */}
      <section className="w-full bg-[#004b73] text-[#ffffff]">
        <div className="max-w-[1200px] mx-auto px-4 lg:px-8 py-12 flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-col gap-2">
            <h2 className="text-2xl lg:text-[28px] font-bold">{copy.finalTitle}</h2>
            <p className="text-base text-[#dbeeff]">{copy.finalBody}</p>
            <p className="text-base text-[#dbeeff]">
              {copy.specialistsPrompt}{' '}
              <a
                href={href('specialists')}
                onClick={link('specialists')}
                className="font-semibold text-[#ffffff] underline underline-offset-2"
              >
                {copy.specialistsLink}
              </a>
            </p>
          </div>
          <div className="shrink-0">
            {isAuthenticated ? (
              <button
                type="button"
                onClick={() => navigate('upload-lab')}
                className="inline-flex items-center gap-2 rounded-md bg-[#ffffff] px-6 py-3 text-base font-bold text-[#004b73] hover:bg-[#eff4ff] cursor-pointer"
              >
                {copy.ctaUpload}
                <ArrowRight className="w-5 h-5" aria-hidden="true" />
              </button>
            ) : (
              <button
                type="button"
                onClick={onOpenAccount}
                className="inline-flex items-center gap-2 rounded-md bg-[#ffffff] px-6 py-3 text-base font-bold text-[#004b73] hover:bg-[#eff4ff] cursor-pointer"
              >
                {copy.ctaCreate}
                <ArrowRight className="w-5 h-5" aria-hidden="true" />
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  );
};
