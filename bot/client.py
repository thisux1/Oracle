import warnings
from typing import Optional
warnings.simplefilter("ignore", category=RuntimeWarning)
import discord
import asyncio
import time
import re
import traceback
from colorama import Fore, Style
from random import randint
from bot.typo import send_with_typo_chance
from bot.hud import HUD, logger
import bot.config as config
from bot.state import (
    bot_state,
    sessionData,
    coinflip_strategy,
    highPriorityQueue,
    highPriorityQueueSet,
    lowPriorityQueue,
    lowPriorityQueueSet,
    add_to_low_priority_queue,
    add_to_high_priority_queue,
    human_delay,
    reset_bot_state,
    queue_tc_commands,
    is_sleepet_command,
    ENCHANT_TIERS_ORDER,
    AUTO_ENCHANT_MAX_ATTEMPTS,
)
from bot.telegram import send_telegram_notification, send_telegram_raw
from bot.captcha import tentar_resolver_captcha, set_client
from bot.handlers import responseResolver
from bot.parsers import format_session_data
from bot.persistence import save_session_data, get_stats_for_period
from bot.locales import t, set_language

# ─── Constants ───
CONFIG_RELOAD_CHECK_INTERVAL = 3.0
WATCHDOG_NO_RESPONSE_LIMIT = 3
WATCHDOG_COOLDOWN_MIN = 45
WATCHDOG_COOLDOWN_MAX = 90
CURIOSITY_TRIGGER_PERCENT = 5
CURIOSITY_COOLDOWN = 300
DUEL_TIMEOUT = 60
COINFLIP_TIMEOUT = 60
CARD_HAND_TIMEOUT = 120
RESPONSE_PENDING_DURATION = 5.0
ANTI_SPAM_WINDOW = 5.0
SLEEPET_STATE_TIMEOUT = 20
TC_REUSE_INTERVAL = 2
DUNGEON_TIMEOUT = 60
AUTO_ENCHANT_TIMEOUT = 60
MAIN_LOOP_SLEEP = 0.5
DISCORD_FILE_SIZE_LIMIT = 8 * 1024 * 1024
TRUNCATED_LOG_SIZE = 5 * 1024 * 1024
COFFEE_BREAK_DURATION_MIN = 300
COFFEE_BREAK_DURATION_MAX = 900
COFFEE_BREAK_INTERVAL_MIN = 3600
COFFEE_BREAK_INTERVAL_MAX = 7200
MAINTENANCE_COOLDOWN_MIN = 45
MAINTENANCE_COOLDOWN_MAX = 90
LOOTBOX_COOLDOWN = 1800
RD_INTERVAL = 120
SAVE_INTERVAL = 300
TELEGRAM_GETUPDATES_TIMEOUT = 10
TELEGRAM_HTTP_TIMEOUT = 15
TELEGRAM_CALLBACK_TIMEOUT = 2
TELEGRAM_POLL_INTERVAL = 3


def parse_neon_recommendation(embed_dict: dict) -> Optional[str]:
    embed_text = str(embed_dict).lower()
    if "expected tc per choice" not in embed_text:
        return None
    text_to_parse = ""
    if "description" in embed_dict and embed_dict["description"]:
        text_to_parse = embed_dict["description"]
    if not text_to_parse and "fields" in embed_dict:
        for field in embed_dict["fields"]:
            field_name = field.get("name", "").lower()
            if "expected tc per choice" in field_name:
                text_to_parse = field.get("value", "")
                break
    if text_to_parse:
        lines = text_to_parse.split('\n')
        for line in lines:
            if "(optimal)" in line.lower():
                if "pass" in line.lower():
                    return "pass"
                card_match = re.search(r'[HDCS][2-9AJQK]|[HDCS]10|EN', line, re.IGNORECASE)
                if card_match:
                    return card_match.group(0).lower()
    return None


