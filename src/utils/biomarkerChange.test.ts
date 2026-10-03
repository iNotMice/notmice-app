import assert from 'node:assert/strict';
import test from 'node:test';
import {
  summarizeLatestChange,
  type BiomarkerMeasurement,
} from './biomarkerChange.ts';

const measurements: BiomarkerMeasurement[] = [
  { date: '2026-01-10', lab: 'Lab A', value: 4.2, unit: 'mg/L' },
  { date: '2026-03-15', lab: 'Lab B', value: 5.1, unit: 'mg/L' },
];

test('compares the latest two values in the same unit, independent of input order', () => {
  const result = summarizeLatestChange(measurements);
  assert.equal(result.kind, 'compared');
  if (result.kind === 'compared') {
    assert.equal(result.latest, measurements[1]);
    assert.equal(result.previous, measurements[0]);
    assert.ok(Math.abs(result.difference - 0.9) < 1e-12);
  }
});

test('does not compare measurements expressed in different units', () => {
  const result = summarizeLatestChange([
    measurements[0],
    { date: '2026-03-15', lab: 'Lab B', value: 51, unit: 'mg/dL' },
  ]);
  assert.equal(result.kind, 'unit-mismatch');
});

test('reports insufficient data when fewer than two valid values are present', () => {
  assert.deepEqual(summarizeLatestChange([measurements[0]]), {
    kind: 'insufficient',
    latest: measurements[0],
  });
  assert.deepEqual(
    summarizeLatestChange([{ ...measurements[0], value: Number.NaN }]),
    { kind: 'insufficient', latest: null },
  );
});

test('orders measurements by date and does not label direction as improvement or risk', async () => {
  const result = summarizeLatestChange([...measurements].reverse());
  assert.equal(result.kind, 'compared');
  if (result.kind === 'compared') {
    assert.equal(result.latest.date, '2026-03-15');
    assert.ok(Math.abs(result.difference - 0.9) < 1e-12);
  }

  const { history: en } = await import('../i18n/messages/en/history.ts');
  const { history: de } = await import('../i18n/messages/de/history.ts');
  assert.match(en.changeDisclaimer, /not a medical interpretation/i);
  assert.match(de.changeDisclaimer, /keine medizinische Interpretation/i);
  assert.doesNotMatch(
    `${en.changeCompared} ${de.changeCompared}`,
    /improv|worsen|risk|danger|verbesser|verschlechter|risiko|gefah/i,
  );
});
