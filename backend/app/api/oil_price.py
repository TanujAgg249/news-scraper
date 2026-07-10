"""
API router: Oil Price — latest price and recent history for sparkline.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import OilPrice
from app.schemas import OilPriceResponse, OilPriceEntry

router = APIRouter(prefix="/api/oil-price", tags=["Oil Price"])


@router.get("", response_model=OilPriceResponse)
def get_oil_price(db: Session = Depends(get_db)):
    """
    Get the latest oil price and the last 24 price entries for a sparkline chart.
    """
    # Fetch the last 24 records, ordered most-recent first
    records = (
        db.query(OilPrice)
        .order_by(desc(OilPrice.fetched_at))
        .limit(24)
        .all()
    )

    if not records:
        return OilPriceResponse(latest=None, history=[])

    latest = OilPriceEntry(
        price=records[0].price,
        change=records[0].change,
        change_pct=records[0].change_pct,
        fetched_at=records[0].fetched_at,
    )

    # History in chronological order (oldest first) for sparkline
    history = [
        OilPriceEntry(
            price=r.price,
            change=r.change,
            change_pct=r.change_pct,
            fetched_at=r.fetched_at,
        )
        for r in reversed(records)
    ]

    return OilPriceResponse(latest=latest, history=history)
