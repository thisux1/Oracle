import re
import logging
from colorama import init, Fore, Back, Style

init(strip=False)

class HUDHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        HUD._write(msg)

# Setup root logger and OracleHUD logger to use HUDHandler
logger = logging.getLogger("OracleHUD")
logger.setLevel(logging.INFO)
logger.propagate = False

# Remove old handlers to prevent stdout tearing
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

hud_handler = HUDHandler()
hud_handler.setFormatter(logging.Formatter("%(message)s"))
logging.root.addHandler(hud_handler)
logger.addHandler(hud_handler)

class HUD:
    tui_callback = None
    _pause_depth = 1
    _buffer: list[str] = []
    _log_file = None
    _log_path = None

    @staticmethod
    def _is_paused() -> bool:
        return HUD._pause_depth > 0

    @staticmethod
    def pause():
        """Pause log output — buffer messages instead of writing."""
        HUD._pause_depth += 1

    @staticmethod
    def resume():
        """Resume log output and flush buffered messages."""
        if HUD._pause_depth > 0:
            HUD._pause_depth -= 1

        if HUD._is_paused():
            return

        for msg in HUD._buffer:
            if HUD.tui_callback:
                HUD.tui_callback(msg)
            else:
                print(msg)
        HUD._buffer.clear()

    @staticmethod
    def _write(msg):
        # Clean ANSI escape codes and log to profile-specific log file
        try:
            import options_resolver
            options_path = getattr(options_resolver, "optionsFilePath", None)
            if options_path:
                log_path = options_path.rsplit(".", 1)[0] + ".log"
                if HUD._log_path != log_path:
                    if HUD._log_file:
                        HUD._log_file.close()
                    HUD._log_path = log_path
                    HUD._log_file = open(log_path, "a", encoding="utf-8")
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                clean_msg = ansi_escape.sub('', msg).strip()
                if clean_msg:
                    import datetime
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    HUD._log_file.write(f"[{timestamp}] {clean_msg}\n")
                    HUD._log_file.flush()
        except Exception:
            pass

        if HUD._is_paused():
            HUD._buffer.append(msg)
            return
        if HUD.tui_callback:
            HUD.tui_callback(msg)
        else:
            print(msg)

    @staticmethod
    def loot(player, item, qty):
        # Premium green/yellow loot logs
        HUD._write(f"{Fore.GREEN}📦 [LOOT]{Fore.LIGHTGREEN_EX} {player.upper()} encontrou {qty:,}x {item.upper()}{Style.RESET_ALL}")

    @staticmethod
    def oracle(msg):
        # Oracle cyan/black logs
        HUD._write(f"{Fore.CYAN}{Back.BLACK} 🔮 [ORACLE] {msg} {Style.RESET_ALL}")

    @staticmethod
    def alert(msg):
        # Alert red/black logs
        HUD._write(f"{Fore.RED}{Back.BLACK} 🚨 [ALERTA] {msg.upper()} {Style.RESET_ALL}")

    @staticmethod
    def command(cmd, priority="LPQ"):
        # Commands styled beautifully
        if priority == "HPQ":
            prefix = f"{Fore.LIGHTMAGENTA_EX}⚡ [HPQ]{Fore.MAGENTA}"
        else:
            prefix = f"{Fore.LIGHTBLUE_EX}⚙️ [LPQ]{Fore.BLUE}"
        HUD._write(f"{prefix} ➔ {cmd}{Style.RESET_ALL}")

    @staticmethod
    def system(msg):
        # System black/gray logs
        HUD._write(f"{Fore.LIGHTBLACK_EX}⚙️ [SIS]{Fore.WHITE} {msg}{Style.RESET_ALL}")

    @staticmethod
    def cooldown(msg):
        # Cooldown logs
        HUD._write(f"{Fore.CYAN}⏳ [COOLDOWN]{Fore.LIGHTCYAN_EX} {HUD.clean_markdown(msg)}{Style.RESET_ALL}")

    SEPARATOR = f"{Fore.LIGHTBLACK_EX}{'─' * 60}{Style.RESET_ALL}"

    @staticmethod
    def dungeon(msg):
        HUD._write(f"{Fore.MAGENTA}⚔️ [DUNGEON]{Fore.LIGHTMAGENTA_EX} {msg}{Style.RESET_ALL}")

    @staticmethod
    def tc(msg):
        HUD._write(f"{Fore.YELLOW}🍪 [TIME COOKIE]{Fore.LIGHTYELLOW_EX} {msg}{Style.RESET_ALL}")

    @staticmethod
    def cardhand(msg):
        HUD._write(f"{Fore.LIGHTCYAN_EX}🃏 [MÃO DE CARTAS]{Fore.CYAN} {msg}{Style.RESET_ALL}")

    @staticmethod
    def separator():
        HUD._write(HUD.SEPARATOR)

    @staticmethod
    def navi(msg):
        HUD._write(f"{Fore.LIGHTBLUE_EX}🧚 [NAVI]{Fore.BLUE} {msg}{Style.RESET_ALL}")

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
