import re
import time
import asyncio
from bot.hud import HUD, logger
import bot.config as config
from bot.state import (
    bot_state,
    sessionData,
    coinflip_strategy,
    runtimeErrors,
    add_to_low_priority_queue,
    add_to_high_priority_queue,
)
from bot.parsers import (
    process_drops,
    rdCheckNavi,
    rdCheckEpicRPG,
    format_session_data,
)
from bot.telegram import send_telegram_notification, make_channel_link
from bot.captcha import save_and_crop_attachment
from colorama import Fore, Style


async def handleCoinflipResponse(message):
    if not bot_state.coinflip_pending:
        return False
        
    embed_text = ""
    if message.embeds:
        for embed in message.embeds:
            embed_text += str(embed.to_dict()).lower() + " "
            
    msg = message.content.lower() + " " + embed_text
    if "you won" in msg:
        bot_state.coinflip_pending = False
        coinflip_strategy.win()
        bot_state.coinflip_step = coinflip_strategy.step
        bot_state.coinflip_sequence = coinflip_strategy.fib_sequence[
            : bot_state.coinflip_step
        ]
        bot_state.coinflip_base_unit = coinflip_strategy.base_unit
        bot_state.coinflip_profit = coinflip_strategy.profit
        
        # Gambling Quest Tracking
        clean_msg = msg.replace('*', '').replace('`', '')
        win_match = re.search(r'won ([\d,]+) coins', clean_msg)
        if win_match and bot_state.gamble_quest_goal > 0:
            won_amount = int(win_match.group(1).replace(",", ""))
            bot_state.gamble_quest_current += won_amount
            HUD.system(f"Casino Quest: {bot_state.gamble_quest_current:,} / {bot_state.gamble_quest_goal:,}")
            
            if bot_state.gamble_quest_current >= bot_state.gamble_quest_goal:
                bot_state.gambling_paused = True
                bot_state.gamble_quest_goal = 0
                bot_state.gamble_quest_current = 0
                HUD.system("Casino Quest completed! Gambling paused.")
                add_to_high_priority_queue("rpg quest")
                return True
                
        next_bet = coinflip_strategy.get_bet_command()
        add_to_high_priority_queue(next_bet)
        bot_state.coinflip_pending = True
        logger.info(f"Coinflip won. Next bet queued: {next_bet}")
        return True
    elif "you lost" in msg:
        bot_state.coinflip_pending = False
        coinflip_strategy.loss()
        bot_state.coinflip_step = coinflip_strategy.step
        bot_state.coinflip_sequence = coinflip_strategy.fib_sequence[
            : bot_state.coinflip_step
        ]
        bot_state.coinflip_base_unit = coinflip_strategy.base_unit
        bot_state.coinflip_profit = coinflip_strategy.profit
        if coinflip_strategy.consecutive_losses >= coinflip_strategy.max_losses:
            bot_state.gambling_paused = True
            logger.info("Max consecutive losses reached. Gambling paused.")
            add_to_high_priority_queue(
                "⚠️ Max consecutive losses reached. Gambling paused."
            )
            return True
        next_bet = coinflip_strategy.get_bet_command()
        add_to_high_priority_queue(next_bet)
        bot_state.coinflip_pending = True
        logger.info(f"Coinflip lost. Next bet queued: {next_bet}")
        return True
    return False


