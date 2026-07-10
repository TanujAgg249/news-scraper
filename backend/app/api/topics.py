"""
API router: Topics — CRUD endpoints for managing news topics.
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Topic, Article
from app.schemas import TopicCreate, TopicUpdate, TopicResponse

router = APIRouter(prefix="/api/topics", tags=["Topics"])


def _topic_to_response(topic: Topic, article_count: int = 0) -> TopicResponse:
    """Convert a Topic ORM instance to a TopicResponse schema."""
    rss_feeds = None
    if topic.rss_feeds:
        try:
            rss_feeds = json.loads(topic.rss_feeds)
        except (json.JSONDecodeError, TypeError):
            rss_feeds = []

    keywords = None
    if topic.keywords:
        try:
            keywords = json.loads(topic.keywords)
        except (json.JSONDecodeError, TypeError):
            keywords = []

    return TopicResponse(
        id=topic.id,
        name=topic.name,
        query=topic.query,
        rss_feeds=rss_feeds,
        keywords=keywords,
        macro_summary=topic.macro_summary,
        is_active=topic.is_active,
        created_at=topic.created_at,
        article_count=article_count,
    )


@router.get("", response_model=list[TopicResponse])
def list_topics(db: Session = Depends(get_db)):
    """List all topics with article counts."""
    # Sub-query for article count per topic
    count_subq = (
        db.query(
            Article.topic_id,
            func.count(Article.id).label("cnt"),
        )
        .group_by(Article.topic_id)
        .subquery()
    )

    results = (
        db.query(Topic, func.coalesce(count_subq.c.cnt, 0))
        .outerjoin(count_subq, Topic.id == count_subq.c.topic_id)
        .order_by(Topic.name)
        .all()
    )

    return [_topic_to_response(topic, count) for topic, count in results]


@router.post("", response_model=TopicResponse, status_code=201)
def create_topic(payload: TopicCreate, db: Session = Depends(get_db)):
    """Create a new topic."""
    # Check for duplicate name
    existing = db.query(Topic).filter(Topic.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Topic '{payload.name}' already exists")

    topic = Topic(
        name=payload.name,
        query=payload.query,
        rss_feeds=json.dumps(payload.rss_feeds) if payload.rss_feeds else None,
        keywords=json.dumps(payload.keywords) if payload.keywords else None,
        is_active=payload.is_active,
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    print(f"[Topics] Created: {topic.name}")
    return _topic_to_response(topic, 0)


@router.put("/{topic_id}", response_model=TopicResponse)
def update_topic(topic_id: str, payload: TopicUpdate, db: Session = Depends(get_db)):
    """Update an existing topic."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    if payload.name is not None:
        # Check uniqueness if name is changing
        if payload.name != topic.name:
            dup = db.query(Topic).filter(Topic.name == payload.name).first()
            if dup:
                raise HTTPException(status_code=409, detail=f"Topic '{payload.name}' already exists")
        topic.name = payload.name

    if payload.query is not None:
        topic.query = payload.query

    if payload.rss_feeds is not None:
        topic.rss_feeds = json.dumps(payload.rss_feeds)

    if payload.keywords is not None:
        topic.keywords = json.dumps(payload.keywords)

    if payload.is_active is not None:
        topic.is_active = payload.is_active

    db.commit()
    db.refresh(topic)

    article_count = db.query(func.count(Article.id)).filter(Article.topic_id == topic_id).scalar() or 0
    print(f"[Topics] Updated: {topic.name}")
    return _topic_to_response(topic, article_count)


@router.delete("/{topic_id}", status_code=204)
def delete_topic(topic_id: str, db: Session = Depends(get_db)):
    """Delete a topic and its associated articles."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    name = topic.name
    db.delete(topic)
    db.commit()
    print(f"[Topics] Deleted: {name}")
    return None


@router.post("/{topic_id}/scrape")
def scrape_topic(topic_id: str, db: Session = Depends(get_db)):
    """Manually trigger a scrape for a specific topic."""
    import asyncio
    from app.scraper.crawler import fetch_articles_for_topic
    from app.analysis.classifier import classify_batch
    from app.analysis.embeddings import generate_embedding
    from datetime import datetime, timezone

    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    print(f"[Topics] Manual scrape triggered for: {topic.name}")

    # Fetch articles
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        fetched = loop.run_until_complete(fetch_articles_for_topic(topic))
    finally:
        loop.close()

    # Filter out existing URLs
    new_articles = []
    from app.models import Article
    for art in fetched:
        existing = db.query(Article.id).filter(Article.url == art["url"]).first()
        if not existing:
            art["topic_id"] = topic.id
            # Keyword matching
            kw_list = []
            if topic.keywords:
                try:
                    kw_list = json.loads(topic.keywords)
                except (json.JSONDecodeError, TypeError):
                    kw_list = []
            matched = []
            combined_text = f"{art['headline']} {art.get('description', '') or ''}".lower()
            for kw in kw_list:
                if kw.lower() in combined_text:
                    matched.append(kw)
            art["matched_keywords"] = ", ".join(matched) if matched else None
            new_articles.append(art)
            if len(new_articles) >= 15:
                break

    if not new_articles:
        return {"message": "No new articles found", "new_articles": 0}

    # Classify
    classified = classify_batch(new_articles)

    # Embed & Save
    saved_count = 0
    for art in classified:
        try:
            embed_text = f"{art['headline']}. {art.get('description') or ''}"
            embedding_bytes = generate_embedding(embed_text)
            article = Article(
                headline=art["headline"],
                description=art.get("description"),
                source=art.get("source"),
                published_at=art.get("published_at"),
                url=art["url"],
                topic_id=art.get("topic_id"),
                matched_keywords=art.get("matched_keywords"),
                oil_impact=art.get("oil_impact", "Unknown"),
                impact_reason=art.get("impact_reason"),
                impact_confidence=art.get("impact_confidence", 0.0),
                importance_score=art.get("importance_score", 50.0),
                event_type=art.get("event_type", "primary"),
                location=art.get("location"),
                latitude=art.get("latitude"),
                longitude=art.get("longitude"),
                entities=json.dumps(art.get("entities", [])),
                embedding=embedding_bytes,
            )
            db.add(article)
            db.commit()
            saved_count += 1
        except Exception as exc:
            db.rollback()
            print(f"[Topics] Error saving article: {exc}")

    # --- Generate Macro Summary ---
    from app.analysis.classifier import generate_macro_summary
    top_articles = db.query(Article).filter(Article.topic_id == topic.id).order_by(Article.published_at.desc().nullslast()).limit(20).all()
    if top_articles:
        articles_text = "\n\n".join(
            f"Headline: {a.headline}\nDescription: {a.description or ''}" 
            for a in top_articles
        )
        summary = generate_macro_summary(articles_text)
        if summary:
            topic.macro_summary = summary
            db.commit()
            print(f"[Topics] Generated macro summary for topic: {topic.name}")

    print(f"[Topics] Manual scrape for '{topic.name}' complete. Saved {saved_count} articles.")
    return {"message": f"Scraping complete for {topic.name}", "new_articles": saved_count}
