"""
oil_price.py - Live Brent Crude Oil Price Fetcher
===================================================

Fetches the current Brent Crude oil price from Yahoo Finance
using the yfinance library.
"""

import yfinance as yf


def get_brent_crude_price() -> dict:
    """
    Fetch the current Brent Crude oil price.

    Returns:
        A dict with:
            - price: Current price in USD (float)
            - change: Price change from previous close (float)
            - change_pct: Percentage change (float)
            - currency: "USD"
            - timestamp: When this price was fetched (str)
        Returns None if fetching fails.
    """
    try:
        ticker = yf.Ticker("BZ=F")  # Brent Crude Futures
        info = ticker.fast_info

        price = info.get("lastPrice", 0)
        prev_close = info.get("previousClose", 0)

        if price and prev_close:
            change = price - prev_close
            change_pct = (change / prev_close) * 100
        else:
            change = 0
            change_pct = 0

        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"🛢️  Brent Crude: ${price:.2f} ({change:+.2f}, {change_pct:+.2f}%)")

        return {
            "price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "currency": "USD",
            "timestamp": timestamp,
        }

    except Exception as e:
        print(f"⚠️  Could not fetch Brent Crude price: {e}")
        return None
