from aiogram import Dispatcher
from aiogram.types import Update
from fastapi import APIRouter, HTTPException, Request, status, Header

from src.services.bots import bots_service
from src.bot.handlers import ALL_ROUTERS
from src.utils.settings import settings

router = APIRouter(
    prefix="/bot",
    include_in_schema=False
)

dp = Dispatcher()
dp.include_router(*ALL_ROUTERS)


@router.post("/{id}/webhook")
async def handle_bot_webhook(
    id: int, 
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None, alias="X-Telegram-Bot-Api-Secret-Token")
):
    """Handle incoming webhook requests for a specific bot."""
    if x_telegram_bot_api_secret_token != settings.TELEGRAM_SECRET.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid secret token"
        )
    
    bot = bots_service.get_bot_by_id(id)
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )
    
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)

    return {
        "ok": True,
        "message": "Webhook handled successfully",
        "bot_id": id,
        "update_id": update.update_id
    }
    