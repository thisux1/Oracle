"""
Oracle v2 - Modern Terminal User Interface (TUI)
Complete implementation of the Textual interface and Discord bot hooks.
"""

import asyncio
import time
from random import randint

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import Screen, ModalScreen
from textual.widgets import Input, RichLog, Static

import bot.config as config
import options_resolver
from bot.hud import HUD
from bot.state import (
    bot_state,
    sessionData,
    initialSessionData,
    lowPriorityQueue,
    highPriorityQueue,
    lowPriorityQueueSet,
    highPriorityQueueSet,
    reset_bot_state,
    queue_tc_commands,
    add_to_high_priority_queue,
    add_to_low_priority_queue
)
from bot.tui_eye import EYE_FRAMES, SLEEP_SEQ, WAKE_SEQ, IDLE_SEQ
from bot.tui_frames import separator_heavy, separator_medium, separator_light
from bot.tui_splash_art import COFFEE_ART, COFFEE_ART_B, SLEEP_ART, SLEEP_ART_B
from bot.tui_themes import ORACLE_THEMES
from bot.utils import is_sleep_time
from bot import UserBot


# Theme definitions live in tui_themes.py


# ─── Help Modal ───
class HelpModal(ModalScreen):
    """Modal Screen displaying commands and shortcuts."""

    def compose(self) -> ComposeResult:
        theme_info = next((t for t in ORACLE_THEMES if t["name"] == self.app.theme), ORACLE_THEMES[0])
        pri = theme_info["colors"][0]
        sec = theme_info["colors"][1]
        acc = theme_info["colors"][2]
        fg = theme_info["colors"][3]

        title = (
            "\n"
            f"[bold {fg}]     O R A C L E   V 2[/]\n"
            f"[{acc}]     ════════════════════════[/]\n"
        )

        core_cmds = (
            f"[bold {acc}]CONTROLES PRINCIPAIS[/]\n"
            "[dim](prefixo 'sb ' é opcional)[/]\n"
            f"[{acc}]──────────────────────────────[/]\n"
            f"[bold {acc}]start[/] [dim]│[/] [bold {acc}]resume[/]\n"
            f"  [{fg}]Despausa o bot[/]\n"
            f"[bold {acc}]pause[/] [dim]│[/] [bold {acc}]stop[/]\n"
            f"  [{fg}]Pausa o bot[/]\n"
            f"[bold {acc}]say[/] [dim #6b5e4a]<texto>[/]\n"
            f"  [{fg}]Envia comando para o canal[/]\n"
            f"[bold {acc}]reset[/]\n"
            f"  [{fg}]Limpa estado e filas[/]\n"
            f"[bold {acc}]stats[/] [dim #6b5e4a][periodo][/]\n"
            f"  [{fg}]Mostra estatísticas (ex: 1h, 30m)[/]\n"
            f"[bold {acc}]queue[/]\n"
            f"  [{fg}]Mostra filas de prioridade[/]\n"
            f"[bold {acc}]theme[/]\n"
            f"  [{fg}]Abre seletor de temas[/]\n"
            f"[bold {acc}]exit[/] [dim]│[/] [bold {acc}]quit[/]\n"
            f"  [{fg}]Encerramento seguro[/]"
        )

        tc_cmds = (
            f"[bold {acc}]COOKIE DE TEMPO[/]\n"
            f"[{acc}]──────────────────────────────[/]\n"
            f"[bold {acc}]tc start[/] [dim #6b5e4a][Xc] [Xm][/]\n"
            f"  [{fg}]Ativa o modo TC[/]\n"
            f"[bold {acc}]tc stop[/]\n"
            f"  [{fg}]Desativa o modo TC[/]"
        )

        rpg_cmds = (
            f"[bold {acc}]RPG DIRETO[/]\n"
            f"[{acc}]──────────────────────────────[/]\n"
            f"[bold {acc}]rpg[/] [dim #6b5e4a]<comando>[/]\n"
            f"  [{fg}]Envia para a fila de alta prioridade (HPQ)[/]"
        )

        shortcuts = (
            f"[bold {acc}]ATALHOS[/]\n"
            f"[{acc}]──────────────────────────────[/]\n"
            f"[bold {fg}]↑ ↓[/]   [{fg}]Navegação do histórico[/]\n"
            f"[bold {fg}]Tab[/]   [{fg}]Alternar foco[/]\n"
            f"[bold {fg}]Esc[/]   [{fg}]Fechar esta sobreposição[/]"
        )

        footer = (
            "[dim]-----------------------[/]\n"
            "[dim italic]Pressione [bold]Esc[/bold] para fechar[/]"
        )

        yield Container(
            Static(title, id="help_title"),
            VerticalScroll(
                Static(core_cmds, classes="help-section"),
                Static(tc_cmds, classes="help-section"),
                Static(rpg_cmds, classes="help-section"),
                Static(shortcuts, classes="help-section"),
                id="help_body",
            ),
            Static(footer, id="help_footer"),
            id="help_box",
        )

    def on_mount(self) -> None:
        """Pause log output while modal is visible to prevent render corruption."""
        HUD.pause()

    def on_key(self, event) -> None:
        if event.key == "escape":
            HUD.resume()
            self.dismiss()


