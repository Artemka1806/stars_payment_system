import asyncio
import base64
import binascii
from collections import defaultdict
import logging
import mimetypes
import re
from time import perf_counter
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
    started_at = perf_counter()
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
    logger.info("Loading broadcast users for bot=%s with filters=%s", bot_id, match_stage)
    results = await Payment.aggregate(pipeline).to_list()
    user_data = [doc for doc in results if doc["_id"] is not None]
    logger.info(
        "Loaded %s unique broadcast users for bot=%s in %.3fs",
        len(user_data),
        bot_id,
        perf_counter() - started_at,
    )
    return user_data


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


def _parse_object_id(value: Optional[str]) -> Optional[ObjectId]:
    try:
        return ObjectId(value)
    except Exception:
        return None


async def _find_langs_in_db(client: AsyncIOMotorClient, db_name: str, order_ids: List[ObjectId]) -> Dict[str, str]:
    unique_order_ids = list(dict.fromkeys(order_ids))
    if not unique_order_ids:
        return {}

    started_at = perf_counter()
    docs = await client[db_name]["payment_order"].find(
        {"_id": {"$in": unique_order_ids}},
        {"lang_code": 1},
    ).to_list(length=None)
    result = {
        str(doc["_id"]): doc["lang_code"]
        for doc in docs
        if doc.get("lang_code")
    }
    logger.info(
        "Resolved %s/%s order languages in db=%s in %.3fs",
        len(result),
        len(unique_order_ids),
        db_name,
        perf_counter() - started_at,
    )
    return result


async def resolve_user_langs(user_data: List[dict]) -> Dict[int, str]:
    """Resolve lang_code for each user_id. Returns {user_id: lang_code}."""
    started_at = perf_counter()
    client = AsyncIOMotorClient(settings.EXTERNAL_MONGO_URI)
    try:
        result: Dict[int, str] = {}
        order_to_user_ids: Dict[str, List[int]] = defaultdict(list)
        preferred_db_order_ids: Dict[str, List[ObjectId]] = defaultdict(list)
        unresolved_orders: Dict[str, ObjectId] = {}

        for entry in user_data:
            user_id = entry["_id"]
            result[user_id] = DEFAULT_LANG
            order_id = entry.get("order_id")
            webhook = entry.get("webhook")

            if not order_id:
                continue

            order_object_id = _parse_object_id(order_id)
            if order_object_id is None:
                logger.warning("Skipping invalid order_id=%s for user_id=%s", order_id, user_id)
                continue

            order_key = str(order_object_id)
            order_to_user_ids[order_key].append(user_id)
            unresolved_orders[order_key] = order_object_id

            db_name = _parse_db_name(webhook)
            if db_name:
                preferred_db_order_ids[db_name].append(order_object_id)

        logger.info(
            "Resolving languages for broadcast users=%s orders=%s preferred_dbs=%s",
            len(user_data),
            len(unresolved_orders),
            len(preferred_db_order_ids),
        )

        resolved_order_langs: Dict[str, str] = {}
        queried_db_names = set()

        for db_name, order_ids in preferred_db_order_ids.items():
            db_langs = await _find_langs_in_db(client, db_name, order_ids)
            resolved_order_langs.update(db_langs)
            queried_db_names.add(db_name)

        unresolved_orders = {
            order_key: order_object_id
            for order_key, order_object_id in unresolved_orders.items()
            if order_key not in resolved_order_langs
        }

        if unresolved_orders:
            db_names = await client.list_database_names()
            fallback_db_names = [
                db_name for db_name in db_names
                if db_name.startswith("sub_data") and db_name not in queried_db_names
            ]
            logger.info(
                "Running fallback language lookup for %s unresolved orders across %s dbs",
                len(unresolved_orders),
                len(fallback_db_names),
            )

            for db_name in fallback_db_names:
                if not unresolved_orders:
                    break
                db_langs = await _find_langs_in_db(client, db_name, list(unresolved_orders.values()))
                if not db_langs:
                    continue
                resolved_order_langs.update(db_langs)
                for order_key in db_langs:
                    unresolved_orders.pop(order_key, None)

        for order_key, user_ids in order_to_user_ids.items():
            lang = resolved_order_langs.get(order_key)
            normalized_lang = lang if lang in ("uk", "ru", "en") else DEFAULT_LANG
            for user_id in user_ids:
                result[user_id] = normalized_lang

        resolved_user_count = sum(1 for lang in result.values() if lang != DEFAULT_LANG)
        logger.info(
            "Resolved broadcast languages for users=%s resolved=%s defaulted=%s unresolved_orders=%s in %.3fs",
            len(result),
            resolved_user_count,
            len(result) - resolved_user_count,
            len(unresolved_orders),
            perf_counter() - started_at,
        )
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


