import { useCallback } from "react";
import { useOracleStore } from "../stores/useOracleStore";
import GlassCard from "../components/GlassCard";
import StatusBadge from "../components/StatusBadge";
import AnimatedCounter from "../components/AnimatedCounter";
import MiniTerminal from "../components/MiniTerminal";
import { Play, Square, Pause, RefreshCw, Cookie, ShieldAlert, Sparkles } from "lucide-react";

function formatUptime(seconds) {
  if (!seconds || seconds <= 0) return "0s";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function QueueBar({ label, value, max = 20, color }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span style={{ color: "var(--text-secondary)" }}>{label}</span>
        <span className="tabular-nums" style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
          {value}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full" style={{ background: "var(--bg-void)" }}>
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

export default function OverviewTab({ onNavigateTerminal }) {
  const activeProfile = useOracleStore((s) => s.activeProfile);
  const botState = useOracleStore((s) => s.botState);
  const uptime = useOracleStore((s) => s.uptime);
  const hpqSize = useOracleStore((s) => s.hpqSize);
  const lpqSize = useOracleStore((s) => s.lpqSize);
  const sessionStats = useOracleStore((s) => s.sessionStats);
  const terminalLines = useOracleStore((s) => s.terminalLines);
  const botActionPending = useOracleStore((s) => s.botActionPending);
  const startBot = useOracleStore((s) => s.startBot);
  const stopBot = useOracleStore((s) => s.stopBot);
  const sendTerminalBinary = useOracleStore((s) => s.sendTerminalBinary);
  const connected = useOracleStore((s) => s.terminalConnected);

  const handleSendCommand = useCallback((cmd) => {
    if (connected) {
      sendTerminalBinary(cmd + "\r");
    }
  }, [connected, sendTerminalBinary]);

  const commands = sessionStats?.commands || {};
  const progress = sessionStats?.progress || {};

  const counters = [
    { label: "Hunts", value: commands.hunt || 0, color: "var(--accent-cyan)" },
    { label: "Adventures", value: commands.adventure || 0, color: "var(--accent-primary)" },
    { label: "Farms", value: commands.farm || 0, color: "var(--accent-success)" },
    { label: "Lootboxes", value: commands.lootbox || 0, color: "var(--accent-warning)" },
    { label: "Coins", value: progress.coins || 0, color: "#fbbf24" },
    { label: "XP", value: progress.xp || 0, color: "#a78bfa" },
  ];

  return (
    <div className="space-y-4">
      {/* Top row: State + Queue + Quick Actions | Counters */}
      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        {/* Left column */}
        <div className="space-y-4">
          {/* Bot State Card */}
          <GlassCard title="Estado do Bot" subtitle={activeProfile}>
            <div className="flex items-start justify-between">
              <div>
                <StatusBadge state={botState} size="md" />
                <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                  <div>
                    <dt style={{ color: "var(--text-dim)" }}>Tempo Online (Uptime)</dt>
                    <dd className="mt-0.5 font-medium tabular-nums" style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                      {formatUptime(uptime)}
                    </dd>
                  </div>
                  <div>
                    <dt style={{ color: "var(--text-dim)" }}>Perfil</dt>
                    <dd className="mt-0.5 font-medium" style={{ color: "var(--text-primary)" }}>
                      {(activeProfile || "").replace(/\.ini$/i, "")}
                    </dd>
                  </div>
                </dl>
              </div>
            </div>
          </GlassCard>

          {/* Quick Actions */}
          <GlassCard title="Ações Rápidas">
            <div className="space-y-4">
              {/* Process control */}
              <div>
                <span className="text-[10px] uppercase tracking-wider font-semibold opacity-60 block mb-2">Daemon do Processo</span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => startBot(activeProfile)}
                    disabled={botActionPending || botState === "online" || botState === "starting"}
                    className="btn btn-success flex items-center gap-1.5 py-1.5 px-3 text-xs"
                  >
                    <Play size={12} /> Iniciar
                  </button>
                  <button
                    type="button"
                    onClick={() => stopBot(activeProfile)}
                    disabled={botActionPending || botState === "offline" || botState === "stopping"}
                    className="btn btn-danger flex items-center gap-1.5 py-1.5 px-3 text-xs"
                  >
                    <Square size={12} fill="currentColor" /> Parar
                  </button>
                </div>
              </div>

              {/* Bot commands */}
              {botState === "online" && (
                <div className="space-y-3 border-t pt-3" style={{ borderColor: "var(--border-subtle)" }}>
                  <div>
                    <span className="text-[10px] uppercase tracking-wider font-semibold opacity-60 block mb-2">Controle do Bot</span>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => handleSendCommand("/resume")}
                        disabled={!connected}
                        className="btn btn-ghost border border-[var(--border-subtle)] flex items-center gap-1.5 py-1.5 px-3 text-xs hover:bg-[rgba(52,211,153,0.1)] hover:text-[var(--accent-success)]"
                      >
                        <Play size={12} /> Retomar (Resume)
                      </button>
                      <button
                        type="button"
                        onClick={() => handleSendCommand("/pause")}
                        disabled={!connected}
                        className="btn btn-ghost border border-[var(--border-subtle)] flex items-center gap-1.5 py-1.5 px-3 text-xs hover:bg-[rgba(239,68,68,0.1)] hover:text-[var(--accent-danger)]"
                      >
                        <Pause size={12} /> Pausar (Pause)
                      </button>
                      <button
                        type="button"
                        onClick={() => handleSendCommand("/reset")}
                        disabled={!connected}
                        className="btn btn-ghost border border-[var(--border-subtle)] flex items-center gap-1.5 py-1.5 px-3 text-xs hover:bg-[rgba(96,165,250,0.1)] hover:text-[var(--accent-cyan)]"
                      >
                        <RefreshCw size={12} /> Resetar
                      </button>
                    </div>
                  </div>

                  <div>
                    <span className="text-[10px] uppercase tracking-wider font-semibold opacity-60 block mb-2">Time Cookie (TC)</span>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => handleSendCommand("/tc start")}
                        disabled={!connected}
                        className="btn btn-ghost border border-[var(--border-subtle)] flex items-center gap-1.5 py-1.5 px-3 text-xs hover:bg-[rgba(251,191,36,0.1)] hover:text-[var(--accent-warning)]"
                      >
                        <Cookie size={12} /> Iniciar TC
                      </button>
                      <button
                        type="button"
                        onClick={() => handleSendCommand("/tc stop")}
                        disabled={!connected}
                        className="btn btn-ghost border border-[var(--border-subtle)] flex items-center gap-1.5 py-1.5 px-3 text-xs hover:bg-[rgba(239,68,68,0.1)] hover:text-[var(--accent-danger)]"
                      >
                        <ShieldAlert size={12} /> Parar TC
                      </button>
                    </div>
                  </div>

                  <div>
                    <span className="text-[10px] uppercase tracking-wider font-semibold opacity-60 block mb-2">Cassino (Gambling)</span>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => handleSendCommand("/g start")}
                        disabled={!connected}
                        className="btn btn-ghost border border-[var(--border-subtle)] flex items-center gap-1.5 py-1.5 px-3 text-xs hover:bg-[rgba(167,139,250,0.1)] hover:text-[var(--accent-primary)]"
                      >
                        <Sparkles size={12} fill="currentColor" /> Iniciar Apostas
                      </button>
                      <button
                        type="button"
                        onClick={() => handleSendCommand("/g pause")}
                        disabled={!connected}
                        className="btn btn-ghost border border-[var(--border-subtle)] flex items-center gap-1.5 py-1.5 px-3 text-xs hover:bg-[rgba(239,68,68,0.1)] hover:text-[var(--accent-danger)]"
                      >
                        <Pause size={12} /> Pausar Apostas
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </GlassCard>
        </div>

        {/* Right column */}
        <div className="space-y-4">
          {/* Counters Grid */}
          <GlassCard title="Contadores da Sessão">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {counters.map((c) => (
                <AnimatedCounter key={c.label} value={c.value} label={c.label} color={c.color} />
              ))}
            </div>
          </GlassCard>

          {/* Queue Card */}
          <GlassCard title="Fila (Queue)">
            <div className="space-y-3">
              <QueueBar label="HPQ" value={hpqSize} color="var(--accent-cyan)" />
              <QueueBar label="LPQ" value={lpqSize} color="var(--accent-primary)" />
            </div>
          </GlassCard>

          {/* Recent Drops */}
          <GlassCard title="Drops Recentes" subtitle="Top 10 drops desta sessão">
            <DropsList loot={sessionStats?.loot} />
          </GlassCard>
        </div>
      </div>

      {/* Mini Terminal */}
      <MiniTerminal lines={terminalLines} onNavigateTerminal={onNavigateTerminal} />
    </div>
  );
}

