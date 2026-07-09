import os
import discord
import re
import time
import asyncio
import random
from typing import Optional
from bot.hud import HUD, logger
import bot.config as config
from bot.state import (
    bot_state,
    sessionData,
    initialSessionData,
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
    process_pet_claim_drops,
)
from bot.telegram import (
    send_telegram_notification,
    send_telegram_raw,
    send_telegram_html,
    make_channel_link,
    send_telegram_keyboard,
    edit_telegram_message,
    edit_telegram_caption,
    send_telegram_photo,
)
from bot.locales import t, set_language
from bot.captcha import save_and_crop_attachment
from colorama import Fore, Style

# ─── Constants ───
NEON_STALE_THRESHOLD = 20.0
NEON_RECENCY_WINDOW = 3.0
NEON_WAIT_TIMEOUT = 8.0
CARD_HAND_MAX_TURNS = 15
CARD_HAND_FIRST_TURN_TIMEOUT = 15
CARD_HAND_TURN_TIMEOUT = 5
CARD_HAND_EDIT_MAX_ITERATIONS = 30
CARD_HAND_EDIT_POLL_INTERVAL = 0.5
RUNTIME_ERRORS_MAX_SIZE = 1000
MINIGAME_PAUSE_DURATION = 16
PET_TIMER_BUFFER_SECONDS = 30
PET_COMMAND_RECENCY_WINDOW = 6.0
NEON_HISTORY_LIMIT = 5
STATUS_UPDATE_INTERVAL = 30


def _get_uptime_str():
    elapsed = int(time.time() - config.startTime)
    h, m = elapsed // 3600, (elapsed % 3600) // 60
    return f"{h}h {m}m"


def _get_state_label():
    from bot.utils import is_sleep_time
    if is_sleep_time():
        return "💤 Sleeping", "sleep"
    if bot_state.paused:
        if bot_state.watchdog_paused_until > time.monotonic():
            remaining = max(0, int(bot_state.watchdog_paused_until - time.monotonic()))
            mm, ss = remaining // 60, remaining % 60
            return f"⏸️ Watchdog Pause ({mm:02d}:{ss:02d})", "watchdog"
        return "⏸️ Paused", "paused"
    if bot_state.is_on_coffee_break:
        remaining = max(0, int(bot_state.coffee_break_end_time - time.monotonic()))
        mm, ss = remaining // 60, remaining % 60
        return f"☕ Coffee Break ({mm:02d}:{ss:02d})", "coffee"
    if bot_state.cardhand_in_progress:
        return "🃏 Card Hand", "minigame"
    if bot_state.dungeon_in_progress:
        return "⚔️ Dungeon", "minigame"
    if bot_state.duel_in_progress:
        step = bot_state.duel_step or "init"
        return f"🤺 Duel ({step})", "minigame"
    if bot_state.auto_enchant_active:
        return f"✨ Enchanting ({bot_state.auto_enchant_attempts})", "minigame"
    if bot_state.sleepet_mode:
        return f"🐾 Sleepet ({bot_state.sleepet_state or 'init'})", "special"
    if bot_state.time_cookie_mode:
        if bot_state.tc_end_time > time.monotonic():
            remaining = max(0, int(bot_state.tc_end_time - time.monotonic()))
            mm, ss = remaining // 60, remaining % 60
            return f"🍪 Time Cookie ({mm:02d}:{ss:02d})", "special"
        return f"🍪 Time Cookie (∞ × {bot_state.tc_quantity})", "special"
    if not bot_state.gambling_paused:
        return "🎰 Gambling", "special"
    return "🟢 Online", "online"


def _session_stats():
    hunts = sessionData["command_data"].get("hunt", 0) - initialSessionData["command_data"].get("hunt", 0)
    advs = sessionData["command_data"].get("adventure", 0) - initialSessionData["command_data"].get("adventure", 0)
    farms = sessionData["command_data"].get("farm", 0) - initialSessionData["command_data"].get("farm", 0)
    lb_drops = sessionData["loot_data"].get("lootbox_drops", {})
    init_lb_drops = initialSessionData["loot_data"].get("lootbox_drops", {})
    lboxes = sum(v - init_lb_drops.get(k, 0) for k, v in lb_drops.items())
    coins = sessionData["progress_data"].get("coins", 0) - initialSessionData["progress_data"].get("coins", 0)
    xp = sessionData["progress_data"].get("xp", 0) - initialSessionData["progress_data"].get("xp", 0)
    return hunts, advs, farms, lboxes, coins, xp


def build_status_discord():
    from bot.state import highPriorityQueue, lowPriorityQueue
    state_label, _ = _get_state_label()
    uptime = _get_uptime_str()
    hunts, advs, farms, lboxes, coins, xp = _session_stats()
    profile = os.path.basename(config.active_profile_path)
    user = config.user_name_lower or "unknown"
    last_cmd = bot_state.last_sent_command or "—"
    if len(last_cmd) > 25:
        last_cmd = last_cmd[:22] + "..."
    ts = int(time.time())

    lines = [
        f"```ansi",
        f"\x1b[1;36m╔══════════════════════════════════╗\x1b[0m",
        f"\x1b[1;36m║\x1b[0m   \x1b[1;37m🔮 O R A C L E   S T A T U S\x1b[0m    \x1b[1;36m║\x1b[0m",
        f"\x1b[1;36m╚══════════════════════════════════╝\x1b[0m",
        f"",
        f"\x1b[1;33m▸ Profile:\x1b[0m  {profile}",
        f"\x1b[1;33m▸ Account:\x1b[0m  @{user}",
        f"\x1b[1;33m▸ State:\x1b[0m    {state_label}",
        f"\x1b[1;33m▸ Uptime:\x1b[0m   {uptime}",
        f"",
        f"\x1b[1;34m┌─── Session Stats ───────────────┐\x1b[0m",
        f"\x1b[1;34m│\x1b[0m  Hunts: {hunts:<6} Advs: {advs:<6}  \x1b[1;34m│\x1b[0m",
        f"\x1b[1;34m│\x1b[0m  Farms: {farms:<6} Lbx:  {lboxes:<6}  \x1b[1;34m│\x1b[0m",
        f"\x1b[1;34m│\x1b[0m  Coins: +{coins:<14,}     \x1b[1;34m│\x1b[0m",
        f"\x1b[1;34m│\x1b[0m  XP:    +{xp:<14,}     \x1b[1;34m│\x1b[0m",
        f"\x1b[1;34m└────────────────────────────────-┘\x1b[0m",
        f"",
        f"\x1b[1;35m▸ Queues:\x1b[0m   HPQ: {len(highPriorityQueue)}  │  LPQ: {len(lowPriorityQueue)}",
        f"\x1b[1;35m▸ Last Cmd:\x1b[0m {last_cmd}",
        f"```",
        f"-# 🔄 Updated <t:{ts}:R>",
    ]
    return "\n".join(lines)


def build_status_telegram():
    from bot.state import highPriorityQueue, lowPriorityQueue
    state_label, _ = _get_state_label()
    uptime = _get_uptime_str()
    hunts, advs, farms, lboxes, coins, xp = _session_stats()
    last_cmd = bot_state.last_sent_command or "—"
    if len(last_cmd) > 25:
        last_cmd = last_cmd[:22] + "..."

    lines = [
        "<b>🔮 ORACLE STATUS</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"<b>State:</b>  {state_label}",
        f"<b>Uptime:</b> {uptime}",
        "",
        "<b>📊 Session Stats</b>",
        f"  Hunts: {hunts}  •  Advs: {advs}",
        f"  Farms: {farms}  •  Lbx: {lboxes}",
        f"  Coins: +{coins:,}",
        f"  XP: +{xp:,}",
        "",
        f"<b>⚡ Queues:</b> HPQ: {len(highPriorityQueue)}  |  LPQ: {len(lowPriorityQueue)}",
        f"<b>▸ Last:</b> <code>{last_cmd}</code>",
    ]
    return "\n".join(lines)


