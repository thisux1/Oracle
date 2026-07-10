"""Sidebar and status widgets for the Oracle TUI."""

import time

from rich.text import Text
from textual.reactive import reactive
from textual.widgets import Static

import bot.config as config
from bot.locales import t
from bot.state import bot_state, highPriorityQueue, initialSessionData, lowPriorityQueue, sessionData
from bot.tui_eye import CAT_FRAMES, CAT_FRAME_COLORS, EYE_FRAMES, IDLE_SEQ, CAT_SLEEP_SEQ
from bot.tui_frames import separator_medium
from bot.tui_splash_art import COFFEE_ART, COFFEE_ART_B, SLEEP_ART, SLEEP_ART_B
from bot.tui_themes import ORACLE_THEMES
from bot.utils import is_sleep_time


class EyeWidget(Static):
    """Dynamic animated mascot — shows the eye while active, switches to a
    sleeping-cat animation during hibernation or coffee breaks.

    Responsively crops/centers frames to fit the available sidebar width,
    keeping the visual center always visible.
    """

    ALLOW_SELECT = False

    _EYE_FRAME_WIDTH = 41
    _CAT_FRAME_WIDTH = 33

    def on_mount(self) -> None:
        self.mode = "active"
        self.sequence = list(IDLE_SEQ)
        self.seq_idx = 0
        self._current_frame = self.sequence[0]
        self.set_interval(0.5, self._tick_anim)
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
            pad_total = target_w - frame_w
            left = pad_total // 2
            return " " * left + line + " " * (pad_total - left)
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
            h = h[0] * 2 + h[1] * 2 + h[2] * 2
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

        def scale(factor: float) -> str:
            return f"#{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}"

        return {"c0": hex_color, "c2": scale(0.85), "c1": scale(0.50), "c3": scale(0.45)}

    def _show_frame(self, frame_name: str) -> None:
        self._current_frame = frame_name
        avail_w = max(self.size.width - 2, 10)

        if self._is_cat_frame(frame_name):
            raw = CAT_FRAMES[frame_name]
            frame_w = self._CAT_FRAME_WIDTH
            lines = raw.split("\n")
            if lines and lines[-1] == "":
                lines = lines[:-1]

            accent = self._frame_style(frame_name)
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
            fitted = "\n".join(self._fit_line(l, avail_w, frame_w) for l in lines)
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


class HeaderPane(Static):
    """Top header bar with status indicators and a light shimmer."""

    ALLOW_SELECT = False

    rune_idx = reactive(0)
    title_idx = reactive(0)

    def on_mount(self) -> None:
        self._runes = ["▪", "▫", "▪", "▫"]
        self._title = "O R A C L E   V 3"
        self.set_interval(1.5, self._tick)

    def _tick(self) -> None:
        self.rune_idx = (self.rune_idx + 1) % len(self._runes)
        self.title_idx = (self.title_idx + 1) % len(self._title)
        self.refresh()

    def _status(self) -> tuple[str, str]:
        theme_info = next((t for t in ORACLE_THEMES if t["name"] == self.app.theme), ORACLE_THEMES[0])
        sec = theme_info["colors"][1]
        acc = theme_info["colors"][2]
        if is_sleep_time():
            return t("header_sleep"), f"bold {sec}"
        if bot_state.paused:
            return t("header_paused"), "bold #cc0000"
        if bot_state.is_on_coffee_break:
            return t("header_idle"), f"bold {acc}"
        return t("header_online"), "bold #00f2ff"

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


