import React from 'react';
import { ArrowRight, Building2, Check, ExternalLink, FlaskConical, Mail, Stethoscope, X } from 'lucide-react';
import { ExampleCalculator } from '../ExampleCalculator';
import { MedicalReviewBadge } from '../MedicalReviewBadge';
import { PublicDatasetPanel } from '../PublicDatasetPanel';
import { LEVINE_2018_DOI_URL, LEVINE_2018_PUBMED_URL, TEAM_CONTACT_EMAIL } from '../../config/site';
import { PHENOAGE_BIOMARKERS } from '../../data/phenoAgeData';
import { BIOMARKER_IDS, type BiomarkerId } from '../../i18n/biomarkerIds';
import { useI18n } from '../../i18n/I18nProvider';
import { sectionLang } from '../../i18n/locales';
import { SPECIALIST_PAGES, type SpecialistPage } from '../../routes';

interface SpecialistsTabProps {
  page: SpecialistPage;
  onSelectPage: (page: SpecialistPage) => void;
}

/** Levine 2018 model units and weights, as in app/services/phenoage.py. */
const MODEL_ROWS: Record<BiomarkerId, { modelUnit: string; coefficient: string; conversion: 'creatinine' | 'glucose' | 'crp' | 'same' }> = {
  albumin: { modelUnit: 'g/L', coefficient: '−0.0336', conversion: 'same' },
  creatinine: { modelUnit: 'µmol/L', coefficient: '0.0095', conversion: 'creatinine' },
  glucose: { modelUnit: 'mmol/L', coefficient: '0.1953', conversion: 'glucose' },
  crp: { modelUnit: 'ln(mg/dL)', coefficient: '0.0954', conversion: 'crp' },
  lymphocyte: { modelUnit: '%', coefficient: '−0.0120', conversion: 'same' },
  mcv: { modelUnit: 'fL', coefficient: '0.0268', conversion: 'same' },
  rdw: { modelUnit: '%', coefficient: '0.3306', conversion: 'same' },
  alp: { modelUnit: 'U/L', coefficient: '0.0019', conversion: 'same' },
  wbc: { modelUnit: '10³/µL', coefficient: '0.0554', conversion: 'same' },
};

const AUDIENCE_ICONS = { doctor: Stethoscope, researcher: FlaskConical, laboratory: Building2 } as const;

const h2 = "font-['Inter'] text-2xl font-bold tracking-tight text-[#0b1c30]";
const h3 = "font-['Inter'] text-lg font-bold text-[#0b1c30]";
const p = "font-['Inter'] text-[15px] leading-relaxed text-[#3f4850]";
const card = 'rounded-xl border border-[#e2e8f0] bg-[#ffffff] p-5';

