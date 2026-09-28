export const instructions = {
  stage: 'Documents',
  stageMeta: 'How to use NotMice',
  title: 'User instructions',
  lead: 'A short map of the app: what each part does, and the order that keeps your numbers under your control.',
  openSection: 'Open this section',
  aboutTitle: 'What NotMice does',
  aboutBody:
    'NotMice reads a laboratory PDF on the server, asks you to confirm the numbers, and calculates PhenoAge as a research index. It is not a diagnosis and it does not replace a clinician.',
  mapTitle: 'What is in the header',
  mapLead: 'The header groups the work into a few menus so you do not have to guess where to go.',
  mapItems: [
    {
      name: 'Overview',
      body: 'The start page. It explains the method and shows a worked example, not your own lab file.',
    },
    {
      name: 'Lab',
      body: 'Upload Lab takes a PDF or scan. Review and Extraction is where you check the numbers before anything is saved.',
    },
    {
      name: 'PhenoAge',
      body: 'PhenoAge Engine shows the research index and marker cards. Biomarker History keeps panels you save during this browser session.',
    },
    {
      name: 'Data',
      body: 'Your account, email sign-in, and the switch for public sharing.',
    },
    {
      name: 'Documents',
      body: 'This page. Open it whenever the menus are unclear.',
    },
    {
      name: 'Account button',
      body: 'The key icon and the green address open sign-in. Guest means you are not signed in yet.',
    },
    {
      name: 'Language',
      body: 'Switches the interface between English and German. Your numbers stay the same.',
    },
    {
      name: 'No raw files',
      body: 'The shield means the original laboratory file is not written to disk.',
    },
  ],
  pathTitle: 'A path that is easy to follow',
  pathSteps: [
    'Create an account and write down the 12 words. They are the only way back in. The server does not store the words.',
    'Open Lab, then Upload Lab. Drop a PDF, or use a demo fixture if you only want to see the flow.',
    'On Review and Extraction, compare each number with your report and correct units before you continue.',
    'Open PhenoAge Engine to see the index beside your calendar age, and the marker cards under the score.',
    'Save to History only if you want that panel in the chart for this browser session. The list is not loaded from the laboratory dataset.',
    'On Data, turn public sharing on only if you want confirmed rows in the open dataset. Leave it off if you do not.',
  ],
  screensTitle: 'What each screen is for',
  screens: [
    {
      tab: 'overview-landing',
      title: 'Overview',
      body: 'Read what the protocol is, try the example sliders, and start an account. The numbers here are a tutorial until you load a real panel.',
    },
    {
      tab: 'upload-lab',
      title: 'Upload Lab',
      body: 'Drop a Quest, LabCorp, NHS, or clinic PDF or scan. The server reads it in memory and does not keep the original file. You must be signed in to extract a real file. The demo buttons fill sample numbers. They are not a file upload, and confirming them does not publish a lab document.',
    },
    {
      tab: 'review-extraction',
      title: 'Review and Extraction',
      body: 'Check every extracted value against your paper or PDF. Edit anything that looks wrong, then verify and compute PhenoAge. Nothing is stored as a confirmed result until you sign off.',
    },
    {
      tab: 'phenoage-engine',
      title: 'PhenoAge Engine',
      body: 'Shows PhenoAge, the gap versus calendar age, and how each of the nine biomarkers pulls the index. Sliders let you try values. Lower on the page, the same marker cards appear for every account. This is the Levine 2018 research index, not a medical service.',
    },
    {
      tab: 'biomarker-history',
      title: 'Biomarker History',
      body: 'Charts panels you saved from this browser session. A panel appears here only after you choose Save to History. You can export a PDF of that session list.',
    },
    {
      tab: 'protocol-journal',
      title: 'Journal',
      body: 'Write a drug, supplement, meal pattern, activity, or sleep period in your own words, with an optional dose and an open or closed date range. The entry stays on this account. It is included when you download your own JSON or CSV.',
    },
    {
      tab: 'data-sovereignty-public-sharing',
      title: 'Data',
      body: 'Sign in with the 12-word phrase, or create an account. Sharing stays off until you turn it on. When it is on, confirmed biomarker rows for this account join the public dataset. Names, dates of birth, and the original file are not included.',
    },
  ],
};
