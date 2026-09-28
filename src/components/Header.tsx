import React, { useEffect, useRef, useState } from 'react';
import { TabType } from '../types';
import { ChevronDown, Shield, Terminal, Menu, X, KeyRound } from 'lucide-react';
import logo from '../assets/images/logo.jpg';
import { useI18n } from '../i18n/I18nProvider';
import { LanguageSwitcher } from './LanguageSwitcher';

interface HeaderProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  onOpenTerminal: () => void;
  onOpenSeedPhrase: () => void;
  accountAddress: string;
  isAuthenticated: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  onOpenTerminal,
  onOpenSeedPhrase,
  accountAddress,
  isAuthenticated,
}) => {
  const { m } = useI18n();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const desktopNavRef = useRef<HTMLElement>(null);

  const navItems: { id: TabType; label: string }[] = [
    { id: 'overview-landing', label: m.nav.overviewLanding },
    { id: 'upload-lab', label: m.nav.uploadLab },
    { id: 'review-extraction', label: m.nav.reviewExtraction },
    { id: 'phenoage-engine', label: m.nav.phenoAgeEngine },
    { id: 'biomarker-history', label: m.nav.biomarkerHistory },
    { id: 'protocol-journal', label: m.nav.journal },
    { id: 'data-sovereignty-public-sharing', label: m.nav.dataSovereignty },
    { id: 'research-news', label: m.nav.news },
  ];

  const labItems = navItems.filter((item) => item.id === 'upload-lab' || item.id === 'review-extraction');
  const phenoAgeItems = navItems.filter(
    (item) => item.id === 'phenoage-engine' || item.id === 'biomarker-history',
  );

  const desktopGroups: { id: string; label: string; items: { id: TabType; label: string }[] }[] = [
    { id: 'lab', label: m.nav.lab, items: labItems },
    { id: 'phenoage', label: m.nav.phenoAge, items: phenoAgeItems },
  ];

  useEffect(() => {
    if (!openMenu) {
      return;
    }
    const onPointerDown = (event: MouseEvent) => {
      if (!desktopNavRef.current?.contains(event.target as Node)) {
        setOpenMenu(null);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpenMenu(null);
      }
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [openMenu]);

  const linkClass = (isActive: boolean) =>
    `font-['Inter'] text-[13px] font-medium px-3 py-1.5 rounded transition-all cursor-pointer whitespace-nowrap ${
      isActive
        ? 'bg-[#007bb9] text-[#ffffff] shadow-sm font-semibold'
        : 'text-[#3f4850] hover:bg-[#e5eeff] hover:text-[#0b1c30]'
    }`;

  const selectTab = (tab: TabType) => {
    setActiveTab(tab);
    setOpenMenu(null);
  };

  return (
    <header className="fixed top-0 left-0 w-full z-50 bg-[#ffffff]/90 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.04)] border-b border-[#e2e8f0]">
      <div className="relative w-full max-w-[1440px] mx-auto px-4 lg:px-6 h-20 flex items-center justify-between gap-4 xl:gap-6 min-w-0">
        <div className="flex items-center min-w-0">
          <button
            onClick={() => setActiveTab('overview-landing')}
            className="flex items-center gap-3 text-left focus:outline-none group cursor-pointer shrink-0"
            id="brand-logo-btn"
          >
            <div className="relative">
              <img
                alt={m.nav.brandAlt}
                className="w-12 h-12 rounded-full object-cover ring-2 ring-[#006194]/20 group-hover:ring-[#006194]/50 transition-all"
                src={logo}
                referrerPolicy="no-referrer"
              />
              <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-[#00855b] border-2 border-white rounded-full"></span>
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5">
                <span className="font-['Inter'] text-[18px] text-[#0b1c30] tracking-tight font-bold">
                  NotMice
                </span>
              </div>
              <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74] hidden sm:inline-block">
                {m.nav.researchProtocol}
              </span>
            </div>
          </button>
        </div>

          <nav
            ref={desktopNavRef}
            className="hidden xl:flex shrink-0 items-center gap-1"
            id="desktop-nav"
          >
            <button
              type="button"
              onClick={() => selectTab('overview-landing')}
              data-path="overview-landing"
              className={linkClass(activeTab === 'overview-landing')}
            >
              {m.nav.overview}
            </button>

            {desktopGroups.map((group) => {
              const isOpen = openMenu === group.id;
              const isActive = group.items.some((item) => item.id === activeTab);
              return (
                <div key={group.id} className="relative">
                  <button
                    type="button"
                    aria-expanded={isOpen}
                    aria-haspopup="menu"
                    onClick={() => setOpenMenu(isOpen ? null : group.id)}
                    className={`${linkClass(isActive)} inline-flex items-center gap-1`}
                  >
                    {group.label}
                    <ChevronDown
                      className={`w-3.5 h-3.5 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                    />
                  </button>
                  {isOpen && (
                    <div
                      role="menu"
                      className="absolute left-0 top-full mt-1 min-w-[220px] rounded-lg border border-[#e2e8f0] bg-[#ffffff] py-1 shadow-lg"
                    >
                      {group.items.map((item) => {
                        const itemActive = activeTab === item.id;
                        return (
                          <button
                            key={item.id}
                            type="button"
                            role="menuitem"
                            data-path={item.id}
                            onClick={() => selectTab(item.id)}
                            className={`block w-full text-left px-3 py-2 text-[13px] font-medium cursor-pointer ${
                              itemActive
                                ? 'bg-[#007bb9] text-[#ffffff]'
                                : 'text-[#3f4850] hover:bg-[#eff4ff] hover:text-[#0b1c30]'
                            }`}
                          >
                            {item.label}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}

            <button
              type="button"
              onClick={() => selectTab('protocol-journal')}
              data-path="protocol-journal"
              className={linkClass(activeTab === 'protocol-journal')}
            >
              {m.nav.journal}
            </button>

            <button
              type="button"
              onClick={() => selectTab('data-sovereignty-public-sharing')}
              data-path="data-sovereignty-public-sharing"
              className={linkClass(activeTab === 'data-sovereignty-public-sharing')}
            >
              {m.nav.data}
            </button>

            <button
              type="button"
              onClick={() => selectTab('research-news')}
              data-path="research-news"
              className={linkClass(activeTab === 'research-news')}
            >
              {m.nav.news}
            </button>

            <div className="relative">
              <button
                type="button"
                aria-expanded={openMenu === 'documents'}
                aria-haspopup="menu"
                onClick={() => setOpenMenu(openMenu === 'documents' ? null : 'documents')}
                className={`${linkClass(activeTab === 'user-instructions')} inline-flex items-center gap-1`}
              >
                {m.nav.documents}
                <ChevronDown
                  className={`w-3.5 h-3.5 transition-transform ${openMenu === 'documents' ? 'rotate-180' : ''}`}
                />
              </button>
              {openMenu === 'documents' && (
                <div
                  role="menu"
                  className="absolute left-0 top-full mt-1 min-w-[220px] rounded-lg border border-[#e2e8f0] bg-[#ffffff] py-1 shadow-lg"
                >
                  <button
                    type="button"
                    role="menuitem"
                    data-path="user-instructions"
                    onClick={() => selectTab('user-instructions')}
                    className={`block w-full text-left px-3 py-2 text-[13px] font-medium cursor-pointer ${
                      activeTab === 'user-instructions'
                        ? 'bg-[#007bb9] text-[#ffffff]'
                        : 'text-[#3f4850] hover:bg-[#eff4ff] hover:text-[#0b1c30]'
                    }`}
                  >
                    {m.nav.userInstructions}
                  </button>
                </div>
              )}
            </div>
          </nav>

        {/* Right Status Controls */}
        <div className="flex items-center gap-2.5 shrink-0">
          {/* Ephemeral in-memory key */}
          <button
            onClick={onOpenSeedPhrase}
            title={isAuthenticated ? m.nav.accountRecovery : m.nav.signInOrCreate}
            className="hidden md:flex items-center gap-2 bg-[#eff4ff] hover:bg-[#e5eeff] px-2.5 py-1.5 rounded border border-[#dce9ff] transition-colors cursor-pointer"
          >
            <span className="w-2 h-2 rounded-full bg-[#00855b] animate-pulse"></span>
            <span className="font-['JetBrains_Mono'] text-[11px] text-[#0b1c30] font-medium">
              {accountAddress}
            </span>
            <span className="font-['JetBrains_Mono'] text-[11px] text-[#006947] font-semibold hidden lg:inline bg-[#4edea3]/20 px-1.5 py-0.5 rounded">
              {isAuthenticated ? m.nav.signedIn : m.nav.guest}
            </span>
          </button>

          <div className="hidden sm:flex items-center gap-1.5 bg-[#eff4ff] text-[#3f4850] px-2.5 py-1.5 rounded font-['JetBrains_Mono'] text-[11px] border border-[#dce9ff]">
            <Shield className="w-3.5 h-3.5 text-[#006947]" />
            <span className="font-medium">{m.nav.noRawFiles}</span>
          </div>

          {/* Key generation modal toggle */}
          <button
            onClick={onOpenSeedPhrase}
            aria-label={m.nav.accountRecovery}
            title={m.nav.accountRecovery}
            className="flex items-center gap-1 text-[#3f4850] hover:text-[#0b1c30] bg-[#eff4ff] hover:bg-[#e5eeff] p-2 rounded transition-colors border border-[#dce9ff] cursor-pointer"
          >
            <KeyRound className="w-4 h-4 text-[#006194]" />
          </button>

          <LanguageSwitcher />

          {import.meta.env.DEV && (
            <button
              onClick={onOpenTerminal}
              aria-label={m.nav.sessionLog}
              title={m.nav.sessionLog}
              className="flex items-center gap-1 text-[#3f4850] hover:text-[#0b1c30] bg-[#eff4ff] hover:bg-[#e5eeff] p-2 rounded transition-colors border border-[#dce9ff] cursor-pointer"
            >
              <Terminal className="w-4 h-4 text-[#3f4850]" />
            </button>
          )}

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="xl:hidden p-2 rounded text-[#3f4850] hover:bg-[#eff4ff] cursor-pointer"
            aria-label={m.nav.toggleNav}
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="xl:hidden bg-[#ffffff] border-b border-[#e2e8f0] px-4 py-3 shadow-lg">
          <div className="flex flex-col gap-1">
            <div className="flex justify-end pb-2">
              <LanguageSwitcher />
            </div>
            {navItems.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    setActiveTab(item.id);
                    setMobileMenuOpen(false);
                  }}
                  className={`text-left px-3 py-2 rounded text-[14px] font-medium ${
                    isActive
                      ? 'bg-[#007bb9] text-[#ffffff]'
                      : 'text-[#3f4850] hover:bg-[#eff4ff]'
                  }`}
                >
                  {item.label}
                </button>
              );
            })}
            <button
              type="button"
              onClick={() => {
                setActiveTab('user-instructions');
                setMobileMenuOpen(false);
              }}
              className={`text-left px-3 py-2 rounded text-[14px] font-medium ${
                activeTab === 'user-instructions'
                  ? 'bg-[#007bb9] text-[#ffffff]'
                  : 'text-[#3f4850] hover:bg-[#eff4ff]'
              }`}
            >
              {m.nav.userInstructions}
            </button>
            <button
              type="button"
              onClick={() => {
                setMobileMenuOpen(false);
                onOpenSeedPhrase();
              }}
              title={isAuthenticated ? m.nav.accountRecovery : m.nav.signInOrCreate}
              className="mt-2 border-t border-[#e2e8f0] flex w-full items-center justify-between px-3 py-2.5 text-left text-xs text-[#565e74] hover:bg-[#eff4ff] rounded cursor-pointer"
            >
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#00855b]"></span>
                {isAuthenticated ? m.nav.signedIn : m.nav.guest}
              </span>
              <span className="font-mono">{accountAddress}</span>
            </button>
          </div>
        </div>
      )}
    </header>
  );
};
