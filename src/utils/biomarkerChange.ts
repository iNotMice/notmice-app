export interface BiomarkerMeasurement {
  date: string;
  lab: string;
  value: number;
  unit: string;
}

export type BiomarkerChange =
  | { kind: 'insufficient'; latest: BiomarkerMeasurement | null }
  | { kind: 'unit-mismatch'; latest: BiomarkerMeasurement; previous: BiomarkerMeasurement }
  | {
      kind: 'compared';
      latest: BiomarkerMeasurement;
      previous: BiomarkerMeasurement;
      difference: number;
    };

export function summarizeLatestChange(measurements: BiomarkerMeasurement[]): BiomarkerChange {
  const ordered = measurements
    .filter(
      (measurement) =>
        Number.isFinite(measurement.value) &&
        measurement.date.length > 0 &&
        measurement.unit.trim().length > 0,
    )
    .slice()
    .sort((left, right) => left.date.localeCompare(right.date));
  const latest = ordered[ordered.length - 1] ?? null;
  const previous = ordered[ordered.length - 2] ?? null;

  if (!latest || !previous) {
    return { kind: 'insufficient', latest };
  }
  if (latest.unit !== previous.unit) {
    return { kind: 'unit-mismatch', latest, previous };
  }
  return {
    kind: 'compared',
    latest,
    previous,
    difference: latest.value - previous.value,
  };
}
