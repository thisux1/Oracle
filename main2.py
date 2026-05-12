"""
Oracle v2 - Epic RPG Automation
Entry point. All logic lives in the bot/ package.
"""
from bot import UserBot, config
import options_resolver

print("\nStarting Oracle v2...")
print(f"Loaded Configuration: {options_resolver.optionsFilePath}\n")

UserBot.run(config.userToken)