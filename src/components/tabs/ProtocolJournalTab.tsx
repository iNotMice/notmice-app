import React, { useEffect, useState } from 'react';
import { NotebookPen } from 'lucide-react';
import {
  ProtocolDraft,
  ProtocolEntry,
  ProtocolKind,
  createProtocolEntry,
  deleteProtocolEntry,
  listProtocolEntries,
  replaceProtocolEntry,
} from '../../api/protocol';
import { useI18n } from '../../i18n/I18nProvider';

const KINDS: ProtocolKind[] = ['drug', 'supplement', 'nutrition', 'activity', 'sleep', 'other'];

const EMPTY_DRAFT: ProtocolDraft = {
  kind: 'supplement',
  title: '',
  dose: '',
  startedOn: '',
  endedOn: '',
  note: '',
};

interface ProtocolJournalTabProps {
  isAuthenticated: boolean;
  onRequestAuth: () => void;
}

function draftFromEntry(entry: ProtocolEntry): ProtocolDraft {
  return {
    kind: entry.kind,
    title: entry.title,
    dose: entry.dose ?? '',
    startedOn: entry.startedOn,
    endedOn: entry.endedOn ?? '',
    note: entry.note ?? '',
  };
}

export const ProtocolJournalTab: React.FC<ProtocolJournalTabProps> = ({
  isAuthenticated,
  onRequestAuth,
}) => {
  const { m } = useI18n();
  const copy = m.journal;
  const [entries, setEntries] = useState<ProtocolEntry[]>([]);
  const [draft, setDraft] = useState<ProtocolDraft>(EMPTY_DRAFT);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      setEntries([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    void listProtocolEntries()
      .then((rows) => {
        if (!cancelled) {
          setEntries(rows);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError(copy.errorGeneric);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, copy.errorGeneric]);

  const resetForm = () => {
    setDraft(EMPTY_DRAFT);
    setEditingId(null);
  };

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (draft.endedOn && draft.startedOn && draft.endedOn < draft.startedOn) {
      setError(copy.errorEndBeforeStart);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      if (editingId) {
        const saved = await replaceProtocolEntry(editingId, draft);
        setEntries((current) => current.map((row) => (row.id === saved.id ? saved : row)));
      } else {
        const saved = await createProtocolEntry(draft);
        setEntries((current) => [...current, saved].sort((a, b) => a.startedOn.localeCompare(b.startedOn)));
      }
      resetForm();
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : '';
      if (message === 'Forbidden field') {
        setError(copy.errorForbidden);
      } else if (message.includes('End date')) {
        setError(copy.errorEndBeforeStart);
      } else {
        setError(copy.errorGeneric);
      }
    } finally {
      setSaving(false);
    }
  };

  const onDelete = async (entry: ProtocolEntry) => {
    if (!window.confirm(copy.deleteConfirm)) {
      return;
    }
    setError(null);
    try {
      await deleteProtocolEntry(entry.id);
      setEntries((current) => current.filter((row) => row.id !== entry.id));
      if (editingId === entry.id) {
        resetForm();
      }
    } catch {
      setError(copy.errorGeneric);
    }
  };

  return (
    <div className="w-full flex flex-col gap-8" id="protocol-journal">
      <div className="border-b border-[#e2e8f0] pb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="bg-[#cce5ff] text-[#004b73] font-['JetBrains_Mono'] text-xs font-semibold px-2 py-0.5 rounded">
            {copy.stage}
          </span>
          <span className="font-['JetBrains_Mono'] text-xs text-[#565e74]">{copy.stageMeta}</span>
        </div>
        <h2 className="font-['Inter'] text-2xl lg:text-3xl font-bold text-[#0b1c30]">{copy.title}</h2>
        <p className="font-['Inter'] text-sm text-[#3f4850] mt-1 max-w-2xl">{copy.lead}</p>
      </div>

      {!isAuthenticated ? (
        <section className="bg-[#ffffff] border border-[#e2e8f0] rounded-lg p-5 flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="flex items-start gap-3 flex-1">
            <div className="w-8 h-8 rounded-full bg-[#cce5ff] text-[#004b73] flex items-center justify-center shrink-0">
              <NotebookPen className="w-4 h-4" />
            </div>
            <p className="font-['Inter'] text-sm text-[#3f4850]">{copy.signIn}</p>
          </div>
          <button
            type="button"
            onClick={onRequestAuth}
            className="shrink-0 bg-[#007bb9] hover:bg-[#006194] text-white px-4 py-2 rounded font-['Inter'] text-sm font-semibold cursor-pointer"
          >
            {copy.signInAction}
          </button>
        </section>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          <form
            onSubmit={(event) => void onSubmit(event)}
            className="lg:col-span-5 bg-[#ffffff] border border-[#e2e8f0] rounded-lg p-5 flex flex-col gap-4"
          >
            <h2 className="font-['Inter'] text-lg font-semibold text-[#0b1c30]">
              {editingId ? copy.editTitle : copy.formTitle}
            </h2>
            <label className="flex flex-col gap-1 font-['Inter'] text-sm text-[#3f4850]">
              {copy.kind}
              <select
                value={draft.kind}
                onChange={(event) => setDraft({ ...draft, kind: event.target.value as ProtocolKind })}
                className="px-2.5 py-2 bg-[#eff4ff] border border-[#cbd5e1] rounded text-sm text-[#0b1c30]"
              >
                {KINDS.map((kind) => (
                  <option key={kind} value={kind}>
                    {copy.kinds[kind]}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 font-['Inter'] text-sm text-[#3f4850]">
              {copy.name}
              <input
                required
                maxLength={120}
                value={draft.title}
                onChange={(event) => setDraft({ ...draft, title: event.target.value })}
                className="px-2.5 py-2 bg-[#ffffff] border border-[#cbd5e1] rounded text-sm text-[#0b1c30]"
              />
            </label>
            <label className="flex flex-col gap-1 font-['Inter'] text-sm text-[#3f4850]">
              {copy.dose}
              <input
                maxLength={80}
                value={draft.dose}
                placeholder={copy.optional}
                onChange={(event) => setDraft({ ...draft, dose: event.target.value })}
                className="px-2.5 py-2 bg-[#ffffff] border border-[#cbd5e1] rounded text-sm text-[#0b1c30]"
              />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1 font-['Inter'] text-sm text-[#3f4850]">
                {copy.startedOn}
                <input
                  required
                  type="date"
                  value={draft.startedOn}
                  onChange={(event) => setDraft({ ...draft, startedOn: event.target.value })}
                  className="px-2.5 py-2 bg-[#ffffff] border border-[#cbd5e1] rounded text-sm text-[#0b1c30]"
                />
              </label>
              <label className="flex flex-col gap-1 font-['Inter'] text-sm text-[#3f4850]">
                {copy.endedOn}
                <input
                  type="date"
                  value={draft.endedOn}
                  onChange={(event) => setDraft({ ...draft, endedOn: event.target.value })}
                  className="px-2.5 py-2 bg-[#ffffff] border border-[#cbd5e1] rounded text-sm text-[#0b1c30]"
                />
              </label>
            </div>
            <p className="font-['Inter'] text-xs text-[#565e74] -mt-2">{copy.endedHint}</p>
            <label className="flex flex-col gap-1 font-['Inter'] text-sm text-[#3f4850]">
              {copy.note}
              <textarea
                maxLength={2000}
                rows={3}
                value={draft.note}
                placeholder={copy.optional}
                onChange={(event) => setDraft({ ...draft, note: event.target.value })}
                className="px-2.5 py-2 bg-[#ffffff] border border-[#cbd5e1] rounded text-sm text-[#0b1c30]"
              />
            </label>
            {error && (
              <p className="font-['Inter'] text-sm text-[#3f4850] bg-[#f8f9ff] border border-[#cbd5e1] rounded px-2.5 py-1.5">
                {error}
              </p>
            )}
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={saving}
                className="bg-[#007bb9] hover:bg-[#006194] disabled:opacity-60 text-white px-4 py-2 rounded font-['Inter'] text-sm font-semibold cursor-pointer"
              >
                {editingId ? copy.saveChanges : copy.save}
              </button>
              {editingId && (
                <button
                  type="button"
                  onClick={resetForm}
                  className="bg-[#eff4ff] hover:bg-[#e5eeff] text-[#0b1c30] px-4 py-2 rounded font-['Inter'] text-sm font-medium border border-[#dce9ff] cursor-pointer"
                >
                  {copy.cancel}
                </button>
              )}
            </div>
          </form>

          <section className="lg:col-span-7 flex flex-col gap-3">
            <h2 className="font-['Inter'] text-lg font-semibold text-[#0b1c30]">{copy.listTitle}</h2>
            {loading ? (
              <p className="font-['Inter'] text-sm text-[#565e74]">{copy.loading}</p>
            ) : entries.length === 0 ? (
              <p className="font-['Inter'] text-sm text-[#565e74]">{copy.empty}</p>
            ) : (
              <ul className="flex flex-col gap-3">
                {entries.map((entry) => (
                  <li key={entry.id} className="bg-[#ffffff] border border-[#e2e8f0] rounded-lg p-4">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <h3 className="font-['Inter'] text-base font-semibold text-[#0b1c30]">{entry.title}</h3>
                      <span className="font-['JetBrains_Mono'] text-[11px] text-[#004b73] bg-[#cce5ff] px-2 py-0.5 rounded">
                        {copy.kinds[entry.kind]}
                      </span>
                    </div>
                    <p className="font-['JetBrains_Mono'] text-xs text-[#565e74] mt-1">
                      {entry.startedOn} – {entry.endedOn ?? copy.ongoing}
                      {entry.dose ? ` · ${entry.dose}` : ''}
                    </p>
                    {entry.note && (
                      <p className="font-['Inter'] text-sm text-[#3f4850] mt-2">{entry.note}</p>
                    )}
                    <div className="flex gap-2 mt-3">
                      <button
                        type="button"
                        onClick={() => {
                          setEditingId(entry.id);
                          setDraft(draftFromEntry(entry));
                          setError(null);
                        }}
                        className="bg-[#eff4ff] hover:bg-[#e5eeff] text-[#0b1c30] px-3 py-1.5 rounded font-['Inter'] text-xs font-medium border border-[#dce9ff] cursor-pointer"
                      >
                        {copy.edit}
                      </button>
                      <button
                        type="button"
                        onClick={() => void onDelete(entry)}
                        className="text-[#3f4850] hover:bg-[#f8f9ff] px-3 py-1.5 rounded font-['Inter'] text-xs font-medium border border-[#e2e8f0] cursor-pointer"
                      >
                        {copy.remove}
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </div>
  );
};
