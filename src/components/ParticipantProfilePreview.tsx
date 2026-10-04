import type { SurveyCatalog } from '../api/survey';
import type { AppMessages } from '../i18n/messages/en';

type ProfileSurveyCopy = AppMessages['sovereignty']['profileSurvey'];

function SelectField({
  label,
  options,
  copy,
}: {
  label: string;
  options: string[];
  copy: ProfileSurveyCopy;
}) {
  return (
    <label className="block text-sm font-medium text-[#31465b]">
      {label}
      <select
        disabled
        defaultValue=""
        className="mt-1.5 block w-full rounded-lg border border-[#ccd8e3] bg-[#f6f8fa] px-3 py-2.5 text-sm text-[#526579] disabled:cursor-not-allowed"
      >
        <option value="">{copy.selectPlaceholder}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {copy.options[option as keyof typeof copy.options] ?? option}
          </option>
        ))}
      </select>
    </label>
  );
}

function NumberField({
  label,
  min,
  max,
  suffix,
}: {
  label: string;
  min: number;
  max: number;
  suffix?: string;
}) {
  return (
    <label className="block text-sm font-medium text-[#31465b]">
      {label}
      <span className="mt-1.5 flex items-center gap-2">
        <input
          type="number"
          min={min}
          max={max}
          disabled
          className="block w-full rounded-lg border border-[#ccd8e3] bg-[#f6f8fa] px-3 py-2.5 text-sm text-[#526579] disabled:cursor-not-allowed"
        />
        {suffix && <span className="shrink-0 text-xs text-[#8190a0]">{suffix}</span>}
      </span>
    </label>
  );
}

export function ParticipantProfilePreview({
  catalog,
  copy,
}: {
  catalog: SurveyCatalog;
  copy: ProfileSurveyCopy;
}) {
  return (
    <div className="mt-4 rounded-lg border border-[#e1e8ef] bg-[#fbfcfd] p-4">
      <p className="text-sm leading-6 text-[#607286]">{copy.previewIntro}</p>
      <fieldset disabled className="mt-4 grid gap-4 sm:grid-cols-2">
        <SelectField label={copy.sexAtBirth} options={catalog.sex_at_birth} copy={copy} />
        <NumberField label={copy.yearOfBirth} min={1900} max={2015} />
        <SelectField label={copy.country} options={catalog.countries} copy={copy} />
        <NumberField label={copy.height} min={100} max={250} suffix="cm" />
        <NumberField label={copy.weight} min={30} max={400} suffix="kg" />
        <SelectField label={copy.smoking} options={catalog.smoking} copy={copy} />
        <SelectField label={copy.alcohol} options={catalog.alcohol} copy={copy} />
        <SelectField label={copy.activity} options={catalog.activity} copy={copy} />
      </fieldset>
      <p className="mt-4 rounded-md bg-[#f1f5f8] p-3 text-xs leading-5 text-[#718398]">
        {copy.noFreeText}
      </p>
      <a
        href="/legal/consent-personal-research-2026-10-03.html"
        target="_blank"
        rel="noreferrer"
        className="mt-3 inline-block text-xs font-semibold text-[#006194] underline"
      >
        {copy.legalDocumentLink}
      </a>
    </div>
  );
}
