import React, { useEffect, useMemo, useState } from 'react';
import type { SurveyCatalog } from '../api/survey';
import {
  ProfileRequestError,
  deleteProfile,
  fetchProfile,
  saveProfile,
  type ParticipantProfile,
} from '../api/survey';
import type { AppMessages } from '../i18n/messages/en';
import { useI18n } from '../i18n/I18nProvider';
import { CONSENT_DOCUMENT_URL } from '../config/site';

type ProfileSurveyCopy = AppMessages['sovereignty']['profileSurvey'];

type Draft = {
  sex_at_birth: string;
  year_of_birth: string;
  country: string;
  height_cm: string;
  weight_kg: string;
  smoking: string;
  alcohol: string;
  activity: string;
};

const EMPTY: Draft = {
  sex_at_birth: '',
  year_of_birth: '',
  country: '',
  height_cm: '',
  weight_kg: '',
  smoking: '',
  alcohol: '',
  activity: '',
};

function toDraft(profile: ParticipantProfile | null): Draft {
  if (!profile) {
    return EMPTY;
  }
  const text = (value: unknown) => (value === null || value === undefined ? '' : String(value));
  return {
    sex_at_birth: text(profile.sex_at_birth),
    year_of_birth: text(profile.year_of_birth),
    country: text(profile.country),
    height_cm: text(profile.height_cm),
    weight_kg: profile.weight_kg === null ? '' : String(Number(profile.weight_kg)),
    smoking: text(profile.smoking),
    alcohol: text(profile.alcohol),
    activity: text(profile.activity),
  };
}

const field =
  'mt-1.5 block w-full rounded-lg border border-[#ccd8e3] bg-[#ffffff] px-3 py-2.5 text-[15px] text-[#0b1c30] focus:border-[#006194] focus:outline-none focus:ring-2 focus:ring-[#006194]/20';

interface ParticipantProfileFormProps {
  catalog: SurveyCatalog;
  copy: ProfileSurveyCopy;
}

/**
 * The optional questionnaire, editable once collection is on and the
 * profile consent is active. Answers are controlled choices and bounded numbers only.
 */
