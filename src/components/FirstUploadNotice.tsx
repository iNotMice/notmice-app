import React, { useEffect, useRef } from 'react';
import { Info } from 'lucide-react';
import { useI18n } from '../i18n/I18nProvider';
import { sectionLang } from '../i18n/locales';

const SEEN_KEY = 'notmice.firstUploadNoticeSeen';

export function firstUploadNoticeSeen(): boolean {
  try {
    return localStorage.getItem(SEEN_KEY) === '1';
  } catch {
    return false;
  }
}

function markSeen(): void {
  try {
    localStorage.setItem(SEEN_KEY, '1');
  } catch {
    // Storage can be blocked; the notice closes for this visit only.
  }
}

interface FirstUploadNoticeProps {
  onClose: () => void;
  onOpenGuide: () => void;
}

/**
 * Three-point summary of the guide before the first upload.
 * It informs only; consents keep their own screens and logic.
 */
export const FirstUploadNotice: React.FC<FirstUploadNoticeProps> = ({ onClose, onOpenGuide }) => {
  const { m, locale } = useI18n();
  const copy = m.instructions.firstUpload;
  const okRef = useRef<HTMLButtonElement>(null);

  const close = () => {
    markSeen();
    onClose();
  };

  useEffect(() => {
    okRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        markSeen();
        onClose();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-[#0b1c30]/50 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="first-upload-title"
        lang={sectionLang(locale, 'instructions')}
        className="w-full max-w-lg rounded-2xl bg-[#ffffff] p-6 shadow-xl flex flex-col gap-4"
      >
        <h2 id="first-upload-title" className="inline-flex items-center gap-2 text-xl font-bold text-[#0b1c30]">
          <Info className="w-5 h-5 text-[#006194]" aria-hidden="true" />
          {copy.title}
        </h2>
        <ol className="flex flex-col gap-3">
          {copy.points.map((point, index) => (
            <li key={point} className="flex gap-3 text-base leading-relaxed text-[#3f4850]">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#eff4ff] text-sm font-bold text-[#006194]">
                {index + 1}
              </span>
              {point}
            </li>
          ))}
        </ol>
        <p className="text-sm text-[#3f4850]">{copy.note}</p>
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={() => {
              markSeen();
              onOpenGuide();
            }}
            className="rounded-md border border-[#cbd5e1] px-4 py-2.5 text-base font-semibold text-[#0b1c30] hover:bg-[#eff4ff] cursor-pointer"
          >
            {copy.readGuide}
          </button>
          <button
            ref={okRef}
            type="button"
            onClick={close}
            className="rounded-md bg-[#006194] px-5 py-2.5 text-base font-semibold text-[#ffffff] hover:bg-[#004b73] cursor-pointer"
          >
            {copy.ok}
          </button>
        </div>
      </div>
    </div>
  );
};
