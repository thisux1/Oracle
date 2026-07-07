from __future__ import annotations

import asyncio
import errno
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import options_resolver

if os.name != "nt":
    import fcntl
    import pty
    import struct
    import termios
else:
    fcntl = None
    pty = None
    struct = None
    termios = None

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_PROFILE = options_resolver.DEFAULT_PROFILE

try:
    import winpty  # type: ignore
except Exception:
    winpty = None


class BotState(str, Enum):
    OFFLINE = "offline"
    STARTING = "starting"
    ONLINE = "online"
    STOPPING = "stopping"


class ConfigUpdatePayload(BaseModel):
    profile: str = Field(default=DEFAULT_PROFILE)
    settings: dict[str, Any]


class BotControlPayload(BaseModel):
    profile: str = Field(default=DEFAULT_PROFILE)


class ProfileCreatePayload(BaseModel):
    name: str
    copyFrom: str | None = None


def api_error(status_code: int, code: str, message: str, details: dict[str, Any] | None = None) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
            "details": details or {},
        },
    )


def normalize_and_validate_profile(profile: str | None) -> str:
    normalized = options_resolver.normalize_profile_name(profile)
    try:
        options_resolver.resolve_profile_path(
            profile=normalized,
            base_dir=options_resolver.USER_DATA_DIR,
            ensure_exists=True,
        )
    except FileNotFoundError:
        api_error(404, "profile_not_found", "Profile file was not found", {"profile": normalized})
    except ValueError:
        api_error(400, "invalid_profile", "Profile must point to a local .ini file", {"profile": normalized})
    return normalized


