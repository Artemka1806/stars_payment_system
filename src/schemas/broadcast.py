from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class BroadcastFilters(BaseModel):
    status: str = Field("completed", description="Payment status filter")
    date_from: Optional[datetime] = Field(None, description="Only users who paid after this date")
    date_to: Optional[datetime] = Field(None, description="Only users who paid before this date")


class BroadcastPreviewRequest(BaseModel):
    bot_id: int
    filters: Optional[BroadcastFilters] = None


class BroadcastSendRequest(BaseModel):
    bot_id: int
    text: Optional[str] = Field(None, description="Message text")
    photo_url: Optional[str] = Field(None, description="Photo URL to send")
    filters: Optional[BroadcastFilters] = None

    @model_validator(mode="after")
    def check_text_or_photo(self):
        if not self.text and not self.photo_url:
            raise ValueError("At least text or photo_url must be provided")
        return self
