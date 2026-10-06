/** User guide. One page with anchors; read before the first upload. */
export const instructions = {
  stage: 'Guide',
  title: 'User guide',
  lead: 'A step-by-step guide: how to create an account, give consents, upload a test, check the numbers and find your results. If something does not work, see “If something does not work” below.',
  tocTitle: 'On this page',
  sections: {
    start: 'Quick start',
    account: 'Account and sign-in',
    consents: 'Consents',
    need: 'What you need',
    upload: 'How to upload',
    file: 'What happens to the file',
    check: 'Checking the numbers',
    get: 'What you get',
    share: 'Sharing your data',
    cabinet: 'Your account pages',
    trouble: 'If something does not work',
    faq: 'Frequently asked questions',
  },
  need: {
    lead: 'A blood test with nine markers, and your age.',
    markersTitle: 'The nine markers',
    hsCrpNote:
      'A routine blood count and biochemistry panel do not always include high-sensitivity C-reactive protein. It sometimes has to be ordered separately.',
    missingNote:
      'If one marker is missing, the platform saves the other values but does not calculate the index, and shows which marker is missing.',
    reportLook:
      'A suitable report is a table with the marker name, the value, the unit, and usually the reference range.',
    oneFileNote:
      'Today the index is calculated from one uploaded report. If the blood count and the biochemistry came as separate files, each is saved, but the index is not calculated from them.',
  },
  upload: {
    items: [
      'You can upload a PDF, a scan or a photo of the report.',
      'For a photo, frame only the results table in the browser before sending. Leave the header with your name outside the frame.',
      'The server additionally hides lines with personal data before the numbers are read. If it is not sure, you see the hidden frame and decide whether to send it.',
    ],
  },
  file: {
    items: [
      'The original file is read in the server memory and is not written to disk.',
      'From a text PDF, a program on the server extracts the text and removes lines with personal data. In a scan or photo, the server first paints over such lines.',
      'Then the cleaned text or image is sent to an external recognition service, Google Gemini, which finds the markers and their values.',
      'Only the file hash (SHA-256, a fingerprint that cannot be turned back into the file) and the values you confirm are kept.',
    ],
  },
  check: {
    items: [
      'You see the recognised values and units next to each marker.',
      'Compare them with your report, correct anything that is wrong, and confirm.',
      'Until you confirm, nothing is saved.',
    ],
  },
  get: {
    items: [
      'The research index and how it compares with your passport age.',
      'The history of your uploads and how each marker changes.',
    ],
    notTitle: 'What you will not get',
    notItems: [
      'Diagnoses.',
      'Treatment advice.',
      'Advice on supplements or food.',
    ],
  },
  share: {
    lead: 'Sharing is off by default. You can turn it on or off at any time in “Account → Data and consents”.',
    shownTitle: 'If you turn it on, we publish',
    shown: [
      'a pseudonymous ID, not linked to your name;',
      'the collection date;',
      'your age at collection;',
      'the marker codes and values.',
    ],
    hiddenTitle: 'We never publish',
    hidden: ['your name;', 'your email;', 'your date of birth;', 'the internal account ID;', 'your journal notes.'],
    warningTitle: 'Important before you turn it on',
    warning:
      'Published rows are released under the CC0 license. Copies that other people have already downloaded cannot be recalled, even if you delete your account.',
  },
  start: {
    lead: 'Six steps from your first visit to a result. Each step is explained further down this page.',
    steps: [
      {
        title: 'Create an account',
        body: 'Click “Guest” in the top right corner of the page (on a phone, at the bottom of the menu), then “Create an account”. Enter your email and a password of at least 12 characters.',
      },
      {
        title: 'Tick the consents',
        body: 'In the same form, tick the required health-data consent. The other two consents are optional; you can give them later.',
      },
      {
        title: 'Confirm your email',
        body: 'Open the email and click the link in it. You cannot sign in before that. Then sign in with the same email and password.',
      },
      {
        title: 'Upload a test',
        body: 'Menu “Upload → Upload a test”, button “Select Lab PDF File”. A PDF, scan or photo of the report works.',
      },
      {
        title: 'Check the numbers',
        body: 'Compare every value and unit with the report, fix any mistakes and click “Verify All & Compute PhenoAge”.',
      },
      {
        title: 'See your results',
        body: 'The index, all your tests and the marker charts are in the “Account” menu.',
      },
    ],
    languageNote: 'Change the site language with the switcher in the page header, next to the sign-in button.',
  },
  account: {
    lead: 'You need an account to save your tests and see their history. Instead of a name, the account has a pseudonymous public ID.',
    steps: [
      'Click “Guest” in the top right corner of the page. On a phone, open the menu; the sign-in button is at the bottom.',
      'In the sign-in window, click “Create an account”.',
      'Enter your email address and a password of at least 12 characters. Type the password twice.',
      'Tick the required health-data consent. Without it the account cannot be created. The other consents are optional.',
      'Click “Create account”. An email with a link arrives. The link works once and is valid for 24 hours 30 minutes.',
      'Open the email and click the link. If there is no email, check the spam and promotions folders.',
      'Return to the site, click “Guest” and sign in with the same email and password. “Guest” changes to “Signed in”; that button opens your account.',
    ],
    forgot:
      'Forgot your password? In the sign-in window click “Forgot password”, enter your email and open the link from the email. You can also change the password under “Account → Sign-in and security”.',
    phrase:
      'Was your account created earlier with a 12-word phrase? Sign in with it: in the sign-in window, click “Sign in with a recovery phrase”.',
  },
  consents: {
    lead: 'A consent takes effect as soon as you tick it. You can change any of them at any time: “Account → Data and consents”, the “Your consents” block at the top of the page.',
    items: [
      {
        title: 'Health-data processing',
        badge: 'Required',
        body: 'Without it the server does not accept lab files. If you untick it, new uploads stop.',
      },
      {
        title: 'Research reuse',
        badge: 'Optional',
        body: 'Your confirmed tests and questionnaire answers count towards summary statistics for verified laboratories. Laboratories see only totals for groups, never the records of individual people. Groups smaller than 10 are hidden.',
      },
      {
        title: 'Questionnaire',
        badge: 'Optional',
        body: 'Lets us store your questionnaire answers: sex at birth, year of birth, country, height, weight, smoking, alcohol and activity. Until this consent is ticked, the questionnaire fields are inactive.',
      },
      {
        title: 'Publishing in the open dataset',
        badge: 'Separate choice',
        body: 'This is a separate switch, off by default. See “Sharing your data” for details.',
      },
    ],
    surveyNote:
      'The questionnaire is on the same page, below the consents. Every question is optional. Fill in what you want and click “Save answers”.',
  },
  cabinet: {
    lead: 'The “Account” menu works after you sign in. It has six sections that only you can see.',
    items: [
      {
        title: 'Overview',
        body: 'Your account, the number of tests, the latest index and what is missing for it, and the latest marker values. You can also download your copy as JSON or CSV here.',
      },
      {
        title: 'My tests',
        body: 'Every confirmed test, newest first. “Show values” opens the table. A test with a mistake can be deleted and uploaded again.',
      },
      {
        title: 'Markers',
        body: 'Charts of each marker and the index over time. They become useful once you have more than one test.',
      },
      {
        title: 'Journal',
        body: 'Notes on medication, food, activity and sleep with start and end dates. Only you see them; laboratories never receive them.',
      },
      {
        title: 'Data and consents',
        body: 'Consents, the questionnaire, publishing, downloading your copy, deleting tests and the account.',
      },
      {
        title: 'Sign-in and security',
        body: 'Change your password, sign out on other devices, or sign out.',
      },
    ],
  },
  trouble: [
    {
      q: 'An upload shows a message about the health-data consent',
      a: 'The account has no current required consent. Open “Account → Data and consents”, tick “Required health-data consent” and upload the file again.',
    },
    {
      q: 'The email with the link does not arrive',
      a: 'Wait a few minutes and check the spam and promotions folders. Check that the address is spelled correctly. To get a new link, create the account again with the same address: while the email is unconfirmed, the message is sent again.',
    },
    {
      q: 'The link from the email does not open',
      a: 'The link works once and is valid for 24 hours 30 minutes. If it has expired or was already used, request a new one the same way as when you first registered.',
    },
    {
      q: 'The questionnaire fields are grey and cannot be filled in',
      a: 'The questionnaire opens once you tick “Questionnaire (optional)” in the “Your consents” block on “Account → Data and consents”.',
    },
    {
      q: 'The index was not calculated',
      a: 'The index needs all nine markers and your age on one report. What is missing is shown in “Account → Overview” and in “My tests”. The other values are still saved.',
    },
    {
      q: 'A value was read incorrectly',
      a: 'Correct it on the check screen before confirming. If the test is already confirmed with a mistake, delete it in “Account → My tests” and upload it again.',
    },
    {
      q: 'The account page asks me to sign in',
      a: 'You are not signed in or the session has ended. Click “Guest” in the top right corner and sign in again.',
    },
    {
      q: 'I do not remember my password',
      a: 'In the sign-in window click “Forgot password”, enter your email and open the link from the email. The link is sent only if the account email is confirmed.',
    },
  ],
  faq: [
    {
      q: 'Is this a diagnosis?',
      a: 'No. It is a research index. It does not name or exclude diseases.',
    },
    {
      q: 'My index is above my passport age. What should I do?',
      a: 'Discuss the numbers with a doctor. The platform gives no advice on what to do.',
    },
    {
      q: 'How often should I take a test?',
      a: 'The platform does not set a schedule. To compare two tests fairly, take them under the same conditions: fasting, not ill, no hard workout the day before, preferably in the same laboratory.',
    },
    {
      q: 'Why was my photo not recognised?',
      a: 'Usually the photo is blurred, taken at an angle, or the table is cut off. Take the photo in good light, straight on, with the whole results table in the frame. A PDF from the laboratory works best.',
    },
    {
      q: 'How do I delete my data?',
      a: 'In “Account → Data and consents” you can delete saved tests or the whole account together with the confirmed values. Copies of public rows that others have already downloaded cannot be recalled.',
    },
    {
      q: 'Who sees my data?',
      a: 'Only you, while sharing is off. If you turn sharing on, your rows appear in the public dataset under a pseudonym. Verified laboratories see only aggregate statistics, and only if you gave research-reuse consent.',
    },
  ],
  firstUpload: {
    title: 'Before your first upload',
    points: [
      'You need a blood test with nine markers, including high-sensitivity C-reactive protein, and your age.',
      'We do not keep the original file. The text or a painted image is read by the recognition service Google Gemini. Only the values you confirm are saved.',
      'Sharing your data is off by default. If you turn it on, rows are published under a pseudonym and cannot be recalled from people who already downloaded them.',
    ],
    note: 'This summary does not replace the consent texts.',
    readGuide: 'Read the full guide',
    ok: 'Got it',
  },
};
