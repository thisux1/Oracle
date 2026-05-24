import re
import logging
from colorama import init, Fore, Back, Style

init()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("OracleHUD")


class HUD:
    @staticmethod
    def loot(player, item, qty):
        # Premium green/yellow loot logs
        print(f"{Fore.GREEN}📦 [LOOT]{Fore.LIGHTGREEN_EX} {player.upper()} found {qty:,}x {item.upper()}{Style.RESET_ALL}")

    @staticmethod
    def oracle(msg):
        # Oracle cyan/black logs
        print(f"{Fore.CYAN}{Back.BLACK} 🔮 [ORACLE] {msg} {Style.RESET_ALL}")

    @staticmethod
    def alert(msg):
        # Alert red/black logs
        print(f"{Fore.RED}{Back.BLACK} 🚨 [ALERT] {msg.upper()} {Style.RESET_ALL}")

    @staticmethod
    def command(cmd, priority="LPQ"):
        # Commands styled beautifully
        if priority == "HPQ":
            prefix = f"{Fore.LIGHTMAGENTA_EX}⚡ [HPQ]{Fore.MAGENTA}"
        else:
            prefix = f"{Fore.LIGHTBLUE_EX}⚙️ [LPQ]{Fore.BLUE}"
        print(f"{prefix} ➔ {cmd}{Style.RESET_ALL}")

    @staticmethod
    def system(msg):
        # System black/gray logs
        print(f"{Fore.LIGHTBLACK_EX}⚙️ [SYS]{Fore.WHITE} {msg}{Style.RESET_ALL}")

    @staticmethod
    def cooldown(msg):
        # Cooldown logs
        print(f"{Fore.CYAN}⏳ [COOLDOWN]{Fore.LIGHTCYAN_EX} {HUD.clean_markdown(msg)}{Style.RESET_ALL}")

    SEPARATOR = f"{Fore.LIGHTBLACK_EX}{'─' * 60}{Style.RESET_ALL}"

    @staticmethod
    def dungeon(msg):
        print(f"{Fore.MAGENTA}⚔️ [DUNGEON]{Fore.LIGHTMAGENTA_EX} {msg}{Style.RESET_ALL}")

    @staticmethod
    def tc(msg):
        print(f"{Fore.YELLOW}🍪 [TIME COOKIE]{Fore.LIGHTYELLOW_EX} {msg}{Style.RESET_ALL}")

    @staticmethod
    def cardhand(msg):
        print(f"{Fore.LIGHTCYAN_EX}🃏 [CARD HAND]{Fore.CYAN} {msg}{Style.RESET_ALL}")

    @staticmethod
    def separator():
        print(HUD.SEPARATOR)

    @staticmethod
    def navi(msg):
        print(f"{Fore.LIGHTBLUE_EX}🧚 [NAVI]{Fore.BLUE} {msg}{Style.RESET_ALL}")

    @staticmethod
    def clean_markdown(text):
        """Purge Discord IDs and translate markdown to ANSI."""
        if not text:
            return ""
        text = re.sub(r'<@!?[0-9]+>|<#[0-9]+>|<@&[0-9]+>', '', text)
        text = re.sub(r'<:[^:]+:[0-9]+>', '', text)
        text = re.sub(r'\*\*(.*?)\*\*', f'{Style.BRIGHT}\\1{Style.NORMAL}', text)
        text = re.sub(r'__(.*?)__', f'{Fore.CYAN}\\1{Fore.RESET}', text)
        return text.strip()
