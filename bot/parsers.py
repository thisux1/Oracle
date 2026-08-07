import re
import time
import asyncio
from bot.hud import HUD, logger
import bot.config as config
from bot.state import (
    sessionData,
    add_to_low_priority_queue,
    add_to_high_priority_queue,
    bot_state,
)
from bot.telegram import send_telegram_notification, make_channel_link
from colorama import Fore, Style
from bot.locales import t

MISC_MAX_ITEMS = 25

def _cap_misc(misc_drops, item_name, qty):
    if item_name in misc_drops:
        misc_drops[item_name] += qty
    elif len(misc_drops) < MISC_MAX_ITEMS:
        misc_drops[item_name] = qty



def process_drops(lines, player_name, loot_data):
    mob_drops = loot_data["mob_drops"]
    lootbox_drops = loot_data["lootbox_drops"]
    work_drops = loot_data["work_drops"]
    player_clean = player_name.lower().replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
    target_clean = config.user_name_lower.lower().replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
    misc = (
        loot_data.get("misc", sessionData["misc"])
        if player_clean == target_clean
        else sessionData["partner_loot_data"]["misc"]
    )
    misc_drops = misc["misc"]

    for line in lines:
        for match in config.drop_regex.finditer(line):
            qty = int(match.group(1))
            item_name = (
                match.group(2).strip().lower().replace('**', '').replace('__', '')
            )
            item_name = re.sub(
                r'\s*!.*$|\s*\(.*?\)$|\s*in one of the leaves.*$|\s*use it with.*$',
                '',
                item_name,
            ).strip()

            card_match = re.match(
                r"(common|uncommon|epic|omega|godly|eternal) card", item_name
            )
            if card_match:
                card_type = card_match.group(1)
                misc["cards"][card_type] += qty
                HUD.loot(player_name, f"{card_type} card", qty)
                continue

            if "arena cookie" in item_name:
                misc["arena_cookies"] += qty
                HUD.loot(player_name, "arena cookie", qty)
                continue

            if "coolness" in item_name:
                misc["coolness"] += qty
                HUD.loot(player_name, "coolness", qty)
                continue

            lootbox_match = re.match(
                r"(common|uncommon|rare|epic|edgy|void|eternal|galaxy) lootbox",
                item_name,
            )
            if lootbox_match and lootbox_match.group(1) in lootbox_drops:
                lootbox_type = lootbox_match.group(1)
                lootbox_drops[lootbox_type] += qty
                logger.info(
                    f"{player_name} collected: {lootbox_type} lootbox, quantity: {qty:,}"
                )
            elif item_name in mob_drops:
                mob_drops[item_name] += qty
                logger.info(
                    f"{player_name} collected: {item_name}, quantity: {qty:,}"
                )
            elif item_name in work_drops:
                work_drops[item_name] += qty
                logger.info(
                    f"{player_name} collected: {item_name}, quantity: {qty:,}"
                )
                if config.do_summer and bot_state.summer_current_work:
                    from bot.summer import increment_summer_work_count
                    increment_summer_work_count(bot_state.summer_current_work)
            else:
                _cap_misc(misc_drops, item_name, qty)
                logger.info(
                    f"{player_name} collected (misc): {item_name}, quantity: {qty:,}"
                )

            # ─── Summer Event item tracking ───
            if config.do_summer:
                if "coconut" in item_name:
                    bot_state.summer_coconut_count += qty
                    if "summer_coconuts" not in sessionData:
                        sessionData["summer_coconuts"] = 0
                    sessionData["summer_coconuts"] += qty
                    HUD.system(f"Summer: +{qty} coconut(s) (total: {bot_state.summer_coconut_count})")
                elif "mega palm log" in item_name:
                    bot_state.summer_mega_palm_log_count += qty
                    HUD.loot(player_name, item_name, qty)
                    HUD.system(f"Summer: +{qty} mega palm log(s) (total: {bot_state.summer_mega_palm_log_count})")
                elif "palm log" in item_name:
                    bot_state.summer_palm_log_count += qty
                    HUD.loot(player_name, item_name, qty)
                    HUD.system(f"Summer: +{qty} palm log(s) (total: {bot_state.summer_palm_log_count})")
                elif "summer slime" in item_name:
                    HUD.oracle("Summer Slime encontrado no hunt!")
                elif "sunglasses" in item_name:
                    HUD.oracle("Sunglasses artifact encontrado!")

        for match in config.lootbox_drop_regex.finditer(line):
            qty = int(match.group(1).replace(',', ''))
            item_name = (
                match.group(2).strip().lower().replace('**', '').replace('__', '')
            )
            item_name = re.sub(
                r'\s*!.*$|\s*\(.*?\)$|\s*in one of the leaves.*$|\s*use it with.*$',
                '',
                item_name,
            ).strip()

            card_match = re.match(
                r"(common|uncommon|epic|omega|godly|eternal) card", item_name
            )
            if card_match:
                card_type = card_match.group(1)
                misc["cards"][card_type] += qty
                logger.info(
                    f"{player_name} collected: {card_type} card, quantity: {qty:,}"
                )
                continue

            lootbox_match = re.match(
                r"(common|uncommon|rare|epic|edgy|void|eternal|galaxy) lootbox",
                item_name,
            )
            if lootbox_match and lootbox_match.group(1) in lootbox_drops:
                lootbox_type = lootbox_match.group(1)
                lootbox_drops[lootbox_type] += qty
                logger.info(
                    f"{player_name} collected: {lootbox_type} lootbox, quantity: {qty:,}"
                )
            elif item_name in mob_drops:
                mob_drops[item_name] += qty
                logger.info(
                    f"{player_name} collected: {item_name}, quantity: {qty:,}"
                )
            elif item_name in work_drops:
                work_drops[item_name] += qty
                logger.info(
                    f"{player_name} collected: {item_name}, quantity: {qty:,}"
                )
            else:
                _cap_misc(misc_drops, item_name, qty)
                logger.info(
                    f"{player_name} collected (misc): {item_name}, quantity: {qty:,}"
                )

        for match in config.special_banana_regex.finditer(line):
            qty = int(match.group(1))
            item_name = (
                match.group(2)
                .strip()
                .lower()
                .replace('**', '')
                .replace('__', '')
                .replace('??', '')
            )
            item_name = re.sub(
                r'\s*!.*$|\s*\(.*?\)$|\s*in one of the leaves.*$|\s*use it with.*$',
                '',
                item_name,
            ).strip()
            if item_name in work_drops:
                work_drops[item_name] += qty
                logger.info(
                    f"{player_name} collected: {item_name}, quantity: {qty:,}"
                )
            else:
                _cap_misc(misc_drops, item_name, qty)
                logger.info(
                    f"{player_name} collected (misc): {item_name}, quantity: {qty:,}"
                )

        for match in config.special_tree_regex.finditer(line):
            qty = int(match.group(1).replace(',', ''))
            item_name = (
                match.group(2).strip().lower().replace('**', '').replace('__', '')
            )
            item_name = re.sub(
                r'\s*!.*$|\s*\(.*?\)$|\s*in one of the leaves.*$|\s*use it with.*$',
                '',
                item_name,
            ).strip()
            if item_name in work_drops:
                work_drops[item_name] += qty
                logger.info(
                    f"{player_name} collected: {item_name}, quantity: {qty:,}"
                )
            else:
                _cap_misc(misc_drops, item_name, qty)
                logger.info(
                    f"{player_name} collected (misc): {item_name}, quantity: {qty:,}"
                )


