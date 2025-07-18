from fastapi import APIRouter, HTTPException, status

from src.models import Payment
from src.schemas import CreatePayment
from src.services import bots_service

router = APIRouter(
    prefix="/bot",
    tags=["Bot"],
)


@router.post("/{id}/create-payment", response_model=dict)
async def create_payment(id: int, payment: CreatePayment):
    """Create a new payment."""
    bot = bots_service.get_bot_by_id(id)
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
    
    payment = Payment(bot_id=id, **payment.model_dump())
    await payment.save()
    
    payment_link = await bots_service.create_payment_link(id, str(payment.id), payment)
    return {"message": "Payment created successfully", "payment_id": str(payment.id), "payment_link": payment_link}