class DiscordClient(discord.Client):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Deduplication cache: tracks recently processed message IDs
        # to prevent on_message_edit from re-processing messages
        # already handled by on_message
        self._processed_msg_ids = set()
        self._processed_msg_ids_order = []  # FIFO for eviction
        self._PROCESSED_MSG_CACHE_SIZE = 200
        self._ready_initialized = False  # Guard for one-time on_ready actions

    def _track_processed_message(self, message_id: int) -> None:
        """Add a message ID to the deduplication cache."""
        if message_id in self._processed_msg_ids:
            return
        self._processed_msg_ids.add(message_id)
        self._processed_msg_ids_order.append(message_id)
        # Evict oldest entries if cache is full
        while len(self._processed_msg_ids_order) > self._PROCESSED_MSG_CACHE_SIZE:
            old_id = self._processed_msg_ids_order.pop(0)
            self._processed_msg_ids.discard(old_id)

    async def setup_hook(self):
        self.bg_task = self.loop.create_task(self.my_background_task())

    async def close(self):
        try:
            save_session_data(sessionData)
        except Exception:
            pass
        if hasattr(self, 'bg_task') and self.bg_task and not self.bg_task.done():
            self.bg_task.cancel()
            try:
                await self.bg_task
            except asyncio.CancelledError:
                pass
        if hasattr(self, 'tg_task') and self.tg_task and not self.tg_task.done():
            self.tg_task.cancel()
            try:
                await self.tg_task
            except asyncio.CancelledError:
                pass
        await super().close()

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('----------------------------------------------')
        # Register client reference so captcha module can use wait_for()
        set_client(self)
        
        # One-time initialization (guard against multiple on_ready calls during reconnects)
        if not self._ready_initialized:
            self._ready_initialized = True
            # Add rpg pet summary to queue at startup to sync pet timers
            if config.do_pet:
                add_to_low_priority_queue("rpg pet summary")
                logger.info("Queued 'rpg pet summary' at session start.")
        
        # Cancel existing telegram listener task before creating a new one
        # (on_ready fires on every reconnect, which would otherwise spawn duplicate loops)
        if hasattr(self, 'tg_task') and self.tg_task and not self.tg_task.done():
            self.tg_task.cancel()
            try:
                await self.tg_task
            except asyncio.CancelledError:
                pass
        self.tg_task = self.loop.create_task(self.telegram_listener_loop())
        
        config.userID = self.user.id
        config.userMentionText = f"<@{self.user.id}>"
        if self.user.id not in config.ADMIN_IDS:
            config.ADMIN_IDS.append(self.user.id)
            config.ALLOWED_IDS.append(self.user.id)
        # Resolve username (Epic RPG uses the username/tag for prefixing embeds, not server nicknames)
        await asyncio.sleep(1)
        config.user_name_lower = self.user.name.lower()
        logger.info(f"Using username for Epic RPG filtering: {config.user_name_lower}")

    async def my_background_task(self):
        await self.wait_until_ready()
        
        # Resilient channel resolution
        channel = self.get_channel(config.channelID)
        if not channel:
            try:
                channel = await self.fetch_channel(config.channelID)
                logger.info(f"Channel resolved via fetch_channel: {channel.name if channel else 'None'}")
            except Exception as e:
                logger.warning(f"Could not fetch channel {config.channelID} on startup: {e}")
                channel = None

        import os
        last_config_mtime = 0.0
        try:
            if config.active_profile_path and os.path.exists(config.active_profile_path):
                last_config_mtime = os.path.getmtime(config.active_profile_path)
        except Exception:
            pass
        last_mtime_check_time = 0.0

        last_check = time.monotonic() - 120

        while not self.is_closed():
            # Dynamic recovery of channel if it was not resolved yet or config channel changed
            if not channel or channel.id != config.channelID:
                channel = self.get_channel(config.channelID)
                if not channel:
                    try:
                        channel = await self.fetch_channel(config.channelID)
                    except Exception:
                        pass
            from bot.utils import is_sleep_time
            if is_sleep_time():
                moon_art = f"""
{Fore.LIGHTBLACK_EX}    ─────────────────────────────────────────────
{Fore.LIGHTBLUE_EX}        *   .       .   *     {Fore.CYAN}🌙 SYSTEM HIBERNATING
{Fore.LIGHTBLUE_EX}             *  .  *          {Fore.LIGHTCYAN_EX}Sleep Mode Active
{Fore.LIGHTCYAN_EX}           .---.              {Fore.WHITE}Closed Discord connection
{Fore.LIGHTCYAN_EX}          /     \\  *          {Fore.LIGHTBLACK_EX}Stealth offline status
{Fore.CYAN}         |  🌙   |            {Fore.LIGHTBLUE_EX}Offline: {config.sleep_at} - {config.wake_up_at}
{Fore.BLUE}          '---'               {Fore.GREEN}Safe auto-wakeup scheduled
{Fore.LIGHTBLACK_EX}    ─────────────────────────────────────────────{Style.RESET_ALL}"""
                HUD._write(moon_art)
                await self.close()
                break

            try:
                current_time = time.monotonic()

                # Dynamic config reload check (skip until on_ready completes)
                if self._ready_initialized and current_time - last_mtime_check_time > CONFIG_RELOAD_CHECK_INTERVAL:
                    last_mtime_check_time = current_time
                    try:
                        if config.active_profile_path and os.path.exists(config.active_profile_path):
                            mtime = os.path.getmtime(config.active_profile_path)
                            if mtime > last_config_mtime:
                                last_config_mtime = mtime
                                config.reload_config()
                                HUD.system(f"Configurações recarregadas dinamicamente: {os.path.basename(config.active_profile_path)}")
                    except Exception as reload_err:
                        logger.debug(f"Failed to check config mtime/reload: {reload_err}")

                # Watchdog/Maintenance Auto-Resume Check
                if bot_state.paused and bot_state.watchdog_paused_until > 0 and current_time >= bot_state.watchdog_paused_until:
                    bot_state.paused = False
                    bot_state.watchdog_paused_until = 0
                    bot_state.no_response_count = 0
                    HUD.system("Fim do cooldown do Watchdog/Manutenção. Retomando automaticamente...")
                    await send_telegram_notification("🔄 Cooldown do Watchdog/Manutenção expirou. Tentando retomar atividades...")
                    add_to_low_priority_queue("rpg rd")

                logger.debug(
                    f"States - Paused: {bot_state.paused}, "
                    f"Gambling: {not bot_state.gambling_paused}, "
                    f"Coinflip: {bot_state.coinflip_pending}, "
                    f"Withdraw: {bot_state.awaiting_withdraw}"
                )

                # Stealth: Coffee Breaks
                if bot_state.paused or bot_state.jailed:
                    if current_time > bot_state.next_break_time:
                        bot_state.next_break_time = current_time + randint(COFFEE_BREAK_INTERVAL_MIN, COFFEE_BREAK_INTERVAL_MAX)
                elif (
                    current_time > bot_state.next_break_time
                    and not bot_state.is_on_coffee_break
                ):
                    break_duration = randint(COFFEE_BREAK_DURATION_MIN, COFFEE_BREAK_DURATION_MAX)
                    bot_state.is_on_coffee_break = True
                    bot_state.coffee_break_end_time = time.monotonic() + break_duration
                    
                    coffee_art = f"""
{Fore.LIGHTBLACK_EX}    ─────────────────────────────────────────────
{Fore.YELLOW}             ~ ~ ~            {Fore.CYAN}☕ PAUSA PARA CAFÉ ATIVA
{Fore.YELLOW}            ~ ~ ~             {Fore.LIGHTCYAN_EX}Estado Inativo Furtivo
{Fore.YELLOW}           .------.           {Fore.WHITE}Simulando pausa humana
{Fore.YELLOW}          /  ☕   /|          {Fore.LIGHTBLACK_EX}Filas bloqueadas por segurança
{Fore.YELLOW}         |       | |__        {Fore.YELLOW}Duração: {break_duration/60:.1f}m
{Fore.YELLOW}         |  ☕   |/  /        {Fore.GREEN}Retomando automaticamente
{Fore.YELLOW}          \\_____/___/         {Fore.LIGHTWHITE_EX}Próxima pausa em 1-2h
{Fore.LIGHTBLACK_EX}    ─────────────────────────────────────────────{Style.RESET_ALL}"""
                    HUD._write(coffee_art)
                    
                    await asyncio.sleep(break_duration)
                    bot_state.is_on_coffee_break = False
                    bot_state.next_break_time = time.monotonic() + randint(COFFEE_BREAK_INTERVAL_MIN, COFFEE_BREAK_INTERVAL_MAX)
                    HUD.system("Fim da pausa. Retomando.")

                # Watchdog: Detect expired response_pending (command sent, no Epic RPG reply at all)
                if (
                    bot_state.response_pending_until > 0
                    and current_time > bot_state.response_pending_until
                    and bot_state.last_epic_rpg_channel_message_time < bot_state.last_sent_time
                ):
                    bot_state.no_response_count += 1
                    bot_state.response_pending_until = 0
                    HUD.system(f"Watchdog: Sem resposta do Epic RPG para '{bot_state.last_sent_command}' ({bot_state.no_response_count}/{WATCHDOG_NO_RESPONSE_LIMIT})")

                # Watchdog: Emergency Pause
                if bot_state.no_response_count >= WATCHDOG_NO_RESPONSE_LIMIT:
                    bot_state.paused = True
                    bot_state.no_response_count = 0
                    cooldown_minutes = randint(WATCHDOG_COOLDOWN_MIN, WATCHDOG_COOLDOWN_MAX)
                    bot_state.watchdog_paused_until = current_time + (cooldown_minutes * 60)
                    highPriorityQueue.clear()
                    highPriorityQueueSet.clear()
                    lowPriorityQueue.clear()
                    lowPriorityQueueSet.clear()
                    HUD.alert(f"WATCHDOG: Sem resposta. Pausa de emergência ({cooldown_minutes}m de cooldown)!")
                    await send_telegram_notification(
                        f"🚨 WATCHDOG: Pausa de Emergência ativada por {cooldown_minutes} minutos "
                        "devido à falta de respostas do jogo. Filas limpas. Tentará auto-retomar depois."
                    )
                    continue

                if (
                    not bot_state.paused
                    and not bot_state.jailed
                    and not bot_state.is_on_coffee_break
                ):
                    # Human Curiosity: Random stats check
                    if (
                        not highPriorityQueue
                        and not lowPriorityQueue
                        and (current_time - bot_state.last_curiosity_time) > CURIOSITY_COOLDOWN
                    ):
                        if randint(1, 100) <= CURIOSITY_TRIGGER_PERCENT:
                            curiosity_cmd = ["rpg i", "rpg p", "rpg cd"][
                                randint(0, 2)
                            ]
                            add_to_low_priority_queue(
                                curiosity_cmd, suppress_log=True
                            )
                            bot_state.last_curiosity_time = current_time
                            HUD.system(
                                f"Curioso... checando '{curiosity_cmd}'"
                            )

                    def track_command(command):
                        cmd_clean = command.lower()
                        if cmd_clean.startswith("rpg "):
                            parts = cmd_clean.split()
                            if len(parts) > 1:
                                c_type = parts[1]
                                if c_type in sessionData["command_data"]:
                                    if c_type != "quest":
                                        sessionData["command_data"][c_type] += 1
                                elif c_type == "adv":
                                    sessionData["command_data"]["adventure"] += 1
                                elif c_type in ["chop", "fish", "mine", "pickup", "axe", "net", "pickaxe", "ladder", "boat", "bow", "chainsaw", "bigboat"]:
                                    sessionData["command_data"]["work"] += 1
                        save_session_data(sessionData)

                    if bot_state.duel_in_progress and bot_state.last_duel_time > 0 and current_time - bot_state.last_duel_time > DUEL_TIMEOUT:
                        bot_state.duel_in_progress = False
                        bot_state.duel_step = None
                        bot_state.last_duel_time = 0
                        bot_state.duel_channel_id = 0
                        HUD.system(f"Timeout do Duel ({DUEL_TIMEOUT}s). Filas liberadas.")

                    # Resolve channel to send commands (respecting duel channel if in progress)
                    active_channel = channel
                    if bot_state.duel_in_progress and getattr(bot_state, "duel_channel_id", 0):
                        duel_chan = self.get_channel(bot_state.duel_channel_id)
                        if not duel_chan:
                            try:
                                duel_chan = await self.fetch_channel(bot_state.duel_channel_id)
                            except Exception:
                                pass
                        if duel_chan:
                            active_channel = duel_chan

                    if current_time <= bot_state.minigame_pending_until or current_time <= bot_state.quest_dialog_pending_until:
                        # During a minigame/quest dialog, only allow the answer through HPQ
                        # (answers are plain text like "3", "yes" — never start with "rpg")
                        for cmd in list(highPriorityQueue):
                            if not cmd.lower().startswith("rpg"):
                                target_cmd = cmd
                                await human_delay(1.5, 2.0)
                                if target_cmd in highPriorityQueue:
                                    highPriorityQueue.remove(target_cmd)
                                    highPriorityQueueSet.discard(target_cmd)
                                    HUD.command(target_cmd, "HPQ-MG")
                                    await send_with_typo_chance(active_channel, target_cmd, "HPQ-MG")
                                break
                        # else: wait silently for minigame to resolve
                    elif bot_state.cardhand_in_progress:
                        # Card Hand active — only allow non-rpg HPQ commands (e.g. "pass")
                        # Safety timeout: reset after 120s
                        if current_time - bot_state.cardhand_start_time > CARD_HAND_TIMEOUT:
                            bot_state.cardhand_in_progress = False
                            HUD.system(f"Timeout do Card Hand ({CARD_HAND_TIMEOUT}s). Filas liberadas.")
                        else:
                            for cmd in list(highPriorityQueue):
                                if not cmd.lower().startswith("rpg"):
                                    target_cmd = cmd
                                    await human_delay(1.5, 2.0)
                                    if target_cmd in highPriorityQueue:
                                        highPriorityQueue.remove(target_cmd)
                                        highPriorityQueueSet.discard(target_cmd)
                                        HUD.command(target_cmd, "HPQ-CH")
                                        await send_with_typo_chance(active_channel, target_cmd, "HPQ-CH")
                                    break
                    elif current_time < bot_state.response_pending_until:
                        # Waiting for Epic RPG to respond to previous rpg command.
                        # Only allow non-rpg answers through HPQ (e.g. training answers, event responses).
                        for cmd in list(highPriorityQueue):
                            if not cmd.lower().startswith("rpg"):
                                target_cmd = cmd
                                await human_delay(1.5, 2.0)
                                if target_cmd in highPriorityQueue:
                                    highPriorityQueue.remove(target_cmd)
                                    highPriorityQueueSet.discard(target_cmd)
                                    bot_state.response_pending_until = time.monotonic() + RESPONSE_PENDING_DURATION
                                    HUD.command(target_cmd, "HPQ-RP")
                                    await send_with_typo_chance(active_channel, target_cmd, "HPQ-RP")
                                break
                        # else: wait for response before sending next rpg command
                    elif bot_state.duel_in_progress:
                        # Duel active — only allow non-rpg answers (yes, a/b/c) through HPQ
                        for cmd in list(highPriorityQueue):
                            if not cmd.lower().startswith("rpg"):
                                target_cmd = cmd
                                await human_delay(1.5, 2.0)
                                if target_cmd in highPriorityQueue:
                                    highPriorityQueue.remove(target_cmd)
                                    highPriorityQueueSet.discard(target_cmd)
                                    HUD.command(target_cmd, "HPQ-DL")
                                    await send_with_typo_chance(active_channel, target_cmd, "HPQ-DL")
                                break
                        # else: wait for duel to finish
                    elif highPriorityQueue:
                        if bot_state.auto_enchant_active:
                            allowed_idx = -1
                            enchant_cmd_prefix = f"rpg {bot_state.auto_enchant_tier}"
                            for idx, cmd_candidate in enumerate(highPriorityQueue):
                                cmd_lower = cmd_candidate.lower()
                                if not cmd_lower.startswith("rpg") or cmd_lower.startswith(enchant_cmd_prefix):
                                    allowed_idx = idx
                                    break
                            if allowed_idx == -1:
                                continue
                            cmd = highPriorityQueue.pop(allowed_idx)
                            highPriorityQueueSet.discard(cmd)
                        else:
                            cmd = highPriorityQueue.pop(0)
                            highPriorityQueueSet.discard(cmd)
                        
                        await human_delay(1.5, 2.0)
                        current_time = time.monotonic()
                        if cmd == bot_state.last_sent_command and (current_time - bot_state.last_sent_time) < ANTI_SPAM_WINDOW and not cmd.startswith("rpg cf") and not is_sleepet_command(cmd) and not any(x in cmd.lower() for x in ["enchant", "refine", "transmute", "transcend"]):
                            HUD.system(f"Comando duplicado '{cmd}' ignorado (Anti-Spam).")
                        else:
                            # Set card hand lock BEFORE sending the command
                            if cmd.lower() == "rpg card hand" and config.card_hand_action == "auto":
                                bot_state.cardhand_in_progress = True
                                bot_state.cardhand_first_pass_done = False
                                bot_state.cardhand_start_time = current_time
                                HUD.system("Card Hand iniciado! Filas bloqueadas.")
                            track_command(cmd)
                            bot_state.last_sent_command = cmd
                            bot_state.last_sent_time = current_time
                            if cmd.lower().startswith("rpg cf"):
                                bot_state.last_coinflip_time = current_time
                            if bot_state.auto_enchant_active and (any(x in cmd.lower() for x in ["enchant", "refine", "transmute", "transcend"]) or "withdraw" in cmd.lower()):
                                bot_state.last_auto_enchant_time = current_time
                            if cmd.lower().startswith("rpg"):
                                bot_state.response_pending_until = current_time + RESPONSE_PENDING_DURATION
                            if is_sleepet_command(cmd):
                                bot_state.last_sleepet_cmd_time = current_time
                            HUD.command(cmd, "HPQ")
                            await send_with_typo_chance(active_channel, cmd, "HPQ")
                    elif lowPriorityQueue and bot_state.gambling_paused and not bot_state.duel_in_progress and not bot_state.auto_enchant_active:
                        await human_delay(1.5, 2.5)
                        if (
                            not lowPriorityQueue
                            or highPriorityQueue
                            or bot_state.paused
                            or bot_state.jailed
                            or bot_state.is_on_coffee_break
                            or not bot_state.gambling_paused
                            or bot_state.duel_in_progress
                            or bot_state.auto_enchant_active
                        ):
                            continue
                        cmd = lowPriorityQueue.pop(0)
                        lowPriorityQueueSet.discard(cmd)
                        current_time = time.monotonic()
                        if cmd == bot_state.last_sent_command and (current_time - bot_state.last_sent_time) < ANTI_SPAM_WINDOW and not cmd.startswith("rpg cf") and not is_sleepet_command(cmd) and not any(x in cmd.lower() for x in ["enchant", "refine", "transmute", "transcend"]):
                            HUD.system(f"Comando duplicado '{cmd}' ignorado (Anti-Spam).")
                        else:
                            # Set card hand lock BEFORE sending the command (if queued in LPQ too)
                            if cmd.lower() == "rpg card hand" and config.card_hand_action == "auto":
                                bot_state.cardhand_in_progress = True
                                bot_state.cardhand_first_pass_done = False
                                bot_state.cardhand_start_time = current_time
                                HUD.system("Card Hand iniciado! Filas bloqueadas.")
                            track_command(cmd)
                            bot_state.last_sent_command = cmd
                            bot_state.last_sent_time = current_time
                            if cmd.lower().startswith("rpg cf"):
                                bot_state.last_coinflip_time = current_time
                            if cmd.lower().startswith("rpg"):
                                bot_state.response_pending_until = current_time + RESPONSE_PENDING_DURATION
                            if is_sleepet_command(cmd):
                                bot_state.last_sleepet_cmd_time = current_time
                            HUD.command(cmd, "LPQ")
                            await send_with_typo_chance(active_channel, cmd, "LPQ")
                    else:
                        if bot_state.sleepet_mode:
                            current_time = time.monotonic()
                            if bot_state.sleepet_state in ["init", None]:
                                bot_state.sleepet_state = "waiting_summary"
                                bot_state.last_sleepet_cmd_time = current_time
                                add_to_high_priority_queue("rpg pet summary")
                                HUD.system("[Sleepet] State machine started with summary command.")
                            elif current_time - bot_state.last_sleepet_cmd_time > SLEEPET_STATE_TIMEOUT:
                                HUD.alert(f"[Sleepet] State '{bot_state.sleepet_state}' timed out! Re-syncing with pet summary...")
                                bot_state.sleepet_state = "waiting_summary"
                                bot_state.last_sleepet_cmd_time = current_time
                                add_to_high_priority_queue("rpg pet summary")
                        elif bot_state.time_cookie_mode:
                            if 0 < bot_state.tc_end_time < current_time:
                                bot_state.time_cookie_mode = False
                                bot_state.tc_end_time = 0
                                HUD.system("Modo Time Cookie expirado.")
                                await send_telegram_notification("⏳ Modo Time Cookie desativado automaticamente (tempo esgotado).")
                            elif not highPriorityQueue and not lowPriorityQueue and current_time - bot_state.last_tc_use_time > TC_REUSE_INTERVAL:
                                bot_state.last_tc_use_time = current_time
                                add_to_high_priority_queue(f"rpg use tc {bot_state.tc_quantity}")
                                add_to_low_priority_queue("rpg rd", suppress_log=True)
                                HUD.tc(f"Ciclo: use tc {bot_state.tc_quantity} -> rd")

                    # Coinflip State: timeout safety
                    if bot_state.coinflip_pending and current_time - bot_state.last_coinflip_time > COINFLIP_TIMEOUT:
                        bot_state.gambling_paused = True
                        HUD.alert("Timeout do coinflip (1 min sem resposta). Resgatando estado normal e liberando filas.")
                        await send_telegram_notification("⚠️ *Timeout do Coinflip:* Sem resposta por 1 minuto. Apostas pausadas e filas liberadas.")

                    # Dungeon State: timeout safety
                    if bot_state.dungeon_in_progress and current_time - bot_state.last_dungeon_time > DUNGEON_TIMEOUT:
                        bot_state.dungeon_in_progress = False
                        bot_state.dragon_alive = False
                        HUD.dungeon("Timeout do estado, resetando.")

                    # Auto Enchant: timeout safety
                    if bot_state.auto_enchant_active and current_time - bot_state.last_auto_enchant_time > AUTO_ENCHANT_TIMEOUT:
                        bot_state.auto_enchant_active = False
                        HUD.alert("Timeout do auto-enchant (1 min sem resposta). Resgatando estado normal e liberando filas.")
                        await send_telegram_notification("⚠️ *Timeout do Auto-Enchant:* Sem resposta por 1 minuto. Auto-enchant desativado e filas liberadas.")
                        highPriorityQueue[:] = [c for c in highPriorityQueue if not any(x in c.lower() for x in ["enchant", "refine", "transmute", "transcend", "withdraw"])]
                        highPriorityQueueSet.clear()
                        highPriorityQueueSet.update(highPriorityQueue)

                    # Pet Adventure: auto-claim when timer expires
                    if (
                        config.do_pet
                        and not bot_state.sleepet_mode
                        and bot_state.pet_adventure_return_time > 0
                        and current_time >= bot_state.pet_adventure_return_time
                    ):
                        bot_state.pet_adventure_return_time = 0
                        add_to_low_priority_queue("rpg pet claim")
                        HUD.system("Aventura do pet completa! Resgatando recompensas...")

                    # Periodic pet summary fallback: send every 1.5h to 3h
                    if (
                        config.do_pet
                        and not bot_state.sleepet_mode
                        and current_time >= bot_state.next_pet_summary_check
                    ):
                        bot_state.next_pet_summary_check = current_time + randint(5400, 10800)
                        add_to_low_priority_queue("rpg pet summary")
                        HUD.system("Verificação periódica de pets: enviando rpg pet summary...")

                    if current_time - last_check >= RD_INTERVAL:
                        last_check = current_time
                        add_to_low_priority_queue("rpg rd", suppress_log=True)
                        logger.info("Command rpg rd queued")

                    if current_time - bot_state.last_save_time >= SAVE_INTERVAL:
                        is_hourly = False
                        if current_time - getattr(bot_state, "last_snapshot_time", 0) >= 3600:
                            is_hourly = True
                            bot_state.last_snapshot_time = current_time
                            
                        save_session_data(sessionData, save_snapshot=is_hourly)
                        bot_state.last_save_time = current_time


            except Exception as e:
                logger.error(
                    f"Error in background task: {e}\n{traceback.format_exc()}"
                )
            await asyncio.sleep(MAIN_LOOP_SLEEP)

    async def on_message(self, message):
        # ─── 0. Manual Commands (sb prefix — always processed) ───
        if message.author.id in config.ADMIN_IDS:
            msg_clean = message.content.lower().strip()
            if msg_clean.startswith("sb "):
                cmd = msg_clean[3:].strip()
                if cmd in ["pause", "stop"]:
                    bot_state.paused = True
                    HUD.alert("Bot PAUSADO via comando do Discord.")
                    await message.channel.send("⏸️ **Bot Pausado.**")
                    return
                elif cmd in ["start", "resume"]:
                    bot_state.paused = False
                    bot_state.watchdog_paused_until = 0
                    bot_state.no_response_count = 0
                    HUD.system("Bot RETOMADO via comando do Discord.")
                    await message.channel.send("▶️ **Bot Retomado.**")
                    return
                elif cmd == "sleepet start":
                    lowPriorityQueue.clear()
                    lowPriorityQueueSet.clear()
                    bot_state.sleepet_mode = True
                    bot_state.sleepet_state = "init"
                    bot_state.last_sleepet_cmd_time = time.monotonic()
                    HUD.system("Sleepet Mode ATIVADO via Discord.")
                    await message.channel.send("😴 **Sleepet Mode Ativado. LPQ limpa e loop de pets iniciado!**")
                    return
                elif cmd == "sleepet stop":
                    bot_state.sleepet_mode = False
                    bot_state.sleepet_state = None
                    HUD.system("Sleepet Mode DESATIVADO via Discord.")
                    await message.channel.send("🛑 **Sleepet Mode Desavtivado. Filas normais liberadas.**")
                    return
                elif cmd == "force":
                    await responseResolver(message)
                    HUD.system("Processamento FORÇADO executado.")
                    return
                elif cmd == "reset":
                    highPriorityQueue.clear()
                    highPriorityQueueSet.clear()
                    lowPriorityQueue.clear()
                    lowPriorityQueueSet.clear()
                    reset_bot_state()
                    HUD.system("Filas, Estado e Cooldowns RESETADOS via Discord.")
                    await message.channel.send(
                        "🔄 **Filas, Estados e Cooldowns Resetados. Bot Despausado!**"
                    )
                    return
                # Auto Enchant command check
                parts = cmd.split()
                if len(parts) >= 2 and parts[0] in ["enchant", "refine", "transmute", "transcend"]:
                    if parts[1] == "stop":
                        bot_state.auto_enchant_active = False
                        HUD.system(f"Auto-Enchant {parts[0].upper()} cancelado via Discord.")
                        await message.channel.send(f"🛑 **Auto-Enchant {parts[0].title()} Cancelado.**")
                        return
                    elif len(parts) >= 3:
                        tier = parts[0]
                        target = parts[1].lower()
                        if target not in ["a", "s"]:
                            await message.channel.send("⚠️ O alvo deve ser `a` (armadura) ou `s` (espada).")
                            return
                        
                        target_val_raw = " ".join(parts[2:])
                        target_val = target_val_raw.lower().replace(" ", "").replace("-", "")
                        
                        if target_val not in ENCHANT_TIERS_ORDER:
                            await message.channel.send(f"⚠️ Encantamento desconhecido: `{target_val_raw}`.")
                            return
                        
                        bot_state.auto_enchant_active = True
                        bot_state.auto_enchant_tier = tier
                        bot_state.auto_enchant_target = target
                        bot_state.auto_enchant_target_value = target_val
                        bot_state.auto_enchant_channel_id = config.channelID
                        bot_state.auto_enchant_attempts = 0
                        bot_state.last_auto_enchant_time = time.monotonic()
                        bot_state.auto_enchant_withdrawn = False
                        
                        lowPriorityQueue.clear()
                        lowPriorityQueueSet.clear()
                        
                        HUD.system(f"Auto-Enchant ATIVADO: {tier} {target} para {target_val_raw.upper()}. LPQ limpa.")
                        await message.channel.send(
                            f"🔮 **Auto-Enchant Iniciado!**\n"
                            f"• Tipo: `{tier.upper()}`\n"
                            f"• Alvo: `{'Espada' if target == 's' else 'Armadura'}`\n"
                            f"• Level Desejado: `{target_val_raw.upper()}`\n"
                            f"• LPQ limpa e bloqueada. Comando enviado para HPQ."
                        )
                        
                        add_to_high_priority_queue(f"rpg {tier} {target}")
                        return
                elif cmd.startswith("tc start"):

                    parts = cmd.split()
                    bot_state.time_cookie_mode = True

                    bot_state.tc_quantity = config.tc_quantity
                    for part in parts[2:]:
                        if part.endswith('c') and part[:-1].isdigit():
                            bot_state.tc_quantity = int(part[:-1])
                            break

                    for part in parts[2:]:
                        if part.endswith('m') and part[:-1].isdigit():
                            mins = int(part[:-1])
                            bot_state.tc_end_time = time.monotonic() + (mins * 60)
                            break
                    else:
                        bot_state.tc_end_time = 0

                    HUD.tc(f"Modo Time Cookie ATIVADO ({bot_state.tc_quantity} cookies/uso).")
                    await message.channel.send(f"🍪 **Modo Time Cookie Ativado ({bot_state.tc_quantity}c/uso).**")
                    await queue_tc_commands()
                    return
                elif cmd in ["tc stop", "tc pause"]:
                    bot_state.time_cookie_mode = False
                    bot_state.tc_end_time = 0
                    HUD.system("Modo Time Cookie DESATIVADO.")
                    await message.channel.send("🛑 **Modo Time Cookie Desativado.**")
                    return
                elif cmd == "g start":
                    if coinflip_strategy:
                        bot_state.gambling_paused = False
                        first_bet = coinflip_strategy.get_bet_command()
                        add_to_high_priority_queue(first_bet)
                        bot_state.coinflip_pending = True
                        HUD.system("Gambling ATIVADO via Discord.")
                        await message.channel.send("🎰 **Gambling Ativado.**")
                    else:
                        await message.channel.send("⚠️ Coinflip strategy não inicializada.")
                    return
                elif cmd in ["g stop", "g pause"]:
                    bot_state.gambling_paused = True
                    HUD.system("Gambling PAUSADO via Discord.")
                    await message.channel.send("⏸️ **Gambling Pausado.**")
                    return
                elif cmd == "log":
                    import options_resolver
                    import os
                    import io
                    options_path = getattr(options_resolver, "optionsFilePath", None)
                    if options_path:
                        log_path = options_path.rsplit(".", 1)[0] + ".log"
                        if os.path.exists(log_path):
                            try:
                                file_size = os.path.getsize(log_path)
                                # Discord file limit is 8MB
                                if file_size <= DISCORD_FILE_SIZE_LIMIT:
                                    await message.channel.send(file=discord.File(log_path))
                                else:
                                    with open(log_path, "rb") as f:
                                        f.seek(-TRUNCATED_LOG_SIZE, os.SEEK_END)
                                        log_data = f.read()
                                    stream = io.BytesIO(log_data)
                                    filename = os.path.basename(log_path)
                                    await message.channel.send(
                                        content="⚠️ O arquivo de log original excede 8MB. Enviando os últimos 5MB do log:",
                                        file=discord.File(stream, filename=f"latest_{filename}")
                                    )
                                HUD.system("Arquivo de log enviado para o Discord.")
                            except Exception as exc:
                                await message.channel.send(f"⚠️ Erro ao enviar log: {exc}")
                        else:
                            await message.channel.send("⚠️ Arquivo de log não existe.")
                    else:
                        await message.channel.send("⚠️ Não foi possível determinar o arquivo de opções.")
                    return
                elif cmd in ["ajuda", "tutorial", "help"]:

                    tutorial_msg = (
                        "📚 **Tutorial Oracle v2**\n\n"
                        "**Comandos de Controle:**\n"
                        "• `sb start` / `sb pause`: Inicia ou pausa a execução do bot\n"
                        "• `sb reset`: Limpa todas as filas e reseta variáveis de estado\n"
                        "• `sb tc start [Xc] [m]`: Ativa modo Time Cookie. Ex: `sb tc start 4c 60m` (4 cookies, 60 min)\n"
                        "• `sb tc stop`: Desativa o modo Time Cookie\n"
                        "• `sb g start` / `sb g pause`: Inicia ou pausa o gambling (Fibonacci)\n"
                        "• `sb sleepet start` / `sb sleepet stop`: Inicia ou encerra o loop automático do Sleepet Mode\n"
                        "• `sb <enchant/refine/transmute/transcend> <a/s> <enchant_name>`: Auto-encanta arma (`s`) ou armadura (`a`) até atingir ou superar o nível desejado (ex: `sb refine s godly`)\n"
                        "• `sb <enchant/refine/transmute/transcend> stop`: Interrompe o encantamento automático\n"
                        "• `sb stats [tempo]`: Mostra progresso, loot e status da sessão. Ex: `sb stats 7d` (últimos 7 dias)\n"
                        "• `sb say [texto]`: Envia uma mensagem no canal configurado\n"
                        "• `sb log`: Envia o arquivo .log da sessão atual (ou os últimos 5MB dele)\n\n"
                        "**Configurações (options.ini):**\n"
                        "• `do_hunt`, `do_adv`, `do_farm`, etc: Liga/desliga comandos individuais sem editar o código\n"
                        "• `do_ultr`: Substitui training pela sequência ULTR (rpg ultr, ou rpg ultr → double → attack se não for eternal)\n"
                        "• `is_eternal`: Habilita auto-enter em dungeon e bite loop automático no dragão eternal\n"
                        "• `card_hand_action`: `auto` (joga via IA) ou `notify` (só notifica Telegram pra jogar manual)\n"
                        "• `tc_quantity`: Quantidade padrão de cookies por uso. Sobrescrito via `sb tc start Xc`\n"
                        "• `life_boost_before_adv`: Compra life boost antes de adventure\n"
                        "• `adventure_area` / `current_area`: Troca de área no adv\n"
                        "• `user_id` / `channel_id` / `admin_ids`: IDs fundamentais\n"
                        "• `work_command` / `seed` / `lootbox_type`: Ações padrão\n"
                        "• `is_married` / `is_ascended` / `partner_name`: partner tracking\n"
                        "• `telegram_bot_token` / `chat_id`: Alertas de captcha e prisão\n"
                        "• `random_interval` / `typo_chance`: Anti-detecção humana\n"
                        "• `tc_stop_on`: Desliga TC automaticamente quando cd estiver pronto\n"
                        "• `current_area` / `zombie_horde_event_response`: Eventos\n"
                        "• `bankroll` / `max_losses` / `initial_step`: Gambling (Fibonacci)\n"
                        "• `daysToCloseVoid`: Quantidade de dias para fechamento da área atual (void tr)"
                    )

                    await message.channel.send(tutorial_msg)
                    return
                elif cmd.startswith("stats"):
                    parts = cmd.split()
                    
                    if len(parts) > 1 and parts[1].replace("h","").replace("d","").replace("m","").isdigit():
                        period_str = parts[1]
                        period_data = get_stats_for_period(sessionData, period_str)
                        stats_msg = "```ansi\n" + format_session_data(period_data, f"Dados da Sessão (Último(s) {period_str})") + "\n```"
                    else:
                        stats_msg = "```ansi\n" + format_session_data(sessionData, "Dados da Sessão (Histórico Completo)") + "\n```"
                        
                    await message.channel.send(stats_msg)
                    return
                elif cmd.startswith("say "):
                    text_to_say = msg_clean.split("sb say ")[1]
                    add_to_high_priority_queue(text_to_say)
                    HUD.system(f"Comando remoto enfileirado: {text_to_say}")
                    await message.channel.send(
                        f"🚀 **Enviado para o canal <#{config.channelID}>:** `{text_to_say}`"
                    )
                    return

        # (Watchdog reset moved inside status detection below to respect channel filter)

        # ─── 1. Content Extraction (Embed Vision) ───
        msg_lower = message.content.lower()
        combined_content = msg_lower
        if message.embeds:
            embed = message.embeds[0]
            if embed.description:
                combined_content += " " + embed.description.lower()
            if embed.author and embed.author.name:
                combined_content += " " + embed.author.name.lower()
            if embed.title:
                combined_content += " " + embed.title.lower()
            for field in embed.fields:
                combined_content += (
                    f" {field.name.lower()} {field.value.lower()}"
                )

        content_to_log = combined_content.strip()

        # ─── 2. Channel Filter ───
        is_invite = False
        if message.author.id == config.EPIC_RPG_ID:
            # Invite/challenge patterns that require cross-channel delivery
            invite_keywords = ["will you accept", "do you want to join"]
            has_invite = any(kw in combined_content for kw in invite_keywords)
            user_name_clean = config.user_name_lower.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
            content_clean = combined_content.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
            has_my_name = (config.user_name_lower in combined_content) or (user_name_clean and user_name_clean in content_clean)

            # Case A: New invite addressed to us
            if has_invite and has_my_name:
                is_invite = True
            # Case B: Subsequent message for an active invite in the same channel
            elif bot_state.duel_in_progress and getattr(bot_state, "duel_channel_id", 0) == message.channel.id:
                is_invite = True

        if message.channel.id != config.channelID and not is_invite and not (
            isinstance(message.channel, discord.DMChannel)
            and message.author.id in config.ADMIN_IDS
        ):
            return

        # Forward cardhand image if applicable
        from bot.handlers import check_and_forward_cardhand_image
        await check_and_forward_cardhand_image(message)

        # ─── 3. Status Detection (bypasses pause) ───
        if message.author.id == config.EPIC_RPG_ID:
            # Any Epic RPG message in our channel resets watchdog timers
            if message.channel.id == config.channelID:
                bot_state.last_epic_rpg_channel_message_time = time.monotonic()
                bot_state.response_pending_until = 0
            # Plain text errors for Auto Enchant
            if bot_state.auto_enchant_active and message.channel.id == bot_state.auto_enchant_channel_id:
                if "don't have enough money" in combined_content.lower() or "don't have enough coin" in combined_content.lower():
                    bot_state.no_response_count = 0
                    bot_state.response_pending_until = 0
                    if not bot_state.auto_enchant_withdrawn:
                        bot_state.auto_enchant_withdrawn = True
                        HUD.system("Auto-Enchant: Sem dinheiro suficiente. Tentando sacar...")
                        highPriorityQueue[:] = [c for c in highPriorityQueue if not any(x in c.lower() for x in ["enchant", "refine", "transmute", "transcend", "withdraw"])]
                        add_to_high_priority_queue("rpg withdraw all")
                        add_to_high_priority_queue(f"rpg {bot_state.auto_enchant_tier} {bot_state.auto_enchant_target}")
                        highPriorityQueueSet.clear()
                        highPriorityQueueSet.update(highPriorityQueue)
                        bot_state.last_auto_enchant_time = time.monotonic()
                    else:
                        bot_state.auto_enchant_active = False
                        HUD.alert("Auto-Enchant CANCELADO: Sem dinheiro suficiente mesmo após 'rpg withdraw all'!")
                        await send_telegram_notification("⚠️ *Auto-Enchant Cancelado:* Sem dinheiro suficiente (falha no saque).")
                        highPriorityQueue[:] = [c for c in highPriorityQueue if not any(x in c.lower() for x in ["enchant", "refine", "transmute", "transcend", "withdraw"])]
                        highPriorityQueueSet.clear()
                        highPriorityQueueSet.update(highPriorityQueue)
                    return
                elif "unlocked in the" in combined_content.lower() or "is unlocked in" in combined_content.lower() or "unlocked in" in combined_content.lower():
                    bot_state.no_response_count = 0
                    bot_state.response_pending_until = 0
                    tiers = ["enchant", "refine", "transmute", "transcend"]
                    if bot_state.auto_enchant_tier in tiers:
                        current_idx = tiers.index(bot_state.auto_enchant_tier)
                        if current_idx > 0:
                            new_tier = tiers[current_idx - 1]
                            HUD.system(f"Auto-Enchant: Comando {bot_state.auto_enchant_tier.upper()} bloqueado. Voltando para {new_tier.upper()}...")
                            bot_state.auto_enchant_tier = new_tier
                            highPriorityQueue[:] = [c for c in highPriorityQueue if not any(x in c.lower() for x in ["enchant", "refine", "transmute", "transcend", "withdraw"])]
                            add_to_high_priority_queue(f"rpg {bot_state.auto_enchant_tier} {bot_state.auto_enchant_target}")
                            highPriorityQueueSet.clear()
                            highPriorityQueueSet.update(highPriorityQueue)
                            bot_state.last_auto_enchant_time = time.monotonic()
                        else:
                            bot_state.auto_enchant_active = False
                            HUD.alert("Auto-Enchant CANCELADO: Comando base 'enchant' bloqueado!")
                            await send_telegram_notification("⚠️ *Auto-Enchant Cancelado:* Comando base 'enchant' bloqueado!")
                            highPriorityQueue[:] = [c for c in highPriorityQueue if not any(x in c.lower() for x in ["enchant", "refine", "transmute", "transcend", "withdraw"])]
                            highPriorityQueueSet.clear()
                            highPriorityQueueSet.update(highPriorityQueue)
                    return
                elif "don't have a bank account" in combined_content.lower():
                    bot_state.no_response_count = 0
                    bot_state.response_pending_until = 0
                    bot_state.auto_enchant_active = False
                    HUD.alert("Auto-Enchant CANCELADO: Conta bancária não encontrada!")
                    await send_telegram_notification("⚠️ *Auto-Enchant Cancelado:* Sem conta bancária.")
                    highPriorityQueue[:] = [c for c in highPriorityQueue if not any(x in c.lower() for x in ["enchant", "refine", "transmute", "transcend", "withdraw"])]
                    highPriorityQueueSet.clear()
                    highPriorityQueueSet.update(highPriorityQueue)
                    return

            # Maintenance Detection
            if any(x in combined_content for x in ["maintenance", "manutenção"]):
                if not bot_state.paused:
                    bot_state.paused = True
                    bot_state.no_response_count = 0
                    maint_cooldown_minutes = randint(MAINTENANCE_COOLDOWN_MIN, MAINTENANCE_COOLDOWN_MAX)
                    bot_state.watchdog_paused_until = time.monotonic() + (maint_cooldown_minutes * 60)
                    highPriorityQueue.clear()
                    highPriorityQueueSet.clear()
                    lowPriorityQueue.clear()
                    lowPriorityQueueSet.clear()
                    HUD.alert(f"MANUTENÇÃO DETECTADA! Bot pausado por segurança ({maint_cooldown_minutes}m de cooldown).")
                    await send_telegram_notification(
                        f"🛠️ EPIC RPG em Manutenção! O bot foi pausado automaticamente por {maint_cooldown_minutes} minutos e tentará retomar atividades depois."
                    )
                return

            # Verify if this message is for us to reset watchdog/pending timers
            is_for_us = False
            if message.reference:
                if message.reference.resolved:
                    ref = message.reference.resolved
                    if hasattr(ref, "author") and ref.author.id == config.userID:
                        is_for_us = True
                if not is_for_us and message.reference.message_id in bot_state.sent_message_ids:
                    is_for_us = True
            
            if not is_for_us:
                from bot.handlers import check_user_matches
                embed_dict = message.embeds[0].to_dict() if message.embeds else None
                user_name_clean = config.user_name_lower.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
                content_clean = combined_content.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
                
                is_for_us = check_user_matches(embed_dict, config.user_name_lower, config.userID) or \
                            (config.user_name_lower and config.user_name_lower in combined_content) or \
                            (user_name_clean and user_name_clean in content_clean) or \
                            str(config.userID) in combined_content

            # Debug logging for auto-enchant diagnosis
            if bot_state.auto_enchant_active:
                logger.info(f"[AE-DEBUG] is_for_us={is_for_us}, channel_match={message.channel.id == bot_state.auto_enchant_channel_id}, has_embeds={bool(message.embeds)}, content_preview={repr(combined_content[:200])}")

            if is_for_us:
                bot_state.no_response_count = 0
                bot_state.response_pending_until = 0
                if bot_state.pending_lootbox_buy and "successfully bought" in combined_content and "lootbox" in combined_content:
                    HUD.system(f"Lootbox ({bot_state.pending_lootbox_buy}) comprada com sucesso!")
                    bot_state.pending_lootbox_buy = None
                    bot_state.lootbox_fallback_triggered = False

                if bot_state.pending_life_boost_buy and (
                    ("successfully bought" in combined_content and "life boost" in combined_content)
                    or "already have a life boost" in combined_content
                ):
                    if "already have a life boost" in combined_content:
                        HUD.system(f"Life Boost ({bot_state.pending_life_boost_buy}) já ativo!")
                    else:
                        HUD.system(f"Life Boost ({bot_state.pending_life_boost_buy}) comprado com sucesso!")
                    bot_state.pending_life_boost_buy = None
                    bot_state.life_boost_fallback_triggered = False

                # Auto Enchant Check
                if bot_state.auto_enchant_active and message.channel.id == bot_state.auto_enchant_channel_id:
                    match = re.search(r'~-~>\s*([^<]+?)\s*<~-~', combined_content)
                    logger.info(f"[AE-DEBUG] Regex match={match}, combined_content_full={repr(combined_content)}")
                    if match:
                        rolled_name = match.group(1).replace("*", "").replace("_", "").strip()
                        rolled_normalized = rolled_name.lower().replace(" ", "").replace("-", "")
                        
                        rolled_idx = ENCHANT_TIERS_ORDER.index(rolled_normalized) if rolled_normalized in ENCHANT_TIERS_ORDER else -1
                        target_idx = ENCHANT_TIERS_ORDER.index(bot_state.auto_enchant_target_value) if bot_state.auto_enchant_target_value in ENCHANT_TIERS_ORDER else -1
                        logger.info(f"[AE-DEBUG] rolled='{rolled_normalized}' idx={rolled_idx}, target='{bot_state.auto_enchant_target_value}' idx={target_idx}")
                        
                        if rolled_idx == -1 or target_idx == -1:
                            bot_state.auto_enchant_active = False
                            HUD.alert(f"Auto-Enchant CANCELADO: Encantamento inválido ou desconhecido detectado (rolado: {rolled_normalized}, alvo: {bot_state.auto_enchant_target_value})")
                            await send_telegram_notification(f"⚠️ *Auto-Enchant Cancelado:* Encantamento desconhecido detectado (rolado: {rolled_name})")
                            highPriorityQueue[:] = [c for c in highPriorityQueue if not any(x in c.lower() for x in ["enchant", "refine", "transmute", "transcend", "withdraw"])]
                            highPriorityQueueSet.clear()
                            highPriorityQueueSet.update(highPriorityQueue)
                        elif rolled_idx >= target_idx:
                            bot_state.auto_enchant_active = False
                            HUD.system(f"Auto-Enchant SUCESSO! Rolado: {rolled_name.upper()} (Alvo era: {bot_state.auto_enchant_target_value.upper()})")
                            await send_telegram_notification(
                                f"✨ *Auto-Enchant SUCESSO!*\n"
                                f"• Alvo: `{bot_state.auto_enchant_target_value.upper()}`\n"
                                f"• Rolado: `{rolled_name.upper()}`\n"
                                f"• Equipamento: `{'Espada' if bot_state.auto_enchant_target == 's' else 'Armadura'}`"
                            )
                            highPriorityQueue[:] = [c for c in highPriorityQueue if not any(x in c.lower() for x in ["enchant", "refine", "transmute", "transcend", "withdraw"])]
                            highPriorityQueueSet.clear()
                            highPriorityQueueSet.update(highPriorityQueue)
                        else:
                            bot_state.auto_enchant_attempts += 1
                            HUD.system(f"Auto-Enchant: Rolado {rolled_name.upper()}, tentativa #{bot_state.auto_enchant_attempts}. Tentando novamente...")
                            if bot_state.auto_enchant_attempts >= AUTO_ENCHANT_MAX_ATTEMPTS:
                                bot_state.auto_enchant_active = False
                                HUD.alert(f"Auto-Enchant CANCELADO: Número máximo de tentativas ({AUTO_ENCHANT_MAX_ATTEMPTS}) atingido!")
                                await send_telegram_notification(f"⚠️ *Auto-Enchant Cancelado:* Número máximo de tentativas ({AUTO_ENCHANT_MAX_ATTEMPTS}) atingido!")
                                highPriorityQueue[:] = [c for c in highPriorityQueue if not any(x in c.lower() for x in ["enchant", "refine", "transmute", "transcend", "withdraw"])]
                                highPriorityQueueSet.clear()
                                highPriorityQueueSet.update(highPriorityQueue)
                            else:
                                bot_state.last_auto_enchant_time = time.monotonic()
                                highPriorityQueue[:] = [c for c in highPriorityQueue if not any(x in c.lower() for x in ["enchant", "refine", "transmute", "transcend", "withdraw"])]
                                add_to_high_priority_queue(f"rpg {bot_state.auto_enchant_tier} {bot_state.auto_enchant_target}")
                                highPriorityQueueSet.clear()
                                highPriorityQueueSet.update(highPriorityQueue)
                        return


            # Captcha Detection
            if (
                ("check you are actually playing" in combined_content
                 or "stop there" in combined_content)
                and (str(config.userID) in combined_content)
            ):
                bot_state.paused = True
                HUD.alert("CAPTCHA DETECTADO! Bot pausado por segurança.")
                sessionData["misc"]["guard_events"] += 1
                highPriorityQueue.clear()
                highPriorityQueueSet.clear()
                lowPriorityQueue.clear()
                lowPriorityQueueSet.clear()
                if not bot_state.captcha_pending:
                    bot_state.captcha_pending = True
                    # Save captcha image BEFORE starting the resolver
                    if message.attachments:
                        from bot.captcha import save_and_crop_attachment
                        await save_and_crop_attachment(
                            message.attachments[0], out_path='epic_guard.png'
                        )
                    bot_state.captcha_task = asyncio.create_task(
                        tentar_resolver_captcha(message)
                    )
                return

            # Jail Detection
            user_name_clean = config.user_name_lower.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
            content_clean = combined_content.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()

            if (
                ("is now in the jail" in combined_content
                 or "is now in the adventure jail" in combined_content)
                and (config.user_name_lower and (config.user_name_lower in combined_content or (user_name_clean and user_name_clean in content_clean)))
            ):
                bot_state.jailed = True
                bot_state.paused = True
                HUD.alert("PRISÃO DETECTADA! Automação suspensa.")
                await send_telegram_notification(
                    "🚨 BOT PRESO! Captcha falhou ou expirou. "
                    "Intervenção manual necessária."
                )
                return

            # Jail Feedback Detection (immediate reply, no username needed)
            # Epic RPG replies with "you are in the jail" when you try any
            # command while jailed. This catches the case where the bot
            # was already jailed before startup or the jail event was missed.
            if (
                "you are in the jail" in combined_content
                or "you are in the adventure jail" in combined_content
                or "use the command `jail`" in combined_content
            ) and not bot_state.jailed:
                bot_state.jailed = True
                bot_state.paused = True
                HUD.alert("PRISÃO DETECTADA (feedback imediato)! Automação suspensa.")
                await send_telegram_notification(
                    "🚨 BOT PRESO! Detectado via feedback do Epic RPG. "
                    "Intervenção manual necessária."
                )
                # Also start jail interaction immediately
                add_to_high_priority_queue("rpg jail")
                return

            # Freedom Detection
            if any(
                x in combined_content
                for x in [
                    "is no longer in the jail",
                    "fine, i will let you go",
                    "you are free",
                    "everything seems fine",
                    "everything looks fine",
                ]
            ):
                has_username = config.user_name_lower and (config.user_name_lower in combined_content or (user_name_clean and user_name_clean in content_clean))
                is_our_pending = bot_state.captcha_pending or bot_state.jailed
                if has_username or is_our_pending:
                    bot_state.jailed = False
                    bot_state.paused = False
                    bot_state.captcha_pending = False
                    HUD.system("Liberdade detectada! Retomando automação.")
                    return

            # Profile detection (update bankroll)
            is_profile = False
            if "— profile" in combined_content:
                if (config.user_name_lower and config.user_name_lower in combined_content) or (user_name_clean and user_name_clean in content_clean):
                    is_profile = True
            if is_profile:
                clean_content_for_profile = re.sub(r'<:[a-zA-Z0-9_]+:\d+>', '', combined_content)
                coins_match = re.search(r"coins:\s*([\d,]+)", clean_content_for_profile)
                bank_match = re.search(r"bank:\s*([\d,]+)", clean_content_for_profile)
                if coins_match or bank_match:
                    coins = int(coins_match.group(1).replace(",", "")) if coins_match else 0
                    bank = int(bank_match.group(1).replace(",", "")) if bank_match else 0
                    total_balance = coins + bank
                    if coinflip_strategy:
                        coinflip_strategy.bankroll = total_balance
                        coinflip_strategy.update_base_unit()
                        HUD.system(f"Saldo atualizado via perfil: {total_balance:,} moedas")
                return

            # Jail Interaction (processed even when paused)
            if bot_state.jailed:
                if (
                    "you are in the **jail**" in combined_content
                    or "use the command `jail`" in combined_content
                ):
                    add_to_high_priority_queue("rpg jail")
                    logger.info("Sending rpg jail command due to jail")
                    return
                elif (
                    "what will you do?" in combined_content
                    or "protest" in combined_content
                ):
                    add_to_high_priority_queue("protest")
                    logger.info("Sending protest command due to jail")
                    return

            if bot_state.time_cookie_mode and "you don't have that item" in combined_content:
                bot_state.time_cookie_mode = False
                bot_state.tc_end_time = 0
                HUD.alert("Time Cookies esgotados! Modo TC desativado.")
                await send_telegram_notification("🚨 Fim dos Time Cookies! Modo Time Cookie desativado automaticamente.")
                return

            # Financial & Quest Error Handling
            if bot_state.pending_trade_letter and (
                "don't have enough" in combined_content
                or "did not unlock area" in combined_content
            ):
                letters = ["a", "b", "c", "d", "e", "f"]
                try:
                    idx = letters.index(bot_state.pending_trade_letter)
                    if idx < len(letters) - 1:
                        next_letter = letters[idx + 1]
                        bot_state.pending_trade_letter = next_letter
                        add_to_low_priority_queue(f"rpg trade {next_letter} 1")
                        HUD.system(
                            f"Troca {letters[idx]} falhou. "
                            f"Tentando '{next_letter}'..."
                        )
                    else:
                        bot_state.pending_trade_letter = None
                        HUD.alert("Todas as opções de troca (A-F) falharam.")
                except ValueError:
                    bot_state.pending_trade_letter = None

            if bot_state.pending_trade_letter and (
                "our trade is done then" in combined_content
            ):
                bot_state.pending_trade_letter = None
                HUD.system("Quest de Troca Concluída com Sucesso!")

            if (
                "don't have enough money" in combined_content
                or "don't have a bank account" in combined_content
            ):

                if bot_state.pending_lootbox_buy and bot_state.has_bank_account and not bot_state.lootbox_fallback_triggered:

                    bot_state.lootbox_fallback_triggered = True
                    HUD.system(
                        f"Falta de dinheiro detectada ao comprar lootbox ({bot_state.pending_lootbox_buy}). "
                        f"Tentando fallback: withdraw 420666..."
                    )
                    add_to_high_priority_queue("rpg withdraw 420666")
                    add_to_high_priority_queue(f"rpg buy {bot_state.pending_lootbox_buy}")
                    add_to_high_priority_queue("rpg deposit all")
                    return

                if bot_state.pending_life_boost_buy and bot_state.has_bank_account and not bot_state.life_boost_fallback_triggered:

                    bot_state.life_boost_fallback_triggered = True
                    HUD.system(
                        f"Falta de dinheiro detectada ao comprar life boost ({bot_state.pending_life_boost_buy}). "
                        f"Tentando fallback: withdraw all..."
                    )
                    add_to_high_priority_queue("rpg withdraw all")
                    add_to_high_priority_queue(f"rpg buy life boost {bot_state.pending_life_boost_buy}")
                    add_to_high_priority_queue("rpg deposit all")
                    return

                bot_state.lootbox_cooldown_until = time.monotonic() + LOOTBOX_COOLDOWN
                if "don't have a bank account" in combined_content:
                    bot_state.has_bank_account = False
                HUD.alert(
                    "Erro Financeiro! Compra de lootbox suspensa por 30 minutos."
                )
                bot_state.pending_lootbox_buy = None
                bot_state.lootbox_fallback_triggered = False
                bot_state.pending_life_boost_buy = None
                bot_state.life_boost_fallback_triggered = False
                for cmd in list(highPriorityQueue):
                    if any(x in cmd for x in ["buy", "withdraw", "deposit"]):
                        highPriorityQueue.remove(cmd)
                        highPriorityQueueSet.discard(cmd)
                for cmd in list(lowPriorityQueue):
                    if any(x in cmd for x in ["buy", "withdraw", "deposit"]):
                        lowPriorityQueue.remove(cmd)
                        lowPriorityQueueSet.discard(cmd)
                return

        # Donut Engine: Void Area Question
        if (
            "how many days are left for this area to close?" in combined_content
            and message.author.id == config.EPIC_RPG_ID
        ):
            days = config.userOptions.get("daysToCloseVoid", "3")
            add_to_high_priority_queue(days)
            HUD.system(f"Respondida pergunta do Void: {days}")
            return

        # ─── 4. Pause Gatekeeper ───
        if bot_state.paused and not (
            message.author.id in config.ADMIN_IDS
            and message.content.lower().startswith("sb ")
        ):
            return

        # ─── 5. Quest Master: NPC Interaction ───
        if "are you looking for a quest?" in combined_content and (
            message.author.id == config.EPIC_RPG_ID
            or "EPIC NPC" in message.author.name
        ):
            # Parse target username inside ** and verify exact match to avoid similar names (e.g. thix_._ vs thix_._2)
            bold_names = []
            if message.content:
                bold_names.extend(re.findall(r"\*\*(.*?)\*\*", message.content))
            for embed in message.embeds:
                emb_dict = embed.to_dict()
                if "description" in emb_dict and emb_dict["description"]:
                    bold_names.extend(re.findall(r"\*\*(.*?)\*\*", emb_dict["description"]))
                if "fields" in emb_dict:
                    for field in emb_dict["fields"]:
                        if field.get("value"):
                            bold_names.extend(re.findall(r"\*\*(.*?)\*\*", field["value"]))
            
            bold_names_clean = [n.strip().lower() for n in bold_names if n]
            if config.user_name_lower not in bold_names_clean:
                logger.debug(f"Quest ignored (username not in bold elements): {bold_names_clean}")
                return

            HUD.system("Diálogo de NPC detectado. Analisando quest...")
            bot_state.quest_dialog_pending_until = time.monotonic() + 15
            if any(
                x in combined_content
                for x in ["arena", "miniboss", "guild raid"]
            ):
                add_to_high_priority_queue("no")
                HUD.alert("Quest Recusada (Tipo Manual/Chato).")
                return

            add_to_high_priority_queue("yes")
            HUD.system("Quest Aceita. Iniciando estratégia...")

            clean_quest = combined_content.replace('*', '').replace('_', '').replace('`', '')
            craft_match = re.search(
                r"craft (\d+) ([a-z\s]+)", clean_quest
            )
            if craft_match:
                qty, item = craft_match.groups()
                add_to_low_priority_queue(f"rpg craft {item.strip()} {qty}")
                return

            if "trading quest" in clean_quest:
                bot_state.pending_trade_letter = "a"
                add_to_low_priority_queue(
                    "rpg trade a 1", suppress_log=True
                )
                HUD.system("Quest de troca aceita. Tentando 'a'...")
                return

            gamble_match = re.search(
                r"get at least ([\d,]+) coins with minigames", clean_quest
            )
            if gamble_match:
                goal = int(gamble_match.group(1).replace(",", ""))
                bot_state.gamble_quest_goal = goal
                bot_state.gamble_quest_current = 0
                bot_state.gambling_paused = False
                first_bet = coinflip_strategy.get_bet_command()
                add_to_high_priority_queue(first_bet)
                bot_state.coinflip_pending = True
                HUD.system(f"Modo Cassino Ativo. Meta: {goal:,}. Primeira aposta enviada para a fila.")
                return

            HUD.system("Quest aceita (Tipo Hunt/Adventure passiva).")
            return

        # ─── 5.5 Active Quest Detection ───
        if "if you don't want this quest anymore" in combined_content and message.author.id == config.EPIC_RPG_ID:
            clean_quest = combined_content.replace('*', '').replace('_', '').replace('`', '')
            craft_match = re.search(r"craft (\d+) ([a-z\s]+) \(\d+/\d+\)", clean_quest)
            if craft_match:
                qty, item = craft_match.groups()
                add_to_low_priority_queue(f"rpg craft {item.strip()} {qty}")
                HUD.system(f"Quest de Craft Ativa detectada: craft {qty} {item.strip()}")
                return

            if "trading quest" in clean_quest:
                if not bot_state.pending_trade_letter:
                    bot_state.pending_trade_letter = "a"
                    add_to_low_priority_queue("rpg trade a 1", suppress_log=True)
                    HUD.system("Quest de Troca ativa detectada. Tentando 'a'...")
                return

            gamble_match = re.search(r"get at least ([\d,]+) coins with minigames", clean_quest)
            if gamble_match:
                goal = int(gamble_match.group(1).replace(",", ""))
                if bot_state.gamble_quest_goal == 0:
                    bot_state.gamble_quest_goal = goal
                    bot_state.gamble_quest_current = 0
                    bot_state.gambling_paused = False
                    first_bet = coinflip_strategy.get_bet_command()
                    add_to_high_priority_queue(first_bet)
                    bot_state.coinflip_pending = True
                    HUD.system(f"Quest de Cassino ativa detectada. Meta: {goal:,}. Cassino iniciado!")
                return

        # ─── 6. Live Feed + Response Processing ───
        if content_to_log:
            author_name = message.author.name.upper()
            if message.author.id == config.EPIC_RPG_ID:
                prefix = f"{Fore.LIGHTRED_EX}🎮 [EPIC RPG]{Style.RESET_ALL}"
                color = Fore.LIGHTYELLOW_EX
            elif message.author.id == config.NAVI_LITE_ID or message.author.name.lower() == "navi lite":
                prefix = f"{Fore.LIGHTBLUE_EX}🧚 [NAVI LITE]{Style.RESET_ALL}"
                color = Fore.LIGHTCYAN_EX
            elif message.author.id == config.userID:
                prefix = f"{Fore.LIGHTGREEN_EX}👤 [PLAYER]{Style.RESET_ALL}"
                color = Fore.WHITE
            else:
                prefix = f"{Fore.LIGHTBLACK_EX}💬 [{author_name}]{Style.RESET_ALL}"
                color = Fore.LIGHTBLACK_EX
            HUD._write(f"{prefix} {color}{HUD.clean_markdown(content_to_log)}{Style.RESET_ALL}")

        if message.embeds:
            embed_dict = message.embeds[0].to_dict()
            logger.debug("Embed description: %s", message.embeds[0].description)
            logger.debug("Embed fields: %s", message.embeds[0].fields)
            logger.debug("Full embed dict: %s", embed_dict)

            # NeonUtil parsing for new messages
            if message.author.id in config.NEON_BOT_IDS and not bot_state.paused:
                rec = parse_neon_recommendation(embed_dict)
                if rec:
                    from bot.handlers import format_neon_for_telegram
                    formatted = format_neon_for_telegram(embed_dict)
                    bot_state.latest_neon_recommendation = (rec, formatted, time.monotonic())
                    bot_state.neon_updated_event.set()

                    if config.card_hand_action == "legacy_auto":
                        add_to_high_priority_queue(rec)
                        HUD.system(f"NeonUtil (legacy): Carta ideal é '{rec}'")
        try:
            await responseResolver(message)
            save_session_data(sessionData)
            # Track this message as processed to prevent on_message_edit
            # from re-processing it (Epic RPG often edits embeds after sending)
            is_pet_message = False
            is_cardhand_message = False
            if message.embeds:
                msg_embed_dict = message.embeds[0].to_dict()
                msg_text = str(msg_embed_dict).lower()
                if "— pets" in msg_text or "pet adventure rewards" in msg_text:
                    is_pet_message = True
                author_name = (msg_embed_dict.get("author") or {}).get("name") or ""
                title = msg_embed_dict.get("title") or ""
                embed_header = (author_name + " " + title).lower()
                if "card hand" in embed_header:
                    is_cardhand_message = True
            if message.author.id == config.EPIC_RPG_ID and message.embeds and not is_pet_message and not is_cardhand_message:
                self._track_processed_message(message.id)
        except Exception as e:
            logger.error(
                f"Error processing message: {e}\n{traceback.format_exc()}"
            )
            bot_state.coinflip_pending = False

    async def on_message_edit(self, before, after):
        if after.author.id not in config.NEON_BOT_IDS and after.author.id != config.EPIC_RPG_ID:
            return
        if after.channel.id != config.channelID:
            return

        # Forward cardhand image if applicable on message edit
        from bot.handlers import check_and_forward_cardhand_image
        await check_and_forward_cardhand_image(after)

        is_cardhand_message = False
        if after.embeds:
            edit_embed_dict = after.embeds[0].to_dict()
            embed_text = str(edit_embed_dict).lower()
            author_name = (edit_embed_dict.get("author") or {}).get("name") or ""
            title = edit_embed_dict.get("title") or ""
            embed_header = (author_name + " " + title).lower()
            if "card hand" in embed_header:
                is_cardhand_message = True

        if bot_state.paused:
            return
        if not after.embeds:
            return
        if before.embeds == after.embeds and not is_cardhand_message:
            return

        if after.author.id == config.EPIC_RPG_ID:
            # Skip if this message was already fully processed by on_message
            # (Epic RPG frequently edits embeds after sending, causing duplicate processing)
            # EXCEPT for pet/sleepet messages because they might be loaded dynamically.
            is_pet_edit = False
            is_cardhand_edit = False
            if after.embeds:
                after_dict = after.embeds[0].to_dict()
                after_text = str(after_dict).lower()
                if "— pets" in after_text or "pet adventure rewards" in after_text:
                    is_pet_edit = True
                author_name = (after_dict.get("author") or {}).get("name") or ""
                title = after_dict.get("title") or ""
                embed_header = (author_name + " " + title).lower()
                if "card hand" in embed_header:
                    is_cardhand_edit = True

            if after.id in self._processed_msg_ids and not is_pet_edit and not is_cardhand_edit:
                logger.debug(f"Skipping already-processed Epic RPG edit: {after.id}")
                return
            try:
                await responseResolver(after)
                save_session_data(sessionData)
                # Track it now so further edits are also skipped (except if it's still a pet/cardhand message edit)
                if after.embeds and not is_pet_edit and not is_cardhand_edit:
                    self._track_processed_message(after.id)
            except Exception as e:
                logger.error(f"Error processing edited message: {e}\n{traceback.format_exc()}")
            return

        # Neon Bot Helper edit — handle based on card_hand_action mode
        if after.author.id in config.NEON_BOT_IDS:
            embed_dict = after.embeds[0].to_dict()
            rec = parse_neon_recommendation(embed_dict)
            if rec:
                from bot.handlers import format_neon_for_telegram
                formatted = format_neon_for_telegram(embed_dict)
                bot_state.latest_neon_recommendation = (rec, formatted, time.monotonic())
                bot_state.neon_updated_event.set()

                HUD.cardhand(f"Neon Bot Helper atualizou análise do Card Hand.")
                logger.info(f"Neon edit detected (rec: {rec})...")

                needs_immediate_send = (
                    config.card_hand_action == "legacy_auto"
                    or not bot_state.cardhand_in_progress
                )
                if config.card_hand_action in ["auto", "legacy_auto"] and needs_immediate_send:
                    try:
                        await send_telegram_raw(formatted)
                    except Exception as e:
                        logger.error(f"Erro ao encaminhar edição do Neon para o Telegram: {e}")

                # In legacy_auto mode, parse and auto-queue the optimal card
                if config.card_hand_action == "legacy_auto":
                    add_to_high_priority_queue(rec)
                    HUD.system(f"NeonUtil (legacy): Carta ideal é '{rec}'")
            return

    async def telegram_listener_loop(self):
        if not config.TelegramBotToken or not config.TelegramChatID:
            logger.warning("Telegram token ou chat ID não configurado no options.ini. Controle remoto via Telegram desabilitado.")
            return

        HUD.system("Iniciando controle remoto interativo via Telegram...")
        
        last_update_id = 0
        
        # Poll once at start to flush old updates
        try:
            from bot.telegram import _get_session
            session = _get_session()
            url = f"https://api.telegram.org/bot{config.TelegramBotToken}/getUpdates"
            async with session.get(url, params={"offset": -1, "timeout": 0}) as resp:
                data = await resp.json()
                if data.get("ok") and data.get("result"):
                    last_update_id = data["result"][0]["update_id"]
        except Exception:
            pass

        while not self.is_closed():
            try:
                from bot.telegram import _get_session
                session = _get_session()
                url = f"https://api.telegram.org/bot{config.TelegramBotToken}/getUpdates"
                params = {"offset": last_update_id + 1, "timeout": TELEGRAM_GETUPDATES_TIMEOUT}
                async with session.get(url, params=params, timeout=TELEGRAM_HTTP_TIMEOUT) as resp:
                    data = await resp.json()
                    if data.get("ok") and data.get("result"):
                        for update in data["result"]:
                            last_update_id = update["update_id"]
                            
                            # Route callback queries and text to card hand if active
                            if "callback_query" in update:
                                cb = update["callback_query"]
                                cb_data = cb.get("data", "")
                                if bot_state.cardhand_in_progress and cb_data:
                                    if cb_data.startswith("ch_"):
                                        bot_state.cardhand_user_choice = cb_data.split("_")[1]
                                    else:
                                        bot_state.cardhand_user_choice = cb_data
                                    # Answer callback to clear loading spinner
                                    cb_id = cb.get("id")
                                    ans_url = f"https://api.telegram.org/bot{config.TelegramBotToken}/answerCallbackQuery"
                                    try:
                                        await session.post(ans_url, json={"callback_query_id": cb_id}, timeout=TELEGRAM_CALLBACK_TIMEOUT)
                                    except Exception:
                                        pass
                                continue
                                
                            msg = update.get("message")
                            if msg:
                                chat_id = msg.get("chat", {}).get("id")
                                if str(chat_id) != str(config.TelegramChatID):
                                    continue
                                    
                                text = msg.get("text", "").strip()
                                if text:
                                    await self.handle_telegram_command(text)
            except Exception as e:
                logger.error(f"Erro no loop de comandos do Telegram: {e}")
                
            await asyncio.sleep(TELEGRAM_POLL_INTERVAL)

    async def handle_telegram_command(self, text):
        cmd = text.lower().strip()
        
        if cmd == "/stats" or cmd == "stats":
            stats_msg = "📊 *ESTATÍSTICAS DA SESSÃO* 📊\n\n"
            raw_stats = format_session_data(sessionData, "Dados da Sessão")
            # Strip ANSI escape codes
            clean_stats = re.sub(r'\x1b\[[0-9;]*m', '', raw_stats)
            stats_msg += f"```\n{clean_stats}\n```"
            await send_telegram_notification(stats_msg)
            
        elif cmd == "/status" or cmd == "status":
            status_emoji = "🟢 RUNNING"
            if bot_state.paused:
                status_emoji = "🔴 PAUSED"
            elif bot_state.is_on_coffee_break:
                status_emoji = "☕ COFFEE BREAK"
            elif bot_state.jailed:
                status_emoji = "💀 JAILED (PRESO)"
            elif bot_state.sleepet_mode:
                status_emoji = "😴 SLEEPET MODE"
                
            msg = (
                f"ℹ️ *STATUS DO ORACLE*\n\n"
                f"• Estado: {status_emoji}\n"
                f"• Sleepet Mode: {'Ativo (' + str(bot_state.sleepet_state) + ')' if bot_state.sleepet_mode else 'Inativo'}\n"
                f"• Time Cookie Mode: {'Ativo' if bot_state.time_cookie_mode else 'Inativo'}\n"
                f"• Cooldowns pendentes: {len(lowPriorityQueue)} no LPQ, {len(highPriorityQueue)} no HPQ\n"
                f"• Telegram Notifier: Ativo\n"
                f"• Configs:\n"
                f"  - Hunt: {'Ativo' if config.do_hunt else 'Inativo'}\n"
                f"  - Adventure: {'Ativo' if config.do_adv else 'Inativo'}\n"
                f"  - Farm: {'Ativo' if config.do_farm else 'Inativo'}\n"
                f"  - Coinflip: {'Pausado' if bot_state.gambling_paused else 'Jogando'}"
            )
            await send_telegram_notification(msg)
            
        elif cmd == "/pause" or cmd == "pause":
            bot_state.paused = True
            HUD.alert("📲 COMANDO TELEGRAM: Bot PAUSADO.")
            await send_telegram_notification("⏸️ O bot foi PAUSADO pelo Telegram.")
            
        elif cmd == "/resume" or cmd == "resume":
            bot_state.paused = False
            HUD.system("📲 COMANDO TELEGRAM: Bot RETOMADO.")
            await send_telegram_notification("▶️ O bot foi RETOMADO pelo Telegram.")
            
        elif cmd.startswith("/toggle ") or cmd.startswith("toggle "):
            parts = cmd.split()
            if len(parts) > 1:
                opt = parts[1]
                if opt in ["hunt", "do_hunt"]:
                    config.do_hunt = not config.do_hunt
                    await send_telegram_notification(f"🔄 `do_hunt` alterado para: {config.do_hunt}")
                elif opt in ["adv", "adventure", "do_adv"]:
                    config.do_adv = not config.do_adv
                    await send_telegram_notification(f"🔄 `do_adv` alterado para: {config.do_adv}")
                elif opt in ["farm", "do_farm"]:
                    config.do_farm = not config.do_farm
                    await send_telegram_notification(f"🔄 `do_farm` alterado para: {config.do_farm}")
                elif opt in ["work", "do_work"]:
                    config.do_work = not config.do_work
                    await send_telegram_notification(f"🔄 `do_work` alterado para: {config.do_work}")
                elif opt in ["cf", "coinflip", "gamble"]:
                    bot_state.gambling_paused = not bot_state.gambling_paused
                    await send_telegram_notification(f"🔄 Coinflip (Cassino) alterado para: {'Pausado' if bot_state.gambling_paused else 'Jogando'}")
                else:
                    await send_telegram_notification(f"❌ Opção desconhecida: {opt}")
            else:
                await send_telegram_notification("⚠️ Use: `/toggle [hunt/adv/farm/work/cf]`")
                
        elif cmd == "/sleepet start" or cmd == "sleepet start":
            lowPriorityQueue.clear()
            lowPriorityQueueSet.clear()
            bot_state.sleepet_mode = True
            bot_state.sleepet_state = "init"
            bot_state.last_sleepet_cmd_time = time.monotonic()
            HUD.system("📲 COMANDO TELEGRAM: Sleepet Mode ATIVADO.")
            await send_telegram_notification("😴 *Sleepet Mode Ativado.* LPQ limpa e loop de pets iniciado!")

        elif cmd.startswith("/sleepet stop") or cmd == "sleepet stop":
            bot_state.sleepet_mode = False
            bot_state.sleepet_state = None
            HUD.system("📲 COMANDO TELEGRAM: Sleepet Mode DESATIVADO.")
            await send_telegram_notification("🛑 *Sleepet Mode Desativado. Filas normais liberadas.*")

        elif cmd.startswith("/tc start") or cmd.startswith("tc start"):
            parts = cmd.split()
            bot_state.time_cookie_mode = True
            bot_state.tc_quantity = config.tc_quantity

            for part in parts[2:]:
                if part.endswith('c') and part[:-1].isdigit():
                    bot_state.tc_quantity = int(part[:-1])
                    break

            for part in parts[2:]:
                if part.endswith('m') and part[:-1].isdigit():
                    mins = int(part[:-1])
                    bot_state.tc_end_time = time.monotonic() + (mins * 60)
                    break
            else:
                bot_state.tc_end_time = 0

            HUD.tc(f"📲 COMANDO TELEGRAM: Modo Time Cookie ATIVADO ({bot_state.tc_quantity} cookies/uso).")
            await send_telegram_notification(f"🍪 *Modo Time Cookie Ativado ({bot_state.tc_quantity}c/uso).*")
            await queue_tc_commands()

        elif cmd.startswith("/tc stop") or cmd == "/tc pause" or cmd == "tc stop" or cmd == "tc pause":
            bot_state.time_cookie_mode = False
            bot_state.tc_end_time = 0
            HUD.system("📲 COMANDO TELEGRAM: Modo Time Cookie DESATIVADO.")
            await send_telegram_notification("🛑 *Modo Time Cookie Desativado.*")

        # Auto Enchant command check
        else:
            cmd_clean = cmd
            if cmd_clean.startswith("/"):
                cmd_clean = cmd_clean[1:]
            if cmd_clean.startswith("sb "):
                cmd_clean = cmd_clean[3:].strip()
                
            parts = cmd_clean.split()
            if len(parts) >= 2 and parts[0] in ["enchant", "refine", "transmute", "transcend"]:
                if parts[1] == "stop":
                    bot_state.auto_enchant_active = False
                    HUD.system(f"📲 COMANDO TELEGRAM: Auto-Enchant {parts[0].upper()} cancelado.")
                    await send_telegram_notification(f"🛑 *Auto-Enchant {parts[0].title()} Cancelado.*")
                    return
                elif len(parts) >= 3:
                    tier = parts[0]
                    target = parts[1].lower()
                    if target not in ["a", "s"]:
                        await send_telegram_notification("⚠️ O alvo deve ser `a` (armadura) ou `s` (espada).")
                        return
                    
                    target_val_raw = " ".join(parts[2:])
                    target_val = target_val_raw.lower().replace(" ", "").replace("-", "")
                    
                    if target_val not in ENCHANT_TIERS_ORDER:
                        await send_telegram_notification(f"⚠️ Encantamento desconhecido: `{target_val_raw}`.")
                        return
                    
                    bot_state.auto_enchant_active = True
                    bot_state.auto_enchant_tier = tier
                    bot_state.auto_enchant_target = target
                    bot_state.auto_enchant_target_value = target_val
                    bot_state.auto_enchant_channel_id = config.channelID
                    bot_state.auto_enchant_attempts = 0
                    bot_state.last_auto_enchant_time = time.monotonic()
                    bot_state.auto_enchant_withdrawn = False
                    
                    lowPriorityQueue.clear()
                    lowPriorityQueueSet.clear()
                    
                    HUD.system(f"📲 COMANDO TELEGRAM: Auto-Enchant ATIVADO: {tier} {target} para {target_val_raw.upper()}. LPQ limpa.")
                    await send_telegram_notification(
                        f"🔮 *Auto-Enchant Iniciado via Telegram!*\n"
                        f"• Tipo: `{tier.upper()}`\n"
                        f"• Alvo: `{'Espada' if target == 's' else 'Armadura'}`\n"
                        f"• Level Desejado: `{target_val_raw.upper()}`\n"
                        f"• LPQ limpa e bloqueada. Comando enviado para HPQ."
                    )
                    
                    add_to_high_priority_queue(f"rpg {tier} {target}")
                    return

        if cmd.startswith("language "):
            parts = cmd.split()
            if len(parts) > 1:
                new_lang = parts[1].lower().strip()
                if new_lang in ("pt", "en"):
                    set_language(new_lang)
                    HUD.system(f"📲 COMANDO TELEGRAM: Idioma alterado para {new_lang}.")
                    await send_telegram_notification(t("telegram_language_changed", lang="pt" if new_lang == "pt" else "en"))

        if cmd == "/help" or cmd == "help":
            help_msg = (
                "🎯 *COMANDOS DISPONÍVEIS NO TELEGRAM* 🎯\n\n"
                "• `stats` ou `/stats` - Envia estatísticas de progresso e Drops\n"
                "• `status` ou `/status` - Envia o estado atual do bot e queues\n"
                "• `pause` ou `/pause` - Pausa todas as ações do bot\n"
                "• `resume` ou `/resume` - Retoma as ações do bot\n"
                "• `sleepet start` ou `/sleepet start` - Inicia Sleepet Mode\n"
                "• `sleepet stop` ou `/sleepet stop` - Para Sleepet Mode\n"
                "• `tc start [Xc] [Xm]` ou `/tc start [Xc] [Xm]` - Inicia Time Cookie Mode (ex: `/tc start 1c 5m`)\n"
                "• `tc stop` ou `/tc stop` - Desativa Time Cookie Mode\n"
                "• `enchant/refine/transmute/transcend <a/s> <enchant_name>` - Inicia Auto Enchant (ex: `/refine s godly`)\n"
                "• `enchant/refine/transmute/transcend stop` - Para Auto Enchant\n"
                "• `toggle [hunt/adv/farm/work/cf]` - Alterna configurações em tempo real (cf = coinflip/gambling)\n"
                "• `language [pt/en]` ou `/language [pt/en]` - Altera o idioma do bot / Change bot language\n"
                "• `help` ou `/help` - Exibe esta ajuda"
            )

            await send_telegram_notification(help_msg)
        else:
            if bot_state.captcha_pending:
                # Route text messages to captcha override during pending captcha
                bot_state.captcha_user_override = text
                logger.info(f"📲 CAPTCHA TELEGRAM OVERRIDE RECEIVED: {text}")
                return
            if bot_state.cardhand_in_progress:
                # Route text messages to card hand during active game
                bot_state.cardhand_user_choice = text
                return
            if not cmd.startswith("/start"):
                await send_telegram_notification("❓ Comando não reconhecido. Digite `/help` para ver as opções.")


UserBot = DiscordClient()


def recreate_user_bot():
    global UserBot
    UserBot = DiscordClient()
    import bot
    bot.UserBot = UserBot
    return UserBot
