export type TabType = 
  | 'overview-landing'
  | 'upload-lab'
  | 'review-extraction'
  | 'phenoage-engine'
  | 'biomarker-history'
  | 'data-sovereignty-public-sharing'
  | 'research-news'
  | 'user-instructions';

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
  mortalityScore10yr: number; // percentage
  percentileRank: number; // against NHANES cohort
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

export interface HistoricalTestRecord {
  id: string;
  date: string;
  /** Specimen date from the laboratory report. Null when the report did not state one. */
  collectedAt: string | null;
  chronologicalAge: number;
  phenoAge: number;
  delta: number;
  labSource: string;
  biomarkers: Record<string, number>;
  /** SHA-256 of a confirmed laboratory file. Empty for a session-only engine snapshot. */
  hash: string;
  /** Canonical marker ids from the panel. Not the full default biomarker map. */
  markerIds: string[];
  /** Every analyte row on the upload, including names the dictionary did not map. */
  markerCount: number;
  /** True when the row exists only in this browser session and is not stored on the account. */
  sessionOnly: boolean;
}

export interface AccountState {
  publicId: string;
  isPublic: boolean;
  createdAt: string;
}
