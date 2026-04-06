from .bot import router as bot_router
from .bots import router as bots_router
from .analytics import router as analytics_router
from .broadcast import router as broadcast_router

ALL_ROUTERS = [
    bot_router,
    bots_router,
    analytics_router,
    broadcast_router,
]

__all__ = ["ALL_ROUTERS", ]
