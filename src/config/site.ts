/**
 * Site-wide facts that are still being decided. Copy reads them from here,
 * so a rename or a newly approved fact changes one line, not every dictionary.
 */

/** Working product name. The co-founders have not approved it yet. */
export const BRAND_NAME = 'NotMice';

/**
 * Team address for the "Contact" page for specialists.
 * Null hides the page until a real mailbox exists.
 */
export const TEAM_CONTACT_EMAIL: string | null = null;

/**
 * Named medical review shown on Method, Limits and the user guide.
 * Null hides the badge. Fill it only after the reviewer's written consent
 * and a check of the stated qualification.
 */
export const MEDICAL_REVIEW: { name: string; qualification: string; date: string } | null = null;

/** Original PhenoAge paper. */
export const LEVINE_2018_DOI_URL = 'https://doi.org/10.18632/aging.101414';
export const LEVINE_2018_PUBMED_URL = 'https://pubmed.ncbi.nlm.nih.gov/29676998/';

/** Consent text currently in force. */
export const CONSENT_DOCUMENT_URL = '/legal/consent-personal-research-2026-10-03.html';
