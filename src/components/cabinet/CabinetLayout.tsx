import React from 'react';
import { LogIn, UserRound } from 'lucide-react';
import { TabType } from '../../types';
import { fill } from '../../i18n/fill';
import { useI18n } from '../../i18n/I18nProvider';
import { sectionLang } from '../../i18n/locales';
import { CABINET_SECTIONS, pathForTab } from '../../routes';

/** Sections that only make sense for a signed-in participant. */
const GATED: readonly TabType[] = ['cabinet', 'cabinet-tests', 'cabinet-security'];

interface CabinetLayoutProps {
  activeTab: TabType;
  navigate: (tab: TabType) => void;
  isAuthenticated: boolean;
  publicId: string | null;
  onOpenAccount: () => void;
  children: React.ReactNode;
}

/** Personal account shell: title, section menu, and a sign-in gate for guests. */
export const CabinetLayout: React.FC<CabinetLayoutProps> = ({
  activeTab,
  navigate,
  isAuthenticated,
  publicId,
  onOpenAccount,
  children,
}) => {
  const { m, locale } = useI18n();
  const copy = m.cabinet;
  const gated = !isAuthenticated && GATED.includes(activeTab);

  return (
    <div className="w-full max-w-[1200px] mx-auto px-4 lg:px-8 py-8 flex flex-col gap-6" lang={sectionLang(locale, 'cabinet')}>
      <header className="flex flex-col gap-2 border-b border-[#e2e8f0] pb-5 md:flex-row md:items-end md:justify-between">
        <div className="flex flex-col gap-1">
          <h1 className="inline-flex items-center gap-2 font-['Inter'] text-3xl font-bold tracking-tight text-[#0b1c30]">
            <UserRound className="w-7 h-7 text-[#006194]" aria-hidden="true" />
            {copy.title}
          </h1>
          <p className="max-w-2xl text-base text-[#3f4850]">{copy.lead}</p>
        </div>
        {isAuthenticated && publicId && (
          <span className="self-start rounded-md border border-[#dce9ff] bg-[#eff4ff] px-3 py-1.5 font-['JetBrains_Mono'] text-sm text-[#0b1c30] md:self-auto">
            {fill(copy.publicId, { id: publicId })}
          </span>
        )}
      </header>

      <nav aria-label={copy.title}>
        <ul className="flex gap-1 overflow-x-auto pb-1">
          {CABINET_SECTIONS.map((section) => {
            const active = section.tab === activeTab;
            return (
              <li key={section.tab} className="shrink-0">
                <a
                  href={pathForTab(section.tab)}
                  aria-current={active ? 'page' : undefined}
                  onClick={(event) => {
                    event.preventDefault();
                    navigate(section.tab);
                  }}
                  className={`block whitespace-nowrap rounded-md px-3 py-2 text-[15px] font-medium transition-colors ${
                    active ? 'bg-[#006194] text-[#ffffff]' : 'text-[#3f4850] hover:bg-[#eff4ff] hover:text-[#0b1c30]'
                  }`}
                >
                  {copy.nav[section.key]}
                </a>
              </li>
            );
          })}
        </ul>
      </nav>

      {gated ? (
        <section className="rounded-xl border border-[#cbd5e1] bg-[#ffffff] p-6 flex flex-col gap-4 max-w-2xl">
          <h2 className="text-xl font-bold text-[#0b1c30]">{copy.gate.title}</h2>
          <p className="text-base text-[#3f4850]">{copy.gate.body}</p>
          <ul className="flex flex-col gap-2">
            {copy.gate.points.map((point) => (
              <li key={point} className="flex gap-2 text-base text-[#3f4850]">
                <span aria-hidden="true" className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[#006194]" />
                {point}
              </li>
            ))}
          </ul>
          <div className="flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              onClick={onOpenAccount}
              className="inline-flex items-center justify-center gap-2 rounded-md bg-[#006194] px-5 py-2.5 text-base font-semibold text-[#ffffff] hover:bg-[#004b73] cursor-pointer"
            >
              <LogIn className="w-5 h-5" aria-hidden="true" />
              {copy.gate.signIn}
            </button>
            <button
              type="button"
              onClick={onOpenAccount}
              className="rounded-md border border-[#cbd5e1] px-5 py-2.5 text-base font-semibold text-[#0b1c30] hover:bg-[#eff4ff] cursor-pointer"
            >
              {copy.gate.create}
            </button>
          </div>
        </section>
      ) : (
        <div className="min-w-0">{children}</div>
      )}
    </div>
  );
};
