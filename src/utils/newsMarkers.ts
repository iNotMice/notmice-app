import { BIOMARKER_IDS, type BiomarkerId } from '../i18n/biomarkerIds';

/** Word patterns for the nine PhenoAge markers. Source text stays in its original language. */
const MARKER_PATTERNS: Record<BiomarkerId, RegExp> = {
  albumin: /\balbumin\b/i,
  creatinine: /\bcreatinine\b/i,
  glucose: /\b(?:glucose|glycaemia|glycemia)\b/i,
  crp: /\b(?:hs[-\s]?crp|crp|c[-\s]?reactive protein)\b/i,
  lymphocyte: /\blymphocytes?\b/i,
  mcv: /\b(?:mcv|mean corpuscular volume)\b/i,
  rdw: /\b(?:rdw|red cell distribution width)\b/i,
  alp: /\b(?:alp|alkaline phosphatase)\b/i,
  wbc: /\b(?:wbc|white blood cells?|leukocytes?)\b/i,
};

export function markerTags(title: string, snippet: string): BiomarkerId[] {
  const text = `${title}\n${snippet}`;
  return BIOMARKER_IDS.filter((id) => MARKER_PATTERNS[id].test(text));
}

export function cardMatchesPanel(
  tags: readonly string[],
  markerIds: readonly string[],
): boolean {
  if (markerIds.length === 0) {
    return false;
  }
  const mine = new Set(markerIds);
  return tags.some((id) => mine.has(id));
}
