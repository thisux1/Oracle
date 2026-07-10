const STATUS_STYLES = {
  offline: {
    label: "Offline",
    dot: "bg-slate-500",
    dotGlow: "",
    bg: "rgba(100, 116, 139, 0.12)",
    color: "#94a3b8",
    border: "rgba(148, 163, 184, 0.2)",
  },
  starting: {
    label: "Iniciando",
    dot: "bg-amber-400",
    dotGlow: "",
    bg: "var(--accent-warning-dim)",
    color: "var(--accent-warning)",
    border: "var(--border-glow-warning)",
  },
  online: {
    label: "Online",
    dot: "bg-cyan-400",
    dotGlow: "animate-oracle-pulse",
    bg: "var(--accent-cyan-dim)",
    color: "var(--accent-cyan)",
    border: "var(--border-glow-cyan)",
  },
  stopping: {
    label: "Parando",
    dot: "bg-rose-400",
    dotGlow: "",
    bg: "var(--accent-danger-dim)",
    color: "var(--accent-danger)",
    border: "var(--border-glow-danger)",
  },
};

export default function StatusBadge({ state = "offline", size = "sm" }) {
  const style = STATUS_STYLES[state] || STATUS_STYLES.offline;

  const sizes = {
    xs: "px-2 py-0.5 text-[10px]",
    sm: "px-2.5 py-1 text-xs",
    md: "px-3 py-1.5 text-sm",
  };

  const dotSizes = {
    xs: "h-1.5 w-1.5",
    sm: "h-2 w-2",
    md: "h-2.5 w-2.5",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold uppercase tracking-wide ${sizes[size]}`}
      style={{
        background: style.bg,
        color: style.color,
        border: `1px solid ${style.border}`,
      }}
    >
      <span className="relative flex">
        <span
          className={`${dotSizes[size]} rounded-full ${style.dot} ${style.dotGlow}`}
        />
        {state === "online" ? (
          <span
            className={`absolute inset-0 rounded-full ${style.dot} opacity-40 ${style.dotGlow}`}
          />
        ) : null}
      </span>
      {style.label}
    </span>
  );
}
