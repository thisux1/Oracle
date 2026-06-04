"""Oracle Dashboard - Desktop launcher.

Starts the FastAPI backend (uvicorn) in a daemon thread, mounts the built
frontend, and opens the dashboard in a native window (pywebview) or the
default browser as fallback.
"""

from __future__ import annotations

import atexit
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DIST_DIR = ROOT_DIR / "dashboard" / "dist"

HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}"


def _start_server() -> None:
    """Run uvicorn in a background daemon thread."""
    import uvicorn

    config = uvicorn.Config(
        "dashboard_server:app",
        host=HOST,
        port=PORT,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True, name="oracle-uvicorn")
    thread.start()

    # Wait until the server is accepting connections
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if server.started:
            break
        time.sleep(0.1)

    if not server.started:
        print(f"[oracle] ERROR: server did not start within 10s on {URL}")
        sys.exit(1)

    return thread


def _open_native_window(url: str) -> bool:
    """Try to open a native webview window. Returns True on success."""
    try:
        import webview

        window = webview.create_window(
            "Oracle OS",
            url,
            width=1280,
            height=800,
            min_size=(960, 600),
        )

        atexit.register(lambda: window.destroy() if window and window._is_loaded else None)
        webview.start(debug=False)
        return True
    except ImportError:
        return False
    except Exception:
        return False


def _open_browser(url: str) -> None:
    """Open the dashboard in the default browser."""
    webbrowser.open(url)


def main() -> None:
    print(f"[oracle] Starting Oracle Dashboard on {URL}")

    if not DIST_DIR.exists():
        print(f"[oracle] WARNING: dist directory not found at {DIST_DIR}")
        print("[oracle] Run 'cd dashboard && npm run build' first.")
        print("[oracle] Starting in dev mode (frontend served by Vite)...")

    _start_server()
    print(f"[oracle] Backend ready at {URL}")

    # Try native window first, fallback to browser
    opened_native = _open_native_window(URL)
    if opened_native:
        print("[oracle] Running in native window.")
    else:
        print("[oracle] Opening in default browser...")
        _open_browser(URL)

    print("[oracle] Dashboard is running. Close the window or press Ctrl+C to stop.")

    # Keep main thread alive so daemon thread keeps running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[oracle] Shutting down...")


if __name__ == "__main__":
    main()
