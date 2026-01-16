from pydantic import BaseModel
from pydantic.fields import Field


class CreateBot(BaseModel):
    """Schema for creating a bot record."""
    token: str = Field(..., description="Telegram bot token")