# ─── Theme Selector ───
class ThemeModal(ModalScreen):
    """Theme selector with live preview on navigation."""

    def __init__(self) -> None:
        super().__init__()
        self._prev_theme: str = ""
        self._idx: int = 0

    def compose(self) -> ComposeResult:
        title = (
            "\n"
            "[bold]     T E M A S[/]\n"
        )
        footer = (
            "[dim]↑↓ Navegar   Enter Confirmar   Esc Cancelar[/]"
        )
        yield Container(
            Static(title, id="theme_title"),
            VerticalScroll(
                Static(id="theme_list"),
                id="theme_body",
            ),
            Static(footer, id="theme_footer"),
            id="theme_box",
        )

    def on_mount(self) -> None:
        self._prev_theme = self.app.theme
        for i, t in enumerate(ORACLE_THEMES):
            if t["name"] == self._prev_theme:
                self._idx = i
                break
        HUD.pause()
        self._render_list()

    def _render_list(self) -> None:
        lines: list[str] = []
        for i, t in enumerate(ORACLE_THEMES):
            sw = " ".join(f"[{c}]██[/]" for c in t["colors"])
            if i == self._idx:
                lines.append(
                    f"[bold]▸ {t['label']}[/]  {sw}\n"
                    f"  [dim italic]{t['desc']}[/]"
                )
            else:
                lines.append(f"  [dim]{t['label']}[/]  {sw}")
        self.query_one("#theme_list", Static).update(
            Text.from_markup("\n".join(lines))
        )

    def _apply_preview(self) -> None:
        self.app.theme = ORACLE_THEMES[self._idx]["name"]
        self._render_list()

    def on_key(self, event) -> None:
        if event.key == "up":
            self._idx = (self._idx - 1) % len(ORACLE_THEMES)
            self._apply_preview()
            event.prevent_default()
        elif event.key == "down":
            self._idx = (self._idx + 1) % len(ORACLE_THEMES)
            self._apply_preview()
            event.prevent_default()
        elif event.key == "enter":
            new_theme = ORACLE_THEMES[self._idx]["name"]
            config.theme = new_theme
            options_resolver.editData("theme", new_theme)
            HUD.resume()
            self.dismiss(new_theme)
        elif event.key == "escape":
            self.app.theme = self._prev_theme
            HUD.resume()
            self.dismiss()


