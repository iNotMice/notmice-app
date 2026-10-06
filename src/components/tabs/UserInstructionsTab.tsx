import React from 'react';
import { AlertTriangle, BookOpen, Check, X } from 'lucide-react';
import { MedicalReviewBadge } from '../MedicalReviewBadge';
import { BIOMARKER_IDS } from '../../i18n/biomarkerIds';
import { useI18n } from '../../i18n/I18nProvider';
import { sectionLang } from '../../i18n/locales';

const SECTION_IDS = [
  'start',
  'account',
  'consents',
  'need',
  'upload',
  'file',
  'check',
  'get',
  'cabinet',
  'share',
  'trouble',
  'faq',
] as const;
type SectionId = (typeof SECTION_IDS)[number];

const h2 = "font-['Inter'] text-xl lg:text-2xl font-bold text-[#0b1c30]";
const p = "font-['Inter'] text-base leading-relaxed text-[#3f4850]";

function Bullets({ items }: { items: string[] }) {
  return (
    <ul className="flex flex-col gap-2">
      {items.map((item) => (
        <li key={item} className={`flex gap-2 ${p}`}>
          <span aria-hidden="true" className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[#006194]" />
          {item}
        </li>
      ))}
    </ul>
  );
}

function Questions({ items }: { items: { q: string; a: string }[] }) {
  return (
    <div className="flex flex-col divide-y divide-[#e2e8f0]">
      {items.map((item) => (
        <details key={item.q} className="group py-3">
          <summary className="cursor-pointer list-none text-base font-semibold text-[#0b1c30] marker:hidden">
            <span className="mr-2 inline-block text-[#006194] transition-transform group-open:rotate-90" aria-hidden="true">
              ›
            </span>
            {item.q}
          </summary>
          <p className={`mt-2 pl-5 ${p}`}>{item.a}</p>
        </details>
      ))}
    </div>
  );
}

function TitledList({ items }: { items: { title: string; body: string }[] }) {
  return (
    <dl className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {items.map((item) => (
        <div key={item.title} className="rounded-lg border border-[#e2e8f0] bg-[#f8f9ff] px-4 py-3">
          <dt className="text-base font-semibold text-[#0b1c30]">{item.title}</dt>
          <dd className={`mt-1 ${p}`}>{item.body}</dd>
        </div>
      ))}
    </dl>
  );
}

/** One page with anchors: a step-by-step guide from sign-up to results. */
export const UserInstructionsTab: React.FC = () => {
  const { m, locale } = useI18n();
  const copy = m.instructions;

  const section = (id: SectionId, children: React.ReactNode) => (
    <section
      id={`guide-${id}`}
      aria-labelledby={`guide-${id}-title`}
      className="scroll-mt-24 rounded-xl border border-[#e2e8f0] bg-[#ffffff] p-5 lg:p-6 flex flex-col gap-3"
    >
      <h2 id={`guide-${id}-title`} className={h2}>
        {copy.sections[id]}
      </h2>
      {children}
    </section>
  );

  return (
    <div
      className="w-full max-w-[1200px] mx-auto px-4 lg:px-8 py-8 lg:py-10 grid grid-cols-1 lg:grid-cols-12 gap-8 items-start"
      lang={sectionLang(locale, 'instructions')}
    >
      <header className="lg:col-span-12 flex flex-col gap-2 border-b border-[#e2e8f0] pb-6">
        <span className="inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-[#006194]">
          <BookOpen className="w-4 h-4" aria-hidden="true" />
          {copy.stage}
        </span>
        <h1 className="font-['Inter'] text-3xl lg:text-4xl font-bold tracking-tight text-[#0b1c30]">{copy.title}</h1>
        <p className="max-w-3xl text-lg leading-relaxed text-[#3f4850]">{copy.lead}</p>
        <MedicalReviewBadge />
      </header>

      <nav aria-label={copy.tocTitle} className="lg:col-span-3 lg:sticky lg:top-24">
        <p className="mb-2 text-sm font-semibold text-[#3f4850]">{copy.tocTitle}</p>
        <ol className="flex flex-col gap-1">
          {SECTION_IDS.map((id) => (
            <li key={id}>
              <a
                href={`#guide-${id}`}
                className="block rounded-md px-3 py-1.5 text-[15px] text-[#3f4850] hover:bg-[#eff4ff] hover:text-[#0b1c30]"
              >
                {copy.sections[id]}
              </a>
            </li>
          ))}
        </ol>
      </nav>

      <div className="lg:col-span-9 flex flex-col gap-5 min-w-0">
        {section(
          'start',
          <>
            <p className={p}>{copy.start.lead}</p>
            <ol className="flex flex-col gap-3">
              {copy.start.steps.map((step, index) => (
                <li key={step.title} className="flex gap-3">
                  <span
                    aria-hidden="true"
                    className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#006194] text-sm font-bold text-[#ffffff]"
                  >
                    {index + 1}
                  </span>
                  <div className="min-w-0">
                    <p className="text-base font-semibold text-[#0b1c30]">{step.title}</p>
                    <p className={p}>{step.body}</p>
                  </div>
                </li>
              ))}
            </ol>
            <p className="rounded-lg bg-[#eff4ff] px-4 py-3 text-base text-[#0b1c30]">{copy.start.languageNote}</p>
          </>,
        )}
        {section(
          'account',
          <>
            <p className={p}>{copy.account.lead}</p>
            <ol className="flex flex-col gap-2 list-decimal pl-6">
              {copy.account.steps.map((step) => (
                <li key={step} className={p}>
                  {step}
                </li>
              ))}
            </ol>
            <p className={p}>{copy.account.forgot}</p>
            <p className={p}>{copy.account.phrase}</p>
          </>,
        )}
        {section(
          'consents',
          <>
            <p className={p}>{copy.consents.lead}</p>
            <ul className="flex flex-col gap-3">
              {copy.consents.items.map((item, index) => (
                <li key={item.title} className="rounded-lg border border-[#e2e8f0] px-4 py-3">
                  <p className="flex flex-wrap items-center gap-2 text-base font-semibold text-[#0b1c30]">
                    {item.title}
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-semibold ${
                        index === 0 ? 'bg-[#fff6e0] text-[#5c3a00]' : 'bg-[#eff4ff] text-[#006194]'
                      }`}
                    >
                      {item.badge}
                    </span>
                  </p>
                  <p className={`mt-1 ${p}`}>{item.body}</p>
                </li>
              ))}
            </ul>
            <p className={p}>{copy.consents.surveyNote}</p>
          </>,
        )}
        {section(
          'need',
          <>
            <p className={p}>{copy.need.lead}</p>
            <p className="text-base font-semibold text-[#0b1c30]">{copy.need.markersTitle}</p>
            <ol className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5 list-decimal pl-6">
              {BIOMARKER_IDS.map((id) => (
                <li key={id} className="text-base text-[#3f4850]">
                  {m.biomarkers[id].name}
                </li>
              ))}
            </ol>
            <p className={p}>{copy.need.reportLook}</p>
            <p className="rounded-lg bg-[#eff4ff] px-4 py-3 text-base text-[#0b1c30]">{copy.need.hsCrpNote}</p>
            <p className={p}>{copy.need.missingNote}</p>
            <p className="rounded-lg border border-[#f5c97a] bg-[#fff6e0] px-4 py-3 text-base text-[#5c3a00]">{copy.need.oneFileNote}</p>
          </>,
        )}
        {section('upload', <Bullets items={copy.upload.items} />)}
        {section('file', <Bullets items={copy.file.items} />)}
        {section('check', <Bullets items={copy.check.items} />)}
        {section(
          'get',
          <>
            <Bullets items={copy.get.items} />
            <p className="text-base font-semibold text-[#0b1c30]">{copy.get.notTitle}</p>
            <ul className="flex flex-col gap-1.5">
              {copy.get.notItems.map((item) => (
                <li key={item} className={`flex gap-2 ${p}`}>
                  <X className="mt-1 w-4 h-4 shrink-0 text-[#ba1a1a]" aria-hidden="true" />
                  {item}
                </li>
              ))}
            </ul>
          </>,
        )}
        {section(
          'cabinet',
          <>
            <p className={p}>{copy.cabinet.lead}</p>
            <TitledList items={copy.cabinet.items} />
          </>,
        )}
        {section(
          'share',
          <>
            <p className={p}>{copy.share.lead}</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="mb-2 text-base font-semibold text-[#006947]">{copy.share.shownTitle}</p>
                <ul className="flex flex-col gap-1.5">
                  {copy.share.shown.map((item) => (
                    <li key={item} className={`flex gap-2 ${p}`}>
                      <Check className="mt-1 w-4 h-4 shrink-0 text-[#006947]" aria-hidden="true" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="mb-2 text-base font-semibold text-[#ba1a1a]">{copy.share.hiddenTitle}</p>
                <ul className="flex flex-col gap-1.5">
                  {copy.share.hidden.map((item) => (
                    <li key={item} className={`flex gap-2 ${p}`}>
                      <X className="mt-1 w-4 h-4 shrink-0 text-[#ba1a1a]" aria-hidden="true" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="rounded-lg border-2 border-[#d97706] bg-[#fff6e0] p-4" role="note">
              <p className="inline-flex items-center gap-2 text-base font-bold text-[#5c3a00]">
                <AlertTriangle className="w-5 h-5" aria-hidden="true" />
                {copy.share.warningTitle}
              </p>
              <p className="mt-1 text-base leading-relaxed text-[#5c3a00]">{copy.share.warning}</p>
            </div>
          </>,
        )}
        {section('trouble', <Questions items={copy.trouble} />)}
        {section('faq', <Questions items={copy.faq} />)}
      </div>
    </div>
  );
};
