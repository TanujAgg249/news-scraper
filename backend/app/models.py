"""
SQLAlchemy ORM models for EnergyPulse.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    Boolean,
    Integer,
    DateTime,
    LargeBinary,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class ArticleTopic(Base):
    __tablename__ = "article_topics"

    article_id = Column(String(36), ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True)
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True)
    matched_keywords = Column(String(500), nullable=True)
    relevance_score = Column(Float, default=1.0)
    created_at = Column(DateTime, default=_utcnow)


class Article(Base):
    __tablename__ = "articles"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    headline = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    source = Column(String(200), nullable=True)
    published_at = Column(DateTime, nullable=True)
    url = Column(String(1000), unique=True, nullable=False)
    fetched_at = Column(DateTime, default=_utcnow)

    # Classification
    oil_impact = Column(String(20), default="Unknown")  # Bullish / Bearish / Neutral / Mixed / Uncertain
    impact_reason = Column(Text, nullable=True)
    impact_confidence = Column(Float, default=0.0)
    importance_score = Column(Float, default=50.0)
    event_type = Column(String(20), default="primary")  # primary / reaction / analysis / follow-up

    # Embedding (pickled numpy array)
    embedding = Column(LargeBinary, nullable=True)

    # Geo-location (extracted by classifier)
    location = Column(String(200), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Entity extraction
    entities = Column(Text, nullable=True)  # JSON string: ["Entity1", "Entity2"]

    created_at = Column(DateTime, default=_utcnow)

    # Relationships
    topics = relationship("Topic", secondary="article_topics", back_populates="articles")

    def __repr__(self) -> str:
        return f"<Article {self.id[:8]}… {self.headline[:40]}>"


class Topic(Base):
    __tablename__ = "topics"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    name = Column(String(200), unique=True, nullable=False)
    query = Column(String(500), nullable=True)
    rss_feeds = Column(Text, nullable=True)   # JSON string: ["url1","url2"]
    keywords = Column(Text, nullable=True)    # JSON string: ["kw1","kw2"]
    macro_summary = Column(Text, nullable=True) # AI-generated 3-bullet summary
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)

    # Relationships
    articles = relationship("Article", secondary="article_topics", back_populates="topics")

    def __repr__(self) -> str:
        return f"<Topic {self.name}>"


class OilPrice(Base):
    __tablename__ = "oil_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    price = Column(Float, nullable=False)
    change = Column(Float, default=0.0)
    change_pct = Column(Float, default=0.0)
    fetched_at = Column(DateTime, default=_utcnow)

    def __repr__(self) -> str:
        return f"<OilPrice ${self.price:.2f}>"