# ─── Splash Screen ───
class SplashScreen(ModalScreen):
    """Clean splash screen with progress bar, giant eye art, and text animation."""

    progress = reactive(0)
    shine_pos = reactive(-10)

    def compose(self) -> ComposeResult:
        yield Static(id="splash_art")

    def on_mount(self) -> None:
        self._progress_timer = self.set_interval(0.04, self._tick_progress)
        self._anim_timer = self.set_interval(0.05, self._tick_anim)
        self._render_splash()

    def _tick_progress(self) -> None:
        if self.progress < 100:
            self.progress += 2
            self._render_splash()
        else:
            self._progress_timer.stop()
            self._anim_timer.stop()
            self.dismiss()

    def _tick_anim(self) -> None:
        self.shine_pos += 2
        if self.shine_pos > 80:
            self.shine_pos = -10
        self._render_splash()

    def _render_splash(self) -> None:
        from bot.tui_splash_art import GIANT_EYE_ART, ORACLE_TITLE_ART
        
        theme_info = next((t for t in ORACLE_THEMES if t["name"] == self.app.theme), ORACLE_THEMES[0])
        pri = theme_info["colors"][0]
        sec = theme_info["colors"][1]
        acc = theme_info["colors"][2]
        fg = theme_info["colors"][3]

        # 1. Crop vertical empty space
        lines = GIANT_EYE_ART.split("\n")
        cropped_lines = [line for line in lines if line.strip() != ""]
        
        # 2. Crop horizontal empty space
        if cropped_lines:
            min_leading = min(len(line) - len(line.lstrip()) for line in cropped_lines if line.strip())
            cropped_lines = [line[min_leading:] for line in cropped_lines]
        
        # 3. Dynamic height adjustment to prevent overflowing the terminal
        term_height = self.size.height if self.size.height > 0 else 24
        reserved_lines = 16  # Title(7) + Progress(1) + texts + padding
        available_lines = max(5, term_height - reserved_lines)
        
        if len(cropped_lines) > available_lines:
            # Take the bottom portion of the eye (which usually contains the main details)
            start_idx = len(cropped_lines) - available_lines
            eye_art = "\n".join(cropped_lines[start_idx:])
        else:
            eye_art = "\n".join(cropped_lines)

        bar_w = 40
        filled = int((self.progress / 100) * bar_w)
        bar = "█" * filled + "░" * (bar_w - filled)

        # Gradient / Shine effect on the giant title (Horizontal Sweep)
        title_lines = ORACLE_TITLE_ART.strip("\n").split("\n")
        styled_title_lines = []
        for line in title_lines:
            styled_line = ""
            for i, char in enumerate(line):
                dist = abs(i - self.shine_pos)
                if dist <= 1:
                    styled_line += f"[#ffffff]{char}[/]"
                elif dist <= 3:
                    styled_line += f"[{acc}]{char}[/]"
                elif dist <= 5:
                    styled_line += f"[{fg}]{char}[/]"
                else:
                    styled_line += f"[{pri}]{char}[/]"
            styled_title_lines.append(styled_line)
        
        # We need to center the title explicitly since Textual centers the entire block
        styled_title = "\n".join(styled_title_lines)
                
        subtitle = "  Terminal de IA do Epic RPG  "
        styled_subtitle = ""
        for i, char in enumerate(subtitle):
            dist = abs((i + 15) - self.shine_pos)
            if dist <= 1:
                styled_subtitle += f"[#ffffff]{char}[/]"
            elif dist <= 3:
                styled_subtitle += f"[{acc}]{char}[/]"
            elif dist <= 5:
                styled_subtitle += f"[{fg}]{char}[/]"
            else:
                styled_subtitle += f"[{pri}]{char}[/]"

        splash = (
            f"[{pri}]{eye_art}[/]\n"
            "\n"
            f"{styled_title}\n"
            "\n"
            f"{styled_subtitle}\n"
            "\n"
            f"┃ [{pri}]{bar}[/] {self.progress:3d}% ┃\n"
            "\n"
            "Conectando…\n"
            "\n"
            "---------------------\n"
            "\n"
            f"[{fg}][ Pressione qualquer tecla para pular ][/]"
        )
        self.query_one("#splash_art", Static).update(splash)

    def on_key(self, event) -> None:
        self._progress_timer.stop()
        self._anim_timer.stop()
        self.dismiss()


# ─── Eye Widget ───
class EyeWidget(Static):
    """Dynamic animated eye mascot with continuous ping-pong idle motion.

    Responsively crops/centers frames to fit the available sidebar width,
    keeping the visual center of the eye always visible.
    """

    # The original frame width in columns
    _FRAME_WIDTH = 41

    def on_mount(self) -> None:
        self.mode = "active"
        self.sequence = list(IDLE_SEQ)
        self.seq_idx = 0
        self._current_frame = self.sequence[0]
        self.set_interval(0.25, self._tick_anim)
        self._show_frame(self._current_frame)

    def on_resize(self, event) -> None:
        """Re-render current frame when sidebar width changes."""
        if hasattr(self, "_current_frame"):
            self._show_frame(self._current_frame)

    def set_mode(self, mode: str, force: bool = False) -> None:
        self.mode = mode

    def _frame_style(self, frame_name: str) -> str:
        theme_info = next((t for t in ORACLE_THEMES if t["name"] == self.app.theme), ORACLE_THEMES[0])
        return theme_info["colors"][2]

    @staticmethod
    def _fit_line(line: str, target_w: int, frame_w: int) -> str:
        """Center-crop or center-pad a single line to *target_w* columns."""
        if target_w >= frame_w:
            # Widget is wider than the frame — centre-pad
            pad_total = target_w - frame_w
            left = pad_total // 2
            return " " * left + line + " " * (pad_total - left)
        # Widget is narrower — centre-crop
        trim = frame_w - target_w
        left_trim = trim // 2
        return line[left_trim : left_trim + target_w]

    def _show_frame(self, frame_name: str) -> None:
        self._current_frame = frame_name
        avail_w = max(self.size.width - 2, 10)  # account for margin
        raw = EYE_FRAMES[frame_name]
        lines = raw.split("\n")
        # Strip trailing empty element from split
        if lines and lines[-1] == "":
            lines = lines[:-1]
        fitted = "\n".join(
            self._fit_line(l, avail_w, self._FRAME_WIDTH) for l in lines
        )
        self.update(Text.from_markup(f"[{self._frame_style(frame_name)}]{fitted}[/]"))

    def _tick_anim(self) -> None:
        if not self.sequence:
            self.sequence = list(IDLE_SEQ)
            self.seq_idx = 0

        frame_name = self.sequence[self.seq_idx]
        self._show_frame(frame_name)
        self.seq_idx += 1

        if self.seq_idx >= len(self.sequence):
            self.seq_idx = 0


