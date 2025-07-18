from .start import router as start_router
from .payment import router as payment_router

ALL_ROUTERS = [
    start_router,
    payment_router
]

__all__ = ["ALL_ROUTERS", ]
