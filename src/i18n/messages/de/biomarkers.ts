import type { BiomarkerCopyMap } from '../../biomarkerIds';

export const biomarkers: BiomarkerCopyMap = {
  albumin: {
    name: 'Serumalbumin',
    shortName: 'Albumin',
    domain: 'Hepatische / nutritive Synthese',
    risk: 'Eingabe des Forschungsindex',
    weight: 'Serumalbumin ist ein Protein, das in einer Blutprobe gemessen wird. Labore geben es in Gramm pro Liter an.',
  },
  creatinine: {
    name: 'Serumkreatinin',
    shortName: 'Kreatinin',
    domain: 'Renale Filtration',
    risk: 'Eingabe des Forschungsindex',
    weight: 'Serumkreatinin wird in einer Blutprobe gemessen. Labore geben es oft in Milligramm pro Deziliter an.',
  },
  glucose: {
    name: 'Nüchtern-Serumglukose',
    shortName: 'Nüchternglukose',
    domain: 'Stoffwechsel / Insulinsensitivität',
    risk: 'Eingabe des Forschungsindex',
    weight: 'Die Glukose dieses Panels ist die Nüchternmessung im Blut. Labore geben sie oft in Milligramm pro Deziliter an.',
  },
  crp: {
    name: 'hs-C-reaktives Protein',
    shortName: 'hs-CRP',
    domain: 'Systemische sterile Entzündung',
    risk: 'Eingabe des Forschungsindex',
    weight: 'Das C-reaktive Protein dieses Panels ist die hochsensitive Blutmessung. Labore geben es oft in Milligramm pro Liter an.',
  },
  lymphocyte: {
    name: 'Lymphozytenanteil',
    shortName: 'Lymphozyten',
    domain: 'Gleichgewicht der Immunseneszenz',
    risk: 'Eingabe des Forschungsindex',
    weight: 'Der Lymphozytenanteil ist der Anteil der weißen Blutzellen, die als Lymphozyten gezählt werden.',
  },
  mcv: {
    name: 'Mittleres Erythrozytenvolumen (MCV)',
    shortName: 'MCV',
    domain: 'Hämatologie und Methylierung',
    risk: 'Eingabe des Forschungsindex',
    weight: 'Das mittlere Erythrozytenvolumen ist das durchschnittliche Volumen der roten Blutzellen. Labore geben es in Femtoliter an.',
  },
  rdw: {
    name: 'Erythrozytenverteilungsbreite (RDW)',
    shortName: 'RDW',
    domain: 'Erythrozytenumsatz / Frailty',
    risk: 'Eingabe des Forschungsindex',
    weight: 'Die Erythrozytenverteilungsbreite beschreibt, wie stark die Größe der roten Blutzellen streut. Labore geben sie in Prozent an.',
  },
  alp: {
    name: 'Alkalische Phosphatase (ALP)',
    shortName: 'AP',
    domain: 'Biliär / Knochenmineralisation',
    risk: 'Eingabe des Forschungsindex',
    weight: 'Die alkalische Phosphatase ist eine Enzymaktivität in einer Blutprobe. Labore geben sie oft in Einheiten pro Liter an.',
  },
  wbc: {
    name: 'Leukozytenzahl (WBC)',
    shortName: 'Leukozyten',
    domain: 'Aktivierung der angeborenen Immunität',
    risk: 'Eingabe des Forschungsindex',
    weight: 'Die Leukozytenzahl ist die Anzahl der weißen Zellen in einer Blutprobe. Labore geben sie oft in Tausend pro Mikroliter an.',
  },
};
