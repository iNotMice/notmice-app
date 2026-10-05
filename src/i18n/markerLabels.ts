import { PHENOAGE_BIOMARKERS } from '../data/phenoAgeData';
import { isBiomarkerId } from './biomarkerIds';
import type { AppMessages } from './messages/en';

/** Reader-facing name of a canonical marker id; unknown ids fall back to the id itself. */
export function markerLabel(canonicalId: string, m: AppMessages): string {
  if (isBiomarkerId(canonicalId)) {
    return m.biomarkers[canonicalId].name;
  }
  return m.cabinet.markerNames[canonicalId] ?? canonicalId;
}

/** Localized unit for the nine index markers when the stored unit is the dictionary one. */
export function markerUnit(canonicalId: string | null, unit: string, m: AppMessages): string {
  if (canonicalId && isBiomarkerId(canonicalId)) {
    const standard = PHENOAGE_BIOMARKERS.find((marker) => marker.id === canonicalId)?.standardUnit;
    if (standard === unit) {
      return m.biomarkers[canonicalId].unit;
    }
  }
  return unit;
}
