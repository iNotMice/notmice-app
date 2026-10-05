import React, { useEffect, useState } from 'react';
import { TabType } from '../../types';
import {
  deleteOwnAccount,
  downloadOwnExport,
  fetchOwnConsents,
  updateOwnConsent,
  type ConsentRecord,
} from '../../api/accounts';
import { DatasetRequestError, fetchPublicTimeseries, PublicTimeseries } from '../../api/dataset';
import { fetchSurveyCatalog, SurveyCatalogRequestError, type SurveyCatalog } from '../../api/survey';
import { ParticipantProfilePreview } from '../ParticipantProfilePreview';
import { ArrowRight, Share2, Trash2, Lock, EyeOff } from 'lucide-react';
import { getActiveI18n } from '../../i18n/catalog';
import { fill } from '../../i18n/fill';
import { useI18n } from '../../i18n/I18nProvider';

interface DataSovereigntyTabProps {
  accountAddress: string;
  isAuthenticated: boolean;
  isPublic: boolean;
  onTogglePublic: (isPublic: boolean, consentVersion: string) => Promise<void>;
  onAccountDeleted: () => void;
  onPurgeMemory: () => void | Promise<void>;
  onOpenSeedPhrase: () => void;
  setActiveTab: (tab: TabType) => void;
  /** Opens the public dataset and charter page for specialists. */
  onOpenCharter: () => void;
}