def mask_config(config: dict[str, Any]) -> dict[str, Any]:
    masked = dict(config)
    for token_key in ("user_token", "miner_token", "telegram_bot_token"):
        if token_key in masked and masked[token_key]:
            masked[token_key] = "********"
    return masked


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _load_json_file(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            parsed = json.load(handle)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return None


def _load_stats_for_profile(profile: str) -> dict[str, Any] | None:
    profile_stem = Path(profile).stem
    user_data_path = Path(options_resolver.USER_DATA_DIR)
    candidates = [
        user_data_path / f"stats_{profile_stem}.json",
        user_data_path / "stats_totals.json",
    ]

    for candidate in candidates:
        result = _load_json_file(candidate)
        if result is not None:
            return result
    return None


def _load_baseline_for_profile(profile: str) -> dict[str, Any] | None:
    profile_stem = Path(profile).stem
    user_data_path = Path(options_resolver.USER_DATA_DIR)
    candidates = [
        user_data_path / f"session_baseline_{profile_stem}.json",
        user_data_path / "session_baseline.json",
    ]

    for candidate in candidates:
        result = _load_json_file(candidate)
        if result is not None:
            return result
    return None


def _subtract_stats(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    """Subtract baseline values from current stats to get session-only deltas."""
    result: dict[str, Any] = {}
    for key, value in current.items():
        if key == "start_time":
            result[key] = value
            continue
        if isinstance(value, dict):
            base_val = baseline.get(key, {})
            if isinstance(base_val, dict):
                result[key] = _subtract_stats(value, base_val)
            else:
                result[key] = value
        elif isinstance(value, (int, float)):
            base_num = baseline.get(key, 0)
            if isinstance(base_num, (int, float)):
                result[key] = value - base_num
            else:
                result[key] = value
        else:
            result[key] = value
    return result


def _extract_queue_sizes(stats: dict[str, Any] | None) -> tuple[int | None, int | None]:
    if not isinstance(stats, dict):
        return None, None

    hpq = _coerce_int(stats.get("hpq") or stats.get("hpqSize") or stats.get("hpq_size"))
    lpq = _coerce_int(stats.get("lpq") or stats.get("lpqSize") or stats.get("lpq_size"))

    queue_data = stats.get("queue")
    if isinstance(queue_data, dict):
        if hpq is None:
            hpq = _coerce_int(queue_data.get("hpq") or queue_data.get("hpqSize"))
        if lpq is None:
            lpq = _coerce_int(queue_data.get("lpq") or queue_data.get("lpqSize"))

    return hpq, lpq


class BotProcessManager:
    def __init__(self, profile: str):
        self.profile = options_resolver.normalize_profile_name(profile)
        self.state: BotState = BotState.OFFLINE
        self.process: subprocess.Popen[Any] | Any | None = None
        self.ws_clients: set[WebSocket] = set()
        self.started_at: float | None = None
        self.last_exit_code: int | None = None
        self.last_crash_at: float | None = None
        self.cols: int = 80
        self.rows: int = 24

        self._pty_master_fd: int | None = None
        self._pty_process: Any | None = None

        self._state_lock = asyncio.Lock()
        self._stop_output_event = threading.Event()
        self._output_thread: threading.Thread | None = None
        self._watch_task: asyncio.Task[None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def status_payload(self) -> dict[str, Any]:
        now = time.time()
        uptime = int(now - self.started_at) if self.started_at and self.state in (BotState.STARTING, BotState.ONLINE) else 0
        stats = _load_stats_for_profile(self.profile)
        hpq_size, lpq_size = _extract_queue_sizes(stats)

        return {
            "profile": self.profile,
            "state": self.state.value,
            "uptime": uptime,
            "hpq": hpq_size,
            "lpq": lpq_size,
            "lastExitCode": self.last_exit_code,
            "lastCrashAt": self.last_crash_at,
        }

    async def start(self) -> bool:
        async with self._state_lock:
            if self.state in (BotState.STARTING, BotState.ONLINE):
                return False

            options_resolver.resolve_profile_path(
                profile=self.profile,
                base_dir=options_resolver.USER_DATA_DIR,
                ensure_exists=True,
            )

            # Truncate the clean logs file for this profile
            log_path = Path(options_resolver.USER_DATA_DIR) / f"{Path(self.profile).stem}.log"
            if log_path.exists():
                try:
                    log_path.unlink()
                except Exception:
                    pass

            self.state = BotState.STARTING
            self.last_exit_code = None
            self.last_crash_at = None
            self._loop = asyncio.get_running_loop()

            try:
                if os.name == "nt":
                    self._spawn_windows()
                else:
                    self._spawn_posix()
            except Exception as exc:
                import traceback as _tb
                print(f"[oracle] ERROR spawning bot: {exc}")
                print(_tb.format_exc())
                self.state = BotState.OFFLINE
                self._cleanup_runtime()
                api_error(
                    500,
                    "start_failed",
                    "Failed to start bot process",
                    {"profile": self.profile, "reason": str(exc)},
                )

            self.started_at = time.time()
            self.state = BotState.ONLINE

            self._stop_output_event.clear()
            self._output_thread = threading.Thread(
                target=self._output_worker,
                name=f"bot-output-{self.profile}",
                daemon=True,
            )
            self._output_thread.start()

            if self._watch_task and not self._watch_task.done():
                self._watch_task.cancel()
            self._watch_task = asyncio.create_task(self._watch_process())

        await self._broadcast_json({"type": "status", "profile": self.profile, "state": self.state.value})
        return True

    async def stop(self) -> bool:
        async with self._state_lock:
            if self.state in (BotState.OFFLINE, BotState.STOPPING):
                return False

            self.state = BotState.STOPPING

            if self._watch_task and not self._watch_task.done():
                self._watch_task.cancel()
            self._watch_task = None

            exit_code = await asyncio.to_thread(self._terminate_process)
            self.last_exit_code = exit_code

            self._cleanup_runtime()
            self.state = BotState.OFFLINE

        await self._broadcast_json(
            {
                "type": "status",
                "profile": self.profile,
                "state": self.state.value,
                "reason": "stopped",
                "exitCode": self.last_exit_code,
            }
        )
        return True

    async def add_ws_client(self, ws: WebSocket) -> None:
        self.ws_clients.add(ws)

    async def remove_ws_client(self, ws: WebSocket) -> None:
        self.ws_clients.discard(ws)

    async def write_input(self, data: bytes) -> bool:
        if not data or not self._is_process_alive():
            return False

        try:
            if os.name == "nt":
                if self._pty_process is None:
                    return False
                text = data.decode("utf-8", errors="ignore")
                self._pty_process.write(text)
            else:
                if self._pty_master_fd is None:
                    return False
                os.write(self._pty_master_fd, data)
        except Exception:
            return False

        return True

    async def resize(self, cols: int, rows: int) -> bool:
        if cols <= 0 or rows <= 0:
            return False

        self.cols = cols
        self.rows = rows

        if not self._is_process_alive():
            return True

        try:
            if os.name == "nt":
                if self._pty_process is None:
                    return False
                self._pty_process.set_size(cols, rows)
            else:
                if self._pty_master_fd is None:
                    return False
                if hasattr(os, "set_terminal_size"):
                    os.set_terminal_size(self._pty_master_fd, os.terminal_size((cols, rows)))
                else:
                    winsize = struct.pack("HHHH", rows, cols, 0, 0)
                    fcntl.ioctl(self._pty_master_fd, termios.TIOCSWINSZ, winsize)

                if self.process is not None:
                    try:
                        if hasattr(self.process, "send_signal"):
                            self.process.send_signal(signal.SIGWINCH)
                    except Exception:
                        pass
                    if hasattr(self.process, "pid"):
                        try:
                            os.killpg(os.getpgid(self.process.pid), signal.SIGWINCH)
                        except Exception:
                            pass
        except Exception:
            return False

        return True

    @staticmethod
    def _build_bot_command(profile: str) -> list[str]:
        """Build the subprocess command to launch the bot.

        When running as a frozen PyInstaller bundle, sys.executable points to
        the packaged .exe itself — we re-invoke it with --run-bot so the entry
        point can start the TUI instead of the dashboard server.
        When running in normal development mode, we call main.py directly.
        """
        if getattr(sys, "frozen", False):
            # Frozen: re-invoke the bundle exe in bot mode
            return [sys.executable, "--run-bot", profile]
        # Development: invoke main.py with the current interpreter
        main_py = Path(__file__).resolve().parent / "main.py"
        return [sys.executable, str(main_py), profile]

    def _spawn_posix(self) -> None:
        master_fd, slave_fd = pty.openpty()

        # Set the terminal window size (TIOCSWINSZ) before launching the subprocess
        try:
            import fcntl
            import termios
            import struct
            winsize = struct.pack("HHHH", self.rows, self.cols, 0, 0)
            fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
        except Exception as resize_err:
            print(f"[oracle] Failed to set initial dimensions on POSIX openpty: {resize_err}")

        command = self._build_bot_command(self.profile)
        
        # Copy environment and ensure terminal capability variables are set
        import os
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["COLORTERM"] = "truecolor"

        try:
            self.process = subprocess.Popen(
                command,
                cwd=str(PROJECT_DIR),
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                start_new_session=True,
                close_fds=True,
                env=env,
            )
        finally:
            os.close(slave_fd)

        self._pty_master_fd = master_fd

    @staticmethod
    def _is_wine() -> bool:
        """Detect Wine emulation (winpty/ConPTY don't work under Wine)."""
        try:
            import ctypes
            return hasattr(ctypes.CDLL("ntdll.dll"), "wine_get_version")
        except Exception:
            return False

    def _spawn_windows_fallback(self, command: list[str]) -> None:
        """Fallback for when winpty is unavailable or fails."""
        cmd_args = list(command)
        if "--headless" not in cmd_args:
            cmd_args.append("--headless")
        self.process = subprocess.Popen(
            cmd_args,
            cwd=str(PROJECT_DIR),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        # Read stdout pipe instead of PTY fd
        self._pty_master_fd = self.process.stdout.fileno()

    def _spawn_windows(self) -> None:
        command = self._build_bot_command(self.profile)

        if self._is_wine() or winpty is None:
            self._spawn_windows_fallback(command)
            return

        command_line = subprocess.list2cmdline(command)
        try:
            self._pty_process = winpty.PtyProcess.spawn(command_line, cwd=str(PROJECT_DIR))
            self.process = self._pty_process
            # Set the initial size immediately after spawn
            try:
                self._pty_process.set_size(self.cols, self.rows)
            except Exception as resize_err:
                print(f"[oracle] Failed to set initial dimensions on Windows spawn: {resize_err}")
        except Exception as e:
            print(f"[oracle] winpty failed to spawn ({e}), falling back to plain Popen...")
            self._spawn_windows_fallback(command)

    def _read_chunk(self) -> bytes:
        if os.name == "nt":
            # winpty path (real Windows with PTY)
            if self._pty_process is not None:
                data = self._pty_process.read(4096)
                if not data:
                    return b""
                if isinstance(data, bytes):
                    return data
                return str(data).encode("utf-8", errors="replace")

            # Pipe fallback (Wine or no winpty): read from stdout pipe fd
            if self._pty_master_fd is not None:
                try:
                    return os.read(self._pty_master_fd, 4096)
                except OSError:
                    return b""
            return b""

        # POSIX path: read from PTY master fd
        if self._pty_master_fd is None:
            return b""

        try:
            return os.read(self._pty_master_fd, 4096)
        except OSError as exc:
            if exc.errno in (errno.EIO, errno.EBADF):
                return b""
            raise

    def _output_worker(self) -> None:
        while not self._stop_output_event.is_set():
            try:
                chunk = self._read_chunk()
            except Exception:
                break

            if not chunk:
                if not self._is_process_alive():
                    break
                continue

            if self._loop is None:
                continue

            future = asyncio.run_coroutine_threadsafe(self._broadcast_bytes(chunk), self._loop)
            try:
                future.result(timeout=2)
            except Exception:
                continue

    async def _watch_process(self) -> None:
        try:
            while True:
                await asyncio.sleep(0.75)
                if self._is_process_alive():
                    continue

                async with self._state_lock:
                    if self.state == BotState.STOPPING:
                        return

                    self.last_exit_code = self._read_exit_code()
                    self.last_crash_at = time.time()
                    self._cleanup_runtime()
                    self.state = BotState.OFFLINE

                await self._broadcast_json(
                    {
                        "type": "status",
                        "profile": self.profile,
                        "state": self.state.value,
                        "reason": "crashed",
                        "exitCode": self.last_exit_code,
                    }
                )
                return
        except asyncio.CancelledError:
            return

    def _is_process_alive(self) -> bool:
        try:
            if os.name == "nt" and self._pty_process is not None:
                return bool(self._pty_process.isalive())
            return bool(self.process is not None and self.process.poll() is None)
        except Exception:
            return False

    def _read_exit_code(self) -> int | None:
        if os.name == "nt" and self._pty_process is not None:
            return _coerce_int(getattr(self._pty_process, "exitstatus", None))

        if self.process is None:
            return None
        return _coerce_int(self.process.poll())

    def _terminate_process(self) -> int | None:
        if os.name == "nt" and self._pty_process is not None:
            if hasattr(self._pty_process, "isalive") and self._pty_process.isalive():
                if hasattr(self._pty_process, "terminate"):
                    self._pty_process.terminate(force=True)
                elif hasattr(self._pty_process, "kill"):
                    self._pty_process.kill()
                elif hasattr(self._pty_process, "close"):
                    self._pty_process.close(True)

            return _coerce_int(getattr(self._pty_process, "exitstatus", None))

        if self.process is None:
            return None

        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass

        return _coerce_int(self.process.poll())

    async def _broadcast_json(self, payload: dict[str, Any]) -> None:
        if not self.ws_clients:
            return

        stale_clients: list[WebSocket] = []
        for client in tuple(self.ws_clients):
            try:
                await client.send_json(payload)
            except Exception:
                stale_clients.append(client)

        for client in stale_clients:
            self.ws_clients.discard(client)

    async def _broadcast_bytes(self, payload: bytes) -> None:
        if not self.ws_clients:
            return

        stale_clients: list[WebSocket] = []
        for client in tuple(self.ws_clients):
            try:
                await client.send_bytes(payload)
            except Exception:
                stale_clients.append(client)

        for client in stale_clients:
            self.ws_clients.discard(client)

    def _cleanup_runtime(self) -> None:
        self._stop_output_event.set()

        if self._pty_master_fd is not None:
            try:
                os.close(self._pty_master_fd)
            except OSError:
                pass
        self._pty_master_fd = None

        if self._pty_process is not None and hasattr(self._pty_process, "close"):
            try:
                self._pty_process.close()
            except Exception:
                pass

        if self._output_thread and self._output_thread.is_alive():
            self._output_thread.join(timeout=1)
        self._output_thread = None

        self.process = None
        self._pty_process = None
        self.started_at = None


app = FastAPI(title="Oracle Dashboard Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def handle_http_exception(_, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        payload = detail
    else:
        payload = {
            "code": "http_error",
            "message": str(detail),
            "details": {},
        }
    return JSONResponse(status_code=exc.status_code, content={"ok": False, "error": payload})


@app.exception_handler(Exception)
async def handle_unexpected_exception(_, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": {
                "code": "internal_error",
                "message": "Unexpected server error",
                "details": {"reason": str(exc)},
            },
        },
    )


MANAGERS: dict[str, BotProcessManager] = {}
MANAGERS_LOCK = asyncio.Lock()


@app.on_event("shutdown")
async def shutdown_event():
    print("[oracle] Stopping all running bots...")
    async with MANAGERS_LOCK:
        for profile, manager in list(MANAGERS.items()):
            if manager.state in (BotState.ONLINE, BotState.STARTING):
                print(f"[oracle] Terminating bot process for profile: {profile}")
                try:
                    await manager.stop()
                except Exception as e:
                    print(f"[oracle] Error stopping bot {profile} during shutdown: {e}")


async def get_manager(profile: str) -> BotProcessManager:
    async with MANAGERS_LOCK:
        manager = MANAGERS.get(profile)
        if manager is None:
            manager = BotProcessManager(profile)
            MANAGERS[profile] = manager
        return manager


@app.get("/api/config")
async def get_config(profile: str = Query(default=DEFAULT_PROFILE)):
    profile_name = normalize_and_validate_profile(profile)
    config = options_resolver.import_profile_data(profile=profile_name, base_dir=options_resolver.USER_DATA_DIR)
    return {
        "profile": profile_name,
        "config": mask_config(config),
        "masked": ["user_token"],
    }


@app.post("/api/config")
async def post_config(payload: ConfigUpdatePayload):
    profile_name = normalize_and_validate_profile(payload.profile)
    if not payload.settings:
        api_error(400, "invalid_payload", "Settings payload must not be empty")

    # If any token is masked, restore the original value(s)
    for token_key in ("user_token", "miner_token", "telegram_bot_token"):
        incoming_token = payload.settings.get(token_key)
        if incoming_token is not None:
            is_masked = isinstance(incoming_token, str) and incoming_token.startswith("*") and all(c == "*" for c in incoming_token)
            if is_masked:
                existing_config = options_resolver.import_profile_data(profile=profile_name, base_dir=options_resolver.USER_DATA_DIR)
                original_token = existing_config.get(token_key)
                if original_token:
                    payload.settings[token_key] = original_token
                else:
                    payload.settings.pop(token_key, None)

    options_resolver.edit_profile_data(
        settings=payload.settings,
        profile=profile_name,
        base_dir=options_resolver.USER_DATA_DIR,
    )

    return {
        "status": "ok",
        "profile": profile_name,
    }


@app.get("/api/status")
async def get_status(profile: str = Query(default=DEFAULT_PROFILE)):
    profile_name = normalize_and_validate_profile(profile)
    manager = await get_manager(profile_name)
    return manager.status_payload()


@app.get("/api/stats")
async def get_stats(profile: str = Query(default=DEFAULT_PROFILE), mode: str = Query(default="session")):
    profile_name = normalize_and_validate_profile(profile)
    stats = _load_stats_for_profile(profile_name)
    if stats is None:
        stats = {}

    if mode == "session":
        baseline = _load_baseline_for_profile(profile_name)
        if baseline is not None:
            stats = _subtract_stats(stats, baseline)

    return stats


@app.get("/api/logs")
async def get_logs(profile: str = Query(default=DEFAULT_PROFILE), limit: int = 50):
    profile_name = normalize_and_validate_profile(profile)
    log_path = Path(options_resolver.USER_DATA_DIR) / f"{Path(profile_name).stem}.log"
    
    if not log_path.exists():
        return {"profile": profile_name, "lines": []}
        
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        lines = [line.strip() for line in lines[-limit:]]
        return {"profile": profile_name, "lines": lines}
    except Exception as exc:
        api_error(500, "read_logs_failed", f"Failed to read logs: {str(exc)}")


@app.post("/api/bot/start")
async def start_bot(payload: BotControlPayload):
    profile_name = normalize_and_validate_profile(payload.profile)
    manager = await get_manager(profile_name)
    started = await manager.start()
    return {
        "status": "started" if started else "already_running",
        "profile": profile_name,
    }


@app.post("/api/bot/stop")
async def stop_bot(payload: BotControlPayload):
    profile_name = normalize_and_validate_profile(payload.profile)
    manager = await get_manager(profile_name)
    stopped = await manager.stop()
    return {
        "status": "stopped" if stopped else "already_stopped",
        "profile": profile_name,
    }


# --- Profile Management Endpoints ---


@app.get("/api/profiles")
async def list_profiles():
    user_data_path = Path(options_resolver.USER_DATA_DIR)
    ini_files = sorted(
        p.name for p in user_data_path.iterdir()
        if p.is_file() and p.suffix == ".ini" and not p.name.startswith(".")
    )
    
    profiles_data = []
    for name in ini_files:
        manager = MANAGERS.get(name)
        state = manager.state.value if manager else "offline"
        
        is_incomplete = False
        try:
            config = options_resolver.import_profile_data(profile=name, base_dir=str(user_data_path))
            user_token = config.get("user_token", "").strip()
            guild_id = config.get("guild_id", "").strip()
            channel_id = config.get("channel_id", "").strip()
            if not user_token or not guild_id or not channel_id:
                is_incomplete = True
            elif user_token.lower() == "none" or guild_id.lower() == "none" or channel_id.lower() == "none":
                is_incomplete = True
        except Exception:
            is_incomplete = True
            
        profiles_data.append({
            "name": name,
            "state": state,
            "is_incomplete": is_incomplete
        })
        
    return {"profiles": profiles_data}


@app.post("/api/profiles")
async def create_profile(payload: ProfileCreatePayload):
    name = options_resolver.normalize_profile_name(payload.name)
    user_data_path = Path(options_resolver.USER_DATA_DIR)
    target = user_data_path / name

    if target.exists():
        api_error(409, "profile_exists", f"Profile '{name}' already exists", {"name": name})

    if payload.copyFrom:
        source_name = options_resolver.normalize_profile_name(payload.copyFrom)
        source = user_data_path / source_name
        if not source.exists():
            api_error(404, "source_not_found", f"Source profile '{source_name}' not found", {"name": source_name})
        shutil.copy2(str(source), str(target))
    else:
        example_src = os.path.join(options_resolver.BUNDLE_DIR, "options_example.ini")
        if os.path.exists(example_src):
            shutil.copy2(example_src, str(target))
        else:
            target.write_text("# Oracle profile\n", encoding="utf-8")

    return {"status": "ok", "name": name}


@app.delete("/api/profiles")
async def delete_profile(name: str = Query(...)):
    profile_name = options_resolver.normalize_profile_name(name)

    if profile_name == DEFAULT_PROFILE:
        api_error(403, "cannot_delete_default", "Cannot delete the default profile")

    user_data_path = Path(options_resolver.USER_DATA_DIR)
    target = user_data_path / profile_name
    if not target.exists():
        api_error(404, "profile_not_found", f"Profile '{profile_name}' not found", {"name": profile_name})

    manager = MANAGERS.get(profile_name)
    if manager and manager.state in (BotState.ONLINE, BotState.STARTING):
        api_error(
            409,
            "bot_running",
            "Stop the bot before deleting this profile",
            {"name": profile_name, "state": manager.state.value},
        )

    target.unlink()
    return {"status": "ok", "name": profile_name}


@app.post("/api/profiles/import")
async def import_profile(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".ini"):
        api_error(400, "invalid_file", "Only .ini files are allowed")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        api_error(400, "invalid_encoding", "File must be UTF-8 encoded")

    if "=" not in text:
        api_error(400, "invalid_content", "File does not appear to be a valid .ini file")

    name = options_resolver.normalize_profile_name(file.filename)
    user_data_path = Path(options_resolver.USER_DATA_DIR)
    target = user_data_path / name

    if target.exists():
        manager = MANAGERS.get(name)
        if manager and manager.state in (BotState.ONLINE, BotState.STARTING):
            api_error(
                409,
                "bot_running",
                "Pare o bot associado antes de sobrescrever o arquivo de configuração.",
                {"name": name, "state": manager.state.value},
            )

    target.write_text(text, encoding="utf-8")
    return {"status": "ok", "name": name}


@app.get("/api/profiles/export")
async def export_profile(name: str = Query(...)):
    profile_name = options_resolver.normalize_profile_name(name)
    user_data_path = Path(options_resolver.USER_DATA_DIR)
    target = user_data_path / profile_name

    if not target.exists():
        api_error(404, "profile_not_found", f"Profile '{profile_name}' not found", {"name": profile_name})

    content = target.read_text(encoding="utf-8-sig")
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{profile_name}"'},
    )


@app.websocket("/ws/terminal")
async def ws_terminal(websocket: WebSocket):
    raw_profile = websocket.query_params.get("profile", DEFAULT_PROFILE)
    profile_name = options_resolver.normalize_profile_name(raw_profile)

    try:
        normalize_and_validate_profile(profile_name)
    except HTTPException:
        await websocket.close(code=1008, reason="Invalid profile")
        return

    manager = await get_manager(profile_name)
    await websocket.accept()

    if manager.state == BotState.ONLINE:
        try:
            # Switch the client terminal to the alternate screen buffer, enable mouse tracking and SGR mouse mode
            await websocket.send_bytes(b"\x1b[?1049h\x1b[?1000h\x1b[?1002h\x1b[?1003h\x1b[?1006h")
            # Force the TUI process to redraw the entire screen (Ctrl+L)
            await manager.write_input(b"\x0c")
        except Exception:
            pass

    await manager.add_ws_client(websocket)

    try:
        await websocket.send_json(
            {
                "type": "status",
                "profile": profile_name,
                "state": manager.state.value,
            }
        )

        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            binary_payload = message.get("bytes")
            if binary_payload is not None:
                await manager.write_input(binary_payload)
                continue

            text_payload = message.get("text")
            if text_payload is None:
                continue

            try:
                control = json.loads(text_payload)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "invalid_json",
                        "message": "Invalid control message",
                    }
                )
                continue

            message_type = str(control.get("type", "")).strip().lower()
            if message_type == "heartbeat":
                await websocket.send_json({"type": "pong"})
                continue

            if message_type == "resize":
                cols = _coerce_int(control.get("cols"))
                rows = _coerce_int(control.get("rows"))
                if cols is None or rows is None or cols <= 0 or rows <= 0:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "code": "invalid_resize",
                            "message": "Resize requires positive cols and rows",
                        }
                    )
                    continue

                await manager.resize(cols=cols, rows=rows)
                continue

            await websocket.send_json(
                {
                    "type": "error",
                    "code": "unknown_control",
                    "message": "Unknown control message type",
                }
            )

    except WebSocketDisconnect:
        pass
    finally:
        await manager.remove_ws_client(websocket)


# --- Static file serving for built frontend ---

DIST_DIR = PROJECT_DIR / "dashboard" / "dist"

if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Serve the file if it exists, otherwise serve index.html for SPA routing
        file_path = DIST_DIR / full_path
        if full_path and file_path.is_file():
            return Response(
                content=file_path.read_bytes(),
                media_type=_guess_media_type(full_path),
            )
        index = DIST_DIR / "index.html"
        return Response(
            content=index.read_bytes(),
            media_type="text/html; charset=utf-8",
        )

    def _guess_media_type(path: str) -> str:
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        types = {
            "js": "application/javascript; charset=utf-8",
            "css": "text/css; charset=utf-8",
            "json": "application/json; charset=utf-8",
            "png": "image/png",
            "jpg": "image/jpeg",
            "svg": "image/svg+xml",
            "ico": "image/x-icon",
            "woff": "font/woff",
            "woff2": "font/woff2",
        }
        return types.get(ext, "application/octet-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("dashboard_server:app", host="127.0.0.1", port=8000, reload=False)
