"""
Oracle v3 - Epic RPG Automation
Entry point. Launches the modern Textual TUI.
"""

import os
import sys
import time

# Suppress TensorFlow C++ logs before importing any bot modules
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from bot.tui import OracleApp

SESSION_START_TIME = time.time()

def main():
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