export const ParticipantProfileForm: React.FC<ParticipantProfileFormProps> = ({ catalog, copy }) => {
  const { locale } = useI18n();
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [hasSaved, setHasSaved] = useState(false);

  const regionNames = useMemo(() => {
    try {
      return new Intl.DisplayNames([locale], { type: 'region' });
    } catch {
      return null;
    }
  }, [locale]);
  const countries = useMemo(
    () =>
      [...catalog.countries]
        .map((code) => ({ code, name: regionNames?.of(code) ?? code }))
        .sort((a, b) => a.name.localeCompare(b.name, locale)),
    [catalog.countries, regionNames, locale],
  );

  useEffect(() => {
    const controller = new AbortController();
    void fetchProfile(controller.signal)
      .then((profile) => {
        setDraft(toDraft(profile));
        setHasSaved(profile !== null);
        setLoaded(true);
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') {
          return;
        }
        setLoaded(true);
        setMessage({ ok: false, text: copy.loadFailed });
      });
    return () => controller.abort();
  }, [copy.loadFailed]);

  const set = (key: keyof Draft) => (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setDraft((current) => ({ ...current, [key]: event.target.value }));

  const number = (value: string): number | null => {
    const trimmed = value.trim().replace(',', '.');
    return trimmed === '' ? null : Number(trimmed);
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setMessage(null);
    const year = number(draft.year_of_birth);
    const height = number(draft.height_cm);
    const weight = number(draft.weight_kg);
    if (
      (year !== null && (!Number.isInteger(year) || year < 1900 || year > 2015)) ||
      (height !== null && (!Number.isInteger(height) || height < 100 || height > 250)) ||
      (weight !== null && (Number.isNaN(weight) || weight < 30 || weight > 400))
    ) {
      setMessage({ ok: false, text: copy.outOfRange });
      return;
    }
    setBusy(true);
    try {
      const saved = await saveProfile({
        sex_at_birth: draft.sex_at_birth || null,
        year_of_birth: year,
        country: draft.country || null,
        height_cm: height,
        weight_kg: weight,
        smoking: draft.smoking || null,
        alcohol: draft.alcohol || null,
        activity: draft.activity || null,
        conditions: [],
      });
      setDraft(toDraft(saved));
      setHasSaved(true);
      setMessage({ ok: true, text: copy.saved });
    } catch (err) {
      const status = err instanceof ProfileRequestError ? err.status : 0;
      setMessage({ ok: false, text: status === 403 ? copy.needConsent : status === 422 ? copy.outOfRange : copy.saveFailed });
    } finally {
      setBusy(false);
    }
  };

  const clear = async () => {
    if (!window.confirm(copy.clearConfirm)) {
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      await deleteProfile();
      setDraft(EMPTY);
      setHasSaved(false);
      setMessage({ ok: true, text: copy.cleared });
    } catch {
      setMessage({ ok: false, text: copy.saveFailed });
    } finally {
      setBusy(false);
    }
  };

  const select = (key: keyof Draft, label: string, options: string[]) => (
    <label className="block text-sm font-medium text-[#31465b]">
      {label}
      <select value={draft[key]} onChange={set(key)} className={field}>
        <option value="">{copy.selectPlaceholder}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {copy.options[option as keyof typeof copy.options] ?? option}
          </option>
        ))}
      </select>
    </label>
  );

  const numeric = (key: keyof Draft, label: string, min: number, max: number, suffix?: string, step = 1) => (
    <label className="block text-sm font-medium text-[#31465b]">
      {label}
      <span className="flex items-center gap-2">
        <input
          type="number"
          inputMode="decimal"
          min={min}
          max={max}
          step={step}
          value={draft[key]}
          onChange={set(key)}
          className={field}
        />
        {suffix && <span className="mt-1.5 shrink-0 text-sm text-[#3f4850]">{suffix}</span>}
      </span>
    </label>
  );

  if (!loaded) {
    return <p className="text-sm text-[#3f4850]">{copy.loading}</p>;
  }

  return (
    <form className="mt-2 flex flex-col gap-4" onSubmit={(event) => void submit(event)} noValidate>
      <p className="text-sm leading-6 text-[#3f4850]">{copy.formIntro}</p>
      <div className="grid gap-4 sm:grid-cols-2">
        {select('sex_at_birth', copy.sexAtBirth, catalog.sex_at_birth)}
        {numeric('year_of_birth', copy.yearOfBirth, 1900, 2015)}
        <label className="block text-sm font-medium text-[#31465b]">
          {copy.country}
          <select value={draft.country} onChange={set('country')} className={field}>
            <option value="">{copy.selectPlaceholder}</option>
            {countries.map((country) => (
              <option key={country.code} value={country.code}>
                {country.name}
              </option>
            ))}
          </select>
        </label>
        {numeric('height_cm', copy.height, 100, 250, copy.cm)}
        {numeric('weight_kg', copy.weight, 30, 400, copy.kg, 0.1)}
        {select('smoking', copy.smoking, catalog.smoking)}
        {select('alcohol', copy.alcohol, catalog.alcohol)}
        {select('activity', copy.activity, catalog.activity)}
      </div>
      <p className="rounded-md bg-[#f1f5f8] p-3 text-sm leading-5 text-[#3f4850]">{copy.noFreeText}</p>
      {message && (
        <p className={`text-[15px] ${message.ok ? 'text-[#006947]' : 'text-[#ba1a1a]'}`} role={message.ok ? 'status' : 'alert'}>
          {message.text}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-[#006194] px-5 py-2.5 text-[15px] font-semibold text-[#ffffff] hover:bg-[#004b73] disabled:opacity-60 cursor-pointer"
        >
          {busy ? copy.saving : copy.save}
        </button>
        {hasSaved && (
          <button
            type="button"
            disabled={busy}
            onClick={() => void clear()}
            className="rounded-md border border-[#fecdd3] bg-[#fff1f2] px-4 py-2.5 text-[15px] font-semibold text-[#ba1a1a] hover:bg-[#ffe4e6] disabled:opacity-60 cursor-pointer"
          >
            {copy.clear}
          </button>
        )}
        <a href={CONSENT_DOCUMENT_URL} target="_blank" rel="noreferrer" className="text-sm font-semibold text-[#006194] underline">
          {copy.legalDocumentLink}
        </a>
      </div>
    </form>
  );
};
