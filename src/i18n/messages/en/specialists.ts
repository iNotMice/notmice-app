/** Section for doctors, researchers and laboratories. Terminology is allowed; facts carry sources. */
export const specialists = {
  kicker: 'For specialists',
  title: 'Method, limits and data',
  lead: 'For doctors, researchers and laboratories: how the index is calculated, where it should not be used, and how the data can be accessed.',
  audienceTitle: 'Who are you?',
  audiences: [
    {
      id: 'doctor',
      title: 'Doctor',
      body: 'What the index is, how far it can be trusted, what it is not, and how to talk with a patient who brings the numbers.',
      action: 'Method and limits',
      page: 'method',
    },
    {
      id: 'researcher',
      title: 'Researcher',
      body: 'Data format, licenses, field list and how to download the public dataset.',
      action: 'Data and charter',
      page: 'data',
    },
    {
      id: 'laboratory',
      title: 'Laboratory or organization',
      body: 'Access to aggregate cohort statistics after verification and a data-use agreement.',
      action: 'For laboratories',
      page: 'labs',
    },
  ],
  pages: {
    method: 'Method',
    limits: 'Limits and correct use',
    data: 'Data and charter',
    labs: 'Laboratories and organizations',
    contact: 'Contact',
  },
  reviewBadge: 'Medical review: {name}, {qualification}, {date}',

  method: {
    title: 'Method',
    lead: 'Phenotypic age (PhenoAge) after Levine et al., Aging 2018;10(4):573–591. The formula runs on the server; the browser never calculates the score.',
    formulaTitle: 'Formula',
    formulaBody: [
      'Step 1. A linear predictor xb is built from nine blood markers and chronological age with the Gompertz coefficients from Table 1 of the paper. C-reactive protein enters as a natural logarithm.',
      'Step 2. xb is turned into M, the 10-year (120-month) probability of the Gompertz model in the paper, gamma = 0.0076927.',
      'Step 3. M is converted back into years: PhenoAge = 141.50225 + ln(−0.00553 × ln(1 − M)) / 0.090165.',
      'The engine reproduces the worked case from the supplementary materials of the paper (age 71, PhenoAge 66.95); this is a unit test in the repository.',
    ],
    sourceTitle: 'Where the formula comes from',
    sourceBody:
      'Training data: NHANES III, 9,926 US adults with complete biomarker data; 42 candidate markers were narrowed to nine plus age by penalized Cox regression. Validation: NHANES IV, 6,209 US adults followed for up to 12 years. In the validation sample, each year of phenotypic age above chronological age was associated with a 9% higher chance of death from any cause (HR 1.09).',
    unitsTitle: 'Units and conversions',
    unitsLead:
      'The dictionary stores lab-friendly units. Before scoring, three markers are converted into the units the coefficients were fitted on.',
    colMarker: 'Marker',
    colLoinc: 'LOINC',
    colInput: 'Input unit',
    colModel: 'Model unit',
    colCoefficient: 'Coefficient',
    conversions: {
      creatinine: 'mg/dL × 88.4 → µmol/L',
      glucose: 'mg/dL × 0.0555 → mmol/L',
      crp: 'mg/L × 0.1 → mg/dL, then ln',
      same: 'as entered',
    },
    ageRow: 'Chronological age',
    versionsTitle: 'Versions',
    versions: [
      'Engine: Levine 2018 coefficients, gamma 0.0076927, ALP weight 0.0019 as printed.',
      'Biomarker dictionary: LOINC dictionary v1, licensed CC BY 4.0.',
      'The parser version is stored with every extracted panel.',
    ],
    pipelineTitle: 'Processing pipeline',
    pipeline: [
      {
        title: 'Intake in memory',
        body: 'The file is read into server RAM and is not written to disk. A SHA-256 hash of the file is kept for provenance.',
      },
      {
        title: 'Personal lines removed',
        body: 'For a text PDF, the text is extracted on the server with pdfplumber and lines with personal data are dropped. For a scan or a photo, a local OCR engine (Tesseract) paints over personal lines; if it is unsure, the person sees the painted frame and decides whether to send it.',
      },
      {
        title: 'Recognition',
        body: 'The cleaned text or the painted image is sent to an external recognition model (Google Gemini), which returns marker names, values and units. Names are mapped to the versioned LOINC dictionary; unmatched names stay in an unmapped queue.',
      },
      {
        title: 'Human check',
        body: 'The person compares every value with the report and corrects values and units. Nothing is stored as a confirmed result before this sign-off.',
      },
      {
        title: 'Score',
        body: 'PhenoAge is calculated only when all nine markers and the age are present. A missing marker is listed and never filled in.',
      },
    ],
    slidersTitle: 'Algorithm sensitivity',
    slidersLead:
      'The same fictional example as on the home page. Move a marker to see how the index responds.',
  },

  limits: {
    title: 'Limits and correct use',
    lead: 'What the index is not, what distorts it, and what is known about whom it applies to.',
    notTitle: 'What the index is not',
    notItems: [
      'Not a diagnosis. It does not name a disease and does not exclude one.',
      'Not a forecast for a particular person. The coefficients describe a population average, not an individual.',
      'Not a reason to start, stop or change treatment.',
      'Not a replacement for the individual markers. Each marker should be read against the reference interval printed by its laboratory.',
    ],
    authorsNote:
      'The authors of the formula write that an estimate of this kind should not replace clinical biomarkers in medical decisions.',
    distortTitle: 'What distorts the numbers',
    distortItems: [
      'An acute infection or inflammation: C-reactive protein and white cells rise within days.',
      'Hard physical exercise the day before the test.',
      'A test taken without fasting: glucose rises.',
      'Different laboratories, methods and units between two tests. Compare tests taken under the same conditions.',
      'A standard CRP test instead of high-sensitivity CRP: low values may be printed as “below the limit” and cannot be scored exactly.',
    ],
    populationTitle: 'Population and applicability',
    populationBody: [
      'The formula was trained and validated on US national survey data (NHANES III and NHANES IV). Its accuracy in other populations has not been established by this platform.',
      'The authors note that markers such as CRP, albumin, creatinine and glucose vary little in children, young adults and very healthy people, so the index may separate them less well.',
      'Applicability across menopause stages and other specific groups is not claimed here. This part will be completed by the medical reviewer with references to the literature.',
    ],
    patientTitle: 'If a patient brings the numbers',
    patientItems: [
      'The index is a research measure. It is reasonable to look at the nine markers themselves and at their reference intervals.',
      'A large gap between the index and passport age is a reason to review the individual markers, not a finding in itself.',
      'The platform gives patients no advice. Clinical decisions stay with the doctor.',
    ],
  },

  data: {
    title: 'Data and charter',
    lead: 'What the public dataset contains, under which licenses it is published, and how access is organized.',
    licensesTitle: 'Licenses',
    licenses: [
      { name: 'AGPL-3.0', body: 'Source code of the platform.' },
      { name: 'CC BY 4.0', body: 'The LOINC mapping dictionary.' },
      { name: 'CC0 1.0', body: 'Public dataset rows and aggregate statistics.' },
    ],
    fieldsTitle: 'Fields in the public dataset',
    fieldsShown: [
      'Pseudonymous public ID',
      'Collection date',
      'Age at collection, when the report has it',
      'LOINC code, marker name and the name as printed',
      'Value, unit and mapping status',
    ],
    fieldsHidden: [
      'Name and email',
      'Date of birth',
      'Internal account ID',
      'Hash of the original document',
      'Journal entries',
    ],
    shownLabel: 'Published',
    hiddenLabel: 'Never published',
    pseudonymNote:
      'Rows are pseudonymous, not anonymous: one public ID links all rows of one person. Only aggregate statistics are anonymous.',
    cc0Note:
      'Rows are published under CC0. Copies that other people have already downloaded cannot be recalled, even if the participant later deletes the account.',
    accessTitle: 'Access model',
    access: [
      {
        title: 'Public dataset',
        body: 'Rows of participants who turned public sharing on. Read-only API GET /api/v1/dataset, plus CSV, Parquet and a datasheet.',
      },
      {
        title: 'Level 1: aggregates for verified laboratories',
        body: 'Only for participants who gave research-reuse consent. Groups smaller than 10 are hidden, counts are rounded down to a multiple of 5, adults only.',
      },
      {
        title: 'Level 2: row-level data for a specific study',
        body: 'Planned. Only for participants who explicitly agree to that study. Not available today.',
      },
    ],
  },

  labs: {
    title: 'Laboratories and organizations',
    lead: 'Verified organizations can request aggregate statistics on consent-eligible cohorts. Participant-level records are not available.',
    steps: [
      'Register the organization and confirm the owner email.',
      'Our team reviews and verifies the organization by hand.',
      'Accept the data-use agreement once it is legally approved.',
    ],
    privacy:
      'Laboratory accounts are separate from participant accounts. Small groups are suppressed and counts are rounded.',
    open: 'Open the laboratory portal',
  },

  contact: {
    title: 'Contact',
    lead: 'Questions about the method, the data or cooperation:',
  },
};
