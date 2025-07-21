import logging

from aiogram import Bot, Router, F
from aiogram.types import Message, PreCheckoutQuery
from aiohttp import ClientSession
from beanie import PydanticObjectId

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from src.models import Payment

router = Router()

TOTAL_STARS_EARNED = 0


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

    if payment.status == "pending" and payment.webhook:
        data = payment.model_dump()

        data["id"] = str(data["id"])
        data["created_at"] = data["created_at"].isoformat()
        data["payload"] = payment.payload or {}

        try:
            async with ClientSession() as session:
                async with session.post(payment.webhook, json=data, headers={"ngrok-skip-browser-warning": "true"}) as response:
                    if response.status != 200:
                        logger.error(f"Webhook for payment {payment.id} failed with status {response.status}")
                        await message.answer("Error: Failed to notify the webhook.")
                        payment.status = "error"
                        await payment.save()
                        await bot.refund_star_payment(message.from_user.id, message.successful_payment.telegram_payment_charge_id)
                        return
        except Exception as e:
            logger.error(f"An exception occurred while sending webhook for payment {payment.id}: {e}")
            await message.answer("An internal error occurred while processing your payment webhook.")
            payment.status = "error"
            await payment.save()
            await bot.refund_star_payment(message.from_user.id, message.successful_payment.telegram_payment_charge_id)
            return

    payment.status = "completed"
    await payment.save()

    global TOTAL_STARS_EARNED
    TOTAL_STARS_EARNED += message.successful_payment.total_amount
    logger.info(f"Total stars earned: {TOTAL_STARS_EARNED}")

    await message.answer("Payment was successful!\nThank you for your purchase!")
