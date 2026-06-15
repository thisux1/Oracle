"""Modal and overlay components for the Oracle TUI."""

import os
from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Static, Switch, Select, Input, Button, Label

import bot.config as config
import options_resolver
from bot.hud import HUD
from bot.tui_themes import ORACLE_THEMES


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
            f"[bold {fg}]     O R A C L E   V 3[/]\n"
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

        sleepet_cmds = (
            f"[bold {acc}]MODO SLEEPET (PETS)[/]\n"
            f"[{acc}]──────────────────────────────[/]\n"
            f"[bold {acc}]sleepet start[/]\n"
            f"  [{fg}]Ativa o loop de pets automatizado[/]\n"
            f"[bold {acc}]sleepet stop[/]\n"
            f"  [{fg}]Desativa o loop de pets[/]"
        )

        gambling_cmds = (
            f"[bold {acc}]GAMBLING (COINFLIP)[/]\n"
            f"[{acc}]──────────────────────────────[/]\n"
            f"[bold {acc}]g start[/]\n"
            f"  [{fg}]Ativa o modo gambling (rpg cf)[/]\n"
            f"[bold {acc}]g pause[/] [dim]│[/] [bold {acc}]g stop[/]\n"
            f"  [{fg}]Pausa o modo gambling[/]"
        )

        config_cmds = (
            f"[bold {acc}]CONFIGURAÇÕES[/]\n"
            f"[{acc}]──────────────────────────────[/]\n"
            f"[bold {acc}]config[/]\n"
            f"  [{fg}]Abre o painel de configurações interativo[/]\n"
            f"[bold {acc}]cfg[/] [dim #6b5e4a]<chave> <valor>[/]\n"
            f"  [{fg}]Muda config rápida (ex: cfg do_hunt false)[/]"
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
            f"[bold {fg}]Tab[/]   [{fg}]Autocompletar comando[/]\n"
            f"[bold {fg}]F1[/]    [{fg}]Abrir esta ajuda[/]\n"
            f"[bold {fg}]F2[/]    [{fg}]Abrir configurações interativas[/]\n"
            f"[bold {fg}]Esc[/]   [{fg}]Fechar sobreposição[/]"
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
                Static(sleepet_cmds, classes="help-section"),
                Static(gambling_cmds, classes="help-section"),
                Static(config_cmds, classes="help-section"),
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


class ThemeOptionCard(Static):
    """Individual theme card within the theme selector."""

    def __init__(self, theme_data: dict, index: int, parent_modal) -> None:
        super().__init__()
        self._theme_data = theme_data
        self._index = index
        self._modal = parent_modal
        self.can_focus = False

    def render(self) -> Text:
        t = self._theme_data
        is_selected = self._index == self._modal._idx

        result = Text()
        if is_selected:
            result.append("▸ ", style="bold")
        else:
            result.append("  ")

        result.append(t["label"], style="bold" if is_selected else "dim")
        result.append("  ")
        for c in t["colors"]:
            result.append("██", style=c)
            result.append(" ")
        result.append("\n")
        if is_selected:
            result.append(f"  {t['desc']}", style="dim italic")
        return result

    def on_click(self) -> None:
        self._modal._idx = self._index
        self._modal.action_confirm()


class ThemeModal(ModalScreen):
    """Theme selector with card-based layout and live preview."""

    BINDINGS = [
        ("up", "move_up", "Acima"),
        ("down", "move_down", "Abaixo"),
        ("enter", "confirm", "Confirmar"),
        ("escape", "cancel", "Cancelar"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._prev_theme: str = ""
        self._idx: int = 0

    def compose(self) -> ComposeResult:
        theme_info = next((t for t in ORACLE_THEMES if t["name"] == self.app.theme), ORACLE_THEMES[0])
        acc = theme_info["colors"][2]
        fg = theme_info["colors"][3]

        title = (
            "\n"
            f"[bold {fg}]     T E M A S[/]\n"
            f"[{acc}]     ════════════════════════[/]\n"
        )
        footer = "[dim]↑↓ Navegar   Enter Confirmar   Esc Cancelar[/]"

        body = VerticalScroll(id="theme_body")
        body.can_focus = False

        yield Container(
            Static(title, id="theme_title"),
            body,
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
        self._build_cards()

    def _build_cards(self) -> None:
        """Rebuild all theme cards inside the scrollable body."""
        body = self.query_one("#theme_body", VerticalScroll)
        body.remove_children()
        for i, t in enumerate(ORACLE_THEMES):
            card = ThemeOptionCard(t, i, self)
            card.classes = "theme-option"
            if i == self._idx:
                card.add_class("selected")
            body.mount(card)

    def _update_cards(self) -> None:
        """Update card visual state without full rebuild."""
        body = self.query_one("#theme_body", VerticalScroll)
        cards = list(body.query(ThemeOptionCard))
        for i, card in enumerate(cards):
            if i == self._idx:
                card.add_class("selected")
                card.scroll_visible()
            else:
                card.remove_class("selected")
            card.refresh()

    def _apply_preview(self) -> None:
        self.app.theme = ORACLE_THEMES[self._idx]["name"]
        self._update_cards()

    def action_move_up(self) -> None:
        self._idx = (self._idx - 1) % len(ORACLE_THEMES)
        self._apply_preview()

    def action_move_down(self) -> None:
        self._idx = (self._idx + 1) % len(ORACLE_THEMES)
        self._apply_preview()

    def action_confirm(self) -> None:
        new_theme = ORACLE_THEMES[self._idx]["name"]
        config.theme = new_theme
        options_resolver.editData("theme", new_theme)
        HUD.resume()
        self.dismiss(new_theme)

    def action_cancel(self) -> None:
        self.app.theme = self._prev_theme
        HUD.resume()
        self.dismiss()


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
            c1 = c1.lstrip("#")
            c2 = c2.lstrip("#")
            if len(c1) == 3:
                c1 = "".join(x * 2 for x in c1)
            if len(c2) == 3:
                c2 = "".join(x * 2 for x in c2)
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
            if pos < 0.5:
                return interpolate_color(pri, acc, (pos - 0.25) / 0.25)
            if pos < 0.75:
                return interpolate_color(acc, pri, (pos - 0.5) / 0.25)
            return interpolate_color(pri, sec, (pos - 0.75) / 0.25)

        term_height = self.size.height if self.size.height > 0 else 24
        term_width = self.size.width if self.size.width > 0 else 80

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

        lines = GIANT_EYE_ART.split("\n")
        cropped_lines = [line for line in lines if line.replace(" ", "").replace("\u2800", "") != ""]

        if cropped_lines:
            min_leading = 9999
            max_trailing = 0
            for line in cropped_lines:
                left = 0
                while left < len(line) and line[left] in (" ", "\u2800"):
                    left += 1
                if left < len(line) and left < min_leading:
                    min_leading = left

                right = len(line)
                while right > 0 and line[right - 1] in (" ", "\u2800"):
                    right -= 1
                if right > max_trailing:
                    max_trailing = right

            if min_leading < max_trailing:
                cropped_lines = [line[min_leading:max_trailing] for line in cropped_lines]

        w_art = len(cropped_lines[0]) if cropped_lines else 0
        final_lines = []
        for i, line in enumerate(cropped_lines):
            line_color = get_line_color(i, len(cropped_lines))
            if term_width < w_art:
                crop_left = (w_art - term_width) // 2
                crop_right = crop_left + term_width
                line_content = line[crop_left:crop_right]
            else:
                line_content = line

            styled_line = f"[{line_color}]{line_content}[/]"
            final_lines.append(styled_line)

        if len(final_lines) > available_lines:
            start_idx = (len(final_lines) - available_lines) // 2
            eye_art = "\n".join(final_lines[start_idx : start_idx + available_lines])
        else:
            eye_art = "\n".join(final_lines)

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

        bar_w = min(40, term_width - 12) if term_width > 15 else 10
        filled = int((self.progress / 100) * bar_w)
        bar = "█" * filled + "░" * (bar_w - filled)
        bar_text = f"┃ [{pri}]{bar}[/] {self.progress:3d}% ┃"

        connecting_text = "Conectando…"
        separator = "---------------------"
        skip_text = f"[{fg}][ Pressione qualquer tecla para pular ][/]"

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


CONFIG_SCHEMA = [
    ("🔑 Credenciais", [
        ("user_token", "password", ""),
        ("channel_id", "text", "0"),
        ("guild_id", "text", "0"),
    ]),
    ("⚙️ Geral", [
        ("random_interval", "bool", "true"),
        ("typo_chance", "text", "0.05"),
    ]),
    ("⚔️ Adventure", [
        ("life_boost_before_adv", "dropdown", "none", ["none", "a", "b", "c"]),
        ("adventure_area", "dropdown", "none", ["none"] + [str(i) for i in range(1, 22)]),
        ("current_area", "dropdown", "none", ["none"] + [str(i) for i in range(1, 22)]),
        ("zombie_horde_event_response", "dropdown", "fight", ["fight", "join", "cry"]),
        ("pet_adventure_command", "text", "rpg pet adv learn a"),
    ]),
    ("🌾 Economy / Gambling", [
        ("lootbox_type", "dropdown", "ed lb", ["ed lb", "ep lb", "rare lb", "uncommon lb", "common lb"]),
        ("seed", "dropdown", "carrot", ["carrot", "potato", "bread"]),
        ("work_command", "dropdown", "chainsaw", ["chainsaw", "pickaxe", "bigboat", "greenhouse", "axe", "net", "pickup"]),
        ("bankroll", "text", "1000000000000"),
        ("max_losses", "text", "20"),
        ("initial_step", "text", "1"),
    ]),
    ("📱 Telegram", [
        ("telegram_bot_token", "text", ""),
        ("telegram_chat_id", "text", ""),
    ]),
    ("✅ Features", [
        ("do_hunt", "bool", "true"),
        ("do_adv", "bool", "true"),
        ("do_farm", "bool", "true"),
        ("do_work", "bool", "true"),
        ("do_training", "bool", "true"),
        ("do_daily", "bool", "true"),
        ("do_weekly", "bool", "true"),
        ("do_quest", "bool", "true"),
        ("do_lootbox", "bool", "true"),
        ("do_dungeon", "bool", "true"),
        ("do_card_hand", "bool", "true"),
        ("do_duel", "bool", "false"),
        ("win_duel", "bool", "true"),
        ("do_pet", "bool", "true"),
    ]),
    ("🧪 Advanced", [
        ("do_ultr", "bool", "false"),
        ("card_hand_action", "dropdown", "auto", ["auto", "legacy_auto"]),
        ("tc_quantity", "text", "1"),
        ("is_eternal", "bool", "false"),
        ("eternal_tier", "dropdown", "t1", ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9", "t10"]),
        ("is_married", "bool", "false"),
        ("partner_name", "text", ""),
        ("is_ascended", "bool", "false"),
        ("admin_ids", "text", ""),
        ("duel_partner_id", "text", ""),
        ("tc_stop_on", "text", "dungeon,miniboss"),
        ("sleep_at", "text", "none"),
        ("wake_up_at", "text", "none"),
        ("theme", "dropdown", "dracula", ["cathedral", "dracula", "nord", "monokai", "gruvbox", "catppuccin", "tokyonight", "rosepine", "solarized", "cyberpunk"]),
    ]),
]

def load_example_comments() -> dict[str, str]:
    comments = {
        "do_hunt": "Habilitar caça (hunt) automática",
        "do_adv": "Habilitar aventura (adventure) automática",
        "do_farm": "Habilitar plantação (farm) automática",
        "do_work": "Habilitar trabalho (work) automático",
        "do_training": "Habilitar treino (training) automático",
        "do_daily": "Habilitar resgate diário (daily) automático",
        "do_weekly": "Habilitar resgate semanal (weekly) automático",
        "do_quest": "Habilitar missões (quest) automáticas",
        "do_lootbox": "Habilitar compra de lootbox automática",
        "do_dungeon": "Habilitar dungeons automáticas",
        "do_card_hand": "Habilitar jogo card hand automático",
        "do_duel": "Habilitar duelo (duel) automático com o parceiro",
        "win_duel": "Se true, escolhe arma para ganhar duelos. Se false, não envia arma e perde por WO.",
        "do_pet": "Habilitar a automação e coleta de aventuras de pets",
        "duel_partner_id": "ID de Discord do parceiro para mencionar em rpg duel",
        "is_married": "Habilitar suporte a casamento/casado no Epic RPG",
        "partner_name": "Nome do parceiro(a) no jogo",
        "is_ascended": "Habilitar se o jogador já tiver ascendido no Epic RPG",
        "admin_ids": "IDs extras de Discord autorizados a comandar o bot remotamente",
        "tc_stop_on": "Parar o uso de time cookie caso ocorram estes eventos",
        "eternal_tier": "Tier do eternal (de t1 até t10)",
        "pet_adventure_command": "Comando personalizado de aventura do pet. Ex: 'find epic', 'learn a' ou 'rpg pet adv find epic'",
    }
    
    try:
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(root_dir, "options_example.ini")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line:
                        parts = line.split("=", 1)
                        key = parts[0].strip()
                        val_and_comment = parts[1].split("#", 1)
                        if len(val_and_comment) > 1:
                            comments[key] = val_and_comment[1].strip()
    except Exception:
        pass
    return comments


class ConfigModal(ModalScreen):
    """An interactive configuration form inside a modal overlay."""

    def compose(self) -> ComposeResult:
        theme_info = next((t for t in ORACLE_THEMES if t["name"] == self.app.theme), ORACLE_THEMES[0])
        acc = theme_info["colors"][2]
        fg = theme_info["colors"][3]

        title = (
            "\n"
            f"[bold {fg}]    ⚙️  C O N F I G U R A Ç Õ E S[/]\n"
            f"[{acc}]    ═════════════════════════════════════[/]\n"
        )
        
        body = VerticalScroll(id="config_body")
        body.can_focus = False

        yield Container(
            Static(title, id="config_title"),
            body,
            Static("[dim]Foque ou passe o mouse sobre uma configuração para ver detalhes.[/]", id="config_help_panel"),
            Horizontal(
                Button("Salvar", variant="success", id="config_save_btn"),
                Button("Cancelar", variant="error", id="config_cancel_btn"),
                id="config_buttons_container"
            ),
            Static("[dim]Tab para navegar • Enter no Botão para Executar • Esc para Sair[/]", id="config_footer"),
            id="config_box"
        )

    def on_mount(self) -> None:
        HUD.pause()
        self._initial_values = {}
        
        body = self.query_one("#config_body", VerticalScroll)
        
        for section_title, fields in CONFIG_SCHEMA:
            sec_header = Static(f"\n[bold]{section_title}[/]", classes="config-section-title")
            body.mount(sec_header)
            
            for field in fields:
                key = field[0]
                ftype = field[1]
                default = field[2]
                
                curr_val = config.userOptions.get(key, default)
                self._initial_values[key] = curr_val
                
                if ftype == "bool":
                    switch_val = str(curr_val).lower() == "true"
                    ctrl = Switch(value=switch_val, id=f"cfg_{key}")
                elif ftype == "dropdown":
                    options = field[3]
                    if key == "theme":
                        theme_labels = {
                            "cathedral": "Cathedral",
                            "dracula": "Dracula",
                            "nord": "Nord",
                            "monokai": "Monokai Pro",
                            "gruvbox": "Gruvbox",
                            "catppuccin": "Catppuccin",
                            "tokyonight": "Tokyo Night",
                            "rosepine": "Rosé Pine",
                            "solarized": "Solarized",
                            "cyberpunk": "Cyberpunk"
                        }
                        select_options = [(theme_labels.get(opt, opt), opt) for opt in options]
                    else:
                        select_options = [(opt, opt) for opt in options]
                    select_val = curr_val if curr_val in options else options[0]
                    ctrl = Select(options=select_options, value=select_val, id=f"cfg_{key}", allow_blank=False)
                else:
                    is_pw = (ftype == "password")
                    input_val = curr_val if curr_val != "none" else ""
                    ctrl = Input(value=input_val, password=is_pw, placeholder="none (vazio)", id=f"cfg_{key}")
                
                ctrl_col = Horizontal(
                    ctrl,
                    classes="config-control-container"
                )
                ctrl_col.can_focus = False
                
                row = Horizontal(
                    Label(f"[bold]{key}[/]", classes="config-label"),
                    ctrl_col,
                    classes="config-item",
                    id=f"row_{key}"
                )
                row.can_focus = False
                
                body.mount(row)

    def update_help_text(self, key: str) -> None:
        comments = load_example_comments()
        desc = comments.get(key, "")
        try:
            help_panel = self.query_one("#config_help_panel", Static)
            if desc:
                help_panel.update(f"[bold]{key}[/]: {desc}")
            else:
                help_panel.update("[dim]Foque ou passe o mouse sobre uma configuração para ver detalhes.[/]")
        except Exception:
            pass

    def on_focus(self, event: events.Focus) -> None:
        w = event.widget
        while w:
            if w.id and w.id.startswith("cfg_"):
                key = w.id[4:]
                self.update_help_text(key)
                break
            w = w.parent

    def on_mouse_move(self, event: events.MouseMove) -> None:
        try:
            widget, _ = self.screen.get_widget_at(event.screen_x, event.screen_y)
            while widget:
                if widget.id and widget.id.startswith("cfg_"):
                    key = widget.id[4:]
                    self.update_help_text(key)
                    break
                if widget.id and widget.id.startswith("row_"):
                    key = widget.id[4:]
                    self.update_help_text(key)
                    break
                widget = widget.parent
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "config_save_btn":
            self.action_confirm_save()
        elif event.button.id == "config_cancel_btn":
            HUD.resume()
            self.dismiss()

    def action_confirm_save(self) -> None:
        errors = []
        updates = {}
        
        for section_title, fields in CONFIG_SCHEMA:
            for field in fields:
                key = field[0]
                ftype = field[1]
                
                try:
                    if ftype == "bool":
                        widget = self.query_one(f"#cfg_{key}", Switch)
                        val = "true" if widget.value else "false"
                    elif ftype == "dropdown":
                        widget = self.query_one(f"#cfg_{key}", Select)
                        val = str(widget.value) if widget.value is not None else "none"
                    else:
                        widget = self.query_one(f"#cfg_{key}", Input)
                        val = widget.value.strip()
                        if not val:
                            val = "none"
                except Exception:
                    continue
                
                if key == "user_token" and val == "none":
                    errors.append("O Token do Usuário é obrigatório.")
                if key in ["channel_id", "guild_id"] and val != "none":
                    if not val.isdigit():
                        errors.append(f"O campo '{key}' deve conter apenas números.")
                
                updates[key] = val
        
        if errors:
            self.notify("\n".join(errors), title="Erro de Validação", severity="error")
            return
            
        for key, val in updates.items():
            config.userOptions[key] = val
            
            if hasattr(config, key):
                old_val = getattr(config, key)
                try:
                    if isinstance(old_val, bool):
                        setattr(config, key, val.lower() == "true")
                    elif isinstance(old_val, int):
                        setattr(config, key, int(val) if val.isdigit() else 0)
                    elif isinstance(old_val, float):
                        setattr(config, key, float(val))
                    else:
                        setattr(config, key, val)
                except ValueError:
                    setattr(config, key, val)
            
            try:
                options_resolver.editData(key, val)
            except Exception as e:
                HUD.alert(f"Erro ao salvar config '{key}': {e}")
        
        if "theme" in updates and updates["theme"] != self._initial_values.get("theme"):
            self.app.theme = updates["theme"]
            
        HUD.oracle("Configurações salvas e aplicadas com sucesso.")
        self.notify("Configurações salvas!", title="Sucesso", severity="info")
        HUD.resume()
        self.dismiss()

    def on_key(self, event) -> None:
        if event.key == "escape":
            HUD.resume()
            self.dismiss()