async def rdCheckNavi(message):
    commands = [
        "hunt", "adventure", "farm", "training", "work",
        "daily", "weekly", "lootbox", "pickup", "chop", "fish", "mine", "duel", "quest",
    ]
    msg_lines = (
        message.strip().splitlines()
        if isinstance(message, str)
        else message.content.strip().splitlines()
    )
    for line in msg_lines:
        for cmd in commands:
            if cmd in line.lower():
                if cmd == "hunt" and config.do_hunt:
                    hunt_command = "rpg hunt"
                    if config.is_ascended:
                        hunt_command += " h"
                    if config.is_married:
                        hunt_command += " t"
                    add_to_low_priority_queue(hunt_command, suppress_log=True)
                    logger.info(f"Command '{hunt_command}' added to LPQ from Navi Lite.")
                elif cmd == "adventure" and config.do_adv:
                    adv_cmd = "rpg adv"
                    if config.is_ascended:
                        adv_cmd += " h"
                    if config.life_boost_before_adv in ["a", "b", "c"]:
                        add_to_high_priority_queue(f"rpg buy life boost {config.life_boost_before_adv}")
                        bot_state.pending_life_boost_buy = config.life_boost_before_adv
                        bot_state.life_boost_fallback_triggered = False
                    if config.adventure_area != "none":
                        add_to_low_priority_queue(f"rpg area {config.adventure_area}", suppress_log=True)
                        add_to_low_priority_queue(adv_cmd, suppress_log=True)
                        add_to_low_priority_queue(f"rpg area {config.current_area}", suppress_log=True)
                    else:
                        add_to_low_priority_queue(adv_cmd, suppress_log=True)
                    logger.info(f"Adventure queued from Navi Lite: {adv_cmd}")
                elif cmd == "farm" and config.do_farm:
                    farm_cmd = f"rpg farm {config.farm_seed}" if config.farm_seed and config.farm_seed.lower() != "none" else "rpg farm"
                    add_to_low_priority_queue(farm_cmd, suppress_log=True)
                    logger.info(f"Command '{farm_cmd}' added to LPQ from Navi Lite.")
                elif cmd == "training" and (config.do_training or config.do_ultr):
                    if config.training_command_sequence:
                        for tc_cmd in config.training_command_sequence:
                            add_to_low_priority_queue(tc_cmd, suppress_log=True)
                        logger.info(f"Training sequence queued from Navi Lite: {config.training_command_sequence}")
                    else:
                        add_to_low_priority_queue("rpg training", suppress_log=True)
                        logger.info("Command 'rpg training' added to LPQ from Navi Lite.")
                elif cmd == "work" and config.do_work:
                    add_to_low_priority_queue(f"rpg {config.work_command}", suppress_log=True)
                    logger.info(f"Command 'rpg {config.work_command}' added to LPQ from Navi Lite.")
                elif cmd == "daily" and config.do_daily:
                    add_to_low_priority_queue("rpg daily", suppress_log=True)
                    logger.info("Command 'rpg daily' added to LPQ from Navi Lite.")
                elif cmd == "weekly" and config.do_weekly:
                    add_to_low_priority_queue("rpg weekly", suppress_log=True)
                    logger.info("Command 'rpg weekly' added to LPQ from Navi Lite.")
                elif cmd == "lootbox" and config.do_lootbox:
                    lootbox_type = config.lootbox_type
                    if (
                        lootbox_type != "none"
                        and time.monotonic() > bot_state.lootbox_cooldown_until
                    ):
                        add_to_low_priority_queue(
                            f"rpg buy {lootbox_type}", suppress_log=True
                        )
                        bot_state.pending_lootbox_buy = lootbox_type
                        bot_state.lootbox_fallback_triggered = False
                        HUD.system(
                            f"Comando de compra de lootbox ({lootbox_type}) enfileirado a partir do Navi Lite."
                        )
                    elif time.monotonic() < bot_state.lootbox_cooldown_until:
                        HUD.system("Compra de lootbox pulada (Cooldown Financeiro).")
                elif cmd in ["pickup", "chop", "fish", "mine"] and config.do_work:
                    add_to_low_priority_queue(f"rpg {cmd}", suppress_log=True)
                    logger.info(f"Command 'rpg {cmd}' added to LPQ from Navi Lite.")
                elif cmd == "duel" and config.do_duel:
                    if bot_state.duel_paused_until > time.time():
                        logger.info("Auto-duel blocked (3h pause).")
                    else:
                        if bot_state.duel_fail_count >= 2:
                            bot_state.duel_fail_count = 0
                            bot_state.duel_paused_until = 0
                        partner_id = config.duel_partner_id
                        if partner_id and not bot_state.duel_in_progress:
                            add_to_low_priority_queue(f"rpg duel <@{partner_id}>")
                            logger.info(f"Duel queued from Navi Lite: rpg duel <@{partner_id}>")
                elif cmd == "quest" and config.do_quest:
                    add_to_high_priority_queue("rpg quest", suppress_log=True)
                    logger.info("Command 'rpg quest' added to HPQ from Navi Lite.")
                break


