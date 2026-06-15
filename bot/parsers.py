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



def process_drops(lines, player_name, loot_data):
    mob_drops = loot_data["mob_drops"]
    lootbox_drops = loot_data["lootbox_drops"]
    work_drops = loot_data["work_drops"]
    misc = (
        loot_data.get("misc", sessionData["misc"])
        if player_name == config.user_name_lower
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
            else:
                misc_drops[item_name] = misc_drops.get(item_name, 0) + qty
                logger.info(
                    f"{player_name} collected (misc): {item_name}, quantity: {qty:,}"
                )

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
                misc_drops[item_name] = misc_drops.get(item_name, 0) + qty
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
                misc_drops[item_name] = misc_drops.get(item_name, 0) + qty
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
                misc_drops[item_name] = misc_drops.get(item_name, 0) + qty
                logger.info(
                    f"{player_name} collected (misc): {item_name}, quantity: {qty:,}"
                )


async def rdCheckNavi(message):
    commands = [
        "hunt", "adventure", "farm", "training", "work",
        "daily", "weekly", "lootbox", "pickup", "chop", "fish", "mine", "duel",
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
                    if config.life_boost_before_adv != "none":
                        add_to_high_priority_queue("rpg withdraw all")
                        add_to_high_priority_queue(f"rpg buy life boost {config.life_boost_before_adv}")
                        add_to_high_priority_queue("rpg deposit all")
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
                    add_to_low_priority_queue(f"rpg {config.userOptions['work_command']}", suppress_log=True)
                    logger.info(f"Command 'rpg {config.userOptions['work_command']}' added to LPQ from Navi Lite.")
                elif cmd == "daily" and config.do_daily:
                    add_to_low_priority_queue("rpg daily", suppress_log=True)
                    logger.info("Command 'rpg daily' added to LPQ from Navi Lite.")
                elif cmd == "weekly" and config.do_weekly:
                    add_to_low_priority_queue("rpg weekly", suppress_log=True)
                    logger.info("Command 'rpg weekly' added to LPQ from Navi Lite.")
                elif cmd == "lootbox" and config.do_lootbox:
                    add_to_low_priority_queue("rpg lootbox", suppress_log=True)
                    logger.info("Command 'rpg lootbox' added to LPQ from Navi Lite.")
                elif cmd in ["pickup", "chop", "fish", "mine"] and config.do_work:
                    add_to_low_priority_queue(f"rpg {cmd}", suppress_log=True)
                    logger.info(f"Command 'rpg {cmd}' added to LPQ from Navi Lite.")
                elif cmd == "duel" and config.do_duel:
                    partner_id = config.duel_partner_id
                    if partner_id and not bot_state.duel_in_progress:
                        add_to_low_priority_queue(f"rpg duel <@{partner_id}>")
                        logger.info(f"Duel queued from Navi Lite: rpg duel <@{partner_id}>")
                break


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

        if "author" in embed_dict:
            author_name = embed_dict["author"].get("name", "").lower()
            ready_match = re.match(r"(.+?) — ready", author_name)
            if ready_match:
                mentioned_user = ready_match.group(1).lower().strip()
                if (
                    mentioned_user == target_name
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
                                current_time = time.time()
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
                        cmd = f"rpg farm {config.farm_seed}" if config.farm_seed and config.farm_seed.lower() != "none" else "rpg farm"
                        add_to_low_priority_queue(cmd, suppress_log=True)
                        logger.info(
                            f"Command '{cmd}' added to LPQ from Epic RPG rd."
                        )

                    elif cmd_type == "work":
                        cmd = f"rpg {config.userOptions['work_command']}"
                        add_to_low_priority_queue(cmd, suppress_log=True)
                        logger.info(
                            f"Command '{cmd}' added to LPQ from Epic RPG rd."
                        )

                    elif cmd_type == "lootbox":
                        lootbox_type = config.userOptions.get("lootbox_type", "none")
                        if (
                            lootbox_type != "none"
                            and time.time() > bot_state.lootbox_cooldown_until
                        ):
                            add_to_low_priority_queue(
                                f"rpg buy {lootbox_type}", suppress_log=True
                            )
                            bot_state.pending_lootbox_buy = lootbox_type
                            bot_state.lootbox_fallback_triggered = False
                            HUD.system(
                                f"Comando de compra de lootbox ({lootbox_type}) enfileirado."
                            )
                        elif time.time() < bot_state.lootbox_cooldown_until:
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
                        if config.life_boost_before_adv != "none":
                            add_to_high_priority_queue("rpg withdraw all")
                            add_to_high_priority_queue(f"rpg buy life boost {config.life_boost_before_adv}")
                            add_to_high_priority_queue("rpg deposit all")
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

                    elif cmd_type == "duel":
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
        output.append(f"{Fore.LIGHTBLACK_EX}desde {formatted}{Style.RESET_ALL}")

    command_data = filter_non_zero(data.get("command_data", {}))
    if command_data:
        output.append(f"{Fore.GREEN}Comandos Executados:{Style.RESET_ALL}")
        for cmd, count in command_data.items():
            output.append(f"  {Fore.LIGHTCYAN_EX}{cmd.capitalize()}{Style.RESET_ALL}: {Fore.YELLOW}{count}{Style.RESET_ALL}")

    progress_data = filter_non_zero(data.get("progress_data", {}))
    if progress_data:
        output.append(f"{Fore.GREEN}Progresso:{Style.RESET_ALL}")
        for stat, value in progress_data.items():
            stat_name = {
                "coins": "Moedas",
                "xp": "XP",
                "levels": "Níveis"
            }.get(stat.lower(), stat.capitalize())
            output.append(f"  {Fore.LIGHTCYAN_EX}{stat_name}{Style.RESET_ALL}: {Fore.YELLOW}{value:,}{Style.RESET_ALL}")

    loot_data = data.get("loot_data", {})
    if loot_data:
        output.append(f"{Fore.GREEN}Loot:{Style.RESET_ALL}")
        for category, items in loot_data.items():
            non_zero_items = filter_non_zero(items)
            if non_zero_items:
                cat_name = {
                    "mob_drops": "Drops de Monstros",
                    "lootbox_drops": "Drops de Lootbox",
                    "work_drops": "Drops de Trabalho",
                    "farm_drops": "Drops de Plantação",
                }.get(category.lower(), category.replace('_', ' ').title())
                output.append(f"  {Fore.LIGHTMAGENTA_EX}{cat_name}:{Style.RESET_ALL}")
                for item, qty in non_zero_items.items():
                    output.append(f"    {Fore.WHITE}{item}{Style.RESET_ALL}: {Fore.YELLOW}{qty:,}{Style.RESET_ALL}")

    misc_data = filter_non_zero(data.get("misc", {}))
    if misc_data:
        output.append(f"{Fore.GREEN}Diversos:{Style.RESET_ALL}")
        for key, value in misc_data.items():
            if isinstance(value, dict):
                non_zero_items = filter_non_zero(value)
                if non_zero_items:
                    key_name = {
                        "cards": "Cartas",
                    }.get(key.lower(), key.capitalize())
                    output.append(f"  {Fore.LIGHTMAGENTA_EX}{key_name}:{Style.RESET_ALL}")
                    for item, qty in non_zero_items.items():
                        output.append(f"    {Fore.WHITE}{item}{Style.RESET_ALL}: {Fore.YELLOW}{qty:,}{Style.RESET_ALL}")
            else:
                key_name = {
                    "coolness": "Estilo",
                    "arena_cookies": "Cookies de Arena",
                    "guard_events": "Eventos de Guarda",
                    "personal_events": "Eventos Pessoais",
                    "pets": "Pets",
                }.get(key.lower(), key.capitalize())
                output.append(f"  {Fore.LIGHTCYAN_EX}{key_name}{Style.RESET_ALL}: {Fore.YELLOW}{value:,}{Style.RESET_ALL}")

    partner_loot_data = data.get("partner_loot_data", {})
    if partner_loot_data:
        output.append(f"{Fore.GREEN}Loot do Parceiro:{Style.RESET_ALL}")
        for category, items in partner_loot_data.items():
            non_zero_items = filter_non_zero(items)
            if non_zero_items:
                cat_name = {
                    "mob_drops": "Drops de Monstros",
                    "lootbox_drops": "Drops de Lootbox",
                    "work_drops": "Drops de Trabalho",
                    "farm_drops": "Drops de Plantação",
                }.get(category.lower(), category.replace('_', ' ').title())
                output.append(f"  {Fore.LIGHTMAGENTA_EX}{cat_name}:{Style.RESET_ALL}")
                for item, qty in non_zero_items.items():
                    output.append(f"    {Fore.WHITE}{item}{Style.RESET_ALL}: {Fore.YELLOW}{qty:,}{Style.RESET_ALL}")

    return "\n".join(output)


def process_pet_claim_drops(embed_dict, embed_text, player_name):
    if player_name == config.user_name_lower:
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
        misc_drops[item_name] = misc_drops.get(item_name, 0) + qty
        HUD.loot(player_name, item_name, qty)
        logger.info(f"{player_name} collected (pet claim misc): {item_name}, quantity: {qty:,}")
