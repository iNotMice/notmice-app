import type { BiomarkerId } from '../../biomarkerIds';

/** Statische Marker-Notizen. Derselbe Text für jedes Konto. */
export const lifestyleUi = {
  title: 'Marker-Karten',
  badge: 'Gleich für jedes Konto',
  lead: 'Vorbereitete Notizen zu den neun Markern des PhenoAge-Forschungsindex. Der Text ändert sich nicht mit Ihren Ergebnissen.',
  interval:
    'Im Diagramm wird ein Ergebnis mit dem Referenzintervall verglichen, das auf diesem Laborbefund gedruckt ist.',
  indexRole: 'Eine Eingabe des Forschungsindex nach Levine 2018.',
  studyLabel: 'Forschung',
  studyCitation: 'Levine et al., Aging, 2018.',
  studyHref: 'https://doi.org/10.18632/aging.101414',
  disclaimerTitle: 'Hinweis.',
  disclaimer:
    'Ein Werkzeug zur Selbstbeobachtung für Forschungszwecke. Keine medizinische Diagnose und kein Ersatz für eine Ärztin oder einen Arzt.',
  cards: {
    albumin:
      'Serumalbumin ist ein Protein, das in einer Blutprobe gemessen wird. Labore geben es in Gramm pro Liter an.',
    creatinine:
      'Serumkreatinin wird in einer Blutprobe gemessen. Labore geben es oft in Milligramm pro Deziliter an.',
    glucose:
      'Die Glukose dieses Panels ist die Nüchternmessung im Blut. Labore geben sie oft in Milligramm pro Deziliter an.',
    crp: 'Das C-reaktive Protein dieses Panels ist die hochsensitive Blutmessung. Labore geben es oft in Milligramm pro Liter an.',
    lymphocyte:
      'Der Lymphozytenanteil ist der Anteil der weißen Blutzellen, die als Lymphozyten gezählt werden.',
    mcv: 'Das mittlere Erythrozytenvolumen ist das durchschnittliche Volumen der roten Blutzellen. Labore geben es in Femtoliter an.',
    rdw: 'Die Erythrozytenverteilungsbreite beschreibt, wie stark die Größe der roten Blutzellen streut. Labore geben sie in Prozent an.',
    alp: 'Die alkalische Phosphatase ist eine Enzymaktivität in einer Blutprobe. Labore geben sie oft in Einheiten pro Liter an.',
    wbc: 'Die Leukozytenzahl ist die Anzahl der weißen Zellen in einer Blutprobe. Labore geben sie oft in Tausend pro Mikroliter an.',
  } satisfies Record<BiomarkerId, string>,
};