def _process_rd_surf_cooldown(embed_dict, target_name):
    """Summer Surf: o RD/CD é a fonte de verdade do timer interno.

    O status do surf vem na description do embed do rd/cd:
      - pronto:   "summer surf cooldown: :white_check_mark:"
      - cooldown: "summer surf cooldown: :clock4: 3h 54m 31s"
    Quando o rd/cd diz pronto, reseta o timer interno e enfileira o surf.
    Quando diz cooldown, atualiza o timer interno para refletir o rd/cd.
    """
    if not config.do_summer:
        return
    if not embed_dict:
        return
    desc = (embed_dict.get("description") or "").lower()
    if "summer surf cooldown" not in desc:
        return

    author_name = (embed_dict.get("author") or {}).get("name", "").lower()
    if author_name:
        mentioned_user = author_name.split("—")[0].lower().strip()
        mentioned_user_clean = mentioned_user.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
        target_name_clean = target_name.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
        is_ours = (
            mentioned_user == target_name
            or (target_name_clean and mentioned_user_clean == target_name_clean)
            or str(config.userID) in desc
            or str(config.userID) in author_name
        )
        if not is_ours:
            return

    if ":white_check_mark:" in desc:
        bot_state.summer_surf_cooldown_until = 0.0
        if not bot_state.surf_in_progress:
            add_to_low_priority_queue("rpg smr surf")
            HUD.command("rpg smr surf (rd ready)", priority="LPQ")
            bot_state.surf_in_progress = True
    elif ":clock4:" in desc:
        time_match = re.search(r'(\d+)h\s*(\d+)m\s*(\d+)s', desc)
        if time_match:
            seconds = int(time_match.group(1)) * 3600 + int(time_match.group(2)) * 60 + int(time_match.group(3))
            bot_state.summer_surf_cooldown_until = time.time() + seconds
            HUD.cooldown(f"Summer Surf: cooldown atualizado via rd/cd ({seconds}s restante)")


