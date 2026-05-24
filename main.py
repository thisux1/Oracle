"""
Oracle v2 - Epic RPG Automation
Entry point. All logic lives in the bot/ package.
"""
import asyncio
import sys
from bot import UserBot, config
from bot.utils import is_sleep_time
import options_resolver


async def main():
    print("\n🔮 Oracle v2 - Starting Session...")
    print(f"Loaded Configuration: {options_resolver.optionsFilePath}\n")

    retry_delay = 5
    max_retry_delay = 300

    while True:
        if is_sleep_time():
            print(f"💤 [Sleep Mode] Active ({config.sleep_at} - {config.wake_up_at}). Going offline...")
            retry_delay = 5
            await asyncio.sleep(60)
            continue

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