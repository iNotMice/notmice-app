import { isBiomarkerId, type BiomarkerCopyMap } from '../i18n/biomarkerIds';
import type { HistoricalTestRecord } from '../types';

export function shortMarkerName(id: string, biomarkers: BiomarkerCopyMap): string {
  return isBiomarkerId(id) ? biomarkers[id].shortName : id;
}

export function missingMarkerText(
  record: HistoricalTestRecord,
  biomarkers: BiomarkerCopyMap,
): string {
  return record.missingMarkers.map((id) => shortMarkerName(id, biomarkers)).join(', ');
}

export function scoredRecords(history: HistoricalTestRecord[]): HistoricalTestRecord[] {
  return history
    .filter(
      (record) =>
        !record.sessionOnly && record.phenoAge !== null && record.chronologicalAge !== null,
    )
    .slice()
    .sort((left, right) => left.date.localeCompare(right.date));
}
