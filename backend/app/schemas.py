"""
Pydantic v2 request / response schemas for the EnergyPulse API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


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
    is_active: bool = True


class TopicUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    query: Optional[str] = Field(None, max_length=500)
    rss_feeds: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    is_active: Optional[bool] = None


class TopicResponse(BaseModel):
    id: str
    name: str
    query: Optional[str] = None
    rss_feeds: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    macro_summary: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    article_count: int = 0

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Oil Price
# ---------------------------------------------------------------------------

class OilPriceEntry(BaseModel):
    price: float
    change: float = 0.0
    change_pct: float = 0.0
    fetched_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OilPriceResponse(BaseModel):
    latest: Optional[OilPriceEntry] = None
    history: List[OilPriceEntry] = []
