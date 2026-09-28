import type { BiomarkerId } from '../../biomarkerIds';

/** Static marker notes. The same text for every account. */
export const lifestyleUi = {
  title: 'Marker cards',
  badge: 'Same for every account',
  lead: 'Prepared notes about the nine markers in the PhenoAge research index. The text does not change with your results.',
  interval:
    'On the chart, a result is compared with the reference interval printed on that laboratory report.',
  indexRole: 'One input of the Levine 2018 research index.',
  studyLabel: 'Research',
  studyCitation: 'Levine et al., Aging, 2018.',
  studyHref: 'https://doi.org/10.18632/aging.101414',
  disclaimerTitle: 'Note.',
  disclaimer:
    'A self-observation tool for research purposes. Not a medical diagnosis and not a substitute for a physician.',
  cards: {
    albumin:
      'Serum albumin is a protein measured in a blood sample. Laboratories report it in grams per litre.',
    creatinine:
      'Serum creatinine is measured in a blood sample. Laboratories often report it in milligrams per decilitre.',
    glucose:
      'Glucose on this panel is the fasting blood measurement. Laboratories often report it in milligrams per decilitre.',
    crp: 'C-reactive protein on this panel is the high-sensitivity blood measurement. Laboratories often report it in milligrams per litre.',
    lymphocyte:
      'Lymphocyte percent is the share of white blood cells counted as lymphocytes.',
    mcv: 'Mean corpuscular volume is the average volume of red blood cells. Laboratories report it in femtolitres.',
    rdw: 'Red cell distribution width describes how much red blood cell size varies. Laboratories report it as a percent.',
    alp: 'Alkaline phosphatase is an enzyme activity measured in a blood sample. Laboratories often report it in units per litre.',
    wbc: 'White blood cell count is the number of white cells in a blood sample. Laboratories often report it as thousands per microlitre.',
  } satisfies Record<BiomarkerId, string>,
};
