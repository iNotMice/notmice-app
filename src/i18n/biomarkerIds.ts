export const BIOMARKER_IDS = [
  'albumin',
  'creatinine',
  'glucose',
  'crp',
  'lymphocyte',
  'mcv',
  'rdw',
  'alp',
  'wbc',
] as const;

export type BiomarkerId = (typeof BIOMARKER_IDS)[number];

export type BiomarkerCopy = {
  name: string;
  shortName: string;
  /** Unit as shown to a reader in this language. */
  unit: string;
  domain: string;
  risk: string;
  weight: string;
};

export type BiomarkerCopyMap = Record<BiomarkerId, BiomarkerCopy>;

export function isBiomarkerId(value: string): value is BiomarkerId {
  return (BIOMARKER_IDS as readonly string[]).includes(value);
}
