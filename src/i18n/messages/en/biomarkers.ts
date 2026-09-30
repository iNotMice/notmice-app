import type { BiomarkerCopyMap } from '../../biomarkerIds';

export const biomarkers: BiomarkerCopyMap = {
  albumin: {
    name: 'Serum Albumin',
    shortName: 'Albumin',
    domain: 'Hepatic / Nutritional Synthesis',
    risk: 'Research index input',
    weight: 'Serum albumin is a protein measured in a blood sample. Laboratories report it in grams per litre.',
  },
  creatinine: {
    name: 'Serum Creatinine',
    shortName: 'Creatinine',
    domain: 'Renal Filtration Efficiency',
    risk: 'Research index input',
    weight: 'Serum creatinine is measured in a blood sample. Laboratories often report it in milligrams per decilitre.',
  },
  glucose: {
    name: 'Fasting Serum Glucose',
    shortName: 'Fasting Glucose',
    domain: 'Metabolic / Insulin Sensitivity',
    risk: 'Research index input',
    weight: 'Glucose on this panel is the fasting blood measurement. Laboratories often report it in milligrams per decilitre.',
  },
  crp: {
    name: 'hs-C-Reactive Protein',
    shortName: 'hs-CRP',
    domain: 'Systemic Sterile Inflammation',
    risk: 'Research index input',
    weight: 'C-reactive protein on this panel is the high-sensitivity blood measurement. Laboratories often report it in milligrams per litre.',
  },
  lymphocyte: {
    name: 'Lymphocyte Percentage',
    shortName: 'Lymphocytes',
    domain: 'Immunosenescence Balance',
    risk: 'Research index input',
    weight: 'Lymphocyte percent is the share of white blood cells counted as lymphocytes.',
  },
  mcv: {
    name: 'Mean Corpuscular Volume (MCV)',
    shortName: 'MCV',
    domain: 'Hematology & Methylation',
    risk: 'Research index input',
    weight: 'Mean corpuscular volume is the average volume of red blood cells. Laboratories report it in femtolitres.',
  },
  rdw: {
    name: 'Red Cell Distribution Width (RDW)',
    shortName: 'RDW',
    domain: 'Erythrocyte Turnover / Frailty',
    risk: 'Research index input',
    weight: 'Red cell distribution width describes how much red blood cell size varies. Laboratories report it as a percent.',
  },
  alp: {
    name: 'Alkaline Phosphatase (ALP)',
    shortName: 'Alk Phos',
    domain: 'Biliary / Bone Mineralization',
    risk: 'Research index input',
    weight: 'Alkaline phosphatase is an enzyme activity measured in a blood sample. Laboratories often report it in units per litre.',
  },
  wbc: {
    name: 'White Blood Cell Count (WBC)',
    shortName: 'WBC',
    domain: 'Innate Immune Activation',
    risk: 'Research index input',
    weight: 'White blood cell count is the number of white cells in a blood sample. Laboratories often report it as thousands per microlitre.',
  },
};
