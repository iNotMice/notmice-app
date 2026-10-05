import type { AppMessages } from '../en';
// Sections rewritten in October 2026 show in English until a German translation exists.
import { home } from '../en/home';
import { instructions } from '../en/instructions';
import { specialists } from '../en/specialists';
import { biomarkers } from './biomarkers';
import { history } from './history';
import { journal } from './journal';
import { lifestyleUi } from './lifestyleUi';
import { laboratory } from './laboratory';
import { modals } from './modals';
import { nav } from './nav';
import { news } from './news';
import { phenoage } from './phenoage';
import { report } from './report';
import { review } from './review';
import { shell } from './shell';
import { sovereignty } from './sovereignty';
import { upload } from './upload';

export const deMessages = {
  nav,
  news,
  shell,
  home,
  specialists,
  upload,
  review,
  phenoage,
  history,
  instructions,
  journal,
  sovereignty,
  modals,
  report,
  biomarkers,
  lifestyleUi,
  laboratory,
} satisfies AppMessages;
