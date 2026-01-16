from beanie import Document
from pydantic.fields import Field


class BotRecord(Document):
    """Represents a Telegram bot token stored in the database."""
    bot_id: int = Field(..., description="Telegram bot ID")
    token_encrypted: str = Field(..., description="Encrypted Telegram bot token")

    class Settings:
        name = "bots"