async def init_broadcast_stats(broadcast_id: str, total: int, rc: aioredis.Redis) -> None:
    stats_key = f"broadcast:{broadcast_id}:stats"
    await rc.hset(stats_key, mapping={
        "total": total,
        "processed": 0,
        "success": 0,
        "failed": 0,
        "finished": 0,
        "error": "",
    })
    await rc.expire(stats_key, BROADCAST_TTL)
    logger.info("Initialized broadcast stats for broadcast=%s total=%s", broadcast_id, total)


async def mark_broadcast_error(broadcast_id: str, total: int, error: str, rc: aioredis.Redis) -> None:
    stats_key = f"broadcast:{broadcast_id}:stats"
    await rc.hset(stats_key, mapping={
        "total": total,
        "processed": total,
        "failed": total,
        "finished": 1,
        "error": error,
    })
    await rc.expire(stats_key, BROADCAST_TTL)
    logger.error("Broadcast %s failed before send loop: %s", broadcast_id, error)


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
    started_at = perf_counter()
    stats_key = f"broadcast:{broadcast_id}:stats"
    if not await rc.exists(stats_key):
        await init_broadcast_stats(broadcast_id, len(user_ids), rc)

    logger.info(
        "Starting broadcast send loop broadcast=%s bot=%s users=%s has_text=%s has_photo=%s has_video=%s",
        broadcast_id,
        bot_id,
        len(user_ids),
        bool(texts),
        bool(photo),
        bool(video),
    )

    for index, user_id in enumerate(user_ids, start=1):
        user_key = f"broadcast:{broadcast_id}:{bot_id}:{user_id}"

        if await rc.exists(user_key):
            await rc.hincrby(stats_key, "processed", 1)
            logger.info("Skipping already processed broadcast user=%s broadcast=%s", user_id, broadcast_id)
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
        if index % 25 == 0 or index == len(user_ids):
            logger.info(
                "Broadcast progress broadcast=%s processed=%s total=%s",
                broadcast_id,
                index,
                len(user_ids),
            )
        await asyncio.sleep(0.1)

    await rc.hset(stats_key, "finished", 1)
    stats = await rc.hgetall(stats_key)
    logger.info(
        "Broadcast %s finished in %.3fs success=%s failed=%s processed=%s total=%s",
        broadcast_id,
        perf_counter() - started_at,
        stats.get("success", 0),
        stats.get("failed", 0),
        stats.get("processed", 0),
        stats.get("total", 0),
    )


async def prepare_and_run_broadcast(
    broadcast_id: str,
    bot: Bot,
    bot_id: int,
    user_data: List[dict],
    texts: Optional[Dict[str, str]],
    photo: ResolvedMedia,
    video: ResolvedMedia,
    rc: aioredis.Redis,
) -> None:
    user_ids = [doc["_id"] for doc in user_data]
    logger.info(
        "Preparing broadcast=%s bot=%s users=%s before send loop",
        broadcast_id,
        bot_id,
        len(user_ids),
    )
    try:
        user_langs = await resolve_user_langs(user_data)
    except Exception:
        logger.exception("Failed to resolve user languages for broadcast %s", broadcast_id)
        await mark_broadcast_error(
            broadcast_id,
            len(user_ids),
            "Failed to resolve user languages from external MongoDB",
            rc,
        )
        return

    await run_broadcast(
        broadcast_id,
        bot,
        bot_id,
        user_ids,
        user_langs,
        texts,
        photo,
        video,
        rc,
    )
