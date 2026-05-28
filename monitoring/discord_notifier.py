"""
Discord webhook notifier.

Set DISCORD_WEBHOOK_URL in .env to enable. No-op if unset.
"""

import requests
from loguru import logger


class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, message: str):
        if not self.webhook_url:
            return
        try:
            requests.post(
                self.webhook_url,
                json={"content": message[:1900]},
                timeout=10,
            )
        except Exception as e:
            logger.warning(f"Discord notification failed: {e}")
