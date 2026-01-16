from .bot import router as bot_router
from .bots import router as bots_router

ALL_ROUTERS = [
    bot_router,
    bots_router,
]

__all__ = ["ALL_ROUTERS", ]
