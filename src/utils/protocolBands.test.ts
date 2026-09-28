import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { history as deHistory } from '../i18n/messages/de/history.ts';
import { history as enHistory } from '../i18n/messages/en/history.ts';
import {
  dayMs,
  fractionOnAxis,
  layoutPeriodBands,
  type JournalSpan,
} from './protocolBands.ts';

const TODAY = '2026-09-28';

const entries: JournalSpan[] = [
  {
    id: 'a',
    title: 'Magnesium',
    startedOn: '2026-03-01',
    endedOn: '2026-04-01',
  },
  {
    id: 'b',
    title: 'Walks',
    startedOn: '2026-03-15',
    endedOn: null,
  },
  {
    id: 'c',
    title: 'Early sleep',
    startedOn: '2026-01-10',
    endedOn: '2026-01-20',
  },
];

test('an empty end date runs through today and the label is the name', () => {
  const layout = layoutPeriodBands(['2026-01-01', '2026-07-01'], entries, TODAY);
  const walks = layout.periods.find((period) => period.id === 'b');
  assert.ok(walks);
  assert.equal(walks.title, 'Walks');
  assert.equal(walks.end, dayMs(TODAY));
  assert.deepEqual(Object.keys(walks).sort(), ['end', 'id', 'lane', 'start', 'title']);
});

test('a written end date stays on that day', () => {
  const layout = layoutPeriodBands(['2026-01-01'], entries, TODAY);
  const magnesium = layout.periods.find((period) => period.id === 'a');
  assert.ok(magnesium);
  assert.equal(magnesium.end, dayMs('2026-04-01'));
  assert.ok(magnesium.end < dayMs(TODAY)!);
});

test('overlapping periods sit on different lanes and a later gap reuses one', () => {
  const layout = layoutPeriodBands(['2026-01-01', '2026-07-01'], entries, TODAY);
  const byId = Object.fromEntries(layout.periods.map((period) => [period.id, period]));
  assert.notEqual(byId.a.lane, byId.b.lane);
  assert.equal(byId.c.lane, byId.a.lane);
  assert.equal(layout.periods.length, 3);
});

test('the band covers its dates on the collection-date axis', () => {
  const layout = layoutPeriodBands(['2026-01-01', '2026-07-01'], entries, TODAY);
  const magnesium = layout.periods.find((period) => period.id === 'a');
  assert.ok(magnesium);
  const start = fractionOnAxis(magnesium.start, layout.axis);
  const january = fractionOnAxis(dayMs('2026-01-01')!, layout.axis);
  const july = fractionOnAxis(dayMs('2026-07-01')!, layout.axis);
  assert.ok(start > january);
  assert.ok(start < july);
  assert.ok(fractionOnAxis(magnesium.end, layout.axis) > start);
  assert.ok(layout.axis.end > dayMs(TODAY)!);
});

test('a blank name or a broken date is left off the chart', () => {
  const layout = layoutPeriodBands(
    ['2026-01-01'],
    [
      { id: 'blank', title: '   ', startedOn: '2026-01-01', endedOn: null },
      { id: 'bad', title: 'Nope', startedOn: 'yesterday', endedOn: null },
      { id: 'backwards', title: 'Backwards', startedOn: '2026-05-02', endedOn: '2026-05-01' },
    ],
    TODAY,
  );
  assert.equal(layout.periods.length, 0);
});

test('the legend names the mark and does not state an effect', () => {
  const copy = `${enHistory.journalPeriod} ${deHistory.journalPeriod}`;
  assert.equal(enHistory.journalPeriod, 'Journal period');
  assert.equal(deHistory.journalPeriod, 'Journalzeitraum');
  assert.doesNotMatch(copy, /effect|cause|worked|recommend|risk|danger/i);
});

test('the PhenoAge trend does not draw journal periods', () => {
  const tab = readFileSync(
    join(dirname(fileURLToPath(import.meta.url)), '../components/tabs/BiomarkerHistoryTab.tsx'),
    'utf8',
  );
  const trendStart = tab.indexOf('<LineChart');
  const trendEnd = tab.indexOf('</LineChart>');
  assert.ok(trendStart >= 0 && trendEnd > trendStart);
  const trend = tab.slice(trendStart, trendEnd);
  assert.equal(trend.includes('periodLayout'), false);
  assert.equal(trend.includes('journalEntries'), false);
  assert.equal(trend.includes('layoutPeriodBands'), false);
  const svgStart = tab.indexOf('<svg');
  assert.ok(svgStart > trendEnd);
  assert.ok(tab.slice(svgStart).includes('periodLayout'));
});
