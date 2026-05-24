"""
Oracle v2 - Epic RPG Automation
Entry point. All logic lives in the bot/ package.
"""
import asyncio
import sys
from bot import UserBot, config
from bot.utils import is_sleep_time
import options_resolver


from colorama import Fore, Style
from bot.hud import HUD

async def main():
    banner = f"""
{Fore.MAGENTA}       ____                  __
{Fore.LIGHTMAGENTA_EX}      / __ \\_________ ______/ /__
{Fore.LIGHTCYAN_EX}     / / / / ___/ __ `/ ___/ / _ \\
{Fore.CYAN}    / /_/ / /  / /_/ / /__/ /  __/
{Fore.BLUE}    \\____/_/   \\__,_/\\___/_/\\___/  {Fore.LIGHTWHITE_EX}v2.0.0
{Fore.LIGHTBLACK_EX}    ─────────────────────────────────────
{Fore.CYAN}     AI-POWERED EPIC RPG AUTOMATION SYSTEM
{Fore.LIGHTBLACK_EX}    ─────────────────────────────────────{Style.RESET_ALL}
"""
    print(banner)
    print(f" ⚙️  {Fore.LIGHTBLACK_EX}Config: {Fore.WHITE}{options_resolver.optionsFilePath}")
    print(f" 🧚  {Fore.LIGHTBLACK_EX}Channel ID: {Fore.WHITE}{config.channelID}")
    print(f" 💤  {Fore.LIGHTBLACK_EX}Sleep schedule: {Fore.WHITE}{config.sleep_at} - {config.wake_up_at}")
    print(f" ⏳  {Fore.LIGHTBLACK_EX}Watchdog Cooldown: {Fore.GREEN}1 Hour Auto-Recover")
    HUD.separator()

    retry_delay = 5
    max_retry_delay = 300
    in_sleep_mode = False

    while True:
        if is_sleep_time():
            if not in_sleep_mode:
                in_sleep_mode = True
                moon_art = f"""
{Fore.LIGHTBLUE_EX}        *   .         .   *
{Fore.LIGHTBLUE_EX}             *  .  *
{Fore.LIGHTCYAN_EX}           .---.
{Fore.LIGHTCYAN_EX}          /     \\  *    {Fore.CYAN}🌙 SYSTEM HIBERNATING (SLEEP MODE)
{Fore.CYAN}         |  🌙   |      {Fore.WHITE}Closed all gateway channels.
{Fore.CYAN}          \\     /       {Fore.LIGHTBLACK_EX}Safe offline status until morning.
{Fore.BLUE}           '---'        {Fore.LIGHTBLUE_EX}Offline period: {config.sleep_at} - {config.wake_up_at}
{Style.RESET_ALL}"""
                print(moon_art)
            retry_delay = 5
            await asyncio.sleep(60)
            continue

        in_sleep_mode = False
        print("🚀 [Online] Connecting to Discord...")
        try:
            await UserBot.start(config.userToken)
            retry_delay = 5
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"⚠️ [Error] Bot disconnected: {e}")
            print(f"Retrying in {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_retry_delay)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Oracle v2 closed by user.")
        try:
            from bot.state import sessionData
            from bot.parsers import format_session_data
            print("\n" + "=" * 45)
            print(format_session_data(sessionData, "Final Session Summary"))
            print("=" * 45 + "\n")
        except Exception:
            pass