async def rdCheckEpicRPG(message):
    target_name = (
        config.user_name_lower
        if config.user_name_lower
        else config.userMentionText.lower()
        .replace('<@', '')
        .replace('>', '')
        .replace('!', '')
        .strip()
    )

    all_lines = []
    ready_for_user = False

    if message.embeds:
        embed = message.embeds[0]
        embed_dict = embed.to_dict()

        # ─── Summer Surf cooldown (RD/CD é a fonte de verdade) ───
        # O status do surf vem na DESCRIPTION do embed do rd/cd, não em fields:
        #   pronto:  "summer surf cooldown: :white_check_mark:"
        #   cooldown:"summer surf cooldown: :clock4: 3h 54m 31s"
        _process_rd_surf_cooldown(embed_dict, target_name)

        if "author" in embed_dict:
            author_name = embed_dict["author"].get("name", "").lower()
            ready_match = re.match(r"(.+?) — ready", author_name)
            if ready_match:
                mentioned_user = ready_match.group(1).lower().strip()
                mentioned_user_clean = mentioned_user.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
                target_name_clean = target_name.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
                if (
                    mentioned_user == target_name
                    or (target_name_clean and mentioned_user_clean == target_name_clean)
                    or str(config.userID) in str(embed_dict).lower()
                ):
                    ready_for_user = True
                    logger.info(
                        f"Processing ready message for user {mentioned_user}"
                    )
                    if "fields" in embed_dict:
                        for field in embed_dict["fields"]:
                            if (
                                "name" in field
                                and field["name"]
                                and "value" in field
                            ):
                                all_lines.extend(field["value"].splitlines())
                else:
                    logger.debug(
                        f"Ready message ignored (not for user): {author_name}"
                    )
                    return
    else:
        all_lines = message.content.lower().splitlines()

    if not ready_for_user and not message.content.lower():
        return

    command_aliases = {
        "hunt": ["hunt"],
        "training": ["training"],
        "adventure": ["adventure"],
        "daily": ["daily"],
        "weekly": ["weekly"],
        "farm": ["farm"],
        "work": ["work", "pickup", "chop", "fish", "mine"],
        "lootbox": ["lootbox"],
        "quest": ["quest", "epic quest"],
        "card hand": ["card hand"],
        "duel": ["duel"],
    }

    processed_commands = set()
    COMMAND_FLAGS = {
        "hunt": "do_hunt",
        "adventure": "do_adv",
        "farm": "do_farm",
        "work": "do_work",
        "training": "do_training",
        "daily": "do_daily",
        "weekly": "do_weekly",
        "quest": "do_quest",
        "lootbox": "do_lootbox",
        "card hand": "do_card_hand",
        "duel": "do_duel",
    }

    for line in all_lines:
        line = line.strip().lower()
        if "summer surf" in line.lower():
            if ":white_check_mark:" in line:
                bot_state.summer_surf_cooldown_until = 0.0
                if config.do_summer and not bot_state.surf_in_progress:
                    add_to_low_priority_queue("rpg smr surf")
                    HUD.command("rpg smr surf (rd ready)", priority="LPQ")
                    bot_state.surf_in_progress = True
            elif ":clock4:" in line:
                time_match = re.search(r'(\d+)h\s*(\d+)m\s*(\d+)s', line)
                if time_match:
                    seconds = int(time_match.group(1)) * 3600 + int(time_match.group(2)) * 60 + int(time_match.group(3))
                    bot_state.summer_surf_cooldown_until = time.time() + seconds

        if ":white_check_mark:" in line:
            clean_line = re.sub(r':[^:]+:', '', line).replace('~-~', '').strip()

            if bot_state.time_cookie_mode:
                for stop_cond in config.tc_stop_conditions:
                    if stop_cond and stop_cond in clean_line:
                        bot_state.time_cookie_mode = False
                        bot_state.tc_end_time = 0
                        HUD.system(f"Modo Time Cookie parado devido à condição: {stop_cond}")
                        asyncio.create_task(send_telegram_notification(
                            f"🎯 Modo Time Cookie desativado!\nMotivo: `{stop_cond}` está pronto."
                        ))
                    # Catch legacy TC stop
                    if "ended" in clean_line and "you lost" not in line:
                        bot_state.time_cookie_mode = False
                        bot_state.tc_end_time = 0
                        logger.info("Time cookie finalizado. Voltando ao fluxo normal.")

            for cmd_type, aliases in command_aliases.items():
                if (
                    any(alias in clean_line for alias in aliases)
                    and cmd_type not in processed_commands
                ):
                    processed_commands.add(cmd_type)

                    # ─── CHECK FLAG ───
                    flag_name = COMMAND_FLAGS.get(cmd_type)
                    if flag_name:
                        flag_value = getattr(config, flag_name, True)
                        if cmd_type == "training":
                            flag_value = flag_value or config.do_ultr
                        if not flag_value:
                            # Special case: card hand still sends notification when disabled
                            if cmd_type == "card hand":
                                current_time = time.monotonic()
                                if current_time - bot_state.last_cardhand_notification_time >= 3600:
                                    bot_state.last_cardhand_notification_time = current_time
                                    asyncio.create_task(send_telegram_notification(
                                        f"\U0001f0cf Card Hand PRONTO!\n"
                                        f"Jogue manualmente:\n"
                                        f"{make_channel_link()}"
                                    ))
                                    HUD.system("Mão de cartas pronta! Notificação de Telegram enviada.")
                                else:
                                    HUD.system("Mão de cartas pronta! Notificação omitida (cooldown de 1h ativo).")
                            else:
                                logger.debug("Command '%s' skipped (disabled via %s)", cmd_type, flag_name)
                            continue

                    if cmd_type == "hunt":
                        hunt_command = "rpg hunt"
                        if config.is_ascended:
                            hunt_command += " h"
                        if config.is_married:
                            hunt_command += " t"
                        add_to_low_priority_queue(hunt_command, suppress_log=True)
                        logger.info(
                            f"Command '{hunt_command}' added to LPQ from Epic RPG rd."
                        )

                    elif cmd_type == "farm":
                        if bot_state.farm_seed_fallback:
                            cmd = "rpg farm"
                        else:
                            cmd = f"rpg farm {config.farm_seed}" if config.farm_seed and config.farm_seed.lower() != "none" else "rpg farm"
                        add_to_low_priority_queue(cmd, suppress_log=True)
                        logger.info(
                            f"Command '{cmd}' added to LPQ from Epic RPG rd."
                        )

                    elif cmd_type == "work":
                        cmd = f"rpg {config.work_command}"
                        add_to_low_priority_queue(cmd, suppress_log=True)
                        logger.info(
                            f"Command '{cmd}' added to LPQ from Epic RPG rd."
                        )

                        # ─── Summer work queue counter ───
                        if config.do_summer and bot_state.summer_current_work:
                            from bot.summer import increment_summer_work_count
                            increment_summer_work_count(bot_state.summer_current_work)

                    elif cmd_type == "lootbox":
                        lootbox_type = config.lootbox_type
                        if (
                            lootbox_type != "none"
                            and time.monotonic() > bot_state.lootbox_cooldown_until
                        ):
                            add_to_low_priority_queue(
                                f"rpg buy {lootbox_type}", suppress_log=True
                            )
                            bot_state.pending_lootbox_buy = lootbox_type
                            bot_state.lootbox_fallback_triggered = False
                            HUD.system(
                                f"Comando de compra de lootbox ({lootbox_type}) enfileirado."
                            )
                        elif time.monotonic() < bot_state.lootbox_cooldown_until:
                            HUD.system("Compra de lootbox pulada (Cooldown Financeiro).")

                    elif cmd_type == "card hand":
                        add_to_high_priority_queue("rpg card hand")
                        HUD.system("Mão de cartas pronta! Auto-play enfileirado.")

                    elif cmd_type == "training":
                        if config.training_command_sequence:
                            for tc_cmd in config.training_command_sequence:
                                add_to_low_priority_queue(tc_cmd, suppress_log=True)
                            logger.info(f"Training sequence queued from Epic RPG rd: {config.training_command_sequence}")
                        else:
                            add_to_low_priority_queue("rpg training", suppress_log=True)
                            logger.info("Command 'rpg training' added to LPQ from Epic RPG rd.")

                    elif cmd_type == "adventure":
                        adv_cmd = "rpg adv"
                        if config.is_ascended:
                            adv_cmd += " h"
                        if config.life_boost_before_adv in ["a", "b", "c"]:
                            add_to_high_priority_queue(f"rpg buy life boost {config.life_boost_before_adv}")
                            bot_state.pending_life_boost_buy = config.life_boost_before_adv
                            bot_state.life_boost_fallback_triggered = False
                        if config.adventure_area != "none":
                            add_to_low_priority_queue(f"rpg area {config.adventure_area}", suppress_log=True)
                            add_to_low_priority_queue(adv_cmd, suppress_log=True)
                            add_to_low_priority_queue(f"rpg area {config.current_area}", suppress_log=True)
                        else:
                            add_to_low_priority_queue(adv_cmd, suppress_log=True)
                        logger.info(f"Adventure queued from Epic RPG rd: {adv_cmd}")

                    elif cmd_type == "quest":
                        add_to_high_priority_queue("rpg quest")
                        HUD.system("Quest pronta! Enfileirada na HPQ.")

                    elif cmd_type == "duel" and config.do_duel:
                        if bot_state.duel_paused_until > time.time():
                            logger.info("Auto-duel blocked from Epic RPG rd (3h pause).")
                        else:
                            if bot_state.duel_fail_count >= 2:
                                bot_state.duel_fail_count = 0
                                bot_state.duel_paused_until = 0
                            partner_id = config.duel_partner_id
                            if partner_id and not bot_state.duel_in_progress:
                                add_to_low_priority_queue(f"rpg duel <@{partner_id}>")
                                logger.info(f"Command 'rpg duel <@{partner_id}>' added to LPQ from Epic RPG rd.")

                    else:
                        cmd = f"rpg {cmd_type}"
                        add_to_low_priority_queue(cmd, suppress_log=True)
                        logger.info(
                            f"Command '{cmd}' added to LPQ from Epic RPG rd."
                        )


