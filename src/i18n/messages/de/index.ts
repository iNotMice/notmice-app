import type { AppMessages } from '../en';
import { biomarkers } from './biomarkers';
import { history } from './history';
import { instructions } from './instructions';
import { journal } from './journal';
import { lifestyleUi } from './lifestyleUi';
import { modals } from './modals';
import { nav } from './nav';
import { news } from './news';
import { overview } from './overview';
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
  overview,
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
} satisfies AppMessages;
