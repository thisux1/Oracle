import { useEffect, useMemo, useState } from "react";
import { ApiClientError } from "./lib/api";
import { useOracleStore } from "./stores/useOracleStore";
import ProfileSidebar from "./components/ProfileSidebar";
import Header from "./components/Header";
import TabNav from "./components/TabNav";
import OverviewTab from "./tabs/OverviewTab";
import TerminalTab from "./tabs/TerminalTab";
import ConfigTab from "./tabs/ConfigTab";
import StatsTab from "./tabs/StatsTab";
import CustomCursor from "./components/CustomCursor";

const TAB_KEYS = ["overview", "terminal", "config", "stats"];

export default function App() {
  const [activeTab, setActiveTab] = useState(TAB_KEYS[0]);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const activeProfile = useOracleStore((s) => s.activeProfile);
  const loadingConfig = useOracleStore((s) => s.loadingConfig);
  const loadingStatus = useOracleStore((s) => s.loadingStatus);
  const lastError = useOracleStore((s) => s.lastError);

  const fetchProfiles = useOracleStore((s) => s.fetchProfiles);
  const fetchConfig = useOracleStore((s) => s.fetchConfig);
  const fetchStatus = useOracleStore((s) => s.fetchStatus);
  const fetchStats = useOracleStore((s) => s.fetchStats);
  const connectTerminal = useOracleStore((s) => s.connectTerminal);
  const disconnectTerminal = useOracleStore((s) => s.disconnectTerminal);

  // 1. Initial bootstrap of profiles list
  useEffect(() => {
    fetchProfiles().catch(() => undefined);
  }, [fetchProfiles]);

  // 2. Fetch config when active profile changes
  useEffect(() => {
    if (!activeProfile) return;
    fetchConfig(activeProfile).catch(() => undefined);
  }, [activeProfile, fetchConfig]);

  // 3. Connect terminal when active profile changes
  useEffect(() => {
    if (!activeProfile) return;
    connectTerminal(activeProfile);
    return () => disconnectTerminal();
  }, [activeProfile, connectTerminal, disconnectTerminal]);

  const fetchLogs = useOracleStore((s) => s.fetchLogs);

  // 4. Poll status, stats, and logs every 5s while profile is active
  useEffect(() => {
    if (!activeProfile) return;

    // Fetch immediately
    fetchStatus(activeProfile).catch(() => undefined);
    fetchStats(activeProfile).catch(() => undefined);
    fetchLogs(activeProfile).catch(() => undefined);

    const interval = setInterval(() => {
      fetchStatus(activeProfile).catch(() => undefined);
      fetchStats(activeProfile).catch(() => undefined);
      fetchLogs(activeProfile).catch(() => undefined);
    }, 5000);

    return () => clearInterval(interval);
  }, [activeProfile, fetchStatus, fetchStats, fetchLogs]);

  const loading = loadingConfig || loadingStatus;

  const errorText = useMemo(() => {
    if (!lastError) return "";
    if (lastError instanceof ApiClientError) return `${lastError.code}: ${lastError.message}`;
    if (lastError instanceof Error) return lastError.message;
    return "Unknown error";
  }, [lastError]);

  const navigateToTerminal = () => setActiveTab("terminal");

  return (
    <div className="h-screen overflow-hidden bg-[var(--bg-void)]">
      <CustomCursor />
      <div className="scanline" />
      <ProfileSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main area offset by sidebar width on desktop */}
      <div className="flex h-screen flex-col md:ml-[260px] overflow-hidden">
        <div className="flex-none space-y-3 px-4 pt-4 pb-0 md:px-6 md:pt-5">
          <Header onMenuToggle={() => setSidebarOpen((v) => !v)} />
          <TabNav activeTab={activeTab} onTabChange={setActiveTab} />
        </div>

        <main className="flex-1 min-h-0 flex flex-col mt-4">
          <div className={`tab-pane flex-1 overflow-y-auto px-4 pb-4 md:px-6 md:pb-5 ${activeTab === "overview" ? "block" : "hidden"}`}>
            <OverviewTab onNavigateTerminal={navigateToTerminal} />
          </div>

          <div className={`tab-pane flex-1 flex flex-col px-4 pb-4 md:px-6 md:pb-5 min-h-0 ${activeTab === "terminal" ? "flex" : "hidden"}`}>
            <TerminalTab isActive={activeTab === "terminal"} />
          </div>

          <div className={`tab-pane flex-1 overflow-y-auto px-4 pb-4 md:px-6 md:pb-5 ${activeTab === "config" ? "block" : "hidden"}`}>
            <ConfigTab />
          </div>

          <div className={`tab-pane flex-1 overflow-y-auto px-4 pb-4 md:px-6 md:pb-5 ${activeTab === "stats" ? "block" : "hidden"}`}>
            <StatsTab />
          </div>
        </main>
      </div>
    </div>
  );
}
