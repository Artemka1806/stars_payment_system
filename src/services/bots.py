import os
from typing import List, Optional, Dict, Tuple
import logging

from aiogram import Bot
from aiogram.types import LabeledPrice
from cryptography.fernet import Fernet, InvalidToken

from src.schemas import CreatePayment
from src.models import BotRecord

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

    def __get_fernet(self) -> Fernet:
        """Create a Fernet instance from the configured key."""
        key = settings.BOT_TOKEN_ENCRYPTION_KEY.get_secret_value()
        try:
            return Fernet(key)
        except Exception as exc:
            raise ValueError("Invalid BOT_TOKEN_ENCRYPTION_KEY value.") from exc

    def __parse_bot_id(self, token: str) -> Optional[int]:
        """Parse a bot ID from a Telegram bot token."""
        if ":" not in token:
            return None
        bot_id_part = token.split(":", 1)[0]
        if not bot_id_part.isdigit():
            return None
        return int(bot_id_part)

    def __encrypt_token(self, token: str) -> str:
        fernet = self.__get_fernet()
        return fernet.encrypt(token.encode("utf-8")).decode("utf-8")

    def __decrypt_token(self, token_encrypted: str) -> str:
        fernet = self.__get_fernet()
        try:
            return fernet.decrypt(token_encrypted.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Failed to decrypt bot token.") from exc

    async def __seed_bots_from_env(self) -> None:
        """Seed bot records from environment variables (deprecated)."""
        tokens = self.__get_tokens()
        if not tokens:
            return
        logger.warning("Environment bot tokens are deprecated; use the API to store tokens in DB.")

        for token in tokens:
            bot_id = self.__parse_bot_id(token)
            if bot_id is None:
                logger.warning("Skipping invalid bot token in environment.")
                continue
            existing = await BotRecord.find_one(BotRecord.bot_id == bot_id)
            if existing:
                try:
                    existing_token = self.__decrypt_token(existing.token_encrypted)
                except ValueError:
                    logger.warning("Failed to decrypt existing token for bot %s.", bot_id)
                    continue
                if existing_token != token:
                    existing.token_encrypted = self.__encrypt_token(token)
                    await existing.save()
                continue
            record = BotRecord(bot_id=bot_id, token_encrypted=self.__encrypt_token(token))
            await record.insert()
    
    async def initialize_bots(self):
        """
        Створює екземпляри ботів ОДИН РАЗ і зберігає їх.
        Цей метод потрібно викликати під час старту додатку.
        """
        await self.__seed_bots_from_env()
        records = await BotRecord.find_all().to_list()
        if not records:
            logger.warning("No bot records found.")
            return

        tokens = []
        for record in records:
            try:
                tokens.append(self.__decrypt_token(record.token_encrypted))
            except ValueError:
                logger.warning("Skipping bot %s due to token decryption failure.", record.bot_id)

        if not tokens:
            logger.warning("No bot tokens available after decryption.")
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

    async def create_bot_record(self, token: str) -> Tuple[BotRecord, bool]:
        """Create a bot record and ensure it is initialized in memory."""
        bot_id = self.__parse_bot_id(token)
        if bot_id is None:
            raise ValueError("Invalid bot token format.")

        existing = await BotRecord.find_one(BotRecord.bot_id == bot_id)
        if existing:
            if bot_id not in self.bots_map:
                try:
                    existing_token = self.__decrypt_token(existing.token_encrypted)
                    self.__add_bot_instance(existing_token)
                except ValueError:
                    logger.warning("Failed to decrypt token for existing bot %s.", bot_id)
            return existing, False

        record = BotRecord(bot_id=bot_id, token_encrypted=self.__encrypt_token(token))
        await record.insert()
        self.__add_bot_instance(token)
        return record, True

    def __add_bot_instance(self, token: str) -> None:
        """Add a bot instance to the in-memory registry."""
        bot = Bot(token=token)
        self.bots_map[bot.id] = bot
        if bot not in self.bots:
            self.bots.append(bot)

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
