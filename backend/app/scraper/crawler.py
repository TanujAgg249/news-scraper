"""
Web search crawler using Google News RSS and Trafilatura full-text extraction.
"""

import json
import asyncio
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional
from email.utils import parsedate_to_datetime

import trafilatura
from sqlalchemy.orm import Session

from app.models import Article, Topic
from app.analysis.classifier import classify_batch, check_article_relevance
from app.analysis.embeddings import generate_embedding
from app.logger import logger


def _parse_pub_date(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


async def fetch_articles_for_topic(topic: Topic, progress_cb=None) -> list[dict]:
    """
    Fetch articles via Google News RSS search and extract full text using Trafilatura.
    """
    all_articles: list[dict] = []
    seen_urls: set[str] = set()

    if progress_cb:
        progress_cb(f"Preparing to search for '{topic.name}'...")

    if not topic.query:
        return []

    # Map time_filter to Google News 'when:' syntax
    when_suffix = ""
    if topic.time_filter == "d":
        when_suffix = "+when:1d"
    elif topic.time_filter == "w":
        when_suffix = "+when:7d"
    elif topic.time_filter == "m":
        when_suffix = "+when:30d"

    # We do NOT use hardcoded Reuters/Bloomberg generic feeds anymore.
    # We only use Google News RSS for the exact specific query.
    # Also, we explicitly search publisher-scoped Google News for high-quality energy publishers.
    
    search_queries = [topic.query]
    for site in ["reuters.com", "bloomberg.com", "aljazeera.com", "ft.com", "cnbc.com", "wsj.com"]:
        search_queries.append(f"{topic.query} site:{site}")

    logger.info(f"Topic '{topic.name}': searching Google News with {len(search_queries)} query variations")

    for q in search_queries:
        encoded_query = urllib.parse.quote_plus(q + when_suffix)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req, timeout=10)
            root = ET.fromstring(response.read())
            
            for item in root.findall('.//item'):
                link = item.findtext('link')
                if not link or link in seen_urls:
                    continue
                seen_urls.add(link)
                
                title = item.findtext('title')
                pub_date_str = item.findtext('pubDate')
                source = item.findtext('source') or "Unknown"
                
                # Extract Full Text
                full_text = None
                try:
                    downloaded = trafilatura.fetch_url(link)
                    if downloaded:
                        full_text = trafilatura.extract(downloaded)
                except Exception as e:
                    pass
                    
                if not full_text or len(full_text) < 100:
                    # Google News RSS returns some HTML description, we can try to strip it, but it's usually useless.
                    import re, html
                    raw_desc = item.findtext('description') or ""
                    full_text = html.unescape(re.sub(r"<[^>]+>", "", raw_desc)).strip()

                all_articles.append({
                    "headline": (title or "").strip(),
                    "description": full_text,  # We pass full text to the AI instead of a summary!
                    "url": link,
                    "source": source,
                    "published_at": _parse_pub_date(pub_date_str),
                })
                
                if progress_cb:
                    progress_cb(f"Fetched {len(all_articles)}/15 articles...")
                
                # Limit to 15 articles total per topic to ensure fast scraping response
                if len(all_articles) >= 15:
                    break
                    
        except Exception as exc:
            logger.error(f"Error fetching Google News RSS for query '{q}': {exc}")
            
        if len(all_articles) >= 15:
            break

    logger.info(f"Topic '{topic.name}': fetched and extracted {len(all_articles)} full-text articles")
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

            # DATE FILTER: Reject articles older than MAX_ARTICLE_AGE_HOURS
            from app.config import settings
            from datetime import timedelta
            if art.get("published_at"):
                age_cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.MAX_ARTICLE_AGE_HOURS)
                if art["published_at"] < age_cutoff:
                    continue

            # Keyword matching
            matched: list[str] = []
            combined_text = f"{art['headline']} {art.get('description', '') or ''}".lower()
            for kw in kw_list:
                if kw.lower() in combined_text:
                    matched.append(kw)
            matched_str = ", ".join(matched) if matched else None

            # STRICT KEYWORD FILTER: Article must match at least 1 keyword
            if kw_list and not matched:
                continue

            # AI RELEVANCE GATE: Quick yes/no check from gpt-4o-mini
            if not check_article_relevance(art["headline"], art.get("description"), topic.name):
                logger.info(f"AI rejected as irrelevant to '{topic.name}': {art['headline'][:60]}")
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
