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
from bot.tui_eye import EYE_FRAMES, CAT_FRAMES, SLEEP_SEQ, WAKE_SEQ, IDLE_SEQ, CAT_SLEEP_SEQ, CAT_COLORS, CAT_FRAME_COLORS
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
        self._splash_timer = self.set_interval(0.05, self._tick_splash)
        self._render_splash()

    def _tick_splash(self) -> None:
        if self.progress < 100:
            self.progress += 2
        else:
            self._splash_timer.stop()
            self.dismiss()
            return

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

        def interpolate_color(c1: str, c2: str, factor: float) -> str:
            c1 = c1.lstrip('#')
            c2 = c2.lstrip('#')
            if len(c1) == 3: c1 = "".join(x*2 for x in c1)
            if len(c2) == 3: c2 = "".join(x*2 for x in c2)
            r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
            r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
            r = int(r1 + (r2 - r1) * factor)
            g = int(g1 + (g2 - g1) * factor)
            b = int(b1 + (b2 - b1) * factor)
            return f"#{r:02x}{g:02x}{b:02x}"

        def get_line_color(i: int, total_lines: int) -> str:
            if total_lines <= 1:
                return acc
            pos = i / (total_lines - 1)
            if pos < 0.25:
                return interpolate_color(sec, pri, pos / 0.25)
            elif pos < 0.5:
                return interpolate_color(pri, acc, (pos - 0.25) / 0.25)
            elif pos < 0.75:
                return interpolate_color(acc, pri, (pos - 0.5) / 0.25)
            else:
                return interpolate_color(pri, sec, (pos - 0.75) / 0.25)

        # Get terminal size
        term_height = self.size.height if self.size.height > 0 else 24
        term_width = self.size.width if self.size.width > 0 else 80

        # Responsive layout settings
        if term_height < 22:
            show_title = False
            spacing = ""
            reserved_lines = 5
        elif term_height < 32:
            show_title = True
            spacing = ""
            reserved_lines = 11
        else:
            show_title = True
            spacing = "\n"
            reserved_lines = 15

        available_lines = max(5, term_height - reserved_lines)

        # 1. Clean vertical empty space
        lines = GIANT_EYE_ART.split("\n")
        cropped_lines = [line for line in lines if line.replace(" ", "").replace("\u2800", "") != ""]
        
        # 2. Horizontal auto-crop empty space (Braille blank space is \u2800)
        if cropped_lines:
            min_leading = 9999
            max_trailing = 0
            for line in cropped_lines:
                left = 0
                while left < len(line) and line[left] in (' ', '\u2800'):
                    left += 1
                if left < len(line) and left < min_leading:
                    min_leading = left
                
                right = len(line)
                while right > 0 and line[right - 1] in (' ', '\u2800'):
                    right -= 1
                if right > max_trailing:
                    max_trailing = right
            
            if min_leading < max_trailing:
                cropped_lines = [line[min_leading:max_trailing] for line in cropped_lines]

        # 3. Apply coloring and horizontal slicing
        W_art = len(cropped_lines[0]) if cropped_lines else 0
        final_lines = []
        for i, line in enumerate(cropped_lines):
            line_color = get_line_color(i, len(cropped_lines))
            if term_width < W_art:
                crop_left = (W_art - term_width) // 2
                crop_right = crop_left + term_width
                line_content = line[crop_left:crop_right]
            else:
                line_content = line
            
            styled_line = f"[{line_color}]{line_content}[/]"
            final_lines.append(styled_line)

        # 4. Apply vertical cropping
        if len(final_lines) > available_lines:
            start_idx = (len(final_lines) - available_lines) // 2
            eye_art = "\n".join(final_lines[start_idx : start_idx + available_lines])
        else:
            eye_art = "\n".join(final_lines)

        # Giant title horizontal sweep shine
        styled_title = ""
        if show_title:
            title_lines = ORACLE_TITLE_ART.strip("\n").split("\n")
            styled_title_lines = []
            for line in title_lines:
                left_idx = max(0, self.shine_pos - 5)
                right_idx = min(len(line), self.shine_pos + 6)
                
                left_part = line[:left_idx]
                shine_part = line[left_idx:right_idx]
                right_part = line[right_idx:]
                
                styled_line = ""
                if left_part:
                    styled_line += f"[{pri}]{left_part}[/]"
                
                for idx_in_shine, char in enumerate(shine_part):
                    real_idx = left_idx + idx_in_shine
                    dist = abs(real_idx - self.shine_pos)
                    if dist <= 1:
                        styled_line += f"[#ffffff]{char}[/]"
                    elif dist <= 3:
                        styled_line += f"[{acc}]{char}[/]"
                    elif dist <= 5:
                        styled_line += f"[{fg}]{char}[/]"
                    else:
                        styled_line += f"[{pri}]{char}[/]"
                        
                if right_part:
                    styled_line += f"[{pri}]{right_part}[/]"
                styled_title_lines.append(styled_line)
            styled_title = "\n".join(styled_title_lines)
        
        # Subtitle
        subtitle = "  Terminal de IA do Epic RPG  "
        left_idx = max(0, self.shine_pos - 15 - 5)
        right_idx = min(len(subtitle), self.shine_pos - 15 + 6)
        left_part = subtitle[:left_idx]
        shine_part = subtitle[left_idx:right_idx]
        right_part = subtitle[right_idx:]
        
        styled_subtitle = ""
        if left_part:
            styled_subtitle += f"[{pri}]{left_part}[/]"
        for idx_in_shine, char in enumerate(shine_part):
            real_idx = left_idx + idx_in_shine
            dist = abs((real_idx + 15) - self.shine_pos)
            if dist <= 1:
                styled_subtitle += f"[#ffffff]{char}[/]"
            elif dist <= 3:
                styled_subtitle += f"[{acc}]{char}[/]"
            elif dist <= 5:
                styled_subtitle += f"[{fg}]{char}[/]"
            else:
                styled_subtitle += f"[{pri}]{char}[/]"
        if right_part:
            styled_subtitle += f"[{pri}]{right_part}[/]"

        # Progress Bar
        bar_w = min(40, term_width - 12) if term_width > 15 else 10
        filled = int((self.progress / 100) * bar_w)
        bar = "█" * filled + "░" * (bar_w - filled)
        bar_text = f"┃ [{pri}]{bar}[/] {self.progress:3d}% ┃"

        # Connecting text
        connecting_text = "Conectando…"

        # Separator
        separator = "---------------------"

        # Skip prompt
        skip_text = f"[{fg}][ Pressione qualquer tecla para pular ][/]"

        # Assemble the full layout
        parts = []
        parts.append(eye_art)
        if spacing:
            parts.append("")
        
        if show_title:
            parts.append(styled_title)
            if spacing:
                parts.append("")
        
        parts.append(styled_subtitle)
        if spacing:
            parts.append("")
            
        parts.append(bar_text)
        if spacing:
            parts.append("")
            
        parts.append(connecting_text)
        if spacing:
            parts.append("")
            
        parts.append(separator)
        if spacing:
            parts.append("")
            
        parts.append(skip_text)
        
        splash = "\n".join(parts)
        self.query_one("#splash_art", Static).update(splash)


    def on_key(self, event) -> None:
        self._splash_timer.stop()
        self.dismiss()


