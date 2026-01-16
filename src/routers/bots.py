from fastapi import APIRouter, HTTPException, status

from src.schemas import CreateBot
from src.services import bots_service
from src.utils import settings

router = APIRouter(
    prefix="/bots",
    tags=["Bots"],
)


@router.post("", response_model=dict)
async def create_bot(payload: CreateBot):
    """Create a new bot record."""
    try:
        record, created = await bots_service.create_bot_record(payload.token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    bot = bots_service.get_bot_by_id(record.bot_id)
    if bot:
        webhook_url = f"{settings.API_URL}/bot/{bot.id}/webhook"
        secret = settings.TELEGRAM_SECRET.get_secret_value()
        await bots_service.set_bot_webhook(bot, webhook_url, secret)

    return {"message": "Bot record created" if created else "Bot record already exists", "bot_id": record.bot_id}
