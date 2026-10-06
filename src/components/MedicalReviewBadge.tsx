import React from 'react';
import { BadgeCheck } from 'lucide-react';
import { MEDICAL_REVIEW } from '../config/site';
import { fill } from '../i18n/fill';
import { useI18n } from '../i18n/I18nProvider';

/** Named medical review line. Renders nothing until a reviewer is configured. */
export const MedicalReviewBadge: React.FC = () => {
  const { m } = useI18n();
  if (!MEDICAL_REVIEW) {
    return null;
  }
  return (
    <p className="inline-flex items-center gap-2 rounded-md border border-[#b7e4cf] bg-[#effaf5] px-3 py-1.5 text-sm text-[#004f35]">
      <BadgeCheck className="w-4 h-4 shrink-0" aria-hidden="true" />
      {fill(m.specialists.reviewBadge, MEDICAL_REVIEW)}
    </p>
  );
};