# ─── Header Pane ───
class HeaderPane(Static):
    """Top header bar with status indicators and a light shimmer."""

    rune_idx = reactive(0)
    title_idx = reactive(0)

    def on_mount(self) -> None:
        self._runes = ["▪", "▫", "▪", "▫"]
        self._title = "O R A C L E   V 2"
        self.set_interval(0.30, self._tick)

    def _tick(self) -> None:
        self.rune_idx = (self.rune_idx + 1) % len(self._runes)
        self.title_idx = (self.title_idx + 1) % len(self._title)
        self.refresh()

    def _status(self) -> tuple[str, str]:
        theme_info = next((t for t in ORACLE_THEMES if t["name"] == self.app.theme), ORACLE_THEMES[0])
        sec = theme_info["colors"][1]
        acc = theme_info["colors"][2]
        if is_sleep_time():
            return "SONO", f"bold {sec}"
        if bot_state.paused:
            return "PAUSADO", "bold #cc0000"
        if bot_state.is_on_coffee_break:
            return "OCIOSO", f"bold {acc}"
        return "ONLINE", "bold #00f2ff"

    def render(self) -> Text:
        theme_info = next((t for t in ORACLE_THEMES if t["name"] == self.app.theme), ORACLE_THEMES[0])
        pri = theme_info["colors"][0]
        acc = theme_info["colors"][2]
        fg = theme_info["colors"][3]

        status_text, status_style = self._status()
        title = Text()
        for idx, char in enumerate(self._title):
            if char == " ":
                title.append(" ")
                continue

            distance = abs(idx - self.title_idx)
            if distance == 0:
                style = f"bold {fg}"
            elif distance == 1:
                style = acc
            else:
                style = pri
            title.append(char, style=style)

        line = Text()
        line.append("  ")
        line.append(self._runes[self.rune_idx], style=f"bold {acc}")
        line.append("  ")
        line.append(title)
        line.append("  ")
        line.append(self._runes[(self.rune_idx + 2) % len(self._runes)], style=f"bold {acc}")
        line.append("  ")
        line.append(status_text, style=status_style)
        line.append("  ")
        line.append(self._runes[(self.rune_idx + 1) % len(self._runes)], style=f"bold {acc}")
        return line


