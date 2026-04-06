import asyncio
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Security
from fastapi.middleware.cors import CORSMiddleware

from src.bot import bot_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from src.services import bots_service
from src.utils import settings, init_db, init_redis, close_redis, validate_api_key
from src.models import ALL_DB_MODELS
from src.routers import ALL_ROUTERS


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    await init_db(ALL_DB_MODELS)
    await init_redis()

    BASE_URL = settings.API_URL
    
    await bots_service.initialize_bots()

    async def _set_webhooks_in_background() -> None:
        secret = settings.TELEGRAM_SECRET.get_secret_value()
        for bot in bots_service.bots:
            webhook_url = f"{BASE_URL}/bot/{bot.id}/webhook"
            logger.info("Setting webhook for bot %s to %s", bot.id, webhook_url)
            try:
                await bots_service.set_bot_webhook(bot, webhook_url, secret)
            except Exception:
                logger.exception("Failed to set webhook for bot %s", bot.id)
            await asyncio.sleep(1)

    webhook_task = asyncio.create_task(_set_webhooks_in_background())

    yield
    
    if not webhook_task.done():
        webhook_task.cancel()
        try:
            await webhook_task
        except asyncio.CancelledError:
            pass
    await bots_service.close_bots()
    await close_redis()

app = FastAPI(title="Stars Payment System API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(bot_router)
for router in ALL_ROUTERS:
    app.include_router(router, prefix="/api", dependencies=[Security(validate_api_key)])


@app.get("/", include_in_schema=False)
async def read_root():
    return {"message": "Welcome to the Stars Payment System API"}
