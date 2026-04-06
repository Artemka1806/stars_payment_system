import asyncio
import logging
import uuid

from fastapi import APIRouter, HTTPException, status

from src.schemas.broadcast import BroadcastPreviewRequest, BroadcastSendRequest
from src.services import bots_service
from src.services.broadcast import (
    get_user_data,
    get_unique_user_ids,
    init_broadcast_stats,
    prepare_broadcast_media,
    prepare_and_run_broadcast,
)
from src.utils.redis import get_redis

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/broadcast",
    tags=["Broadcast"],
)


@router.post("/preview")
async def broadcast_preview(body: BroadcastPreviewRequest):
    bot = bots_service.get_bot_by_id(body.bot_id)
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

    user_ids = await get_unique_user_ids(body.bot_id, body.filters)
    return {"bot_id": body.bot_id, "user_count": len(user_ids)}


@router.post("/send")
async def broadcast_send(body: BroadcastSendRequest):
    bot = bots_service.get_bot_by_id(body.bot_id)
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

    user_data = await get_user_data(body.bot_id, body.filters)
    if not user_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No users found matching filters")

    try:
        photo, video = prepare_broadcast_media(body.photo_url, body.video_url)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    broadcast_id = uuid.uuid4().hex
    rc = get_redis()
    user_count = len(user_data)
    await init_broadcast_stats(broadcast_id, user_count, rc)

    asyncio.create_task(prepare_and_run_broadcast(
        broadcast_id, bot, body.bot_id, user_data,
        body.text, photo, video, rc,
    ))

    return {"broadcast_id": broadcast_id, "user_count": user_count, "message": "Broadcast started"}


@router.get("/{broadcast_id}/status")
async def broadcast_status(broadcast_id: str):
    rc = get_redis()
    stats = await rc.hgetall(f"broadcast:{broadcast_id}:stats")
    if not stats:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Broadcast not found or expired")

    return {
        "broadcast_id": broadcast_id,
        "total": int(stats.get("total", 0)),
        "processed": int(stats.get("processed", 0)),
        "success": int(stats.get("success", 0)),
        "failed": int(stats.get("failed", 0)),
        "is_finished": stats.get("finished") == "1",
        "error": stats.get("error") or None,
    }
