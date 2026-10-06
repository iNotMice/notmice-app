import type { AppMessages } from '../en';
import { biomarkers } from './biomarkers';
import { cabinet } from './cabinet';
import { history } from './history';
import { home } from './home';
import { instructions } from './instructions';
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
import { specialists } from './specialists';
import { upload } from './upload';

export const frMessages = {
  nav,
  news,
  shell,
  home,
  specialists,
  cabinet,
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
