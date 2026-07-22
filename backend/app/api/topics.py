"""
API router: Topics — CRUD endpoints for managing news topics.
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Topic, Article, ArticleTopic
from app.schemas import TopicCreate, TopicUpdate, TopicResponse
from app.logger import logger

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
        time_filter=topic.time_filter,
        macro_summary=topic.macro_summary,
        is_active=topic.is_active,
        created_at=topic.created_at,
        article_count=article_count,
    )


@router.get("", response_model=list[TopicResponse])
def list_topics(db: Session = Depends(get_db)):
    """List all topics with article counts."""
    from app.models import ArticleTopic
    # Sub-query for article count per topic via the association table
    count_subq = (
        db.query(
            ArticleTopic.topic_id,
            func.count(ArticleTopic.article_id).label("cnt"),
        )
        .group_by(ArticleTopic.topic_id)
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
        time_filter=payload.time_filter,
        is_active=payload.is_active,
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    logger.info(f"Created: {topic.name}")
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

    if payload.time_filter is not None:
        topic.time_filter = payload.time_filter

    if payload.is_active is not None:
        topic.is_active = payload.is_active

    db.commit()
    db.refresh(topic)

    article_count = db.query(func.count(ArticleTopic.article_id)).filter(ArticleTopic.topic_id == topic_id).scalar() or 0
    logger.info(f"Updated: {topic.name}")
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
    logger.info(f"Deleted: {name}")
    return None


def _run_background_scrape(topic_id: str):
    """Background task to run the scrape cycle without blocking the HTTP response."""
    from app.database import SessionLocal
    import asyncio
    from app.scraper.crawler import fetch_articles_for_topic
    from app.analysis.classifier import classify_batch
    from app.analysis.embeddings import generate_embedding
    
    db = SessionLocal()
    try:
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            return

        logger.info(f"Background manual scrape started for: {topic.name}")

        # Fetch articles
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            fetched = loop.run_until_complete(fetch_articles_for_topic(topic))
        finally:
            loop.close()

        new_articles = []
        for art in fetched:
            existing = db.query(Article).filter(Article.url == art["url"]).first()
            
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
            matched_str = ", ".join(matched) if matched else None
                    
            if existing:
                assoc_exists = db.query(ArticleTopic).filter(
                    ArticleTopic.article_id == existing.id,
                    ArticleTopic.topic_id == topic.id
                ).first()
                if not assoc_exists:
                    new_assoc = ArticleTopic(
                        article_id=existing.id,
                        topic_id=topic.id,
                        matched_keywords=matched_str
                    )
                    db.add(new_assoc)
                    db.commit()
                continue
                
            art["matched_keywords"] = matched_str
            new_articles.append(art)
            if len(new_articles) >= 15:
                break

        if not new_articles:
            logger.info(f"No new articles found for {topic.name}")
            return

        classified = classify_batch(new_articles)

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
                db.flush()
                
                assoc = ArticleTopic(
                    article_id=article.id,
                    topic_id=topic.id,
                    matched_keywords=art.get("matched_keywords")
                )
                db.add(assoc)
                
                db.commit()
                saved_count += 1
            except Exception as exc:
                db.rollback()
                logger.error(f"Error saving article in bg task: {exc}")

        # Macro Summary
        from app.analysis.classifier import generate_macro_summary
        top_articles = db.query(Article).join(ArticleTopic).filter(ArticleTopic.topic_id == topic.id).order_by(Article.published_at.desc().nullslast()).limit(20).all()
        if top_articles:
            articles_text = "\n\n".join(
                f"Headline: {a.headline}\nDescription: {a.description or ''}" 
                for a in top_articles
            )
            summary = generate_macro_summary(articles_text)
            if summary:
                topic.macro_summary = summary
                db.commit()

        logger.info(f"Background scrape for '{topic.name}' complete. Saved {saved_count} articles.")

    except Exception as exc:
        logger.error(f"Background scrape failed: {exc}")
    finally:
        db.close()

@router.post("/{topic_id}/scrape", status_code=202)
def scrape_topic(topic_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Manually trigger a scrape for a specific topic (runs in background)."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    background_tasks.add_task(_run_background_scrape, topic.id)
    return {"message": "Scrape initiated in the background. Articles will appear shortly."}