# ─── Eye Widget ───
class EyeWidget(Static):
    """Dynamic animated mascot — shows the eye while active, switches to a
    sleeping-cat animation during hibernation or coffee breaks.

    Responsively crops/centers frames to fit the available sidebar width,
    keeping the visual center always visible.
    """

    # Original frame widths per animation set
    _EYE_FRAME_WIDTH = 41
    _CAT_FRAME_WIDTH = 33

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
        if mode == self.mode and not force:
            return
        old_mode = self.mode
        self.mode = mode

        # Determine if the animation set needs to change
        was_cat = old_mode in ("sleep", "coffee")
        is_cat = mode in ("sleep", "coffee")

        if was_cat != is_cat or force:
            if is_cat:
                self.sequence = list(CAT_SLEEP_SEQ)
            else:
                self.sequence = list(IDLE_SEQ)
            self.seq_idx = 0
            if self.sequence:
                self._show_frame(self.sequence[0])

    def _is_cat_frame(self, frame_name: str) -> bool:
        return frame_name.startswith("cat_")

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

    @staticmethod
    def _cat_shades(hex_color: str) -> dict[str, str]:
        """Derive opacity shades from a theme hex color.

        Returns a dict mapping color classes to scaled hex colors:
        c0 = 100% (full brightness), c2 = 85%, c1 = 50%, c3 = 45%.
        """
        h = hex_color.lstrip("#")
        if len(h) == 3:
            h = h[0]*2 + h[1]*2 + h[2]*2
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        def scale(factor: float) -> str:
            return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"
        return {"c0": hex_color, "c2": scale(0.85), "c1": scale(0.50), "c3": scale(0.45)}

    def _show_frame(self, frame_name: str) -> None:
        self._current_frame = frame_name
        avail_w = max(self.size.width - 2, 10)  # account for margin

        if self._is_cat_frame(frame_name):
            raw = CAT_FRAMES[frame_name]
            frame_w = self._CAT_FRAME_WIDTH
            lines = raw.split("\n")
            if lines and lines[-1] == "":
                lines = lines[:-1]
            # Build theme-aware shade palette from accent color
            accent = self._frame_style(frame_name)  # e.g. "#d4a843"
            shades = self._cat_shades(accent)
            color_map = CAT_FRAME_COLORS.get(frame_name, {})
            result = Text()
            for y, line in enumerate(lines):
                fitted = self._fit_line(line, avail_w, frame_w)
                if avail_w >= frame_w:
                    offset = -(avail_w - frame_w) // 2
                else:
                    offset = (frame_w - avail_w) // 2
                for fitted_x, ch in enumerate(fitted):
                    orig_x = fitted_x + offset
                    key = f"{orig_x},{y}"
                    ck = color_map.get(key)
                    if ck:
                        result.append(ch, style=shades.get(ck, accent))
                    elif ch.strip():
                        result.append(ch, style=shades.get("c1", accent))
                    else:
                        result.append(ch)
                if y < len(lines) - 1:
                    result.append("\n")
            self.update(result)
        else:
            raw = EYE_FRAMES[frame_name]
            frame_w = self._EYE_FRAME_WIDTH
            lines = raw.split("\n")
            if lines and lines[-1] == "":
                lines = lines[:-1]
            fitted = "\n".join(
                self._fit_line(l, avail_w, frame_w) for l in lines
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
