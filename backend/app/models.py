"""
SQLAlchemy ORM models for EnergyPulse.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Any

from sqlalchemy import (
    String,
    Text,
    Float,
    Boolean,
    Integer,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class ArticleTopic(Base):
    __tablename__ = "article_topics"

    article_id: Mapped[str] = mapped_column(String(36), ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True)
    topic_id: Mapped[str] = mapped_column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True)
    matched_keywords: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    headline: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    url: Mapped[str] = mapped_column(String(1000), unique=True, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    # Classification
    oil_impact: Mapped[str] = mapped_column(String(20), default="Unknown")  # Bullish / Bearish / Neutral / Mixed / Uncertain
    impact_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    impact_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    importance_score: Mapped[float] = mapped_column(Float, default=50.0)
    event_type: Mapped[str] = mapped_column(String(20), default="primary")  # primary / reaction / analysis / follow-up

    # Embedding (OpenAI text-embedding-3-small is 1536 dims)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector(1536), nullable=True)

    # Geo-location (extracted by classifier)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Entity extraction
    entities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string: ["Entity1", "Entity2"]

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    # Relationships
    topics: Mapped[List["Topic"]] = relationship("Topic", secondary="article_topics", back_populates="articles")

    def __repr__(self) -> str:
        return f"<Article {self.id[:8]}… {self.headline[:40]}>"


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    query: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    rss_feeds: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # JSON string: ["url1","url2"]
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)    # JSON string: ["kw1","kw2"]
    time_filter: Mapped[str] = mapped_column(String(10), default="d") # 'd' (day), 'w' (week), 'm' (month)
    macro_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # AI-generated 3-bullet summary
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    # Relationships
    articles: Mapped[List["Article"]] = relationship("Article", secondary="article_topics", back_populates="topics")

    def __repr__(self) -> str:
        return f"<Topic {self.name}>"


class OilPrice(Base):
    __tablename__ = "oil_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    change: Mapped[float] = mapped_column(Float, default=0.0)
    change_pct: Mapped[float] = mapped_column(Float, default=0.0)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    def __repr__(self) -> str:
        return f"<OilPrice ${self.price:.2f}>"
