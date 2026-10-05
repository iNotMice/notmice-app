import React from 'react';
import { BRAND_NAME, CONSENT_DOCUMENT_URL, LEVINE_2018_DOI_URL, TEAM_CONTACT_EMAIL } from '../config/site';
import { fill } from '../i18n/fill';
import { useI18n } from '../i18n/I18nProvider';
import { pathForTab, type SpecialistPage } from '../routes';
import { TabType } from '../types';

interface FooterProps {
  navigate: (tab: TabType, page?: SpecialistPage) => void;
}

export const Footer: React.FC<FooterProps> = ({ navigate }) => {
  const { m } = useI18n();
  const copy = m.shell;

  const internal = (label: string, tab: TabType, page?: SpecialistPage) => (
    <a
      href={`${pathForTab(tab)}${page ? `#${page}` : ''}`}
      onClick={(event) => {
        event.preventDefault();
        navigate(tab, page);
      }}
      className="hover:text-[#0b1c30] hover:underline"
    >
      {label}
    </a>
  );

  return (
    <footer className="w-full bg-[#ffffff] border-t border-[#e2e8f0] mt-auto">
      <div className="w-full max-w-[1200px] mx-auto px-4 lg:px-8 py-8 flex flex-col gap-5 text-[15px] text-[#3f4850]">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="flex flex-col gap-1 max-w-xl">
            <span className="text-base font-bold text-[#0b1c30]">{fill(copy.footerBrand, { brand: BRAND_NAME })}</span>
            <p>{copy.footerNonDiagnostic}</p>
          </div>
          <nav aria-label={fill(copy.footerBrand, { brand: BRAND_NAME })}>
            <ul className="flex flex-wrap gap-x-5 gap-y-2 font-medium">
              <li>{internal(copy.footerGuide, 'user-instructions')}</li>
              <li>{internal(copy.footerSpecialists, 'specialists')}</li>
              <li>{internal(copy.footerCharter, 'specialists', 'data')}</li>
              <li>
                <a href={CONSENT_DOCUMENT_URL} target="_blank" rel="noreferrer" className="hover:text-[#0b1c30] hover:underline">
                  {copy.footerConsent}
                </a>
              </li>
              {TEAM_CONTACT_EMAIL !== null && <li>{internal(copy.footerContact, 'specialists', 'contact')}</li>}
            </ul>
          </nav>
        </div>
        <div className="flex flex-col gap-1 border-t border-[#e2e8f0] pt-4 text-sm sm:flex-row sm:flex-wrap sm:gap-x-4">
          <span>{copy.footerNoRawFiles}</span>
          <span>
            {copy.footerLicensesTitle}: {copy.footerLicenses}
          </span>
          <a href={LEVINE_2018_DOI_URL} target="_blank" rel="noreferrer" className="hover:text-[#0b1c30] hover:underline">
            {copy.footerCitation}
          </a>
        </div>
      </div>
    </footer>
  );
};