export const DataSovereigntyTab: React.FC<DataSovereigntyTabProps> = ({
  accountAddress,
  isAuthenticated,
  isPublic,
  onTogglePublic,
  onAccountDeleted,
  onPurgeMemory,
  onOpenSeedPhrase,
  onOpenCharter,
}) => {
  const { m } = useI18n();
  const copy = m.sovereignty;
  const [datasetReload, setDatasetReload] = useState(0);
  const [series, setSeries] = useState<PublicTimeseries | null>(null);
  const [seriesNote, setSeriesNote] = useState<string | null>(null);
  const [purgeBusy, setPurgeBusy] = useState(false);
  const [purgeError, setPurgeError] = useState<string | null>(null);
  const [ownBusy, setOwnBusy] = useState(false);
  const [ownError, setOwnError] = useState<string | null>(null);
  const [surveyCatalog, setSurveyCatalog] = useState<SurveyCatalog | null>(null);
  const [surveyError, setSurveyError] = useState<number | null>(null);
  const [consents, setConsents] = useState<ConsentRecord[]>([]);
  const [consentError, setConsentError] = useState<string | null>(null);
  const [consentBusy, setConsentBusy] = useState(false);
  const [shareBusy, setShareBusy] = useState(false);
  const [shareError, setShareError] = useState<string | null>(null);

  const isConsentActive = (type: ConsentRecord['type'], version: string | null | undefined) =>
    version !== null &&
    version !== undefined &&
    consents.some(
      (consent) =>
        consent.type === type && consent.version === version && consent.withdrawn_at === null,
    );

  const researchReuseActive = isConsentActive(
    'research_reuse',
    surveyCatalog?.research_reuse_consent_version,
  );
  const healthDataActive = isConsentActive(
    'health_data',
    surveyCatalog?.health_data_consent_version,
  );
  const publicSharingConsentActive = isConsentActive(
    'public_sharing',
    surveyCatalog?.public_sharing_consent_version,
  );
  const publicSharingEnabled = isPublic && publicSharingConsentActive;

  useEffect(() => {
    const controller = new AbortController();
    setSurveyError(null);
    void fetchSurveyCatalog(controller.signal)
      .then((catalog) => setSurveyCatalog(catalog))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') {
          return;
        }
        setSurveyCatalog(null);
        setSurveyError(err instanceof SurveyCatalogRequestError ? err.status : 0);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      setConsents([]);
      return;
    }
    let cancelled = false;
    setConsentError(null);
    void fetchOwnConsents()
      .then((current) => {
        if (!cancelled) {
          setConsents(current);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setConsentError(copy.consentsFailed);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, copy.consentsFailed]);

  useEffect(() => {
    if (!publicSharingEnabled || !isAuthenticated) {
      setSeries(null);
      setSeriesNote(null);
      return;
    }
    const controller = new AbortController();
    setSeriesNote(getActiveI18n().messages.sovereignty.loadingProfile);
    void fetchPublicTimeseries(accountAddress, controller.signal)
      .then((payload) => {
        setSeries(payload);
        setSeriesNote(
          payload.points.length === 0
            ? getActiveI18n().messages.sovereignty.noPublicRows
            : null,
        );
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') {
          return;
        }
        setSeries(null);
        const messages = getActiveI18n().messages.sovereignty;
        setSeriesNote(
          err instanceof DatasetRequestError && err.status === 404
            ? messages.profileMissing
            : messages.profileFailed,
        );
      });
    return () => controller.abort();
  }, [accountAddress, isAuthenticated, publicSharingEnabled, datasetReload]);

  const handlePurge = () => {
    setPurgeError(null);
    setPurgeBusy(true);
    void Promise.resolve(onPurgeMemory())
      .then(() => {
        setDatasetReload((value) => value + 1);
      })
      .catch(() => {
        setPurgeError(copy.purgeFailed);
      })
      .finally(() => {
        setPurgeBusy(false);
      });
  };

  const downloadOwn = (kind: 'json' | 'csv') => {
    if (!isAuthenticated) {
      return;
    }
    setOwnError(null);
    setOwnBusy(true);
    void downloadOwnExport(kind)
      .catch(() => setOwnError(copy.ownExportFailed))
      .finally(() => setOwnBusy(false));
  };

  const deleteAccount = () => {
    if (!isAuthenticated || !window.confirm(copy.deleteAccountConfirm)) {
      return;
    }
    setOwnError(null);
    setOwnBusy(true);
    void deleteOwnAccount()
      .then(() => onAccountDeleted())
      .catch(() => setOwnError(copy.deleteFailed))
      .finally(() => setOwnBusy(false));
  };

  const toggleHealthData = async (accepted: boolean) => {
    if (!surveyCatalog || !isAuthenticated) {
      return;
    }
    setConsentBusy(true);
    setConsentError(null);
    try {
      await updateOwnConsent(
        'health_data',
        surveyCatalog.health_data_consent_version,
        accepted,
      );
      setConsents(await fetchOwnConsents());
    } catch {
      setConsentError(copy.consentUpdateFailed);
    } finally {
      setConsentBusy(false);
    }
  };

  const toggleResearchReuse = async (accepted: boolean) => {
    if (!surveyCatalog || !isAuthenticated) {
      return;
    }
    setConsentBusy(true);
    setConsentError(null);
    try {
      await updateOwnConsent(
        'research_reuse',
        surveyCatalog.research_reuse_consent_version,
        accepted,
      );
      setConsents(await fetchOwnConsents());
    } catch {
      setConsentError(copy.consentUpdateFailed);
    } finally {
      setConsentBusy(false);
    }
  };

  const togglePublicSharing = async (accepted: boolean) => {
    if (!surveyCatalog || !isAuthenticated) {
      if (!isAuthenticated) {
        onOpenSeedPhrase();
      }
      return;
    }
    setShareBusy(true);
    setShareError(null);
    try {
      await onTogglePublic(accepted, surveyCatalog.public_sharing_consent_version);
      setConsents(await fetchOwnConsents());
      setDatasetReload((value) => value + 1);
    } catch {
      setShareError(copy.publicShareUpdateFailed);
    } finally {
      setShareBusy(false);
    }
  };

  return (
    <div className="w-full flex flex-col gap-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#e2e8f0] pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="bg-[#cce5ff] text-[#004b73] font-['JetBrains_Mono'] text-xs font-semibold px-2 py-0.5 rounded">
              {copy.stage}
            </span>
            <span className="font-['JetBrains_Mono'] text-xs text-[#565e74]">
              {copy.stageMeta}
            </span>
          </div>
          <h2 className="font-['Inter'] text-2xl lg:text-3xl font-bold text-[#0b1c30]">
            {copy.title}
          </h2>
          <p className="font-['Inter'] text-sm text-[#3f4850] mt-1 max-w-2xl">
            {copy.lead}
          </p>
          <button
            type="button"
            onClick={onOpenCharter}
            className="mt-2 inline-flex items-center gap-1 text-sm font-semibold text-[#006194] hover:underline cursor-pointer"
          >
            {copy.charterLink}
            <ArrowRight className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handlePurge}
            disabled={purgeBusy}
            className="flex items-center gap-2 px-4 py-2.5 rounded font-['Inter'] text-xs font-bold bg-[#fff1f2] hover:bg-[#ffe4e6] text-[#ba1a1a] border border-[#fecdd3] transition-colors cursor-pointer disabled:opacity-60"
          >
            <Trash2 className="w-4 h-4" />
            <span>{isAuthenticated ? copy.purgeAccount : copy.purgeLocal}</span>
          </button>
          {purgeError && (
            <p className="text-xs text-[#ba1a1a]" role="alert">
              {purgeError}
            </p>
          )}
        </div>
      </div>

      <section
        className="bg-[#ffffff] p-6 rounded-xl border border-[#cbd5e1] shadow-xs flex flex-col gap-2"
        aria-live="polite"
      >
        <h2 className="font-['Inter'] text-base font-bold text-[#0b1c30]">
          {copy.profileSurveyTitle}
        </h2>
        {surveyCatalog === null && surveyError === null && (
          <p className="font-['Inter'] text-sm text-[#3f4850]">{copy.profileSurveyLoading}</p>
        )}
        {surveyError !== null && (
          <p className="font-['Inter'] text-sm text-[#ba1a1a]" role="alert">
            {surveyError === 0
              ? copy.profileSurveySilent
              : fill(copy.profileSurveyFailed, { status: surveyError })}
          </p>
        )}
        {surveyCatalog && (
          <>
            <p className="font-['Inter'] text-sm text-[#3f4850]">
              {surveyCatalog.enabled ? copy.profileSurveyConfigured : copy.profileSurveyDisabled}
            </p>
            {isAuthenticated && (
              <ParticipantProfilePreview
                catalog={surveyCatalog}
                copy={copy.profileSurvey}
              />
            )}
            {!isAuthenticated && (
              <p className="font-['Inter'] text-sm text-[#607286]">
                {copy.profileSurvey.loginRequired}
              </p>
            )}
          </>
        )}
      </section>

      {isAuthenticated && (
        <div className="bg-[#ffffff] p-6 rounded-xl border border-[#cbd5e1] shadow-xs flex flex-col gap-3">
          <span className="font-['Inter'] text-base font-bold text-[#0b1c30]">{copy.ownTitle}</span>
          <p className="font-['Inter'] text-sm text-[#3f4850]">{copy.ownLead}</p>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => downloadOwn('json')}
              disabled={ownBusy}
              className="px-4 py-2 rounded font-['Inter'] text-xs font-bold bg-[#006194] text-[#ffffff] hover:bg-[#007bb9] disabled:opacity-60 cursor-pointer"
            >
              {copy.ownJson}
            </button>
            <button
              type="button"
              onClick={() => downloadOwn('csv')}
              disabled={ownBusy}
              className="px-4 py-2 rounded font-['Inter'] text-xs font-bold bg-[#eff4ff] text-[#006194] border border-[#dce9ff] hover:bg-[#e5eeff] disabled:opacity-60 cursor-pointer"
            >
              {copy.ownCsv}
            </button>
            <button
              type="button"
              onClick={deleteAccount}
              disabled={ownBusy}
              className="px-4 py-2 rounded font-['Inter'] text-xs font-bold bg-[#fff1f2] text-[#ba1a1a] border border-[#fecdd3] hover:bg-[#ffe4e6] disabled:opacity-60 cursor-pointer"
            >
              {copy.deleteAccount}
            </button>
          </div>
          {ownError && (
            <p className="text-xs text-[#ba1a1a]" role="alert">
              {ownError}
            </p>
          )}
        </div>
      )}

      {isAuthenticated && surveyCatalog && (
        <section className="bg-[#ffffff] p-6 rounded-xl border border-[#cbd5e1] shadow-xs flex flex-col gap-3">
          <h2 className="font-['Inter'] text-base font-bold text-[#0b1c30]">
            {copy.healthConsentTitle}
          </h2>
          <p className="font-['Inter'] text-sm text-[#3f4850]">
            {copy.healthConsentBody}
          </p>
          <a
            href="/legal/consent-personal-research-2026-10-03.html"
            target="_blank"
            rel="noreferrer"
            className="text-xs font-semibold text-[#006194] underline"
          >
            {copy.healthConsentLegalLink}
          </a>
          <label className="flex items-start gap-3 rounded-lg border border-[#e1e8ef] p-3 text-sm">
            <input
              aria-label={copy.healthConsentTitle}
              type="checkbox"
              checked={healthDataActive}
              disabled={consentBusy}
              onChange={(event) => void toggleHealthData(event.target.checked)}
              className="mt-1 h-4 w-4 shrink-0 accent-[#006194] disabled:opacity-50"
            />
            <span>{healthDataActive ? copy.healthConsentActive : copy.healthConsentRequired}</span>
          </label>
          {consentError && (
            <p className="text-xs text-[#ba1a1a]" role="alert">
              {consentError}
            </p>
          )}
        </section>
      )}

      {/* Main Grid: Export Modules vs Decentralized Cohort Sharing */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Account sign-in */}
        <div className="lg:col-span-6 flex flex-col gap-6">
          {/* Seed Phrase Security Card */}
          <div className="bg-[#ffffff] p-6 rounded-xl border border-[#cbd5e1] shadow-xs flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="font-['Inter'] text-sm font-bold text-[#0b1c30] flex items-center gap-2">
                <Lock className="w-4 h-4 text-[#006194]" />
                {copy.vaultTitle}
              </span>
              <button
                onClick={onOpenSeedPhrase}
                className="text-xs text-[#006194] hover:underline font-semibold cursor-pointer"
              >
                {copy.openAccount}
              </button>
            </div>
            <p className="text-xs text-[#565e74] leading-relaxed">
              {copy.vaultBody}
            </p>
            <div className="flex items-center justify-between p-2.5 bg-[#f8f9ff] rounded border border-[#e2e8f0] font-['JetBrains_Mono'] text-xs text-[#565e74]">
              <span>{fill(copy.activeId, { id: accountAddress })}</span>
              <span className="text-[#006947] font-semibold">
                {isAuthenticated ? copy.authenticated : copy.guest}
              </span>
            </div>
          </div>
        </div>

        {/* Right Column: Public Sharing & Open Science Research Charter */}
        <div className="lg:col-span-6 flex flex-col gap-6">
          {/* Open Science Cohort Opt-in */}
          <div className="bg-[#ffffff] p-6 rounded-xl border border-[#cbd5e1] shadow-xs flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <span className="font-['Inter'] text-base font-bold text-[#0b1c30] flex items-center gap-2">
                <Share2 className="w-5 h-5 text-[#006947]" />
                {copy.optInTitle}
              </span>
              <span className="font-['JetBrains_Mono'] text-xs bg-[#4edea3]/20 text-[#006947] px-2 py-0.5 rounded font-bold">
                {copy.openAccess}
              </span>
            </div>

            <p className="font-['Inter'] text-xs text-[#565e74] leading-relaxed">
              {copy.optInBody}
            </p>

            <div className="rounded-lg border border-[#d6e5ef] bg-[#f8fbfd] p-3 text-xs leading-5 text-[#526579]">
              {copy.publicSharingDisclosure}
            </div>

            <div className="flex items-start justify-between gap-4 rounded-lg border border-[#e1e8ef] p-3">
              <div>
                <p className="text-sm font-semibold text-[#18334b]">{copy.researchReuseTitle}</p>
                <p className="mt-1 text-xs leading-5 text-[#607286]">{copy.researchReuseBody}</p>
              </div>
              <input
                aria-label={copy.researchReuseTitle}
                type="checkbox"
                checked={researchReuseActive}
                disabled={!isAuthenticated || !surveyCatalog || consentBusy}
                onChange={(event) => void toggleResearchReuse(event.target.checked)}
                className="mt-1 h-4 w-4 shrink-0 accent-[#006194] disabled:opacity-50"
              />
            </div>
            {consentError && <p className="text-xs text-[#ba1a1a]" role="alert">{consentError}</p>}

            {/* Privacy disclosure summarizes exactly which fields the public API exposes. */}
            <div className="bg-[#f8f9ff] p-3.5 rounded-lg border border-[#e2e8f0] space-y-2 text-xs">
              <span className="font-['Inter'] font-bold text-[#0b1c30] flex items-center gap-1.5">
                <EyeOff className="w-4 h-4 text-[#ba1a1a]" />
                {copy.redaction}
              </span>
              <div className="grid grid-cols-2 gap-2 text-[11px] font-['JetBrains_Mono'] text-[#565e74]">
                <div>✗ {copy.strippedName}</div>
                <div>✓ {copy.keptAge}</div>
                <div>✗ {copy.strippedDob}</div>
                <div>✓ {copy.keptMarkers}</div>
                <div>✗ {copy.strippedAccount}</div>
                <div>✓ {copy.keptDelta}</div>
              </div>
            </div>

            {/* Toggle switch */}
            <div className="flex items-center justify-between p-3 bg-[#eff4ff] rounded-lg border border-[#dce9ff]">
              <div className="flex flex-col">
                <span className="font-['Inter'] text-xs font-bold text-[#0b1c30]">
                  {copy.contribute}
                </span>
                <span className="text-[11px] text-[#565e74]">
                  {isAuthenticated ? copy.contributeOn : copy.contributeOff}
                </span>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  aria-label={copy.contribute}
                  type="checkbox"
                  checked={isPublic && publicSharingConsentActive}
                  disabled={!isAuthenticated || !surveyCatalog || shareBusy}
                  onChange={(e) => void togglePublicSharing(e.target.checked)}
                  className="mt-1 h-4 w-4 shrink-0 accent-[#00855b] disabled:opacity-50"
                />
              </label>
            </div>
            {shareError && <p className="text-xs text-[#ba1a1a]" role="alert">{shareError}</p>}
            {isPublic && !publicSharingConsentActive && (
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-amber-50 p-3 text-xs leading-5 text-amber-900" role="status">
                <span>{copy.publicShareNeedsConsent}</span>
                <button
                  type="button"
                  disabled={shareBusy}
                  onClick={() => void togglePublicSharing(false)}
                  className="font-semibold underline disabled:opacity-50"
                >
                  {copy.turnPublicOff}
                </button>
              </div>
            )}

            {/* Public sharing status */}
            {publicSharingEnabled && (
              <div className="p-3 bg-[#f8f9ff] rounded border border-[#dce9ff] flex flex-col gap-1.5 text-xs animate-in fade-in">
                <span className="font-['JetBrains_Mono'] text-[#006947] font-semibold">
                  {copy.sharingOn}
                </span>
                <p className="text-[11px] text-[#565e74] leading-relaxed">
                  {copy.sharingBody}
                </p>
                {seriesNote && <p className="text-[11px] text-[#0b1c30]">{seriesNote}</p>}
                {series && series.points.length > 0 && (
                  <p className="font-['JetBrains_Mono'] text-[11px] text-[#565e74]">
                    {fill(copy.collectionDates, {
                      count: series.points.length,
                      unit: series.points.length === 1 ? copy.dateOne : copy.dateMany,
                      id: series.publicId,
                    })}
                  </p>
                )}
              </div>
            )}
          </div>

        </div>
      </div>

    </div>
  );
};
