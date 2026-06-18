"""
Oracle v3 - Modern Terminal User Interface (TUI)
Complete implementation of the Textual interface and Discord bot hooks.
"""

import re
import asyncio

from rich.text import Text
from textual import events, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import RichLog

import bot.config as config
from bot.client import recreate_user_bot
from bot.hud import HUD
from bot.locales import t
from bot.tui_input import AutocompleteDropdown, CommandInput
from bot.tui_modals import HelpModal, SplashScreen, ConfigModal
from bot.tui_sidebar import EyeWidget, HeaderPane, SidebarPane, StatusBar
from bot.tui_themes import ORACLE_THEMES
from bot.utils import is_sleep_time
from textual.strip import Strip
from textual.selection import Selection
from rich.cells import cell_len


class SelectableRichLog(RichLog):
    """RichLog subclass with text selection explicitly enabled."""

    ALLOW_SELECT = True

    def on_mouse_down(self, event: events.MouseDown) -> None:
        if event.button == 1 and hasattr(self.app, "begin_log_selection"):
            self.app.begin_log_selection()

    def get_selection(self, selection: Selection) -> tuple[str, str] | None:
        text = "\n".join(line.text for line in self.lines)
        return selection.extract(text), "\n"

    def selection_updated(self, selection: Selection | None) -> None:
        self._line_cache.clear()
        self.refresh()

    def render_line(self, y: int) -> Strip:
        scroll_x, scroll_y = self.scroll_offset
        strip = super().render_line(y)

        line_idx = scroll_y + y
        selection = self.text_selection
        if selection is not None:
            select_span = selection.get_span(line_idx)
            if select_span is not None:
                start, end = select_span
                line_text = Text()
                for segment in strip._segments:
                    line_text.append(segment.text, segment.style)

                start_rel = max(0, start - scroll_x)
                if end == -1:
                    end_rel = len(line_text)
                else:
                    end_rel = min(len(line_text), end - scroll_x)

                if start_rel < end_rel:
                    if self.screen is not None:
                        selection_style = self.screen.get_component_rich_style("screen--selection")
                    else:
                        selection_style = "reverse"
                    line_text.stylize(selection_style, start_rel, end_rel)
                    strip = Strip(line_text.render(self.app.console), strip.cell_length)

        return strip.apply_offsets(scroll_x, scroll_y + y)