class SidebarPane(Static):
    """Dynamic status panel showing session stats, coffee break, or sleep state.

    All content adapts to the available widget width:
    - Section headers fill the width with ornamental dashes
    - ASCII art is center-cropped when too wide
    - Text lines are truncated with ellipsis when needed
    """

    ALLOW_SELECT = False

    uptime = reactive("0h 0m")
    steam_idx = reactive(0)

    def on_mount(self) -> None:
        self._steam = ["︵", " ︵", "  ︵"]
        self._ornaments = ["▪", "▫", "▪"]
        self._eye_mode = None
        self.set_interval(1.5, self._tick)
        self._sync_eye_mode()

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

    def _tick(self) -> None:
        self.steam_idx = (self.steam_idx + 1) % len(self._steam)
        elapsed = int(time.time() - config.startTime)
        h, m = elapsed // 3600, (elapsed % 3600) // 60
        self.uptime = f"{h}h {m}m"
        self._sync_eye_mode()
        self.refresh()

    def render(self) -> str:
        w = max(self.size.width - 2, 10)
        marker = self._ornaments[self.steam_idx % len(self._ornaments)]

        if is_sleep_time():
            sleep_art = SLEEP_ART if self.steam_idx % 2 == 0 else SLEEP_ART_B
            return (
                f"{self._header(t('sidebar_hibernation'), marker, w)}\n"
                "\n"
                f"{self._fit_art(sleep_art, w)}\n"
                "\n"
                f"{self._trunc(' ' + t('sidebar_hibernating'), w)}\n"
                f"{self._trunc(' ' + t('sidebar_wake_up', time=config.wake_up_at), w)}\n"
                f"{self._trunc(' ' + t('sidebar_auto_resume'), w)}\n"
                f"\n{separator_medium(w)}\n"
            )

        if bot_state.paused:
            if bot_state.watchdog_paused_until > time.monotonic():
                remaining = max(0, int(bot_state.watchdog_paused_until - time.monotonic()))
                mm, ss = remaining // 60, remaining % 60
                return (
                    f"{self._header(t('sidebar_paused_wd'), marker, w)}\n"
                    "\n"
                    f"{self._trunc(' ' + t('sidebar_wd_active'), w)}\n"
                    f"{self._trunc(' ' + t('sidebar_resuming_in', time=f'{mm:02d}:{ss:02d}'), w)}\n"
                    f"\n{separator_medium(w)}\n"
                )
            return (
                f"{self._header(t('sidebar_paused'), marker, w)}\n"
                "\n"
                f"{self._trunc(' ' + t('sidebar_bot_paused'), w)}\n"
                f"{self._trunc(' ' + t('sidebar_resume_hint'), w)}\n"
                f"\n{separator_medium(w)}\n"
            )

        if bot_state.is_on_coffee_break:
            remaining = max(0, int(bot_state.coffee_break_end_time - time.monotonic()))
            mm, ss = remaining // 60, remaining % 60
            coffee_art = COFFEE_ART if self.steam_idx % 2 == 0 else COFFEE_ART_B

            return (
                f"{self._header(t('sidebar_coffee'), marker, w)}\n"
                "\n"
                f"{self._fit_art(coffee_art, w)}\n"
                "\n"
                f"{self._trunc(' ' + t('sidebar_coffee_desc'), w)}\n"
                f"\n{separator_medium(w)}\n"
                f"{self._trunc('  ' + t('sidebar_resuming_in', time=f'{mm:02d}:{ss:02d}'), w)}\n"
            )

        hunts = sessionData["command_data"].get("hunt", 0) - initialSessionData["command_data"].get("hunt", 0)
        advs = sessionData["command_data"].get("adventure", 0) - initialSessionData["command_data"].get("adventure", 0)
        farms = sessionData["command_data"].get("farm", 0) - initialSessionData["command_data"].get("farm", 0)
        lb_drops = sessionData["loot_data"].get("lootbox_drops", {})
        init_lb_drops = initialSessionData["loot_data"].get("lootbox_drops", {})
        lboxes = sum(v - init_lb_drops.get(k, 0) for k, v in lb_drops.items())
        coins = sessionData["progress_data"].get("coins", 0) - initialSessionData["progress_data"].get("coins", 0)
        xp = sessionData["progress_data"].get("xp", 0) - initialSessionData["progress_data"].get("xp", 0)

        drops = []
        for cat in ["mob_drops", "work_drops", "farm_drops"]:
            for k, v in sessionData["loot_data"].get(cat, {}).items():
                delta = v - initialSessionData["loot_data"].get(cat, {}).get(k, 0)
                if delta > 0:
                    drops.append(f" · {k}: {delta}")

        if drops:
            drops_str = "\n".join(self._trunc(d, w) for d in drops[:5])
        else:
            drops_str = self._trunc(f" · {t('sidebar_no_drops_yet')}", w)

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

        state_str = t("sidebar_active")
        if bot_state.sleepet_mode:
            state_str = t("sidebar_state_sleepet", state=bot_state.sleepet_state or 'init')
        elif bot_state.cardhand_in_progress:
            state_str = t("sidebar_state_cardhand")
        elif bot_state.dungeon_in_progress:
            state_str = t("sidebar_state_dungeon")
        elif bot_state.duel_in_progress:
            state_str = t("sidebar_state_duel", step=bot_state.duel_step or 'init')

        tc_str = ""
        if bot_state.time_cookie_mode:
            if bot_state.tc_end_time > time.monotonic():
                tc_remaining = max(0, int(bot_state.tc_end_time - time.monotonic()))
                tcm, tcs = tc_remaining // 60, tc_remaining % 60
                tc_str = f"{self._trunc(' ' + t('sidebar_tc_remaining', time=f'{tcm:02d}:{tcs:02d}'), w)}\n"
            else:
                tc_str = f"{self._trunc(' ' + t('sidebar_tc_unlimited', qty=bot_state.tc_quantity), w)}\n"

        return (
            f"{self._header(t('sidebar_estado'), marker, w)}\n"
            f"{self._trunc(' ' + t('sidebar_estado') + ': ' + state_str, w)}\n"
            f"{self._trunc(' ' + t('sidebar_sleep_time', time=config.sleep_at), w)}\n"
            f"{self._trunc(' ' + t('sidebar_uptime', time=self.uptime), w)}\n"
            f"{tc_str}"
            f"\n{separator_medium(w)}\n"
            f" {t('sidebar_session_stats')}\n"
            f"{stats_lines}"
            f"\n{separator_medium(w)}\n"
            f" {t('sidebar_latest_drops')}\n"
            f"{drops_str}\n"
        )