async def update_status_messages(channel):
    try:
        # Update Discord message
        if bot_state.status_discord_msg_id:
            resolved_chan = channel
            if not resolved_chan:
                import bot
                if bot.UserBot and bot.UserBot.is_ready() and not bot.UserBot.is_closed():
                    resolved_chan = bot.UserBot.get_channel(bot_state.status_discord_channel_id)
                    if not resolved_chan:
                        try:
                            resolved_chan = await bot.UserBot.fetch_channel(bot_state.status_discord_channel_id)
                        except Exception:
                            pass

            if resolved_chan:
                try:
                    msg = await resolved_chan.fetch_message(bot_state.status_discord_msg_id)
                    await msg.edit(content=build_status_discord())
                except Exception as e:
                    logger.debug(f"Status Discord edit failed: {e}")
                    bot_state.status_discord_msg_id = 0

        # Update Telegram message
        if bot_state.status_telegram_msg_id:
            try:
                await edit_telegram_message(
                    bot_state.status_telegram_msg_id,
                    build_status_telegram(),
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.debug(f"Status Telegram edit failed: {e}")
                bot_state.status_telegram_msg_id = 0
    except Exception as e:
        logger.error(f"Error in update_status_messages: {e}")


async def _status_update_loop(channel):
    while True:
        await asyncio.sleep(STATUS_UPDATE_INTERVAL)
        if not bot_state.status_discord_msg_id and not bot_state.status_telegram_msg_id:
            break
        await update_status_messages(channel)


def start_status_loop(channel):
    if bot_state.status_update_task and not bot_state.status_update_task.done():
        bot_state.status_update_task.cancel()
    bot_state.status_update_task = asyncio.create_task(_status_update_loop(channel))


async def trigger_status_command(channel=None):
    import bot
    resolved_channel = channel
    if not resolved_channel:
        if bot.UserBot and bot.UserBot.is_ready() and not bot.UserBot.is_closed():
            resolved_channel = bot.UserBot.get_channel(config.channelID)
            if not resolved_channel:
                try:
                    resolved_channel = await bot.UserBot.fetch_channel(config.channelID)
                except Exception:
                    pass

    discord_sent = False
    if resolved_channel:
        discord_text = build_status_discord()
        try:
            sent = await resolved_channel.send(discord_text)
            bot_state.status_discord_msg_id = sent.id
            bot_state.status_discord_channel_id = resolved_channel.id
            discord_sent = True
        except Exception as e:
            logger.error(f"Error sending status to Discord: {e}")

    tg_text = build_status_telegram()
    tg_id = await send_telegram_html(tg_text)
    if tg_id:
        bot_state.status_telegram_msg_id = tg_id

    start_status_loop(resolved_channel)

    if discord_sent and tg_id:
        HUD.system("Live status message sent to Discord & Telegram. Auto-updating every 30s.")
    elif discord_sent:
        HUD.system("Live status message sent to Discord. Auto-updating every 30s (Telegram skipped).")
    elif tg_id:
        HUD.system("Live status message sent to Telegram. Auto-updating every 30s (Discord offline/skipped).")
    else:
        HUD.system("Live status failed to send on both Discord and Telegram.")


async def handleCoinflipResponse(message) -> bool:
    if not bot_state.coinflip_pending:
        return False
        
    embed_text = ""
    if message.embeds:
        embed_text = " ".join(str(e.to_dict()).lower() for e in message.embeds) + " "
            
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
            HUD.system(f"Quest do Cassino: {bot_state.gamble_quest_current:,} / {bot_state.gamble_quest_goal:,}")
            
            if bot_state.gamble_quest_current >= bot_state.gamble_quest_goal:
                bot_state.gambling_paused = True
                bot_state.gamble_quest_goal = 0
                bot_state.gamble_quest_current = 0
                HUD.system("Quest do Cassino completada! Apostas pausadas.")
                add_to_high_priority_queue("rpg quest")
                return True
                
        if not bot_state.gambling_paused:
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
        if not bot_state.gambling_paused:
            next_bet = coinflip_strategy.get_bet_command()
            add_to_high_priority_queue(next_bet)
            bot_state.coinflip_pending = True
            logger.info(f"Coinflip lost. Next bet queued: {next_bet}")
        return True
    return False


active_card_hand_msg_id = None
_sent_cardhand_images = set()


def clean_embed_text_for_telegram(embed_dict: dict, is_final: bool = False) -> str:
    desc = embed_dict.get("description", "")
    
    fields_text = ""
    if embed_dict.get("fields"):
        for f in embed_dict["fields"]:
            fname = f.get('name', '')
            fval = f.get('value', '')
            fields_text += f"\n{fname}:\n{fval}"
    
    full_text = desc + fields_text

    emoji_map = {
        ":timecookie:": "🍪",
        ":guildring:": "💍",
        ":arenacookie:": "⚔️",
        ":cookie:": "🍪",
        ":gem:": "💎",
        ":moneybag:": "💰",
        ":coin:": "🪙",
        ":star:": "⭐",
        ":trophy:": "🏆",
        ":crossed_swords:": "⚔️",
        ":shield:": "🛡️",
        ":heart:": "❤️",
        ":fire:": "🔥",
        ":muscle:": "💪",
        ":scroll:": "📜",
        ":carrot:": "🥕",
        ":potato:": "🥔",
        ":bread:": "🍞",
        ":fish:": "🐟",
        ":pick:": "⛏️",
        ":ring:": "💍",
        ":crown:": "👑",
        ":medal:": "🏅",
    }
    for old, new in emoji_map.items():
        full_text = full_text.replace(old, new)

    # Remove Discord custom emojis (<:name:id> and <a:name:id>)
    full_text = re.sub(r'<a?:[^:]+:\d+>', '', full_text)
    # Remove Discord sticker/emoji ID references (e.g. <🍪1025993469426143303>)
    # These appear as <emoji + numeric_id> in reward lines
    full_text = re.sub(r'<([^<>]*?)(\d{15,})>', r'\1', full_text)
    full_text = re.sub(r':\w+:', '', full_text)
    full_text = re.sub(r'[*_~`|]+', '', full_text)
    full_text = re.sub(r'  +', ' ', full_text)
    full_text = re.sub(r'\n{3,}', '\n\n', full_text)
    full_text = full_text.replace("YOUR HAND", "🃏 SUA MÃO")
    full_text = full_text.replace("Try to get the best possible hand", "Tente conseguir a melhor mão possível")
    full_text = full_text.replace("See the list with the hands button", "")
    full_text = full_text.replace("There are 3 turns", "3 turnos")
    full_text = full_text.replace("in each turn you can decide to change a card (with its button) or pass, and you will receive a new card", "")
    full_text = full_text.replace("goldened", "✨ Concluída")
    
    # For the final result message, format reward lines nicely
    if is_final:
        lines = full_text.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            # Clean up reward lines: "+N emoji item_name" format
            reward_match = re.match(r'^([+-]\d+)\s+(.+)$', stripped)
            if reward_match:
                qty = reward_match.group(1)
                item_part = reward_match.group(2).strip()
                # Remove any remaining long numeric IDs that leaked through
                item_part = re.sub(r'\d{10,}', '', item_part).strip()
                # Collapse multiple spaces
                item_part = re.sub(r'\s{2,}', ' ', item_part)
                cleaned_lines.append(f"  {qty} {item_part}")
            elif stripped:
                cleaned_lines.append(stripped)
        full_text = '\n'.join(cleaned_lines)
    
    full_text = re.sub(r'  +', ' ', full_text)
    full_text = re.sub(r'\n{3,}', '\n\n', full_text)
    return full_text.strip()


def format_neon_for_telegram(emb: dict) -> Optional[str]:
    """Format a Neon Bot Helper embed into a beautiful Telegram message.
    Uses plain text with emojis (sent via send_telegram_raw, no Markdown parsing)."""
    lines = []
    lines.append("🔮 NEON BOT HELPER — Análise")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Title / author
    if emb.get("author", {}).get("name"):
        lines.append(f"📋 {emb['author']['name']}")
    if emb.get("title"):
        lines.append(f"🏷️ {emb['title']}")

    # Description body
    desc = emb.get("description", "")
    if desc:
        lines.append("")
        for raw_line in desc.split("\n"):
            stripped = raw_line.strip()
            if not stripped:
                continue
            if "(optimal)" in stripped.lower():
                lines.append(f"  ✅ {stripped}  ◀ OPTIMAL")
            else:
                lines.append(f"  • {stripped}")

    # Fields
    for field in emb.get("fields", []):
        fname = field.get("name", "")
        fval = field.get("value", "")
        lines.append("")
        lines.append(f"📊 {fname}")
        lines.append("─────────────────────")
        for raw_line in fval.split("\n"):
            stripped = raw_line.strip()
            if not stripped:
                continue
            if "(optimal)" in stripped.lower():
                lines.append(f"  ✅ {stripped}  ◀ OPTIMAL")
            else:
                lines.append(f"  • {stripped}")

    # Footer
    if emb.get("footer", {}).get("text"):
        lines.append("")
        lines.append(f"— {emb['footer']['text']}")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


async def find_neon_recommendation(channel) -> tuple:
    """Search channel history for Neon's card hand recommendation.
    Returns a tuple (optimal_card, formatted_telegram_text) or (None, None)."""
    try:
        import datetime
        # Search the most recent 5 messages in the channel to find Neon's helper recommendation
        async for msg in channel.history(limit=NEON_HISTORY_LIMIT):
            if msg.author.id in config.NEON_BOT_IDS and msg.embeds:
                # Security check: ignore messages older than 20 seconds to prevent reading stale cards from previous games
                msg_time = msg.edited_at or msg.created_at
                if msg_time:
                    age = (datetime.datetime.now(datetime.timezone.utc) - msg_time).total_seconds()
                    if age > NEON_STALE_THRESHOLD:
                        continue

                emb = msg.embeds[0].to_dict()
                emb_text = str(emb).lower()
                if "expected tc per choice" in emb_text:
                    formatted = format_neon_for_telegram(emb)
                    text_to_parse = ""
                    if "description" in emb and emb["description"]:
                        text_to_parse = emb["description"]
                    if not text_to_parse and "fields" in emb:
                        for f in emb["fields"]:
                            if "expected tc per choice" in f.get("name", "").lower():
                                text_to_parse = f.get("value", "")
                                break
                    if text_to_parse:
                        for line in text_to_parse.split('\n'):
                            if "(optimal)" in line.lower():
                                if "pass" in line.lower():
                                    return "pass", formatted
                                card_match = re.search(r'[HDCS][2-9AJQK]|[HDCS]10|EN', line, re.IGNORECASE)
                                if card_match:
                                    return card_match.group(0).lower(), formatted
                    # Found a Neon embed but couldn't parse optimal — still return formatted text
                    return None, formatted
    except Exception as e:
        logger.error(f"Erro ao buscar recomendação do Neon: {e}")
    return None, None


async def check_and_forward_cardhand_image(message) -> None:
    """Downloads and forwards Card Hand images (cards2.png, cards3.png, etc.)
    to Telegram. Only acts when cardhand_in_progress is active and message is on the correct channel.
    Uses a set-based deduplication to prevent race conditions between on_message_edit and the loop.
    
    Handles two cases:
    1. Image as message attachment (turns 2+): downloaded via discord.Attachment.save()
    2. Image as embed.image.url (first turn): downloaded via HTTP since Epic RPG
       sends cards2.png embedded in the embed's image field, not as an attachment.
    """
    global _sent_cardhand_images
    if not bot_state.cardhand_in_progress:
        return
    # Legacy mode: no Telegram notifications
    if config.card_hand_action == "legacy_auto":
        return
    cardhand_chan_id = getattr(bot_state, "cardhand_channel_id", config.channelID)
    if message.channel.id != cardhand_chan_id and message.channel.id != config.channelID:
        return

    # User verification: check embeds if available, but don't block on first turn
    # where attachments may arrive before embeds are populated
    if message.embeds:
        if not check_user_matches(message.embeds[0].to_dict(), config.user_name_lower, config.userID):
            return
    elif message.author.id != config.EPIC_RPG_ID:
        # If no embeds AND not from Epic RPG, skip
        return

    import os
    import aiohttp
    import options_resolver
    from bot.captcha import save_and_crop_attachment
    from bot.telegram import send_telegram_photo

    found_attachment_image = False

    # Case 1: Image as message attachment (normal case for turns 2+)
    for attachment in message.attachments:
        filename = attachment.filename.lower()
        if any(x in filename for x in ["cards", "card_hand"]):
            found_attachment_image = True
            # Atomic deduplication using message_id + filename
            dedup_key = f"{message.id}_{attachment.filename}"
            if dedup_key in _sent_cardhand_images:
                continue
            _sent_cardhand_images.add(dedup_key)
                
            photo_name = f"cardhand_{attachment.filename}"
            photo_path = os.path.join(options_resolver.USER_DATA_DIR, photo_name)
                
            try:
                await save_and_crop_attachment(attachment, out_path=photo_path)
                    
                caption = f"🃏 Card Hand — {attachment.filename}"
                embed_text = ""
                if message.embeds:
                    embed_text = str(message.embeds[0].to_dict()).lower()
                    
                if "goldened" in message.content.lower() or "goldened" in embed_text:
                    caption += " (Final)"
                else:
                    caption += f" (Turno {bot_state.cardhand_turn_count})"
                        
                await send_telegram_photo(photo_path, caption)
                HUD.cardhand(f"Imagem {attachment.filename} encaminhada ao Telegram.")
            except Exception as img_err:
                logger.error(f"Erro ao baixar/enviar imagem do Card Hand: {img_err}")
                # Remove from dedup set so it can be retried
                _sent_cardhand_images.discard(dedup_key)

    # Case 2: Image embedded in embed.image.url (first turn — cards2.png)
    # Epic RPG sends the first turn image as the embed's image field, not as an attachment.
    if not found_attachment_image and message.embeds:
        for embed in message.embeds:
            if embed.image and embed.image.url:
                image_url = embed.image.url
                # Extract filename from URL (e.g. ".../cards2.png?...")
                url_path = image_url.split("?")[0]
                url_filename = url_path.split("/")[-1].lower()
                if any(x in url_filename for x in ["cards", "card_hand"]):
                    dedup_key = f"{message.id}_embed_{url_filename}"
                    if dedup_key in _sent_cardhand_images:
                        continue
                    _sent_cardhand_images.add(dedup_key)
                    
                    photo_name = f"cardhand_{url_filename}"
                    photo_path = os.path.join(options_resolver.USER_DATA_DIR, photo_name)
                    
                    try:
                        # Download via HTTP since it's an embed image URL, not a discord.Attachment
                        async with aiohttp.ClientSession() as session:
                            async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                                if resp.status == 200:
                                    img_data = await resp.read()
                                    with open(photo_path, "wb") as f:
                                        f.write(img_data)
                                    logger.info(f"Embed image saved to {photo_path}")
                                else:
                                    logger.error(f"Failed to download embed image: HTTP {resp.status}")
                                    _sent_cardhand_images.discard(dedup_key)
                                    continue
                        
                        caption = f"🃏 Card Hand — {url_filename}"
                        embed_text = str(embed.to_dict()).lower()
                        
                        if "goldened" in message.content.lower() or "goldened" in embed_text:
                            caption += " (Final)"
                        else:
                            caption += f" (Turno {bot_state.cardhand_turn_count})"
                        
                        await send_telegram_photo(photo_path, caption)
                        HUD.cardhand(f"Imagem {url_filename} (embed) encaminhada ao Telegram.")
                    except Exception as img_err:
                        logger.error(f"Erro ao baixar/enviar imagem embed do Card Hand: {img_err}")
                        _sent_cardhand_images.discard(dedup_key)


async def interactive_card_hand_loop(message) -> None:
    global active_card_hand_msg_id
    HUD.system("Iniciando loop de Card Hand interativo-automático...")
    
    loop_start_time = time.monotonic()
    bot_state.cardhand_message = message
    if hasattr(bot_state, '_cardhand_updated_event') and bot_state._cardhand_updated_event is not None:
        bot_state._cardhand_updated_event.set()
    
    try:
        while bot_state.cardhand_in_progress:
            try:
                # Wait for up to 20 seconds for the next turn message or edit event
                await asyncio.wait_for(bot_state.cardhand_updated_event.wait(), timeout=20.0)
            except asyncio.TimeoutError:
                logger.warning("Mensagem de Card Hand não foi atualizada no tempo limite.")
                if bot_state.cardhand_message:
                    try:
                        bot_state.cardhand_message = await bot_state.cardhand_message.channel.fetch_message(bot_state.cardhand_message.id)
                    except Exception:
                        break
                else:
                    break
            
            if hasattr(bot_state, '_cardhand_updated_event') and bot_state._cardhand_updated_event is not None:
                bot_state._cardhand_updated_event.clear()
            
            message = bot_state.cardhand_message
            if not message:
                break
                
            # If the Epic RPG message doesn't have embeds yet, wait for the edit that adds it
            if not message.embeds:
                continue

            # Re-fetch from API to guarantee attachments are populated
            # (on_message often delivers attachments empty for selfbots)
            try:
                fresh = await message.channel.fetch_message(message.id)
                if fresh:
                    message = fresh
                    bot_state.cardhand_message = fresh
            except Exception:
                pass

            # Brief wait for attachment on first turn (image is often added via edit right after)
            if message.attachments is not None and len(message.attachments) == 0 and bot_state.cardhand_turn_count == 1:
                for _ in range(6):
                    await asyncio.sleep(0.5)
                    try:
                        fresh = await message.channel.fetch_message(message.id)
                        if fresh and fresh.attachments:
                            message = fresh
                            bot_state.cardhand_message = fresh
                            break
                    except Exception:
                        pass

            # Ensure the image is forwarded for this turn
            try:
                await check_and_forward_cardhand_image(message)
            except Exception as e:
                logger.error(f"Erro ao verificar/encaminhar imagem no loop do Card Hand: {e}")
                
            embed_dict = message.embeds[0].to_dict()
            embed_text = str(embed_dict).lower()
            
            # Check if game is finished — "goldened" only appears in the final embed
            if "goldened" in embed_text:
                clean_txt = clean_embed_text_for_telegram(embed_dict, is_final=True)
                final_msg = f"🎯 CARD HAND CONCLUÍDO!\n\n{clean_txt}"
                if active_card_hand_msg_id:
                    await edit_telegram_message(active_card_hand_msg_id, final_msg, None, parse_mode=None)
                else:
                    # Only send as new message if there's no existing message to edit
                    await send_telegram_raw(final_msg)
                
                bot_state.cardhand_in_progress = False
                bot_state.cardhand_first_pass_done = False
                bot_state.cardhand_turn_count = 1
                HUD.system("Card Hand concluído com sucesso!")
                active_card_hand_msg_id = None
                break
                
            # Re-check game state
            if not bot_state.cardhand_in_progress:
                break
            
            # Wait up to 8 seconds for Neon's recommendation using the event sync model
            rec = None
            neon_formatted = None
            bot_state.neon_updated_event.clear()

            # Check if there is already a very fresh recommendation (within last 3 seconds)
            # Only use if it arrived after the loop started (avoids re-sending what
            # on_message_edit already sent before the loop began)
            if bot_state.latest_neon_recommendation:
                rec_val, form_val, ts = bot_state.latest_neon_recommendation
                if time.monotonic() - ts < NEON_RECENCY_WINDOW and ts > loop_start_time:
                    rec = rec_val
                    neon_formatted = form_val

            if not rec and bot_state.cardhand_in_progress:
                try:
                    await asyncio.wait_for(bot_state.neon_updated_event.wait(), timeout=NEON_WAIT_TIMEOUT)
                    if bot_state.latest_neon_recommendation:
                        rec, neon_formatted = bot_state.latest_neon_recommendation[0], bot_state.latest_neon_recommendation[1]
                except asyncio.TimeoutError:
                    if bot_state.cardhand_in_progress:
                        rec, neon_formatted = await find_neon_recommendation(message.channel)
                
            # Determine timeout
            timeout = CARD_HAND_FIRST_TURN_TIMEOUT if bot_state.cardhand_turn_count == 1 else CARD_HAND_TURN_TIMEOUT
            rec_display = rec.upper() if rec else "PASS"
            
            clean_txt = clean_embed_text_for_telegram(embed_dict)
            msg_text = (
                f"🃏 CARD HAND ATIVO (Turno {bot_state.cardhand_turn_count})\n\n"
                f"{clean_txt}\n\n"
                f"🤖 Recomendação: {rec_display}\n"
                f"⏳ Autoplay em: {timeout}s"
            )
            
            if active_card_hand_msg_id is None:
                active_card_hand_msg_id = await send_telegram_keyboard(msg_text, None, parse_mode=None)
            else:
                await edit_telegram_message(active_card_hand_msg_id, msg_text, None, parse_mode=None)
            
            # Send Neon analysis AFTER the status message (preserves order: status first, analysis second)
            if neon_formatted:
                try:
                    await send_telegram_raw(neon_formatted, reply_to=active_card_hand_msg_id)
                    HUD.cardhand(f"Análise do Neon enviada ao Telegram (rec: {rec or 'N/A'}).")
                except Exception as neon_err:
                    logger.error(f"Erro ao enviar análise Neon ao Telegram: {neon_err}")
            
            bot_state.cardhand_user_choice = None
            user_choice = None
            
            # Poll for the duration of the timeout, checking centralized state
            for t_left in range(timeout, 0, -1):
                if not bot_state.cardhand_in_progress:
                    break
                if bot_state.cardhand_user_choice:
                    user_choice = bot_state.cardhand_user_choice.strip().lower()
                    bot_state.cardhand_user_choice = None
                    break
                
                # Edit countdown to keep it visually alive
                if t_left in [10, 5, 2] and active_card_hand_msg_id:
                    msg_text = (
                        f"🃏 CARD HAND ATIVO (Turno {bot_state.cardhand_turn_count})\n\n"
                        f"{clean_txt}\n\n"
                        f"🤖 Recomendação: {rec_display}\n"
                        f"⏳ Autoplay em: {t_left}s"
                    )
                    await edit_telegram_message(active_card_hand_msg_id, msg_text, None, parse_mode=None)
                await asyncio.sleep(1)
                
            if not bot_state.cardhand_in_progress:
                break
                
            final_choice = None
            is_auto = False
            if user_choice:
                final_choice = user_choice
                HUD.oracle(f"Intervenção manual no Card Hand: '{final_choice}'")
            else:
                final_choice = rec if rec else "pass"
                is_auto = True
                HUD.oracle(f"Nenhuma resposta manual. Enviando escolha automática: '{final_choice}'")
                
            choice_label = f"🤖 {final_choice.upper()}" if is_auto else f"📲 {final_choice.upper()}"
            
            await edit_telegram_message(
                active_card_hand_msg_id,
                f"🃏 CARD HAND ATIVO (Turno {bot_state.cardhand_turn_count})\n\n{clean_txt}\n\n{choice_label}",
                None, parse_mode=None
            )
            
            # Send choice to Discord channel
            await message.channel.send(final_choice)
            bot_state.cardhand_turn_count += 1
            
            # Reset Neon recommendation to avoid using stale data on the next turn
            bot_state.latest_neon_recommendation = None
            
    except Exception as e:
        logger.error(f"Erro no loop interativo de Card Hand: {e}")
    finally:
        bot_state.cardhand_in_progress = False
        bot_state.cardhand_first_pass_done = False
        bot_state.cardhand_turn_count = 1
        bot_state.last_sent_cardhand_image = None
        bot_state.cardhand_user_choice = None
        bot_state.cardhand_message = None
        _sent_cardhand_images.clear()
        if hasattr(bot_state, '_cardhand_updated_event') and bot_state._cardhand_updated_event is not None:
            bot_state._cardhand_updated_event.clear()
        active_card_hand_msg_id = None


def check_user_matches(embed_dict: dict, target_username: str, target_userid: Optional[int]) -> bool:
    if not embed_dict:
        return False
    title = (embed_dict.get("title", "") or "").lower()
    author_name = (embed_dict.get("author", {}).get("name", "") or "").lower()
    
    for text in [author_name, title]:
        if not text:
            continue
        text = text.replace("’", "'").replace(" - ", " — ")
        
        if target_userid and str(target_userid) in text:
            return True
            
        part = text.split(" — ")[0].split("'s")[0].strip()
        if target_username:
            t_clean = target_username.lower().strip()
            p_clean = part.lower().strip()
            if p_clean == t_clean or t_clean in p_clean or p_clean in t_clean:
                return True
            t_norm = t_clean.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
            p_norm = p_clean.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
            if t_norm and p_norm and (p_norm == t_norm or t_norm in p_norm or p_norm in t_norm):
                return True
            
    return False


async def handle_sleepet_summary(embed_dict: dict, embed_text: str) -> None:
    if bot_state.sleepet_state != "waiting_summary":
        return
    if not check_user_matches(embed_dict, config.user_name_lower, config.userID):
        logger.debug("Sleepet summary ignored: Username mismatch.")
        return

    # Parse ready to claim and pet count
    ready_claim_match = re.search(r'ready to claim:\s*(\d+)/(\d+)', embed_text)
    pet_count_match = re.search(r'pet count:\s*(\d+)/(\d+)', embed_text)

    if not ready_claim_match or not pet_count_match:
        logger.warning(f"Could not parse sleepet summary from embed: {embed_text}")
        return

    ready_to_claim = int(ready_claim_match.group(1))
    total_on_adventure = int(ready_claim_match.group(2))
    total_pets = int(pet_count_match.group(1))
    idle_pets = total_pets - total_on_adventure

    if total_pets == 0:
        bot_state.sleepet_mode = False
        bot_state.sleepet_state = None
        HUD.alert("Sleepet Mode desativado: Nenhum pet na conta!")
        await send_telegram_notification("⚠️ *Sleepet Mode desativado:* Nenhum pet encontrado na conta!")
        add_to_high_priority_queue("rpg rd")
        return

    HUD.system(f"[Sleepet] Summary parsed: Ready={ready_to_claim}, OnAdv={total_on_adventure}, Total={total_pets}, Idle={idle_pets}")

    if ready_to_claim > 0:
        bot_state.sleepet_state = "waiting_claim"
        bot_state.last_sleepet_cmd_time = time.monotonic()
        add_to_high_priority_queue("rpg pet claim")
        HUD.system("[Sleepet] Queued claim.")
    elif idle_pets > 0:
        bot_state.sleepet_state = "waiting_adventure"
        bot_state.last_sleepet_cmd_time = time.monotonic()
        add_to_high_priority_queue(config.pet_adventure_command)
        HUD.system(f"[Sleepet] Queued adventure: {config.pet_adventure_command}")
    else:
        # All on adventure
        bot_state.sleepet_state = "waiting_potion"
        bot_state.last_sleepet_cmd_time = time.monotonic()
        add_to_high_priority_queue("rpg use sleepet potion")
        HUD.system("[Sleepet] Queued use sleepet potion.")


async def handle_sleepet_claim(embed_dict: dict, embed_text: str) -> None:
    if bot_state.sleepet_state != "waiting_claim":
        return
    if not check_user_matches(embed_dict, config.user_name_lower, config.userID):
        return

    # Check if pet inventory is full (Purrency check)
    if "purrency" in embed_text.lower():
        bot_state.sleepet_mode = False
        bot_state.sleepet_state = None
        HUD.alert("Sleepet Mode desativado: Inventário de pets cheio (Purrency ganho)!")
        await send_telegram_notification("⚠️ *Sleepet Mode desativado:* Inventário de pets cheio (Purrency ganho)!")
        add_to_high_priority_queue("rpg rd")
        return

    HUD.system("[Sleepet] Recompensas coletadas! Enviando pet para aventura...")
    bot_state.sleepet_state = "waiting_adventure"
    bot_state.last_sleepet_cmd_time = time.monotonic()
    add_to_high_priority_queue(config.pet_adventure_command)


async def handle_sleepet_adv(message, msg) -> None:
    if bot_state.sleepet_state != "waiting_adventure":
        return
    # Verify that it is for the user
    is_for_us = False
    
    # 1. Check if it is a direct reply to our command
    if message.reference and message.reference.resolved:
        ref = message.reference.resolved
        if hasattr(ref, "author") and ref.author.id == config.userID:
            is_for_us = True

    # 2. Validation by time interval and compatible command
    # If the last sent command contained "pet" and ("adv" or "adventure"), and was sent within 6 seconds
    current_time = time.monotonic()
    time_since_last_cmd = current_time - bot_state.last_sent_time
    
    is_recent_our_command = False
    if bot_state.last_sent_command:
        last_cmd = bot_state.last_sent_command.lower()
        if "pet" in last_cmd and ("adv" in last_cmd or "adventure" in last_cmd) and time_since_last_cmd < PET_COMMAND_RECENCY_WINDOW:
            is_recent_our_command = True
            
    if is_recent_our_command:
        is_for_us = True
    elif bot_state.sleepet_mode and bot_state.sleepet_state == "waiting_adventure" and time_since_last_cmd < PET_COMMAND_RECENCY_WINDOW:
        is_for_us = True

    if not is_for_us:
        logger.debug("handle_sleepet_adv ignored: not for us.")
        return

    # Check for instant returns
    if any(term in msg for term in ["travel in time", "back instantly", "are back instantly"]):
        HUD.system("[Sleepet] Retorno instantâneo detectado na aventura! Re-claimando...")
        bot_state.sleepet_state = "waiting_claim"
        bot_state.last_sleepet_cmd_time = time.monotonic()
        add_to_high_priority_queue("rpg pet claim")
        return

    HUD.system("[Sleepet] Aventura iniciada com sucesso! Usando poção sleepet...")
    bot_state.sleepet_state = "waiting_potion"
    bot_state.last_sleepet_cmd_time = time.monotonic()
    add_to_high_priority_queue("rpg use sleepet potion")


# [ignoring loop detection]
CONFIG_CATEGORIES = {
    "commands": {
        "title": "⚙️ Categorias de Comando (Ativar/Desativar)",
        "params": {
            "do_hunt": {"desc": "Ativa a caça automática (rpg hunt).", "type": "bool", "syntax": "do_hunt <true/false>"},
            "do_adv": {"desc": "Ativa a aventura automática (rpg adv).", "type": "bool", "syntax": "do_adv <true/false>"},
            "do_farm": {"desc": "Ativa o cultivo automático (rpg farm).", "type": "bool", "syntax": "do_farm <true/false>"},
            "do_work": {"desc": "Ativa o trabalho automático (rpg work).", "type": "bool", "syntax": "do_work <true/false>"},
            "do_training": {"desc": "Ativa o treino automático (rpg tr).", "type": "bool", "syntax": "do_training <true/false>"},
            "do_daily": {"desc": "Resgata o daily automático (rpg daily).", "type": "bool", "syntax": "do_daily <true/false>"},
            "do_weekly": {"desc": "Resgata o weekly automático (rpg weekly).", "type": "bool", "syntax": "do_weekly <true/false>"},
            "do_quest": {"desc": "Aceita/completa quests automáticas.", "type": "bool", "syntax": "do_quest <true/false>"},
            "do_lootbox": {"desc": "Compra/abre lootboxes automaticamente.", "type": "bool", "syntax": "do_lootbox <true/false>"},
            "do_dungeon": {"desc": "Entra em dungeons automaticamente.", "type": "bool", "syntax": "do_dungeon <true/false>"},
            "do_card_hand": {"desc": "Joga/alerta minigame card hand.", "type": "bool", "syntax": "do_card_hand <true/false>"},
            "do_duel": {"desc": "Ativa automação de duelos.", "type": "bool", "syntax": "do_duel <true/false>"},
            "do_pet": {"desc": "Ativa envios de aventuras de pet.", "type": "bool", "syntax": "do_pet <true/false>"},
            "do_ultr": {"desc": "Ativa sequência de treino ULTR.", "type": "bool", "syntax": "do_ultr <true/false>"}
        }
    },
    "account": {
        "title": "👤 Configurações de Conta",
        "params": {
            "user_token": {"desc": "Token de login do Discord (ocultado por segurança).", "type": "token", "syntax": "user_token <token>"},
            "channel_id": {"desc": "ID do canal do Discord onde o bot caça.", "type": "int", "syntax": "channel_id <id>"},
            "guild_id": {"desc": "ID do servidor/guild do Discord.", "type": "int", "syntax": "guild_id <id>"},
            "username": {"desc": "Nome de usuário do jogador (minúsculo).", "type": "str", "syntax": "username <name>"},
            "admin_ids": {"desc": "IDs de administradores separados por vírgula.", "type": "str", "syntax": "admin_ids <id1,id2>"},
            "is_married": {"desc": "Habilita verificações de casamento.", "type": "bool", "syntax": "is_married <true/false>"},
            "partner_name": {"desc": "Nome do parceiro/casamento (minúsculo).", "type": "str", "syntax": "partner_name <name>"},
            "is_ascended": {"desc": "Habilita comportamento de jogador ascendido.", "type": "bool", "syntax": "is_ascended <true/false>"}
        }
    },
    "safety": {
        "title": "🚨 Segurança e Anti-Detecção",
        "params": {
            "random_interval": {"desc": "Atraso randômico entre comandos (+1-4s).", "type": "bool", "syntax": "random_interval <true/false>"},
            "typo_chance": {"desc": "Chance de erro de digitação proposital (0.0 a 1.0).", "type": "float", "syntax": "typo_chance <chance>"},
            "sleep_at": {"desc": "Horário para o bot dormir (formato HH:MM).", "type": "time", "syntax": "sleep_at <HH:MM>"},
            "wake_up_at": {"desc": "Horário para o bot acordar (formato HH:MM).", "type": "time", "syntax": "wake_up_at <HH:MM>"},
            "telegram_bot_token": {"desc": "Token do bot do Telegram.", "type": "token", "syntax": "telegram_bot_token <token>"},
            "telegram_chat_id": {"desc": "ID do chat de notificações do Telegram.", "type": "str", "syntax": "telegram_chat_id <chat_id>"}
        }
    },
    "items": {
        "title": "📦 Ajustes de Itens e Áreas",
        "params": {
            "seed": {"desc": "Semente para plantar no rpg farm.", "type": "str", "syntax": "seed <carrot/potato/etc>"},
            "work_command": {"desc": "Comando executado no rpg work.", "type": "str", "syntax": "work_command <chainsaw/pickaxe/etc>"},
            "lootbox_type": {"desc": "Lootbox para comprar (ex: ed lb, ep lb, none).", "type": "str", "syntax": "lootbox_type <type>"},
            "life_boost_before_adv": {"desc": "Poção de life boost (a, b, c, none).", "type": "str", "syntax": "life_boost_before_adv <a/b/c/none>"},
            "adventure_area": {"desc": "Área máxima de segurança para aventura.", "type": "str", "syntax": "adventure_area <area/none>"},
            "current_area": {"desc": "Área para reentrar após teletransporte.", "type": "str", "syntax": "current_area <area/none>"},
            "pet_adventure_command": {"desc": "Comando de pet adventure (ex: learn a).", "type": "str", "syntax": "pet_adventure_command <command>"}
        }
    },
    "minigames": {
        "title": "🎮 Minijogos e Coinflip",
        "params": {
            "card_hand_action": {"desc": "Ação do Card Hand (auto ou notify).", "type": "str", "syntax": "card_hand_action <auto/notify>"},
            "tc_quantity": {"desc": "Quantidade padrão de cookies por ativação.", "type": "int", "syntax": "tc_quantity <number>"},
            "tc_stop_on": {"desc": "Eventos que param o TC (ex: dungeon, miniboss).", "type": "str", "syntax": "tc_stop_on <events/none>"},
            "is_eternal": {"desc": "Habilita dungeon eternal e loop de bite.", "type": "bool", "syntax": "is_eternal <true/false>"},
            "eternal_tier": {"desc": "Nível da dungeon eternal (t1-t10).", "type": "str", "syntax": "eternal_tier <t1-t10>"},
            "win_duel": {"desc": "Escolhe arma para ganhar duelos (se False, perde).", "type": "bool", "syntax": "win_duel <true/false>"},
            "duel_partner_id": {"desc": "ID do parceiro de duelo cooperativo.", "type": "str", "syntax": "duel_partner_id <id>"},
            "bankroll": {"desc": "Capital máximo para Fibonacci.", "type": "int", "syntax": "bankroll <number>"},
            "max_losses": {"desc": "Derrotas consecutivas limite no Fibonacci.", "type": "int", "syntax": "max_losses <number>"},
            "initial_step": {"desc": "Aposta inicial no Fibonacci.", "type": "int", "syntax": "initial_step <number>"}
        }
    }
}


TOGGLE_ALIASES = {
    "do_hunt": "hunt",
    "do_adv": "adv",
    "do_farm": "farm",
    "do_work": "work",
    "do_training": "train",
    "do_daily": "daily",
    "do_weekly": "weekly",
    "do_quest": "quest",
    "do_lootbox": "lootbox",
    "do_dungeon": "dungeon",
    "do_card_hand": "card",
    "do_duel": "duel",
    "do_pet": "pet",
    "do_ultr": "ultr",
    "is_married": "married",
    "is_ascended": "ascended",
    "random_interval": "delay",
    "is_eternal": "eternal",
    "win_duel": "winduel"
}


async def _update_config_param(param_name: str, new_value: str, details: dict) -> str:
    import options_resolver
    p_type = details["type"]
    val_to_save = new_value
    
    if p_type == "bool":
        val_lower = new_value.lower()
        if val_lower in ("true", "yes", "1", "on"):
            val_to_save = "true"
        elif val_lower in ("false", "no", "0", "off"):
            val_to_save = "false"
        else:
            return f"❌ Erro: O valor para `{param_name}` deve ser `true` ou `false`."
            
    elif p_type == "int":
        if not new_value.isdigit():
            return f"❌ Erro: O valor para `{param_name}` deve ser um número inteiro positivo."
            
    elif p_type == "float":
        try:
            val_float = float(new_value)
            if not (0.0 <= val_float <= 1.0):
                return f"❌ Erro: O valor para `{param_name}` deve ser um número decimal entre 0.0 e 1.0."
            val_to_save = str(val_float)
        except ValueError:
            return f"❌ Erro: O valor para `{param_name}` deve ser um número decimal (ex: 0.05)."
            
    elif p_type == "time":
        if new_value.lower() in ("none", ""):
            val_to_save = ""
        else:
            import re
            if not re.match(r"^\d{2}:\d{2}$", new_value):
                return f"❌ Erro: O valor para `{param_name}` deve estar no formato 24h `HH:MM` ou ser `none`."
                
    elif param_name == "lootbox_type":
        val_lower = new_value.lower()
        valid_lbs = {"common", "uncommon", "rare", "epic", "edgy", "common lb", "uncommon lb", "rare lb", "epic lb", "edgy lb", "none"}
        if val_lower not in valid_lbs:
            return f"❌ Erro: Lootbox inválida. Escolha entre: `common`, `uncommon`, `rare`, `epic`, `edgy` ou `none`."
        norm_map = {
            "common": "common lb", "uncommon": "uncommon lb", "rare": "rare lb",
            "epic": "ep lb", "edgy": "ed lb", "none": "none"
        }
        val_to_save = norm_map.get(val_lower, val_lower)
        
    elif param_name == "life_boost_before_adv":
        val_lower = new_value.lower()
        if val_lower not in ("a", "b", "c", "none"):
            return f"❌ Erro: O valor deve ser `a`, `b`, `c` ou `none`."
        val_to_save = val_lower
        
    elif param_name == "card_hand_action":
        val_lower = new_value.lower()
        if val_lower not in ("auto", "legacy_auto", "notify"):
            return f"❌ Erro: O valor deve ser `auto`, `legacy_auto` ou `notify`."
        val_to_save = val_lower

    profile_path = config.active_profile_path or "options.ini"
    old_value = config.userOptions.get(param_name, "")
    
    if old_value == val_to_save:
        return f"💡 O parâmetro `{param_name}` já está definido como `{new_value}`."
        
    try:
        options_resolver.editData(param_name, val_to_save, filePath=profile_path)
        config.reload_config()
        
        disp_old = str(old_value).strip() if old_value is not None else ""
        disp_new = str(val_to_save).strip() if val_to_save is not None else ""
        if not disp_old:
            disp_old = "none"
        if not disp_new:
            disp_new = "none"
            
        if p_type == "token":
            disp_old = disp_old[:4] + "..." + disp_old[-4:] if len(disp_old) > 8 else "********"
            disp_new = disp_new[:4] + "..." + disp_new[-4:] if len(disp_new) > 8 else "********"
            
        return f"✅ **Configuração atualizada com sucesso!**\nParâmetro `{param_name}` alterado de `{disp_old}` para `{disp_new}` no perfil `{os.path.basename(profile_path)}`."
    except Exception as e:
        logger.error(f"Erro ao salvar configuração {param_name}: {e}")
        return f"❌ Erro ao salvar configuração: {e}"


def find_bool_param(name: str) -> str | None:
    norm = name.lower().replace(" ", "").replace("_", "").replace("-", "").strip()
    aliases = {
        "hunt": "do_hunt", "dohunt": "do_hunt",
        "adv": "do_adv", "doadv": "do_adv", "adventure": "do_adv",
        "farm": "do_farm", "dofarm": "do_farm",
        "work": "do_work", "dowork": "do_work",
        "train": "do_training", "training": "do_training", "dotraining": "do_training", "tr": "do_training",
        "daily": "do_daily", "dodaily": "do_daily",
        "weekly": "do_weekly", "doweekly": "do_weekly",
        "quest": "do_quest", "doquest": "do_quest",
        "lootbox": "do_lootbox", "dolootbox": "do_lootbox", "lb": "do_lootbox",
        "dungeon": "do_dungeon", "dodungeon": "do_dungeon", "dg": "do_dungeon",
        "card": "do_card_hand", "hand": "do_card_hand", "cardhand": "do_card_hand", "docardhand": "do_card_hand", "do_card_hand": "do_card_hand",
        "duel": "do_duel", "doduel": "do_duel",
        "pet": "do_pet", "dopet": "do_pet",
        "ultr": "do_ultr", "doultr": "do_ultr",
        "married": "is_married", "ismarried": "is_married", "marry": "is_married",
        "ascended": "is_ascended", "isascended": "is_ascended", "ascend": "is_ascended",
        "randominterval": "random_interval", "interval": "random_interval", "randomdelay": "random_interval", "delay": "random_interval",
        "eternal": "is_eternal", "iseternal": "is_eternal",
        "winduel": "win_duel", "win_duels": "win_duel"
    }
    return aliases.get(norm)


def resolve_parameter_and_value(text: str) -> tuple[str, str, dict] | None:
    cleaned = text.strip()
    if "=" in cleaned:
        parts_eq = cleaned.split("=", 1)
        param_part = parts_eq[0].strip()
        val_part = parts_eq[1].strip()
    else:
        tokens = cleaned.split()
        if not tokens:
            return None
        param_part = ""
        val_part = ""
        
        # Build map of param keys and aliases
        param_map = {}
        for cat_name, cat_data in CONFIG_CATEGORIES.items():
            for p_name, p_details in cat_data["params"].items():
                param_map[p_name] = (p_name, p_details)
                norm_canonical = p_name.lower().replace("_", "").replace("-", "")
                param_map[norm_canonical] = (p_name, p_details)
                
        aliases = {
            "hunt": "do_hunt", "dohunt": "do_hunt",
            "adv": "do_adv", "doadv": "do_adv", "adventure": "do_adv",
            "farm": "do_farm", "dofarm": "do_farm",
            "work": "work_command", "dowork": "do_work",
            "train": "do_training", "training": "do_training", "dotraining": "do_training", "tr": "do_training",
            "daily": "do_daily", "dodaily": "do_daily",
            "weekly": "do_weekly", "doweekly": "do_weekly",
            "quest": "do_quest", "doquest": "do_quest",
            "lootbox": "do_lootbox", "dolootbox": "do_lootbox", "lb": "do_lootbox",
            "dungeon": "do_dungeon", "dodungeon": "do_dungeon", "dg": "do_dungeon",
            "card": "do_card_hand", "hand": "do_card_hand", "cardhand": "do_card_hand", "docardhand": "do_card_hand", "do_card_hand": "do_card_hand",
            "duel": "do_duel", "doduel": "do_duel",
            "pet": "do_pet", "dopet": "do_pet",
            "ultr": "do_ultr", "doultr": "do_ultr",
            "token": "user_token", "discordtoken": "user_token",
            "channel": "channel_id",
            "guild": "guild_id", "server": "guild_id",
            "user": "username",
            "admins": "admin_ids",
            "married": "is_married",
            "partner": "partner_name",
            "ascended": "is_ascended",
            "delay": "random_interval", "interval": "random_interval", "randomdelay": "random_interval",
            "typo": "typo_chance",
            "sleep": "sleep_at",
            "wake": "wake_up_at", "wakeup": "wake_up_at",
            "telegramtoken": "telegram_bot_token", "tgtoken": "telegram_bot_token",
            "telegramchat": "telegram_chat_id", "tgchat": "telegram_chat_id",
            "plant": "seed",
            "workcommand": "work_command", "workcmd": "work_command", "job": "work_command",
            "lootboxtype": "lootbox_type", "lbtype": "lootbox_type",
            "lifeboost": "life_boost_before_adv",
            "adventurearea": "adventure_area", "advarea": "adventure_area",
            "currentarea": "current_area",
            "petcommand": "pet_adventure_command", "petcmd": "pet_adventure_command",
            "tcquantity": "tc_quantity", "tccount": "tc_quantity",
            "tcstop": "tc_stop_on", "tcstopon": "tc_stop_on",
            "eternal": "is_eternal",
            "eternaltier": "eternal_tier",
            "winduel": "win_duel", "winduels": "win_duel",
            "partnerid": "duel_partner_id"
        }
        
        for alias, canonical in aliases.items():
            for cat_name, cat_data in CONFIG_CATEGORIES.items():
                if canonical in cat_data["params"]:
                    param_map[alias] = (canonical, cat_data["params"][canonical])
                    break
                    
        best_match = None
        num_tokens_matched = 0
        for i in range(1, len(tokens) + 1):
            test_str = "".join(tokens[:i]).lower().replace("_", "").replace("-", "")
            if test_str in param_map:
                best_match = param_map[test_str]
                num_tokens_matched = i
                
        if best_match:
            canonical_name, details = best_match
            val_str = " ".join(tokens[num_tokens_matched:]).strip()
            return canonical_name, val_str, details
        else:
            return None

    # Handle the cases with '='
    norm_param = param_part.lower().replace(" ", "").replace("_", "").replace("-", "")
    for cat_name, cat_data in CONFIG_CATEGORIES.items():
        for p_name, p_details in cat_data["params"].items():
            norm_canonical = p_name.lower().replace("_", "").replace("-", "")
            if norm_param == p_name.lower() or norm_param == norm_canonical:
                return p_name, val_part, p_details
                
    aliases = {
        "hunt": "do_hunt", "dohunt": "do_hunt",
        "adv": "do_adv", "doadv": "do_adv", "adventure": "do_adv",
        "farm": "do_farm", "dofarm": "do_farm",
        "work": "work_command", "dowork": "do_work",
        "train": "do_training", "training": "do_training", "dotraining": "do_training", "tr": "do_training",
        "daily": "do_daily", "dodaily": "do_daily",
        "weekly": "do_weekly", "doweekly": "do_weekly",
        "quest": "do_quest", "doquest": "do_quest",
        "lootbox": "do_lootbox", "dolootbox": "do_lootbox", "lb": "do_lootbox",
        "dungeon": "do_dungeon", "dodungeon": "do_dungeon", "dg": "do_dungeon",
        "card": "do_card_hand", "hand": "do_card_hand", "cardhand": "do_card_hand", "docardhand": "do_card_hand", "do_card_hand": "do_card_hand",
        "duel": "do_duel", "doduel": "do_duel",
        "pet": "do_pet", "dopet": "do_pet",
        "ultr": "do_ultr", "doultr": "do_ultr",
        "token": "user_token", "discordtoken": "user_token",
        "channel": "channel_id",
        "guild": "guild_id", "server": "guild_id",
        "user": "username",
        "admins": "admin_ids",
        "married": "is_married",
        "partner": "partner_name",
        "ascended": "is_ascended",
        "delay": "random_interval", "interval": "random_interval", "randomdelay": "random_interval",
        "typo": "typo_chance",
        "sleep": "sleep_at",
        "wake": "wake_up_at", "wakeup": "wake_up_at",
        "telegramtoken": "telegram_bot_token", "tgtoken": "telegram_bot_token",
        "telegramchat": "telegram_chat_id", "tgchat": "telegram_chat_id",
        "plant": "seed",
        "workcommand": "work_command", "workcmd": "work_command", "job": "work_command",
        "lootboxtype": "lootbox_type", "lbtype": "lootbox_type",
        "lifeboost": "life_boost_before_adv",
        "adventurearea": "adventure_area", "advarea": "adventure_area",
        "currentarea": "current_area",
        "petcommand": "pet_adventure_command", "petcmd": "pet_adventure_command",
        "tcquantity": "tc_quantity", "tccount": "tc_quantity",
        "tcstop": "tc_stop_on", "tcstopon": "tc_stop_on",
        "eternal": "is_eternal",
        "eternaltier": "eternal_tier",
        "winduel": "win_duel", "winduels": "win_duel",
        "partnerid": "duel_partner_id"
    }
    
    if norm_param in aliases:
        canonical = aliases[norm_param]
        for cat_name, cat_data in CONFIG_CATEGORIES.items():
            if canonical in cat_data["params"]:
                return canonical, val_part, cat_data["params"][canonical]
                
    return None


async def handle_toggle_command(param_arg: str) -> str:
    cleaned = param_arg.strip()
    if not cleaned:
        return "⚠️ Uso: `sb toggle <parametro>` (exemplo: `sb toggle hunt` ou `sb toggle delay`)"
        
    param_name = find_bool_param(cleaned)
    if not param_name:
        return f"⚠️ Parâmetro booleano `{cleaned}` não reconhecido para toggle. Use opções como: `hunt`, `adv`, `farm`, `training`, `dungeon`, `card`, `delay`."
        
    config.reload_config()
    current_val = config.userOptions.get(param_name, "false")
    new_val = "false" if str(current_val).lower() in ("true", "yes", "1", "on") else "true"
    
    details = None
    for cat_name, cat_data in CONFIG_CATEGORIES.items():
        if param_name in cat_data["params"]:
            details = cat_data["params"][param_name]
            break
            
    if not details:
        return f"❌ Erro interno ao buscar detalhes de `{param_name}`."
        
    return await _update_config_param(param_name, new_val, details)


async def handle_config_command(command_text: str) -> str:
    profile_path = config.active_profile_path or "options.ini"
    profile_name = os.path.basename(profile_path)
    
    config.reload_config()
    
    def is_bool_true(val: str) -> bool:
        return str(val).lower() in ("true", "yes", "1", "on")
        
    def get_val(key: str, fallback: str = "none") -> str:
        v = config.userOptions.get(key, "")
        if v is None:
            return fallback
        v_str = str(v).strip()
        return v_str if v_str else fallback

    cleaned_input = command_text.strip()
    if not cleaned_input:
        def get_bool_icon(name):
            val = config.userOptions.get(name, "false")
            return "✅" if is_bool_true(val) else "❌"

        cmd_status = f"Hunt: {get_bool_icon('do_hunt')} | Adv: {get_bool_icon('do_adv')} | Farm: {get_bool_icon('do_farm')} | Training: {get_bool_icon('do_training')} | Dungeon: {get_bool_icon('do_dungeon')}"
        
        uname = get_val("username")
        guild = get_val("guild_id")
        guild_short = guild[:6] + "..." if len(guild) > 8 else guild
        married = get_bool_icon("is_married")
        acc_status = f"User: `{uname}` | Server: `{guild_short}` | Married: {married}"
        
        rand_delay = get_bool_icon("random_interval")
        typo = config.userOptions.get("typo_chance", "0.0")
        try:
            typo_pct = f"{int(float(typo)*100)}%"
        except:
            typo_pct = f"{typo}"
        sleep = get_val("sleep_at", "")
        wake = get_val("wake_up_at", "")
        sleep_str = f"{sleep} às {wake}" if (sleep or wake) else "desativado"
        safety_status = f"Delay: {rand_delay} | Typo: `{typo_pct}` | Sleep: `{sleep_str}`"
        
        seed = get_val("seed")
        work = get_val("work_command")
        lb = get_val("lootbox_type")
        area = get_val("adventure_area")
        items_status = f"Seed: `{seed}` | Work: `{work}` | LB: `{lb}` | Area: `{area}`"
        
        card = get_val("card_hand_action")
        eternal = get_bool_icon("is_eternal")
        tc_stop = get_val("tc_stop_on")
        mini_status = f"Card: `{card}` | Eternal: {eternal} | TC Stop: `{tc_stop}`"

        lines = [
            "⚙️ **Oracle Configuração Dinâmica** ⚙️",
            f"Perfil ativo: `{profile_name}`",
            "",
            "Escolha uma categoria abaixo para visualizar os parâmetros, valores atuais e exemplos:",
            "",
            "• ⚙️ `sb config commands` - Comandos e automações ativas",
            f"  └─ Automações: {cmd_status}",
            "",
            "• 👤 `sb config account` - Configurações de conta e Discord/Telegram IDs",
            f"  └─ Status: {acc_status}",
            "",
            "• 🚨 `sb config safety` - Segurança, sono e anti-detecção",
            f"  └─ Status: {safety_status}",
            "",
            "• 📦 `sb config items` - Cultivo, work, lootboxes e áreas",
            f"  └─ Status: {items_status}",
            "",
            "• 🎮 `sb config minigames` - Minijogos, Gambling e TC",
            f"  └─ Status: {mini_status}",
            "",
            "Sintaxe para alterar um parâmetro:",
            "`sb config <categoria> <parametro> <valor>` ou apenas `sb config <parametro> <valor>`",
            "💡 Exemplo: `sb config commands do_hunt false` ou `sb config do_hunt false`"
        ]
        return "\n".join(lines)
        
    # Check if we should display list for a category
    parts = cleaned_input.split()
    first_arg = parts[0].lower().strip()
    
    def get_param_line(name, details):
        raw_val = get_val(name)
        p_type = details["type"]
        
        if p_type == "bool":
            icon = "✅" if is_bool_true(raw_val) else "❌"
            toggle_name = TOGGLE_ALIASES.get(name, name)
            return f"{icon} `{name}`: {details['desc']}\n  └─ Sintaxe: `sb toggle {toggle_name}`"
            
        if p_type == "token":
            icon = "🔒"
            if raw_val and raw_val != "none":
                val_disp = f"`{raw_val[:4]}...{raw_val[-4:]}`"
            else:
                val_disp = "`********`"
        elif p_type == "time":
            icon = "⏰"
            val_disp = f"`{raw_val}`" if (raw_val and raw_val != "none") else "`Desativado`"
        elif p_type == "int":
            icon = "🔢"
            val_disp = f"`{raw_val}`"
        elif p_type == "float":
            icon = "📊"
            try:
                val_disp = f"`{int(float(raw_val)*100)}%`"
            except:
                val_disp = f"`{raw_val}`"
        else:
            icon = "⚙️"
            val_disp = f"`{raw_val}`"

        return f"{icon} `{name}`: {details['desc']}\n  └─ Valor atual: {val_disp} | Sintaxe: `sb config {details['syntax']}`"

    if first_arg in CONFIG_CATEGORIES:
        category = first_arg
        if len(parts) == 1:
            cat_info = CONFIG_CATEGORIES[category]
            lines = [
                f"**{cat_info['title']}**",
                f"Perfil ativo: `{profile_name}`",
                ""
            ]
            for p_name, p_details in cat_info["params"].items():
                lines.append(get_param_line(p_name, p_details))
            return "\n".join(lines)
        else:
            remaining = " ".join(parts[1:])
            res = resolve_parameter_and_value(remaining)
            if not res:
                return f"⚠️ Parâmetro não reconhecido na categoria `{category}`."
            param_name, val_str, details = res
            return await _update_config_param(param_name, val_str, details)
            
    # Try resolving globally without category
    res = resolve_parameter_and_value(cleaned_input)
    if res:
        param_name, val_str, details = res
        if not val_str:
            raw_val = config.userOptions.get(param_name, "")
            if details["type"] == "token" and raw_val:
                raw_val = raw_val[:4] + "..." + raw_val[-4:] if len(raw_val) > 8 else "********"
            return f"💡 **{param_name}** (Valor: `{raw_val}`): {details['desc']}\nSintaxe para alterar: `sb config {details['syntax']}`"
            
        return await _update_config_param(param_name, val_str, details)
        
    return f"⚠️ Categoria ou parâmetro `{first_arg}` não reconhecido. Digite `sb config` para ver ajuda."


async def responseResolver(message) -> None:
    msg = message.content.lower()

    if message.author.id == config.EPIC_RPG_ID and config.is_married:
        logger.debug(
            "Partner name config: '%s' (lower: '%s')",
            config.partner_name,
            config.partner_name.lower(),
        )
        logger.debug("User name: '%s'", config.user_name_lower)
        logger.debug("Message content: %s", message.content)

    # ─── User Commands ───
    if message.author.id == config.userID:
        if msg == "rpg s t":
            add_to_low_priority_queue(
                "```" + format_session_data(sessionData, "Dados da Sessão (Principal)") + "```"
            )
            logger.info("Comando rpg s t enfileirado")
            return
        elif msg == "rpg s":
            logger.info(
                "\n" + format_session_data(sessionData, "Dados da Sessão (Principal)")
            )
            return
        elif msg.startswith("sb stats"):
            parts = msg.split()
            if len(parts) > 2:
                period_str = parts[2]
                from bot.persistence import get_stats_for_period
                period_data = get_stats_for_period(sessionData, period_str)
                logger.info(
                    f"\n" + format_session_data(period_data, f"Dados da Sessão (Último(s) {period_str})")
                )
            else:
                logger.info(
                    "\n" + format_session_data(sessionData, "Dados da Sessão (Histórico Completo)")
                )
            return
        elif msg == "rpg s p" and config.is_married:
            logger.info(
                "\n"
                + format_session_data(
                    {"partner_loot_data": sessionData["partner_loot_data"]},
                    f"Dados da Sessão (Parceiro: {config.partner_name})",
                )
            )
            return
        elif msg == "rpg u t":
            add_to_high_priority_queue(
                f"{int(time.time() - config.startTime)} segundos"
            )
            logger.info("Command rpg u t queued")
            return
        elif msg == "rpg u":
            logger.info(str(time.time() - config.startTime) + " seconds")
            return
        elif msg == "sb pause":
            if not bot_state.paused:
                bot_state.paused = True
                logger.info("Bot freeze.")
            else:
                logger.info("Bot already paused.")
            return
        elif msg == "sb start":
            if bot_state.paused:
                bot_state.paused = False
                logger.info("Bot started.")
            else:
                logger.info("Bot already running.")
        elif msg in ["sb help", "sb ajuda"]:
            help_text = (
                "\n=== Oracle v2 Admin Commands ===\n"
                "sb help / sb ajuda : Shows this help message\n"
                "sb pause           : Pause the bot (Freeze)\n"
                "sb start           : Unpause the bot (Unfreeze)\n"
                "sb reset           : Clear queues and reset state\n"
                "sb stats           : Show all-time session stats\n"
                "sb stats [time]    : Show stats for period (e.g., sb stats 10h, 7d, 1m)\n"
                "sb tc start [Xc][m] : Activate TC mode (e.g. sb tc start 4c 60m)\n"
                "sb tc stop         : Deactivate TC mode\n"
                "sb g start         : Start the gambling/coinflip module\n"
                "sb g pause         : Stop the gambling module\n"
                "sb say <text>      : Send a message in the channel\n"
                "rpg u              : Show bot uptime\n"
                "\n=== New Features ===\n"
                "do_[cmd]=true/false  : Toggle individual commands in options.ini\n"
                "do_duel=true/false   : Actives/Deactives automatic duels\n"
                "duel_partner_id=ID   : Mentions this partner ID in rpg duel\n"
                "sleepet start/stop   : Controls sleepet mode automation\n"
                "do_ultr=true         : ULTR training sequence override\n"
                "is_eternal=true      : Dungeon auto-enter + dragon bite loop\n"
                "card_hand_action     : auto (play) or notify (Telegram only)\n"
                "tc_quantity=N        : Default cookies per use\n"
                "life_boost_before_adv: Buy life boost before adventure\n"
                "sb language [pt|en] : Change bot language\n"
                "sb export [ini|txt] : Export active config file\n"
                "sb status           : Send live status to Discord + Telegram\n"
                "sb config           : Dynamic interactive configuration editor\n"
            )
            logger.info(help_text)
            return
        elif msg == "sb config" or msg.startswith("sb config "):
            cmd_text = msg[9:].strip()
            response = await handle_config_command(cmd_text)
            try:
                await message.channel.send(response)
            except Exception as e:
                logger.error(f"Error sending config response to Discord: {e}")
            return
        elif msg.startswith("sb language") or msg.startswith("sb lang"):
            parts = msg.split()
            if len(parts) >= 3:
                new_lang = parts[2].lower().strip()
                if new_lang in ("pt", "en"):
                    set_language(new_lang)
                    logger.info(t("telegram_language_changed", lang="pt" if new_lang == "pt" else "en"))
            return
        elif msg == "sb export" or msg.startswith("sb export "):
            parts = msg.split()
            ext = "ini"  # Default
            if len(parts) >= 3:
                requested_ext = parts[2].lower().strip()
                if requested_ext in ["txt", "ini"]:
                    ext = requested_ext
            
            profile_path = config.active_profile_path
            if not profile_path or not os.path.exists(profile_path):
                profile_path = "options.ini"
                
            if os.path.exists(profile_path):
                base_name = os.path.basename(profile_path)
                if ext == "txt":
                    out_filename = base_name.replace(".ini", "") + ".txt"
                else:
                    out_filename = base_name.replace(".ini", "") + ".ini"
                
                try:
                    file_to_send = discord.File(profile_path, filename=out_filename)
                    await message.channel.send(file=file_to_send)
                    logger.info(f"Exported configuration profile: {out_filename} to Discord channel.")
                except Exception as e:
                    logger.error(f"Error exporting profile to Discord: {e}")
            else:
                try:
                    await message.channel.send("⚠️ Arquivo de configuração não encontrado.")
                except Exception:
                    pass
            return
        elif msg == "sb status":
            await trigger_status_command(message.channel)
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
        user_name_clean = config.user_name_lower.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
        msg_clean = msg.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
        if str(config.userID) not in msg and config.user_name_lower not in msg and (not user_name_clean or user_name_clean not in msg_clean):
            return

        _temp = msg.replace(f"<@{config.userID}>", "").replace(f"<@!{config.userID}>", "").replace(config.user_name_lower, "")
        if user_name_clean:
            _temp = _temp.replace(user_name_clean, "")
        _temp = _temp.replace("`", "").strip()

        if "heal" in _temp:
            add_to_high_priority_queue("rpg heal")
            logger.info("Command rpg heal queued from Navi Lite")
            return

        slash_match = re.search(
            r'</(hunt|adventure|fish|chop|mine|pickup|tr|farm|training|pets claim|pets|quest start|quest|lootbox|daily|weekly):[0-9]+>',
            _temp,
        )
        if slash_match:
            cmd_name = slash_match.group(1)
            cmd_flag_map = {
                "hunt": config.do_hunt,
                "adventure": config.do_adv,
                "tr": config.do_training or config.do_ultr,
                "training": config.do_training or config.do_ultr,
                "farm": config.do_farm,
                "fish": config.do_work,
                "chop": config.do_work,
                "mine": config.do_work,
                "pickup": config.do_work,
                "pets claim": config.do_pet,
                "pets": config.do_pet,
                "quest start": config.do_quest,
                "quest": config.do_quest,
                "lootbox": config.do_lootbox,
                "daily": config.do_daily,
                "weekly": config.do_weekly,
            }
            if not cmd_flag_map.get(cmd_name, True):
                logger.debug("Navi slash command '%s' skipped (disabled via config)", cmd_name)
                return
            if cmd_name == "hunt":
                final_cmd = "rpg hunt"
                if config.is_ascended:
                    final_cmd += " h"
                if config.is_married:
                    final_cmd += " t"
                add_to_high_priority_queue(final_cmd)
            elif cmd_name == "adventure":
                final_cmd = "rpg adv"
                if config.is_ascended:
                    final_cmd += " h"
                add_to_high_priority_queue(final_cmd)
            elif cmd_name == "farm":
                if bot_state.farm_seed_fallback:
                    farm_cmd = "rpg farm"
                else:
                    farm_cmd = f"rpg farm {config.farm_seed}" if config.farm_seed and config.farm_seed.lower() != "none" else "rpg farm"
                add_to_high_priority_queue(farm_cmd)
                final_cmd = farm_cmd
            elif cmd_name in ("tr", "training"):
                if config.training_command_sequence:
                    for tc_cmd in config.training_command_sequence:
                        add_to_high_priority_queue(tc_cmd)
                    final_cmd = str(config.training_command_sequence)
                else:
                    final_cmd = "rpg training"
                    add_to_high_priority_queue(final_cmd)
            elif cmd_name in ("fish", "chop", "mine", "pickup"):
                final_cmd = f"rpg {config.userOptions.get('work_command', cmd_name)}"
                add_to_high_priority_queue(final_cmd)
            elif cmd_name in ("pets claim", "pets"):
                final_cmd = "rpg pet claim"
                add_to_low_priority_queue(final_cmd)
            elif cmd_name in ("quest start", "quest"):
                final_cmd = "rpg quest"
                add_to_high_priority_queue(final_cmd)
            elif cmd_name == "lootbox":
                lootbox_type = config.lootbox_type
                if (
                    lootbox_type != "none"
                    and time.monotonic() > bot_state.lootbox_cooldown_until
                ):
                    add_to_low_priority_queue(f"rpg buy {lootbox_type}")
                    bot_state.pending_lootbox_buy = lootbox_type
                    bot_state.lootbox_fallback_triggered = False
                    final_cmd = f"rpg buy {lootbox_type}"
                elif time.monotonic() < bot_state.lootbox_cooldown_until:
                    HUD.system("Compra de lootbox pulada (Cooldown Financeiro).")
                    return
                else:
                    final_cmd = "rpg lootbox"
                    add_to_low_priority_queue(final_cmd)
            elif cmd_name in ("daily", "weekly"):
                final_cmd = f"rpg {cmd_name}"
                add_to_low_priority_queue(final_cmd)
            else:
                final_cmd = f"rpg {cmd_name}"
                add_to_high_priority_queue(final_cmd)
            HUD.system(f"Comando de Slash da Navi detectado: {final_cmd}")
            return

        # ─── Minigame Answer Extraction ───
        # Navi Lite sends answers in two formats:
        #   1) Exact match: just "3" or "yes"
        #   2) Parentheses format: "normie fish (`1`)." → extract "1"
        #
        # NOTE: If the message starts with "yes" or "no" followed by parentheses (e.g., "no (you have 222 ruby)"),
        # the answer is "yes" or "no", not the info inside the parentheses.
        extracted_answer = None
        starts_with_yes_no = re.match(r'^(yes|no)\b', _temp)
        if starts_with_yes_no:
            extracted_answer = starts_with_yes_no.group(1)
        else:
            paren_match = re.search(r'\(\s*([^)]+?)\s*\)', _temp)
            if paren_match:
                candidate = paren_match.group(1).strip().rstrip('.')
                if any(x in candidate.lower() for x in ["you have", "you got", "ruby", "coin", "gold", "level", ":", "<", ">"]):
                    before_paren = _temp.split('(')[0].strip()
                    if before_paren in ["yes", "no"]:
                        extracted_answer = before_paren
                else:
                    extracted_answer = candidate

        if extracted_answer:
            add_to_high_priority_queue(extracted_answer)
            HUD.system(f"Resposta da Navi extraída: {extracted_answer}")
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
                HUD.system(f"Escolha da Navi detectada: {response}")
                return

        # Ignora avisos normais do Navi Lite que não são comandos
        if "hey! it's time for" not in msg and "your pet" not in msg and "is back!" not in msg:
            runtimeErrors.append(
                time.strftime(
                    "%Y/%m/%d %H:%M:%S - unexpected helper response " + _temp
                )
            )
            if len(runtimeErrors) > RUNTIME_ERRORS_MAX_SIZE:
                runtimeErrors.pop(0)
            logger.error(f"Unexpected helper response: {_temp}")
        
        # Remove common formatting characters like slash, backticks and stars for robust command detection
        msg_clean_for_check = msg.replace("/", "").replace("`", "").replace("*", "").strip()
        if any(
            cmd in line
            for line in msg_clean_for_check.splitlines()
            for cmd in [
                "hunt", "adventure", "farm", "training", "work",
                "daily", "weekly", "lootbox", "pickup", "chop", "fish", "mine", "quest",
            ]
        ):
            await rdCheckNavi(msg)
            logger.info(
                "Processing rdCheck for Navi Lite cooldown message."
            )
            return

    # ─── Epic RPG Responses ───
    elif message.author.id == config.EPIC_RPG_ID:
        # Check for locked pet commands error (no pets / no 2nd time travel)
        if "command is unlocked after the second" in msg or "when you get your first pet" in msg:
            current_time = time.monotonic()
            is_our_error = False
            
            # Check if reference is our command
            if message.reference and message.reference.resolved:
                ref = message.reference.resolved
                if hasattr(ref, "author") and ref.author.id == config.userID:
                    is_our_error = True
            
            # Or if we sent a pet command recently (within 6 seconds)
            if bot_state.last_sent_command:
                last_cmd = bot_state.last_sent_command.lower()
                if "pet" in last_cmd and (current_time - bot_state.last_sent_time) < PET_COMMAND_RECENCY_WINDOW:
                    is_our_error = True

                    
            if is_our_error:
                if bot_state.sleepet_mode:
                    bot_state.sleepet_mode = False
                    bot_state.sleepet_state = None
                    HUD.alert("Sleepet Mode desativado: Pets não liberados nesta conta!")
                    await send_telegram_notification("⚠️ *Sleepet Mode desativado:* Pets ou comando não liberados na conta!")
                    add_to_high_priority_queue("rpg rd")
                return

        # Check for instant pet returns (perks / VOIDog time travel)
        full_msg = msg
        if message.embeds:
            full_msg += " " + " ".join(str(e.to_dict()).lower() for e in message.embeds)

        is_instant_return = False
        if "back instantly" in full_msg or "pets are back" in full_msg:
            is_instant_return = True
        elif "voidog" in full_msg and "now they are all back" in full_msg:
            is_instant_return = True

        if is_instant_return:
            current_time = time.monotonic()
            
            # Check if reference is our message
            is_reference_ours = False
            if message.reference and message.reference.resolved:
                ref = message.reference.resolved
                if hasattr(ref, "author") and ref.author.id == config.userID:
                    is_reference_ours = True
                    
            # Check if we sent a pet command recently (within 6 seconds)
            is_recent_our_pet_command = False
            if bot_state.last_sent_command:
                last_cmd = bot_state.last_sent_command.lower()
                if "pet" in last_cmd and (current_time - bot_state.last_sent_time) < PET_COMMAND_RECENCY_WINDOW:
                    is_recent_our_pet_command = True

            is_our_pet_command = is_reference_ours or is_recent_our_pet_command

            if is_our_pet_command:
                if bot_state.sleepet_mode:
                    HUD.system("Retorno instantâneo do pet detectado no Sleepet Mode! Resgatando recompensas...")
                    bot_state.sleepet_state = "waiting_claim"
                    bot_state.last_sleepet_cmd_time = time.monotonic()
                    add_to_high_priority_queue("rpg pet claim")
                    return
                HUD.system("Retorno instantâneo do pet detectado! Resgatando recompensas...")
                bot_state.pet_adventure_return_time = 0
                bot_state.last_sleepet_cmd_time = time.monotonic()
                add_to_low_priority_queue("rpg pet claim")
                return
            else:
                logger.debug("Instant pet return message ignored (not triggered by our command)")

        # ─── Sleepet Potion Detection ───
        if bot_state.sleepet_mode:
            user_name_clean = config.user_name_lower.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
            msg_clean = msg.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
            if "sleepet potion" in msg or "sleepet_potion" in msg:
                if (config.user_name_lower in msg or (user_name_clean and user_name_clean in msg_clean)) and bot_state.sleepet_state == "waiting_potion":
                    if any(err in msg for err in ["don't have", "do not have", "not have"]):
                        bot_state.sleepet_mode = False
                        bot_state.sleepet_state = None
                        HUD.alert("Sleepet Mode desativado: Sem poções de sleepet!")
                        await send_telegram_notification("⚠️ *Sleepet Mode desativado:* Poções esgotadas!")
                        add_to_high_priority_queue("rpg rd")
                    else:
                        HUD.system("Sleepet potion usada com sucesso! Resgatando recompensas...")
                        bot_state.sleepet_state = "waiting_claim"
                        bot_state.last_sleepet_cmd_time = time.monotonic()
                        add_to_high_priority_queue("rpg pet claim")
                    return
            elif bot_state.sleepet_state == "waiting_potion" and any(err in msg for err in ["don't have", "do not have", "not have"]):
                is_our_error = False
                if message.reference and message.reference.resolved:
                    ref = message.reference.resolved
                    if hasattr(ref, "author") and ref.author.id == config.userID:
                        is_our_error = True
                if config.user_name_lower in msg or str(config.userID) in msg or (user_name_clean and user_name_clean in msg_clean):
                    is_our_error = True
                if bot_state.last_sent_command:
                    last_cmd = bot_state.last_sent_command.lower()
                    if "sleepet" in last_cmd and (time.monotonic() - bot_state.last_sent_time) < PET_COMMAND_RECENCY_WINDOW:
                        is_our_error = True
                if is_our_error:
                    bot_state.sleepet_mode = False
                    bot_state.sleepet_state = None
                    HUD.alert("Sleepet Mode desativado: Sem poções de sleepet!")
                    await send_telegram_notification("⚠️ *Sleepet Mode desativado:* Poções esgotadas ou item indisponível!")
                    add_to_high_priority_queue("rpg rd")
                    return

        is_pet_message = False
        user_name_clean = config.user_name_lower.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
        msg_clean = msg.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
        if "is approaching" in msg and (config.user_name_lower in msg or (user_name_clean and user_name_clean in msg_clean)):
            is_pet_message = True
        elif message.embeds:
            embed_dict = message.embeds[0].to_dict()
            embed_text = str(embed_dict).lower()
            logger.debug("Full embed: %s", embed_dict)
            embed_text_clean = embed_text.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
            if "is approaching" in embed_text and (config.user_name_lower in embed_text or (user_name_clean and user_name_clean in embed_text_clean)):
                is_pet_message = True
                logger.debug("Pet message found in embed: %s...", embed_text[:100])

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
            bot_state.minigame_pending_until = time.monotonic() + MINIGAME_PAUSE_DURATION
            logger.info(f"Minigame detected. All queues paused for {MINIGAME_PAUSE_DURATION} seconds.")
            
        if any(w in msg for w in ["better luck next time", "you got it", "you passed", "well done", "nope! it was"]):
            if bot_state.minigame_pending_until > 0:
                bot_state.minigame_pending_until = 0
                logger.info("Minigame finished. Queues resumed.")

        full_msg = msg
        if message.embeds:
            full_msg += " " + " ".join(str(e.to_dict()).lower() for e in message.embeds)

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

            # ─── Duel State Machine ───
            if config.do_duel or bot_state.duel_in_progress or "will you accept" in embed_text:
                user_name_clean = config.user_name_lower.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
                embed_text_clean = embed_text.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()

                if "will you accept" in embed_text:
                    if f"will you accept, {config.user_name_lower}" in embed_text or (user_name_clean and f"willyouaccept,{user_name_clean}" in embed_text_clean.replace(" ", "")):
                        from bot.state import lowPriorityQueue, lowPriorityQueueSet
                        can_accept = False
                        
                        author_title = (embed_dict.get("title", "") or embed_dict.get("author", {}).get("name", ""))
                        challenger_name = ""
                        if " — duel" in author_title:
                            challenger_name = author_title.split(" — duel")[0].strip().lower()
                        elif " - duel" in author_title:
                            challenger_name = author_title.split(" - duel")[0].strip().lower()

                        if challenger_name:
                            guild = message.guild
                            if guild:
                                # Check configured admins by fetching each and comparing names
                                for admin_id in config.ADMIN_IDS:
                                    try:
                                        m = await guild.fetch_member(admin_id)
                                        if m and (
                                            m.name.lower() == challenger_name or
                                            (m.nick and m.nick.lower() == challenger_name) or
                                            (getattr(m, "global_name", None) and m.global_name.lower() == challenger_name) or
                                            (getattr(m, "display_name", None) and m.display_name.lower() == challenger_name)
                                        ):
                                            can_accept = True
                                            break
                                    except Exception:
                                        pass

                                # Check duel partner by name (if not already accepted as admin)
                                if not can_accept and config.duel_partner_id:
                                    try:
                                        partner_id = int(config.duel_partner_id)
                                        m = await guild.fetch_member(partner_id)
                                        if m and (
                                            m.name.lower() == challenger_name or
                                            (m.nick and m.nick.lower() == challenger_name) or
                                            (getattr(m, "global_name", None) and m.global_name.lower() == challenger_name) or
                                            (getattr(m, "display_name", None) and m.display_name.lower() == challenger_name)
                                        ):
                                            can_accept = True
                                    except (ValueError, Exception):
                                        pass

                            # Fallback check against partner name
                            if not can_accept and config.partner_name:
                                if challenger_name == config.partner_name.lower():
                                    can_accept = True

                        if can_accept:
                            lowPriorityQueue.clear()
                            lowPriorityQueueSet.clear()
                            bot_state.duel_in_progress = True
                            bot_state.duel_step = "waiting_weapon"
                            bot_state.last_duel_time = time.monotonic()
                            bot_state.duel_channel_id = message.channel.id
                            add_to_high_priority_queue("yes")
                            HUD.system(f"Duelo recebido! Aceitando com 'yes' no canal {message.channel.id}. LPQ limpa.")
                            return
                        else:
                            HUD.system("Duelo ignorado (desafiante não autorizado).")
                            return
                    elif config.user_name_lower in embed_text or (user_name_clean and user_name_clean in embed_text_clean):
                        from bot.state import lowPriorityQueue, lowPriorityQueueSet
                        lowPriorityQueue.clear()
                        lowPriorityQueueSet.clear()
                        bot_state.duel_in_progress = True
                        bot_state.duel_step = "waiting_confirmation"
                        bot_state.last_duel_time = time.monotonic()
                        bot_state.duel_channel_id = message.channel.id
                        bot_state.duel_fail_count = 0
                        HUD.system(f"Duelo enviado! Aguardando resposta do parceiro no canal {message.channel.id}. LPQ limpa.")
                        return

                if bot_state.duel_in_progress:
                    # Escolha de Arma
                    if "choose the weapon that better fits" in embed_text:
                        if (config.user_name_lower in embed_text or (user_name_clean and user_name_clean in embed_text_clean)) and not bot_state.duel_weapon_chosen:
                            bot_state.duel_weapon_chosen = True
                            bot_state.duel_fail_count = 0
                            if config.do_duel and config.win_duel:
                                choice = random.choice(["a", "b", "c"])
                                add_to_high_priority_queue(choice)
                                bot_state.duel_step = "finished"
                                bot_state.last_duel_time = time.monotonic()
                                HUD.system(f"Arma de duelo selecionada: '{choice}'")
                            else:
                                bot_state.duel_step = "finished"
                                HUD.system("Duelo com win_duel=False. Não enviando arma para perder por WO.")
                            return

                    # Finalização
                    if any(x in embed_text for x in ["won!", "lost!", "it's a draw"]):
                        if config.user_name_lower in embed_text or (user_name_clean and user_name_clean in embed_text_clean):
                            bot_state.duel_in_progress = False
                            bot_state.duel_step = None
                            bot_state.duel_weapon_chosen = False
                            bot_state.last_duel_time = 0
                            bot_state.duel_channel_id = 0
                            bot_state.duel_fail_count = 0
                            HUD.system("Duelo concluído. Filas liberadas!")
                            return
                    
                    # Erro / Cancelamento / Recusa
                    elif any(x in embed_text for x in ["refused to duel", "duel cancelled", "you cannot duel", "already in a duel"]):
                        bot_state.duel_in_progress = False
                        bot_state.duel_step = None
                        bot_state.duel_weapon_chosen = False
                        bot_state.last_duel_time = 0
                        bot_state.duel_channel_id = 0
                        bot_state.duel_fail_count += 1
                        if bot_state.duel_fail_count == 1:
                            await send_telegram_notification(
                                "⚠️ Duelo cancelado — parceiro não respondeu. "
                                "Auto-duel será suspenso após 2 falhas consecutivas."
                            )
                        elif bot_state.duel_fail_count >= 2:
                            await send_telegram_notification(
                                "🛑 Auto-duel suspenso: 2 falhas consecutivas. "
                                "Reative manualmente com sb duel reset ou aguarde o reset automático."
                            )
                        HUD.system(f"Duelo cancelado/recusado. (fail_count={bot_state.duel_fail_count})")
                        return

            # ─── Quest Completion Detection ───
            author_name = embed_dict.get("author", {}).get("name", "").lower()
            if "quest" in author_name:
                if check_user_matches(embed_dict, config.user_name_lower, config.userID):
                    description = embed_dict.get("description", "").lower()
                    fields_text = ""
                    for field in embed_dict.get("fields", []):
                        fields_text += field.get("name", "").lower() + " " + field.get("value", "").lower() + " "
                    combined_body = description + " " + fields_text
                    
                    if "completed!" in combined_body:
                        sessionData["command_data"]["quest"] += 1
                        logger.info(f"Quest Completed detected! Count: {sessionData['command_data']['quest']}.")
                        HUD.system(f"Quest Completada! Total: {sessionData['command_data']['quest']}")
                        from bot.persistence import save_session_data
                        save_session_data(sessionData)
                        return

            # ─── Dungeon State Machine ───
            if config.is_eternal and config.do_dungeon:
                if "are you sure you want to enter" in embed_text and "all players have to say 'yes'" in embed_text:
                    add_to_high_priority_queue("yes")
                    bot_state.dungeon_in_progress = True
                    bot_state.last_dungeon_time = time.monotonic()
                    HUD.dungeon("Entrando com 'yes'")
                    return
                if bot_state.dungeon_in_progress:
                    if "eternal dragon" in embed_text:
                        if not bot_state.dragon_alive and ("you have encountered" in embed_text or "turn" in embed_text):
                            bot_state.dragon_alive = True
                            bot_state.last_dungeon_time = time.monotonic()
                            add_to_high_priority_queue("bite")
                            HUD.dungeon("Encontrado! Iniciando loop de mordida")
                        elif bot_state.dragon_alive and "died" not in embed_text:
                            add_to_high_priority_queue("bite")
                        elif "died" in embed_text or "is dead" in embed_text:
                            bot_state.dragon_alive = False
                            bot_state.dungeon_in_progress = False
                            HUD.dungeon("Derrotado!")
                            return

            # ─── Global Events (processed even if embed is not user-specific) ───
            if "defenseless monster" in embed_text and "zombie horde" in embed_text:
                sessionData["misc"]["personal_events"] += 1
                add_to_high_priority_queue(
                    config.userOptions.get("zombie_horde_event_response", "fight")
                )
                if config.current_area != "none":
                    add_to_high_priority_queue(f"rpg area {config.current_area}")
                HUD.system("Evento de horda de zumbis detectado, comandos enfileirados")
                return
            if "matter how much you look around" in embed_text:
                sessionData["misc"]["personal_events"] += 1
                add_to_high_priority_queue("move")
                add_to_high_priority_queue("fight")
                HUD.system("Comando enfileirado para o evento mover e lutar")
                return
            if "You planted a seed, but for some reason it's not growing up" in embed_text:
                sessionData["misc"]["personal_events"] += 1
                add_to_high_priority_queue("fight")
                HUD.system("Comando fight enfileirado para o evento de semente")
                return
            if "You have encountered a mysterious man" in embed_text:
                sessionData["misc"]["personal_events"] += 1
                add_to_high_priority_queue("cry")
                HUD.system("Comando cry enfileirado para o evento misterioso")
                return
            if "God accidentally dropped" in embed_text or "I have a special trade today" in embed_text:
                sessionData["misc"]["personal_events"] += 1
                if embed_dict.get("fields") and len(embed_dict["fields"]) > 0:
                    add_to_low_priority_queue(
                        embed_dict["fields"][0]["value"]
                        .splitlines()[1]
                        .replace("**", "")
                        .lower(),
                        suppress_log=True,
                    )
                    HUD.system("Comando para troca especial enfileirado")
                else:
                    logger.warning("Embed with special trade has no fields.")
                return

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

            # ─── Profile Area Parsing ───
            author_name = embed_dict.get("author", {}).get("name", "").lower()
            if "profile" in author_name:
                max_area_match = re.search(r'area:\s*\d+\s*\(max:\s*(\d+)\)', embed_text)
                if max_area_match:
                    extracted_max_area = max_area_match.group(1)
                    if config.max_area != extracted_max_area:
                        logger.info(f"Nova max_area detectada: {extracted_max_area} (antiga: {config.max_area})")
                        config.update_max_area(extracted_max_area)
                        HUD.system(f"Área Máxima atualizada para: {extracted_max_area}")

            # ─── Ruby Dragon Event ───
            if "ruby dragon just spawned in front of you" in embed_text:
                sessionData["misc"]["personal_events"] += 1
                current_time = time.monotonic()
                
                # Check if previous turn has expired (>60s) to avoid desync
                if bot_state.ruby_dragon_state == "first_turn":
                    if current_time - bot_state.ruby_dragon_time > 60.0:
                        bot_state.ruby_dragon_state = None

                if bot_state.ruby_dragon_state is None:
                    bot_state.ruby_dragon_state = "first_turn"
                    bot_state.ruby_dragon_time = current_time
                    add_to_high_priority_queue("move")
                    HUD.system("Ruby Dragon detectado (Turno 1): Enviando 'move'")
                elif bot_state.ruby_dragon_state == "first_turn":
                    bot_state.ruby_dragon_state = None
                    bot_state.ruby_dragon_time = 0
                    add_to_high_priority_queue("fight")
                    HUD.system("Ruby Dragon detectado (Turno 2): Enviando 'fight'")
                    
                    area_to_return = config.current_area
                    if not area_to_return or area_to_return.lower() == "none":
                        area_to_return = config.max_area
                    
                    add_to_high_priority_queue(f"rpg area {area_to_return}")
                    HUD.system(f"Enfileirando retorno para a área {area_to_return} após derrotar Ruby Dragon")
                return

            # Check game-over FIRST — final embed has both "try to get the best
            # possible hand" AND "goldened", so goldened must be checked before
            # the mid-game pattern to avoid an early return.
            # Only reset here if the interactive loop hasn't started yet;
            # otherwise let the loop handle it to avoid concurrent state resets.
            if bot_state.cardhand_in_progress and "goldened" in embed_text and check_user_matches(embed_dict, config.user_name_lower, config.userID):
                if config.card_hand_action == "legacy_auto":
                    # Legacy mode: reset state directly, no loop to notify
                    bot_state.cardhand_in_progress = False
                    bot_state.cardhand_first_pass_done = False
                    bot_state.cardhand_turn_count = 1
                    bot_state.cardhand_message = None
                    _sent_cardhand_images.clear()
                    HUD.system("Card Hand (legacy) concluído! Filas liberadas.")
                elif not bot_state.cardhand_first_pass_done:
                    bot_state.cardhand_in_progress = False
                    bot_state.cardhand_first_pass_done = False
                    bot_state.cardhand_turn_count = 1
                    bot_state.cardhand_message = None
                    if hasattr(bot_state, '_cardhand_updated_event') and bot_state._cardhand_updated_event is not None:
                        bot_state._cardhand_updated_event.clear()
                    HUD.system("Card Hand concluído! Filas liberadas.")
                else:
                    bot_state.cardhand_message = message
                    bot_state.cardhand_updated_event.set()
                return

            if (
                target_name in embed_text
                and "card hand" in embed_text
            ):
                # ─── Legacy Auto: detect game start from embed, send pass immediately ───
                if config.card_hand_action == "legacy_auto":
                    if not bot_state.cardhand_in_progress:
                        # First detection — game just started
                        bot_state.cardhand_in_progress = True
                        bot_state.cardhand_first_pass_done = True
                        bot_state.cardhand_start_time = time.monotonic()
                        bot_state.cardhand_turn_count = 1
                        bot_state.cardhand_channel_id = message.channel.id
                        add_to_high_priority_queue("pass")
                        HUD.system("Card Hand (legacy) iniciado! Pass enfileirado. Filas bloqueadas.")
                    # Subsequent turns: Neon handles via on_message/on_message_edit
                    return

                # ─── Auto mode: interactive loop with Telegram + delays ───
                if config.card_hand_action == "auto" and bot_state.cardhand_in_progress:
                    if not bot_state.cardhand_first_pass_done:
                        bot_state.cardhand_first_pass_done = True
                        asyncio.create_task(interactive_card_hand_loop(message))
                    else:
                        bot_state.cardhand_message = message
                        bot_state.cardhand_updated_event.set()
                    return

            # ─── Pet Embeds (Summary / Reward / Status) ───
            if config.do_pet and ("— pets" in embed_text or "pet adventure rewards" in embed_text):
                from random import randint
                bot_state.next_pet_summary_check = time.monotonic() + randint(5400, 10800)
                
                author_name = (embed_dict.get("author") or {}).get("name") or ""
                author_name = author_name.lower()
                title = (embed_dict.get("title") or "").lower()
                is_reward = "reward summary" in author_name or "reward summary" in title or "pet adventure rewards" in author_name or "pet adventure rewards" in title

                if bot_state.sleepet_mode:
                    if is_reward:
                        await handle_sleepet_claim(embed_dict, embed_text)
                    else:
                        await handle_sleepet_summary(embed_dict, embed_text)
                    return

                if is_reward:
                    player_name = config.user_name_lower
                    if config.partner_name and check_user_matches(embed_dict, config.partner_name, None):
                        player_name = config.partner_name

                    if check_user_matches(embed_dict, player_name, config.userID if player_name == config.user_name_lower else None):
                        process_pet_claim_drops(embed_dict, embed_text, player_name)

                    if "purrency" in embed_text:
                        HUD.alert("Purrency recebida — inventário de pets cheio! Não reenviando para aventura.")
                        return

                    bot_state.pet_adventure_return_time = 0
                    add_to_low_priority_queue(config.pet_adventure_command)
                    HUD.system("Recompensas do pet resgatadas! Reenviando para aventura...")
                    return

                # Summary: check ready to claim first (rpg pet summary embed format)
                ready_claim_match = re.search(r'ready to claim:\s*(\d+)/(\d+)', embed_text)
                if ready_claim_match:
                    ready_to_claim = int(ready_claim_match.group(1))
                    if ready_to_claim > 0:
                        bot_state.pet_adventure_return_time = 0
                        add_to_low_priority_queue("rpg pet claim")
                        HUD.system(f"Pets prontos para resgate: {ready_to_claim}! Resgatando...")
                        return

                # Summary: parse pet status (timer / back / idle)
                timer_match = re.search(
                    r'status:\s*[a-z]+\s*\|\s*'
                    r'(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?',
                    embed_text
                )
                if timer_match:
                    h = int(timer_match.group(1) or 0)
                    m = int(timer_match.group(2) or 0)
                    s = int(timer_match.group(3) or 0)
                    total_seconds = h * 3600 + m * 60 + s + PET_TIMER_BUFFER_SECONDS
                    bot_state.pet_adventure_return_time = time.monotonic() + total_seconds
                    HUD.system(f"Pet em aventura - retorna em {h}h {m}m {s}s")
                elif "back from adventure" in embed_text:
                    bot_state.pet_adventure_return_time = 0
                    add_to_low_priority_queue("rpg pet claim")
                    HUD.system("Pet aguardando resgate! Resgatando...")
                elif "status: idle" in embed_text or "in adventure: 0" in embed_text:
                    add_to_low_priority_queue(config.pet_adventure_command)
                    HUD.system("Pet ocioso - enviando para aventura!")
                return

            if "— lootbox" in embed_text and "lootbox opened!" in embed_text:
                user_name_clean = config.user_name_lower.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
                embed_text_clean = embed_text.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
                
                is_our_lootbox = False
                if config.user_name_lower and f"{config.user_name_lower} — lootbox" in embed_text:
                    is_our_lootbox = True
                elif user_name_clean and f"{user_name_clean}—lootbox" in embed_text_clean.replace(" ", ""):
                    is_our_lootbox = True

                if not is_our_lootbox:
                    logger.debug("Lootbox opened by another user, ignoring.")
                    return
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

                is_together = False
                if config.is_married and config.partner_name:
                    p_name = config.partner_name.lower()
                    p_clean = p_name.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
                    user_name_clean = config.user_name_lower.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
                    partner_clean = config.partner_name.lower().replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip() if config.partner_name else ""
                    phrase1 = f"{config.user_name_lower} and {p_name} are hunting together"
                    phrase2 = f"{user_name_clean}and{p_clean}arehuntingtogether"
                    if phrase1 in embed_text or (user_name_clean and p_clean and phrase2 in embed_text_clean.replace(" ", "")):
                        is_together = True

                if is_together:
                    logger.info(
                        "Lootbox message detected in married mode. "
                        "Processing for both players."
                    )
                    current_player = None
                    player_lines = []
                    for line in all_lines:
                        line_clean = line.replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip()
                        is_user_line = False
                        is_partner_line = False
                        if line.startswith(f"**{config.user_name_lower}**:"):
                            is_user_line = True
                        elif user_name_clean and line_clean.startswith(f"{user_name_clean}:"):
                            is_user_line = True

                        if config.partner_name:
                            p_lower = config.partner_name.lower()
                            if line.startswith(f"**{p_lower}**:"):
                                is_partner_line = True
                            elif partner_clean and line_clean.startswith(f"{partner_clean}:"):
                                is_partner_line = True

                        if is_user_line:
                            if player_lines and current_player:
                                is_partner = False
                                if config.partner_name:
                                    if current_player.lower() == config.partner_name.lower() or (partner_clean and current_player.lower().replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip() == partner_clean):
                                        is_partner = True
                                process_drops(
                                    player_lines,
                                    current_player,
                                    sessionData["partner_loot_data"]
                                    if is_partner
                                    else sessionData["loot_data"],
                                )
                            current_player = config.user_name_lower
                            player_lines = []
                        elif is_partner_line:
                            if player_lines and current_player:
                                is_partner = False
                                if config.partner_name:
                                    if current_player.lower() == config.partner_name.lower() or (partner_clean and current_player.lower().replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip() == partner_clean):
                                        is_partner = True
                                process_drops(
                                    player_lines,
                                    current_player,
                                    sessionData["partner_loot_data"]
                                    if is_partner
                                    else sessionData["loot_data"],
                                )
                            current_player = config.partner_name.lower()
                            player_lines = []
                        elif line.startswith(">") and current_player:
                            player_lines.append(line[1:].strip())
                    if player_lines and current_player:
                        is_partner = False
                        if config.partner_name:
                            if current_player.lower() == config.partner_name.lower() or (partner_clean and current_player.lower().replace("\\", "").replace("*", "").replace("_", "").replace(".", "").strip() == partner_clean):
                                is_partner = True
                        process_drops(
                            player_lines,
                            current_player,
                            sessionData["partner_loot_data"]
                            if is_partner
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

        # ─── Plain-text Responses ───
        else:
            # Pet Adventure started confirmation
            if "started an adventure" in msg:
                if bot_state.sleepet_mode:
                    await handle_sleepet_adv(message, msg)
                    return
                elif "started an adventure and will be back in" in msg:
                    clean_msg = msg.replace('*', '')
                    timer_match = re.search(
                        r'back in\s*(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?', clean_msg
                    )
                    if timer_match:
                        h = int(timer_match.group(1) or 0)
                        m = int(timer_match.group(2) or 0)
                        s = int(timer_match.group(3) or 0)
                        total_seconds = h * 3600 + m * 60 + s + PET_TIMER_BUFFER_SECONDS
                        bot_state.pet_adventure_return_time = time.monotonic() + total_seconds
                        HUD.system(
                            f"Aventura do pet iniciada - {h}h {m}m {s}s para retornar"
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
                    if config.user_name_lower and f"**{config.user_name_lower}**" in msg.lower():
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
                        if config.user_name_lower and f"**{config.user_name_lower}**" in msg.lower():
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
                if config.user_name_lower and f"**{config.user_name_lower}**" in msg.lower():
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
                if config.user_name_lower and f"**{config.user_name_lower}**" in msg.lower():
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
                if "training" not in msg and (config.user_name_lower and f"**{config.user_name_lower}**" in msg.lower()):
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
                bot_state.farm_seed_fallback = True
                add_to_low_priority_queue("rpg farm", suppress_log=True)
                HUD.system("Semente específica esgotada! Usando rpg farm como fallback.")
                logger.info("rpg farm queued due to invalid seed, fallback activated")

            if "need a" in msg and "seed to farm" in msg:
                add_to_high_priority_queue("rpg buy seed 10")
                HUD.system("Sem sementes! Comprando 10 sementes...")
                logger.info("rpg buy seed 10 queued due to no seeds")

            if bot_state.farm_seed_fallback and "also got" in msg:
                for match in config.drop_regex.finditer(msg):
                    item_name = match.group(2).strip().lower()
                    item_name = re.sub(r'\s*!.*$|\s*\(.*?\)$|\s*in one of the leaves.*$|\s*use it with.*$', '', item_name).strip()
                    if item_name.endswith(" seed"):
                        gained_seed = item_name.replace(" seed", "").strip()
                        cfg_seed = config.farm_seed.lower() if config.farm_seed and config.farm_seed.lower() != "none" else None
                        if cfg_seed is None or gained_seed == cfg_seed:
                            bot_state.farm_seed_fallback = False
                            HUD.system(f"Semente {gained_seed} recuperada! Fallback desativado.")
                            logger.info(f"Farm seed fallback disabled — gained {gained_seed} seed")
                            break