function DropsList({ loot }) {
  if (!loot) {
    return (
      <div
        className="h-[142px] overflow-y-auto rounded-xl p-3"
        style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-subtle)" }}
      >
        <p className="text-xs" style={{ color: "var(--text-dim)" }}>
          Nenhum drop registrado ainda. Inicie o bot para coletar drops.
        </p>
      </div>
    );
  }

  // Extract all non-zero drops from the loot categories
  const allDrops = [];
  const categories = ["mob_drops", "lootbox_drops", "work_drops", "farm_drops"];
  
  categories.forEach((cat) => {
    const items = loot[cat] || {};
    Object.entries(items).forEach(([name, count]) => {
      if (Number(count) > 0) {
        allDrops.push({ name, count: Number(count), category: cat });
      }
    });
  });

  // Sort by count descending
  allDrops.sort((a, b) => b.count - a.count);

  if (allDrops.length === 0) {
    return (
      <div
        className="h-[142px] overflow-y-auto rounded-xl p-3"
        style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-subtle)" }}
      >
        <p className="text-xs" style={{ color: "var(--text-dim)" }}>
          Nenhum drop registrado ainda. Inicie o bot para coletar drops.
        </p>
      </div>
    );
  }

  return (
    <div
      className="h-[142px] overflow-y-auto rounded-xl p-3 space-y-2"
      style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-subtle)" }}
    >
      {allDrops.slice(0, 10).map((drop, idx) => {
        const catLabel = drop.category.replace("_drops", "");
        return (
          <div key={idx} className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span 
                className="rounded-md px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide opacity-80"
                style={{
                  background: 
                    drop.category === "mob_drops" ? "rgba(248, 113, 113, 0.15)" :
                    drop.category === "lootbox_drops" ? "rgba(167, 139, 250, 0.15)" :
                    drop.category === "work_drops" ? "rgba(96, 165, 250, 0.15)" :
                    "rgba(52, 211, 153, 0.15)",
                  color: 
                    drop.category === "mob_drops" ? "var(--accent-danger)" :
                    drop.category === "lootbox_drops" ? "var(--accent-primary)" :
                    drop.category === "work_drops" ? "var(--accent-cyan)" :
                    "var(--accent-success)"
                }}
              >
                {catLabel}
              </span>
              <span style={{ color: "var(--text-primary)" }}>{drop.name}</span>
            </div>
            <span className="font-semibold tabular-nums" style={{ color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
              +{drop.count}
            </span>
          </div>
        );
      })}
    </div>
  );
}