# ─── Sidebar Pane ───
class SidebarPane(Static):
    """Dynamic status panel showing session stats, coffee break, or sleep state.

    All content adapts to the available widget width:
    - Section headers fill the width with ornamental dashes
    - ASCII art is center-cropped when too wide
    - Text lines are truncated with ellipsis when needed
    """

    uptime = reactive("0h 0m")
    steam_idx = reactive(0)

    def on_mount(self) -> None:
        self._steam = ["︵", " ︵", "  ︵"]
        self._ornaments = ["▪", "▫", "▪"]
        self._eye_mode = None
        self.set_interval(1.0, self._tick)
        self.set_interval(0.4, self._tick_steam)
        self._sync_eye_mode()

    # ── helpers ──

    @staticmethod
    def _header(label: str, marker: str, width: int) -> str:
        """Build a centered section header that fills *width* columns.

        Example (w=30):  ──── ✦ STATUS ────
        """
        inner = f" {marker} {label} "
        remaining = max(0, width - len(inner))
        left = remaining // 2
        right = remaining - left
        return "─" * left + inner + "─" * right

    @staticmethod
    def _fit_art(art_lines: list[str], width: int) -> str:
        """Center-crop / center-pad a list of art lines to *width* cols."""
        fitted = []
        for line in art_lines:
            line_w = len(line)
            if line_w <= width:
                pad = width - line_w
                left = pad // 2
                fitted.append(" " * left + line + " " * (pad - left))
            else:
                trim = line_w - width
                left = trim // 2
                fitted.append(line[left : left + width])
        return "\n".join(fitted)

    @staticmethod
    def _trunc(text: str, width: int) -> str:
        """Truncate *text* to *width* columns, adding ellipsis if needed."""
        if len(text) <= width:
            return text
        return text[: max(0, width - 1)] + "…"

    # ── eye sync ──

    def _desired_eye_mode(self) -> str:
        if is_sleep_time() or bot_state.paused:
            return "sleep"
        if bot_state.is_on_coffee_break:
            return "coffee"
        return "active"

    def _sync_eye_mode(self) -> None:
        mode = self._desired_eye_mode()
        if mode == self._eye_mode:
            return

        self._eye_mode = mode
        try:
            eye = self.app.query_one("#eye-widget", EyeWidget)
            eye.set_mode(mode)
        except Exception:
            pass

    # ── tickers ──

    def _tick(self) -> None:
        elapsed = int(time.time() - config.startTime)
        h, m = elapsed // 3600, (elapsed % 3600) // 60
        self.uptime = f"{h}h {m}m"
        self._sync_eye_mode()
        self.refresh()

    def _tick_steam(self) -> None:
        self.steam_idx = (self.steam_idx + 1) % len(self._steam)
        self._sync_eye_mode()
        self.refresh()

    # ── render ──

    def render(self) -> str:
        w = max(self.size.width - 2, 10)
        marker = self._ornaments[self.steam_idx % len(self._ornaments)]

        if is_sleep_time():
            sleep_art = SLEEP_ART if self.steam_idx % 2 == 0 else SLEEP_ART_B
            return (
                f"{self._header('HIBERNAÇÃO', marker, w)}\n"
                "\n"
                f"{self._fit_art(sleep_art, w)}\n"
                "\n"
                f"{self._trunc(' Hibernando...', w)}\n"
                f"{self._trunc(f' Acordar às: {config.wake_up_at}', w)}\n"
                f"{self._trunc(' Auto-retomar: LIGADO', w)}\n"
                f"\n{separator_medium(w)}\n"
            )

        if bot_state.paused:
            return (
                f"{self._header('PAUSADO', marker, w)}\n"
                "\n"
                f"{self._trunc(' O bot está pausado.', w)}\n"
                f"{self._trunc(' Digite sb resume para acordar.', w)}\n"
                f"\n{separator_medium(w)}\n"
            )

        if bot_state.is_on_coffee_break:
            remaining = max(0, int(bot_state.next_break_time - time.time()))
            mm, ss = remaining // 60, remaining % 60
            coffee_art = COFFEE_ART if self.steam_idx % 2 == 0 else COFFEE_ART_B

            return (
                f"{self._header('PAUSA PARA CAFÉ', marker, w)}\n"
                "\n"
                f"{self._fit_art(coffee_art, w)}\n"
                "\n"
                f"{self._trunc(' Simulando pausa humana...', w)}\n"
                f"\n{separator_medium(w)}\n"
                f"{self._trunc(f'  Retomando em {mm:02d}:{ss:02d}', w)}\n"
            )

        hunts = sessionData["command_data"].get("hunt", 0) - initialSessionData["command_data"].get("hunt", 0)
        advs = sessionData["command_data"].get("adventure", 0) - initialSessionData["command_data"].get("adventure", 0)
        farms = sessionData["command_data"].get("farm", 0) - initialSessionData["command_data"].get("farm", 0)
        lboxes = sessionData["command_data"].get("lootbox", 0) - initialSessionData["command_data"].get("lootbox", 0)
        coins = sessionData["progress_data"].get("coins", 0) - initialSessionData["progress_data"].get("coins", 0)
        xp = sessionData["progress_data"].get("xp", 0) - initialSessionData["progress_data"].get("xp", 0)

        drops = []
        for cat in ["mob_drops", "work_drops", "farm_drops"]:
            for k, v in sessionData["loot_data"].get(cat, {}).items():
                delta = v - initialSessionData["loot_data"].get(cat, {}).get(k, 0)
                if delta > 0:
                    drops.append(f" · {k}: {delta}")

        # Truncate each drop line to fit width
        if drops:
            drops_str = "\n".join(self._trunc(d, w) for d in drops[:5])
        else:
            drops_str = self._trunc(" · Sem drops ainda", w)

        # Use compact labels when sidebar is narrow
        if w < 28:
            stats_lines = (
                f" Hunt: {hunts}\n"
                f" Adv: {advs}\n"
                f" Farm: {farms}\n"
                f" Lbx: {lboxes}\n"
                f" Coins: +{coins:,}\n"
                f" XP: +{xp:,}\n"
            )
        else:
            stats_lines = (
                f" Hunts: {hunts}\n"
                f" Advs: {advs}\n"
                f" Farms: {farms}\n"
                f" Lootboxes: {lboxes}\n"
                f" Coins: +{coins:,}\n"
                f" XP: +{xp:,}\n"
            )

        return (
            f"{self._header('ESTADO', marker, w)}\n"
            f"{self._trunc(' Estado: ATIVO', w)}\n"
            f"{self._trunc(f' Sono: {config.sleep_at}', w)}\n"
            f"{self._trunc(f' Uptime: {self.uptime}', w)}\n"
            f"\n{separator_medium(w)}\n"
            f" ESTATÍSTICAS DA SESSÃO\n"
            f"{stats_lines}"
            f"\n{separator_medium(w)}\n"
            f" ÚLTIMOS DROPS\n"
            f"{drops_str}\n"
        )