def format_session_data(data, title="Dados da Sessão"):
    def filter_non_zero(d):
        return {
            k: v
            for k, v in d.items()
            if (isinstance(v, (int, float)) and v > 0)
            or (
                isinstance(v, dict)
                and any(
                    filter_non_zero(v) if isinstance(v, dict) else v > 0
                    for v in v.values()
                )
            )
        }

    output = []
    output.append(f"{Fore.CYAN}=== {title} ==={Style.RESET_ALL}")

    start_time = data.get("start_time", 0.0)
    if start_time > 0.0:
        formatted = time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(start_time))
        output.append(f"{Fore.LIGHTBLACK_EX}{t('stat_since', time=formatted)}{Style.RESET_ALL}")

    command_data = filter_non_zero(data.get("command_data", {}))
    if command_data:
        output.append(f"{Fore.GREEN}{t('stat_command_data')}:{Style.RESET_ALL}")
        for cmd, count in command_data.items():
            output.append(f"  {Fore.LIGHTCYAN_EX}{cmd.capitalize()}{Style.RESET_ALL}: {Fore.YELLOW}{count}{Style.RESET_ALL}")

    progress_data = filter_non_zero(data.get("progress_data", {}))
    if progress_data:
        output.append(f"{Fore.GREEN}{t('stat_progress_data')}:{Style.RESET_ALL}")
        for stat, value in progress_data.items():
            stat_name = {
                "coins": t("stat_coins"),
                "xp": t("stat_xp"),
                "levels": t("stat_levels")
            }.get(stat.lower(), stat.capitalize())
            output.append(f"  {Fore.LIGHTCYAN_EX}{stat_name}{Style.RESET_ALL}: {Fore.YELLOW}{value:,}{Style.RESET_ALL}")

    loot_data = data.get("loot_data", {})
    if loot_data:
        output.append(f"{Fore.GREEN}{t('stat_loot_data')}:{Style.RESET_ALL}")
        for category, items in loot_data.items():
            non_zero_items = filter_non_zero(items)
            if non_zero_items:
                cat_name = {
                    "mob_drops": t("stat_mob_drops"),
                    "lootbox_drops": t("stat_lootbox_drops_sub"),
                    "work_drops": t("stat_work_drops"),
                    "farm_drops": t("stat_farm_drops"),
                }.get(category.lower(), category.replace('_', ' ').title())
                output.append(f"  {Fore.LIGHTMAGENTA_EX}{cat_name}:{Style.RESET_ALL}")
                for item, qty in non_zero_items.items():
                    output.append(f"    {Fore.WHITE}{item}{Style.RESET_ALL}: {Fore.YELLOW}{qty:,}{Style.RESET_ALL}")

    misc_data = filter_non_zero(data.get("misc", {}))
    if misc_data:
        output.append(f"{Fore.GREEN}{t('stat_misc')}:{Style.RESET_ALL}")
        for key, value in misc_data.items():
            if isinstance(value, dict):
                non_zero_items = filter_non_zero(value)
                if non_zero_items:
                    key_name = {
                        "cards": t("stat_cards"),
                    }.get(key.lower(), key.capitalize())
                    output.append(f"  {Fore.LIGHTMAGENTA_EX}{key_name}:{Style.RESET_ALL}")
                    for item, qty in non_zero_items.items():
                        output.append(f"    {Fore.WHITE}{item}{Style.RESET_ALL}: {Fore.YELLOW}{qty:,}{Style.RESET_ALL}")
            else:
                key_name = {
                    "coolness": t("stat_coolness"),
                    "arena_cookies": t("stat_arena_cookies"),
                    "guard_events": t("stat_guard_events"),
                    "personal_events": t("stat_personal_events"),
                    "pets": t("stat_pets"),
                }.get(key.lower(), key.capitalize())
                output.append(f"  {Fore.LIGHTCYAN_EX}{key_name}{Style.RESET_ALL}: {Fore.YELLOW}{value:,}{Style.RESET_ALL}")

        # ─── Summer Event stats ───
        if config.do_summer:
            output.append(f"{Fore.LIGHTMAGENTA_EX}Summer Event:{Style.RESET_ALL}")
            output.append(f"  {Fore.LIGHTCYAN_EX}Surf Rounds{Style.RESET_ALL}: {Fore.YELLOW}{bot_state.summer_surf_rounds}{Style.RESET_ALL}")
            output.append(f"  {Fore.LIGHTCYAN_EX}Coconuts{Style.RESET_ALL}: {Fore.YELLOW}{bot_state.summer_coconut_count}{Style.RESET_ALL}")
            output.append(f"  {Fore.LIGHTCYAN_EX}Tasks Claimed{Style.RESET_ALL}: {Fore.YELLOW}{len(bot_state.summer_tasks_claimed)}{Style.RESET_ALL}")

    partner_loot_data = data.get("partner_loot_data", {})
    if partner_loot_data:
        output.append(f"{Fore.GREEN}{t('stat_partner_loot')}:{Style.RESET_ALL}")
        for category, items in partner_loot_data.items():
            non_zero_items = filter_non_zero(items)
            if non_zero_items:
                cat_name = {
                    "mob_drops": t("stat_mob_drops"),
                    "lootbox_drops": t("stat_lootbox_drops_sub"),
                    "work_drops": t("stat_work_drops"),
                    "farm_drops": t("stat_farm_drops"),
                }.get(category.lower(), category.replace('_', ' ').title())
                output.append(f"  {Fore.LIGHTMAGENTA_EX}{cat_name}:{Style.RESET_ALL}")
                for item, qty in non_zero_items.items():
                    output.append(f"    {Fore.WHITE}{item}{Style.RESET_ALL}: {Fore.YELLOW}{qty:,}{Style.RESET_ALL}")

    return "\n".join(output)


