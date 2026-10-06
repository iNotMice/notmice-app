import type jsPDF from 'jspdf';
// Inter covers Latin and Cyrillic. jsPDF's built-in Helvetica has no Cyrillic glyphs.
import interRegularUrl from '@expo-google-fonts/inter/400Regular/Inter_400Regular.ttf?url';
import interBoldUrl from '@expo-google-fonts/inter/700Bold/Inter_700Bold.ttf?url';

export const REPORT_FONT = 'Inter';
const FALLBACK_FONT = 'helvetica';

let cache: Promise<{ regular: string; bold: string }> | null = null;

async function fetchBase64(url: string): Promise<string> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Font request failed (${response.status})`);
  }
  const bytes = new Uint8Array(await response.arrayBuffer());
  let binary = '';
  const chunk = 0x8000;
  for (let offset = 0; offset < bytes.length; offset += chunk) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunk));
  }
  return btoa(binary);
}

/**
 * Embed Inter into the document and return the family to use.
 * If the font files cannot be loaded, the report still builds with Helvetica.
 */
export async function registerReportFonts(doc: jsPDF): Promise<string> {
  try {
    cache ??= Promise.all([fetchBase64(interRegularUrl), fetchBase64(interBoldUrl)]).then(
      ([regular, bold]) => ({ regular, bold }),
    );
    const fonts = await cache;
    doc.addFileToVFS('Inter-Regular.ttf', fonts.regular);
    doc.addFont('Inter-Regular.ttf', REPORT_FONT, 'normal');
    doc.addFileToVFS('Inter-Bold.ttf', fonts.bold);
    doc.addFont('Inter-Bold.ttf', REPORT_FONT, 'bold');
    return REPORT_FONT;
  } catch {
    cache = null;
    return FALLBACK_FONT;
  }
}
