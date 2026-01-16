from .payment import Payment
from .bot import BotRecord

ALL_DB_MODELS = [Payment, BotRecord,]

__all__ = [model.__name__ for model in ALL_DB_MODELS]
__all__.extend(["ALL_DB_MODELS"])