# ─── Status Bar ───
class StatusBar(Static):
    """Bottom bar showing queue counts, state, and last command."""

    pulse_idx = reactive(0)

    def on_mount(self) -> None:
        self._spinners = ["◐", "◓", "◑", "◒"]
        self.set_interval(0.2, self._tick)

    def _tick(self) -> None:
        self.pulse_idx = (self.pulse_idx + 1) % len(self._spinners)
        self.refresh()

    def _state(self) -> tuple[str, str]:
        if is_sleep_time():
            return "SONO", "bold #6b5e4a"
        if bot_state.paused:
            return "PAUSADO", "bold #cc0000"
        if bot_state.is_on_coffee_break:
            return "OCIOSO", "bold #d4a843"
        return "ONLINE", "bold #00f2ff"

    def render(self) -> Text:
        state_text, state_style = self._state()
        last = bot_state.last_sent_command or "Nenhum"
        if len(last) > 32:
            last = last[:29] + "..."

        line = Text()
        line.append(" ")
        line.append(self._spinners[self.pulse_idx], style="bold #d4a843")
        line.append(" ")
        line.append(f"HPQ: {len(highPriorityQueue)}", style="bold #c8b89a")
        line.append("  │  ", style="dim")
        line.append(f"LPQ: {len(lowPriorityQueue)}", style="bold #c8b89a")
        line.append("  │  ", style="dim")
        line.append(f"Último: {last}", style="#c8b89a")
        line.append("  │  ", style="dim")
        line.append(state_text, style=state_style)
        return line


# ─── Autocomplete System ───
COMMANDS = [
    "/help",
    "/start",
    "/pause",
    "/reset",
    "/stats",
    "/queue",
    "/say",
    "/tc start",
    "/tc stop",
    "/sleep",
    "/theme",
    "/exit"
]

class AutocompleteItem(Static):
    """An individual command item in the autocomplete list."""
    
    def __init__(self, command: str, index: int, parent_dropdown) -> None:
        super().__init__(f"  • {command}")
        self.command = command
        self.index = index
        self.parent_dropdown = parent_dropdown
        self.can_focus = False
        
    def on_click(self) -> None:
        self.parent_dropdown.select_item(self.index)


class AutocompleteDropdown(Static):
    """Dropdown showing command suggestions above the input."""

    items = reactive([])
    selected_idx = reactive(-1)

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="autocomplete-items-container")

    def on_mount(self) -> None:
        self.add_class("hidden")

    def watch_items(self, items: list[str]) -> None:
        self.selected_idx = -1
        self.rebuild_items()

    def rebuild_items(self) -> None:
        container = self.query_one("#autocomplete-items-container", VerticalScroll)
        container.remove_children()
        
        if not self.items:
            self.add_class("hidden")
            return
        
        self.remove_class("hidden")
        for idx, item in enumerate(self.items):
            widget = AutocompleteItem(item, idx, self)
            widget.classes = "autocomplete-item"
            container.mount(widget)

    def select_item(self, index: int) -> None:
        if 0 <= index < len(self.items):
            chosen = self.items[index]
            cmd_input = self.app.query_one("#command-input", CommandInput)
            cmd_input.value = chosen
            cmd_input.focus()
            # Position cursor at the end of the input
            cmd_input.cursor_position = len(chosen)
            self.items = []

    def move_selection(self, direction: int) -> None:
        if not self.items:
            return
        
        new_idx = self.selected_idx + direction
        if new_idx < 0:
            new_idx = len(self.items) - 1
        elif new_idx >= len(self.items):
            new_idx = 0
            
        self.selected_idx = new_idx
        self.update_highlight()

    def update_highlight(self) -> None:
        container = self.query_one("#autocomplete-items-container", VerticalScroll)
        items = container.query(AutocompleteItem)
        for idx, item in enumerate(items):
            if idx == self.selected_idx:
                item.add_class("selected")
                item.scroll_visible()
            else:
                item.remove_class("selected")


