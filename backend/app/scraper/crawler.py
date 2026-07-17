"""
RSS-based news crawler using feedparser.
Fetches articles from Google News RSS and custom RSS feeds per topic.
"""

import json
import asyncio
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote_plus
import html

import feedparser
from sqlalchemy.orm import Session

from app.models import Article, Topic
from app.scraper.sources import DEFAULT_RSS_FEEDS
from app.analysis.classifier import classify_batch
from app.analysis.embeddings import generate_embedding
from app.logger import logger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_published(entry: dict) -> Optional[datetime]:
    """Extract a datetime from a feedparser entry's published_parsed."""
    pp = entry.get("published_parsed")
    if pp:
        try:
            from email.utils import parsedate_to_datetime
            from time import mktime
            # feedparser time_struct can be converted to aware datetime
            dt = datetime.fromtimestamp(mktime(pp)).astimezone(timezone.utc)
            return dt
        except Exception:
            pass
    # Fallback: try dateutil on the raw string
    raw = entry.get("published") or entry.get("updated")
    if raw:
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(raw).replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def _extract_source(entry: dict) -> str:
    """Try to pull the source name from the entry."""
    # Google News puts source in <source> tag
    source_info = entry.get("source", {})
    if isinstance(source_info, dict) and source_info.get("title"):
        return source_info["title"]
    # Fallback: use feed title or empty
    return entry.get("author", "Unknown")


def _clean_html(text: Optional[str]) -> Optional[str]:
    """Strip very basic HTML tags from description."""
    if not text:
        return None
    import re
    clean = re.sub(r"<[^>]+>", "", text)
    clean = html.unescape(clean)
    clean = clean.strip()
    return clean if clean else None


def _build_google_news_url(query: str) -> str:
    """Build a Google News RSS search URL."""
    encoded = quote_plus(query)
    return f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"


# ---------------------------------------------------------------------------
# Core fetching
# ---------------------------------------------------------------------------

def _fetch_feed(url: str) -> list[dict]:
    """Parse a single RSS feed and return a list of raw article dicts."""
    articles: list[dict] = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                continue
            articles.append({
                "headline": title,
                "description": _clean_html(entry.get("summary") or entry.get("description")),
                "url": link,
                "source": _extract_source(entry),
                "published_at": _parse_published(entry),
            })
    except Exception as exc:
        logger.error(f"Error fetching {url}: {exc}")
    return articles


async def fetch_articles_for_topic(topic: Topic) -> list[dict]:
    """
    Fetch articles from Google News RSS (using topic.query) and any custom
    RSS feeds attached to the topic. Returns deduplicated list of article dicts.
    """
    all_articles: list[dict] = []
    seen_urls: set[str] = set()

    # 1. Google News RSS from query
    if topic.query:
        gn_url = _build_google_news_url(topic.query)
        for art in _fetch_feed(gn_url):
            if art["url"] not in seen_urls:
                seen_urls.add(art["url"])
                all_articles.append(art)

    # 2. Custom RSS feeds for this topic
    custom_feeds: list[str] = []
    if topic.rss_feeds:
        try:
            custom_feeds = json.loads(topic.rss_feeds)
        except (json.JSONDecodeError, TypeError):
            custom_feeds = []

    # 3. Also add the default static feeds
    custom_feeds.extend(DEFAULT_RSS_FEEDS)

    for feed_url in custom_feeds:
        for art in _fetch_feed(feed_url):
            if art["url"] not in seen_urls:
                seen_urls.add(art["url"])
                all_articles.append(art)

    logger.info(f"Topic '{topic.name}': fetched {len(all_articles)} articles")
    return all_articles


# ---------------------------------------------------------------------------
# Full scraping cycle
# ---------------------------------------------------------------------------

def _get_existing_article(db: Session, url: str) -> Optional[Article]:
    """Get an existing article by URL."""
    return db.query(Article).filter(Article.url == url).first()


