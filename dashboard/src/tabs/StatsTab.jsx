import { useState, useEffect, useMemo } from "react";
import { useOracleStore } from "../stores/useOracleStore";
import GlassCard from "../components/GlassCard";
import AnimatedCounter from "../components/AnimatedCounter";

const RARITY_COLORS = {
  common: { bg: "#475569", text: "#e2e8f0" },
  uncommon: { bg: "#10b981", text: "#e6fffa" },
  epic: { bg: "#8b5cf6", text: "#f5f3ff" },
  omega: { bg: "#f59e0b", text: "#fffbeb" },
  godly: { bg: "#06b6d4", text: "#ecfeff" },
  eternal: { bg: "#ef4444", text: "#fef2f2" },
};

const RARITY_ORDER = ["common", "uncommon", "epic", "omega", "godly", "eternal"];

function LootTable({ drops, title }) {
  const entries = Object.entries(drops || {}).sort((a, b) => b[1] - a[1]);
  const maxVal = entries.length > 0 ? Math.max(...entries.map(([, v]) => v)) : 0;

  if (entries.length === 0) {
    return (
      <div className="rounded-xl p-3 text-xs" style={{ background: "var(--bg-elevated)", color: "var(--text-dim)" }}>
        Sem dados
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {entries.map(([name, count]) => {
        const pct = maxVal > 0 ? (count / maxVal) * 100 : 0;
        return (
          <div key={name}>
            <div className="mb-1 flex items-center justify-between text-xs">
              <span style={{ color: "var(--text-secondary)" }}>{name}</span>
              <span className="tabular-nums" style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                {count}
              </span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full" style={{ background: "var(--bg-void)" }}>
              <div
                className="h-full rounded-full transition-[width] duration-500"
                style={{
                  width: `${pct}%`,
                  background: "var(--accent-cyan)",
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

const RARITY_TRANSLATION = {
  common: "Common",
  uncommon: "Uncommon",
  epic: "Epic",
  omega: "Omega",
  godly: "Godly",
  eternal: "Eternal"
};

function CardGrid({ cards }) {
  const entries = Object.entries(cards || {}).sort((a, b) => {
    const ai = RARITY_ORDER.indexOf(a[0].toLowerCase());
    const bi = RARITY_ORDER.indexOf(b[0].toLowerCase());
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });

  if (entries.length === 0) {
    return (
      <div className="rounded-xl p-3 text-xs" style={{ background: "var(--bg-elevated)", color: "var(--text-dim)" }}>
        Nenhum card coletado
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {entries.map(([rarity, count]) => {
        const style = RARITY_COLORS[rarity.toLowerCase()] || RARITY_COLORS.common;
        const rarityLabel = RARITY_TRANSLATION[rarity.toLowerCase()] || rarity;
        return (
          <div
            key={rarity}
            className="rounded-xl px-3 py-2 text-center"
            style={{ background: style.bg, color: style.text }}
          >
            <p className="text-lg font-bold tabular-nums" style={{ fontFamily: "var(--font-mono)" }}>
              {count}
            </p>
            <p className="text-[10px] font-semibold uppercase tracking-wide opacity-80">{rarityLabel}</p>
          </div>
        );
      })}
    </div>
  );
}

const CMD_COLORS = [
  "var(--accent-cyan)", "var(--accent-primary)", "var(--accent-success)",
  "var(--accent-warning)", "var(--accent-danger)", "#f472b6",
  "#a78bfa", "#38bdf8", "#fbbf24", "#34d399",
];

function DonutChart({ data, size = 120, thickness = 14 }) {
  const entries = useMemo(() => {
    const filtered = Object.entries(data || {}).filter(([, v]) => v > 0);
    const total = filtered.reduce((a, [, v]) => a + v, 0);
    return filtered.map(([k, v]) => ({ key: k, value: v, pct: total > 0 ? (v / total) * 100 : 0 }));
  }, [data]);

  const total = entries.reduce((a, e) => a + e.value, 0);
  const r = (size - thickness) / 2;
  const circumference = 2 * Math.PI * r;

  if (entries.length === 0) {
    return <div className="text-xs" style={{ color: "var(--text-dim)" }}>No data</div>;
  }

  let offset = 0;
  return (
    <div className="flex items-center gap-4">
      <svg width={size} height={size} className="flex-shrink-0">
        {entries.map((entry, i) => {
          const dash = (entry.pct / 100) * circumference;
          const rotation = (offset / 100) * 360 - 90;
          offset += entry.pct;
          return (
            <circle
              key={entry.key}
              cx={size / 2}
              cy={size / 2}
              r={r}
              fill="none"
              stroke={CMD_COLORS[i % CMD_COLORS.length]}
              strokeWidth={thickness}
              strokeDasharray={`${dash} ${circumference - dash}`}
              transform={`rotate(${rotation} ${size / 2} ${size / 2})`}
              style={{ transition: "stroke-dasharray 0.5s ease" }}
            />
          );
        })}
        <text x={size / 2} y={size / 2 - 6} textAnchor="middle" className="text-sm font-bold" fill="var(--text-primary)" style={{ fontFamily: "var(--font-mono)" }}>
          {total}
        </text>
        <text x={size / 2} y={size / 2 + 10} textAnchor="middle" className="text-[9px]" fill="var(--text-secondary)">
          commands
        </text>
      </svg>
      <div className="space-y-1">
        {entries.slice(0, 6).map((entry, i) => (
          <div key={entry.key} className="flex items-center gap-2 text-xs">
            <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: CMD_COLORS[i % CMD_COLORS.length] }} />
            <span style={{ color: "var(--text-secondary)" }}>{entry.key}</span>
            <span className="tabular-nums ml-auto" style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>{entry.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DeltaIndicator({ session, total }) {
  if (!total || total === 0) return null;
  const delta = session - total;
  const pct = total > 0 ? ((delta / total) * 100).toFixed(1) : "0";
  const positive = delta > 0;
  return (
    <span
      className="text-[10px] font-semibold tabular-nums"
      style={{ color: positive ? "#22c55e" : delta < 0 ? "#ef4444" : "var(--text-secondary)", fontFamily: "var(--font-mono)" }}
    >
      {positive ? "+" : ""}{pct}%
    </span>
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
  const totalLootboxes = Object.values(loot.lootbox_drops || {}).reduce((a, b) => a + (Number(b) || 0), 0);

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
          Sessão
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
          Total Acumulado
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <AnimatedCounter value={progress.coins || 0} label="Coins" color="#fbbf24" delta={viewMode === "session" ? <DeltaIndicator session={progress.coins || 0} total={totalStats?.progress?.coins || 0} /> : null} />
        <AnimatedCounter value={progress.xp || 0} label="XP" color="#a78bfa" delta={viewMode === "session" ? <DeltaIndicator session={progress.xp || 0} total={totalStats?.progress?.xp || 0} /> : null} />
        <AnimatedCounter value={progress.levels || 0} label="Níveis" color="var(--accent-cyan)" delta={viewMode === "session" ? <DeltaIndicator session={progress.levels || 0} total={totalStats?.progress?.levels || 0} /> : null} />
        <AnimatedCounter value={totalLootboxes} label="Lootboxes" color="#f472b6" />
        <AnimatedCounter value={totalCommands} label="Comandos" color="var(--accent-success)" />
      </div>

      {/* Donut Chart — Command Distribution */}
      <GlassCard title="Command Distribution" subtitle="Donut chart by type">
        <DonutChart data={commands} />
      </GlassCard>

      {/* Command Breakdown */}
      <GlassCard title="Comandos" subtitle="Contagem de execução por tipo">
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
        <GlassCard title="Drops de Mobs (Mob Drops)">
          <LootTable drops={loot.mob_drops} />
        </GlassCard>
        <GlassCard title="Drops de Lootbox (Lootbox Drops)">
          <LootTable drops={loot.lootbox_drops} />
        </GlassCard>
        <GlassCard title="Drops de Work (Work Drops)">
          <LootTable drops={loot.work_drops} />
        </GlassCard>
        <GlassCard title="Drops de Farm (Farm Drops)">
          <LootTable drops={loot.farm_drops} />
        </GlassCard>
      </div>

      {/* Cards by Rarity */}
      <GlassCard title="Cards" subtitle="Coleção por raridade">
        <CardGrid cards={misc.cards} />
      </GlassCard>

      {/* Misc Stats */}
      <GlassCard title="Estatísticas Diversas">
        <div className="grid grid-cols-3 gap-3">
          <MiscStat label="Coolness" value={misc.coolness} color="var(--accent-primary)" />
          <MiscStat label="Arena Cookies" value={misc.arena_cookies} color="var(--accent-warning)" />
          <MiscStat label="Guard Events" value={misc.guard_events} color="var(--accent-danger)" />
        </div>
      </GlassCard>
    </div>
  );
}
