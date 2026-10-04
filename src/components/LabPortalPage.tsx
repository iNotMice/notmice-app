import { useEffect, useState, type FormEvent } from 'react';
import { ArrowLeft, Building2, CheckCircle2, FlaskConical, LoaderCircle, ShieldCheck } from 'lucide-react';
import {
  acceptLabDua,
  fetchLabAccount,
  loginLab,
  logoutLab,
  registerLab,
  type LabAccount,
  type LabOrganizationType,
} from '../api/labAccounts';
import { CohortExplorer } from './CohortExplorer';
import { useI18n } from '../i18n/I18nProvider';
import type { AppMessages } from '../i18n/messages/en';
import { LanguageSwitcher } from './LanguageSwitcher';

type FormMode = 'register' | 'login';

const organizationTypes: LabOrganizationType[] = [
  'laboratory',
  'university',
  'research_institute',
  'company',
  'other',
];

function statusClass(status: string): string {
  if (status === 'verified') {
    return 'border-emerald-200 bg-emerald-50 text-emerald-800';
  }
  if (status === 'rejected') {
    return 'border-rose-200 bg-rose-50 text-rose-800';
  }
  return 'border-amber-200 bg-amber-50 text-amber-900';
}

export function LabPortalPage() {
  const { m } = useI18n();
  const copy = m.laboratory;
  const [mode, setMode] = useState<FormMode>('register');
  const [account, setAccount] = useState<LabAccount | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [organizationName, setOrganizationName] = useState('');
  const [organizationType, setOrganizationType] = useState<LabOrganizationType>('laboratory');
  const [country, setCountry] = useState('');

  useEffect(() => {
    let cancelled = false;
    void fetchLabAccount()
      .then((current) => {
        if (!cancelled) {
          setAccount(current);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : copy.loadFailed);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [copy.loadFailed]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('confirmed') === '1') {
      setNotice(copy.emailConfirmed);
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, [copy.emailConfirmed]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      if (mode === 'register') {
        await registerLab({
          organizationName,
          organizationType,
          country: country.trim().toUpperCase(),
          email,
          password,
        });
        setNotice(copy.registrationSent);
        setPassword('');
      } else {
        setAccount(await loginLab(email, password));
        setPassword('');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : copy.requestFailed);
    } finally {
      setBusy(false);
    }
  };

  const signOut = async () => {
    setBusy(true);
    setError(null);
    try {
      await logoutLab();
      setAccount(null);
      setMode('login');
      setNotice(copy.signedOut);
    } catch (err) {
      setError(err instanceof Error ? err.message : copy.requestFailed);
    } finally {
      setBusy(false);
    }
  };

  const acceptDua = async () => {
    setBusy(true);
    setError(null);
    try {
      setAccount(await acceptLabDua());
      setNotice(copy.duaAccepted);
    } catch (err) {
      setError(err instanceof Error ? err.message : copy.requestFailed);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f5f8fc] text-[#0b1c30]">
      <header className="border-b border-[#dce5ef] bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
          <a href="/" className="inline-flex items-center gap-2 text-sm font-semibold text-[#31516c] hover:text-[#006194]">
            <ArrowLeft className="h-4 w-4" />
            {copy.backToPlatform}
          </a>
          <LanguageSwitcher />
        </div>
      </header>

      <main className={`mx-auto grid max-w-6xl gap-10 px-5 py-10 ${account ? 'md:grid-cols-1' : 'md:grid-cols-[minmax(0,1fr)_minmax(320px,0.8fr)]'} md:py-16`}>
        <section className="pt-2">
          <div className="mb-5 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-[#e5f2fb] text-[#006194]">
            <FlaskConical className="h-6 w-6" />
          </div>
          <p className="mb-3 text-xs font-bold uppercase tracking-[0.18em] text-[#1673a5]">
            {copy.eyebrow}
          </p>
          <h1 className="max-w-xl text-3xl font-bold tracking-tight sm:text-4xl">{copy.title}</h1>
          <p className="mt-4 max-w-xl text-base leading-7 text-[#526579]">{copy.intro}</p>
          <div className="mt-8 space-y-4">
            {[copy.stepEmail, copy.stepReview, copy.stepAccess].map((step, index) => (
              <div key={step} className="flex items-start gap-3">
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white text-sm font-semibold text-[#006194] ring-1 ring-[#cfdfec]">
                  {index + 1}
                </span>
                <p className="text-sm leading-6 text-[#3f5368]">{step}</p>
              </div>
            ))}
          </div>
          <div className="mt-8 flex items-start gap-3 rounded-xl border border-[#d6e5ef] bg-white p-4 text-sm leading-6 text-[#506478]">
            <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-[#1673a5]" />
            <p>{copy.privacyNote}</p>
          </div>
        </section>

        <section className="rounded-2xl border border-[#dce5ef] bg-white p-5 shadow-[0_12px_40px_rgba(22,55,85,0.08)] sm:p-7">
          {loading ? (
            <div className="flex min-h-72 items-center justify-center text-[#62758a]" role="status">
              <LoaderCircle className="mr-2 h-5 w-5 animate-spin" />
              {copy.loading}
            </div>
          ) : account ? (
            <LabDashboard
              account={account}
              busy={busy}
              copy={copy}
              error={error}
              notice={notice}
              onAcceptDua={() => void acceptDua()}
              onSignOut={() => void signOut()}
            />
          ) : (
            <div>
              <div className="mb-6 flex rounded-lg bg-[#f0f4f8] p-1" role="tablist" aria-label={copy.formMode}>
                {(['register', 'login'] as const).map((nextMode) => (
                  <button
                    key={nextMode}
                    type="button"
                    role="tab"
                    aria-selected={mode === nextMode}
                    onClick={() => {
                      setMode(nextMode);
                      setError(null);
                      setNotice(null);
                    }}
                    className={`flex-1 rounded-md px-3 py-2 text-sm font-semibold transition ${
                      mode === nextMode ? 'bg-white text-[#0b1c30] shadow-sm' : 'text-[#65768a]'
                    }`}
                  >
                    {nextMode === 'register' ? copy.registerTab : copy.loginTab}
                  </button>
                ))}
              </div>

              {notice && <p className="mb-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}
              {error && <p className="mb-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-800" role="alert">{error}</p>}

              <form onSubmit={(event) => void submit(event)} className="space-y-4">
                {mode === 'register' && (
                  <>
                    <label className="block text-sm font-medium text-[#31465b]">
                      {copy.organizationName}
                      <span className="mt-1.5 block">
                        <input
                          required
                          maxLength={200}
                          autoComplete="organization"
                          value={organizationName}
                          onChange={(event) => setOrganizationName(event.target.value)}
                          className={inputClass}
                        />
                      </span>
                    </label>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <label className="block text-sm font-medium text-[#31465b]">
                        {copy.organizationType}
                        <select
                          value={organizationType}
                          onChange={(event) => setOrganizationType(event.target.value as LabOrganizationType)}
                          className={inputClass}
                        >
                          {organizationTypes.map((type) => (
                            <option key={type} value={type}>{copy.organizationTypes[type]}</option>
                          ))}
                        </select>
                      </label>
                      <label className="block text-sm font-medium text-[#31465b]">
                        {copy.countryCode}
                        <input
                          required
                          minLength={2}
                          maxLength={2}
                          pattern="[A-Za-z]{2}"
                          autoComplete="country"
                          value={country}
                          onChange={(event) => setCountry(event.target.value.toUpperCase())}
                          placeholder="DE"
                          className={inputClass}
                        />
                      </label>
                    </div>
                  </>
                )}

                <label className="block text-sm font-medium text-[#31465b]">
                  {copy.email}
                  <input
                    required
                    type="email"
                    maxLength={254}
                    autoComplete="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className={inputClass}
                  />
                </label>
                <label className="block text-sm font-medium text-[#31465b]">
                  {copy.password}
                  <input
                    required
                    type="password"
                    minLength={mode === 'register' ? 12 : 1}
                    maxLength={128}
                    autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className={inputClass}
                  />
                  {mode === 'register' && <span className="mt-1 block text-xs font-normal text-[#748498]">{copy.passwordHint}</span>}
                </label>

                <button
                  type="submit"
                  disabled={busy}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[#006194] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#004e78] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {busy && <LoaderCircle className="h-4 w-4 animate-spin" />}
                  {mode === 'register' ? copy.createAccount : copy.signIn}
                </button>
              </form>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

const inputClass =
  'mt-1.5 block w-full rounded-lg border border-[#ccd8e3] bg-white px-3 py-2.5 text-sm text-[#172e43] outline-none transition placeholder:text-[#92a1af] focus:border-[#1673a5] focus:ring-2 focus:ring-[#1673a5]/15';

interface LabDashboardProps {
  account: LabAccount;
  busy: boolean;
  copy: AppMessages['laboratory'];
  error: string | null;
  notice: string | null;
  onAcceptDua: () => void;
  onSignOut: () => void;
}

function LabDashboard({
  account,
  busy,
  copy,
  error,
  notice,
  onAcceptDua,
  onSignOut,
}: LabDashboardProps) {
  const org = account.organization;
  const canAcceptDua =
    org.verification_status === 'verified' &&
    org.current_dua_version !== null &&
    org.dua_version !== org.current_dua_version;

  return (
    <div>
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <div className="mb-2 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-[#e5f2fb] text-[#006194]">
            <Building2 className="h-5 w-5" />
          </div>
          <h2 className="text-xl font-bold">{copy.dashboardTitle}</h2>
          <p className="mt-1 text-sm text-[#607286]">{account.email}</p>
        </div>
        <button type="button" onClick={onSignOut} disabled={busy} className="text-sm font-semibold text-[#526579] hover:text-[#006194] disabled:opacity-60">
          {copy.signOut}
        </button>
      </div>

      {notice && <p className="mb-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}
      {error && <p className="mb-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-800" role="alert">{error}</p>}

      <div className="rounded-xl border border-[#e1e8ef] p-4">
        <p className="text-xs font-bold uppercase tracking-wider text-[#76879a]">{copy.organization}</p>
        <p className="mt-2 text-lg font-semibold">{org.name}</p>
        <p className="mt-1 text-sm text-[#607286]">
          {copy.organizationTypes[org.organization_type]} · {org.country}
        </p>
        <div className={`mt-4 inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-semibold ${statusClass(org.verification_status)}`}>
          {org.verification_status === 'verified' ? <CheckCircle2 className="h-4 w-4" /> : <ShieldCheck className="h-4 w-4" />}
          {copy.statuses[org.verification_status]}
        </div>
      </div>

      <div className="mt-4 rounded-xl bg-[#f5f8fb] p-4">
        <h3 className="font-semibold">{copy.accessTitle}</h3>
        <p className="mt-2 text-sm leading-6 text-[#596d81]">
          {org.verification_status === 'pending'
            ? copy.pendingHelp
            : org.verification_status === 'rejected'
              ? copy.rejectedHelp
              : org.current_dua_version === null
                ? copy.duaUnavailable
                : org.dua_version === org.current_dua_version
                  ? copy.accessGranted
                  : copy.duaNeedsAcceptance.replace('{version}', org.current_dua_version)}
        </p>
        {org.dua_version && (
          <p className="mt-2 text-xs text-[#718398]">
            {copy.acceptedDua}: {org.dua_version}
          </p>
        )}
        {canAcceptDua && (
          <button
            type="button"
            onClick={onAcceptDua}
            disabled={busy}
            className="mt-4 rounded-lg bg-[#006194] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#004e78] disabled:opacity-60"
          >
            {copy.acceptDua}
          </button>
        )}
      </div>

      <p className="mt-5 text-xs leading-5 text-[#7b8b9c]">{copy.cabinetNote}</p>
      {org.verification_status === 'verified' &&
        org.current_dua_version !== null &&
        org.dua_version === org.current_dua_version && (
          <CohortExplorer copy={copy.explorer} />
        )}
    </div>
  );
}
