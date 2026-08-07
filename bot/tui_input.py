"""Input and autocomplete widgets for the Oracle TUI."""

import time

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widgets import Input, Static

import bot.config as config
import options_resolver
from bot.hud import HUD
from bot.locales import t, set_language
from bot.state import (
    add_to_high_priority_queue,
    bot_state,
    highPriorityQueue,
    highPriorityQueueSet,
    lowPriorityQueue,
    lowPriorityQueueSet,
    queue_tc_commands,
    reset_bot_state,
    sessionData,
)


COMMANDS = {
    "/help": "Mostra comandos e atalhos",
    "/start": "Inicia ou retoma o bot",
    "/pause": "Pausa o bot (alias: stop, sleep)",
    "/reset": "Limpa estado e filas",
    "/restart": "Limpa estado e reinicia a conexão com o Discord",
    "/stats": "Exibe estatísticas da sessão",
    "/queue": "Mostra filas HPQ e LPQ",
    "/say": "Envia mensagem ao canal",
    "/tc start": "Ativa modo Time Cookie",
    "/tc stop": "Desativa modo Time Cookie",
    "/sleepet start": "Ativa o Sleepet Mode (loop automatizado de pets)",
    "/sleepet stop": "Desativa o Sleepet Mode",
    "/summer status": "Mostra status do Summer Event",
    "/summer sleepy": "Usa sleepy potion manualmente para task weekly",
    "/g start": "Inicia o gambling (rpg cf)",
    "/g pause": "Pausa o gambling",
    "/theme": "Abre seletor de temas",
    "/config": "Abre o painel de configurações interativo",
    "/status": "Envia status live para Discord + Telegram",
    "/exit": "Encerramento seguro",
    "/language": "Altera o idioma (pt ou en)",
    "/lang": "Altera o idioma (pt ou en)",
}

CONFIG_METADATA = {
    "user_token": "Token da sua conta Discord (mantenha em segredo!)",
    "channel_id": "ID do canal do Discord onde o bot opera",
    "guild_id": "ID do servidor (Guild) — use um servidor privado!",
    "random_interval": "Adiciona atraso aleatório de 1 a 4s entre os comandos",
    "typo_chance": "Probabilidade de simular erro de digitação (0.0 - 1.0)",
    "life_boost_before_adv": "Comprar poção de vida antes de ir na aventura",
    "adventure_area": "Ir para área menor antes de iniciar aventura para receber menos dano",
    "current_area": "Sua área atual (para recuperação de eventos)",
    "zombie_horde_event_response": "O que fazer durante eventos de horda de zumbis",
    "lootbox_type": "Qual lootbox comprar automaticamente",
    "seed": "Qual semente plantar no comando farm",
    "work_command": "Ferramenta/comando de trabalho a ser usado",
    "bankroll": "Seu valor máximo de moedas em mãos",
    "max_losses": "Máximo de perdas consecutivas antes de parar (recomendado 15-30)",
    "initial_step": "Passo inicial para estratégias (recomendado 1-3)",
    "telegram_bot_token": "Token do bot do Telegram (opcional)",
    "telegram_chat_id": "ID do chat do Telegram para alertas (opcional)",
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
    "do_card_hand": "Habilitar minijogo de mão de cartas",
    "do_duel": "Habilitar duelo (duel) automático com o parceiro",
    "win_duel": "Se true, escolhe arma para ganhar duelos. Se false, perde por WO.",
    "duel_partner_id": "ID de Discord do parceiro para mencionar em rpg duel",
    "do_ultr": "ULTR Mode: envia apenas rpg ultr se for eternal (sobrescreve tr)",
    "card_hand_action": "Jogar cartas automaticamente ou apenas notificar",
    "tc_quantity": "Quantidade de cápsulas de tempo (TC) por uso",
    "is_eternal": "Habilitar entrar em dungeons + loop eterno de dragon bite",
    "eternal_tier": "Tier de eternal (t1 a t10)",
    "is_married": "Habilitar funcionalidades de parceiro(a) casado",
    "partner_name": "Nome do parceiro(a) no jogo (se casado)",
    "is_ascended": "Habilitar comportamento específico de jogador ascendido",
    "admin_ids": "IDs extras para controle remoto administrativo separados por vírgula",
    "tc_stop_on": "Eventos separados por vírgula que pausam o uso de TC",
    "sleep_at": "Horário para dormir (formato 24h, ex: 23:00)",
    "wake_up_at": "Horário para acordar (formato 24h, ex: 09:00)",
    "theme": "Tema visual a ser utilizado na interface TUI",
    "pet_adventure_command": "Comando de aventura do pet (ex: 'find epic', 'learn a', 'rpg pet adv find epic')",
    "do_pet": "Habilitar a automação e coleta de aventuras de pets",
    "do_summer": "Ativa automacao completa do evento Summer (surf, tasks, boosts, craft, drink)",
    "summer_surf_strategy": "Estrategia de surf: conservative (menor risco, recomendado) ou aggressive (maior recompensa, mais risco de cair)",
    "summer_drink_choice": "Cor da drink para iniciar o torneio semanal na segunda: blue|green|pink|yellow",
    "summer_use_sleepy_potion": "Habilitar uso automatico de sleepy potion para completar task weekly (avanca 24h do jogo!)",
    "language": "Idioma do bot (pt = português, en = english)",
}


