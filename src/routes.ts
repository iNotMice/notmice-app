import { TabType } from './types';

/** Public pages that can be linked to. Every other tab lives at the site root. */
const TAB_PATHS: Partial<Record<TabType, string>> = {
  specialists: '/specialists',
  'user-instructions': '/guide',
};

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
