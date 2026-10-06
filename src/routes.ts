import { TabType } from './types';

/** Public pages that can be linked to. Every other tab lives at the site root. */
const TAB_PATHS: Partial<Record<TabType, string>> = {
  specialists: '/specialists',
  'user-instructions': '/guide',
  cabinet: '/account',
  'cabinet-tests': '/account/tests',
  'biomarker-history': '/account/markers',
  'protocol-journal': '/account/journal',
  'data-sovereignty-public-sharing': '/account/data',
  'cabinet-security': '/account/security',
};

/** Personal account sections in menu order, with their label key. */
export const CABINET_SECTIONS = [
  { tab: 'cabinet', key: 'overview' },
  { tab: 'cabinet-tests', key: 'tests' },
  { tab: 'biomarker-history', key: 'markers' },
  { tab: 'protocol-journal', key: 'journal' },
  { tab: 'data-sovereignty-public-sharing', key: 'data' },
  { tab: 'cabinet-security', key: 'security' },
] as const satisfies readonly { tab: TabType; key: string }[];

export type CabinetSectionKey = (typeof CABINET_SECTIONS)[number]['key'];

export function isCabinetTab(tab: TabType): boolean {
  return CABINET_SECTIONS.some((section) => section.tab === tab);
}

export const SPECIALIST_PAGES = ['method', 'limits', 'data', 'labs', 'contact'] as const;
export type SpecialistPage = (typeof SPECIALIST_PAGES)[number];

function normalise(pathname: string): string {
  const trimmed = pathname.replace(/\/+$/, '');
  return trimmed === '' ? '/' : trimmed;
}

export function pathForTab(tab: TabType): string {
  return TAB_PATHS[tab] ?? '/';
}

/** Tab for a path, or null when the path belongs to the root tabs. */
export function tabFromPath(pathname: string): TabType | null {
  const path = normalise(pathname);
  for (const [tab, tabPath] of Object.entries(TAB_PATHS)) {
    if (tabPath === path) {
      return tab as TabType;
    }
  }
  return null;
}

export function isSpecialistPage(value: string): value is SpecialistPage {
  return (SPECIALIST_PAGES as readonly string[]).includes(value);
}

/** `#method` → `method`, anything else → null. */
export function specialistPageFromHash(hash: string): SpecialistPage | null {
  const value = hash.replace(/^#/, '');
  return isSpecialistPage(value) ? value : null;
}
