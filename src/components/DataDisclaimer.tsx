import React from 'react';
import { useI18n } from '../i18n/I18nProvider';

/** Section 3 notice: self-observation for research, not a diagnosis or a physician. */
export const DataDisclaimer: React.FC = () => {
  const { m } = useI18n();
  return (
    <p
      role="note"
      className="w-full bg-[#ffffff] border-b border-[#e2e8f0] px-4 lg:px-6 py-2"
    >
      <span className="max-w-[1440px] mx-auto block font-['Inter'] text-xs text-[#3f4850]">
        {m.shell.dataDisclaimer}
      </span>
    </p>
  );
};
