from aiogram import Bot, Router
from aiogram.types import Message
from aiogram.filters import Command, CommandStart

router = Router()


@router.message(CommandStart())
async def start_command(message: Message):
    """Handle the /start command."""
    await message.answer("Welcome to the Stars Payment System Bot!")


@router.message(Command("refund"))
async def refund_command(message: Message, bot: Bot):
    """Handle the /refund command."""
    payment_id = message.text.split()[1] if len(message.text.split()) > 1 else None
    if payment_id:
        await bot.refund_star_payment(message.from_user.id, payment_id)
        await message.answer("Your payment has been refunded successfully.")
    else:
        await message.answer("Please provide the payment ID to refund.")
