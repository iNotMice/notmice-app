import React, { useEffect, useState } from 'react';
import { KeyRound, LogOut, MonitorSmartphone } from 'lucide-react';
import {
  CabinetRequestError,
  changePassword,
  fetchCabinet,
  revokeOtherSessions,
  type CabinetOverview,
} from '../../api/cabinet';
import { TabType } from '../../types';
import { fill } from '../../i18n/fill';
import { useI18n } from '../../i18n/I18nProvider';

interface CabinetSecurityProps {
  navigate: (tab: TabType) => void;
  onSignOut: () => void;
}

const card = 'rounded-xl border border-[#e2e8f0] bg-[#ffffff] p-5 flex flex-col gap-3';
const input =
  'w-full rounded-md border border-[#cbd5e1] px-3 py-2 text-base text-[#0b1c30] focus:border-[#006194] focus:outline-none focus:ring-2 focus:ring-[#006194]/20';

/** Sign-in method, password change, and signing out other devices. */
export const CabinetSecurity: React.FC<CabinetSecurityProps> = ({ navigate, onSignOut }) => {
  const { m } = useI18n();
  const copy = m.cabinet.security;
  const [data, setData] = useState<CabinetOverview | null>(null);
  const [reload, setReload] = useState(0);
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [repeat, setRepeat] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [sessionMessage, setSessionMessage] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void fetchCabinet(controller.signal)
      .then(setData)
      .catch(() => undefined);
    return () => controller.abort();
  }, [reload]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setMessage(null);
    if (next.length < 12) {
      setMessage({ ok: false, text: copy.short });
      return;
    }
    if (next !== repeat) {
      setMessage({ ok: false, text: copy.mismatch });
      return;
    }
    setBusy(true);
    try {
      const revoked = await changePassword(current, next);
      setMessage({ ok: true, text: fill(copy.changed, { count: revoked }) });
      setCurrent('');
      setNext('');
      setRepeat('');
      setReload((value) => value + 1);
    } catch (err) {
      const status = err instanceof CabinetRequestError ? err.status : 0;
      const text =
        status === 400 ? copy.wrongCurrent : status === 422 ? copy.short : status === 429 ? copy.rateLimited : copy.failed;
      setMessage({ ok: false, text });
    } finally {
      setBusy(false);
    }
  };

  const revokeOthers = async () => {
    setSessionMessage(null);
    try {
      const revoked = await revokeOtherSessions();
      setSessionMessage({ ok: true, text: fill(copy.revoked, { count: revoked }) });
      setReload((value) => value + 1);
    } catch {
      setSessionMessage({ ok: false, text: copy.revokeFailed });
    }
  };

  const account = data?.account;

  return (
    <section className="flex flex-col gap-5 max-w-3xl" aria-labelledby="cabinet-security-title">
      <div>
        <h2 id="cabinet-security-title" className="text-xl font-bold text-[#0b1c30]">
          {copy.title}
        </h2>
        <p className="mt-1 text-base text-[#3f4850]">{copy.lead}</p>
      </div>

      <div className={card}>
        <h3 className="text-lg font-bold text-[#0b1c30]">{copy.methodTitle}</h3>
        <p className="break-all text-base text-[#3f4850]">
          {!account
            ? '…'
            : account.signInMethod === 'email' && account.email
              ? fill(copy.emailMethod, { email: account.email })
              : copy.phraseMethod}
        </p>
      </div>

      {account?.signInMethod === 'email' && (
        <form className={card} onSubmit={(event) => void submit(event)} aria-labelledby="password-title" noValidate>
          <h3 id="password-title" className="inline-flex items-center gap-2 text-lg font-bold text-[#0b1c30]">
            <KeyRound className="w-5 h-5 text-[#006194]" aria-hidden="true" />
            {copy.passwordTitle}
          </h3>
          <label className="flex flex-col gap-1 text-[15px] font-medium text-[#0b1c30]">
            {copy.current}
            <input
              type="password"
              autoComplete="current-password"
              value={current}
              onChange={(event) => setCurrent(event.target.value)}
              className={input}
              required
            />
          </label>
          <label className="flex flex-col gap-1 text-[15px] font-medium text-[#0b1c30]">
            {copy.next}
            <input
              type="password"
              autoComplete="new-password"
              minLength={12}
              maxLength={128}
              value={next}
              onChange={(event) => setNext(event.target.value)}
              className={input}
              required
            />
          </label>
          <label className="flex flex-col gap-1 text-[15px] font-medium text-[#0b1c30]">
            {copy.repeat}
            <input
              type="password"
              autoComplete="new-password"
              minLength={12}
              maxLength={128}
              value={repeat}
              onChange={(event) => setRepeat(event.target.value)}
              className={input}
              required
            />
          </label>
          <p className="text-sm text-[#3f4850]">{copy.hint}</p>
          {message && (
            <p className={`text-[15px] ${message.ok ? 'text-[#006947]' : 'text-[#ba1a1a]'}`} role={message.ok ? 'status' : 'alert'}>
              {message.text}
            </p>
          )}
          <button
            type="submit"
            disabled={busy || current === '' || next === ''}
            className="self-start rounded-md bg-[#006194] px-5 py-2.5 text-base font-semibold text-[#ffffff] hover:bg-[#004b73] disabled:opacity-60 cursor-pointer"
          >
            {busy ? copy.saving : copy.save}
          </button>
        </form>
      )}

      <div className={card}>
        <h3 className="inline-flex items-center gap-2 text-lg font-bold text-[#0b1c30]">
          <MonitorSmartphone className="w-5 h-5 text-[#006194]" aria-hidden="true" />
          {copy.sessionsTitle}
        </h3>
        <p className="text-base text-[#3f4850]">{fill(copy.sessionsBody, { count: account?.activeSessions ?? '…' })}</p>
        {sessionMessage && (
          <p
            className={`text-[15px] ${sessionMessage.ok ? 'text-[#006947]' : 'text-[#ba1a1a]'}`}
            role={sessionMessage.ok ? 'status' : 'alert'}
          >
            {sessionMessage.text}
          </p>
        )}
        <div className="flex flex-col gap-2 sm:flex-row">
          <button
            type="button"
            onClick={() => void revokeOthers()}
            className="rounded-md border border-[#cbd5e1] px-4 py-2.5 text-base font-semibold text-[#0b1c30] hover:bg-[#eff4ff] cursor-pointer"
          >
            {copy.revoke}
          </button>
          <button
            type="button"
            onClick={onSignOut}
            className="inline-flex items-center justify-center gap-2 rounded-md border border-[#cbd5e1] px-4 py-2.5 text-base font-semibold text-[#0b1c30] hover:bg-[#eff4ff] cursor-pointer"
          >
            <LogOut className="w-4 h-4" aria-hidden="true" />
            {copy.signOut}
          </button>
        </div>
      </div>

      <div className={card}>
        <h3 className="text-lg font-bold text-[#0b1c30]">{copy.deleteTitle}</h3>
        <p className="text-base text-[#3f4850]">{copy.deleteBody}</p>
        <button
          type="button"
          onClick={() => navigate('data-sovereignty-public-sharing')}
          className="self-start text-base font-semibold text-[#ba1a1a] underline underline-offset-2 cursor-pointer"
        >
          {copy.deleteLink}
        </button>
      </div>
    </section>
  );
};
