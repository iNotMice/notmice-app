import assert from 'node:assert/strict';
import test from 'node:test';
import { isSessionExpiry } from './session.ts';

test('a 401 from a private participant endpoint means the session ended', () => {
  assert.ok(isSessionExpiry('/api/v1/accounts/me/cabinet', 401));
  assert.ok(isSessionExpiry('/api/v1/accounts/me', 401));
  assert.ok(isSessionExpiry('/api/v1/uploads/results', 401));
  assert.ok(isSessionExpiry('/api/v1/protocol', 401));
});

test('a wrong password or a laboratory 401 is not a participant session expiry', () => {
  assert.ok(!isSessionExpiry('/api/v1/accounts/login/email', 401));
  assert.ok(!isSessionExpiry('/api/v1/accounts/confirm', 401));
  assert.ok(!isSessionExpiry('/api/v1/lab/me', 401));
  assert.ok(!isSessionExpiry('/api/v1/accounts/me/cabinet', 500));
});
