import asyncio
import logging
from typing import List, Optional

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest
import redis.asyncio as aioredis

from src.models import Payment
from src.schemas.broadcast import BroadcastFilters

logger = logging.getLogger(__name__)

BROADCAST_TTL = 86400  # 24 hours


async def get_unique_user_ids(bot_id: int, filters: Optional[BroadcastFilters] = None) -> List[int]:
    match_stage = {
        "bot_id": bot_id,
        "payload.user_id": {"$exists": True, "$ne": None},
    }
    if filters:
        match_stage["status"] = filters.status
        if filters.date_from:
            match_stage.setdefault("created_at", {})["$gte"] = filters.date_from
        if filters.date_to:
            match_stage.setdefault("created_at", {})["$lte"] = filters.date_to
    else:
        match_stage["status"] = "completed"

    pipeline = [
        {"$match": match_stage},
        {"$group": {"_id": "$payload.user_id"}},
    ]
    results = await Payment.aggregate(pipeline).to_list()
    return [doc["_id"] for doc in results if doc["_id"] is not None]


async def run_broadcast(
    broadcast_id: str,
    bot: Bot,
    bot_id: int,
    user_ids: List[int],
    text: Optional[str],
    photo_url: Optional[str],
    rc: aioredis.Redis,
) -> None:
    stats_key = f"broadcast:{broadcast_id}:stats"
    await rc.hset(stats_key, mapping={
        "total": len(user_ids),
        "processed": 0,
        "success": 0,
        "failed": 0,
        "finished": 0,
    })
    await rc.expire(stats_key, BROADCAST_TTL)

    for user_id in user_ids:
        user_key = f"broadcast:{broadcast_id}:{bot_id}:{user_id}"

        if await rc.exists(user_key):
            await rc.hincrby(stats_key, "processed", 1)
            continue

        try:
            if photo_url:
                await bot.send_photo(user_id, photo=photo_url, caption=text)
            else:
                await bot.send_message(user_id, text=text)
            await rc.set(user_key, "ok", ex=BROADCAST_TTL)
            await rc.hincrby(stats_key, "success", 1)
        except TelegramRetryAfter as e:
            logger.warning("Rate limited, sleeping %s seconds", e.retry_after)
            await asyncio.sleep(e.retry_after)
            try:
                if photo_url:
                    await bot.send_photo(user_id, photo=photo_url, caption=text)
                else:
                    await bot.send_message(user_id, text=text)
                await rc.set(user_key, "ok", ex=BROADCAST_TTL)
                await rc.hincrby(stats_key, "success", 1)
            except Exception:
                logger.exception("Failed to send to %s after retry", user_id)
                await rc.set(user_key, "failed", ex=BROADCAST_TTL)
                await rc.hincrby(stats_key, "failed", 1)
        except (TelegramForbiddenError, TelegramBadRequest):
            logger.info("Cannot send to user %s (blocked/invalid)", user_id)
            await rc.set(user_key, "failed", ex=BROADCAST_TTL)
            await rc.hincrby(stats_key, "failed", 1)
        except Exception:
            logger.exception("Unexpected error sending to user %s", user_id)
            await rc.set(user_key, "failed", ex=BROADCAST_TTL)
            await rc.hincrby(stats_key, "failed", 1)

        await rc.hincrby(stats_key, "processed", 1)
        await asyncio.sleep(0.05)

    await rc.hset(stats_key, "finished", 1)
    logger.info("Broadcast %s finished", broadcast_id)
