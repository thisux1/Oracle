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


async def send_telegram_raw(text, reply_to=None):
    """Send a pre-formatted message to Telegram without escaping.
    Uses plain text mode — emojis and unicode render normally, no Markdown parsing."""
    text = append_profile_info(text)
    if not config.TelegramBotToken or not config.TelegramChatID:
        return None

    url = f"https://api.telegram.org/bot{config.TelegramBotToken}/sendMessage"
    payload = {
        "chat_id": config.TelegramChatID,
        "text": text,
    }
    if reply_to is not None:
        payload["reply_to_message_id"] = reply_to
    try:
        session = _get_session()
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status != 200:
                resp_text = await response.text()
                logger.error(f"Failed to send Telegram raw message: {resp_text}")
                return None
            else:
                logger.info("Telegram raw message sent successfully.")
                data = await response.json()
                return data.get("result", {}).get("message_id")
    except Exception as e:
        logger.error(f"Error sending Telegram raw message: {e}")
    return None


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


async def send_telegram_document(file_path, filename=None, caption=""):
    caption = append_profile_info(caption)
    if not config.TelegramBotToken or not config.TelegramChatID:
        return None

    url = f"https://api.telegram.org/bot{config.TelegramBotToken}/sendDocument"
    try:
        session = _get_session()
        with open(file_path, 'rb') as f:
            file_data = f.read()

        data = aiohttp.FormData()
        data.add_field('chat_id', config.TelegramChatID)
        data.add_field('caption', caption)
        
        fname = filename or os.path.basename(file_path)
        data.add_field('document', file_data, filename=fname)

        async with session.post(url, data=data, timeout=aiohttp.ClientTimeout(total=15)) as response:
            if response.status != 200:
                text = await response.text()
                logger.error(f"Failed to send Telegram document: {text}")
                return None
            else:
                logger.info("Telegram document sent successfully.")
                resp_data = await response.json()
                return resp_data.get("result", {}).get("message_id")
    except Exception as e:
        logger.error(f"Error sending Telegram document: {e}")
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
    """Returns the user override set via the Telegram command handler."""
    from bot.state import bot_state
    if bot_state.captcha_user_override:
        return bot_state.captcha_user_override.lower().strip()
    return None

