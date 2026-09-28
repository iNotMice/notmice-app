import React from 'react';
import { ArrowRight, BookOpen } from 'lucide-react';
import { TabType } from '../../types';
import { useI18n } from '../../i18n/I18nProvider';

const SCREEN_TABS: TabType[] = [
  'overview-landing',
  'upload-lab',
  'review-extraction',
  'phenoage-engine',
  'biomarker-history',
  'protocol-journal',
  'data-sovereignty-public-sharing',
];

function isScreenTab(value: string): value is TabType {
  return (SCREEN_TABS as string[]).includes(value);
}

interface UserInstructionsTabProps {
  setActiveTab: (tab: TabType) => void;
}

export const UserInstructionsTab: React.FC<UserInstructionsTabProps> = ({ setActiveTab }) => {
  const { m } = useI18n();
  const copy = m.instructions;

  return (
    <div className="w-full max-w-[1440px] mx-auto px-4 lg:px-8 py-8 flex flex-col gap-8">
      <div className="border-b border-[#e2e8f0] pb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="bg-[#cce5ff] text-[#004b73] font-['JetBrains_Mono'] text-xs font-semibold px-2 py-0.5 rounded">
            {copy.stage}
          </span>
          <span className="font-['JetBrains_Mono'] text-xs text-[#565e74]">{copy.stageMeta}</span>
        </div>
        <h1 className="font-['Inter'] text-2xl lg:text-3xl font-bold text-[#0b1c30]">{copy.title}</h1>
        <p className="font-['Inter'] text-sm text-[#3f4850] mt-1 max-w-2xl">{copy.lead}</p>
      </div>

      <section className="bg-[#ffffff] border border-[#e2e8f0] rounded-lg p-5 shadow-xs">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-full bg-[#cce5ff] text-[#004b73] flex items-center justify-center shrink-0">
            <BookOpen className="w-4 h-4" />
          </div>
          <div>
            <h2 className="font-['Inter'] text-lg font-semibold text-[#0b1c30]">{copy.aboutTitle}</h2>
            <p className="font-['Inter'] text-sm text-[#3f4850] mt-1 leading-relaxed">{copy.aboutBody}</p>
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <div>
          <h2 className="font-['Inter'] text-lg font-semibold text-[#0b1c30]">{copy.mapTitle}</h2>
          <p className="font-['Inter'] text-sm text-[#3f4850] mt-1">{copy.mapLead}</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
          {copy.mapItems.map((item) => (
            <article key={item.name} className="bg-[#ffffff] border border-[#e2e8f0] rounded-lg p-4">
              <h3 className="font-['Inter'] text-sm font-semibold text-[#0b1c30]">{item.name}</h3>
              <p className="font-['Inter'] text-sm text-[#3f4850] mt-1 leading-relaxed">{item.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="bg-[#ffffff] border border-[#e2e8f0] rounded-lg p-5">
        <h2 className="font-['Inter'] text-lg font-semibold text-[#0b1c30]">{copy.pathTitle}</h2>
        <ol className="mt-3 flex flex-col gap-3">
          {copy.pathSteps.map((step, index) => (
            <li key={step} className="flex gap-3">
              <span className="font-['JetBrains_Mono'] text-xs font-semibold text-[#004b73] bg-[#cce5ff] w-6 h-6 rounded flex items-center justify-center shrink-0">
                {index + 1}
              </span>
              <p className="font-['Inter'] text-sm text-[#3f4850] leading-relaxed">{step}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-['Inter'] text-lg font-semibold text-[#0b1c30]">{copy.screensTitle}</h2>
        <div className="flex flex-col gap-3">
          {copy.screens.map((screen) => {
            const tab = isScreenTab(screen.tab) ? screen.tab : null;
            return (
              <article
                key={screen.tab}
                className="bg-[#ffffff] border border-[#e2e8f0] rounded-lg p-5 flex flex-col sm:flex-row sm:items-start gap-4"
              >
                <div className="flex-1">
                  <h3 className="font-['Inter'] text-base font-semibold text-[#0b1c30]">{screen.title}</h3>
                  <p className="font-['Inter'] text-sm text-[#3f4850] mt-1 leading-relaxed">{screen.body}</p>
                </div>
                {tab && (
                  <button
                    type="button"
                    onClick={() => setActiveTab(tab)}
                    className="shrink-0 inline-flex items-center justify-center gap-2 bg-[#eff4ff] hover:bg-[#e5eeff] text-[#0b1c30] px-4 py-2 rounded font-['Inter'] text-sm font-medium border border-[#dce9ff] cursor-pointer"
                  >
                    {copy.openSection}
                    <ArrowRight className="w-4 h-4 text-[#006194]" />
                  </button>
                )}
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
};
