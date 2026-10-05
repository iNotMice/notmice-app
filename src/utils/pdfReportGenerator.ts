import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import { HistoricalTestRecord } from '../types';
import { PHENOAGE_BIOMARKERS } from '../data/phenoAgeData';
import { getActiveI18n } from '../i18n/catalog';
import { isBiomarkerId } from '../i18n/biomarkerIds';
import { fill } from '../i18n/fill';
import { registerReportFonts } from './pdfFonts';
import { missingMarkerText, scoredRecords } from './phenoTrend';

export async function generateHistoricalReportPDF(history: HistoricalTestRecord[]): Promise<void> {
  if (!history || history.length === 0) return;

  const { locale, messages } = getActiveI18n();
  const copy = messages.report;
  const dateLocale = locale === 'de' ? 'de-DE' : locale === 'ru' ? 'ru-RU' : 'en-US';
  const sortedHistory = [...history].sort((a, b) => a.date.localeCompare(b.date));
  const scored = scoredRecords(sortedHistory);
  const latest = scored.length > 0 ? scored[scored.length - 1] : sortedHistory[sortedHistory.length - 1];

  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  });

  const font = await registerReportFonts(doc);
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 14;

  doc.setFillColor(11, 28, 48);
  doc.rect(0, 0, pageWidth, 38, 'F');
  doc.setFillColor(0, 97, 148);
  doc.rect(0, 38, pageWidth, 2, 'F');

  doc.setTextColor(255, 255, 255);
  doc.setFont(font, 'bold');
  doc.setFontSize(16);
  doc.text(copy.pdfTitle, margin, 15);
  doc.setFont(font, 'normal');
  doc.setFontSize(9);
  doc.setTextColor(203, 213, 225);
  doc.text(copy.pdfSubtitle, margin, 22, { maxWidth: pageWidth - margin * 2 - 40 });

  doc.setFontSize(8);
  doc.setTextColor(148, 163, 184);
  const printDate = new Date().toLocaleDateString(dateLocale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
  doc.text(fill(copy.generatedLine, { date: printDate }), pageWidth - margin, 12, { align: 'right' });
  doc.text(fill(copy.panelsLine, { count: sortedHistory.length }), pageWidth - margin, 18, { align: 'right' });
  doc.text(copy.statusLine, pageWidth - margin, 24, { align: 'right', maxWidth: 70 });

  let currentY = 48;
  doc.setFont(font, 'bold');
  doc.setFontSize(12);
  doc.setTextColor(11, 28, 48);
  doc.text(copy.pdfSummary, margin, currentY);
  currentY += 5;

  const boxWidth = (pageWidth - margin * 2 - 6) / 3;
  const boxHeight = 22;
  const latestValue =
    latest.phenoAge === null ? copy.notCalculated : fill(copy.yrs, { value: latest.phenoAge.toFixed(1) });
  const latestAge =
    latest.chronologicalAge === null
      ? copy.ageMissing
      : fill(copy.chronoAge, { value: latest.chronologicalAge.toFixed(1) });
  const kpis = [
    { title: copy.latestPhenoPdf, value: latestValue, sub: latestAge },
    { title: copy.scoredPdf, value: String(scored.length), sub: copy.panels },
    { title: copy.notScoredPdf, value: String(sortedHistory.length - scored.length), sub: copy.panels },
  ];

  kpis.forEach((kpi, idx) => {
    const x = margin + idx * (boxWidth + 3);
    doc.setFillColor(248, 249, 255);
    doc.setDrawColor(226, 232, 240);
    doc.roundedRect(x, currentY, boxWidth, boxHeight, 2, 2, 'FD');
    doc.setFont(font, 'bold');
    doc.setFontSize(7);
    doc.setTextColor(86, 94, 116);
    doc.text(kpi.title, x + 3, currentY + 5);
    doc.setFontSize(11);
    doc.setTextColor(11, 28, 48);
    doc.text(kpi.value, x + 3, currentY + 12);
    doc.setFont(font, 'normal');
    doc.setFontSize(6.5);
    doc.setTextColor(100, 116, 139);
    doc.text(kpi.sub, x + 3, currentY + 18);
  });

  currentY += boxHeight + 8;
  doc.setFont(font, 'bold');
  doc.setFontSize(11);
  doc.setTextColor(11, 28, 48);
  doc.text(copy.panelsPdf, margin, currentY);
  currentY += 2;

  const panelRows = sortedHistory.map((item) => {
    const age = item.chronologicalAge === null ? copy.ageMissing : item.chronologicalAge.toFixed(1);
    const index = item.phenoAge === null ? copy.notCalculated : item.phenoAge.toFixed(1);
    const gap =
      item.phenoAge !== null
        ? '—'
        : item.missingMarkers.length > 0
          ? missingMarkerText(item, messages.biomarkers)
          : item.chronologicalAge === null
            ? copy.ageMissing
            : copy.notCalculated;
    return [item.collectedAt ?? item.date, item.labSource, age, index, gap];
  });

  autoTable(doc, {
    startY: currentY,
    head: [[copy.colDate, copy.colLab, copy.colCalendar, copy.colPhenoShort, copy.colMissing]],
    body: panelRows,
    theme: 'striped',
    styles: {
      fontSize: 8,
      cellPadding: 2.2,
      font,
      textColor: [51, 65, 85],
    },
    headStyles: {
      fillColor: [0, 97, 148],
      textColor: [255, 255, 255],
      fontStyle: 'bold',
      fontSize: 8,
    },
    margin: { left: margin, right: margin },
  });

  const afterFirstTable = (doc as unknown as { lastAutoTable?: { finalY: number } }).lastAutoTable?.finalY;
  currentY = (afterFirstTable ?? currentY + 40) + 7;
  doc.setFont(font, 'bold');
  doc.setFontSize(11);
  doc.setTextColor(11, 28, 48);
  doc.text(copy.matrixPdf, margin, currentY);
  currentY += 2;

  const biomarkerHead = [copy.colBiomarker, copy.colUnit, ...sortedHistory.map((item) => item.date)];
  const biomarkerBody = PHENOAGE_BIOMARKERS.map((bio) => {
    const row = [isBiomarkerId(bio.id) ? messages.biomarkers[bio.id].name : bio.name, bio.unit];
    sortedHistory.forEach((item) => {
      const value = item.biomarkers[bio.id];
      const measured = item.markerIds.includes(bio.id) || item.sessionOnly;
      row.push(measured && value !== undefined ? String(value) : '—');
    });
    return row;
  });

  autoTable(doc, {
    startY: currentY,
    head: [biomarkerHead],
    body: biomarkerBody,
    theme: 'grid',
    styles: {
      fontSize: 7.5,
      cellPadding: 2,
      font,
      textColor: [51, 65, 85],
    },
    headStyles: {
      fillColor: [11, 28, 48],
      textColor: [255, 255, 255],
      fontStyle: 'bold',
      fontSize: 7.5,
    },
    margin: { left: margin, right: margin },
  });

  const afterSecondTable = (doc as unknown as { lastAutoTable?: { finalY: number } }).lastAutoTable?.finalY;
  currentY = (afterSecondTable ?? currentY + 60) + 7;
  if (currentY > pageHeight - 36) {
    doc.addPage();
    currentY = 20;
  }

  const disclaimer = doc.splitTextToSize(
    `${messages.shell.dataDisclaimer} ${messages.shell.disclaimer} ${copy.citation}`,
    pageWidth - margin * 2 - 6,
  );
  const boxH = 8 + disclaimer.length * 4;
  doc.setFillColor(248, 249, 255);
  doc.setDrawColor(226, 232, 240);
  doc.roundedRect(margin, currentY, pageWidth - margin * 2, boxH, 2, 2, 'FD');
  doc.setFont(font, 'normal');
  doc.setFontSize(8);
  doc.setTextColor(51, 65, 85);
  doc.text(disclaimer, margin + 3, currentY + 6);

  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i += 1) {
    doc.setPage(i);
    doc.setFont(font, 'normal');
    doc.setFontSize(7);
    doc.setTextColor(148, 163, 184);
    const footer = doc.splitTextToSize(copy.footer, pageWidth - margin * 2 - 30);
    doc.text(footer, margin, pageHeight - 8);
    doc.text(fill(copy.page, { page: i, total: totalPages }), pageWidth - margin, pageHeight - 8, {
      align: 'right',
    });
  }

  doc.save(`PhenoAge_Research_Index_${latest.date}.pdf`);
}