class StatusBar(Static):
    """Bottom bar showing queue counts, state, and last command."""

    ALLOW_SELECT = False

    pulse_idx = reactive(0)

    def on_mount(self) -> None:
        self._spinners = ["◐", "◓", "◑", "◒"]
        self.set_interval(1.0, self._tick)

    def _tick(self) -> None:
        self.pulse_idx = (self.pulse_idx + 1) % len(self._spinners)
        self.refresh()

    @staticmethod
    def _normalize_color(value, fallback: str) -> str:
        if value is None:
            return fallback
        if isinstance(value, str):
            return value
        if hasattr(value, "hex"):
            return value.hex
        return fallback

    def _theme_colors(self) -> dict[str, str]:
        theme_info = next((t for t in ORACLE_THEMES if t["name"] == self.app.theme), ORACLE_THEMES[0])
        theme = theme_info.get("theme")
        colors = theme_info["colors"]

        return {
            "primary": self._normalize_color(getattr(theme, "primary", None), colors[0]),
            "secondary": self._normalize_color(getattr(theme, "secondary", None), colors[1]),
            "accent": self._normalize_color(getattr(theme, "accent", None), colors[2]),
            "foreground": self._normalize_color(getattr(theme, "foreground", None), colors[3]),
            "warning": self._normalize_color(getattr(theme, "warning", None), colors[2]),
            "error": self._normalize_color(getattr(theme, "error", None), "#cc0000"),
        }

    def _state(self) -> tuple[str, str]:
        theme_colors = self._theme_colors()
        if is_sleep_time():
            return t("status_sleep"), f"dim {theme_colors['secondary']}"
        if bot_state.paused:
            return t("status_paused"), f"bold {theme_colors['error']}"
        if bot_state.is_on_coffee_break:
            return t("status_idle"), f"bold {theme_colors['warning']}"
        return t("status_online"), f"bold {theme_colors['accent']}"

    def render(self) -> Text:
        theme_colors = self._theme_colors()
        state_text, state_style = self._state()
        last = bot_state.last_sent_command or t("status_no_cmd")
        if len(last) > 32:
            last = last[:29] + "..."

        line = Text()
        line.append(" ")
        line.append(self._spinners[self.pulse_idx], style=f"bold {theme_colors['accent']}")
        line.append(" ")
        line.append(f"HPQ: {len(highPriorityQueue)}", style=f"bold {theme_colors['primary']}")
        line.append("  │  ", style="dim")
        line.append(f"LPQ: {len(lowPriorityQueue)}", style=f"bold {theme_colors['primary']}")
        line.append("  │  ", style="dim")
        line.append(t("status_last_cmd", cmd=last), style=theme_colors["foreground"])
        line.append("  │  ", style="dim")
        line.append(state_text, style=state_style)
        return line
