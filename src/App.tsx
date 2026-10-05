import React, { useEffect, useMemo, useRef, useState } from 'react';
import { TabType, LabPanelData, HistoricalTestRecord, AccountState, PhenoAgeCalculation } from './types';
import { INITIAL_BIOMARKERS, PHENOAGE_BIOMARKERS } from './data/phenoAgeData';
import { deleteOwnLabResult, deleteOwnLabResults, fetchOwnLabResults } from './api/uploads';
import { isBiomarkerId } from './i18n/biomarkerIds';
import { fetchPhenoAge, PhenoAgeScore } from './api/phenoage';
import { displayBiomarkerScores } from './utils/phenoAgeMath';
import {
  confirmEmail,
  confirmPasswordReset,
  fetchCurrentAccount,
  forgetLegacyToken,
  loginWithEmail,
  loginWithMnemonic,
  logoutAccount,
  registerAccount,
  requestPasswordReset,
  updateShareSettings,
} from './api/accounts';
import { Header } from './components/Header';
import { StatusRibbon } from './components/StatusRibbon';
import { OverviewTab } from './components/tabs/OverviewTab';
import { UploadLabTab } from './components/tabs/UploadLabTab';
import { ReviewExtractionTab } from './components/tabs/ReviewExtractionTab';
import { PhenoAgeEngineTab } from './components/tabs/PhenoAgeEngineTab';
import { BiomarkerHistoryTab } from './components/tabs/BiomarkerHistoryTab';
import { ProtocolJournalTab } from './components/tabs/ProtocolJournalTab';
import { DataSovereigntyTab } from './components/tabs/DataSovereigntyTab';
import { ResearchNewsTab } from './components/tabs/ResearchNewsTab';
import { UserInstructionsTab } from './components/tabs/UserInstructionsTab';
import { LabPortalPage } from './components/LabPortalPage';
import { ProofModal } from './components/ProofModal';
import { SeedPhraseModal } from './components/SeedPhraseModal';
import { TerminalModal } from './components/TerminalModal';
import { DataDisclaimer } from './components/DataDisclaimer';
import { Footer } from './components/Footer';
import { SplashScreen } from './components/SplashScreen';
import { getActiveI18n } from './i18n/catalog';
import { useI18n } from './i18n/I18nProvider';

const SPLASH_SEEN_KEY = 'notmice.splashSeen';

function splashAlreadySeen(): boolean {
  try {
    return localStorage.getItem(SPLASH_SEEN_KEY) === '1';
  } catch {
    return true;
  }
}

function markSplashSeen(): void {
  try {
    localStorage.setItem(SPLASH_SEEN_KEY, '1');
  } catch {
    // Storage can be blocked; the splash still closes for this visit.
  }
}

function panelFromHistory(record: HistoricalTestRecord): LabPanelData {
  return {
    id: record.id,
    labName: record.labSource,
    testDate: record.date,
    sourceType: record.sessionOnly ? 'manual' : 'pdf',
    fileName: record.labSource,
    chronologicalAge: record.chronologicalAge ?? 42,
    gender: 'male',
    biomarkers: { ...INITIAL_BIOMARKERS, ...record.biomarkers },
    confidenceScores: {},
    verified: true,
    hash: record.hash,
    focusMarkerIds: record.markerIds,
  };
}

function tutorialPanel(): LabPanelData {
  return {
    id: 'panel-tutorial',
    labName: 'Tutorial example',
    testDate: '—',
    sourceType: 'demo',
    fileName: 'Worked example, not a laboratory file',
    chronologicalAge: 42.0,
    gender: 'male',
    biomarkers: { ...INITIAL_BIOMARKERS },
    confidenceScores: {},
    verified: false,
    hash: '',
    focusMarkerIds: [],
  };
}

