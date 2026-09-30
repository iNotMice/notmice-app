import { PHENOAGE_BIOMARKERS } from '../data/phenoAgeData';
import { PhenoAgeCalculation } from '../types';

/** Slider annotations for the scoreboard. The phenotypic age itself comes from the API. */
export function displayBiomarkerScores(
  biomarkers: Record<string, number>,
): PhenoAgeCalculation['biomarkerScores'] {
  return PHENOAGE_BIOMARKERS.map((bio) => {
    const rawVal = biomarkers[bio.id] ?? bio.optimalRange[0];
    let val = rawVal;
    let contribution = 0;

    if (bio.id === 'albumin') {
      const std = val < 10 ? val * 10 : val;
      contribution = (45.0 - std) * 0.4;
    } else if (bio.id === 'crp') {
      contribution = (val - 0.8) * 1.1;
    } else if (bio.id === 'glucose') {
      contribution = (val - 82.0) * 0.08;
    } else if (bio.id === 'rdw') {
      contribution = (val - 12.0) * 1.8;
    } else if (bio.id === 'creatinine') {
      contribution = (val - 0.85) * 4.2;
    } else if (bio.id === 'lymphocyte') {
      contribution = (35.0 - val) * 0.15;
    } else if (bio.id === 'mcv') {
      contribution = (val - 88.0) * 0.25;
    } else if (bio.id === 'alp') {
      contribution = (val - 55.0) * 0.03;
    } else if (bio.id === 'wbc') {
      contribution = (val - 5.0) * 0.6;
    }

    let status: 'optimal' | 'normal' | 'borderline' | 'elevated' = 'normal';
    if (val >= bio.optimalRange[0] && val <= bio.optimalRange[1]) {
      status = 'optimal';
    } else if (val >= bio.clinicalRange[0] && val <= bio.clinicalRange[1]) {
      status = 'normal';
    } else if (bio.riskInfluence.includes('Positive') && val > bio.clinicalRange[1]) {
      status = 'elevated';
    } else {
      status = 'borderline';
    }

    return {
      id: bio.id,
      name: bio.name,
      value: val,
      unit: bio.unit,
      contribution: Math.round(contribution * 10) / 10,
      status,
    };
  });
}
