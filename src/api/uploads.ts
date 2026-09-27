/** Lab extract/confirm API client. Maps snake_case payloads to camelCase for the UI. */

import type { ExtractedMarker, TokenUsageNotice } from '../types';

export interface ExtractResult {
  extractToken: string;
  documentSha256: string;
  parserVersion: string;
  labName: string | null;
  collectedAt: string | null;
  chronologicalAge: number | null;
  markers: ExtractedMarker[];
  tokenUsage: TokenUsageNotice;
}

export class ExtractRequestError extends Error {
  readonly usage: TokenUsageNotice | null;

  constructor(message: string, usage: TokenUsageNotice | null) {
    super(message);
    this.name = 'ExtractRequestError';
    this.usage = usage;
  }
}

export interface OwnMarker {
  rawName: string;
  canonicalId: string | null;
  loincCode: string | null;
  value: number;
  unit: string;
  reportedValue: number | null;
  reportedUnit: string | null;
  referenceLow: number | null;
  referenceHigh: number | null;
  referenceText: string | null;
  labFlag: string | null;
}

export interface OwnLabResult {
  collectedAt: string | null;
  labName: string | null;
  chronologicalAge: number | null;
  confirmedAt: string;
  documentSha256: string;
  markers: OwnMarker[];
}

export interface ConfirmResult {
  labResultId: string;
  documentSha256: string;
  parserVersion: string;
  confirmedAt: string;
  markerCount: number;
}

interface ExtractedMarkerPayload {
  raw_name: string;
  canonical_id: string | null;
  loinc_code: string | null;
  value: number;
  unit: string;
  confidence: number;
  mapping_status: 'mapped' | 'unmapped';
  within_range: boolean | null;
  reported_value: number | null;
  reported_unit: string | null;
  reference_low: number | null;
  reference_high: number | null;
  reference_text: string | null;
  lab_flag: string | null;
}

interface ExtractPayload {
  extract_token: string;
  document_sha256: string;
  parser_version: string;
  lab_name: string | null;
  collected_at: string | null;
  chronological_age: number | null;
  markers: ExtractedMarkerPayload[];
  tokens_used: number;
  tokens_limit: number;
  warning: boolean;
}

interface OwnMarkerPayload {
  raw_name: string;
  canonical_id: string | null;
  loinc_code: string | null;
  value: number;
  unit: string;
  reported_value: number | null;
  reported_unit: string | null;
  reference_low: number | null;
  reference_high: number | null;
  reference_text: string | null;
  lab_flag: string | null;
}

interface OwnLabResultPayload {
  collected_at: string | null;
  lab_name: string | null;
  chronological_age: number | null;
  confirmed_at: string;
  document_sha256: string;
  markers: OwnMarkerPayload[];
}

interface OwnLabResultsPayload {
  results: OwnLabResultPayload[];
}

interface ConfirmPayload {
  lab_result_id: string;
  document_sha256: string;
  parser_version: string;
  confirmed_at: string;
  marker_count: number;
}

function apiUrl(path: string): string {
  const base = import.meta.env.VITE_API_BASE_URL ?? '';
  return `${base}${path}`;
}

function readTokenUsage(record: Record<string, unknown>, limitReached: boolean): TokenUsageNotice | null {
  if (typeof record.tokens_used !== 'number' || typeof record.tokens_limit !== 'number') {
    return null;
  }
  return {
    tokensUsed: record.tokens_used,
    tokensLimit: record.tokens_limit,
    warning: limitReached || record.warning === true,
    limitReached,
  };
}

async function readExtractFailure(response: Response): Promise<ExtractRequestError> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === 'object') {
      const record = body as Record<string, unknown>;
      const detail =
        typeof record.detail === 'string' ? record.detail : `Request failed (${response.status})`;
      return new ExtractRequestError(detail, readTokenUsage(record, response.status === 429));
    }
  } catch {
    // Fall through to status text.
  }
  return new ExtractRequestError(`Request failed (${response.status})`, null);
}

async function readError(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === 'object' && 'detail' in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === 'string') {
        return detail;
      }
    }
  } catch {
    // Fall through to status text.
  }
  return `Request failed (${response.status})`;
}

