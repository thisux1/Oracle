import { useOracleStore } from "../stores/useOracleStore";
import StatusBadge from "./StatusBadge";

function formatUptime(seconds) {
  if (!seconds || seconds <= 0) return "0s";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

export default function Header({ onMenuToggle }) {
  const activeProfile = useOracleStore((s) => s.activeProfile);
  const botState = useOracleStore((s) => s.botState);
  const uptime = useOracleStore((s) => s.uptime);
  const botActionPending = useOracleStore((s) => s.botActionPending);
  const startBot = useOracleStore((s) => s.startBot);
  const stopBot = useOracleStore((s) => s.stopBot);

  const profileName = (activeProfile || "").replace(/\.ini$/i, "");

  return (
    <header className="glass flex items-center gap-3 rounded-2xl px-4 py-3 md:px-6 md:py-4">
      {/* Mobile hamburger */}
      <button
        type="button"
        onClick={onMenuToggle}
        className="btn btn-ghost shrink-0 p-2 md:hidden"
        aria-label="Toggle sidebar"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>

      {/* Profile name */}
      <div className="min-w-0 flex-1">
        <p
          className="truncate text-[11px] font-semibold uppercase tracking-[0.18em]"
          style={{ color: "var(--accent-cyan)" }}
        >
          {profileName || "No profile"}
        </p>
        <div className="mt-1 flex items-center gap-2">
          <StatusBadge state={botState} size="xs" />
          {(botState === "online" || botState === "starting") && uptime > 0 ? (
            <span
              className="text-[11px] tabular-nums"
              style={{ color: "var(--text-dim)", fontFamily: "var(--font-mono)" }}
            >
              {formatUptime(uptime)}
            </span>
          ) : null}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => startBot(activeProfile)}
          disabled={botActionPending || botState === "online" || botState === "starting"}
          className="btn btn-success"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="none">
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
          <span className="hidden sm:inline">Start</span>
        </button>
        <button
          type="button"
          onClick={() => stopBot(activeProfile)}
          disabled={botActionPending || botState === "offline" || botState === "stopping"}
          className="btn btn-danger"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="none">
            <rect x="4" y="4" width="16" height="16" rx="2" />
          </svg>
          <span className="hidden sm:inline">Stop</span>
        </button>
      </div>
    </header>
  );
}
