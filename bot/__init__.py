# bot/ package - Modularized Epic RPG Automation
# Import order matters: config → hud → state → telegram → captcha → parsers → handlers → client

from bot.client import UserBot
from bot import config
