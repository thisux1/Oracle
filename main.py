"""
Oracle v3 - Epic RPG Automation
Entry point. Launches the modern Textual TUI.
"""

import os
import sys
import time
import io
from contextlib import contextmanager

# Suppress TensorFlow C++ logs before importing any bot modules
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import warnings
warnings.simplefilter("ignore", category=UserWarning)
warnings.simplefilter("ignore", category=RuntimeWarning)

@contextmanager
def capture_startup_output():
    import tempfile
    # Create a temporary file to capture all OS-level output (including C/C++ libs)
    temp_file = tempfile.TemporaryFile(mode='w+t')
    temp_fd = temp_file.fileno()

    # Save original stdout/stderr file descriptors
    try:
        old_stdout_fd = os.dup(1)
        old_stderr_fd = os.dup(2)
    except OSError:
        old_stdout_fd = None
        old_stderr_fd = None

    # Redirect stdout (1) and stderr (2) to the temporary file
    if old_stdout_fd is not None:
        os.dup2(temp_fd, 1)
        os.dup2(temp_fd, 2)

    try:
        yield
        # Flush Python-level buffers BEFORE restoring the OS level file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        # If successful, restore original FDs
        if old_stdout_fd is not None:
            os.dup2(old_stdout_fd, 1)
            os.dup2(old_stderr_fd, 2)
    except (SystemExit, Exception) as e:
        # Flush Python-level buffers BEFORE restoring the OS level file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        # Restore original FDs first
        if old_stdout_fd is not None:
            os.dup2(old_stdout_fd, 1)
            os.dup2(old_stderr_fd, 2)
        # Seek to beginning of the temporary file and print its contents
        temp_file.seek(0)
        output = temp_file.read()
        if output:
            sys.stderr.write(output)
        raise e
    finally:
        if old_stdout_fd is not None:
            try:
                os.close(old_stdout_fd)
                os.close(old_stderr_fd)
            except OSError:
                pass
        temp_file.close()

with capture_startup_output():
    from bot.tui import OracleApp

SESSION_START_TIME = time.time()

def main():
    headless = False
    if "--headless" in sys.argv:
        sys.argv.remove("--headless")
        headless = True
    elif not sys.stdout.isatty():
        headless = True

    if headless:
        import asyncio
        from bot.tui import run_headless
        asyncio.run(run_headless())
    else:
        # Clear screen to wipe launcher messages & warnings before TUI runs
        sys.stdout.write("\033[H\033[2J")
        sys.stdout.flush()
        
        app = OracleApp()
        app.run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    
    # Print session summary and banner on exit
    try:
        from bot.state import sessionData, initialSessionData
        from bot.parsers import format_session_data
        from bot.tui_splash_art import ORACLE_TITLE_ART
        from bot.persistence import subtract_dicts
        
        # Color coding for terminal output using ANSI escape codes
        CYAN = "\033[1;36m"
        MAGENTA = "\033[1;35m"
        GREEN = "\033[1;32m"
        YELLOW = "\033[1;33m"
        RESET = "\033[0m"
        
        # Subtract initialSessionData from final sessionData to get only current session stats
        session_delta = subtract_dicts(sessionData, initialSessionData)
        session_delta["start_time"] = SESSION_START_TIME
        
        # 1. Print the Oracle Title Art
        print(f"\n{CYAN}{ORACLE_TITLE_ART.strip(chr(10))}{RESET}\n")
        
        # 2. Print session statistics
        print(f"{MAGENTA}{'=' * 65}{RESET}")
        print(f"{GREEN}          🔮 RESUMO COMPLETO DA SESSÃO ORACLE V3 🔮{RESET}")
        print(f"{MAGENTA}{'=' * 65}{RESET}")
        
        stats_text = format_session_data(session_delta, "Atividades & Progresso da Sessão")
        print(stats_text)
        
        print(f"{MAGENTA}{'=' * 65}{RESET}\n")
    except Exception:
        # Prevent any exceptions on shutdown from crashing
        pass
