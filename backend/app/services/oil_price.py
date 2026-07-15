"""
Oil price fetcher using yfinance (Brent Crude — BZ=F).
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import OilPrice
from app.logger import logger


def fetch_oil_price() -> Optional[dict]:
    """
    Fetch the latest Brent Crude oil price via yfinance.
    Returns a dict with price, change, change_pct, or None on failure.
    """
    try:
        import yfinance as yf

        ticker = yf.Ticker("BZ=F")
        info = ticker.fast_info

        # Try fast_info first
        price = float(info.get("lastPrice", 0) or info.get("last_price", 0))
        prev_close = float(info.get("previousClose", 0) or info.get("previous_close", 0))

        # Fallback to history if fast_info fails to get price
        if not price or price == 0:
            hist = ticker.history(period="5d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
                if len(hist) > 1:
                    prev_close = float(hist["Close"].iloc[-2])

        change = price - prev_close if prev_close else 0.0
        change_pct = (change / prev_close * 100) if prev_close else 0.0

        return {
            "price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
        }
    except Exception as exc:
        logger.error(f"Error fetching price: {exc}")
        return None


def fetch_and_store_oil_price(db: Session) -> Optional[dict]:
    """
    Fetch the current oil price and store it in the database.
    Returns the price dict or None on failure.
    """
    data = fetch_oil_price()
    if data is None:
        return None

    try:
        record = OilPrice(
            price=data["price"],
            change=data["change"],
            change_pct=data["change_pct"],
            fetched_at=datetime.now(timezone.utc),
        )
        db.add(record)
        db.commit()
        logger.info(f"Stored: ${data['price']:.2f} ({data['change_pct']:+.2f}%)")
        return data
    except Exception as exc:
        db.rollback()
        logger.error(f"DB error: {exc}")
        return None
