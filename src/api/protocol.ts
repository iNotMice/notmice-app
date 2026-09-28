/** Protocol journal API. Maps snake_case payloads to camelCase for the screen. */

export type ProtocolKind = 'drug' | 'supplement' | 'nutrition' | 'activity' | 'sleep' | 'other';

export interface ProtocolEntry {
  id: string;
  kind: ProtocolKind;
  title: string;
  dose: string | null;
  startedOn: string;
  endedOn: string | null;
  note: string | null;
}

export interface ProtocolDraft {
  kind: ProtocolKind;
  title: string;
  dose: string;
  startedOn: string;
  endedOn: string;
  note: string;
}

interface ProtocolEntryPayload {
  id: string;
  kind: ProtocolKind;
  title: string;
  dose: string | null;
  started_on: string;
  ended_on: string | null;
  note: string | null;
}

function apiUrl(path: string): string {
  const base = import.meta.env.VITE_API_BASE_URL ?? '';
  return `${base}${path}`;
}

async function readError(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === 'object' && 'detail' in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === 'string') {
        return detail;
      }
    }
  } catch {
    // Fall through to status text.
  }
  return `Request failed (${response.status})`;
}

function mapEntry(payload: ProtocolEntryPayload): ProtocolEntry {
  return {
    id: payload.id,
    kind: payload.kind,
    title: payload.title,
    dose: payload.dose,
    startedOn: payload.started_on,
    endedOn: payload.ended_on,
    note: payload.note,
  };
}

function toPayload(draft: ProtocolDraft): Record<string, string | null> {
  const dose = draft.dose.trim();
  const note = draft.note.trim();
  const ended = draft.endedOn.trim();
  return {
    kind: draft.kind,
    title: draft.title.trim(),
    dose: dose || null,
    started_on: draft.startedOn,
    ended_on: ended || null,
    note: note || null,
  };
}

export async function listProtocolEntries(): Promise<ProtocolEntry[]> {
  const response = await fetch(apiUrl('/api/v1/protocol'), { credentials: 'include' });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  const body = (await response.json()) as { entries: ProtocolEntryPayload[] };
  return body.entries.map(mapEntry);
}

export async function createProtocolEntry(draft: ProtocolDraft): Promise<ProtocolEntry> {
  const response = await fetch(apiUrl('/api/v1/protocol'), {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(toPayload(draft)),
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return mapEntry((await response.json()) as ProtocolEntryPayload);
}

export async function replaceProtocolEntry(id: string, draft: ProtocolDraft): Promise<ProtocolEntry> {
  const response = await fetch(apiUrl(`/api/v1/protocol/${id}`), {
    method: 'PATCH',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(toPayload(draft)),
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return mapEntry((await response.json()) as ProtocolEntryPayload);
}

export async function deleteProtocolEntry(id: string): Promise<void> {
  const response = await fetch(apiUrl(`/api/v1/protocol/${id}`), {
    method: 'DELETE',
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
}