# ─── Command Input ───
class CommandInput(Input):
    """Stylized command input with history and spinner."""

    spinner_idx = reactive(0)
    is_processing = reactive(False)

    def on_mount(self) -> None:
        self.focus()
        self.placeholder = "OracleCLI | digite /help para comandos..."
        self.history: list[str] = []
        self.history_idx = -1
        self.set_interval(0.25, self._tick_spinner)
        self._spinners = ["◐", "◓", "◑", "◒"]

    def _tick_spinner(self) -> None:
        if self.is_processing:
            self.spinner_idx = (self.spinner_idx + 1) % 4
            self.placeholder = f"Processando {self._spinners[self.spinner_idx]} ..."

    def on_key(self, event) -> None:
        try:
            dropdown = self.app.query_one("#autocomplete-dropdown", AutocompleteDropdown)
        except Exception:
            dropdown = None

        if dropdown and dropdown.items:
            if event.key == "up":
                dropdown.move_selection(-1)
                event.prevent_default()
                return
            elif event.key == "down":
                dropdown.move_selection(1)
                event.prevent_default()
                return
            elif event.key in ("enter", "tab") and dropdown.selected_idx != -1:
                dropdown.select_item(dropdown.selected_idx)
                event.prevent_default()
                return
            elif event.key == "escape":
                dropdown.items = []
                event.prevent_default()
                return

        if event.key == "up" and self.history:
            if self.history_idx < len(self.history) - 1:
                self.history_idx += 1
                self.value = self.history[self.history_idx]
            event.prevent_default()
        elif event.key == "down":
            if self.history_idx > 0:
                self.history_idx -= 1
                self.value = self.history[self.history_idx]
            else:
                self.history_idx = -1
                self.value = ""
            event.prevent_default()

    def watch_value(self, old_value: str, new_value: str) -> None:
        try:
            dropdown = self.app.query_one("#autocomplete-dropdown", AutocompleteDropdown)
        except Exception:
            return
            
        if new_value.startswith("/"):
            search = new_value.lower()
            filtered = [c for c in COMMANDS if c.lower().startswith(search)]
            dropdown.items = filtered
        else:
            dropdown.items = []

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        cmd = event.value.strip()
        self.value = ""
        if not cmd:
            return

        self.history.insert(0, cmd)
        self.history_idx = -1
        self.is_processing = True
        await self._process_command(cmd)
        self.is_processing = False
        self.placeholder = "OracleCLI | digite /help para comandos..."

    async def _process_command(self, cmd: str) -> None:
        cmd_clean = cmd.strip()
        if cmd_clean.startswith("/"):
            cmd_clean = cmd_clean[1:].strip()

        # Support optional prefix "sb " (case-insensitive)
        if cmd_clean.lower().startswith("sb "):
            cmd_clean = cmd_clean[3:].strip()

        parts = cmd_clean.split()
        if not parts:
            return
        base = parts[0].lower()

        if base in ["help", "ajuda", "tutorial", "/help", "?"]:
            self.app.push_screen(HelpModal())

        elif base in ["play", "start", "resume"]:
            bot_state.paused = False
            HUD.oracle("Bot retomado/iniciado manualmente.")

        elif base in ["pause", "stop"]:
            bot_state.paused = True
            HUD.oracle("Bot pausado manualmente.")

        elif base == "reset":
            highPriorityQueue.clear()
            highPriorityQueueSet.clear()
            lowPriorityQueue.clear()
            lowPriorityQueueSet.clear()
            reset_bot_state()
            HUD.oracle("Filas, Estados e Cooldowns RESETADOS. Bot despausado!")

        elif base == "stats":
            from bot.persistence import get_stats_for_period
            from bot.parsers import format_session_data
            if len(parts) > 1:
                period_str = parts[1]
                period_data = get_stats_for_period(sessionData, period_str)
                summary = format_session_data(period_data, f"Dados da Sessão (Últimos {period_str})")
            else:
                summary = format_session_data(sessionData, "Estatísticas da Sessão Ativa")
            for line in summary.split("\n"):
                HUD.oracle(line)

        elif base == "queue":
            HUD.oracle(f"HPQ ({len(highPriorityQueue)}): {list(highPriorityQueue)}")
            HUD.oracle(f"LPQ ({len(lowPriorityQueue)}): {list(lowPriorityQueue)}")

        elif base == "say":
            if len(parts) > 1:
                text_to_say = cmd_clean[len(parts[0]):].strip()
                add_to_high_priority_queue(text_to_say)
                HUD.system(f"Comando manual enviado para a fila: {text_to_say}")
            else:
                HUD.alert("Uso: sb say <mensagem>")

        elif base == "tc":
            if len(parts) > 1 and parts[1].lower() == "start":
                bot_state.time_cookie_mode = True
                bot_state.tc_quantity = config.tc_quantity

                # Check for Xc override or duration
                for part in parts[2:]:
                    if part.endswith('c') and part[:-1].isdigit():
                        bot_state.tc_quantity = int(part[:-1])
                        break

                for part in parts[2:]:
                    if part.endswith('m') and part[:-1].isdigit():
                        mins = int(part[:-1])
                        bot_state.tc_end_time = time.time() + (mins * 60)
                        break
                else:
                    bot_state.tc_end_time = 0

                HUD.tc(f"Modo Time Cookie ATIVADO ({bot_state.tc_quantity} cookies/uso).")
                await queue_tc_commands()

            elif len(parts) > 1 and parts[1].lower() in ["stop", "pause"]:
                bot_state.time_cookie_mode = False
                bot_state.tc_end_time = 0
                HUD.system("Modo Time Cookie DESATIVADO.")
            else:
                HUD.alert("Uso: sb tc start [Xc] [Xm]  ou  sb tc stop")

        elif base == "sleep":
            bot_state.paused = True
            HUD.oracle("Modo hibernação ativado.")

        elif base.startswith("rpg"):
            highPriorityQueue.append(cmd)
            HUD.command(cmd, priority="HPQ")

        elif base == "cfg":
            if len(parts) >= 3:
                key, val = parts[1], " ".join(parts[2:])
                config.userOptions[key] = val
                HUD.oracle(f"Configuração atualizada: {key} = {val}")
            else:
                HUD.alert("Uso: cfg <chave> <valor>")

        elif base in ["theme", "themes"]:
            self.app.push_screen(ThemeModal())

        elif base in ["exit", "quit"]:
            HUD.oracle("Sequência de encerramento seguro iniciada...")
            self.app.exit()

        else:
            HUD.alert(f"Comando desconhecido: {cmd}")



