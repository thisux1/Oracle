import { useMemo } from "react";
import { Sun, Waves, Coffee, Package, Zap, CheckCircle, Clock } from "lucide-react";
import { useOracleStore } from "../stores/useOracleStore";

function formatDuration(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h}h ${m.toString().padStart(2, "0")}m ${sec.toString().padStart(2, "0")}s`;
  if (m > 0) return `${m}m ${sec.toString().padStart(2, "0")}s`;
  return `${sec}s`;
}

const DRINK_INFO = {
  blue: { color: "#3b82f6", label: "Blue Drink", emoji: "\u{1F535}" },
  pink: { color: "#ec4899", label: "Pink Drink", emoji: "\u{1F534}" },
  green: { color: "#22c55e", label: "Green Drink", emoji: "\u{1F7E2}" },
  yellow: { color: "#eab308", label: "Yellow Drink", emoji: "\u{1F7E1}" },
};

const INVENTORY_ITEMS = [
  { key: "coconut", label: "Coconut", emoji: "\u{1F965}" },
  { key: "chopped_coconut", label: "Chopped", emoji: "\u{1F964}" },
  { key: "palm_log", label: "Palm Log", emoji: "\u{1FAB5}" },
  { key: "mega_palm_log", label: "Mega Log", emoji: "\u{1FAB5}" },
  { key: "normiefish", label: "Fish", emoji: "\u{1F41F}" },
  { key: "epic_fish", label: "Epic Fish", emoji: "\u{1F420}" },
  { key: "banana", label: "Banana", emoji: "\u{1F34C}" },
  { key: "ruby", label: "Ruby", emoji: "\u{1F48E}" },
  { key: "mermaid_hair", label: "Mermaid", emoji: "\u{1F9DA}" },
  { key: "lottery_ticket", label: "Lottery", emoji: "\u{1F3AB}" },
  { key: "chip", label: "Chip", emoji: "\u{1F4BF}" },
  { key: "epic_seed", label: "Epic Seed", emoji: "\u{1F331}" },
  { key: "edgy_lootbox", label: "Lootbox", emoji: "\u{1F4E6}" },
];

function CooldownBar({ label, remaining, maxSeconds = 1800 }) {
  const pct = maxSeconds > 0 ? Math.min(100, ((maxSeconds - remaining) / maxSeconds) * 100) : 100;
  const ready = remaining <= 0;
  return (
    <div className="rounded-xl p-3" style={{ background: "var(--bg-card)" }}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>{label}</span>
        <span className="text-xs font-mono" style={{ color: ready ? "#22c55e" : "var(--accent-primary)" }}>
          {ready ? "READY" : formatDuration(remaining)}
        </span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "var(--bg-void)" }}>
        <div
          className="h-full rounded-full transition-[width] duration-1000"
          style={{
            width: `${pct}%`,
            background: ready ? "#22c55e" : "var(--accent-primary)",
          }}
        />
      </div>
    </div>
  );
}

function DrinkCard({ drinkKey, count, chosen }) {
  const info = DRINK_INFO[drinkKey];
  if (!info) return null;
  const isChosen = drinkKey === chosen;
  return (
    <div
      className="rounded-xl p-3 text-center transition-all"
      style={{
        background: isChosen ? `${info.color}15` : "var(--bg-card)",
        border: isChosen ? `1px solid ${info.color}40` : "1px solid transparent",
      }}
    >
      <div className="text-2xl mb-1">{info.emoji}</div>
      <div className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>{count}</div>
      <div className="text-[10px]" style={{ color: "var(--text-secondary)" }}>{info.label}</div>
      {isChosen && (
        <div className="mt-1 text-[10px] font-medium" style={{ color: info.color }}>SELECTED</div>
      )}
    </div>
  );
}

function TaskItem({ task, claimed }) {
  return (
    <div className="flex items-center gap-2 py-1.5">
      {claimed ? (
        <CheckCircle size={14} style={{ color: "#22c55e" }} />
      ) : (
        <Clock size={14} style={{ color: "var(--text-secondary)" }} />
      )}
      <span
        className="text-xs"
        style={{
          color: claimed ? "var(--text-secondary)" : "var(--text-primary)",
          textDecoration: claimed ? "line-through" : "none",
        }}
      >
        {task}
      </span>
    </div>
  );
}

export default function SummerTab() {
  const summerData = useOracleStore((s) => s.summerData);

  const allTasks = useMemo(() => {
    if (!summerData) return [];
    const claimed = new Set(summerData.tasks_claimed || []);
    const pending = summerData.pending_tasks || [];
    return [
      ...pending.map((t) => ({ name: t, claimed: claimed.has(t) })),
      ...[...claimed].filter((t) => !pending.includes(t)).map((t) => ({ name: t, claimed: true })),
    ];
  }, [summerData]);

  if (!summerData || !summerData.active) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4 opacity-60">
        <Sun size={48} style={{ color: "var(--text-secondary)" }} />
        <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
          Summer event is not active
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Hero Status */}
      <div
        className="rounded-2xl p-5"
        style={{
          background: "linear-gradient(135deg, rgba(245,158,11,0.1) 0%, rgba(234,179,8,0.05) 100%)",
          border: "1px solid rgba(245,158,11,0.2)",
        }}
      >
        <div className="flex items-center gap-3 mb-3">
          <Sun size={24} style={{ color: "#f59e0b" }} />
          <h2 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>Summer Event</h2>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
          <div>
            <div className="text-[10px] uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>Team</div>
            <div className="font-medium mt-0.5" style={{ color: "var(--text-primary)" }}>
              {summerData.color_team || "None"}
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>Strategy</div>
            <div className="font-medium mt-0.5" style={{ color: "var(--text-primary)" }}>
              {summerData.strategy || "conservative"}
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>Surf Rounds</div>
            <div className="font-medium mt-0.5" style={{ color: "var(--text-primary)" }}>
              {summerData.surf_rounds || 0}
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>Boosts</div>
            <div className="font-medium mt-0.5" style={{ color: "var(--text-primary)" }}>
              {summerData.boost_count || 0} active
            </div>
          </div>
        </div>
      </div>

      {/* Cooldowns */}
      <div>
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
          <Waves size={16} /> Cooldowns
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <CooldownBar label="Surf" remaining={summerData.surf_cooldown_remaining || 0} />
          <CooldownBar
            label="Beach Party"
            remaining={summerData.beach_party_active ? 0 : 3600}
            maxSeconds={3600}
          />
        </div>
        {/* Boost bars */}
        {summerData.boosts_active && Object.keys(summerData.boosts_active).length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
            {Object.entries(summerData.boosts_active).map(([name, expiresAt]) => {
              const remaining = Math.max(0, expiresAt - Date.now() / 1000);
              return <CooldownBar key={name} label={name} remaining={remaining} maxSeconds={1800} />;
            })}
          </div>
        )}
      </div>

      {/* Tasks & Quest */}
      <div>
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
          <CheckCircle size={16} /> Tasks & Quest
        </h3>
        <div className="rounded-xl p-3" style={{ background: "var(--bg-card)" }}>
          {allTasks.length === 0 ? (
            <p className="text-xs" style={{ color: "var(--text-secondary)" }}>No tasks available</p>
          ) : (
            allTasks.map((t, i) => <TaskItem key={i} task={t.name} claimed={t.claimed} />)
          )}
          <div className="mt-2 pt-2 flex items-center gap-2" style={{ borderTop: "1px solid var(--border-subtle)" }}>
            <span className="text-[10px] uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>Quest</span>
            <span className="text-xs font-medium" style={{ color: summerData.quest_completed ? "#22c55e" : "var(--text-primary)" }}>
              {summerData.quest_completed ? "Completed" : "Pending"}
            </span>
          </div>
        </div>
      </div>

      {/* Drinks */}
      <div>
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
          <Coffee size={16} /> Drink Crafting
        </h3>
        <div className="grid grid-cols-4 gap-2">
          {Object.entries(DRINK_INFO).map(([key]) => (
            <DrinkCard
              key={key}
              drinkKey={key}
              count={summerData.drinks?.[key] ?? 0}
              chosen={summerData.drink_choice}
            />
          ))}
        </div>
        <div className="mt-2 text-[10px]" style={{ color: "var(--text-secondary)" }}>
          {summerData.drink_this_week ? "Weekly drink already used" : "Weekly drink available"}
        </div>
      </div>

      {/* Inventory */}
      <div>
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
          <Package size={16} /> Inventory
        </h3>
        <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-7 gap-2">
          {INVENTORY_ITEMS.map(({ key, label, emoji }) => {
            const count = summerData.inventory?.[key] ?? 0;
            return (
              <div
                key={key}
                className="rounded-xl p-2 text-center"
                style={{ background: "var(--bg-card)" }}
              >
                <div className="text-lg">{emoji}</div>
                <div className="text-[10px] font-medium" style={{ color: count > 0 ? "var(--text-primary)" : "var(--text-secondary)" }}>
                  {count}
                </div>
                <div className="text-[9px]" style={{ color: "var(--text-secondary)" }}>{label}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
