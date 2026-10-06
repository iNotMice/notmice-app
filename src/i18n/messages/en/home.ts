/** Home page for a first-time participant. No technical terms live here. */
export const home = {
  kicker: 'Open research on biological age',
  headline: 'Turn your blood test results into biological data.',
  headlineAccent: 'Help science understand aging.',
  subhead:
    'Upload a test, check the numbers and see your biological age index. If you want, share the data without your name or email, so that scientists can better understand how the body ages.',
  ctaCreate: 'Create an account',
  ctaUpload: 'Upload a test',
  ctaHow: 'How it works',
  trustLine: 'We do not keep the original file.',
  trustLink: 'Details in the guide',

  missionKicker: 'Our mission',
  missionTitle: 'An open database on biological age',
  missionBody: [
    'We are building an open database on biological age. Scientists anywhere can use it to check what actually slows aging: diets, medicines, habits.',
    'We want medicine to learn to notice the wear of the body early, not only to treat diseases.',
    'Data that people choose to share is published under a pseudonym, without names or contact details.',
  ],
  missionStatus:
    'The database is only starting to fill up. You can be one of the first participants.',

  indexKicker: 'The index',
  indexTitle: 'What is the Levine index (PhenoAge)',
  indexBody: [
    'The Levine index compares your blood test with data from thousands of people and shows which age your results match on average. The date in your passport counts years lived. The index looks at the state of the body.',
    'The formula was published in 2018 in the journal Aging by Morgan Levine, Steve Horvath and co-authors. It was built on data from about ten thousand adults in a US national health survey, then checked on a separate group of six thousand people.',
    'The formula takes your age and nine blood markers. Together they reflect inflammation, liver and kidney function, metabolism and immunity. It is a research index, not a diagnosis.',
  ],
  markersToggle: 'Which markers are included',
  markersNote:
    'All nine are needed. If one is missing, the index is not calculated, and we show which marker is missing.',
  paperLink: 'Original paper (Aging, 2018)',
  matrixLink: 'Full marker table for specialists',

  forYouKicker: 'For you',
  forYouTitle: 'Why this matters to you',
  forYou: [
    {
      title: 'See the difference',
      body: 'The index shows how far your biological age is from your passport age, and how this changes over time.',
    },
    {
      title: 'Notice a shift',
      body: 'The formula includes markers of inflammation and metabolism. A clear change between tests is a reason to discuss the numbers with a doctor. The index does not make a diagnosis.',
    },
    {
      title: 'Check your lifestyle',
      body: 'Changed your diet or started running? You can take a test again in about three months and compare. Repeat the conditions: fasting, not ill, no hard workout the day before. Inflammation and white cells change fast.',
    },
  ],

  forScienceKicker: 'For science',
  forScienceTitle: 'Why this matters to science',
  forScienceLead: 'To understand aging, scientists need large sets of data about people.',
  forScience: [
    {
      title: 'Test ideas faster',
      body: 'Nobody can wait 40 years to learn whether a diet or a medicine slows aging. Biological age indices give an early signal within months. How well they stand in for real health outcomes is still being studied.',
    },
    {
      title: 'Look for patterns',
      body: 'By comparing many profiles, researchers can look for what people with a biological age below their passport age have in common: lifestyle, diet, habits.',
    },
    {
      title: 'Find new markers',
      body: 'An open dataset lets researchers test new ideas about early signs of aging without collecting their own data from scratch.',
    },
  ],

  example: {
    badge: 'Fictional example',
    title: 'Alexei, 45',
    storyStart: [
      'Alexei is 45. He works a lot and sleeps little. He uploaded a fresh blood test. C-reactive protein and glucose are above the reference interval printed on the report, and creatinine is near the upper end of its interval.',
      'The Levine index showed 51 years, 6 years above his passport age. Alexei did not look for causes on his own. He showed the numbers to his doctor, who ordered further tests and made a plan with him for sleep, food and exercise.',
    ],
    storyFollowUp: [
      'Four months later he took the test again. C-reactive protein fell from 7.0 to 3.0 mg/L, and the other markers moved towards the middle of their reference intervals. The index: 47 years.',
      'Alexei got a clear trend to discuss with his doctor. Science got one more data point, if he turned sharing on.',
    ],
    footnote:
      'The example is fictional. The numbers are calculated with the Levine 2018 formula on our server. Your result will be different.',
    startTab: 'First test',
    followUpTab: '4 months later',
    passportAge: 'Passport age',
    indexAge: 'Levine index',
    difference: 'Difference',
    years: 'years',
    calculating: 'Calculating…',
    unavailable: 'The index could not be calculated right now.',
    slidersTitle: 'Try it yourself',
    slidersLead: 'Move a marker and the index is recalculated on the server.',
    crpLabel: 'C-reactive protein (CRP)',
    albuminLabel: 'Albumin',
    reset: 'Back to Alexei’s numbers',
  },

  howKicker: 'Step by step',
  howTitle: 'How it works',
  howSteps: [
    {
      title: 'Create an account',
      body: 'You sign in first — uploads and results are only available once registered.',
    },
    {
      title: 'Upload a test',
      body: 'A PDF, a scan or a photo of the report.',
    },
    {
      title: 'Check the numbers',
      body: 'We read the markers. You confirm or correct them.',
    },
    {
      title: 'Get the index',
      body: 'Then decide whether to share your data with science.',
    },
  ],
  privacyTitle: 'What happens to your data',
  privacyLines: [
    'We do not keep the original file. Only the confirmed numbers are saved.',
    'Lines with your name are hidden before the numbers are read.',
    'Sharing with science is off until you turn it on.',
  ],
  guideLink: 'Read the full guide',

  finalTitle: 'Want to see your index?',
  finalBody: 'You need a blood test with nine markers and about five minutes.',
  specialistsPrompt: 'Are you a doctor or a researcher?',
  specialistsLink: 'Go to the section for specialists',
};
