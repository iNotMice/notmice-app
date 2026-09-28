import React, { useEffect, useState } from 'react';
import { X, KeyRound, Copy, Check, Download, LogOut, ShieldAlert, LoaderCircle } from 'lucide-react';
import { fill } from '../i18n/fill';
import { useI18n } from '../i18n/I18nProvider';

interface SeedPhraseModalProps {
  isOpen: boolean;
  onClose: () => void;
  publicId: string | null;
  revealedMnemonic: string[] | null;
  isAuthenticated: boolean;
  isBusy: boolean;
  error: string | null;
  notice: 'check-email' | 'reset-sent' | null;
  resetToken: string | null;
  confirmToken: string | null;
  onConfirmEmail: () => void;
  onRegister: (email: string, password: string, researchReuse: boolean) => void;
  onEmailLogin: (email: string, password: string) => void;
  onRequestReset: (email: string) => void;
  onResetPassword: (password: string) => void;
  onLogin: (mnemonic: string) => void;
  onLogout: () => void;
  onConfirmPhraseSaved: () => void;
}

export const SeedPhraseModal: React.FC<SeedPhraseModalProps> = ({
  isOpen,
  onClose,
  publicId,
  revealedMnemonic,
  isAuthenticated,
  isBusy,
  error,
  notice,
  resetToken,
  confirmToken,
  onConfirmEmail,
  onRegister,
  onEmailLogin,
  onRequestReset,
  onResetPassword,
  onLogin,
  onLogout,
  onConfirmPhraseSaved,
}) => {
  const { m } = useI18n();
  const copy = m.modals;
  const [copied, setCopied] = useState(false);
  const [phraseCaptured, setPhraseCaptured] = useState(false);
  const [savedChecked, setSavedChecked] = useState(false);
  const [restorePhrase, setRestorePhrase] = useState('');
  const [mode, setMode] = useState<'login' | 'register' | 'reset'>('login');
  const [showPhrase, setShowPhrase] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordAgain, setPasswordAgain] = useState('');
  const [healthChecked, setHealthChecked] = useState(false);
  const [researchChecked, setResearchChecked] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    setPhraseCaptured(false);
    setSavedChecked(false);
    setCopied(false);
  }, [revealedMnemonic]);

  const showingReveal = Boolean(revealedMnemonic && revealedMnemonic.length === 12);
  const canContinue = savedChecked && phraseCaptured;

  const requestClose = () => {
    if (showingReveal) return;
    onClose();
  };

  if (!isOpen) return null;

  const handleCopy = () => {
    if (!revealedMnemonic) return;
    void navigator.clipboard.writeText(revealedMnemonic.join(' ')).then(() => {
      setCopied(true);
      setPhraseCaptured(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleDownload = () => {
    if (!revealedMnemonic) return;
    const blob = new Blob([`${revealedMnemonic.join(' ')}\n`], {
      type: 'text/plain;charset=utf-8',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'notmice-recovery-phrase.txt';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setPhraseCaptured(true);
  };

  const handleLogout = () => {
    setRestorePhrase('');
    setSavedChecked(false);
    setCopied(false);
    setPhraseCaptured(false);
    onLogout();
  };

  const handleLogin = () => {
    onLogin(restorePhrase);
  };

  const submitEmail = () => {
    setFormError(null);
    if (password.length < 12) {
      setFormError(copy.passwordTooShort);
      return;
    }
    if (mode === 'register') {
      if (password !== passwordAgain) {
        setFormError(copy.passwordsDiffer);
        return;
      }
      if (!healthChecked) {
        setFormError(copy.consentRequired);
        return;
      }
      onRegister(email.trim(), password, researchChecked);
      return;
    }
    if (mode === 'reset' && resetToken) {
      onResetPassword(password);
      return;
    }
    if (mode === 'reset') {
      onRequestReset(email.trim());
      return;
    }
    onEmailLogin(email.trim(), password);
  };

  const showingSignedIn = isAuthenticated && !showingReveal;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#0b1c30]/50 backdrop-blur-xs animate-in fade-in"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) requestClose();
      }}
    >
      <div className="bg-[#ffffff] rounded-xl border border-[#cbd5e1] shadow-2xl max-w-xl w-full overflow-hidden flex flex-col">
        <div className="px-6 py-4 border-b border-[#e2e8f0] flex items-center justify-between bg-[#eff4ff]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded bg-[#cce5ff] flex items-center justify-center text-[#006194]">
              <KeyRound className="w-5 h-5 text-[#006194]" />
            </div>
            <div>
              <h3 className="font-['Inter'] text-base font-bold text-[#0b1c30]">
                {copy.accountTitle}
              </h3>
              <p className="font-['JetBrains_Mono'] text-xs text-[#565e74]">
                {publicId ? fill(copy.accountId, { id: publicId }) : copy.accountPrompt}
              </p>
            </div>
          </div>
          <button
            onClick={requestClose}
            disabled={showingReveal}
            aria-label={showingReveal ? copy.saveBeforeClose : copy.close}
            title={showingReveal ? copy.saveBeforeClose : undefined}
            className="p-1.5 rounded-lg text-[#565e74] hover:bg-[#e2e8f0] hover:text-[#0b1c30] transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {error && (
            <div className="bg-[#fff1f2] border border-[#fecdd3] p-3 rounded text-xs text-[#ba1a1a]">
              {error}
            </div>
          )}

          {showingReveal && revealedMnemonic && (
            <>
              <div className="bg-[#eff4ff] border border-[#dce9ff] p-3 rounded text-xs text-[#3f4850] flex items-start gap-2.5">
                <ShieldAlert className="w-5 h-5 text-[#006194] shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-[#0b1c30] block">{copy.shownOnce}</span>
                  {copy.shownOnceBody}
                </div>
              </div>

              <div>
                <label className="font-['Inter'] text-xs font-semibold text-[#0b1c30] uppercase tracking-wider block mb-2">
                  {copy.phraseLabel}
                </label>
                <div className="grid grid-cols-3 gap-2 bg-[#f8f9ff] p-3.5 rounded-lg border border-[#e2e8f0]">
                  {revealedMnemonic.map((word, index) => (
                    <div
                      key={`${word}-${index}`}
                      className="bg-[#ffffff] px-2.5 py-1.5 rounded border border-[#e2e8f0] flex items-center gap-2 font-['JetBrains_Mono'] text-xs"
                    >
                      <span className="text-[#94a3b8] select-none text-[10px]">{index + 1}.</span>
                      <span className="font-medium text-[#0b1c30]">{word}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <button
                  onClick={handleDownload}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold bg-[#006194] text-[#ffffff] hover:bg-[#007bb9] transition-colors cursor-pointer"
                >
                  <Download className="w-4 h-4" />
                  <span>{copy.downloadPhrase}</span>
                </button>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold bg-[#eff4ff] hover:bg-[#e5eeff] text-[#006194] border border-[#dce9ff] transition-colors cursor-pointer"
                >
                  {copied ? (
                    <Check className="w-4 h-4 text-[#006947]" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                  <span>{copied ? copy.copied : copy.copyWords}</span>
                </button>
              </div>
              {!phraseCaptured && (
                <p className="font-['Inter'] text-xs text-[#565e74]">
                  {copy.captureFirst}
                </p>
              )}

              <label className="flex items-start gap-2.5 text-xs text-[#3f4850] cursor-pointer">
                <input
                  type="checkbox"
                  checked={savedChecked}
                  onChange={(e) => setSavedChecked(e.target.checked)}
                  className="mt-0.5"
                />
                <span>{copy.storedConfirm}</span>
              </label>
            </>
          )}

          {showingSignedIn && (
            <>
              <div className="bg-[#eff4ff] border border-[#dce9ff] p-3 rounded text-xs text-[#3f4850] flex items-start gap-2.5">
                <ShieldAlert className="w-5 h-5 text-[#006194] shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-[#0b1c30] block">{copy.signedIn}</span>
                  {copy.signedInBody}
                </div>
              </div>
              <div className="flex items-center justify-between p-2.5 bg-[#f8f9ff] rounded border border-[#e2e8f0] font-['JetBrains_Mono'] text-xs text-[#565e74]">
                <span>{fill(copy.publicId, { id: publicId ?? '' })}</span>
                <span className="text-[#006947] font-semibold">{copy.authenticated}</span>
              </div>
            </>
          )}

          {!isAuthenticated && !showingReveal && (
            <>
              <div className="bg-[#eff4ff] border border-[#dce9ff] p-3 rounded text-xs text-[#3f4850] flex items-start gap-2.5">
                <ShieldAlert className="w-5 h-5 text-[#006194] shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-[#0b1c30] block">
                    {notice === 'check-email' || confirmToken
                      ? copy.checkEmailTitle
                      : notice === 'reset-sent'
                        ? copy.resetTitle
                        : resetToken
                          ? copy.resetTitle
                          : copy.noEmail}
                  </span>
                  {notice === 'check-email' || confirmToken
                    ? copy.checkEmailBody
                    : notice === 'reset-sent'
                      ? copy.resetSent
                      : resetToken
                        ? copy.passwordHint
                        : copy.noEmailBody}
                </div>
              </div>

              {formError && (
                <p className="text-xs text-[#ba1a1a]" role="alert">
                  {formError}
                </p>
              )}

              {confirmToken && notice === null && (
                <button
                  type="button"
                  onClick={onConfirmEmail}
                  disabled={isBusy}
                  className="w-full px-4 py-2.5 rounded font-['Inter'] text-sm font-semibold bg-[#006194] text-[#ffffff] hover:bg-[#007bb9] disabled:opacity-60 transition-colors cursor-pointer"
                >
                  {copy.confirmAction}
                </button>
              )}

              {notice === null && !confirmToken && (
                <form
                  className="space-y-3"
                  onSubmit={(event) => {
                    event.preventDefault();
                    submitEmail();
                  }}
                >
                  {!resetToken && (
                    <label className="block">
                      <span className="font-['Inter'] text-xs font-semibold text-[#0b1c30] uppercase tracking-wider">
                        {copy.emailLabel}
                      </span>
                      <input
                        type="email"
                        autoComplete="email"
                        value={email}
                        onChange={(event) => setEmail(event.target.value)}
                        required
                        className="mt-1 w-full rounded-lg border border-[#e2e8f0] bg-[#f8f9ff] px-3 py-2 text-sm text-[#0b1c30] focus:outline-none focus:border-[#006194]"
                      />
                    </label>
                  )}
                  {(mode !== 'reset' || resetToken) && (
                    <label className="block">
                      <span className="font-['Inter'] text-xs font-semibold text-[#0b1c30] uppercase tracking-wider">
                        {resetToken ? copy.newPassword : copy.passwordLabel}
                      </span>
                      <input
                        type="password"
                        autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                        minLength={12}
                        required
                        className="mt-1 w-full rounded-lg border border-[#e2e8f0] bg-[#f8f9ff] px-3 py-2 text-sm text-[#0b1c30] focus:outline-none focus:border-[#006194]"
                      />
                      <span className="mt-1 block text-xs text-[#565e74]">{copy.passwordHint}</span>
                    </label>
                  )}
                  {mode === 'register' && !resetToken && (
                    <>
                      <label className="block">
                        <span className="font-['Inter'] text-xs font-semibold text-[#0b1c30] uppercase tracking-wider">
                          {copy.confirmPassword}
                        </span>
                        <input
                          type="password"
                          autoComplete="new-password"
                          value={passwordAgain}
                          onChange={(event) => setPasswordAgain(event.target.value)}
                          minLength={12}
                          required
                          className="mt-1 w-full rounded-lg border border-[#e2e8f0] bg-[#f8f9ff] px-3 py-2 text-sm text-[#0b1c30] focus:outline-none focus:border-[#006194]"
                        />
                      </label>
                      <label className="flex items-start gap-2.5 text-xs text-[#3f4850] cursor-pointer">
                        <input
                          type="checkbox"
                          checked={healthChecked}
                          onChange={(event) => setHealthChecked(event.target.checked)}
                          className="mt-0.5"
                        />
                        <span>{copy.healthConsent}</span>
                      </label>
                      <label className="flex items-start gap-2.5 text-xs text-[#3f4850] cursor-pointer">
                        <input
                          type="checkbox"
                          checked={researchChecked}
                          onChange={(event) => setResearchChecked(event.target.checked)}
                          className="mt-0.5"
                        />
                        <span>{copy.researchConsent}</span>
                      </label>
                    </>
                  )}
                  <button
                    type="submit"
                    disabled={isBusy}
                    className="w-full px-4 py-2.5 rounded font-['Inter'] text-sm font-semibold bg-[#006194] text-[#ffffff] hover:bg-[#007bb9] disabled:opacity-60 transition-colors cursor-pointer flex items-center justify-center gap-2"
                  >
                    {isBusy ? <LoaderCircle className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
                    <span>
                      {resetToken
                        ? copy.resetAction
                        : mode === 'register'
                          ? copy.registerAction
                          : mode === 'reset'
                            ? copy.resetSend
                            : copy.signIn}
                    </span>
                  </button>
                </form>
              )}

              {notice === null && !resetToken && (
                <div className="flex flex-wrap gap-3 text-xs">
                  {mode === 'login' && (
                    <>
                      <button
                        type="button"
                        onClick={() => {
                          setFormError(null);
                          setMode('register');
                        }}
                        className="text-[#006194] font-semibold cursor-pointer"
                      >
                        {copy.needAccount}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setFormError(null);
                          setMode('reset');
                        }}
                        className="text-[#006194] font-semibold cursor-pointer"
                      >
                        {copy.forgotPassword}
                      </button>
                    </>
                  )}
                  {mode !== 'login' && (
                    <button
                      type="button"
                      onClick={() => {
                        setFormError(null);
                        setMode('login');
                      }}
                      className="text-[#006194] font-semibold cursor-pointer"
                    >
                      {copy.haveAccount}
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => setShowPhrase((value) => !value)}
                    className="text-[#565e74] font-semibold cursor-pointer"
                  >
                    {copy.phraseStill}
                  </button>
                </div>
              )}

              {showPhrase && notice === null && !resetToken && (
                <div className="pt-1">
                  <label className="font-['Inter'] text-xs font-semibold text-[#0b1c30] uppercase tracking-wider block mb-2">
                    {copy.restore}
                  </label>
                  <textarea
                    value={restorePhrase}
                    onChange={(event) => setRestorePhrase(event.target.value)}
                    rows={3}
                    placeholder={copy.pastePlaceholder}
                    className="w-full rounded-lg border border-[#e2e8f0] bg-[#f8f9ff] p-3 font-['JetBrains_Mono'] text-xs text-[#0b1c30] focus:outline-none focus:border-[#006194]"
                  />
                  <button
                    type="button"
                    onClick={handleLogin}
                    disabled={isBusy || restorePhrase.trim().length === 0}
                    className="mt-2 w-full px-4 py-2 rounded font-['Inter'] text-sm font-semibold text-[#0b1c30] bg-[#eff4ff] hover:bg-[#e5eeff] border border-[#dce9ff] disabled:opacity-60 transition-colors cursor-pointer"
                  >
                    {copy.signIn}
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        <div className="px-6 py-3.5 border-t border-[#e2e8f0] bg-[#f8f9ff] flex justify-between">
          {isAuthenticated && !showingReveal ? (
            <button
              onClick={handleLogout}
              disabled={isBusy}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold bg-[#fff1f2] hover:bg-[#ffe4e6] text-[#ba1a1a] border border-[#fecdd3] transition-colors cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
              <span>{copy.signOut}</span>
            </button>
          ) : (
            <span />
          )}
          {showingReveal ? (
            <button
              onClick={() => {
                if (!canContinue) return;
                setSavedChecked(false);
                setCopied(false);
                setPhraseCaptured(false);
                onConfirmPhraseSaved();
              }}
              disabled={!canContinue}
              className="px-4 py-1.5 rounded font-['Inter'] text-sm font-semibold bg-[#006194] text-[#ffffff] hover:bg-[#007bb9] disabled:opacity-50 transition-colors cursor-pointer"
            >
              {copy.continue}
            </button>
          ) : (
            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded font-['Inter'] text-sm font-semibold bg-[#006194] text-[#ffffff] hover:bg-[#007bb9] transition-colors cursor-pointer"
            >
              {copy.done}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
