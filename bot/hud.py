import re
import logging
from colorama import init, Fore, Back, Style

init()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("OracleHUD")


class HUD:
    @staticmethod
    def loot(player, item, qty):
        print(f"{Fore.YELLOW}[LOOT] {player.upper()} found {qty:,}x {item.upper()}{Style.RESET_ALL}")

    @staticmethod
    def oracle(msg):
        print(f"{Fore.CYAN}{Back.BLACK} [ORACLE] {msg} {Style.RESET_ALL}")

    @staticmethod
    def alert(msg):
        print(f"{Fore.WHITE}{Back.RED} [ALERT] {msg.upper()} {Style.RESET_ALL}")

    @staticmethod
    def command(cmd, priority="LPQ"):
        color = Fore.MAGENTA if priority == "HPQ" else Fore.BLUE
        print(f"{color}[{priority}] EXECUTING: {cmd}{Style.RESET_ALL}")

    @staticmethod
    def system(msg):
        print(f"{Fore.GREEN}[SYS] {msg}{Style.RESET_ALL}")

    @staticmethod
    def cooldown(msg):
        print(f"{Fore.BLACK}{Back.CYAN} [COOLDOWN] {HUD.clean_markdown(msg)} {Style.RESET_ALL}")

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
