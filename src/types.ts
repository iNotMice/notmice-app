export type TabType = 
  | 'overview-landing'
  | 'upload-lab'
  | 'review-extraction'
  | 'phenoage-engine'
  | 'biomarker-history'
  | 'protocol-journal'
  | 'data-sovereignty-public-sharing'
  | 'research-news'
  | 'user-instructions'
  | 'specialists'
  | 'cabinet'
  | 'cabinet-tests'
  | 'cabinet-security';

export interface BiomarkerDefinition {
  id: string;
  name: string;
  loinc: string;
  domain: string;
  unit: string;
  standardUnit: string;
  optimalRange: [number, number];
  clinicalRange: [number, number];
  riskInfluence: 'Positive (Accelerant)' | 'Negative (Protective)' | 'Heavy Positive';
  weightDescription: string;
  levineCoeff: number;
  step: number;
}

export interface TokenUsageNotice {
  tokensUsed: number;
  tokensLimit: number;
  warning: boolean;
  limitReached?: boolean;
}

export interface LabPanelData {
  id: string;
  labName: string;
  testDate: string;
  sourceType: 'pdf' | 'manual' | 'demo';
  fileName?: string;
  chronologicalAge: number;
  gender: 'male' | 'female';
  biomarkers: Record<string, number>;
  confidenceScores: Record<string, number>;
  verified: boolean;
  hash: string;
  /** Canonical marker ids that belong to this panel. Empty on the tutorial example. */
  focusMarkerIds: string[];
  extractToken?: string;
  parserVersion?: string;
  extractedMarkers?: ExtractedMarker[];
  tokenUsage?: TokenUsageNotice;
}

export interface ExtractedMarker {
  rawName: string;
  canonicalId: string | null;
  loincCode: string | null;
  value: number;
  unit: string;
  confidence: number;
  mappingStatus: 'mapped' | 'unmapped';
  withinRange: boolean | null;
  reportedValue: number | null;
  reportedUnit: string | null;
  referenceLow: number | null;
  referenceHigh: number | null;
  referenceText: string | null;
  labFlag: string | null;
}

export interface PhenoAgeCalculation {
  chronologicalAge: number;
  phenoAge: number;
  ageDelta: number; // phenoAge - chronologicalAge
  biomarkerScores: {
    id: string;
    name: string;
    value: number;
    unit: string;
    contribution: number; // positive = aging accelerant, negative = decelerant
    status: 'optimal' | 'normal' | 'borderline' | 'elevated';
  }[];
  isValid: boolean;
  activeCount: number;
  disclaimer: string;
}

/** Printed laboratory interval for one analyte on one confirmed panel. */
export interface PrintedLabInterval {
  referenceLow: number | null;
  referenceHigh: number | null;
  referenceText: string | null;
  labFlag: string | null;
  /** True only outside the printed interval, or when the laboratory marked H, L, or *. */
  outsideInterval: boolean;
}

export interface HistoricalTestRecord {
  id: string;
  date: string;
  /** Specimen date from the laboratory report. Null when the report did not state one. */
  collectedAt: string | null;
  /** Null when the report did not state an age. The trend does not invent one. */
  chronologicalAge: number | null;
  /** Null when a Levine marker or the age is missing, or the value cannot be scored. */
  phenoAge: number | null;
  /** Index minus calendar age. Null on the same panels as ``phenoAge``. */
  delta: number | null;
  labSource: string;
  biomarkers: Record<string, number>;
  /** Unit returned for each canonical marker; comparable values must have identical units. */
  biomarkerUnits: Record<string, string>;
  /** SHA-256 of a confirmed laboratory file. Empty for a session-only engine snapshot. */
  hash: string;
  /** Canonical marker ids from the panel. Not the full default biomarker map. */
  markerIds: string[];
  /** Printed interval keyed by canonical marker id. Empty for a session snapshot. */
  printedIntervals: Record<string, PrintedLabInterval>;
  /** Every analyte row on the upload, including names the dictionary did not map. */
  markerCount: number;
  /** True when the row exists only in this browser session and is not stored on the account. */
  sessionOnly: boolean;
  /** Levine marker ids absent from this panel, in dictionary order. */
  missingMarkers: string[];
}

export interface AccountState {
  publicId: string;
  isPublic: boolean;
  createdAt: string;
}