function BulletList({ items }: { items: string[] }) {
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

/** Section for doctors, researchers and laboratories: method, limits, data, lab portal, contact. */
export const SpecialistsTab: React.FC<SpecialistsTabProps> = ({ page, onSelectPage }) => {
  const { m, locale } = useI18n();
  const copy = m.specialists;
  const pages = SPECIALIST_PAGES.filter((id) => id !== 'contact' || TEAM_CONTACT_EMAIL !== null);

  return (
    <div className="w-full max-w-[1200px] mx-auto px-4 lg:px-8 py-8 lg:py-10 flex flex-col gap-8" lang={sectionLang(locale, 'specialists')}>
      <header className="flex flex-col gap-2 border-b border-[#e2e8f0] pb-6">
        <span className="text-sm font-semibold uppercase tracking-wider text-[#006194]">{copy.kicker}</span>
        <h1 className="font-['Inter'] text-3xl lg:text-4xl font-bold tracking-tight text-[#0b1c30]">{copy.title}</h1>
        <p className="max-w-3xl text-base leading-relaxed text-[#3f4850]">{copy.lead}</p>
      </header>

      <section aria-labelledby="specialists-audience" className="flex flex-col gap-3">
        <h2 id="specialists-audience" className="sr-only">
          {copy.audienceTitle}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {copy.audiences.map((audience) => {
            const Icon = AUDIENCE_ICONS[audience.id as keyof typeof AUDIENCE_ICONS] ?? FlaskConical;
            const target = SPECIALIST_PAGES.find((id) => id === audience.page) ?? 'method';
            return (
              <button
                key={audience.id}
                type="button"
                onClick={() => onSelectPage(target)}
                className={`${card} flex flex-col gap-2 text-left transition-colors hover:border-[#006194] hover:bg-[#f8fbff] cursor-pointer`}
              >
                <span className="flex items-center gap-2">
                  <Icon className="w-5 h-5 text-[#006194]" aria-hidden="true" />
                  <span className={h3}>{audience.title}</span>
                </span>
                <span className={p}>{audience.body}</span>
                <span className="mt-auto inline-flex items-center gap-1 pt-1 text-[15px] font-semibold text-[#006194]">
                  {audience.action}
                  <ArrowRight className="w-4 h-4" aria-hidden="true" />
                </span>
              </button>
            );
          })}
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        <nav aria-label={copy.kicker} className="lg:col-span-3 lg:sticky lg:top-24">
          <ul className="flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible">
            {pages.map((id) => (
              <li key={id} className="shrink-0">
                <a
                  href={`#${id}`}
                  aria-current={page === id ? 'page' : undefined}
                  onClick={(event) => {
                    event.preventDefault();
                    onSelectPage(id);
                  }}
                  className={`block rounded-md px-3 py-2 text-[15px] font-medium whitespace-nowrap lg:whitespace-normal ${
                    page === id ? 'bg-[#006194] text-[#ffffff]' : 'text-[#3f4850] hover:bg-[#eff4ff] hover:text-[#0b1c30]'
                  }`}
                >
                  {copy.pages[id]}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="lg:col-span-9 flex flex-col gap-6 min-w-0">
          {page === 'method' && (
            <>
              <div className="flex flex-col gap-2">
                <h2 className={h2}>{copy.method.title}</h2>
                <MedicalReviewBadge />
                <p className={p}>{copy.method.lead}</p>
                <p className="flex flex-wrap gap-x-4 gap-y-1 text-[15px]">
                  <a href={LEVINE_2018_DOI_URL} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-semibold text-[#006194] underline underline-offset-2">
                    DOI 10.18632/aging.101414 <ExternalLink className="w-4 h-4" aria-hidden="true" />
                  </a>
                  <a href={LEVINE_2018_PUBMED_URL} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-semibold text-[#006194] underline underline-offset-2">
                    PubMed 29676998 <ExternalLink className="w-4 h-4" aria-hidden="true" />
                  </a>
                </p>
              </div>
              <section className={`${card} flex flex-col gap-3`}>
                <h3 className={h3}>{copy.method.formulaTitle}</h3>
                {copy.method.formulaBody.map((line) => (
                  <p key={line} className={p}>
                    {line}
                  </p>
                ))}
              </section>
              <section className={`${card} flex flex-col gap-3`}>
                <h3 className={h3}>{copy.method.sourceTitle}</h3>
                <p className={p}>{copy.method.sourceBody}</p>
              </section>
              <section className={`${card} flex flex-col gap-3`}>
                <h3 className={h3}>{copy.method.unitsTitle}</h3>
                <p className={p}>{copy.method.unitsLead}</p>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[640px] text-left text-sm">
                    <thead>
                      <tr className="border-b border-[#dce9ff] bg-[#eff4ff] text-[#3f4850]">
                        <th className="px-3 py-2 font-semibold">{copy.method.colMarker}</th>
                        <th className="px-3 py-2 font-semibold">{copy.method.colLoinc}</th>
                        <th className="px-3 py-2 font-semibold">{copy.method.colInput}</th>
                        <th className="px-3 py-2 font-semibold">{copy.method.colModel}</th>
                        <th className="px-3 py-2 font-semibold">{copy.method.colCoefficient}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#f1f5f9] text-[#0b1c30]">
                      {BIOMARKER_IDS.map((id) => {
                        const row = MODEL_ROWS[id];
                        const loinc = PHENOAGE_BIOMARKERS.find((marker) => marker.id === id)?.loinc ?? '—';
                        return (
                          <tr key={id}>
                            <td className="px-3 py-2 font-medium">{m.biomarkers[id].name}</td>
                            <td className="px-3 py-2 font-['JetBrains_Mono']">{loinc}</td>
                            <td className="px-3 py-2">{m.biomarkers[id].unit}</td>
                            <td className="px-3 py-2">
                              {row.modelUnit}
                              <span className="block text-xs text-[#3f4850]">{copy.method.conversions[row.conversion]}</span>
                            </td>
                            <td className="px-3 py-2 font-['JetBrains_Mono']">{row.coefficient}</td>
                          </tr>
                        );
                      })}
                      <tr>
                        <td className="px-3 py-2 font-medium">{copy.method.ageRow}</td>
                        <td className="px-3 py-2">—</td>
                        <td className="px-3 py-2">{m.shell.years}</td>
                        <td className="px-3 py-2">{m.shell.years}</td>
                        <td className="px-3 py-2 font-['JetBrains_Mono']">0.0804</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </section>
              <section className={`${card} flex flex-col gap-3`}>
                <h3 className={h3}>{copy.method.pipelineTitle}</h3>
                <ol className="flex flex-col gap-3">
                  {copy.method.pipeline.map((step, index) => (
                    <li key={step.title} className="flex gap-3">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#eff4ff] text-sm font-bold text-[#006194]">
                        {index + 1}
                      </span>
                      <div>
                        <p className="text-[15px] font-semibold text-[#0b1c30]">{step.title}</p>
                        <p className={p}>{step.body}</p>
                      </div>
                    </li>
                  ))}
                </ol>
              </section>
              <section className={`${card} flex flex-col gap-3`}>
                <h3 className={h3}>{copy.method.versionsTitle}</h3>
                <BulletList items={copy.method.versions} />
              </section>
              <section className={`${card} flex flex-col gap-3`}>
                <p className={p}>{copy.method.slidersLead}</p>
                <ExampleCalculator variant="method" />
              </section>
            </>
          )}

          {page === 'limits' && (
            <>
              <div className="flex flex-col gap-2">
                <h2 className={h2}>{copy.limits.title}</h2>
                <MedicalReviewBadge />
                <p className={p}>{copy.limits.lead}</p>
              </div>
              <section className={`${card} flex flex-col gap-3`}>
                <h3 className={h3}>{copy.limits.notTitle}</h3>
                <BulletList items={copy.limits.notItems} />
                <p className="rounded-lg bg-[#eff4ff] px-4 py-3 text-[15px] text-[#0b1c30]">
                  {copy.limits.authorsNote}{' '}
                  <a href={LEVINE_2018_DOI_URL} target="_blank" rel="noreferrer" className="font-semibold text-[#006194] underline underline-offset-2">
                    Levine et al., 2018
                  </a>
                </p>
              </section>
              <section className={`${card} flex flex-col gap-3`}>
                <h3 className={h3}>{copy.limits.distortTitle}</h3>
                <BulletList items={copy.limits.distortItems} />
              </section>
              <section className={`${card} flex flex-col gap-3`}>
                <h3 className={h3}>{copy.limits.populationTitle}</h3>
                {copy.limits.populationBody.map((line) => (
                  <p key={line} className={p}>
                    {line}
                  </p>
                ))}
              </section>
              <section className={`${card} flex flex-col gap-3`}>
                <h3 className={h3}>{copy.limits.patientTitle}</h3>
                <BulletList items={copy.limits.patientItems} />
              </section>
            </>
          )}

          {page === 'data' && (
            <>
              <div className="flex flex-col gap-2">
                <h2 className={h2}>{copy.data.title}</h2>
                <p className={p}>{copy.data.lead}</p>
              </div>
              <section className={`${card} flex flex-col gap-3`}>
                <h3 className={h3}>{copy.data.licensesTitle}</h3>
                <dl className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {copy.data.licenses.map((license) => (
                    <div key={license.name} className="rounded-lg border border-[#dce9ff] bg-[#f8fbff] p-3">
                      <dt className="font-['JetBrains_Mono'] text-sm font-semibold text-[#006194]">{license.name}</dt>
                      <dd className="mt-1 text-[15px] text-[#3f4850]">{license.body}</dd>
                    </div>
                  ))}
                </dl>
              </section>
              <section className={`${card} flex flex-col gap-4`}>
                <h3 className={h3}>{copy.data.fieldsTitle}</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <p className="mb-2 text-[15px] font-semibold text-[#006947]">{copy.data.shownLabel}</p>
                    <ul className="flex flex-col gap-1.5">
                      {copy.data.fieldsShown.map((field) => (
                        <li key={field} className={`flex gap-2 ${p}`}>
                          <Check className="mt-1 w-4 h-4 shrink-0 text-[#006947]" aria-hidden="true" />
                          {field}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="mb-2 text-[15px] font-semibold text-[#ba1a1a]">{copy.data.hiddenLabel}</p>
                    <ul className="flex flex-col gap-1.5">
                      {copy.data.fieldsHidden.map((field) => (
                        <li key={field} className={`flex gap-2 ${p}`}>
                          <X className="mt-1 w-4 h-4 shrink-0 text-[#ba1a1a]" aria-hidden="true" />
                          {field}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
                <p className="rounded-lg bg-[#eff4ff] px-4 py-3 text-[15px] text-[#0b1c30]">{copy.data.pseudonymNote}</p>
                <p className="rounded-lg border border-[#f5c97a] bg-[#fff6e0] px-4 py-3 text-[15px] text-[#5c3a00]">{copy.data.cc0Note}</p>
              </section>
              <section className={`${card} flex flex-col gap-3`}>
                <h3 className={h3}>{copy.data.accessTitle}</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {copy.data.access.map((level) => (
                    <div key={level.title} className="rounded-lg border border-[#e2e8f0] bg-[#f8f9ff] p-4">
                      <p className="text-[15px] font-semibold text-[#0b1c30]">{level.title}</p>
                      <p className="mt-1 text-[15px] leading-relaxed text-[#3f4850]">{level.body}</p>
                    </div>
                  ))}
                </div>
              </section>
              <PublicDatasetPanel />
            </>
          )}

          {page === 'labs' && (
            <>
              <div className="flex flex-col gap-2">
                <h2 className={h2}>{copy.labs.title}</h2>
                <p className={p}>{copy.labs.lead}</p>
              </div>
              <section className={`${card} flex flex-col gap-4`}>
                <ol className="flex flex-col gap-3">
                  {copy.labs.steps.map((step, index) => (
                    <li key={step} className="flex gap-3">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#006194] text-sm font-bold text-[#ffffff]">
                        {index + 1}
                      </span>
                      <p className={p}>{step}</p>
                    </li>
                  ))}
                </ol>
                <p className="rounded-lg bg-[#eff4ff] px-4 py-3 text-[15px] text-[#0b1c30]">{copy.labs.privacy}</p>
                <a
                  href="/lab"
                  className="self-start inline-flex items-center gap-2 rounded-md bg-[#006194] px-5 py-2.5 text-base font-semibold text-[#ffffff] hover:bg-[#004b73]"
                >
                  {copy.labs.open}
                  <ArrowRight className="w-4 h-4" aria-hidden="true" />
                </a>
              </section>
            </>
          )}

          {page === 'contact' && TEAM_CONTACT_EMAIL !== null && (
            <section className={`${card} flex flex-col gap-2`}>
              <h2 className={h2}>{copy.contact.title}</h2>
              <p className={p}>
                {copy.contact.lead}{' '}
                <a href={`mailto:${TEAM_CONTACT_EMAIL}`} className="inline-flex items-center gap-1 font-semibold text-[#006194] underline underline-offset-2">
                  <Mail className="w-4 h-4" aria-hidden="true" />
                  {TEAM_CONTACT_EMAIL}
                </a>
              </p>
            </section>
          )}
        </div>
      </div>
    </div>
  );
};
