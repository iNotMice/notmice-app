/** PhenoAge API client. The Levine formula stays on the server. */

export interface PhenoAgeScore {
  chronologicalAge: number;
  phenoAge: number;
  ageDelta: number;
  disclaimer: string;
}

interface PhenoAgePayload {
  chronological_age: number;
  pheno_age: number;
  age_delta: number;
  disclaimer: string;
}

function apiUrl(path: string): string {
  const base = import.meta.env.VITE_API_BASE_URL ?? '';
  return `${base}${path}`;
}

export async function fetchPhenoAge(
  chronologicalAge: number,
  biomarkers: Record<string, number>,
  signal?: AbortSignal,
): Promise<PhenoAgeScore> {
  const response = await fetch(apiUrl('/api/v1/phenoage'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chronological_age: chronologicalAge,
      markers: {
        albumin: biomarkers.albumin,
        creatinine: biomarkers.creatinine,
        glucose: biomarkers.glucose,
        crp: biomarkers.crp,
        lymphocyte: biomarkers.lymphocyte,
        mcv: biomarkers.mcv,
        rdw: biomarkers.rdw,
        alp: biomarkers.alp,
        wbc: biomarkers.wbc,
      },
    }),
    signal,
  });
  if (!response.ok) {
    throw new Error(`PhenoAge request failed (${response.status})`);
  }
  const payload = (await response.json()) as PhenoAgePayload;
  return {
    chronologicalAge: payload.chronological_age,
    phenoAge: payload.pheno_age,
    ageDelta: payload.age_delta,
    disclaimer: payload.disclaimer,
  };
}
