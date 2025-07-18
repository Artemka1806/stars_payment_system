from .bot import router as bot_router

ALL_ROUTERS = [
    bot_router,
]

__all__ = ["ALL_ROUTERS", ]
