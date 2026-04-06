import asyncio
import uuid

from fastapi import APIRouter, HTTPException, status

from src.schemas.broadcast import BroadcastPreviewRequest, BroadcastSendRequest
from src.services import bots_service
from src.services.broadcast import (
    get_user_data,
    get_unique_user_ids,
    prepare_broadcast_media,
    resolve_user_langs,
    run_broadcast,
)
from src.utils.redis import get_redis

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

    user_ids = [doc["_id"] for doc in user_data]
    user_langs = await resolve_user_langs(user_data)
    try:
        photo, video = prepare_broadcast_media(body.photo_url, body.video_url)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    broadcast_id = uuid.uuid4().hex
    rc = get_redis()

    asyncio.create_task(run_broadcast(
        broadcast_id, bot, body.bot_id, user_ids, user_langs,
        body.text, photo, video, rc,
    ))

    return {"broadcast_id": broadcast_id, "user_count": len(user_ids), "message": "Broadcast started"}


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
    }
