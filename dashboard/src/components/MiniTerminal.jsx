import { Terminal } from "lucide-react";

export default function MiniTerminal({ lines = [], onNavigateTerminal }) {
  const display = lines.slice(-5);

  return (
    <div
      className="glass cursor-pointer rounded-2xl p-4 transition-colors duration-150 hover:border-[var(--border-glow-cyan)]"
      onClick={onNavigateTerminal}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onNavigateTerminal();
      }}
    >
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal size={14} style={{ color: "var(--accent-cyan)" }} />
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--text-dim)" }}>
            Mini Terminal
          </p>
        </div>
        <span className="text-[10px]" style={{ color: "var(--text-dim)" }}>
          click to open
        </span>
      </div>
      <div
        className="max-h-28 overflow-y-auto rounded-lg p-2"
        style={{ background: "var(--bg-void)", fontFamily: "var(--font-mono)" }}
      >
        {display.length === 0 ? (
          <p className="text-xs" style={{ color: "var(--text-dim)" }}>No log output yet.</p>
        ) : (
          display.map((line, i) => {
            const match = line.match(/^\[\d{4}-\d{2}-\d{2} (\d{2}:\d{2}:\d{2})\] (.*)$/);
            const timeStr = match ? `[${match[1]}]` : ">";
            const content = match ? match[2] : line;
            return (
              <p key={i} className="text-[11px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                <span className="mr-1 select-none" style={{ color: "var(--text-dim)" }}>{timeStr}</span>
                {content}
              </p>
            );
          })
        )}
      </div>
    </div>
  );
}
