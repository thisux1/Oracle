import time
import aiohttp
from bot.hud import logger
import bot.config as config
import os
import options_resolver


_http_session = None


def append_profile_info(text):
    profile = os.path.basename(options_resolver.optionsFilePath)
    user = config.user_name_lower or "unknown"
    return f"🔮 [{profile} | @{user}]\n{text}"


def _get_session():
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession()
    return _http_session


async def send_telegram_notification(text):
    text = append_profile_info(text)
    if not config.TelegramBotToken or not config.TelegramChatID:
        logger.warning("Telegram bot token or chat ID not set. Notification not sent.")
        return

    escape_chars = r'_*[]()~`>#+-=|{}.!'
    escaped_text = text
    for char in escape_chars:
        escaped_text = escaped_text.replace(char, f'\\{char}')

    url = f"https://api.telegram.org/bot{config.TelegramBotToken}/sendMessage"
    payload = {
        "chat_id": config.TelegramChatID,
        "text": escaped_text,
        "parse_mode": "MarkdownV2",
    }
    try:
        session = _get_session()
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status != 200:
                text = await response.text()
                logger.error(f"Failed to send Telegram notification: {text}")
            else:
                logger.info("Telegram notification sent successfully.")
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")


async def send_telegram_raw(text):
    """Send a pre-formatted message to Telegram without escaping.
    Uses plain text mode — emojis and unicode render normally, no Markdown parsing."""
    text = append_profile_info(text)
    if not config.TelegramBotToken or not config.TelegramChatID:
        return

    url = f"https://api.telegram.org/bot{config.TelegramBotToken}/sendMessage"
    payload = {
        "chat_id": config.TelegramChatID,
        "text": text,
    }
    try:
        session = _get_session()
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status != 200:
                resp_text = await response.text()
                logger.error(f"Failed to send Telegram raw message: {resp_text}")
            else:
                logger.info("Telegram raw message sent successfully.")
    except Exception as e:
        logger.error(f"Error sending Telegram raw message: {e}")


async def send_telegram_photo(photo_path, caption, reply_to=None):
    caption = append_profile_info(caption)
    if not config.TelegramBotToken or not config.TelegramChatID:
        return None

    url = f"https://api.telegram.org/bot{config.TelegramBotToken}/sendPhoto"
    try:
        session = _get_session()
        with open(photo_path, 'rb') as f:
            photo_data = f.read()

        data = aiohttp.FormData()
        data.add_field('chat_id', config.TelegramChatID)
        data.add_field('caption', caption)
        data.add_field('photo', photo_data, filename='captcha.png')
        if reply_to is not None:
            data.add_field('reply_to_message_id', str(reply_to))

        async with session.post(url, data=data, timeout=aiohttp.ClientTimeout(total=15)) as response:
            if response.status != 200:
                text = await response.text()
                logger.error(f"Failed to send Telegram photo: {text}")
                return None
            else:
                logger.info("Telegram photo sent successfully.")
                data = await response.json()
                return data.get("result", {}).get("message_id")
    except Exception as e:
        logger.error(f"Error sending Telegram photo: {e}")
    return None


async def edit_telegram_caption(message_id, caption):
    caption = append_profile_info(caption)
    if not config.TelegramBotToken or not config.TelegramChatID:
        return False
    url = f"https://api.telegram.org/bot{config.TelegramBotToken}/editMessageCaption"
    payload = {
        "chat_id": config.TelegramChatID,
        "message_id": message_id,
        "caption": caption,
    }
    try:
        session = _get_session()
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
            return response.status == 200
    except Exception as e:
        logger.error(f"Error editing Telegram caption: {e}")
    return False


def make_channel_link():
    return f"https://discord.com/channels/{config.GUILD_ID}/{config.channelID}"


async def send_telegram_keyboard(text, buttons=None, parse_mode="HTML"):
    text = append_profile_info(text)
    if not config.TelegramBotToken or not config.TelegramChatID:
        return None
    url = f"https://api.telegram.org/bot{config.TelegramBotToken}/sendMessage"
    payload = {
        "chat_id": config.TelegramChatID,
        "text": text,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if buttons:
        payload["reply_markup"] = {
            "inline_keyboard": buttons
        }
    try:
        session = _get_session()
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status != 200:
                res_text = await response.text()
                logger.error(f"Failed to send Telegram keyboard: {res_text}")
                return None
            data = await response.json()
            return data.get("result", {}).get("message_id")
    except Exception as e:
        logger.error(f"Error sending Telegram keyboard: {e}")
    return None


async def edit_telegram_message(message_id, text, buttons=None, parse_mode="HTML"):
    text = append_profile_info(text)
    if not config.TelegramBotToken or not config.TelegramChatID:
        return False
    url = f"https://api.telegram.org/bot{config.TelegramBotToken}/editMessageText"
    payload = {
        "chat_id": config.TelegramChatID,
        "message_id": message_id,
        "text": text,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    elif buttons is not None:
        payload["reply_markup"] = {"inline_keyboard": []}
    try:
        session = _get_session()
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
            return response.status == 200
    except Exception as e:
        logger.error(f"Error editing Telegram message: {e}")
    return False





async def get_telegram_override(start_time):
    """Polls Telegram for the latest message sent AFTER start_time."""
    if not config.TelegramBotToken:
        return None
    url = f"https://api.telegram.org/bot{config.TelegramBotToken}/getUpdates"
    try:
        session = _get_session()
        params = {"offset": -1, "limit": 1, "timeout": 0}
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as response:
            data = await response.json()
            if data.get("ok") and data.get("result"):
                last_update = data["result"][0]
                msg = last_update.get("message", {})
                msg_time = msg.get("date", 0)
                msg_text = msg.get("text", "").strip().lower()

                if msg_time > start_time and (time.time() - msg_time < 60):
                    return msg_text
    except Exception as e:
        logger.error(f"Error polling Telegram: {e}")
    return None