function mapMarker(payload: ExtractedMarkerPayload): ExtractedMarker {
  return {
    rawName: payload.raw_name,
    canonicalId: payload.canonical_id,
    loincCode: payload.loinc_code,
    value: payload.value,
    unit: payload.unit,
    confidence: payload.confidence,
    mappingStatus: payload.mapping_status,
    withinRange: payload.within_range,
    reportedValue: payload.reported_value,
    reportedUnit: payload.reported_unit,
    referenceLow: payload.reference_low,
    referenceHigh: payload.reference_high,
    referenceText: payload.reference_text,
    labFlag: payload.lab_flag,
  };
}

export async function extractLabFile(token: string, file: File): Promise<ExtractResult> {
  const body = new FormData();
  body.append('file', file);
  const response = await fetch(apiUrl('/api/v1/uploads/extract'), {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body,
  });
  if (!response.ok) {
    throw await readExtractFailure(response);
  }
  const payload = (await response.json()) as ExtractPayload;
  return {
    extractToken: payload.extract_token,
    documentSha256: payload.document_sha256,
    parserVersion: payload.parser_version,
    labName: payload.lab_name,
    collectedAt: payload.collected_at,
    chronologicalAge: payload.chronological_age,
    markers: payload.markers.map(mapMarker),
    tokenUsage: {
      tokensUsed: payload.tokens_used,
      tokensLimit: payload.tokens_limit,
      warning: payload.warning,
    },
  };
}

export async function fetchOwnLabResults(token: string): Promise<OwnLabResult[]> {
  const response = await fetch(apiUrl('/api/v1/uploads/results'), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  const payload = (await response.json()) as OwnLabResultsPayload;
  return payload.results.map((panel) => ({
    collectedAt: panel.collected_at,
    labName: panel.lab_name,
    chronologicalAge: panel.chronological_age,
    confirmedAt: panel.confirmed_at,
    documentSha256: panel.document_sha256,
    markers: panel.markers.map((marker) => ({
      rawName: marker.raw_name,
      canonicalId: marker.canonical_id,
      loincCode: marker.loinc_code,
      value: marker.value,
      unit: marker.unit,
      reportedValue: marker.reported_value,
      reportedUnit: marker.reported_unit,
      referenceLow: marker.reference_low,
      referenceHigh: marker.reference_high,
      referenceText: marker.reference_text,
      labFlag: marker.lab_flag,
    })),
  }));
}

export async function deleteOwnLabResults(token: string): Promise<void> {
  const response = await fetch(apiUrl('/api/v1/uploads/results'), {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new Error('Could not delete saved panels');
  }
}

export async function confirmLabExtraction(
  token: string,
  input: {
    extractToken: string;
    labName: string | null;
    collectedAt: string | null;
    chronologicalAge: number | null;
    markers: {
      rawName: string;
      value: number;
      unit: string;
      reportedValue?: number | null;
      reportedUnit?: string | null;
      referenceLow?: number | null;
      referenceHigh?: number | null;
      referenceText?: string | null;
      labFlag?: string | null;
    }[];
  }
): Promise<ConfirmResult> {
  const response = await fetch(apiUrl('/api/v1/uploads/confirm'), {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      extract_token: input.extractToken,
      lab_name: input.labName,
      collected_at: input.collectedAt,
      chronological_age: input.chronologicalAge,
      markers: input.markers.map((marker) => ({
        raw_name: marker.rawName,
        value: marker.value,
        unit: marker.unit,
        reported_value: marker.reportedValue ?? null,
        reported_unit: marker.reportedUnit ?? null,
        reference_low: marker.referenceLow ?? null,
        reference_high: marker.referenceHigh ?? null,
        reference_text: marker.referenceText ?? null,
        lab_flag: marker.labFlag ?? null,
      })),
    }),
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  const payload = (await response.json()) as ConfirmPayload;
  return {
    labResultId: payload.lab_result_id,
    documentSha256: payload.document_sha256,
    parserVersion: payload.parser_version,
    confirmedAt: payload.confirmed_at,
    markerCount: payload.marker_count,
  };
}