function MainApp() {
  const { m } = useI18n();
  const [activeTab, setActiveTab] = useState<TabType>('overview-landing');
  const [chronologicalAge, setChronologicalAge] = useState<number>(42.0);
  const [biomarkers, setBiomarkers] = useState<Record<string, number>>(INITIAL_BIOMARKERS);
  const [history, setHistory] = useState<HistoricalTestRecord[]>([]);
  const [account, setAccount] = useState<AccountState | null>(null);
  const [revealedMnemonic, setRevealedMnemonic] = useState<string[] | null>(null);
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authNotice, setAuthNotice] = useState<'check-email' | 'reset-sent' | null>(null);
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [confirmToken, setConfirmToken] = useState<string | null>(null);
  const [phenoAgeScore, setPhenoAgeScore] = useState<PhenoAgeScore | null>(null);
  const [phenoAgeLoading, setPhenoAgeLoading] = useState(true);
  const [phenoAgeError, setPhenoAgeError] = useState<string | null>(null);

  // Modals state
  const [isProofModalOpen, setIsProofModalOpen] = useState(false);
  const [isSeedPhraseModalOpen, setIsSeedPhraseModalOpen] = useState(false);
  const [isTerminalModalOpen, setIsTerminalModalOpen] = useState(false);
  const [showSplash, setShowSplash] = useState(() => !splashAlreadySeen());

  const [currentPanel, setCurrentPanel] = useState<LabPanelData>(tutorialPanel);

  useEffect(() => {
    forgetLegacyToken();
    let cancelled = false;
    void (async () => {
      try {
        const current = await fetchCurrentAccount();
        if (!cancelled && current) {
          setAccount(current);
          await restoreSavedPanels();
        }

      } catch {
        // A failed restore leaves the visitor signed out.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const publicIdLabel = account?.publicId ?? m.nav.guest;

  useEffect(() => {
    const controller = new AbortController();
    setPhenoAgeLoading(true);
    const timer = window.setTimeout(() => {
      void fetchPhenoAge(chronologicalAge, biomarkers, controller.signal)
        .then((score) => {
          if (controller.signal.aborted) {
            return;
          }
          setPhenoAgeScore(score);
          setPhenoAgeError(null);
          setPhenoAgeLoading(false);
        })
        .catch((err: unknown) => {
          if (controller.signal.aborted || (err instanceof DOMException && err.name === 'AbortError')) {
            return;
          }
          setPhenoAgeError(err instanceof Error ? err.message : getActiveI18n().messages.shell.phenoAgeFailed);
          setPhenoAgeLoading(false);
        });
    }, 200);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [chronologicalAge, biomarkers]);

  const phenoAgeCalculation = useMemo<PhenoAgeCalculation>(() => {
    const biomarkerScores = displayBiomarkerScores(biomarkers);
    if (!phenoAgeScore || phenoAgeLoading) {
      return {
        chronologicalAge,
        phenoAge: 0,
        ageDelta: 0,
        biomarkerScores,
        isValid: false,
        activeCount: Object.keys(biomarkers).length,
        disclaimer: m.shell.disclaimer,
      };
    }
    return {
      chronologicalAge: phenoAgeScore.chronologicalAge,
      phenoAge: phenoAgeScore.phenoAge,
      ageDelta: phenoAgeScore.ageDelta,
      biomarkerScores,
      isValid: true,
      activeCount: Object.keys(biomarkers).length,
      disclaimer: m.shell.disclaimer,
    };
  }, [biomarkers, chronologicalAge, m.shell.disclaimer, phenoAgeLoading, phenoAgeScore]);

  const handleLoadPanel = (panel: LabPanelData) => {
    setCurrentPanel(panel);
    setBiomarkers({ ...panel.biomarkers });
    setChronologicalAge(panel.chronologicalAge);
  };

  const restoreSavedPanels = async () => {
    try {
      const panels = await fetchOwnLabResults();
      if (panels.length === 0) {
        return;
      }
      const records: HistoricalTestRecord[] = [];
      for (const panel of panels) {
        const saved: Record<string, number> = {};
        const biomarkerUnits: Record<string, string> = {};
        const markerIds: string[] = [];
        const printedIntervals: HistoricalTestRecord['printedIntervals'] = {};
        for (const marker of panel.markers) {
          if (marker.canonicalId && isBiomarkerId(marker.canonicalId)) {
            saved[marker.canonicalId] = marker.value;
            biomarkerUnits[marker.canonicalId] = marker.unit;
            markerIds.push(marker.canonicalId);
            printedIntervals[marker.canonicalId] = {
              referenceLow: marker.referenceLow,
              referenceHigh: marker.referenceHigh,
              referenceText: marker.referenceText,
              labFlag: marker.labFlag,
              outsideInterval: marker.outsideInterval,
            };
          }
        }
        records.push({
          id: panel.id,
          date: panel.collectedAt ?? panel.confirmedAt.slice(0, 10),
          collectedAt: panel.collectedAt,
          chronologicalAge: panel.chronologicalAge,
          phenoAge: panel.phenoAge,
          delta: panel.ageDelta,
          labSource: panel.labName ?? getActiveI18n().messages.shell.unknownLaboratory,
          biomarkers: saved,
          biomarkerUnits,
          hash: panel.documentSha256,
          markerIds,
          printedIntervals,
          markerCount: panel.markerCount,
          sessionOnly: false,
          missingMarkers: panel.missingMarkers,
        });
      }
      setHistory((prev) => [...records, ...prev.filter((row) => row.sessionOnly)]);
      const latest = records[records.length - 1];
      handleLoadPanel(panelFromHistory(latest));
    } catch {
      // A failed reload leaves the current screen in place.
    }
  };

  const handleSaveToHistory = () => {
    if (!phenoAgeCalculation.isValid) {
      return;
    }
    const today = new Date().toISOString().split('T')[0];
    const messages = getActiveI18n().messages;
    const newRecord: HistoricalTestRecord = {
      id: `session-${Date.now()}`,
      date: today,
      collectedAt: null,
      chronologicalAge,
      phenoAge: phenoAgeCalculation.phenoAge,
      delta: phenoAgeCalculation.ageDelta,
      labSource:
        currentPanel.sourceType === 'demo' ? messages.history.sessionSnapshot : currentPanel.labName,
      biomarkers: { ...biomarkers },
      biomarkerUnits: Object.fromEntries(
        currentPanel.focusMarkerIds
          .filter(isBiomarkerId)
          .map((id) => [id, PHENOAGE_BIOMARKERS.find((marker) => marker.id === id)?.standardUnit ?? '']),
      ),
      hash: currentPanel.hash.length === 64 ? currentPanel.hash : '',
      markerIds: [...currentPanel.focusMarkerIds],
      printedIntervals: {},
      markerCount: currentPanel.focusMarkerIds.length,
      sessionOnly: true,
      missingMarkers: [],
    };
    setHistory((prev) => [...prev, newRecord]);
  };

  const handleSelectHistoricalRecord = (record: HistoricalTestRecord) => {
    const panel = panelFromHistory(record);
    setChronologicalAge(panel.chronologicalAge);
    setBiomarkers({ ...panel.biomarkers });
    setCurrentPanel(panel);
  };

  const handleDeleteHistory = async (id: string) => {
    const row = history.find((item) => item.id === id);
    if (!row) {
      return;
    }
    if (!row.sessionOnly) {
      await deleteOwnLabResult(id);
    }
    const remaining = history.filter((item) => item.id !== id);
    setHistory(remaining);
    if (currentPanel.id !== id) {
      return;
    }
    const nextSaved = [...remaining].reverse().find((item) => !item.sessionOnly);
    if (nextSaved) {
      handleSelectHistoricalRecord(nextSaved);
      return;
    }
    setBiomarkers({ ...INITIAL_BIOMARKERS });
    setChronologicalAge(42.0);
    setCurrentPanel(tutorialPanel());
  };

  const handlePurgeMemory = async () => {
    if (account) {
      await deleteOwnLabResults();
    }
    setBiomarkers({ ...INITIAL_BIOMARKERS });
    setChronologicalAge(42.0);
    setHistory([]);
    setCurrentPanel(tutorialPanel());
  };

  const applySession = async (session: AccountState) => {
    setAccount(session);
    setRevealedMnemonic(null);
    setAuthNotice(null);
    setResetToken(null);
    setIsSeedPhraseModalOpen(false);
    await restoreSavedPanels();
  };

  const handleRegister = async (email: string, password: string, researchReuse: boolean) => {
    setAuthBusy(true);
    setAuthError(null);
    try {
      await registerAccount({ email, password, researchReuse });
      setAccount(null);
      setAuthNotice('check-email');
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : getActiveI18n().messages.shell.couldNotCreateAccount);
    } finally {
      setAuthBusy(false);
    }
  };

  const handleEmailLogin = async (email: string, password: string) => {
    setAuthBusy(true);
    setAuthError(null);
    try {
      await applySession(await loginWithEmail(email, password));
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : getActiveI18n().messages.shell.couldNotSignIn);
    } finally {
      setAuthBusy(false);
    }
  };

  const handleRequestReset = async (email: string) => {
    setAuthBusy(true);
    setAuthError(null);
    try {
      await requestPasswordReset(email);
      setAuthNotice('reset-sent');
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : getActiveI18n().messages.shell.couldNotSignIn);
    } finally {
      setAuthBusy(false);
    }
  };

  const handleConfirmEmail = async () => {
    if (!confirmToken) {
      return;
    }
    setAuthBusy(true);
    setAuthError(null);
    try {
      await applySession(await confirmEmail(confirmToken));
      setConfirmToken(null);
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : getActiveI18n().messages.shell.couldNotSignIn);
    } finally {
      setAuthBusy(false);
    }
  };

  const handleResetPassword = async (password: string) => {
    if (!resetToken) {
      return;
    }
    setAuthBusy(true);
    setAuthError(null);
    try {
      await confirmPasswordReset(resetToken, password);
      setResetToken(null);
      setAuthNotice(null);
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : getActiveI18n().messages.shell.couldNotSignIn);
    } finally {
      setAuthBusy(false);
    }
  };

  const handleLogin = async (mnemonic: string) => {
    setAuthBusy(true);
    setAuthError(null);
    try {
      await applySession(await loginWithMnemonic(mnemonic));
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : getActiveI18n().messages.shell.couldNotSignIn);
    } finally {
      setAuthBusy(false);
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const confirm = params.get('confirm');
    const reset = params.get('reset');
    if (!confirm && !reset) {
      return;
    }
    setShowSplash(false);
    markSplashSeen();
    window.history.replaceState({}, '', window.location.pathname);
    setAuthNotice(null);
    setIsSeedPhraseModalOpen(true);
    if (reset) {
      setResetToken(reset);
    }
    if (confirm) {
      setConfirmToken(confirm);
    }
  }, []);

  const confirmAttempted = useRef(false);
  useEffect(() => {
    // Opening the email link is itself the confirmation step, so submit it
    // automatically instead of showing a "check your email" screen again.
    if (confirmToken && !confirmAttempted.current) {
      confirmAttempted.current = true;
      void handleConfirmEmail();
    }
  }, [confirmToken]);

  const handleLogout = async () => {
    setAuthBusy(true);
    setAuthError(null);
    try {
      await logoutAccount();
    } catch {
      // The screen still signs out when the API is unreachable.
    } finally {
      setAccount(null);
      setRevealedMnemonic(null);
      setAuthBusy(false);
    }
  };

  const handleTogglePublic = async (isPublic: boolean, consentVersion: string) => {
    if (!account) {
      setIsSeedPhraseModalOpen(true);
      return;
    }
    const previous = account.isPublic;
    setAccount({ ...account, isPublic });
    try {
      const updated = await updateShareSettings(isPublic, consentVersion);
      setAccount({ ...account, isPublic: updated.isPublic });
    } catch {
      setAccount({ ...account, isPublic: previous });
      throw new Error('Public sharing settings could not be updated');
    }
  };

  const dismissSplash = () => {
    markSplashSeen();
    setShowSplash(false);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#f8f9ff] text-[#0b1c30] antialiased">
      {showSplash && <SplashScreen onDone={dismissSplash} />}
      {/* Top Fixed Header with Brand, Tabs, and Ephemeral Address */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenTerminal={() => setIsTerminalModalOpen(true)}
        onOpenSeedPhrase={() => {
          setAuthError(null);
          setIsSeedPhraseModalOpen(true);
        }}
        accountAddress={publicIdLabel}
        isAuthenticated={account !== null}
      />

      {/* Main Content Pane */}
      <main className="w-full pt-20 flex-1 bg-[#f8f9ff]">
        {/* Live Biological Biomarker Status Ribbon */}
        <StatusRibbon
          biomarkers={biomarkers}
          tutorial={currentPanel.sourceType === 'demo'}
          labName={currentPanel.labName}
        />
        <DataDisclaimer />

        {/* Tab 1: Overview / Landing */}
        {activeTab === 'overview-landing' && (
          <OverviewTab
            setActiveTab={setActiveTab}
            onOpenSeedPhrase={() => {
              setAuthError(null);
              setIsSeedPhraseModalOpen(true);
            }}
            onOpenProofModal={() => setIsProofModalOpen(true)}
            biomarkers={biomarkers}
            onUpdateBiomarkers={setBiomarkers}
            phenoAge={phenoAgeCalculation.isValid ? phenoAgeCalculation.phenoAge : null}
            chronologicalAge={chronologicalAge}
            disclaimer={phenoAgeCalculation.disclaimer}
            isAuthenticated={account !== null}
          />
        )}

        {/* Tab 2: Upload Lab */}
        {activeTab === 'upload-lab' && (
          <UploadLabTab
            onLoadPanel={handleLoadPanel}
            setActiveTab={setActiveTab}
            accountAddress={publicIdLabel}
            isAuthenticated={account !== null}
            onRequestAuth={() => {
              setAuthError(null);
              setIsSeedPhraseModalOpen(true);
            }}
          />
        )}

        {/* Tab 3: Review & Extraction */}
        {activeTab === 'review-extraction' && (
          <ReviewExtractionTab
            currentPanel={currentPanel}
            onUpdateBiomarkers={setBiomarkers}
            setActiveTab={setActiveTab}
            onSaved={() => restoreSavedPanels()}
          />
        )}

        {/* Tab 4: PhenoAge™ Engine */}
        {activeTab === 'phenoage-engine' && (
          <PhenoAgeEngineTab
            calculation={phenoAgeCalculation}
            scoreError={phenoAgeError}
            biomarkers={biomarkers}
            onUpdateBiomarkers={setBiomarkers}
            chronologicalAge={chronologicalAge}
            onUpdateChronologicalAge={setChronologicalAge}
            onSaveToHistory={handleSaveToHistory}
            setActiveTab={setActiveTab}
            onOpenProofModal={() => setIsProofModalOpen(true)}
          />
        )}

        {/* Tab 5: Biomarker History */}
        {activeTab === 'biomarker-history' && (
          <BiomarkerHistoryTab
            history={history}
            isAuthenticated={account !== null}
            onDeleteHistory={handleDeleteHistory}
            onSelectRecord={handleSelectHistoricalRecord}
            setActiveTab={setActiveTab}
          />
        )}

        {activeTab === 'protocol-journal' && (
          <ProtocolJournalTab
            isAuthenticated={account !== null}
            onRequestAuth={() => {
              setAuthError(null);
              setIsSeedPhraseModalOpen(true);
            }}
          />
        )}

        {/* Tab 6: Data Sovereignty & Public Sharing */}
        {activeTab === 'data-sovereignty-public-sharing' && (
          <DataSovereigntyTab
            accountAddress={publicIdLabel}
            isAuthenticated={account !== null}
            isPublic={account?.isPublic ?? false}
            onTogglePublic={handleTogglePublic}
            onAccountDeleted={() => {
              setAccount(null);
              setRevealedMnemonic(null);
            }}
            onPurgeMemory={handlePurgeMemory}
            onOpenSeedPhrase={() => {
              setAuthError(null);
              setIsSeedPhraseModalOpen(true);
            }}
            setActiveTab={setActiveTab}
          />
        )}

        {activeTab === 'research-news' && (
          <ResearchNewsTab markerIds={currentPanel.focusMarkerIds} />
        )}

        {activeTab === 'user-instructions' && <UserInstructionsTab setActiveTab={setActiveTab} />}
      </main>

      {/* Protocol Footer */}
      <Footer />

      {/* Proof Modal */}
      <ProofModal
        isOpen={isProofModalOpen}
        onClose={() => setIsProofModalOpen(false)}
        biomarkers={biomarkers}
        phenoAge={phenoAgeCalculation.phenoAge}
        chronologicalAge={chronologicalAge}
      />

      {/* Seed Phrase Vault Modal */}
      <SeedPhraseModal
        isOpen={isSeedPhraseModalOpen}
        onClose={() => {
          if (revealedMnemonic && revealedMnemonic.length === 12) return;
          setIsSeedPhraseModalOpen(false);
        }}
        publicId={account?.publicId ?? null}
        revealedMnemonic={revealedMnemonic}
        isAuthenticated={account !== null}
        isBusy={authBusy}
        error={authError}
        notice={authNotice}
        resetToken={resetToken}
        confirmToken={confirmToken}
        onConfirmEmail={() => {
          void handleConfirmEmail();
        }}
        onRegister={(email, password, researchReuse) => {
          void handleRegister(email, password, researchReuse);
        }}
        onEmailLogin={(email, password) => {
          void handleEmailLogin(email, password);
        }}
        onRequestReset={(email) => {
          void handleRequestReset(email);
        }}
        onResetPassword={(password) => {
          void handleResetPassword(password);
        }}
        onLogin={(mnemonic) => {
          void handleLogin(mnemonic);
        }}
        onLogout={() => {
          void handleLogout();
        }}
        onConfirmPhraseSaved={() => {
          setRevealedMnemonic(null);
          setIsSeedPhraseModalOpen(false);
        }}
      />

      {import.meta.env.DEV && (
        <TerminalModal
          isOpen={isTerminalModalOpen}
          onClose={() => setIsTerminalModalOpen(false)}
          accountAddress={publicIdLabel}
          phenoAge={phenoAgeCalculation.phenoAge}
        />
      )}
    </div>
  );
}

export default function App() {
  const [isLabPortal, setIsLabPortal] = useState(
    () => window.location.pathname.replace(/\/+$/, '') === '/lab',
  );

  useEffect(() => {
    const updateRoute = () => {
      setIsLabPortal(window.location.pathname.replace(/\/+$/, '') === '/lab');
    };
    window.addEventListener('popstate', updateRoute);
    return () => window.removeEventListener('popstate', updateRoute);
  }, []);

  return isLabPortal ? <LabPortalPage /> : <MainApp />;
}
