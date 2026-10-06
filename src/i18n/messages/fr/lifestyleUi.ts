import type { BiomarkerId } from '../../biomarkerIds';

/** Static marker notes. The same text for every account. */
export const lifestyleUi = {
  title: 'Fiches des marqueurs',
  badge: 'Identiques pour tous',
  lead: 'Notes sur les neuf marqueurs de l’indice de recherche PhenoAge. Le texte ne dépend pas de vos résultats.',
  interval:
    'Sur le graphique, un résultat est comparé à l’intervalle de référence imprimé sur le compte rendu du laboratoire.',
  indexRole: 'L’un des marqueurs de l’indice de Levine 2018.',
  studyLabel: 'Étude',
  studyCitation: 'Levine et al., Aging, 2018.',
  studyHref: 'https://doi.org/10.18632/aging.101414',
  cards: {
    albumin:
      'L’albumine est une protéine du sang produite par le foie. Les laboratoires l’expriment en grammes par litre (g/l).',
    creatinine:
      'La créatinine est mesurée dans le sang et renseigne sur le fonctionnement des reins. Elle est exprimée en µmol/l ou en mg/dl.',
    glucose:
      'La glycémie de ce bilan est le taux de sucre dans le sang à jeun. Elle est exprimée en mmol/l ou en mg/dl.',
    crp: 'La protéine C réactive (CRP) reflète l’inflammation. Il faut le dosage ultrasensible (CRP us), exprimé en mg/l.',
    lymphocyte:
      'Lymphocytes, % : part des lymphocytes parmi tous les globules blancs. Figure dans la numération formule sanguine.',
    mcv: 'Le volume globulaire moyen (VGM) est la taille moyenne des globules rouges, exprimée en femtolitres (fl).',
    rdw: 'L’indice de distribution des globules rouges (IDR) montre à quel point leur taille varie. Il est exprimé en pourcentage.',
    alp: 'Les phosphatases alcalines (PAL) sont des enzymes liées au foie, aux voies biliaires et aux os. Elles sont exprimées en UI/l.',
    wbc: 'Les leucocytes sont les globules blancs. Ils sont exprimés en G/l (10⁹/l), soit des milliers par microlitre.',
  } satisfies Record<BiomarkerId, string>,
};
