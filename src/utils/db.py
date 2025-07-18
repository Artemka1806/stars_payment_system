from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from .settings import settings

client = AsyncIOMotorClient(settings.MONGO_DB_URI)


async def init_db(models: list = []):
    data = await init_beanie(getattr(client, settings.MONGO_DB_NAME), document_models=models)
    return data
