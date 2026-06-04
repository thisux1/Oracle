import { useState, useEffect } from "react";
import { useOracleStore } from "../stores/useOracleStore";
import GlassCard from "../components/GlassCard";
import AnimatedCounter from "../components/AnimatedCounter";

const RARITY_COLORS = {
  common: { bg: "#475569", text: "#e2e8f0" },
  uncommon: { bg: "#34d399", text: "#064e3b" },
  rare: { bg: "#60a5fa", text: "#1e3a5f" },
  epic: { bg: "#a78bfa", text: "#3b0764" },
  legendary: { bg: "#fbbf24", text: "#78350f" },
  eternal: { bg: "#f87171", text: "#7f1d1d" },
};

const RARITY_ORDER = ["common", "uncommon", "rare", "epic", "legendary", "eternal"];

function LootTable({ drops, title }) {
  const entries = Object.entries(drops || {}).sort((a, b) => b[1] - a[1]);
  const maxVal = entries.length > 0 ? Math.max(...entries.map(([, v]) => v)) : 1;

  if (entries.length === 0) {
    return (
      <div className="rounded-xl p-3 text-xs" style={{ background: "var(--bg-elevated)", color: "var(--text-dim)" }}>
        No data
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {entries.map(([name, count]) => (
        <div key={name}>
          <div className="mb-1 flex items-center justify-between text-xs">
            <span style={{ color: "var(--text-secondary)" }}>{name}</span>
            <span className="tabular-nums" style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
              {count}
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full" style={{ background: "var(--bg-void)" }}>
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${(count / maxVal) * 100}%`,
                background: "var(--accent-cyan)",
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function CardGrid({ cards }) {
  const entries = Object.entries(cards || {}).sort((a, b) => {
    const ai = RARITY_ORDER.indexOf(a[0].toLowerCase());
    const bi = RARITY_ORDER.indexOf(b[0].toLowerCase());
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });

  if (entries.length === 0) {
    return (
      <div className="rounded-xl p-3 text-xs" style={{ background: "var(--bg-elevated)", color: "var(--text-dim)" }}>
        No cards collected
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {entries.map(([rarity, count]) => {
        const style = RARITY_COLORS[rarity.toLowerCase()] || RARITY_COLORS.common;
        return (
          <div
            key={rarity}
            className="rounded-xl px-3 py-2 text-center"
            style={{ background: style.bg, color: style.text }}
          >
            <p className="text-lg font-bold tabular-nums" style={{ fontFamily: "var(--font-mono)" }}>
              {count}
            </p>
            <p className="text-[10px] font-semibold uppercase tracking-wide opacity-80">{rarity}</p>
          </div>
        );
      })}
    </div>
  );
}

function MiscStat({ label, value, color = "var(--accent-cyan)" }) {
  return (
    <div className="rounded-xl px-4 py-3 text-center" style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-subtle)" }}>
      <p className="text-xl font-bold tabular-nums" style={{ color, fontFamily: "var(--font-mono)" }}>
        {Number(value) || 0}
      </p>
      <p className="mt-1 text-[10px] font-medium uppercase tracking-wide" style={{ color: "var(--text-dim)" }}>
        {label}
      </p>
    </div>
  );
}

export default function StatsTab() {
  const [viewMode, setViewMode] = useState("session");

  const sessionStats = useOracleStore((s) => s.sessionStats);
  const totalStats = useOracleStore((s) => s.totalStats);
  const activeProfile = useOracleStore((s) => s.activeProfile);
  const fetchTotalStats = useOracleStore((s) => s.fetchTotalStats);

  // Fetch total stats when switching to total view
  useEffect(() => {
    if (viewMode === "total") {
      fetchTotalStats(activeProfile).catch(() => undefined);
    }
  }, [viewMode, activeProfile, fetchTotalStats]);

  const stats = viewMode === "session" ? sessionStats : totalStats;

  const commands = stats?.commands || {};
  const progress = stats?.progress || {};
  const loot = stats?.loot || {};
  const misc = stats?.misc || {};

  const totalCommands = Object.values(commands).reduce((a, b) => a + (Number(b) || 0), 0);

  return (
    <div className="space-y-4">
      {/* Mode Toggle */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setViewMode("session")}
          className="rounded-lg px-4 py-1.5 text-xs font-semibold transition-all duration-200"
          style={{
            background: viewMode === "session" ? "var(--accent-primary)" : "var(--bg-elevated)",
            color: viewMode === "session" ? "#fff" : "var(--text-secondary)",
            border: `1px solid ${viewMode === "session" ? "var(--accent-primary)" : "var(--border-subtle)"}`,
          }}
        >
          Session
        </button>
        <button
          type="button"
          onClick={() => setViewMode("total")}
          className="rounded-lg px-4 py-1.5 text-xs font-semibold transition-all duration-200"
          style={{
            background: viewMode === "total" ? "var(--accent-primary)" : "var(--bg-elevated)",
            color: viewMode === "total" ? "#fff" : "var(--text-secondary)",
            border: `1px solid ${viewMode === "total" ? "var(--accent-primary)" : "var(--border-subtle)"}`,
          }}
        >
          All-Time
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <AnimatedCounter value={progress.coins || 0} label="Coins" color="#fbbf24" />
        <AnimatedCounter value={progress.xp || 0} label="XP" color="#a78bfa" />
        <AnimatedCounter value={progress.levels || 0} label="Levels" color="var(--accent-cyan)" />
        <AnimatedCounter value={totalCommands} label="Total Commands" color="var(--accent-success)" />
      </div>

      {/* Command Breakdown */}
      <GlassCard title="Commands" subtitle="Execution count by type">
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-5">
          {Object.entries(commands).map(([key, val]) => (
            <div
              key={key}
              className="rounded-xl px-3 py-2 text-center"
              style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-subtle)" }}
            >
              <p className="text-lg font-bold tabular-nums" style={{ color: "var(--accent-cyan)", fontFamily: "var(--font-mono)" }}>
                {val || 0}
              </p>
              <p className="mt-0.5 text-[10px] font-medium uppercase tracking-wide" style={{ color: "var(--text-dim)" }}>
                {key}
              </p>
            </div>
          ))}
        </div>
      </GlassCard>

      {/* Loot Breakdown */}
      <div className="grid gap-4 lg:grid-cols-2">
        <GlassCard title="Mob Drops">
          <LootTable drops={loot.mob_drops} />
        </GlassCard>
        <GlassCard title="Lootbox Drops">
          <LootTable drops={loot.lootbox_drops} />
        </GlassCard>
        <GlassCard title="Work Drops">
          <LootTable drops={loot.work_drops} />
        </GlassCard>
        <GlassCard title="Farm Drops">
          <LootTable drops={loot.farm_drops} />
        </GlassCard>
      </div>

      {/* Cards by Rarity */}
      <GlassCard title="Cards" subtitle="Collection by rarity">
        <CardGrid cards={misc.cards} />
      </GlassCard>

      {/* Misc Stats */}
      <GlassCard title="Misc Stats">
        <div className="grid grid-cols-3 gap-3">
          <MiscStat label="Coolness" value={misc.coolness} color="var(--accent-primary)" />
          <MiscStat label="Arena Cookies" value={misc.arena_cookies} color="var(--accent-warning)" />
          <MiscStat label="Guard Events" value={misc.guard_events} color="var(--accent-danger)" />
        </div>
      </GlassCard>
    </div>
  );
}
