import asyncio
import base64
import binascii
import logging
import mimetypes
import re
from typing import Dict, List, Optional, Union

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest
from aiogram.types import BufferedInputFile
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as aioredis

from src.models import Payment
from src.schemas.broadcast import BroadcastFilters, DEFAULT_LANG
from src.utils.settings import settings

logger = logging.getLogger(__name__)

BROADCAST_TTL = 86400  # 24 hours
SUBDOMAIN_RE = re.compile(r"https?://api(\d+)\.")
ResolvedMedia = Optional[Union[str, BufferedInputFile]]


async def get_user_data(bot_id: int, filters: Optional[BroadcastFilters] = None) -> List[dict]:
    """Returns list of {user_id, order_id, webhook} per unique user (latest payment)."""
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
        {"$sort": {"created_at": -1}},
        {"$group": {
            "_id": "$payload.user_id",
            "order_id": {"$first": "$payload.order_id"},
            "webhook": {"$first": "$webhook"},
        }},
    ]
    results = await Payment.aggregate(pipeline).to_list()
    return [doc for doc in results if doc["_id"] is not None]


async def get_unique_user_ids(bot_id: int, filters: Optional[BroadcastFilters] = None) -> List[int]:
    data = await get_user_data(bot_id, filters)
    return [doc["_id"] for doc in data]


def _parse_db_name(webhook: Optional[str]) -> Optional[str]:
    if not webhook:
        return None
    m = SUBDOMAIN_RE.match(webhook)
    if not m:
        return None
    return f"sub_data{m.group(1)}"


async def _find_lang_in_db(client: AsyncIOMotorClient, db_name: str, order_id: str) -> Optional[str]:
    try:
        oid = ObjectId(order_id)
    except Exception:
        return None
    doc = await client[db_name]["payment_order"].find_one({"_id": oid}, {"lang_code": 1})
    if doc and doc.get("lang_code"):
        return doc["lang_code"]
    return None


async def _find_lang_fallback(client: AsyncIOMotorClient, order_id: str) -> Optional[str]:
    try:
        oid = ObjectId(order_id)
    except Exception:
        return None
    db_names = await client.list_database_names()
    for db_name in db_names:
        if not db_name.startswith("sub_data"):
            continue
        doc = await client[db_name]["payment_order"].find_one({"_id": oid}, {"lang_code": 1})
        if doc and doc.get("lang_code"):
            return doc["lang_code"]
    return None


async def resolve_user_langs(user_data: List[dict]) -> Dict[int, str]:
    """Resolve lang_code for each user_id. Returns {user_id: lang_code}."""
    client = AsyncIOMotorClient(settings.EXTERNAL_MONGO_URI)
    try:
        result = {}
        for entry in user_data:
            user_id = entry["_id"]
            order_id = entry.get("order_id")
            webhook = entry.get("webhook")

            if not order_id:
                result[user_id] = DEFAULT_LANG
                continue

            lang = None
            db_name = _parse_db_name(webhook)
            if db_name:
                lang = await _find_lang_in_db(client, db_name, order_id)

            if not lang:
                lang = await _find_lang_fallback(client, order_id)

            result[user_id] = lang if lang in ("uk", "ru", "en") else DEFAULT_LANG
        return result
    finally:
        client.close()


def _get_localized_text(texts: Optional[Dict[str, str]], lang: str) -> Optional[str]:
    if not texts:
        return None
    return texts.get(lang, texts.get(DEFAULT_LANG))


def _resolve_media(value: Optional[str]) -> ResolvedMedia:
    if not value:
        return None
    if value.startswith("data:"):
        try:
            header, encoded = value.split(",", 1)
        except ValueError as exc:
            raise ValueError("Invalid media data URL") from exc
        if ";base64" not in header:
            raise ValueError("Only base64 media uploads are supported")
        mime_type = header[5:].split(";", 1)[0]
        extension = mimetypes.guess_extension(mime_type) or ".bin"
        try:
            data = base64.b64decode(encoded, validate=True)
        except binascii.Error as exc:
            raise ValueError("Invalid base64 media payload") from exc
        return BufferedInputFile(data, filename=f"upload{extension}")
    return value


def prepare_broadcast_media(photo_url: Optional[str], video_url: Optional[str]) -> tuple[ResolvedMedia, ResolvedMedia]:
    return _resolve_media(photo_url), _resolve_media(video_url)


async def _send_message(bot: Bot, user_id: int, text: Optional[str], photo: ResolvedMedia, video: ResolvedMedia):
    if video:
        await bot.send_video(user_id, video=video, caption=text)
    elif photo:
        await bot.send_photo(user_id, photo=photo, caption=text)
    else:
        await bot.send_message(user_id, text=text)


async def run_broadcast(
    broadcast_id: str,
    bot: Bot,
    bot_id: int,
    user_ids: List[int],
    user_langs: Dict[int, str],
    texts: Optional[Dict[str, str]],
    photo: ResolvedMedia,
    video: ResolvedMedia,
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

        lang = user_langs.get(user_id, DEFAULT_LANG)
        text = _get_localized_text(texts, lang)

        try:
            await _send_message(bot, user_id, text, photo, video)
            await rc.set(user_key, "ok", ex=BROADCAST_TTL)
            await rc.hincrby(stats_key, "success", 1)
        except TelegramRetryAfter as e:
            logger.warning("Rate limited, sleeping %s seconds", e.retry_after)
            await asyncio.sleep(e.retry_after)
            try:
                await _send_message(bot, user_id, text, photo, video)
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
        await asyncio.sleep(0.1)

    await rc.hset(stats_key, "finished", 1)
    logger.info("Broadcast %s finished", broadcast_id)
