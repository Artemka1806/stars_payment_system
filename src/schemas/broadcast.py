from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field, model_validator

SUPPORTED_LANGS = ("uk", "ru", "en")
DEFAULT_LANG = "en"


class BroadcastFilters(BaseModel):
    status: str = Field("completed", description="Payment status filter")
    date_from: Optional[datetime] = Field(None, description="Only users who paid after this date")
    date_to: Optional[datetime] = Field(None, description="Only users who paid before this date")


class BroadcastPreviewRequest(BaseModel):
    bot_id: int
    filters: Optional[BroadcastFilters] = None


class BroadcastSendRequest(BaseModel):
    bot_id: int
    text: Optional[Dict[str, str]] = Field(None, description='Localized text: {"en": "...", "uk": "...", "ru": "..."}')
    photo_url: Optional[str] = Field(None, description="Photo URL to send")
    video_url: Optional[str] = Field(None, description="Video URL to send")
    filters: Optional[BroadcastFilters] = None

    @model_validator(mode="after")
    def check_content(self):
        if not self.text and not self.photo_url and not self.video_url:
            raise ValueError("At least text, photo_url, or video_url must be provided")
        if self.photo_url and self.video_url:
            raise ValueError("Cannot send both photo and video in one broadcast")
        if self.text and DEFAULT_LANG not in self.text:
            raise ValueError(f"text must include '{DEFAULT_LANG}' as fallback")
        return self
