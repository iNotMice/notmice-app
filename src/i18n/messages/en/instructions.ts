/** User guide. One page with anchors; read before the first upload. */
export const instructions = {
  stage: 'Guide',
  title: 'User guide',
  lead: 'Read this once before your first upload. It explains what you need, what happens to your file, and what you can expect.',
  tocTitle: 'On this page',
  sections: {
    need: 'What you need',
    upload: 'How to upload',
    file: 'What happens to the file',
    check: 'Checking the numbers',
    get: 'What you get',
    share: 'Sharing your data',
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
