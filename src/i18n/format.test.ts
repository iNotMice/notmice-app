import assert from 'node:assert/strict';
import test from 'node:test';
import { formatDate, formatSigned, formatValue } from './format.ts';

test('date-only strings do not shift by a day', () => {
  assert.equal(formatDate('2026-03-01', 'en', 'short'), '03/01/2026');
  assert.match(formatDate('2026-03-01', 'ru'), /^1 марта 2026/);
});

test('values and signed differences follow the locale', () => {
  assert.equal(formatValue(1.5, 'ru'), '1,5');
  assert.equal(formatValue(104, 'en'), '104');
  assert.equal(formatSigned(-4.3, 'ru'), '\u22124,3');
  assert.equal(formatSigned(6.31, 'en'), '+6.3');
});