# ─── Main Oracle App ───
class OracleApp(App):
    """The central Oracle V2 User Interface."""

    CSS_PATH = "tui_theme.tcss"
    TITLE = "Oracle V2"

    def compose(self) -> ComposeResult:
        yield HeaderPane(id="header-pane")
        with Horizontal(id="main-container"):
            yield RichLog(highlight=False, markup=False, wrap=True, id="log-pane")
            with Vertical(id="sidebar-container"):
                yield EyeWidget(id="eye-widget")
                with VerticalScroll(id="sidebar-scroll"):
                    sidebar = SidebarPane(id="sidebar-pane")
                    sidebar.can_focus = False
                    yield sidebar
        yield StatusBar(id="status-bar")
        with Vertical(id="input-container"):
            yield AutocompleteDropdown(id="autocomplete-dropdown")
            yield CommandInput(id="command-input")

    def on_mount(self) -> None:
        for t in ORACLE_THEMES:
            self.register_theme(t["theme"])
        self.theme = config.theme

        # Show splash
        self.push_screen(SplashScreen())

        # Hook HUD into RichLog
        log_pane = self.query_one("#log-pane", RichLog)
        def tui_writer(msg: str):
            log_pane.write(Text.from_ansi(msg))
        HUD.tui_callback = tui_writer

        # Start Discord bot worker
        self.start_discord_bot()

    @work(exclusive=True)
    async def start_discord_bot(self) -> None:
        """Main loop that drives connection to Discord and sleep scheduling."""
        await asyncio.sleep(3.5)
        HUD.oracle("Mecanismo TUI do Oracle v2.0 inicializado.")
        HUD.oracle("Núcleo da catedral online.")

        retry_delay = 5
        max_retry_delay = 300
        in_sleep_mode = False

        while True:
            if is_sleep_time():
                if not in_sleep_mode:
                    in_sleep_mode = True
                    HUD.alert("O sistema entrou no Modo de Sono / Hibernação.")
                retry_delay = 5
                await asyncio.sleep(60)
                continue

            in_sleep_mode = False
            HUD.system("Conectando ao gateway do Discord...")
            try:
                await UserBot.start(config.userToken)
                retry_delay = 5
            except asyncio.CancelledError:
                raise
            except Exception as e:
                HUD.alert(f"Bot desconectado: {e}")
                HUD.system(f"Tentando reconectar em {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_retry_delay)
