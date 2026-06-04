"""Oracle Dashboard - Desktop launcher.

Starts the FastAPI backend (uvicorn) in a daemon thread, mounts the built
frontend, and opens the dashboard in a native window (pywebview) or the
default browser as fallback.
"""

from __future__ import annotations

import atexit
import os
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging setup — MUST happen before any other import.
# PyInstaller --windowed suppresses stdout/stderr; redirect them to a log file
# in AppData so tracebacks are always recoverable.
# ---------------------------------------------------------------------------

def _setup_logging() -> None:
    app_data = os.environ.get("LOCALAPPDATA")
    if app_data:
        log_dir = Path(app_data) / "OracleOS"
    else:
        log_dir = Path(tempfile.gettempdir()) / "OracleOS"

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "launcher.log"
        log_stream = open(log_file, "w", encoding="utf-8", buffering=1)
        sys.stdout = log_stream
        sys.stderr = log_stream
        print("--- Oracle OS Launcher Start ---")
        print(f"Python: {sys.version}")
        print(f"Platform: {sys.platform}")
        print(f"Executable: {sys.executable}")
    except Exception:
        # Last resort: discard output rather than crash
        devnull = open(os.devnull, "w")
        if sys.stdout is None:
            sys.stdout = devnull
        if sys.stderr is None:
            sys.stderr = devnull


_setup_logging()

# ---------------------------------------------------------------------------
# --run-bot mode: when the frozen bundle is invoked as a bot subprocess by
# the dashboard server, skip the whole server/UI stack and just run the TUI.
# This must happen BEFORE any heavy imports so it's fast.
# ---------------------------------------------------------------------------
if "--run-bot" in sys.argv:
    # Remove the flag so the TUI doesn't see it
    sys.argv.remove("--run-bot")
    try:
        from bot.tui import OracleApp  # noqa: E402
        OracleApp().run()
    except Exception:
        import traceback as _tb
        _tb.print_exc()
    sys.exit(0)

# ---------------------------------------------------------------------------
# Resolve paths — works both in development and in a frozen PyInstaller bundle.
# sys._MEIPASS is set by PyInstaller to the temp extraction directory.
# ---------------------------------------------------------------------------

import socket

import threading
import time
import traceback
import webbrowser

# BUNDLE_DIR: where all packaged files live (in frozen mode, this is _MEIPASS)
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))

# ROOT_DIR: the script's own directory (same as BUNDLE_DIR when frozen)
ROOT_DIR = Path(__file__).resolve().parent if not getattr(sys, "frozen", False) else BUNDLE_DIR

DIST_DIR = BUNDLE_DIR / "dashboard" / "dist"

# ---------------------------------------------------------------------------
# Import dashboard_server early so any ImportError shows a full traceback.
# ---------------------------------------------------------------------------

try:
    import dashboard_server  # noqa: F401  (imported for side-effects / early validation)
    from dashboard_server import app as _asgi_app
except Exception:
    print("\n[CRITICAL ERROR DURING IMPORT OF DASHBOARD_SERVER]:")
    traceback.print_exc()
    sys.exit(1)

# ---------------------------------------------------------------------------
# Port discovery
# ---------------------------------------------------------------------------

HOST = "127.0.0.1"


def _find_free_port(host: str, start: int = 8000) -> int:
    """Return the first free TCP port starting from *start*."""
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    return start  # fallback — unlikely but safe


PORT = _find_free_port(HOST, 8000)
URL = f"http://{HOST}:{PORT}"

# ---------------------------------------------------------------------------
# Backend server
# ---------------------------------------------------------------------------


def _start_server() -> None:
    """Run uvicorn in a background daemon thread."""
    import uvicorn

    # Pass the app *object* directly — avoids the "module not found" error
    # that happens when uvicorn tries to import "dashboard_server:app" by
    # string inside a frozen bundle.
    config = uvicorn.Config(
        _asgi_app,
        host=HOST,
        port=PORT,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True, name="oracle-uvicorn")
    thread.start()

    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if server.started:
            break
        time.sleep(0.1)

    if not server.started:
        print(f"[oracle] ERROR: server did not start within 15s on {URL}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Window / browser helpers
# ---------------------------------------------------------------------------

def _open_browser(url: str) -> None:
    """Open the dashboard in the system default browser."""
    # Small delay so the server is fully ready before the browser hits it
    time.sleep(0.5)
    webbrowser.open(url)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    print(f"[oracle] Starting Oracle Dashboard on {URL}")

    if not DIST_DIR.exists():
        print(f"[oracle] WARNING: dist directory not found at {DIST_DIR}")
        print("[oracle] Run 'cd dashboard && npm run build' first.")

    _start_server()
    print(f"[oracle] Backend ready at {URL}")

    print("[oracle] Opening in default browser...")
    _open_browser(URL)
    print("[oracle] Dashboard is running. Close this console window or press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[oracle] Shutting down...")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("\n[CRITICAL ERROR DURING LAUNCHER STARTUP]:")
        traceback.print_exc()
        sys.exit(1)
