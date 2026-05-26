"""
Oracle v2 - Epic RPG Automation
Entry point. Launches the modern Textual TUI.
"""

import os
import sys

# Suppress TensorFlow C++ logs before importing any bot modules
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from bot.tui import OracleApp

def main():
    app = OracleApp()
    app.run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOracle v2 fechado pelo usuário.")
        try:
            from bot.state import sessionData
            from bot.parsers import format_session_data
            print("\n" + "=" * 45)
            print(format_session_data(sessionData, "Resumo Final da Sessão"))
            print("=" * 45 + "\n")
        except Exception:
            pass