def process_pet_claim_drops(embed_dict, embed_text, player_name):
    player_clean = player_name.lower().replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
    target_clean = config.user_name_lower.lower().replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
    if player_clean == target_clean:
        loot_data = sessionData["loot_data"]
        progress_data = sessionData["progress_data"]
        misc = sessionData["misc"]
    else:
        loot_data = sessionData["partner_loot_data"]
        progress_data = None
        misc = sessionData["partner_loot_data"].setdefault("misc", {})

    lines = []
    if "description" in embed_dict:
        lines.extend(embed_dict["description"].splitlines())
    for field in embed_dict.get("fields", []):
        if "value" in field:
            lines.extend(field["value"].splitlines())

    pattern = re.compile(
        r'\+\s*([\d,]+)\s*(?:<:[^:]+:\d+>|:[a-zA-Z0-9_-]+:)?\s*([a-zA-Z0-9\s()-\[\]\'’|]+)',
        re.IGNORECASE
    )

    for line in lines:
        match = pattern.search(line)
        if not match:
            continue
        
        qty = int(match.group(1).replace(',', ''))
        item_raw = match.group(2).strip().lower()

        if "|" in item_raw:
            item_raw = item_raw.split("|")[0].strip()

        item_name = item_raw
        if item_name == "coins":
            item_name = "coin"
        elif item_name.endswith(" lootbox"):
            item_name = item_name.replace(" lootbox", "")
            
        if item_name == "coin":
            if progress_data is not None:
                progress_data["coins"] += qty
                HUD.loot(player_name, "coins", qty)
            continue

        # 1. work_drops (standard logs, fish, etc.)
        work_drops = loot_data.get("work_drops", {})
        if item_name in work_drops:
            work_drops[item_name] += qty
            HUD.loot(player_name, item_name, qty)
            logger.info(f"{player_name} collected (pet claim): {item_name}, quantity: {qty:,}")
            continue
            
        matched_work = False
        for k in work_drops.keys():
            if k.replace(" ", "") == item_name.replace(" ", ""):
                work_drops[k] += qty
                HUD.loot(player_name, k, qty)
                logger.info(f"{player_name} collected (pet claim): {k}, quantity: {qty:,}")
                matched_work = True
                break
        if matched_work:
            continue

        # 2. lootbox_drops
        lootbox_drops = loot_data.get("lootbox_drops", {})
        if item_name in lootbox_drops:
            lootbox_drops[item_name] += qty
            HUD.loot(player_name, f"{item_name} lootbox", qty)
            logger.info(f"{player_name} collected (pet claim): {item_name} lootbox, quantity: {qty:,}")
            continue

        # 3. mob_drops (e.g. mermaid hair)
        mob_drops = loot_data.get("mob_drops", {})
        matched_mob = False
        for k in mob_drops.keys():
            if k in item_name or item_name in k or k.replace(" ", "") == item_name.replace(" ", ""):
                mob_drops[k] += qty
                HUD.loot(player_name, k, qty)
                logger.info(f"{player_name} collected (pet claim): {k}, quantity: {qty:,}")
                matched_mob = True
                break
        if matched_mob:
            continue

        # 4. Fallback to misc_drops
        misc_drops = misc.setdefault("misc", {})
        _cap_misc(misc_drops, item_name, qty)
        HUD.loot(player_name, item_name, qty)
        logger.info(f"{player_name} collected (pet claim misc): {item_name}, quantity: {qty:,}")


# ═══════════════════════════════════════════════
# Summer Event Parsers
# ═══════════════════════════════════════════════

SUMMER_KEYWORDS = [
    "summer", "smr", "surf", "coconut", "beach",
    "chopped coconut", "palm log",
    "sleepy potion", "summer boost", "sunglasses",
    "beach party", "color tournament", "boost", "drink", "craft",
]

CRAFT_FAIL_PATTERNS = [
    "you failed to craft",
    "craft failed",
    "you don't have the required items",
    "you don't have enough",
    "not enough",
]

COLOR_TEAM_PATTERN = re.compile(r'(blue|green|pink|yellow)\s*(team|color|drink)', re.IGNORECASE)


def detect_summer_drops(content, embed):
    if not content:
        return

    c = content.lower()

    if "coconut" in c and config.do_summer:
        coconut_match = re.findall(r'(\d+)\s*coconut', c)
        if coconut_match:
            total = sum(int(q) for q in coconut_match)
            bot_state.summer_coconut_count += total
            HUD.system(f"Summer: +{total} coconut(s) detectado(s) (total: {bot_state.summer_coconut_count})")

    if "summer slime" in c:
        HUD.oracle("Summer Slime encontrado no hunt!")

    if "mega palm log" in c:
        HUD.loot(None, "Mega Palm Log", 1)

    if "sunglasses" in c:
        HUD.oracle("Sunglasses artifact encontrado!")