class AutocompleteItem(Static):
    """An individual command item in the autocomplete list.

    Clicking directly executes the command (no extra Enter required).
    """

    ALLOW_SELECT = False

    def __init__(self, command: str, description: str, index: int, parent_dropdown) -> None:
        super().__init__()
        self.command = command
        self.description = description
        self.index = index
        self.parent_dropdown = parent_dropdown
        self.can_focus = False

    def render(self) -> Text:
        """Render with command name and description for better readability."""
        result = Text()
        is_sel = self.has_class("selected")
        if is_sel:
            result.append("▸ ", style="bold")
        else:
            result.append("  ")
        result.append(self.command, style="bold" if is_sel else "")
        result.append(f"  {self.description}", style="dim italic")
        return result

    def on_click(self) -> None:
        """Click = execute the command immediately."""
        self.parent_dropdown.execute_item(self.index)


class AutocompleteDropdown(Static):
    """Dropdown showing command suggestions above the input.

    UX rules:
      - Tab selects the first/next suggestion (autocomplete behavior)
      - Enter on a selected suggestion executes it immediately
      - Enter with no selection but dropdown visible: execute top match
      - Click on any item executes it immediately
    """

    ALLOW_SELECT = False

    items = reactive([], always_update=True)
    selected_idx = reactive(-1)
    _suppressed = False

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
        for idx, cmd in enumerate(self.items):
            desc = COMMANDS.get(cmd, "")
            if not desc and cmd.startswith("/cfg "):
                cfg_key = cmd[5:].strip()
                desc = CONFIG_METADATA.get(cfg_key, "")
            # Try translation
            if desc:
                cmd_base = cmd.lstrip("/").split()[0]
                t_key = f"cmd_{cmd_base}" if not cmd.startswith("/cfg ") else f"cfg_{cfg_key}"
                translated = t(t_key)
                if translated != t_key:
                    desc = translated
            widget = AutocompleteItem(cmd, desc, idx, self)
            widget.classes = "autocomplete-item"
            container.mount(widget)

    def select_item(self, index: int) -> None:
        """Visually select an item (fill input but don't execute)."""
        if 0 <= index < len(self.items):
            chosen = self.items[index]
            cmd_input = self.app.query_one("#command-input", CommandInput)
            cmd_input._suppress_autocomplete = True
            cmd_input.value = chosen
            cmd_input.cursor_position = len(chosen)
            cmd_input._suppress_autocomplete = False
            self.items = []
            cmd_input.focus()

    def execute_item(self, index: int) -> None:
        """Execute a command immediately (click or Enter on selected)."""
        if 0 <= index < len(self.items):
            chosen = self.items[index]
            cmd_input = self.app.query_one("#command-input", CommandInput)
            cmd_input._suppress_autocomplete = True
            self.items = []
            cmd_input.value = chosen
            cmd_input.focus()
            cmd_input.action_submit()
            cmd_input._suppress_autocomplete = False

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
        children = container.query(AutocompleteItem)
        for idx, item in enumerate(children):
            if idx == self.selected_idx:
                item.add_class("selected")
                item.scroll_visible()
            else:
                item.remove_class("selected")


