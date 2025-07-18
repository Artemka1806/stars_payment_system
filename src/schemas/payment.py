from typing import Optional, Dict

from pydantic import BaseModel
from pydantic.fields import Field


class CreatePayment(BaseModel):
    """Schema for creating a new payment."""
    webhook: Optional[str] = Field(None, description="Webhook URL for the payment")
    title: str = Field(..., description="Title of the payment")
    description: Optional[str] = Field(None, description="Description of the payment")
    payload: Optional[Dict] = Field(..., description="Payload of the payment")
    label: str = Field(..., description="Label for the payment")
    amount: int = Field(..., description="Amount of the payment")
    photo_url: Optional[str] = Field(None, description="URL of the photo associated with the payment")
    photo_size: Optional[int] = Field(None, description="Size of the photo in bytes")
    photo_width: Optional[int] = Field(None, description="Width of the photo in pixels")
    photo_height: Optional[int] = Field(None, description="Height of the photo in pixels")
