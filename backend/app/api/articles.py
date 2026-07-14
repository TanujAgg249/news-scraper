"""
API router: Articles — list and detail endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from app.database import get_db
from app.models import Article, Topic, ArticleTopic
from app.schemas import ArticleResponse, ArticleListResponse

router = APIRouter(prefix="/api/articles", tags=["Articles"])


def _article_to_response(article: Article) -> ArticleResponse:
    """Convert an Article ORM instance to an ArticleResponse schema."""
    import json
    entities_list = []
    if article.entities:
        try:
            entities_list = json.loads(article.entities)
        except Exception:
            pass
            
    # For backward compatibility with frontend, pick the first topic
    first_topic = article.topics[0] if article.topics else None
    
    # Try to find matched_keywords from the association if possible, or just skip it
    # We'll just leave it None for now since we removed it from Article
    matched_kw = None

    return ArticleResponse(
        id=article.id,
        headline=article.headline,
        description=article.description,
        source=article.source,
        published_at=article.published_at,
        url=article.url,
        fetched_at=article.fetched_at,
        topic_id=first_topic.id if first_topic else None,
        topic_name=first_topic.name if first_topic else None,
        matched_keywords=matched_kw,
        oil_impact=article.oil_impact or "Unknown",
        impact_reason=article.impact_reason,
        impact_confidence=article.impact_confidence or 0.0,
        importance_score=article.importance_score or 50.0,
        event_type=article.event_type or "primary",
        location=article.location,
        latitude=article.latitude,
        longitude=article.longitude,
        entities=entities_list,
        created_at=article.created_at,
    )


@router.get("", response_model=ArticleListResponse)
def list_articles(
    topic_id: Optional[str] = Query(None, description="Filter by topic UUID"),
    oil_impact: Optional[str] = Query(None, description="Filter by oil impact: Bullish, Bearish, Neutral, Unknown"),
    search: Optional[str] = Query(None, description="Search headline (case-insensitive contains)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("published_at", description="Sort field: published_at, importance_score, created_at"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    db: Session = Depends(get_db),
):
    """List articles with optional filters and pagination."""
    query = db.query(Article)

    # --- Filters ---
    if topic_id:
        query = query.join(ArticleTopic).filter(ArticleTopic.topic_id == topic_id)
    if oil_impact:
        query = query.filter(Article.oil_impact == oil_impact)
    if search:
        query = query.filter(Article.headline.ilike(f"%{search}%"))

    # --- Count ---
    total = query.count()

    # --- Sorting ---
    sort_column_map = {
        "published_at": Article.published_at,
        "importance_score": Article.importance_score,
        "created_at": Article.created_at,
        "fetched_at": Article.fetched_at,
    }
    sort_col = sort_column_map.get(sort_by, Article.published_at)
    order_fn = desc if sort_order.lower() == "desc" else asc
    query = query.order_by(order_fn(sort_col))

    # --- Pagination ---
    articles = query.offset(offset).limit(limit).all()

    return ArticleListResponse(
        articles=[_article_to_response(a) for a in articles],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{article_id}", response_model=ArticleResponse)
def get_article(article_id: str, db: Session = Depends(get_db)):
    """Get a single article by ID."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return _article_to_response(article)


from pydantic import BaseModel as PydanticBaseModel

class ReclassifyPayload(PydanticBaseModel):
    oil_impact: str


@router.patch("/{article_id}/classify", response_model=ArticleResponse)
def reclassify_article(article_id: str, payload: ReclassifyPayload, db: Session = Depends(get_db)):
    """Manually reclassify an article's oil impact without calling AI."""
    valid_impacts = {"Bullish", "Bearish", "Neutral", "Mixed", "Uncertain"}
    if payload.oil_impact not in valid_impacts:
        raise HTTPException(status_code=422, detail=f"Invalid oil_impact. Must be one of: {', '.join(valid_impacts)}")

    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    article.oil_impact = payload.oil_impact
    article.impact_confidence = 1.0  # Manual = 100% confidence
    db.commit()
    db.refresh(article)

    print(f"[Articles] Manually reclassified '{article.headline[:40]}' → {payload.oil_impact}")
    return _article_to_response(article)