async def responseResolver(message):
    msg = message.content.lower()

    if message.author.id == config.EPIC_RPG_ID and config.is_married:
        logger.debug(
            f"Partner name config: '{config.partner_name}' "
            f"(lower: '{config.partner_name.lower()}')"
        )
        logger.debug(f"User name: '{config.user_name_lower}'")
        logger.debug(f"Message content: {message.content}")

    # ─── User Commands ───
    if message.author.id == config.userID:
        if msg == "rpg s t":
            add_to_low_priority_queue(
                "```" + format_session_data(sessionData, "Session Data (Main)") + "```"
            )
            logger.info("Command rpg s t queued")
            return
        elif msg == "rpg s":
            logger.info(
                "\n" + format_session_data(sessionData, "Session Data (Main)")
            )
            return
        elif msg == "rpg s p" and config.is_married:
            logger.info(
                "\n"
                + format_session_data(
                    {"partner_loot_data": sessionData["partner_loot_data"]},
                    f"Session Data (Partner: {config.partner_name})",
                )
            )
            return
        elif msg == "rpg u t":
            add_to_high_priority_queue(
                str(time.time() - config.startTime) + " seconds"
            )
            logger.info("Command rpg u t queued")
            return
        elif msg == "rpg u":
            logger.info(str(time.time() - config.startTime) + " seconds")
            return
        elif msg == "rpg f":
            if not bot_state.paused:
                bot_state.paused = True
                logger.info("Bot freeze.")
            else:
                logger.info("Bot already paused.")
            return
        elif msg == "rpg uf":
            if bot_state.paused:
                bot_state.paused = False
                logger.info("Bot started.")
            else:
                logger.info("Bot already running.")
            return
        elif msg == "sb g pause":
            bot_state.gambling_paused = True
            logger.info("Gambling paused. Normal commands enabled.")
            return
        elif msg == "sb g start":
            if coinflip_strategy:
                bot_state.gambling_paused = False
                first_bet = coinflip_strategy.get_bet_command()
                add_to_high_priority_queue(first_bet)
                bot_state.coinflip_pending = True
                logger.info(f"Gambling activated. First bet queued: {first_bet}")
            return

    # ─── Navi Lite ───
    elif message.author.id == config.NAVI_LITE_ID:
        # Se a mensagem não menciona nosso usuário, ignoramos para não pegar respostas dos outros
        if str(config.userID) not in msg and config.user_name_lower not in msg:
            return

        _temp = msg.replace(f"<@{config.userID}>", "").replace(f"<@!{config.userID}>", "").replace(config.user_name_lower, "").replace("`", "").strip()

        if "heal" in _temp:
            add_to_high_priority_queue("rpg heal")
            logger.info("Command rpg heal queued from Navi Lite")
            return

        slash_match = re.search(
            r'</(hunt|adventure|fish|chop|mine|pickup|tr|farm|training):[0-9]+>',
            _temp,
        )
        if slash_match:
            cmd_name = slash_match.group(1)
            final_cmd = "rpg hunt" if cmd_name == "hunt" else f"rpg {cmd_name}"
            if cmd_name == "hunt":
                if config.is_ascended:
                    final_cmd += " h"
                if config.is_married:
                    final_cmd += " t"
            add_to_high_priority_queue(final_cmd)
            HUD.system(f"Navi Slash command detected: {final_cmd}")
            return

        # ─── Minigame Answer Extraction ───
        # Navi Lite sends answers in two formats:
        #   1) Exact match: just "3" or "yes"
        #   2) Parentheses format: "normie fish (`1`)." → extract "1"
        paren_match = re.search(r'\(\s*([^)]+?)\s*\)', _temp)
        if paren_match:
            extracted_answer = paren_match.group(1).strip().rstrip('.')
            if extracted_answer:
                add_to_high_priority_queue(extracted_answer)
                HUD.system(f"Navi response (parentheses format): {extracted_answer}")
                return

        responses = {
            "yes": "yes", "no": "no", "a": "a", "b": "b",
            "e": "e", "l": "l", "n": "n", "p": "p",
        }
        for i in range(10):
            responses[str(i)] = str(i)

        for cmd, response in responses.items():
            if re.search(rf'^{cmd}$', _temp):
                add_to_high_priority_queue(response)
                HUD.system(f"Navi choice detected: {response}")
                return

        # Ignora avisos normais do Navi Lite que não são comandos
        if "hey! it's time for" not in msg:
            runtimeErrors.append(
                time.strftime(
                    "%Y/%m/%d %H:%M:%S - unexpected helper response " + _temp
                )
            )
            logger.error(f"Unexpected helper response: {_temp}")
        
        if any(
            cmd in msg.strip().splitlines()
            for cmd in [
                "hunt", "adventure", "farm", "training", "work",
                "daily", "weekly", "lootbox", "pickup", "chop", "fish", "mine",
            ]
        ):
            await rdCheckNavi(msg)
            logger.info(
                "Processing rdCheck for Navi Lite cooldown message (no mention)."
            )
            return

    # ─── Epic RPG Responses ───
    elif message.author.id == config.EPIC_RPG_ID:
        is_pet_message = False
        if "is approaching" in msg and config.user_name_lower in msg:
            is_pet_message = True
        elif message.embeds:
            embed_dict = message.embeds[0].to_dict()
            embed_text = str(embed_dict).lower()
            logger.debug(f"Full embed: {embed_dict}")
            if "is approaching" in embed_text and config.user_name_lower in embed_text:
                is_pet_message = True
                logger.debug(f"Pet message found in embed: {embed_text[:100]}...")

        if is_pet_message:
            add_to_low_priority_queue("feed feed feed pat pat pat")
            sessionData["misc"]["pets"] += 1
            logger.info(
                "Pet message detected: Queued 'feed feed feed pat pat pat' "
                "and incremented +1 pet"
            )
            return

        if await handleCoinflipResponse(message):
            return

        await rdCheckEpicRPG(message)

        if "you have " in msg and " seconds!" in msg:
            bot_state.minigame_pending_until = time.time() + 16
            logger.info("Minigame detected. All queues paused for 16 seconds.")
            
        if any(w in msg for w in ["better luck next time", "you got it", "you passed", "well done", "nope! it was"]):
            if bot_state.minigame_pending_until > 0:
                bot_state.minigame_pending_until = 0
                logger.info("Minigame finished. Queues resumed.")

        full_msg = msg
        if message.embeds:
            for embed in message.embeds:
                full_msg += " " + str(embed.to_dict()).lower()

        # Coinflip insufficient funds
        if (
            (
                "you have no coins to bet" in full_msg
                or ("you have" in full_msg and "coins" in full_msg and "lmao" in full_msg)
            )
            and bot_state.coinflip_pending
            and not bot_state.awaiting_withdraw
        ):
            try:
                current_balance = 0
                balance_match = re.search(
                    r'you have (\d{1,3}(?:,\d{3})*) coins', full_msg
                )
                if balance_match:
                    current_balance = int(
                        balance_match.group(1).replace(',', '')
                    )

                bot_state.awaiting_withdraw = True
                withdraw_amount = coinflip_strategy.current_bet * 2

                if current_balance > 0:
                    add_to_high_priority_queue(f"rpg withdraw {withdraw_amount}")
                else:
                    add_to_high_priority_queue("rpg withdraw all")

                logger.info(
                    f"Insufficient balance detected. "
                    f"Withdraw command queued: {withdraw_amount}"
                )

            except Exception as e:
                logger.error(f"Error processing insufficient balance: {str(e)}")
                bot_state.gambling_paused = True
                bot_state.coinflip_pending = False
                logger.info(
                    "⚠️ Error in betting system. Gambling mode paused."
                )

        elif (
            bot_state.awaiting_withdraw
            and any(word in full_msg for word in ["withdrawn", "deposited"])
            and "coins" in full_msg
        ):
            bot_state.awaiting_withdraw = False
            if "have been withdrawn" in full_msg:
                next_bet = coinflip_strategy.get_bet_command()
                add_to_high_priority_queue(next_bet)
                bot_state.coinflip_pending = True
                logger.info(f"Withdraw successful. Next bet queued: {next_bet}")
            else:
                bot_state.gambling_paused = True
                bot_state.coinflip_pending = False
                add_to_high_priority_queue(
                    "⚠️ Failed to withdraw. Gambling paused."
                )

        # ─── Jail Interaction (protest/jail commands) ───
        elif bot_state.jailed and (
            "you are in the **jail**! use the command `jail`" in msg
            or "is now in the jail" in msg
        ):
            add_to_high_priority_queue("rpg jail")
            logger.info("Sending rpg jail command due to jail")
            return
        elif bot_state.jailed and (
            "what will you do?" in msg or "protest" in msg
        ):
            add_to_high_priority_queue("protest")
            logger.info("Sending protest command due to jail")
            return
        elif bot_state.jailed and not bot_state.captcha_pending:
            return

        # ─── Embed-based Events ───
        elif len(message.embeds) != 0:
            embed_dict = message.embeds[0].to_dict()
            embed_text_raw = str(embed_dict).lower()
            # Strip Discord markdown so substring checks match cleanly
            embed_text = embed_text_raw.replace('**', '').replace('__', '').replace('`', '')
            target_name = (
                config.user_name_lower
                if config.user_name_lower
                else config.userMentionText.lower()
                .replace('<@', '')
                .replace('>', '')
            )

            is_for_user = (
                target_name in embed_text
                or str(config.userID) in embed_text
                or config.userMentionText.lower() in embed_text
            )
            if not is_for_user:
                logger.debug(
                    f"Embed message ignored (not for user): {embed_text[:100]}..."
                )
                return

            if (
                target_name in embed_text
                and "card hand" in embed_text
                and "try to get the best possible hand" in embed_text
                and bot_state.cardhand_in_progress
                and not bot_state.cardhand_first_pass_done
            ):
                bot_state.cardhand_first_pass_done = True
                add_to_high_priority_queue("pass")
                HUD.system("Card Hand embed received - sending 'pass'.")
                return

            if bot_state.cardhand_in_progress and "goldened" in embed_text:
                bot_state.cardhand_in_progress = False
                bot_state.cardhand_first_pass_done = False
                HUD.system("Card Hand finished! Queues released.")

            # ─── Pet Adventure Detection ───
            if "— pets" in embed_text:
                # rpg pets embed: check if pet is on adventure or idle
                timer_match = re.search(
                    r'status:\s*[a-z]+\s*\|\s*'
                    r'(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?',
                    embed_text
                )
                if timer_match:
                    h = int(timer_match.group(1) or 0)
                    m = int(timer_match.group(2) or 0)
                    s = int(timer_match.group(3) or 0)
                    total_seconds = h * 3600 + m * 60 + s + 30  # +30s buffer
                    bot_state.pet_adventure_return_time = time.time() + total_seconds
                    HUD.system(
                        f"Pet on adventure - returns in {h}h {m}m {s}s"
                    )
                elif "back from adventure" in embed_text:
                    bot_state.pet_adventure_return_time = 0
                    add_to_low_priority_queue("rpg pet claim")
                    HUD.system("Pet waiting for claim! Claiming...")
                elif "status: idle" in embed_text or "in adventure: 0" in embed_text:
                    add_to_low_priority_queue("rpg pet adv learn a")
                    HUD.system("Pet idle - sending to adventure!")
                return

            if "pet adventure rewards" in embed_text:
                # rpg pet claim response: rewards collected, re-send
                bot_state.pet_adventure_return_time = 0
                add_to_low_priority_queue("rpg pet adv learn a")
                HUD.system("Pet rewards claimed! Resending to adventure...")
                return

            if "— lootbox" in embed_text and "lootbox opened!" in embed_text:
                all_lines = []
                if "description" in embed_dict:
                    all_lines.extend(
                        embed_dict["description"].lower().splitlines()
                    )
                if "fields" in embed_dict:
                    for field in embed_dict["fields"]:
                        if "value" in field:
                            all_lines.extend(
                                field["value"].lower().splitlines()
                            )

                if (
                    config.is_married
                    and f"{config.user_name_lower} and {config.partner_name.lower()} are hunting together"
                    in embed_text
                ):
                    logger.info(
                        "Lootbox message detected in married mode. "
                        "Processing for both players."
                    )
                    current_player = None
                    player_lines = []
                    for line in all_lines:
                        if line.startswith(f"**{config.user_name_lower}**:"):
                            if player_lines and current_player:
                                process_drops(
                                    player_lines,
                                    current_player,
                                    sessionData["partner_loot_data"]
                                    if current_player == config.partner_name
                                    else sessionData["loot_data"],
                                )
                            current_player = config.user_name_lower
                            player_lines = []
                        elif line.startswith(
                            f"**{config.partner_name.lower()}**:"
                        ):
                            if player_lines and current_player:
                                process_drops(
                                    player_lines,
                                    current_player,
                                    sessionData["partner_loot_data"]
                                    if current_player == config.partner_name
                                    else sessionData["loot_data"],
                                )
                            current_player = config.partner_name.lower()
                            player_lines = []
                        elif line.startswith(">") and current_player:
                            player_lines.append(line[1:].strip())
                    if player_lines and current_player:
                        process_drops(
                            player_lines,
                            current_player,
                            sessionData["partner_loot_data"]
                            if current_player == config.partner_name
                            else sessionData["loot_data"],
                        )
                else:
                    process_drops(
                        all_lines,
                        config.user_name_lower,
                        sessionData["loot_data"],
                    )
                sessionData["command_data"]["lootbox"] += 1
                logger.info("Lootbox opened, drops processed")
                return

            if "  a defenseless monster" in embed_text:
                sessionData["misc"]["personal_events"] += 1
                add_to_high_priority_queue(
                    config.userOptions["zombie_horde_event_response"]
                )
                add_to_high_priority_queue(
                    "rpg area " + config.userOptions["current_area"]
                )
                logger.info("zombie horde event detected, commands queued")
            elif "matter how much you look around" in embed_text:
                sessionData["misc"]["personal_events"] += 1
                add_to_high_priority_queue("move")
                add_to_high_priority_queue("fight")
                logger.info("Command queued for move and fight event")
            elif (
                "You planted a seed, but for some reason it's not growing up"
                in embed_text
            ):
                sessionData["misc"]["personal_events"] += 1
                add_to_high_priority_queue("fight")
                logger.info("Command fight queued for seed event")
            elif "You have encountered a mysterious man" in embed_text:
                sessionData["misc"]["personal_events"] += 1
                add_to_high_priority_queue("cry")
                logger.info("Command cry queued for mysterious event")
            elif (
                "God accidentally dropped" in embed_text
                or "I have a special trade today" in embed_text
            ):
                sessionData["misc"]["personal_events"] += 1
                if (
                    embed_dict.get("fields")
                    and len(embed_dict["fields"]) > 0
                ):
                    add_to_low_priority_queue(
                        embed_dict["fields"][0]["value"]
                        .splitlines()[1]
                        .replace("**", "")
                        .lower(),
                        suppress_log=True,
                    )
                    logger.info("Command for special trade queued")
                else:
                    logger.warning(
                        "Embed with 'God accidentally dropped' or "
                        "'I have a special trade today' has no fields."
                    )

        # ─── Plain-text Responses ───
        else:
            # Pet Adventure started confirmation
            if "started an adventure and will be back in" in msg:
                clean_msg = msg.replace('*', '')
                timer_match = re.search(
                    r'back in\s*(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?', clean_msg
                )
                if timer_match:
                    h = int(timer_match.group(1) or 0)
                    m = int(timer_match.group(2) or 0)
                    s = int(timer_match.group(3) or 0)
                    total_seconds = h * 3600 + m * 60 + s + 30  # +30s buffer
                    bot_state.pet_adventure_return_time = time.time() + total_seconds
                    HUD.system(
                        f"Pet adventure started - {h}h {m}m {s}s to return"
                    )
                return

            if "found and killed a" in msg or any(
                "got" in l for l in msg.splitlines()
            ):
                msg_lines = msg.splitlines()

                if (
                    config.is_married
                    and f"{config.user_name_lower} and {config.partner_name.lower()} are hunting together"
                    in msg
                ):
                    current_player = None
                    player_lines = []
                    loot_data = sessionData["loot_data"]
                    partner_loot_data = sessionData["partner_loot_data"]
                    for line in msg_lines:
                        line_lower = line.strip().lower()
                        line_original = line.strip()
                        if line_lower.startswith(
                            f"**{config.user_name_lower}**:"
                        ):
                            if player_lines and current_player:
                                target_data = (
                                    partner_loot_data
                                    if current_player
                                    == config.partner_name.lower()
                                    else loot_data
                                )
                                process_drops(
                                    player_lines, current_player, target_data
                                )
                            current_player = config.user_name_lower
                            player_lines = []
                        elif line_lower.startswith(
                            f"**{config.partner_name.lower()}**:"
                        ):
                            if player_lines and current_player:
                                target_data = (
                                    partner_loot_data
                                    if current_player
                                    == config.partner_name.lower()
                                    else loot_data
                                )
                                process_drops(
                                    player_lines, current_player, target_data
                                )
                            current_player = config.partner_name.lower()
                            player_lines = []
                        elif (
                            line_lower.startswith(">") and current_player
                        ):
                            player_lines.append(line_original[1:].strip())
                        if " got " in line_lower:
                            if (
                                f"**{config.user_name_lower}** got"
                                in line_lower
                            ):
                                process_drops(
                                    [line_original],
                                    config.user_name_lower,
                                    sessionData["loot_data"],
                                )
                                logger.info(
                                    f"Processing drop for main user: "
                                    f"{config.user_name_lower}"
                                )
                            elif (
                                f"**{config.partner_name.lower()}** got"
                                in line_lower
                            ):
                                process_drops(
                                    [line_original],
                                    config.partner_name.lower(),
                                    sessionData["partner_loot_data"],
                                )
                                logger.info(
                                    f"Processing drop for partner: "
                                    f"{config.partner_name.lower()}"
                                )
                        coins_xp_match = (
                            config.coins_xp_regex_new.search(line_lower)
                            or config.coins_xp_regex_old.search(line_lower)
                        )
                        if coins_xp_match:
                            coins = int(
                                coins_xp_match.group(1).replace(",", "")
                            )
                            xp = int(
                                coins_xp_match.group(2).replace(",", "")
                            )
                            if f"**{config.user_name_lower}**" in line_lower:
                                sessionData["progress_data"]["coins"] += coins
                                sessionData["progress_data"]["xp"] += xp
                                logger.info(
                                    f"{Fore.YELLOW}{config.user_name_lower}"
                                    f"{Style.RESET_ALL} earned: "
                                    f"{coins:,} coins, {xp:,} XP"
                                )
                            elif (
                                f"**{config.partner_name.lower()}**"
                                in line_lower
                            ):
                                sessionData["partner_loot_data"][
                                    "progress_data"
                                ]["coins"] += coins
                                sessionData["partner_loot_data"][
                                    "progress_data"
                                ]["xp"] += xp
                                logger.info(
                                    f"{config.partner_name.lower()} earned: "
                                    f"{coins:,} coins, {xp:,} XP"
                                )
                    if player_lines and current_player:
                        target_data = (
                            partner_loot_data
                            if current_player == config.partner_name.lower()
                            else loot_data
                        )
                        process_drops(
                            player_lines, current_player, target_data
                        )

                else:
                    if "found and killed a" in msg:
                        coins_xp_match = (
                            config.coins_xp_regex_new.search(msg)
                            or config.coins_xp_regex_old.search(msg)
                        )
                        if coins_xp_match:
                            coins = int(
                                coins_xp_match.group(1).replace(",", "")
                            )
                            xp = int(
                                coins_xp_match.group(2).replace(",", "")
                            )
                            sessionData["progress_data"]["coins"] += coins
                            sessionData["progress_data"]["xp"] += xp
                            logger.info(
                                f"{Fore.YELLOW}{config.user_name_lower}"
                                f"{Style.RESET_ALL} earned: "
                                f"{coins:,} coins, {xp:,} XP"
                            )

                    process_drops(
                        msg_lines,
                        config.user_name_lower,
                        sessionData["loot_data"],
                    )

                if "leveled up" in msg:
                    if (
                        config.is_married
                        and f"{config.user_name_lower} and {config.partner_name} are hunting together"
                        in msg
                    ):
                        if f"**{config.user_name_lower}**" in msg:
                            sessionData["progress_data"]["levels"] += 1
                            logger.info(
                                f"{Fore.YELLOW}{config.user_name_lower}"
                                f"{Style.RESET_ALL} leveled up"
                            )
                        if f"**{config.partner_name}**" in msg:
                            sessionData["partner_loot_data"]["progress_data"][
                                "levels"
                            ] += 1
                            logger.info(f"{config.partner_name} leveled up")
                    else:
                        sessionData["progress_data"]["levels"] += 1
                        logger.info(
                            f"{Fore.YELLOW}{config.user_name_lower}"
                            f"{Style.RESET_ALL} leveled up"
                        )

            elif "fine, i will let you go" in msg:
                bot_state.captcha_pending = False
                bot_state.jailed = False
                logger.info("User released from captcha/jail")
            elif "seed in the ground" in msg:
                farm_drop_match = config.farm_drop_regex.search(msg)
                if farm_drop_match:
                    qty = int(farm_drop_match.group(1))
                    item = farm_drop_match.group(2).lower()
                    if item in sessionData["loot_data"]["farm_drops"]:
                        sessionData["loot_data"]["farm_drops"][item] += qty
                        logger.info(
                            f"{Fore.YELLOW}{config.user_name_lower}"
                            f"{Style.RESET_ALL} collected farm drop: "
                            f"{item}, quantity: {qty:,}"
                        )
                    else:
                        logger.warning(f"Unknown farm item: {item}")

                if "leveled up" in msg:
                    xp_gained = [
                        int(word)
                        for word in msg.replace(",", "").splitlines()[-2].split()
                        if word.isdigit()
                    ][0]
                    sessionData["progress_data"]["xp"] += xp_gained
                    sessionData["progress_data"]["levels"] += 1
                    logger.info(
                        f"{Fore.YELLOW}{config.user_name_lower}"
                        f"{Style.RESET_ALL} gained {xp_gained:,} XP "
                        f"and leveled up"
                    )
                else:
                    xp_gained = [
                        int(word)
                        for word in msg.replace(",", "").splitlines()[-1].split()
                        if word.isdigit()
                    ][0]
                    sessionData["progress_data"]["xp"] += xp_gained
                    logger.info(
                        f"{Fore.YELLOW}{config.user_name_lower}"
                        f"{Style.RESET_ALL} gained {xp_gained:,} XP"
                    )
                logger.info("Seed planted, XP updated")
            elif "well done" in msg:
                xp_gained = [
                    int(word)
                    for word in msg.replace(",", "").splitlines()[1].split()
                    if word.isdigit()
                ][0]
                sessionData["progress_data"]["xp"] += xp_gained
                logger.info(
                    f"{Fore.YELLOW}{config.user_name_lower}"
                    f"{Style.RESET_ALL} gained {xp_gained:,} XP "
                    f"for 'well done'"
                )
                if "leveled up" in msg:
                    sessionData["progress_data"]["levels"] += 1
                    logger.info(
                        f"{Fore.YELLOW}{config.user_name_lower}"
                        f"{Style.RESET_ALL} leveled up"
                    )
            else:
                if "training" not in msg:
                    for item in sessionData["loot_data"]["work_drops"]:
                        if item in msg:
                            numOfDrops = [
                                int(word)
                                for word in msg.split()
                                if word.isdigit()
                            ]
                            if len(numOfDrops) == 1:
                                sessionData["loot_data"]["work_drops"][
                                    item
                                ] += numOfDrops[0]
                                logger.info(
                                    f"{Fore.YELLOW}{config.user_name_lower}"
                                    f"{Style.RESET_ALL} collected: "
                                    f"{item}, quantity: {numOfDrops[0]:,}"
                                )
            if "you do not have this type of seed" in msg:
                add_to_low_priority_queue("rpg farm", suppress_log=True)
                logger.info("rpg farm queued due to invalid seed")
