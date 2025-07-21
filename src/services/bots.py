import os
from typing import List, Optional, Dict
import logging

from aiogram import Bot
from aiogram.types import LabeledPrice

from src.schemas import CreatePayment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from src.utils import settings


class BotsService:
    def __init__(self):
        self.bots: List[Bot] = []
        self.bots_map: Dict[int, Bot] = {}

    def __get_tokens(self) -> List[str]:
        """Retrieve bot tokens from environment variables."""
        tokens = []
        for key, value in os.environ.items():
            if key.startswith(settings.ENV_BOT_TOKEN_PREFIX):
                tokens.append(value)
        return tokens
    
    def initialize_bots(self):
        """
        Створює екземпляри ботів ОДИН РАЗ і зберігає їх.
        Цей метод потрібно викликати під час старту додатку.
        """
        tokens = self.__get_tokens()
        if not tokens:
            logger.warning("No bot tokens found.")
            return
        
        self.bots = [Bot(token=token) for token in tokens]
        self.bots_map = {bot.id: bot for bot in self.bots}
        logger.info(f"Initialized {len(self.bots)} bots.")

    async def close_bots(self) -> None:
        """Close all bot instances during application shutdown."""
        logger.info("Closing bot sessions...")
        for bot in self.bots:
            await bot.session.close()
        logger.info("All bot sessions closed.")

    async def set_bot_webhook(self, bot: Bot, webhook_url: str, secret_token: str) -> bool:
        """Set the webhook for a specific bot instance."""
        return await bot.set_webhook(webhook_url, secret_token=secret_token)

    def get_bots(self) -> List[Bot]:
        """
        Повертає список вже ініціалізованих екземплярів Bot.
        """
        return self.bots

    def get_bots_id(self) -> List[int]:
        """
        Повертає ID вже ініціалізованих екземплярів Bot.
        """
        return list(self.bots_map.keys())
    
    def get_bot_by_id(self, bot_id: int) -> Optional[Bot]:
        """
        Отримує екземпляр бота зі сховища, а не створює новий.
        """
        return self.bots_map.get(bot_id)

    async def create_payment_link(self, bot_id: int, payment_id: str, payment: CreatePayment) -> str:
        """Create a payment link for a specific bot."""
        bot = self.get_bot_by_id(bot_id)
        if not bot:
            raise ValueError(f"Bot with ID {bot_id} not found.")

        prices = [LabeledPrice(label=payment.label, amount=payment.amount)]

        return await bot.create_invoice_link(
            title=payment.title,
            description=payment.description,
            currency="XTR",
            photo_url= payment.photo_url,
            photo_size=payment.photo_size,
            photo_width=payment.photo_width,
            photo_height=payment.photo_height,
            payload=payment_id,
            prices=prices,
        )

bots_service = BotsService()
