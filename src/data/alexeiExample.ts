/**
 * The one worked example on the site: Alexei, a fictional 45-year-old.
 *
 * Values are in the LOINC dictionary units the PhenoAge API accepts.
 * The production engine (app/services/phenoage.py) scores them as
 * 51.31 at the start and 46.97 four months later.
 * app/tests/test_alexei_example.py pins both numbers.
 */

export type ExampleSnapshot = {
  chronologicalAge: number;
  biomarkers: Record<string, number>;
  /** Engine result, rounded to one decimal, for copy that cannot wait for the API. */
  phenoAge: number;
};

export const ALEXEI_START: ExampleSnapshot = {
  chronologicalAge: 45.0,
  biomarkers: {
    albumin: 42.0,
    creatinine: 1.2,
    glucose: 104.0,
    crp: 7.0,
    lymphocyte: 23.0,
    mcv: 92.0,
    rdw: 14.0,
    alp: 80.0,
    wbc: 7.4,
  },
  phenoAge: 51.3,
};

export const ALEXEI_FOLLOW_UP: ExampleSnapshot = {
  chronologicalAge: 45.3,
  biomarkers: {
    albumin: 43.0,
    creatinine: 1.12,
    glucose: 99.0,
    crp: 3.0,
    lymphocyte: 26.0,
    mcv: 92.0,
    rdw: 13.7,
    alp: 74.0,
    wbc: 6.8,
  },
  phenoAge: 47.0,
};