def detect_work_progress(content, command_name):
    if not content or not command_name:
        return False

    c = content.lower()

    if command_name == "fish" and ("fish" in c or "normiefish" in c or "caught" in c):
        return True

    if command_name == "chop" and ("chop" in c or "coconut" in c or "palm log" in c):
        return True

    if command_name in ("fish", "chop") and "you don't have enough energy" in c:
        return False

    return False


def handle_summer_task_message(content, message=None):
    if not content or not config.do_summer:
        return

    import time
    if message:
        valid_commands = ["rpg smr quest", "rpg smr task"]
        is_valid = False
        if bot_state.last_sent_command in valid_commands:
            if time.time() - bot_state.last_sent_time <= 5.0:
                if bot_state.last_sent_channel_id == message.channel.id:
                    is_valid = True
        
        if not is_valid:
            HUD.system("Summer Tasks: Embed ignorado (não solicitado ou wrong channel)")
            return

    from bot.summer import (
        detect_tasks_in_message,
        process_task_updates,
        claim_tasks,
    )

    content = content.replace("\\n", "\n")
    tasks = detect_tasks_in_message(content)
    if not tasks:
        return

    content_hash = str(hash(str(tasks)))
    if content_hash == bot_state.summer_last_task_list:
        return
    bot_state.summer_last_task_list = content_hash

    HUD.system(f"Summer Tasks: {len(tasks)} task(s) detectadas")

    completed = process_task_updates(tasks)
    if completed:
        HUD.oracle(f"Summer Tasks completas: {', '.join(completed)}")
        claim_tasks()


def handle_summer_boost_message(content, embed):
    if not content and not embed:
        return

    from bot.summer import detect_active_boosts, handle_boost_response

    import json
    full = (content or "").lower()
    if embed:
        full += " " + json.dumps(embed.to_dict(), ensure_ascii=False).lower()

    full = full.replace("\\n", "\n")

    boosts = detect_active_boosts(full)
    handle_boost_response(boosts, raw_content=full)


def handle_surf_response(content, embed, is_user_match):
    from bot.summer import (
        detect_surf_result,
        parse_surf_wave,
        parse_surf_choices,
        choose_surf_answer,
        handle_surf_completion,
        handle_surf_cooldown_detected,
    )

    if not is_user_match:
        logger.debug("[SUMMER-DEBUG] surf_response ignorado (is_user_match=False)")
        return None

    result = detect_surf_result(content, embed)
    logger.info(f"[SUMMER-DEBUG] detect_surf_result={result!r}, content_len={len(content or '')}, embed={embed is not None}")

    if result == "prompt":
        bot_state.surf_in_progress = True
        wave = parse_surf_wave(embed, content)
        choices = parse_surf_choices(embed, content, wave=wave)
        logger.info(f"[SUMMER-DEBUG] wave={wave!r}, choices={choices!r}")

        if wave:
            strategy = config.summer_surf_strategy
            answer = choose_surf_answer(wave, strategy, choices)
            HUD.dungeon(f"Summer Surf: onda '{wave}' — escolhendo {answer} ({strategy})")
            return f"respond_{answer}"
        else:
            logger.info(f"[SUMMER-DEBUG] wave={wave!r} choices={choices!r} — pulando resposta")

    elif result == "completed":
        bot_state.surf_in_progress = False
        handle_surf_completion(1)

    elif result == "fell":
        bot_state.surf_in_progress = False
        HUD.alert("Summer Surf: caiu do surfboard")

    elif result == "cooldown":
        bot_state.surf_in_progress = False
        import json
        combined = (content or "")
        if embed:
            combined += " " + json.dumps(embed.to_dict(), ensure_ascii=False)
        handle_surf_cooldown_detected(combined)

    return None


def is_summer_related_message(content, embed):
    if content:
        c = content.lower()
        for kw in SUMMER_KEYWORDS:
            if kw in c:
                return True

    if embed:
        embed_text = str(embed.to_dict()).lower()
        for kw in SUMMER_KEYWORDS:
            if kw in embed_text:
                return True

    return False


def detect_color_team(content):
    if not content or not config.do_summer:
        return

    c = content.lower()
    match = COLOR_TEAM_PATTERN.search(c)
    if match:
        team = match.group(1).lower()
        bot_state.summer_color_team = team
        bot_state.summer_drink_this_week = True
        HUD.oracle(f"Summer: time {team.upper()} confirmado no torneio de cores!")


def detect_craft_result(content):
    if not content:
        return None

    c = content.lower()

    for pattern in CRAFT_FAIL_PATTERNS:
        if pattern in c:
            bot_state.summer_pool_float_craft_queued = False
            if "required items" in c or "don't have" in c or "not enough" in c:
                bot_state.summer_craft_fail_count += 1
                HUD.alert(f"Summer Craft: falhou — sem recursos (falha #{bot_state.summer_craft_fail_count})")

                if bot_state.summer_craft_fail_count >= 3:
                    send_telegram_notification("⚠️ Summer: craft falhou 3x hoje — recursos insuficientes")
                return "no_resources"
            else:
                bot_state.summer_craft_fail_count += 1
                HUD.alert(f"Summer Craft: falha (60% chance) #{bot_state.summer_craft_fail_count}")
                return "fail"

    if "successfully" in c and ("craft" in c or "created" in c):
        HUD.oracle("Summer Craft: sucesso!")
        if "mega surfboard" in c:
            bot_state.summer_mega_surfboard_crafted = True
            HUD.oracle("Summer Craft: MEGA Surfboard criado com sucesso!")
        for color in ["blue", "green", "pink", "yellow"]:
            if color in c:
                return f"success_{color}"
        return "success"

    return None


