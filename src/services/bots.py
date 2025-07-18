import os
from typing import List, Optional

from aiogram import Bot

from src.utils.settings import settings


class BotsService:
    def __get_tokens(self) -> List[str]:
        """Retrieve bot tokens from environment variables."""
        tokens = []
        for key, value in os.environ.items():
            if key.startswith(settings.ENV_BOT_TOKEN_PREFIX):
                tokens.append(value)
        return tokens
    
    def get_bots(self) -> List[Bot]:
        """Create Bot instances for each token and return them."""
        tokens = self.__get_tokens()
        return [Bot(token=token) for token in tokens]

    async def close_bots(self, bots: List[Bot]) -> None:
        """Close all bot instances."""
        for bot in bots:
            await bot.session.close()

    async def set_bot_webhook(self, bot: Bot, webhook_url: str, secret_token: str) -> bool:
        """Set the webhook for a specific bot instance."""
        return await bot.set_webhook(webhook_url, secret_token=secret_token)

    def get_bots_id(self) -> List[int]:
        """Get the IDs of all bot instances."""
        bots = self.get_bots()
        if not bots:
            return []
        return [bot.id for bot in bots]

    def get_bot_by_id(self, bot_id: int) -> Optional[Bot]:
        """Get a specific bot instance by its ID."""
        bots = self.get_bots()
        for bot in bots:
            if bot.id == bot_id:
                return bot
        return None

bots_service = BotsService()