# ─── Main Oracle App ───
class OracleApp(App):
    """The central Oracle V3 User Interface.

    UX design:
      - Tab never leaves the input field (used for autocomplete only)
      - Sidebar and eye widgets are non-focusable (decorative)
      - Logs are selectable for copy/paste
      - All focus stays on CommandInput
    """

    CSS_PATH = "tui_theme.tcss"
    TITLE = "Oracle V3"

    # Disable default Tab focus navigation entirely.
    # Tab is repurposed for command autocomplete inside CommandInput.
    BINDINGS = [
        ("f1", "toggle_help", t("binding_help")),
        ("f2", "toggle_config", t("binding_config")),
        ("ctrl+shift+c", "copy_selection", t("binding_copy")),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._log_selection_paused = False
        self._text_selected_fired = False
        self._mouse_up_timer = None
        self._safety_timer = None

    def action_toggle_help(self) -> None:
        """F1 shortcut to open help modal."""
        self.push_screen(HelpModal())

    def action_toggle_config(self) -> None:
        """F2 shortcut to open config modal."""
        self.push_screen(ConfigModal())

    def _set_selection_scope(self) -> None:
        selectable_ids = {"log-pane", "command-input"}
        screens = set(self.screen_stack)
        for s in self._installed_screens.values():
            if not isinstance(s, str):
                screens.add(s)
        for screen in screens:
            try:
                for widget in screen.query("*"):
                    widget.ALLOW_SELECT = widget.id in selectable_ids
            except Exception:
                pass

    def _clean_copied_text(self, text: str) -> str:
        """Strip ANSI escape codes, Discord mentions, and markdown to get clean text."""
        if not text:
            return ""
        # Strip ANSI escape sequences
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        text = ansi_escape.sub('', text)

        # Strip Discord mention tags and custom emojis
        text = re.sub(r'<@!?[0-9]+>|<#[0-9]+>|<@&[0-9]+>', '', text)
        text = re.sub(r'<:[^:]+:[0-9]+>', '', text)

        # Strip markdown syntax
        text = re.sub(r'\*\*\*(.*?)\*\*\*', r'\1', text)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'__(.*?)__', r'\1', text)
        text = re.sub(r'_(.*?)_', r'\1', text)
        text = re.sub(r'`(.*?)`', r'\1', text)

        # Strip extra trailing whitespaces per line and clean it up
        lines = [line.rstrip() for line in text.splitlines()]
        return "\n".join(lines).strip()

    def begin_log_selection(self) -> None:
        # Reset state flags
        self._text_selected_fired = False
        if self._mouse_up_timer:
            self._mouse_up_timer.stop()
            self._mouse_up_timer = None
        if self._safety_timer:
            self._safety_timer.stop()
            self._safety_timer = None

        if not self._log_selection_paused:
            self._log_selection_paused = True
            HUD.pause()
            # Set a 5.0 second safety timer to force resume logging if selection is abandoned
            self._safety_timer = self.set_timer(5.0, self.end_log_selection)

    def end_log_selection(self) -> None:
        if self._mouse_up_timer:
            self._mouse_up_timer.stop()
            self._mouse_up_timer = None
        if self._safety_timer:
            self._safety_timer.stop()
            self._safety_timer = None

        if not self._log_selection_paused:
            return
        self._log_selection_paused = False
        HUD.resume()

    def on_text_selected(self, event: events.TextSelected) -> None:
        self._text_selected_fired = True
        if self._mouse_up_timer:
            self._mouse_up_timer.stop()
            self._mouse_up_timer = None

        selected_text = getattr(event, "text", "") or self.screen.get_selected_text()
        if selected_text:
            clean_text = self._clean_copied_text(selected_text)
            if clean_text:
                self.copy_to_clipboard(clean_text)
                self.notify(
                    "Seleção copiada com sucesso!",
                    title="Área de Transferência",
                    severity="info",
                    timeout=1.5
                )
        self.end_log_selection()

    def action_copy_selection(self) -> None:
        try:
            self.screen.action_copy_text()
        except Exception:
            pass
        finally:
            self.end_log_selection()

    def on_mouse_up(self, event: events.MouseUp) -> None:
        if event.button == 1 and self._log_selection_paused:
            # Check after a brief delay if a selection was actually made.
            # If no selection happened (e.g. standard click), resume logging cleanly.
            if self._mouse_up_timer:
                self._mouse_up_timer.stop()
            self._mouse_up_timer = self.set_timer(0.15, self._check_resume_after_mouseup)

    def _check_resume_after_mouseup(self) -> None:
        self._mouse_up_timer = None
        if not self._text_selected_fired:
            self.end_log_selection()

    def compose(self) -> ComposeResult:
        yield HeaderPane(id="header-pane")
        with Horizontal(id="main-container"):
            yield SelectableRichLog(highlight=False, markup=False, wrap=True, id="log-pane")
            with Vertical(id="sidebar-container"):
                eye = EyeWidget(id="eye-widget")
                eye.can_focus = False
                yield eye
                sidebar_scroll = VerticalScroll(id="sidebar-scroll")
                sidebar_scroll.can_focus = False
                with sidebar_scroll:
                    sidebar = SidebarPane(id="sidebar-pane")
                    sidebar.can_focus = False
                    yield sidebar
        status = StatusBar(id="status-bar")
        status.can_focus = False
        yield status

        with Vertical(id="input-container"):
            dropdown = AutocompleteDropdown(id="autocomplete-dropdown")
            dropdown.can_focus = False
            yield dropdown
            yield CommandInput(id="command-input")

    def on_mount(self) -> None:
        for t in ORACLE_THEMES:
            self.register_theme(t["theme"])
        self.theme = config.theme

        self.call_after_refresh(self._set_selection_scope)

        # Log pane: focusable for native text selection
        log_pane = self.query_one("#log-pane", SelectableRichLog)
        log_pane.can_focus = True

        # Header: non-focusable (decorative)
        try:
            self.query_one("#header-pane").can_focus = False
        except Exception:
            pass

        # Sidebar container: non-focusable
        try:
            self.query_one("#sidebar-container").can_focus = False
        except Exception:
            pass

        # Show splash
        self.push_screen(SplashScreen())

        # Hook HUD into RichLog
        def tui_writer(msg: str):
            log_pane.write(Text.from_ansi(msg))

        HUD.tui_callback = tui_writer
        HUD.resume()

        # Start Discord bot worker
        self.start_discord_bot()

    @work(exclusive=True)
    async def start_discord_bot(self) -> None:
        """Main loop that drives connection to Discord and sleep scheduling."""
        await asyncio.sleep(3.5)
        HUD.oracle("Mecanismo TUI do Oracle v3.0 inicializado.")
        HUD.oracle("Núcleo do Oracle online.")

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

            # Reload configuration dynamically
            config.reload_config()

            missing_configs = []
            if not config.userToken:
                missing_configs.append("User Token")
            if not config.GUILD_ID:
                missing_configs.append("Guild ID")
            if not config.channelID:
                missing_configs.append("Channel ID")
                
            if missing_configs:
                HUD.alert(f"ERRO CRÍTICO: Configurações obrigatórias ausentes ({', '.join(missing_configs)})!")
                HUD.system("Por favor, preencha essas informações na guia Config do painel ou no terminal (F2).")
                HUD.system("O bot não pode iniciar sem essas informações. Aguardando alterações...")
                await asyncio.sleep(10)
                continue

            HUD.system("Conectando ao gateway do Discord...")
            try:
                client = recreate_user_bot()
                await client.start(config.userToken)
                retry_delay = 5
            except asyncio.CancelledError:
                raise
            except Exception as e:
                HUD.alert(f"Bot desconectado: {e}")
                HUD.system(f"Tentando reconectar em {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_retry_delay)


async def run_headless() -> None:
    """Main loop that drives connection to Discord and sleep scheduling without TUI (headless)."""
    HUD.resume()
    HUD.oracle("Mecanismo Headless do Oracle v3.0 inicializado.")
    HUD.oracle("Núcleo do Oracle online (Modo Headless).")

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

        # Reload configuration dynamically
        config.reload_config()

        missing_configs = []
        if not config.userToken:
            missing_configs.append("User Token")
        if not config.GUILD_ID:
            missing_configs.append("Guild ID")
        if not config.channelID:
            missing_configs.append("Channel ID")
            
        if missing_configs:
            HUD.alert(f"ERRO CRÍTICO: Configurações obrigatórias ausentes ({', '.join(missing_configs)})!")
            HUD.system("Por favor, preencha essas informações na guia Config do painel ou no terminal (F2).")
            HUD.system("O bot não pode iniciar sem essas informações. Aguardando alterações...")
            await asyncio.sleep(10)
            continue

        HUD.system("Conectando ao gateway do Discord...")
        try:
            client = recreate_user_bot()
            await client.start(config.userToken)
            retry_delay = 5
        except asyncio.CancelledError:
            raise
        except Exception as e:
            HUD.alert(f"Bot desconectado: {e}")
            HUD.system(f"Tentando reconectar em {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_retry_delay)

