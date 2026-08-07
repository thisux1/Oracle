"""
bot/commands.py - Standalone Oracle command execution.

Extracted from tui_input.py so commands can be executed from:
- TUI (CommandInput widget)
- API (dashboard_server.py /api/exec endpoint)
- Headless stdin reader

Each command returns a result dict:
    {"ok": bool, "message": str, "type": str, "severity": str, "data": Any}
"""

import asyncio
import time
from typing import Any

import bot.config as config
from bot.hud import HUD
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


def _parse_command(cmd: str) -> tuple[str, str, list[str]]:
    """Normalize and parse a command string.

    Returns:
        (base, cmd_clean, parts) where:
        - base: lowercase first word (e.g. "say", "tc", "rpg")
        - cmd_clean: command string after stripping "/" and "sb " prefixes
        - parts: split words of cmd_clean
    """
    cmd_clean = cmd.strip()
    if cmd_clean.startswith("/"):
        cmd_clean = cmd_clean[1:].strip()
    if cmd_clean.lower().startswith("sb "):
        cmd_clean = cmd_clean[3:].strip()

    parts = cmd_clean.split()
    base = parts[0].lower() if parts else ""
    return base, cmd_clean, parts


async def execute_oracle_command(cmd: str) -> dict[str, Any]:
    """Execute an Oracle command and return a result dict.

    This function contains all the command logic extracted from the TUI's
    CommandInput._process_command, but without any TUI dependencies (no
    widget references, no modal pushes, no app.notify calls).

    The HUD is used for log output (same as before). The returned dict
    is used by the caller for further action (API response, TUI notification, etc).
    """
    base, cmd_clean, parts = _parse_command(cmd)

    if not base:
        return {"ok": False, "message": "Comando vazio", "type": "error", "severity": "error"}

    # ── Help (returns command list) ──
    if base in ("help", "ajuda", "tutorial", "?"):
        from bot.tui_input import COMMANDS
        return {
            "ok": True,
            "message": "Comandos disponíveis",
            "type": "help",
            "severity": "information",
            "data": COMMANDS,
        }

    # ── Start / Resume ──
    if base in ("play", "start", "resume"):
        bot_state.paused = False
        HUD.oracle("Bot retomado/iniciado manualmente.")
        return {"ok": True, "message": "Bot retomado.", "type": "control", "severity": "information"}

    # ── Pause / Stop ──
    if base in ("pause", "stop", "sleep"):
        bot_state.paused = True
        HUD.oracle("Bot pausado manualmente.")
        return {"ok": True, "message": "Bot pausado.", "type": "control", "severity": "warning"}

    # ── Reset ──
    if base == "reset":
        highPriorityQueue.clear()
        highPriorityQueueSet.clear()
        lowPriorityQueue.clear()
        lowPriorityQueueSet.clear()
        reset_bot_state()
        HUD.oracle("Filas, Estados e Cooldowns RESETADOS. Bot despausado!")
        return {"ok": True, "message": "Filas e estado resetados.", "type": "control", "severity": "warning"}

    # ── Restart ──
    if base == "restart":
        import bot
        HUD.oracle("🔄 Restart solicitado. Limpando estado e reconectando...")
        highPriorityQueue.clear()
        highPriorityQueueSet.clear()
        reset_bot_state()
        if bot.UserBot:
            asyncio.create_task(bot.UserBot.close())
        return {"ok": True, "message": "Reiniciando (reset completo)...", "type": "control", "severity": "warning"}

    # ── Stats ──
    if base == "stats":
        from bot.parsers import format_session_data
        from bot.persistence import get_stats_for_period
        from bot.locales import t

        if len(parts) > 1:
            period_str = parts[1]
            period_data = get_stats_for_period(sessionData, period_str)
            summary = format_session_data(period_data, f"{t('stat_session_title')} ({period_str})")
        else:
            summary = format_session_data(sessionData, t("stat_session_title"))

        for line in summary.split("\n"):
            HUD.oracle(line)

        return {"ok": True, "message": summary, "type": "stats", "severity": "information"}

    # ── Queue ──
    if base == "queue":
        hpq_list = list(highPriorityQueue)
        lpq_list = list(lowPriorityQueue)
        HUD.oracle(f"HPQ ({len(hpq_list)}): {hpq_list}")
        HUD.oracle(f"LPQ ({len(lpq_list)}): {lpq_list}")
        return {
            "ok": True,
            "message": f"HPQ: {len(hpq_list)}, LPQ: {len(lpq_list)}",
            "type": "queue",
            "severity": "information",
            "data": {"hpq": hpq_list, "lpq": lpq_list},
        }

    # ── Say (send message to channel) ──
    if base == "say":
        if len(parts) > 1:
            text_to_say = cmd_clean[len(parts[0]):].strip()
            add_to_high_priority_queue(text_to_say)
            HUD.system(f"Comando manual enviado para a fila: {text_to_say}")
            return {"ok": True, "message": f"Enfileirado: {text_to_say}", "type": "say", "severity": "information"}
        HUD.alert("Uso: say <mensagem>")
        return {"ok": False, "message": "Uso: say <mensagem>", "type": "error", "severity": "error"}

    # ── Time Cookie ──
    if base == "tc":
        if len(parts) > 1 and parts[1].lower() == "start":
            bot_state.time_cookie_mode = True
            bot_state.tc_quantity = config.tc_quantity

            for part in parts[2:]:
                if part.endswith("c") and part[:-1].isdigit():
                    bot_state.tc_quantity = int(part[:-1])
                    break

            for part in parts[2:]:
                if part.endswith("m") and part[:-1].isdigit():
                    mins = int(part[:-1])
                    bot_state.tc_end_time = time.monotonic() + (mins * 60)
                    break
            else:
                bot_state.tc_end_time = 0

            HUD.tc(f"Modo Time Cookie ATIVADO ({bot_state.tc_quantity} cookies/uso).")
            await queue_tc_commands()
            return {
                "ok": True,
                "message": f"Time Cookie ativado ({bot_state.tc_quantity} cookies/uso).",
                "type": "tc",
                "severity": "information",
            }

        if len(parts) > 1 and parts[1].lower() in ("stop", "pause"):
            bot_state.time_cookie_mode = False
            bot_state.tc_end_time = 0
            HUD.system("Modo Time Cookie DESATIVADO.")
            return {"ok": True, "message": "Time Cookie desativado.", "type": "tc", "severity": "warning"}

        HUD.alert("Uso: tc start [Xc] [Xm]  ou  tc stop")
        return {"ok": False, "message": "Uso: tc start [Xc] [Xm]  ou  tc stop", "type": "error", "severity": "error"}

    # ── Gambling / Coinflip ──
    if base == "g":
        if len(parts) > 1 and parts[1].lower() == "start":
            from bot.state import coinflip_strategy
            if coinflip_strategy:
                bot_state.gambling_paused = False
                first_bet = coinflip_strategy.get_bet_command()
                add_to_high_priority_queue(first_bet)
                bot_state.coinflip_pending = True
                HUD.oracle("Gambling/Coinflip iniciado manualmente.")
                return {"ok": True, "message": "Gambling iniciado.", "type": "gambling", "severity": "information"}
            HUD.alert("Estratégia de Coinflip não inicializada. Verifique bankroll nas opções.")
            return {"ok": False, "message": "Estratégia de Coinflip não inicializada.", "type": "error", "severity": "error"}

        if len(parts) > 1 and parts[1].lower() in ("stop", "pause"):
            bot_state.gambling_paused = True
            HUD.oracle("Gambling pausado manualmente.")
            return {"ok": True, "message": "Gambling pausado.", "type": "gambling", "severity": "warning"}

        HUD.alert("Uso: g start  ou  g pause")
        return {"ok": False, "message": "Uso: g start  ou  g pause", "type": "error", "severity": "error"}

    # ── Sleepet Mode ──
    if base == "sleepet":
        if len(parts) > 1 and parts[1].lower() == "start":
            lowPriorityQueue.clear()
            lowPriorityQueueSet.clear()
            bot_state.sleepet_mode = True
            bot_state.sleepet_state = "init"
            bot_state.last_sleepet_cmd_time = time.monotonic()
            HUD.oracle("Sleepet Mode ATIVADO manualmente.")
            return {"ok": True, "message": "Sleepet Mode ativado.", "type": "sleepet", "severity": "information"}

        if len(parts) > 1 and parts[1].lower() == "stop":
            bot_state.sleepet_mode = False
            bot_state.sleepet_state = None
            HUD.oracle("Sleepet Mode DESATIVADO manualmente.")
            return {"ok": True, "message": "Sleepet Mode desativado.", "type": "sleepet", "severity": "warning"}

        HUD.alert("Uso: sleepet start  ou  sleepet stop")
        return {"ok": False, "message": "Uso: sleepet start  ou  sleepet stop", "type": "error", "severity": "error"}

    # ── RPG commands (direct queue injection) ──
    if base.startswith("rpg"):
        highPriorityQueue.append(cmd)
        HUD.command(cmd, priority="HPQ")
        return {"ok": True, "message": f"RPG enfileirado: {cmd}", "type": "rpg", "severity": "information"}

    # ── Config (hot-edit) ──
    if base == "cfg":
        if len(parts) >= 3:
            key, val = parts[1], " ".join(parts[2:])
            config.userOptions[key] = val

            # Synchronize to in-memory config module attributes if they exist
            if hasattr(config, key):
                old_val = getattr(config, key)
                try:
                    if isinstance(old_val, bool):
                        setattr(config, key, val.lower() == "true")
                    elif isinstance(old_val, int):
                        setattr(config, key, int(val))
                    elif isinstance(old_val, float):
                        setattr(config, key, float(val))
                    else:
                        setattr(config, key, val)
                except ValueError:
                    setattr(config, key, val)

            # Save changes to .ini file
            try:
                import options_resolver
                options_resolver.editData(key, val)
                HUD.oracle(f"Configuração '{key}' salva: {val}")
                return {"ok": True, "message": f"Configuração '{key}' salva: {val}", "type": "config", "severity": "information"}
            except Exception as e:
                HUD.alert(f"Erro ao salvar config: {e}")
                return {"ok": False, "message": f"Erro ao salvar config: {e}", "type": "error", "severity": "error"}

        HUD.alert("Uso: cfg <chave> <valor>")
        return {"ok": False, "message": "Uso: cfg <chave> <valor>", "type": "error", "severity": "error"}

    # ── Status (Discord + Telegram) ──
    if base == "status":
        HUD.system("Sending live status to Discord + Telegram...")
        from bot.handlers import trigger_status_command
        asyncio.create_task(trigger_status_command())
        return {"ok": True, "message": "Status enviado.", "type": "status", "severity": "information"}

    # ── Language ──
    if base in ("language", "lang"):
        if len(parts) > 1:
            new_lang = parts[1].lower()
            if new_lang in ("pt", "en"):
                from bot.locales import set_language, t
                set_language(new_lang)
                msg = t("notify_language_changed", lang=new_lang)
                HUD.system(msg)
                return {"ok": True, "message": msg, "type": "language", "severity": "information"}
        return {"ok": False, "message": "Uso: lang pt|en", "type": "error", "severity": "error"}

    # ── TUI-only commands (graceful handling for API callers) ──
    if base in ("theme", "themes", "config", "configs"):
        return {"ok": False, "message": f"Comando '{base}' disponível apenas na TUI.", "type": "tui_only", "severity": "warning"}

    if base in ("exit", "quit"):
        return {"ok": False, "message": "Use /api/bot/stop para parar o bot.", "type": "tui_only", "severity": "warning"}

    # ── Unknown ──
    HUD.alert(f"Comando desconhecido: {cmd}")
    return {"ok": False, "message": f"Comando desconhecido: {cmd}", "type": "error", "severity": "error"}
