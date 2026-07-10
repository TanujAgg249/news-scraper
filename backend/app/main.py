"""
EnergyPulse API — FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, SessionLocal
from app.models import Topic
from app.scraper.sources import DEFAULT_TOPICS
from app.services.scheduler import start_scheduler, stop_scheduler

# --- API Routers ---
from app.api.articles import router as articles_router
from app.api.graph import router as graph_router
from app.api.topics import router as topics_router
from app.api.oil_price import router as oil_price_router


# ---------------------------------------------------------------------------
# Startup helpers
# ---------------------------------------------------------------------------

def _seed_default_topics() -> None:
    """Insert default topics if the topics table is empty."""
    db = SessionLocal()
    try:
        count = db.query(Topic).count()
        if count > 0:
            print(f"[Startup] {count} topics already exist — skipping seed.")
            return

        for t in DEFAULT_TOPICS:
            topic = Topic(
                name=t["name"],
                query=t.get("query"),
                rss_feeds=json.dumps(t.get("rss_feeds", [])),
                keywords=json.dumps(t.get("keywords", [])),
                is_active=True,
            )
            db.add(topic)

        db.commit()
        print(f"[Startup] Seeded {len(DEFAULT_TOPICS)} default topics.")
    except Exception as exc:
        db.rollback()
        print(f"[Startup] Error seeding topics: {exc}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    # --- Startup ---
    print("[Startup] Initializing EnergyPulse API…")
    init_db()
    _seed_default_topics()
    start_scheduler(SessionLocal)
    print("[Startup] Ready.")

    yield

    # --- Shutdown ---
    print("[Shutdown] Stopping scheduler…")
    stop_scheduler()
    print("[Shutdown] Done.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="EnergyPulse API",
    description="Energy market intelligence platform — scrapes, classifies, and visualizes energy news.",
    version="0.1.0",
    lifespan=lifespan,
)

# --- CORS (allow all origins for development) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include routers ---
app.include_router(articles_router)
app.include_router(graph_router)
app.include_router(topics_router)
app.include_router(oil_price_router)


# --- Root health-check ---
@app.get("/", tags=["Health"])
def root():
    return {
        "status": "ok",
        "name": "EnergyPulse API",
        "version": "0.1.0",
    }
