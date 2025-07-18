from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.bot import bot_router
from src.services.bots import bots_service
from src.utils.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    BASE_URL = settings.API_URL

    bots = bots_service.get_bots()
    for bot in bots:
        await bots_service.set_bot_webhook(bot, f"{BASE_URL}/bot/{bot.id}/webhook", settings.TELEGRAM_SECRET.get_secret_value())
    
    yield
    
    await bots_service.close_bots(bots)

app = FastAPI(title="Stars Payment System API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(bot_router)


@app.get("/", include_in_schema=False)
async def read_root():
    return {"message": "Welcome to the Stars Payment System API"}
