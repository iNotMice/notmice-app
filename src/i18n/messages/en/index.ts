import { biomarkers } from './biomarkers';
import { history } from './history';
import { instructions } from './instructions';
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

export const enMessages = {
  nav,
  news,
  shell,
  overview,
  upload,
  review,
  phenoage,
  history,
  instructions,
  sovereignty,
  modals,
  report,
  biomarkers,
  lifestyleUi,
};

export type Messages = typeof enMessages;

/** String literals from English become `string`, so another language can satisfy the same shape. */
export type Widen<T> = T extends string
  ? string
  : T extends number
    ? number
    : T extends boolean
      ? boolean
      : T extends readonly (infer U)[]
        ? Widen<U>[]
        : T extends object
          ? { [K in keyof T]: Widen<T[K]> }
          : T;

export type AppMessages = Widen<Messages>;
