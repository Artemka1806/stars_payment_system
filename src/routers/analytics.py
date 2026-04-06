from datetime import datetime, timedelta
from typing import Optional

from beanie.operators import GTE, LTE, Eq
from fastapi import APIRouter, Query

from src.models import Payment

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


@router.get("/payments")
async def get_payments_analytics(
    date_from: Optional[datetime] = Query(None, description="Start date (default: 30 days ago)"),
    date_to: Optional[datetime] = Query(None, description="End date (default: today)"),
    status: Optional[str] = Query("completed", description="Payment status filter"),
    bot_id: Optional[int] = Query(None, description="Bot ID filter"),
):
    now = datetime.utcnow()
    if date_to is None:
        date_to = now
    if date_from is None:
        date_from = now - timedelta(days=30)

    filters = [
        GTE(Payment.created_at, date_from),
        LTE(Payment.created_at, date_to),
    ]
    if status is not None:
        filters.append(Eq(Payment.status, status))
    if bot_id is not None:
        filters.append(Eq(Payment.bot_id, bot_id))

    payments = await Payment.find(*filters).to_list()

    total_count = len(payments)
    total_amount = sum(p.amount for p in payments)

    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "status": status,
        "bot_id": bot_id,
        "total_count": total_count,
        "total_amount": total_amount,
    }
