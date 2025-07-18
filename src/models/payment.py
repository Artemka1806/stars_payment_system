from datetime import datetime
from typing import Dict, Optional

from beanie import Document
from pydantic.fields import Field


class Payment(Document):
    """Represents a payment transaction in the system."""
    bot_id: int = Field(..., description="ID of the bot associated with the payment")
    webhook: Optional[str] = Field(None, description="Webhook URL for the payment")
    status: str = Field("pending", description="Status of the payment")
    title: str = Field(..., description="Title of the payment")
    description: Optional[str] = Field(None, description="Description of the payment")
    payload: Optional[Dict] = Field(..., description="Payload of the payment")
    label: str = Field(..., description="Label for the payment")
    amount: int = Field(..., description="Amount of the payment")
    photo_url: Optional[str] = Field(None, description="URL of the photo associated with the payment")
    photo_size: Optional[int] = Field(None, description="Size of the photo in bytes")
    photo_width: Optional[int] = Field(None, description="Width of the photo in pixels")
    photo_height: Optional[int] = Field(None, description="Height of the photo in pixels")

    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the payment was created")

    class Settings:
        name = "payments"
