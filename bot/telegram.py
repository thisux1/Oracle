import time
import requests
from bot.hud import logger
import bot.config as config


async def send_telegram_notification(text):
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
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            logger.error(f"Failed to send Telegram notification: {response.text}")
        else:
            logger.info("Telegram notification sent successfully.")
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")


async def send_telegram_photo(photo_path, caption):
    if not config.TelegramBotToken or not config.TelegramChatID:
        return

    url = f"https://api.telegram.org/bot{config.TelegramBotToken}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            data = {
                'chat_id': config.TelegramChatID,
                'caption': caption,
            }
            response = requests.post(url, files=files, data=data, timeout=15)
            if response.status_code != 200:
                logger.error(f"Failed to send Telegram photo: {response.text}")
            else:
                logger.info("Telegram photo sent successfully.")
    except Exception as e:
        logger.error(f"Error sending Telegram photo: {e}")


def make_channel_link():
    return f"https://discord.com/channels/{config.GUILD_ID}/{config.channelID}"


async def get_telegram_override(start_time):
    """Polls Telegram for the latest message sent AFTER start_time."""
    if not config.TelegramBotToken:
        return None
    url = f"https://api.telegram.org/bot{config.TelegramBotToken}/getUpdates"
    try:
        params = {"offset": -1, "limit": 1, "timeout": 0}
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        if data.get("ok") and data.get("result"):
            last_update = data["result"][0]
            msg = last_update.get("message", {})
            msg_time = msg.get("date", 0)
            msg_text = msg.get("text", "").strip().lower()

            # Must be newer than when we started AND within the last minute
            if msg_time > start_time and (time.time() - msg_time < 60):
                return msg_text
    except Exception as e:
        logger.error(f"Error polling Telegram: {e}")
    return None