def parse_inventory_summer_items(content):
    if not content or not config.do_summer:
        return
    c = content.lower()
    if "inventory items" in c or "consumables" in c or "more consumables" in c:
        # Convert custom emoji tags <:emoji_name:1234567890> to text "emoji_name: " so numbers match properly
        c_clean = re.sub(r'<:([a-zA-Z0-9_]+):\d+>', r' \1: ', c)

        mega_palm_match = re.search(r'(?:mega\s*palm\s*log|megapalmlog)[^\d]*:?\s*\*?\*?\s*([\d,]+)', c_clean)
        if mega_palm_match:
            qty = int(mega_palm_match.group(1).replace(",", ""))
            bot_state.summer_mega_palm_log_count = qty
            logger.info(f"Inventory update: mega_palm_log_count = {qty}")

        palm_match = re.search(r'(?<!mega\s)(?<!mega)(?:palm\s*log|palmlog)[^\d]*:?\s*\*?\*?\s*([\d,]+)', c_clean)
        if palm_match:
            qty = int(palm_match.group(1).replace(",", ""))
            bot_state.summer_palm_log_count = qty
            logger.info(f"Inventory update: palm_log_count = {qty}")

        coconut_match = re.search(r'(?<!chopped\s)(?<!chopped)(?:coconut)[^\d]*:?\s*\*?\*?\s*([\d,]+)', c_clean)
        if coconut_match:
            qty = int(coconut_match.group(1).replace(",", ""))
            bot_state.summer_coconut_count = qty

        ruby_match = re.search(r'(?:ruby)[^\d]*:?\s*\*?\*?\s*([\d,]+)', c_clean)
        if ruby_match:
            qty = int(ruby_match.group(1).replace(",", ""))
            bot_state.inventory_ruby = qty

        mermaid_match = re.search(r'(?:mermaid\s*hair|mermaidhairs?)[^\d]*:?\s*\*?\*?\s*([\d,]+)', c_clean)
        if mermaid_match:
            qty = int(mermaid_match.group(1).replace(",", ""))
            bot_state.inventory_mermaid_hair = qty

        # --- DRINK MATERIALS ---
        chopped_match = re.search(r'(?:chopped\s*coconut)[^\d]*:?\s*\*?\*?\s*([\d,]+)', c_clean)
        if chopped_match:
            bot_state.inventory_chopped_coconut = int(chopped_match.group(1).replace(",", ""))

        normiefish_match = re.search(r'(?:normie\s*fish)[^\d]*:?\s*\*?\*?\s*([\d,]+)', c_clean)
        if normiefish_match:
            bot_state.inventory_normiefish = int(normiefish_match.group(1).replace(",", ""))

        epicfish_match = re.search(r'(?:epic\s*fish)[^\d]*:?\s*\*?\*?\s*([\d,]+)', c_clean)
        if epicfish_match:
            bot_state.inventory_epic_fish = int(epicfish_match.group(1).replace(",", ""))

        edgy_match = re.search(r'(?:edgy\s*lootbox)[^\d]*:?\s*\*?\*?\s*([\d,]+)', c_clean)
        if edgy_match:
            bot_state.inventory_edgy_lootbox = int(edgy_match.group(1).replace(",", ""))

        chip_match = re.search(r'(?:epic\s*coin|chip)[^\d]*:?\s*\*?\*?\s*([\d,]+)', c_clean)
        if chip_match:
            bot_state.inventory_chip = int(chip_match.group(1).replace(",", ""))

        epicseed_match = re.search(r'(?:epic\s*seed)[^\d]*:?\s*\*?\*?\s*([\d,]+)', c_clean)
        if epicseed_match:
            bot_state.inventory_epic_seed = int(epicseed_match.group(1).replace(",", ""))

        banana_match = re.search(r'(?:banana)[^\d]*:?\s*\*?\*?\s*([\d,]+)', c_clean)
        if banana_match:
            bot_state.inventory_banana = int(banana_match.group(1).replace(",", ""))

        lottery_match = re.search(r'(?:lottery\s*ticket)[^\d]*:?\s*\*?\*?\s*([\d,]+)', c_clean)
        if lottery_match:
            bot_state.inventory_lottery_ticket = int(lottery_match.group(1).replace(",", ""))

        # --- DRINKS ---
        blue_drink = re.search(r'(?:blue\s*drink)[^\d]*:?\s*\*?\*?\s*([\d,]+)', c_clean)
        if blue_drink:
            bot_state.inventory_blue_drink = int(blue_drink.group(1).replace(",", ""))
        
        pink_drink = re.search(r'(?:pink\s*drink)[^\d]*:?\s*\*?\*?\s*([\d,]+)', c_clean)
        if pink_drink:
            bot_state.inventory_pink_drink = int(pink_drink.group(1).replace(",", ""))

        green_drink = re.search(r'(?:green\s*drink)[^\d]*:?\s*\*?\*?\s*([\d,]+)', c_clean)
        if green_drink:
            bot_state.inventory_green_drink = int(green_drink.group(1).replace(",", ""))

        yellow_drink = re.search(r'(?:yellow\s*drink)[^\d]*:?\s*\*?\*?\s*([\d,]+)', c_clean)
        if yellow_drink:
            bot_state.inventory_yellow_drink = int(yellow_drink.group(1).replace(",", ""))


DRINK_COLORS = ["blue", "green", "pink", "yellow"]

def detect_drink_use_failure(content):
    if not content:
        return None
    c = content.lower()
    if any(kw in c for kw in ["don't have any", "don't have a", "don't have that item",
                               "no drink", "no blue drink", "no green drink",
                               "no pink drink", "no yellow drink"]):
        for color in DRINK_COLORS:
            if color in c:
                return color
        return "unknown"
    return None


def detect_drink_use_success(content):
    if not content:
        return None
    c = content.lower()
    if "drink" in c and any(kw in c for kw in ["you take a sip", "you drink", "you feel",
                                                 "you are now", "activated", "effects"]):
        for color in DRINK_COLORS:
            if color in c:
                return color
        return "unknown"
    return None
