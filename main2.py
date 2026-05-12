"""
Oracle v2 - Epic RPG Automation
Entry point. All logic lives in the bot/ package.
"""
import asyncio
import time
from bot import UserBot, config
from bot.utils import is_sleep_time
import options_resolver

async def main():
    print("\n🔮 Oracle v2 - Starting Session...")
    print(f"Loaded Configuration: {options_resolver.optionsFilePath}\n")
    
    while True:
        if is_sleep_time():
            print(f"💤 [Sleep Mode] Active ({config.sleep_at} - {config.wake_up_at}). Going offline...")
            # Wait 1 minute before checking again
            await asyncio.sleep(60)
            continue
            
        print("🚀 [Online] Connecting to Discord...")
        try:
            # We use start() instead of run() to have better control in async
            await UserBot.start(config.userToken)
        except Exception as e:
            print(f"⚠️ [Error] Bot disconnected: {e}")
            print("Retrying in 30 seconds...")
            await asyncio.sleep(30)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Oracle v2 closed by user.")