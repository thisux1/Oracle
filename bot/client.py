import discord
import asyncio
import time
import re
import traceback
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
)
from bot.telegram import send_telegram_notification
from bot.captcha import tentar_resolver_captcha, set_client
from bot.handlers import responseResolver
from colorama import Fore, Back, Style


class DiscordClient(discord.Client):
    async def setup_hook(self):
        self.bg_task = self.loop.create_task(self.my_background_task())

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('----------------------------------------------')
        # Register client reference so captcha module can use wait_for()
        set_client(self)
        
        # Add rpg pet to queue at startup to sync pet timers
        add_to_low_priority_queue("rpg pet")
        logger.info("Queued 'rpg pet' at session start.")
        
        config.userID = self.user.id
        
        # Resolve server nickname
        await asyncio.sleep(1)
        guild = self.get_guild(config.GUILD_ID)
        if guild:
            member = guild.get_member(self.user.id)
            if member and member.nick:
                config.user_name_lower = member.nick.lower()
                logger.info(
                    f"Using server nickname for Epic RPG filtering: "
                    f"{config.user_name_lower}"
                )
            else:
                config.user_name_lower = self.user.name.lower()
                logger.info(
                    f"Using bot name for Epic RPG filtering: "
                    f"{config.user_name_lower} (no server nickname)"
                )
        else:
            config.user_name_lower = self.user.name.lower()
            logger.warning(
                f"Could not retrieve guild (ID: {config.GUILD_ID}). "
                f"Using default bot name for filtering: {config.user_name_lower}"
            )

    async def my_background_task(self):
        await self.wait_until_ready()
        channel = self.get_channel(config.channelID)
        last_check = time.time() - 120

        while not self.is_closed():
            try:
                current_time = time.time()

                logger.debug(
                    f"States - Paused: {bot_state.paused}, "
                    f"Gambling: {not bot_state.gambling_paused}, "
                    f"Coinflip: {bot_state.coinflip_pending}, "
                    f"Withdraw: {bot_state.awaiting_withdraw}"
                )

                # Stealth: Coffee Breaks
                if (
                    current_time > bot_state.next_break_time
                    and not bot_state.is_on_coffee_break
                ):
                    break_duration = randint(300, 900)
                    bot_state.is_on_coffee_break = True
                    HUD.alert(f"Human Coffee Break: {break_duration/60:.1f}m...")
                    await asyncio.sleep(break_duration)
                    bot_state.is_on_coffee_break = False
                    bot_state.next_break_time = time.time() + randint(3600, 7200)
                    HUD.system("Break over. Resuming.")

                # Watchdog: Emergency Pause
                if bot_state.no_response_count >= 3:
                    bot_state.paused = True
                    bot_state.no_response_count = 0
                    HUD.alert("WATCHDOG: No response. Emergency pause!")
                    await send_telegram_notification(
                        "🚨 WATCHDOG: Pausa de Emergência ativada "
                        "devido à falta de respostas do jogo."
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
                        and (current_time - bot_state.last_curiosity_time) > 300
                    ):
                        if randint(1, 100) <= 5:
                            curiosity_cmd = ["rpg i", "rpg p", "rpg cd"][
                                randint(0, 2)
                            ]
                            add_to_low_priority_queue(
                                curiosity_cmd, suppress_log=True
                            )
                            bot_state.last_curiosity_time = current_time
                            HUD.system(
                                f"Feeling curious... checking '{curiosity_cmd}'"
                            )

                    def track_command(command):
                        cmd_clean = command.lower()
                        if cmd_clean.startswith("rpg "):
                            parts = cmd_clean.split()
                            if len(parts) > 1:
                                c_type = parts[1]
                                if c_type in sessionData["command_data"]:
                                    sessionData["command_data"][c_type] += 1
                                elif c_type == "adv":
                                    sessionData["command_data"]["adventure"] += 1
                                elif c_type in ["chop", "fish", "mine", "pickup", "axe", "net", "pickaxe", "ladder", "boat", "bow", "chainsaw", "bigboat"]:
                                    sessionData["command_data"]["work"] += 1

                    if current_time <= bot_state.minigame_pending_until:
                        # During a minigame, only allow the answer through HPQ
                        # (answers are plain text like "3", "yes" — never start with "rpg")
                        for i, cmd in enumerate(highPriorityQueue):
                            if not cmd.lower().startswith("rpg"):
                                await human_delay(1.5, 2.0)
                                cmd_to_send = highPriorityQueue.pop(i)
                                highPriorityQueueSet.discard(cmd_to_send)
                                bot_state.no_response_count += 1
                                await send_with_typo_chance(channel, cmd_to_send, "HPQ-MG")
                                HUD.command(cmd_to_send, "HPQ-MG")
                                break
                        # else: wait silently for minigame to resolve
                    elif bot_state.cardhand_in_progress:
                        # Card Hand active — only allow non-rpg HPQ commands (e.g. "pass")
                        # Safety timeout: reset after 120s
                        if current_time - bot_state.cardhand_start_time > 120:
                            bot_state.cardhand_in_progress = False
                            HUD.system("Card Hand timeout (120s). Queues released.")
                        else:
                            for i, cmd in enumerate(highPriorityQueue):
                                if not cmd.lower().startswith("rpg"):
                                    await human_delay(1.5, 2.0)
                                    cmd_to_send = highPriorityQueue.pop(i)
                                    highPriorityQueueSet.discard(cmd_to_send)
                                    await send_with_typo_chance(channel, cmd_to_send, "HPQ-CH")
                                    HUD.command(cmd_to_send, "HPQ-CH")
                                    break
                    elif highPriorityQueue:
                        await human_delay(1.5, 2.0)
                        cmd = highPriorityQueue.pop(0)
                        highPriorityQueueSet.discard(cmd)
                        current_time = time.time()
                        if cmd == bot_state.last_sent_command and (current_time - bot_state.last_sent_time) < 5.0 and not cmd.startswith("rpg cf"):
                            HUD.system(f"Skipped duplicate command '{cmd}' (Anti-Spam).")
                        else:
                            # Set card hand lock BEFORE sending the command
                            if cmd.lower() == "rpg card hand" and config.card_hand_action == "auto":
                                bot_state.cardhand_in_progress = True
                                bot_state.cardhand_first_pass_done = False
                                bot_state.cardhand_start_time = current_time
                                HUD.system("Card Hand started! Queues locked.")
                            track_command(cmd)
                            bot_state.no_response_count += 1
                            bot_state.last_sent_command = cmd
                            bot_state.last_sent_time = current_time
                            await send_with_typo_chance(channel, cmd, "HPQ")
                            HUD.command(cmd, "HPQ")
                    elif lowPriorityQueue and bot_state.gambling_paused:
                        await human_delay(1.5, 2.5)
                        cmd = lowPriorityQueue.pop(0)
                        lowPriorityQueueSet.discard(cmd)
                        current_time = time.time()
                        if cmd == bot_state.last_sent_command and (current_time - bot_state.last_sent_time) < 5.0 and not cmd.startswith("rpg cf"):
                            HUD.system(f"Skipped duplicate command '{cmd}' (Anti-Spam).")
                        else:
                            # Set card hand lock BEFORE sending the command (if queued in LPQ too)
                            if cmd.lower() == "rpg card hand" and config.card_hand_action == "auto":
                                bot_state.cardhand_in_progress = True
                                bot_state.cardhand_first_pass_done = False
                                bot_state.cardhand_start_time = current_time
                                HUD.system("Card Hand started! Queues locked.")
                            track_command(cmd)
                            bot_state.no_response_count += 1
                            bot_state.last_sent_command = cmd
                            bot_state.last_sent_time = current_time
                            await send_with_typo_chance(channel, cmd, "LPQ")
                            HUD.command(cmd, "LPQ")
                    else:
                        if bot_state.time_cookie_mode:
                            if 0 < bot_state.tc_end_time < current_time:
                                bot_state.time_cookie_mode = False
                                bot_state.tc_end_time = 0
                                HUD.system("Time Cookie mode expired.")
                                await send_telegram_notification("⏳ Modo Time Cookie desativado automaticamente (tempo esgotado).")
                            elif current_time - bot_state.last_tc_use_time > 10:
                                bot_state.last_tc_use_time = current_time
                                add_to_high_priority_queue(f"rpg use tc {bot_state.tc_quantity}")
                                add_to_low_priority_queue("rpg rd", suppress_log=True)
                                HUD.system("Time Cookie Cycle: Empty queue, using cookie and checking rd.")

                    # Dungeon State: timeout safety
                    if bot_state.dungeon_in_progress and current_time - bot_state.last_dungeon_time > 60:
                        bot_state.dungeon_in_progress = False
                        bot_state.dragon_alive = False
                        HUD.dungeon("State timeout, resetting.")

                    # Pet Adventure: auto-claim when timer expires
                    if (
                        bot_state.pet_adventure_return_time > 0
                        and current_time >= bot_state.pet_adventure_return_time
                    ):
                        bot_state.pet_adventure_return_time = 0
                        add_to_low_priority_queue("rpg pet claim")
                        HUD.system("Pet adventure complete! Claiming rewards...")

                    if current_time - last_check >= 120:
                        last_check = current_time
                        add_to_low_priority_queue("rpg rd", suppress_log=True)
                        logger.info("Command rpg rd queued")

                    if current_time - bot_state.last_save_time >= 300:
                        from bot.persistence import save_session_data
                        
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
            await asyncio.sleep(0.5)

    async def on_message(self, message):
        # ─── 0. Manual Commands (sb prefix — always processed) ───
        if message.author.id in config.ADMIN_IDS:
            msg_clean = message.content.lower().strip()
            if msg_clean.startswith("sb "):
                cmd = msg_clean.split("sb ")[1]
                if cmd in ["pause", "stop"]:
                    bot_state.paused = True
                    HUD.alert("Bot PAUSED via Discord command.")
                    await message.channel.send("⏸️ **Bot Pausado.**")
                    return
                elif cmd in ["start", "resume"]:
                    bot_state.paused = False
                    HUD.system("Bot RESUMED via Discord command.")
                    await message.channel.send("▶️ **Bot Retomado.**")
                    return
                elif cmd == "force":
                    await responseResolver(message)
                    HUD.system("FORCED processing executed.")
                    return
                elif cmd == "reset":
                    highPriorityQueue.clear()
                    highPriorityQueueSet.clear()
                    lowPriorityQueue.clear()
                    lowPriorityQueueSet.clear()
                    bot_state.no_response_count = 0
                    bot_state.lootbox_cooldown_until = 0
                    HUD.system("Queues and Cooldowns RESET via Discord.")
                    await message.channel.send(
                        "🔄 **Filas e Cooldowns Financeiros Resetados.**"
                    )
                    return
                elif cmd.startswith("tc start"):
                    parts = cmd.split()
                    bot_state.time_cookie_mode = True

                    bot_state.tc_quantity = config.tc_quantity
                    for part in parts[2:]:
                        if part.endswith('c') and part[:-1].isdigit():
                            bot_state.tc_quantity = int(part[:-1])
                            break

                    if len(parts) > 2 and parts[2].endswith('m') and parts[2][:-1].isdigit():
                        mins = int(parts[2][:-1])
                        bot_state.tc_end_time = time.time() + (mins * 60)
                    else:
                        bot_state.tc_end_time = 0

                    HUD.tc(f"Time Cookie mode ACTIVATED ({bot_state.tc_quantity} cookies/use).")
                    await message.channel.send(f"🍪 **Modo Time Cookie Ativado ({bot_state.tc_quantity}c/uso).**")
                    await queue_tc_commands()
                    return
                elif cmd in ["tc stop", "tc pause"]:
                    bot_state.time_cookie_mode = False
                    bot_state.tc_end_time = 0
                    HUD.system("Time Cookie mode DEACTIVATED.")
                    await message.channel.send("🛑 **Modo Time Cookie Desativado.**")
                    return
                elif cmd in ["ajuda", "tutorial"]:
                    tutorial_msg = (
                        "📚 **Tutorial Oracle v2**\n\n"
                        "**Comandos de Controle:**\n"
                        "• `sb start` / `sb pause`: Inicia ou pausa a execução do bot\n"
                        "• `sb reset`: Limpa todas as filas e reseta variáveis de estado\n"
                        "• `sb tc start [Xc] [m]`: Ativa modo Time Cookie. "
                        "Ex: `sb tc start 4c 60m` (4 cookies, 60 min). "
                        "• `sb tc stop`: Desativa o modo Time Cookie\n"
                        "• `sb g start` / `sb g pause`: Inicia ou pausa o gambling (Fibonacci)\n"
                        "• `sb stats [tempo]`: Mostra progresso, loot e status da sessão. "
                        "Ex: `sb stats 7d` (últimos 7 dias). Dados persistem entre reboots!\n"
                        "• `sb say [texto]`: Envia uma mensagem no canal configurado\n\n"
                        "**Configurações (options.ini):**\n"
                        "• `do_hunt`, `do_adv`, `do_farm`, etc: Liga/desliga comandos "
                        "individuais sem editar o código\n"
                        "• `do_ultr`: Substitui training pela sequência ULTR "
                        "(rpg ultr → double → attack → rpg use tc)\n"
                        "• `is_eternal`: Habilita auto-enter em dungeon e bite loop "
                        "automático no dragão eternal\n"
                        "• `card_hand_action`: `auto` (joga via IA) ou "
                        "`notify` (só notifica Telegram pra jogar manual)\n"
                        "• `tc_quantity`: Quantidade padrão de cookies por uso. "
                        "Sobrescrito via `sb tc start Xc`\n"
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
                        from bot.persistence import get_stats_for_period
                        from bot.parsers import format_session_data
                        period_data = get_stats_for_period(sessionData, period_str)
                        stats_msg = "```ansi\n" + format_session_data(period_data, f"Session Data (Last {period_str})") + "\n```"
                    else:
                        loot_list = []
                        for category in [
                            "mob_drops", "work_drops", "farm_drops", "lootbox_drops",
                        ]:
                            for item, qty in sessionData["loot_data"][
                                category
                            ].items():
                                if qty > 0:
                                    loot_list.append(f"• {item}: {qty}")
                        for item, val in sessionData["misc"].items():
                            if isinstance(val, int):
                                if val > 0:
                                    loot_list.append(f"• {item}: {val}")
                            elif isinstance(val, dict):
                                for sub_item, sub_qty in val.items():
                                    if sub_qty > 0:
                                        loot_list.append(
                                            f"• {sub_item}: {sub_qty}"
                                        )
                        loot_summary = (
                            "\n".join(loot_list[:50]) if loot_list else "None yet"
                        )
                        stats_msg = (
                            f"📊 **Relatório da Sessão Oracle v2**\n"
                            f"**Progresso:**\n"
                            f"• Coins: {sessionData['progress_data']['coins']:,}\n"
                            f"• XP: {sessionData['progress_data']['xp']:,}\n"
                            f"**Comandos:**\n"
                            f"• Hunt: {sessionData['command_data']['hunt']} "
                            f"| Work: {sessionData['command_data']['work']}\n"
                            f"• Quest: {sessionData['command_data']['quest']} "
                            f"| Watchdog: {bot_state.no_response_count}/3\n"
                            f"**Loot:**\n{loot_summary}\n"
                            f"**Status:** "
                            f"{'⏸️ PAUSADO' if bot_state.paused else '🏎️ FARMANDO'}"
                        )
                    await message.channel.send(stats_msg)
                    return
                elif cmd.startswith("say "):
                    text_to_say = msg_clean.split("sb say ")[1]
                    add_to_high_priority_queue(text_to_say)
                    HUD.system(f"Remote command queued: {text_to_say}")
                    await message.channel.send(
                        f"🚀 **Enviado para o canal <#{config.channelID}>:** `{text_to_say}`"
                    )
                    return

        # Reset Watchdog on any Epic RPG / Navi message
        if message.author.id in [config.EPIC_RPG_ID, config.NAVI_LITE_ID]:
            bot_state.no_response_count = 0

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
        if message.channel.id != config.channelID and not (
            isinstance(message.channel, discord.DMChannel)
            and message.author.id in config.ADMIN_IDS
        ):
            return

        # ─── 3. Status Detection (bypasses pause) ───
        if message.author.id == config.EPIC_RPG_ID:
            # Captcha Detection
            if (
                "check you are actually playing" in combined_content
                or "stop there" in combined_content
            ):
                bot_state.paused = True
                HUD.alert("CAPTCHA DETECTED! Bot paused for safety.")
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
            elif (
                "is now in the jail" in combined_content
                or "is now in the adventure jail" in combined_content
            ):
                bot_state.jailed = True
                bot_state.paused = True
                HUD.alert("JAIL DETECTED! Automation suspended.")
                await send_telegram_notification(
                    "🚨 BOT PRESO! Captcha falhou ou expirou. "
                    "Intervenção manual necessária."
                )
                return

            # Freedom Detection
            elif any(
                x in combined_content
                for x in [
                    "is no longer in the jail",
                    "fine, i will let you go",
                    "you are free",
                    "everything seems fine",
                    "everything looks fine",
                ]
            ):
                bot_state.jailed = False
                bot_state.paused = False
                bot_state.captcha_pending = False
                HUD.system("Freedom detected! Resuming automation.")
                return

            # Profile detection (update bankroll)
            elif f"{config.user_name_lower} — profile" in combined_content:
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
                        HUD.system(f"Bankroll updated via profile: {total_balance:,} coins")
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
                HUD.alert("Time Cookies depleted! TC mode disabled.")
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
                            f"Trade {letters[idx]} failed. "
                            f"Trying '{next_letter}'..."
                        )
                    else:
                        bot_state.pending_trade_letter = None
                        HUD.alert("All trade options (A-F) failed.")
                except ValueError:
                    bot_state.pending_trade_letter = None

            if bot_state.pending_trade_letter and (
                "our trade is done then" in combined_content
            ):
                bot_state.pending_trade_letter = None
                HUD.system("Trade Quest Successfully Completed!")

            if (
                "don't have enough money" in combined_content
                or "don't have a bank account" in combined_content
            ):
                bot_state.lootbox_cooldown_until = time.time() + 1800
                if "don't have a bank account" in combined_content:
                    bot_state.has_bank_account = False
                HUD.alert(
                    "Erro Financeiro! Compra de lootbox suspensa por 30 minutos."
                )
                for q in [highPriorityQueue, lowPriorityQueue]:
                    for cmd in list(q):
                        if any(
                            x in cmd for x in ["buy", "withdraw", "deposit"]
                        ):
                            q.remove(cmd)
                            highPriorityQueueSet.discard(cmd)
                            lowPriorityQueueSet.discard(cmd)
                return

        # Donut Engine: Void Area Question
        if (
            "how many days are left for this area to close?" in combined_content
            and message.author.id == config.EPIC_RPG_ID
        ):
            days = config.userOptions.get("daysToCloseVoid", "3")
            add_to_high_priority_queue(days)
            HUD.system(f"Answered Void question: {days}")
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
            HUD.system("NPC dialog detected. Analyzing quest...")
            if any(
                x in combined_content
                for x in ["arena", "miniboss", "guild raid"]
            ):
                add_to_high_priority_queue("no")
                HUD.alert("Quest Declined (Manual/Annoying type).")
                return

            add_to_high_priority_queue("yes")
            HUD.system("Quest Accepted. Initiating strategy...")

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
                HUD.system("Trade quest accepted. Trying 'a'...")
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
                HUD.system(f"Casino Mode Active. Goal: {goal:,}. First bet queued.")
                return

            HUD.system("Quest accepted (Passive Hunt/Adv type).")
            return

        # ─── 5.5 Active Quest Detection ───
        if "if you don't want this quest anymore" in combined_content and message.author.id == config.EPIC_RPG_ID:
            clean_quest = combined_content.replace('*', '').replace('_', '').replace('`', '')
            craft_match = re.search(r"craft (\d+) ([a-z\s]+) \(\d+/\d+\)", clean_quest)
            if craft_match:
                qty, item = craft_match.groups()
                add_to_low_priority_queue(f"rpg craft {item.strip()} {qty}")
                HUD.system(f"Active Craft Quest detected: craft {qty} {item.strip()}")
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
        prefix = f"{Fore.WHITE}{Back.BLACK} 💬 {Style.RESET_ALL}"
        if content_to_log:
            print(
                f"{prefix} {Fore.WHITE}{message.author.name}"
                f"{Style.RESET_ALL}: "
                f"{HUD.clean_markdown(content_to_log)}"
            )

        if message.embeds:
            embed_dict = message.embeds[0].to_dict()
            logger.debug(
                f"Embed description: {message.embeds[0].description}"
            )
            logger.debug(f"Embed fields: {message.embeds[0].fields}")
            logger.debug(f"Full embed dict: {embed_dict}")

            # NeonUtil parsing for new messages
            if message.author.id in config.NEON_BOT_IDS and not bot_state.paused and config.card_hand_action == "auto":
                embed_text = str(embed_dict).lower()
                if "expected tc per choice" in embed_text:
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
                                    add_to_high_priority_queue("pass")
                                    HUD.system("NeonUtil: Optimal card is 'pass'")
                                    return
                                card_match = re.search(r'[HDCS][2-9AJQK]|[HDCS]10|EN', line, re.IGNORECASE)
                                if card_match:
                                    card = card_match.group(0).lower()
                                    add_to_high_priority_queue(card)
                                    HUD.system(f"NeonUtil: Optimal card is '{card}'")
                                    return
        try:
            await responseResolver(message)
        except Exception as e:
            logger.error(
                f"Error processing message: {e}\n{traceback.format_exc()}"
            )
            bot_state.coinflip_pending = False
            reset_bot_state()

    async def on_message_edit(self, before, after):
        if after.author.id not in config.NEON_BOT_IDS and after.author.id != config.EPIC_RPG_ID:
            return
        if after.channel.id != config.channelID:
            return
        if bot_state.paused:
            return
        if not after.embeds:
            return
        if before.embeds == after.embeds:
            return

        if after.author.id == config.EPIC_RPG_ID:
            try:
                await responseResolver(after)
            except Exception as e:
                logger.error(f"Error processing edited message: {e}\n{traceback.format_exc()}")
            return

        if config.card_hand_action != "auto":
            return

        embed_dict = after.embeds[0].to_dict()
        embed_text = str(embed_dict).lower()
        
        if "expected tc per choice" in embed_text:
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
                            add_to_high_priority_queue("pass")
                            HUD.system("NeonUtil: Optimal card is 'pass'")
                            return
                        card_match = re.search(r'[HDCS][2-9AJQK]|[HDCS]10|EN', line, re.IGNORECASE)
                        if card_match:
                            card = card_match.group(0).lower()
                            add_to_high_priority_queue(card)
                            HUD.system(f"NeonUtil: Optimal card is '{card}'")
                            return


UserBot = DiscordClient()
