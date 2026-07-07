import { useCallback, useEffect, useRef, useState } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import { CanvasAddon } from "@xterm/addon-canvas";
import "@xterm/xterm/css/xterm.css";
import { useOracleStore } from "../stores/useOracleStore";
import { Maximize2, Minimize2, Trash2, Play, Pause, RefreshCw, Cookie, ShieldAlert, Sparkles } from "lucide-react";

const TERMINAL_THEME = {
  background: "#06060a",
  foreground: "#f0f0f5",
  cursor: "#06b6d4",
  cursorAccent: "#06060a",
  selectionBackground: "rgba(6, 182, 212, 0.25)",
  black: "#06060a",
  red: "#f87171",
  green: "#34d399",
  yellow: "#fbbf24",
  blue: "#60a5fa",
  magenta: "#a78bfa",
  cyan: "#06b6d4",
  white: "#f0f0f5",
  brightBlack: "#475569",
  brightRed: "#fca5a5",
  brightGreen: "#6ee7b7",
  brightYellow: "#fde68a",
  brightBlue: "#93c5fd",
  brightMagenta: "#c4b5fd",
  brightCyan: "#67e8f9",
  brightWhite: "#f8fafc",
};

export default function TerminalTab({ isActive }) {
  const containerRef = useRef(null);
  const termRef = useRef(null);
  const fitAddonRef = useRef(null);

  const activeProfile = useOracleStore((s) => s.activeProfile);
  const connected = useOracleStore((s) => s.terminalConnected);
  const lastBinaryChunk = useOracleStore((s) => s.lastBinaryChunk);
  const terminalResetKey = useOracleStore((s) => s.terminalResetKey);

  const [fullscreen, setFullscreen] = useState(false);

  // ── Fit helper ──────────────────────────────────────────────────────────
  const fitTerminal = useCallback(() => {
    if (fitAddonRef.current && termRef.current) {
      try {
        fitAddonRef.current.fit();
        const { cols, rows } = termRef.current;
        useOracleStore.getState().resizeTerminal(cols, rows);
      } catch {
        // container not visible yet
      }
    }
  }, []);

  // ── ResizeObserver for container dimension changes ──────────────────────
  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(() => {
      requestAnimationFrame(fitTerminal);
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, [fitTerminal]);

  // ── Re-fit when websocket connects ─────────────────────────────────────
  useEffect(() => {
    if (connected) {
      fitTerminal();
    }
  }, [connected, fitTerminal]);

  // ── Lazy-init flag: only create xterm after the tab has been opened once
  const [hasOpened, setHasOpened] = useState(false);
  if (isActive && !hasOpened) {
    setHasOpened(true);
  }

  // ── Re-fit + refresh when the tab becomes visible ─────────────────────
  useEffect(() => {
    if (!isActive) return;
    const timer = setTimeout(() => {
      fitTerminal();
      // Force the renderer to repaint after display:none culling
      if (termRef.current) {
        termRef.current.refresh(0, termRef.current.rows - 1);
      }
    }, 250); // Matches the 250ms tab transition animation duration
    return () => clearTimeout(timer);
  }, [isActive, fitTerminal]);

  // ── Wait for web fonts to load to prevent xterm.js character measuring race condition ──
  useEffect(() => {
    if (!document.fonts) return;
    document.fonts.ready.then(() => {
      if (termRef.current) {
        // Re-assigning option forces xterm.js to re-measure character dimensions
        termRef.current.options.fontFamily = termRef.current.options.fontFamily;
        fitTerminal();
      }
    });
  }, [fitTerminal]);

  // ── Create xterm instance (once) ───────────────────────────────────────
  useEffect(() => {
    if (!hasOpened || !containerRef.current || termRef.current) return;

    const term = new Terminal({
      scrollback: 5000,
      theme: TERMINAL_THEME,
      fontFamily: 'var(--font-mono), "Cascadia Code", "Fira Code", "SF Mono", monospace',
      fontSize: 13,
      lineHeight: 1.3,
      cursorBlink: true,
      cursorStyle: "bar",
      allowProposedApi: true,
    });

    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();

    term.loadAddon(fitAddon);
    term.loadAddon(webLinksAddon);
    term.open(containerRef.current);

    try {
      const canvasAddon = new CanvasAddon();
      term.loadAddon(canvasAddon);
    } catch (e) {
      console.warn("CanvasAddon failed to load, falling back to DOM renderer:", e);
    }

    termRef.current = term;
    fitAddonRef.current = fitAddon;



    // Replay historical binary chunks once during initialization
    const history = useOracleStore.getState().binaryHistory;
    history.forEach((chunk) => term.write(chunk));

    // Force alternate screen buffer and mouse reporting modes if already connected
    if (useOracleStore.getState().terminalConnected) {
      term.write("\x1b[?1049h\x1b[?1000h\x1b[?1002h\x1b[?1003h\x1b[?1006h");
    }

    // Forward user keystrokes to WebSocket
    const onDataDisposable = term.onData((data) => {
      useOracleStore.getState().sendTerminalBinary(data);
    });

    return () => {
      onDataDisposable.dispose();
      term.dispose();
      termRef.current = null;
      fitAddonRef.current = null;
    };
  }, [hasOpened]);

  // ── Clear terminal buffer on profile switch (store-driven) ─────────────
  const lastResetKeyRef = useRef(terminalResetKey);
  const pendingClearRef = useRef(false);

  useEffect(() => {
    if (lastResetKeyRef.current === terminalResetKey) return;
    lastResetKeyRef.current = terminalResetKey;

    if (!termRef.current) {
      pendingClearRef.current = true;
      return;
    }

    termRef.current.write("\x1b[2J\x1b[3J\x1b[H");
    termRef.current.clear();
  }, [terminalResetKey]);

  // Apply deferred clear when the tab becomes visible
  useEffect(() => {
    if (isActive && pendingClearRef.current && termRef.current) {
      pendingClearRef.current = false;
      termRef.current.write("\x1b[2J\x1b[3J\x1b[H");
      termRef.current.clear();
    }
  }, [isActive]);

  // ── Append new binary chunks from WebSocket ────────────────────────────
  useEffect(() => {
    if (lastBinaryChunk && termRef.current) {
      termRef.current.write(lastBinaryChunk);
    }
  }, [lastBinaryChunk]);

  // ── Sync terminal modes on connection state changes ─────────────────────
  useEffect(() => {
    if (!termRef.current) return;
    if (connected) {
      termRef.current.write("\x1b[?1049h\x1b[?1000h\x1b[?1002h\x1b[?1003h\x1b[?1006h");
    } else {
      termRef.current.write("\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l\x1b[?1049l\x1b[?25h");
    }
  }, [connected]);

  // ── No manual wheel event interception ─────────────────────────────────
  // Using Canvas renderer handles scroll naturally.

  // ── Fullscreen helpers ─────────────────────────────────────────────────
  const toggleFullscreen = () => {
    setFullscreen((v) => {
      setTimeout(fitTerminal, 60);
      return !v;
    });
  };

  // Auto-exit fullscreen when navigating away from the terminal tab
  if (!isActive && fullscreen) {
    setFullscreen(false);
  }

  // ── Actions ────────────────────────────────────────────────────────────
  const handleClear = () => {
    if (termRef.current) termRef.current.clear();
  };

  const handleQuickCommand = useCallback(
    (cmd) => {
      if (connected) {
        useOracleStore.getState().sendTerminalBinary(cmd + "\r");
      }
    },
    [connected]
  );

  return (
    <div
      className={`flex-1 flex flex-col min-h-0 ${
        fullscreen ? "fixed inset-0 z-50 bg-[var(--bg-void)] p-4" : ""
      }`}
    >
      {/* Toolbar */}
      <div className="glass flex items-center justify-between rounded-2xl px-4 py-2">
        <div className="flex items-center gap-3">
          <span
            className="h-2 w-2 rounded-full animate-pulse"
            style={{
              background: connected ? "var(--accent-success)" : "var(--accent-danger)",
              boxShadow: connected
                ? "0 0 8px var(--accent-success)"
                : "0 0 8px var(--accent-danger)",
            }}
          />
          <span className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
            {connected ? "Conectado" : "Desconectado"}
          </span>
          <span className="text-[10px]" style={{ color: "var(--text-dim)" }}>
            {activeProfile}
          </span>
        </div>

        {connected && (
          <div className="hidden lg:flex items-center gap-1 bg-[rgba(0,0,0,0.2)] px-3 py-1 rounded-full border border-[var(--border-subtle)]">
            <button
              type="button"
              onClick={() => handleQuickCommand("/resume")}
              className="btn btn-ghost px-2 py-0.5 text-[10px] h-auto flex items-center gap-1 text-[var(--text-secondary)] hover:text-[var(--accent-success)]"
              title="Retomar Bot"
            >
              <Play size={10} /> Retomar
            </button>
            <button
              type="button"
              onClick={() => handleQuickCommand("/pause")}
              className="btn btn-ghost px-2 py-0.5 text-[10px] h-auto flex items-center gap-1 text-[var(--text-secondary)] hover:text-[var(--accent-danger)]"
              title="Pausar Bot"
            >
              <Pause size={10} /> Pausar
            </button>
            <button
              type="button"
              onClick={() => handleQuickCommand("/reset")}
              className="btn btn-ghost px-2 py-0.5 text-[10px] h-auto flex items-center gap-1 text-[var(--text-secondary)] hover:text-[var(--accent-cyan)]"
              title="Resetar estado e filas"
            >
              <RefreshCw size={10} /> Resetar
            </button>
            <span className="h-3.5 w-px bg-[var(--border-subtle)] mx-1" />
            <button
              type="button"
              onClick={() => handleQuickCommand("/tc start")}
              className="btn btn-ghost px-2 py-0.5 text-[10px] h-auto flex items-center gap-1 text-[var(--text-secondary)] hover:text-[var(--accent-warning)]"
              title="Iniciar Time Cookie"
            >
              <Cookie size={10} /> Iniciar TC
            </button>
            <button
              type="button"
              onClick={() => handleQuickCommand("/tc stop")}
              className="btn btn-ghost px-2 py-0.5 text-[10px] h-auto flex items-center gap-1 text-[var(--text-secondary)] hover:text-[var(--accent-danger)]"
              title="Parar Time Cookie"
            >
              <ShieldAlert size={10} /> Parar TC
            </button>
            <span className="h-3.5 w-px bg-[var(--border-subtle)] mx-1" />
            <button
              type="button"
              onClick={() => handleQuickCommand("/g start")}
              className="btn btn-ghost px-2 py-0.5 text-[10px] h-auto flex items-center gap-1 text-[var(--text-secondary)] hover:text-[var(--accent-primary)]"
              title="Iniciar Apostas"
            >
              <Sparkles size={10} /> Iniciar Apostas
            </button>
            <button
              type="button"
              onClick={() => handleQuickCommand("/g pause")}
              className="btn btn-ghost px-2 py-0.5 text-[10px] h-auto flex items-center gap-1 text-[var(--text-secondary)] hover:text-[var(--accent-danger)]"
              title="Pausar Apostas"
            >
              <Pause size={10} /> Pausar Apostas
            </button>
          </div>
        )}

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={handleClear}
            className="btn btn-ghost p-2"
            title="Limpar terminal"
          >
            <Trash2 size={14} />
          </button>
          <button
            type="button"
            onClick={toggleFullscreen}
            className="btn btn-ghost p-2"
            title={fullscreen ? "Sair da tela cheia" : "Tela cheia"}
          >
            {fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
        </div>
      </div>

      {/* Terminal container */}
      <div
        ref={containerRef}
        className="mt-3 flex-1 min-h-0 overflow-hidden rounded-xl"
        style={{
          background: "var(--bg-void)",
          border: "1px solid var(--border-subtle)",
        }}
      />
    </div>
  );
}
