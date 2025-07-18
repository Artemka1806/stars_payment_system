from aiogram import Bot, Router, F
from aiogram.types import Message, PreCheckoutQuery
from aiohttp import ClientSession
from beanie import PydanticObjectId

from src.models import Payment

router = Router()


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    """Confirm the pre-checkout process."""
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def success_payment_handler(message: Message, bot: Bot):
    """Handle successful payment."""
    payment_id = message.successful_payment.invoice_payload

    payment = await Payment.get(PydanticObjectId(payment_id))
    if not payment:
        await message.answer("Error: Payment not found.")
        await bot.refund_star_payment(message.from_user.id, message.successful_payment.telegram_payment_charge_id)
        return

    if payment.status != "pending" and payment.webhook:
        data = payment.model_dump()
        data["id"] = str(data["id"])
        data["created_at"] = data["created_at"].isoformat()
        async with ClientSession() as session:
            async with session.post(payment.webhook, json=data) as response:
                if response.status != 200:
                    await message.answer("Error: Failed to notify the webhook.")
                    payment.status = "error"
                    await payment.save()
                    await bot.refund_star_payment(message.from_user.id, message.successful_payment.telegram_payment_charge_id)
                    await session.close()

    payment.status = "completed"
    await payment.save()

    await message.answer("Payment was successful!\nThank you for your purchase!")
