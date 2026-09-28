export const instructions = {
  stage: 'Dokumente',
  stageMeta: 'So nutzen Sie NotMice',
  title: 'Benutzeranleitung',
  lead: 'Eine kurze Karte der App: wofür jeder Teil da ist, und in welcher Reihenfolge Ihre Zahlen unter Ihrer Kontrolle bleiben.',
  openSection: 'Diesen Bereich öffnen',
  aboutTitle: 'Was NotMice tut',
  aboutBody:
    'NotMice liest ein Labor-PDF auf dem Server, bittet Sie, die Zahlen zu bestätigen, und berechnet PhenoAge als Forschungsindex. Das ist keine Diagnose und ersetzt keine ärztliche Beurteilung.',
  mapTitle: 'Was in der Kopfzeile steht',
  mapLead: 'Die Kopfzeile bündelt die Arbeit in wenigen Menüs, damit Sie nicht raten müssen, wohin Sie gehen.',
  mapItems: [
    {
      name: 'Übersicht',
      body: 'Die Startseite. Sie erklärt die Methode und zeigt ein Rechenbeispiel, nicht Ihre eigene Labordatei.',
    },
    {
      name: 'Labor',
      body: 'Labor hochladen nimmt ein PDF oder einen Scan. Prüfung und Extraktion ist der Ort, an dem Sie die Zahlen prüfen, bevor etwas gespeichert wird.',
    },
    {
      name: 'PhenoAge',
      body: 'Die PhenoAge-Engine zeigt den Forschungsindex und die Marker-Karten. Der Biomarker-Verlauf behält Panels, die Sie in dieser Browsersitzung speichern.',
    },
    {
      name: 'Daten',
      body: 'Ihr Konto, die Anmeldung per E-Mail und der Schalter für öffentliches Teilen.',
    },
    {
      name: 'Dokumente',
      body: 'Diese Seite. Öffnen Sie sie, wenn die Menüs unklar sind.',
    },
    {
      name: 'Kontoschaltfläche',
      body: 'Das Schlüsselsymbol und die grüne Adresse öffnen die Anmeldung. Gast bedeutet, dass Sie noch nicht angemeldet sind.',
    },
    {
      name: 'Sprache',
      body: 'Schaltet die Oberfläche zwischen Englisch und Deutsch. Ihre Zahlen bleiben dieselben.',
    },
    {
      name: 'Keine Rohdateien',
      body: 'Das Schild bedeutet, dass die ursprüngliche Labordatei nicht auf die Festplatte geschrieben wird.',
    },
  ],
  pathTitle: 'Ein Weg, dem man leicht folgen kann',
  pathSteps: [
    'Legen Sie ein Konto an und schreiben Sie die 12 Wörter auf. Nur damit kommen Sie wieder hinein. Der Server speichert die Wörter nicht.',
    'Öffnen Sie Labor, dann Labor hochladen. Legen Sie ein PDF ab, oder nutzen Sie ein Demo-Beispiel, wenn Sie nur den Ablauf sehen wollen.',
    'Vergleichen Sie unter Prüfung und Extraktion jede Zahl mit Ihrem Befund und korrigieren Sie Einheiten, bevor Sie weitergehen.',
    'Öffnen Sie die PhenoAge-Engine, um den Index neben dem Kalenderalter zu sehen, und die Marker-Karten unter der Punktzahl.',
    'Speichern Sie in den Verlauf nur, wenn dieses Panel im Diagramm dieser Browsersitzung bleiben soll. Die Liste wird nicht aus dem Labordatensatz geladen.',
    'Schalten Sie unter Daten das öffentliche Teilen nur ein, wenn bestätigte Zeilen in den offenen Datensatz sollen. Lassen Sie es aus, wenn nicht.',
  ],
  screensTitle: 'Wofür jeder Bildschirm da ist',
  screens: [
    {
      tab: 'overview-landing',
      title: 'Übersicht',
      body: 'Lesen Sie, was das Protokoll ist, probieren Sie die Beispielregler und legen Sie ein Konto an. Die Zahlen hier sind ein Tutorial, bis Sie ein echtes Panel laden.',
    },
    {
      tab: 'upload-lab',
      title: 'Labor hochladen',
      body: 'Legen Sie ein PDF oder einen Scan von Quest, LabCorp, NHS oder einer Klinik ab. Der Server liest die Datei im Arbeitsspeicher und behält die Originaldatei nicht. Für eine echte Datei müssen Sie angemeldet sein. Die Demo-Schaltflächen füllen Beispielzahlen. Das ist kein Datei-Upload, und das Bestätigen veröffentlicht kein Labordokument.',
    },
    {
      tab: 'review-extraction',
      title: 'Prüfung und Extraktion',
      body: 'Prüfen Sie jeden extrahierten Wert gegen Papier oder PDF. Korrigieren Sie, was falsch aussieht, und bestätigen Sie dann, um PhenoAge zu berechnen. Nichts wird als bestätigtes Ergebnis gespeichert, bevor Sie es freigeben.',
    },
    {
      tab: 'phenoage-engine',
      title: 'PhenoAge-Engine',
      body: 'Zeigt PhenoAge, den Abstand zum Kalenderalter und wie jeder der neun Biomarker den Index zieht. Mit den Reglern können Sie Werte ausprobieren. Weiter unten stehen dieselben Marker-Karten für jedes Konto. Das ist der Forschungsindex nach Levine 2018, kein medizinischer Dienst.',
    },
    {
      tab: 'biomarker-history',
      title: 'Biomarker-Verlauf',
      body: 'Zeichnet Panels, die Sie in dieser Browsersitzung gespeichert haben. Ein Panel erscheint hier erst, nachdem Sie In den Verlauf speichern gewählt haben. Sie können ein PDF dieser Sitzungsliste exportieren.',
    },
    {
      tab: 'data-sovereignty-public-sharing',
      title: 'Daten',
      body: 'Melden Sie sich mit der Phrase aus 12 Wörtern an oder legen Sie ein Konto an. Teilen bleibt aus, bis Sie es einschalten. Wenn es an ist, kommen bestätigte Biomarker-Zeilen dieses Kontos in den öffentlichen Datensatz. Namen, Geburtsdaten und die Originaldatei sind nicht enthalten.',
    },
  ],
};
