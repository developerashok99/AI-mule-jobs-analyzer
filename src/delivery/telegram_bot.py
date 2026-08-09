import logging

import requests

from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

MESSAGE_LIMIT = 4096


def send_message(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured, skipping delivery. Message was:\n%s", text)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for i in range(0, len(text), MESSAGE_LIMIT):
        chunk = text[i:i + MESSAGE_LIMIT]
        try:
            resp = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": chunk}, timeout=15)
            resp.raise_for_status()
        except requests.RequestException:
            logger.exception("Telegram send failed")
