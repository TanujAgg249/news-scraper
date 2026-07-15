"""
APScheduler-based background job management for periodic scraping and oil price fetching.
"""

import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.logger import logger

# ---------------------------------------------------------------------------
# Module-level scheduler instance
# ---------------------------------------------------------------------------
_scheduler: BackgroundScheduler | None = None


def _run_scraping_job(session_factory: sessionmaker) -> None:
    """Job wrapper: run the async scraping cycle in a new event loop."""
    from app.scraper.crawler import run_scraping_cycle

    db = session_factory()
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_scraping_cycle(db))
        finally:
            loop.close()
    except Exception as exc:
        logger.error(f"Scraping job error: {exc}")
    finally:
        db.close()


def _run_oil_price_job(session_factory: sessionmaker) -> None:
    """Job wrapper: fetch and store oil price."""
    from app.services.oil_price import fetch_and_store_oil_price

    db = session_factory()
    try:
        fetch_and_store_oil_price(db)
    except Exception as exc:
        logger.error(f"Oil price job error: {exc}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_scheduler(session_factory: sessionmaker) -> None:
    """Start the background scheduler with all recurring jobs."""
    global _scheduler

    if _scheduler is not None:
        logger.info("Already running.")
        return

    _scheduler = BackgroundScheduler(daemon=True)

    # --- Scraping job (run immediately, then repeat) ---
    from datetime import datetime as _dt
    _scheduler.add_job(
        _run_scraping_job,
        trigger="interval",
        minutes=settings.FETCH_INTERVAL_MINUTES,
        args=[session_factory],
        id="scraping_cycle",
        name="News Scraping Cycle",
        replace_existing=True,
        max_instances=1,
        next_run_time=_dt.now(),
    )

    # --- Oil price job (run immediately, then repeat) ---
    _scheduler.add_job(
        _run_oil_price_job,
        trigger="interval",
        minutes=5,
        args=[session_factory],
        id="oil_price_fetch",
        name="Oil Price Fetch",
        replace_existing=True,
        max_instances=1,
        next_run_time=_dt.now(),
    )

    _scheduler.start()
    print(
        f"[Scheduler] Started. "
        f"Scraping every {settings.FETCH_INTERVAL_MINUTES}min, "
        f"oil price every 5min."
    )


def stop_scheduler() -> None:
    """Shut down the background scheduler gracefully."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Stopped.")