class CommandInput(Input):
    """Stylized command input with history and spinner."""

    spinner_idx = reactive(0)
    is_processing = reactive(False)

    def on_mount(self) -> None:
        self.focus()
        self.placeholder = "OracleCLI | digite /help para comandos..."
        self.history: list[str] = []
        self.history_idx = -1
        self._suppress_autocomplete = False
        self._feedback_timer = None
        self._spinner_timer = None
        self._spinners = ["◐", "◓", "◑", "◒"]

    def _clear_feedback_flash(self) -> None:
        self.remove_class("input-success")
        self.remove_class("input-error")
        self._feedback_timer = None

    def _flash_feedback(self, status: str) -> None:
        if self._feedback_timer is not None:
            self._feedback_timer.stop()
            self._feedback_timer = None
        self.remove_class("input-success")
        self.remove_class("input-error")

        if status == "success":
            self.add_class("input-success")
        else:
            self.add_class("input-error")

        self._feedback_timer = self.set_timer(1.0, self._clear_feedback_flash)

    def _is_accepted_command(self, cmd: str) -> bool:
        cmd_clean = cmd.strip()
        if cmd_clean.startswith("/"):
            cmd_clean = cmd_clean[1:].strip()

        if cmd_clean.lower().startswith("sb "):
            cmd_clean = cmd_clean[3:].strip()

        parts = cmd_clean.split()
        if not parts:
            return False

        base = parts[0].lower()
        if base in ["help", "ajuda", "tutorial", "/help", "?", "play", "start", "resume", "pause", "stop", "sleep", "reset", "restart", "stats", "queue", "theme", "themes", "exit", "quit", "status"]:
            return True
        if base == "say":
            return len(parts) > 1
        if base == "tc":
            return len(parts) > 1 and parts[1].lower() in ["start", "stop", "pause"]
        if base == "sleepet":
            return len(parts) > 1 and parts[1].lower() in ["start", "stop"]
        if base in ["language", "lang"]:
            return len(parts) > 1 and parts[1].lower() in ["pt", "en"]
        if base == "g":
            return len(parts) > 1 and parts[1].lower() in ["start", "stop", "pause"]
        if base.startswith("rpg"):
            return True
        if base == "cfg":
            return len(parts) >= 3
        return False

    def _notify_system(self, message: str, severity: str = "information", timeout: float = 2.5) -> None:
        try:
            self.app.notify(message, title="Sistema", severity=severity, timeout=timeout)
        except Exception:
            pass

    def watch_is_processing(self, is_processing: bool) -> None:
        if is_processing:
            if not self._spinner_timer:
                self._spinner_timer = self.set_interval(0.25, self._tick_spinner)
        else:
            if self._spinner_timer:
                self._spinner_timer.stop()
                self._spinner_timer = None

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
            if event.key == "down":
                dropdown.move_selection(1)
                event.prevent_default()
                return
            if event.key == "tab":
                if dropdown.selected_idx == -1:
                    dropdown.move_selection(1)
                else:
                    dropdown.move_selection(1)
                event.prevent_default()
                return
            if event.key == "enter":
                if dropdown.selected_idx != -1:
                    dropdown.execute_item(dropdown.selected_idx)
                else:
                    dropdown.execute_item(0)
                event.prevent_default()
                return
            if event.key == "escape":
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
        elif event.key == "tab":
            event.prevent_default()

    def watch_value(self, old_value: str, new_value: str) -> None:
        if self._suppress_autocomplete:
            return

        try:
            dropdown = self.app.query_one("#autocomplete-dropdown", AutocompleteDropdown)
        except Exception:
            return

        if new_value.startswith("/"):
            search = new_value.lower()
            if search.startswith("/cfg "):
                key_search = search[5:].strip()
                filtered = []
                for k in CONFIG_METADATA:
                    if k.lower().startswith(key_search):
                        filtered.append(f"/cfg {k}")
                dropdown.items = filtered
            else:
                filtered = [c for c in COMMANDS if c.lower().startswith(search)]
                dropdown.items = filtered
        else:
            dropdown.items = []

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        cmd = event.value.strip()
        self.value = ""
        if not cmd:
            return

        if self._is_accepted_command(cmd):
            self._flash_feedback("success")
        else:
            self._flash_feedback("error")

        self.history.insert(0, cmd)
        self.history_idx = -1
        self.is_processing = True
        await self._process_command(cmd)
        self.is_processing = False
        self.placeholder = "OracleCLI | digite /help para comandos..."

    async def _process_command(self, cmd: str) -> None:
        from bot.tui_modals import HelpModal, ThemeModal, ConfigModal
        from bot.commands import execute_oracle_command

        cmd_clean = cmd.strip()
        if cmd_clean.startswith("/"):
            cmd_clean = cmd_clean[1:].strip()

        if cmd_clean.lower().startswith("sb "):
            cmd_clean = cmd_clean[3:].strip()

        parts = cmd_clean.split()
        if not parts:
            return
        base = parts[0].lower()

        # ── TUI-only commands (require widget/app access) ──
        if base in ["help", "ajuda", "tutorial", "/help", "?"]:
            self.app.push_screen(HelpModal())
            self._notify_system("Ajuda aberta.", severity="information")
            return

        if base in ["config", "configs"]:
            self.app.push_screen(ConfigModal())
            self._notify_system("Painel de configurações aberto.", severity="information")
            return

        if base in ["theme", "themes"]:
            self.app.push_screen(ThemeModal())
            self._notify_system("Seletor de temas aberto.", severity="information")
            return

        if base in ["exit", "quit"]:
            HUD.oracle("Sequência de encerramento seguro iniciada...")
            self._notify_system("Encerrando aplicação...", severity="warning")
            self.app.exit()
            return

        # ── All other commands → shared executor ──
        result = await execute_oracle_command(cmd)
        severity = result.get("severity", "information")
        message = result.get("message", "")
        if message:
            self._notify_system(message, severity=severity)