async def run_scraping_cycle(db: Session) -> int:
    """
    Orchestrate a full scraping cycle:
      1. For each active topic → fetch articles via RSS
      2. Deduplicate and take at most 15 most recent new articles
      3. Classify each new article (Groq LLM)
      4. Generate embeddings
      5. Persist to database progressively
    Returns the number of new articles saved.
    """
    logger.info("Starting scraping cycle…")
    
    # Clean up articles older than MAX_ARTICLE_AGE_HOURS
    from app.config import settings
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.MAX_ARTICLE_AGE_HOURS)
    old_count = db.query(Article).filter(Article.created_at < cutoff).delete()
    if old_count:
        db.commit()
        logger.info(f"Cleaned up {old_count} articles older than {settings.MAX_ARTICLE_AGE_HOURS}h.")

    topics = db.query(Topic).filter(Topic.is_active == True).all()  # noqa: E712
    if not topics:
        logger.info("No active topics found. Skipping.")
        return 0

    new_articles_raw: list[dict] = []
    # url -> list of {topic_id, matched_keywords}
    url_to_topics: dict[str, list[dict]] = {}

    from app.models import ArticleTopic

    for topic in topics:
        fetched = await fetch_articles_for_topic(topic)
        
        fetched.sort(
            key=lambda x: x.get("published_at") or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True
        )

        kw_list: list[str] = []
        if topic.keywords:
            try:
                kw_list = json.loads(topic.keywords)
            except (json.JSONDecodeError, TypeError):
                kw_list = []

        topic_new_count = 0
        for art in fetched:
            if topic_new_count >= 15:
                break

            url = art["url"]

            # Keyword matching
            matched: list[str] = []
            combined_text = f"{art['headline']} {art.get('description', '') or ''}".lower()
            for kw in kw_list:
                if kw.lower() in combined_text:
                    matched.append(kw)
            matched_str = ", ".join(matched) if matched else None

            # STRICT KEYWORD FILTER: Prevent generic news from contaminating topics
            if kw_list and not matched:
                continue

            existing_article = _get_existing_article(db, url)
            if existing_article:
                # Add topic association if it doesn't exist
                assoc_exists = db.query(ArticleTopic).filter(
                    ArticleTopic.article_id == existing_article.id,
                    ArticleTopic.topic_id == topic.id
                ).first()
                if not assoc_exists:
                    new_assoc = ArticleTopic(
                        article_id=existing_article.id,
                        topic_id=topic.id,
                        matched_keywords=matched_str
                    )
                    db.add(new_assoc)
                    db.commit()
                    logger.info(f"Appended topic '{topic.name}' to existing article '{existing_article.headline[:30]}'")
                continue

            if url not in url_to_topics:
                url_to_topics[url] = []
                new_articles_raw.append(art)
                topic_new_count += 1
            
            # Record that this new article belongs to this topic
            url_to_topics[url].append({
                "topic_id": topic.id,
                "matched_keywords": matched_str
            })

    if not new_articles_raw:
        logger.info("No new articles found.")
        return 0

    logger.info(f"{len(new_articles_raw)} new articles to process.")

    # --- Classify ---
    classified = classify_batch(new_articles_raw)

    # --- Embed & Save Progressively ---
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
            db.flush() # get article.id

            # Add multiple topic associations
            for t_info in url_to_topics.get(art["url"], []):
                assoc = ArticleTopic(
                    article_id=article.id,
                    topic_id=t_info["topic_id"],
                    matched_keywords=t_info["matched_keywords"]
                )
                db.add(assoc)

            db.commit()
            saved_count += 1
        except Exception as exc:
            db.rollback()
            logger.error(f"Error saving article '{art.get('headline', '?')[:50]}': {exc}")

    # --- Generate Macro Summaries for topics that had new articles ---
    topics_to_summarize = set()
    for t_infos in url_to_topics.values():
        for t_info in t_infos:
            topics_to_summarize.add(t_info["topic_id"])
            
    from app.analysis.classifier import generate_macro_summary
    from app.models import ArticleTopic
    for t_id in topics_to_summarize:
        top_articles = db.query(Article).join(ArticleTopic).filter(ArticleTopic.topic_id == t_id).order_by(Article.published_at.desc().nullslast()).limit(20).all()
        if not top_articles:
            continue
            
        articles_text = "\n\n".join(
            f"Headline: {a.headline}\nDescription: {a.description or ''}" 
            for a in top_articles
        )
        
        summary = generate_macro_summary(articles_text)
        if summary:
            topic = db.query(Topic).filter(Topic.id == t_id).first()
            if topic:
                topic.macro_summary = summary
                db.commit()
                logger.info(f"Generated macro summary for topic: {topic.name}")

    logger.info(f"Scraping cycle finished. Saved {saved_count} articles.")
    return saved_count
