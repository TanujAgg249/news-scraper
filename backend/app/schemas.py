"""
Pydantic v2 request / response schemas for the EnergyPulse API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, field_serializer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_utc(v: Optional[datetime]) -> Optional[str]:
    """Ensure naive datetimes are tagged as UTC before serialization.

    The database stores all timestamps in UTC but without timezone info.
    By attaching ``timezone.utc`` we guarantee the ISO string ends with
    ``+00:00`` (or ``Z``-equivalent) so that JavaScript's ``new Date()``
    interprets them correctly regardless of the user's local timezone.
    """
    if v is None:
        return None
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v.isoformat()


# ---------------------------------------------------------------------------
# Articles
# ---------------------------------------------------------------------------

class ArticleResponse(BaseModel):
    id: str
    headline: str
    description: Optional[str] = None
    source: Optional[str] = None
    published_at: Optional[datetime] = None
    url: str
    fetched_at: Optional[datetime] = None
    topic_id: Optional[str] = None
    topic_name: Optional[str] = None
    matched_keywords: Optional[str] = None
    oil_impact: str = "Unknown"
    impact_reason: Optional[str] = None
    impact_confidence: float = 0.0
    importance_score: float = 50.0
    event_type: str = "primary"
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    entities: Optional[List[str]] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_serializer("published_at", "fetched_at", "created_at")
    @classmethod
    def _utc_dt(cls, v: Optional[datetime]) -> Optional[str]:
        return _serialize_utc(v)


class ArticleListResponse(BaseModel):
    articles: List[ArticleResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

class GraphNode(BaseModel):
    id: str
    headline: str
    description: Optional[str] = None
    source: Optional[str] = None
    oil_impact: str = "Unknown"
    impact_reason: Optional[str] = None
    importance_score: float = 50.0
    event_type: str = "primary"
    published_at: Optional[datetime] = None
    url: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    entities: Optional[List[str]] = None

    @field_serializer("published_at")
    @classmethod
    def _utc_dt(cls, v: Optional[datetime]) -> Optional[str]:
        return _serialize_utc(v)


class GraphLink(BaseModel):
    source: str
    target: str
    similarity: float


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    links: List[GraphLink]


# ---------------------------------------------------------------------------
# Topics
# ---------------------------------------------------------------------------

class TopicCreate(BaseModel):
    name: str = Field(..., max_length=200)
    query: Optional[str] = Field(None, max_length=500)
    rss_feeds: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    time_filter: str = Field("d", max_length=10)
    is_active: bool = True


class TopicUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    query: Optional[str] = Field(None, max_length=500)
    rss_feeds: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    time_filter: Optional[str] = Field(None, max_length=10)
    is_active: Optional[bool] = None


class TopicResponse(BaseModel):
    id: str
    name: str
    query: Optional[str] = None
    rss_feeds: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    time_filter: Optional[str] = "d"
    macro_summary: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    article_count: int = 0

    model_config = {"from_attributes": True}

    @field_serializer("created_at")
    @classmethod
    def _utc_dt(cls, v: Optional[datetime]) -> Optional[str]:
        return _serialize_utc(v)


# ---------------------------------------------------------------------------
# Oil Price
# ---------------------------------------------------------------------------

class OilPriceEntry(BaseModel):
    price: float
    change: float = 0.0
    change_pct: float = 0.0
    fetched_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_serializer("fetched_at")
    @classmethod
    def _utc_dt(cls, v: Optional[datetime]) -> Optional[str]:
        return _serialize_utc(v)


class OilPriceResponse(BaseModel):
    latest: Optional[OilPriceEntry] = None
    history: List[OilPriceEntry] = []
