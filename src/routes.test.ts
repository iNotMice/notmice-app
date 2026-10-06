import assert from 'node:assert/strict';
import test from 'node:test';
import { CABINET_SECTIONS, isCabinetTab, pathForTab, specialistPageFromHash, tabFromPath } from './routes.ts';

test('every cabinet section has its own address and round-trips', () => {
  for (const section of CABINET_SECTIONS) {
    const path = pathForTab(section.tab);
    assert.ok(path.startsWith('/account'));
    assert.equal(tabFromPath(path), section.tab);
    assert.equal(tabFromPath(`${path}/`), section.tab);
    assert.ok(isCabinetTab(section.tab));
  }
});

test('public tabs are not cabinet sections and root tabs live at /', () => {
  assert.equal(isCabinetTab('overview-landing'), false);
  assert.equal(isCabinetTab('specialists'), false);
  assert.equal(pathForTab('upload-lab'), '/');
  assert.equal(tabFromPath('/'), null);
  assert.equal(tabFromPath('/lab'), null);
});

test('specialist pages come from the hash only when known', () => {
  assert.equal(specialistPageFromHash('#limits'), 'limits');
  assert.equal(specialistPageFromHash('#nope'), null);
});
