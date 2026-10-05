import React, { useEffect, useRef, useState } from 'react';
import { TabType } from '../types';
import { ChevronDown, Shield, Terminal, Menu, X, KeyRound, Stethoscope } from 'lucide-react';
import { BRAND_NAME } from '../config/site';
import { CABINET_SECTIONS, isCabinetTab, pathForTab } from '../routes';
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

type DesktopGroupItem = { id: TabType; label: string };

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
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cancelMenuClose = () => {
    if (closeTimer.current !== null) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  };

  const openMenuNow = (id: string) => {
    cancelMenuClose();
    setOpenMenu(id);
  };

  // Keep the menu open briefly after the pointer leaves, so moving across the
  // small gap between the trigger and the panel does not dismiss it before a click.
  const scheduleMenuClose = (id: string) => {
    cancelMenuClose();
    closeTimer.current = setTimeout(() => {
      setOpenMenu((current) => (current === id ? null : current));
      closeTimer.current = null;
    }, 180);
  };

  useEffect(
    () => () => {
      if (closeTimer.current !== null) {
        clearTimeout(closeTimer.current);
      }
    },
    [],
  );

  const uploadItems: DesktopGroupItem[] = [
    { id: 'upload-lab', label: m.nav.uploadLab },
    { id: 'review-extraction', label: m.nav.reviewExtraction },
  ];
  const cabinetItems: DesktopGroupItem[] = CABINET_SECTIONS.map((section) => ({
    id: section.tab,
    label: m.cabinet.nav[section.key],
  }));

  type DesktopEntry =
    | { kind: 'group'; id: string; label: string; items: DesktopGroupItem[] }
    | { kind: 'link'; item: DesktopGroupItem };

  const desktopEntries: DesktopEntry[] = [
    { kind: 'group', id: 'upload', label: m.nav.upload, items: uploadItems },
    { kind: 'link', item: { id: 'phenoage-engine', label: m.nav.phenoAge } },
    { kind: 'group', id: 'cabinet', label: m.nav.cabinet, items: cabinetItems },
    { kind: 'link', item: { id: 'research-news', label: m.nav.news } },
    { kind: 'link', item: { id: 'user-instructions', label: m.nav.documents } },
  ];

  /** Mobile drawer: the same order as the desktop bar, groups flattened under a heading. */
  const mobileSections: { heading?: string; items: DesktopGroupItem[] }[] = [
    { items: [{ id: 'overview-landing', label: m.nav.overview }] },
    { heading: m.nav.upload, items: uploadItems },
    { items: [{ id: 'phenoage-engine', label: m.nav.phenoAgeEngine }] },
    { heading: m.nav.cabinet, items: cabinetItems },
    {
      items: [
        { id: 'research-news', label: m.nav.news },
        { id: 'user-instructions', label: m.nav.documents },
      ],
    },
  ];

  /** Signed in: the account chip opens the cabinet. Guest: it opens sign-in. */
  const openAccountChip = () => {
    if (isAuthenticated) {
      selectTab('cabinet');
    } else {
      onOpenSeedPhrase();
    }
  };

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
    `font-['Inter'] text-[13px] font-medium px-2.5 2xl:px-3 py-1.5 rounded transition-all cursor-pointer whitespace-nowrap ${
      isActive
        ? 'bg-[#007bb9] text-[#ffffff] shadow-sm font-semibold'
        : 'text-[#3f4850] hover:bg-[#e5eeff] hover:text-[#0b1c30]'
    }`;

  const selectTab = (tab: TabType) => {
    cancelMenuClose();
    setActiveTab(tab);
    setOpenMenu(null);
  };

  return (
    <header className="fixed top-0 left-0 w-full z-50 bg-[#ffffff]/90 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.04)] border-b border-[#e2e8f0]">
      <div className="relative w-full max-w-[1440px] mx-auto px-4 lg:px-6 h-20 flex items-center justify-between gap-4 xl:gap-6 min-w-0">
        <div className="flex items-center shrink-0">
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
                  {BRAND_NAME}
                </span>
              </div>
              <span className="font-['JetBrains_Mono'] text-[11px] text-[#565e74] hidden sm:inline-block xl:hidden">
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
            <a
              href="/"
              onClick={(event) => {
                event.preventDefault();
                selectTab('overview-landing');
              }}
              aria-current={activeTab === 'overview-landing' ? 'page' : undefined}
              data-path="overview-landing"
              className={linkClass(activeTab === 'overview-landing')}
            >
              {m.nav.overview}
            </a>

            {desktopEntries.map((entry) => {
              if (entry.kind === 'link') {
                const item = entry.item;
                return (
                  <a
                    key={item.id}
                    href={pathForTab(item.id)}
                    onClick={(event) => {
                      event.preventDefault();
                      selectTab(item.id);
                    }}
                    aria-current={activeTab === item.id ? 'page' : undefined}
                    data-path={item.id}
                    className={linkClass(activeTab === item.id)}
                  >
                    {item.label}
                  </a>
                );
              }
              const group = entry;
              const isOpen = openMenu === group.id;
              const isActive =
                group.items.some((item) => item.id === activeTab) ||
                (group.id === 'cabinet' && isCabinetTab(activeTab));
              return (
                <div
                  key={group.id}
                  className="relative"
                  onMouseEnter={() => openMenuNow(group.id)}
                  onMouseLeave={() => scheduleMenuClose(group.id)}
                >
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

            <a
              href={pathForTab('specialists')}
              onClick={(event) => {
                event.preventDefault();
                selectTab('specialists');
              }}
              aria-current={activeTab === 'specialists' ? 'page' : undefined}
              data-path="specialists"
              className={`ml-1 2xl:ml-2 inline-flex items-center gap-1.5 rounded border px-2.5 2xl:px-3 py-1.5 font-['Inter'] text-[13px] font-semibold whitespace-nowrap transition-colors ${
                activeTab === 'specialists'
                  ? 'border-[#004b73] bg-[#004b73] text-[#ffffff]'
                  : 'border-[#006194] text-[#004b73] hover:bg-[#e5eeff]'
              }`}
            >
              <Stethoscope className="w-3.5 h-3.5" aria-hidden="true" />
              {m.nav.specialists}
            </a>
          </nav>

        {/* Right Status Controls */}
        <div className="flex items-center gap-2.5 shrink-0">
          {/* Ephemeral in-memory key */}
          <div
            className="relative hidden md:block"
            onMouseEnter={() => openMenuNow('account-id')}
            onMouseLeave={() => scheduleMenuClose('account-id')}
          >
            <button
              type="button"
              onClick={openAccountChip}
              onFocus={() => openMenuNow('account-id')}
              onBlur={(event) => {
                const nextTarget = event.relatedTarget;
                if (
                  !(nextTarget instanceof Node) ||
                  !event.currentTarget.parentElement?.contains(nextTarget)
                ) {
                  setOpenMenu((current) => (current === 'account-id' ? null : current));
                }
              }}
              aria-expanded={openMenu === 'account-id'}
              aria-describedby={openMenu === 'account-id' ? 'account-public-id' : undefined}
              title={isAuthenticated ? m.nav.cabinet : m.nav.signInOrCreate}
              className="flex items-center gap-2 bg-[#eff4ff] hover:bg-[#e5eeff] px-2.5 py-1.5 rounded border border-[#dce9ff] transition-colors cursor-pointer"
            >
              <span className="w-2 h-2 rounded-full bg-[#00855b] animate-pulse"></span>
              <span className="font-['JetBrains_Mono'] text-[11px] text-[#006947] font-semibold bg-[#4edea3]/20 px-1.5 py-0.5 rounded">
                {isAuthenticated ? m.nav.signedIn : m.nav.guest}
              </span>
            </button>
            {openMenu === 'account-id' && (
              <div
                id="account-public-id"
                role="tooltip"
                className="absolute right-0 top-full mt-2 min-w-max rounded-lg border border-[#e2e8f0] bg-[#ffffff] px-3 py-2 shadow-lg"
              >
                <span className="block text-[11px] font-medium text-[#565e74]">{m.nav.publicId}</span>
                <span className="font-['JetBrains_Mono'] text-[12px] text-[#0b1c30]">
                  {accountAddress}
                </span>
              </div>
            )}
          </div>

          <div className="hidden 2xl:flex items-center gap-1.5 bg-[#eff4ff] text-[#3f4850] px-2.5 py-1.5 rounded font-['JetBrains_Mono'] text-[11px] border border-[#dce9ff]">
            <Shield className="w-3.5 h-3.5 text-[#006947]" />
            <span className="font-medium">{m.nav.noRawFiles}</span>
          </div>

          {/* Key generation modal toggle */}
          <button
            onClick={onOpenSeedPhrase}
            aria-label={m.nav.accountRecovery}
            title={m.nav.accountRecovery}
            className="hidden sm:flex items-center gap-1 text-[#3f4850] hover:text-[#0b1c30] bg-[#eff4ff] hover:bg-[#e5eeff] p-2 rounded transition-colors border border-[#dce9ff] cursor-pointer"
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
            {mobileSections.map((section, index) => (
              <div key={section.heading ?? `section-${index}`} className="flex flex-col gap-1">
                {section.heading && (
                  <span className="px-3 pt-2 text-[12px] font-semibold uppercase tracking-wider text-[#565e74]">
                    {section.heading}
                  </span>
                )}
                {section.items.map((item) => {
                  const isActive = activeTab === item.id;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => {
                        setActiveTab(item.id);
                        setMobileMenuOpen(false);
                      }}
                      className={`text-left px-3 py-2.5 rounded text-[15px] font-medium ${
                        isActive ? 'bg-[#007bb9] text-[#ffffff]' : 'text-[#3f4850] hover:bg-[#eff4ff]'
                      }`}
                    >
                      {item.label}
                    </button>
                  );
                })}
              </div>
            ))}
            <button
              type="button"
              onClick={() => {
                setActiveTab('specialists');
                setMobileMenuOpen(false);
              }}
              className={`mt-2 inline-flex items-center gap-2 rounded border px-3 py-2.5 text-left text-[15px] font-semibold ${
                activeTab === 'specialists'
                  ? 'border-[#004b73] bg-[#004b73] text-[#ffffff]'
                  : 'border-[#006194] text-[#004b73] hover:bg-[#e5eeff]'
              }`}
            >
              <Stethoscope className="w-4 h-4" aria-hidden="true" />
              {m.nav.specialists}
            </button>
            <button
              type="button"
              onClick={() => {
                setMobileMenuOpen(false);
                openAccountChip();
              }}
              title={isAuthenticated ? m.nav.accountRecovery : m.nav.signInOrCreate}
              className="mt-2 border-t border-[#e2e8f0] flex w-full items-center justify-between px-3 py-2.5 text-left text-xs text-[#565e74] hover:bg-[#eff4ff] rounded cursor-pointer"
            >
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#00855b]"></span>
                {isAuthenticated ? m.nav.signedIn : m.nav.guest}
              </span>
            </button>
            <details className="px-3 py-2 text-xs text-[#565e74]">
              <summary className="cursor-pointer font-medium">{m.nav.publicId}</summary>
              <span className="mt-1 block break-all font-mono text-[#0b1c30]">{accountAddress}</span>
            </details>
          </div>
        </div>
      )}
    </header>
  );
};
