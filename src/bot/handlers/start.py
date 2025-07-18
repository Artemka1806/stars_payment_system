from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart

router = Router()

@router.message(CommandStart())
async def start_command(message: Message):
    """Handle the /start command."""
    await message.answer("Welcome to the Stars Payment System Bot!")
