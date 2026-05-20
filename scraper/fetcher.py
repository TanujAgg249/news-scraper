"""
fetcher.py - News Article Fetcher
==================================

This module handles:
1. Building the API request to NewsAPI
2. Sending the HTTP request with error handling
3. Parsing the JSON response into a clean list of dictionaries
4. Tagging articles that match keyword filters
"""

import os
from datetime import datetime, timedelta, timezone

import requests

from scraper.config import NEWSAPI_BASE_URL, PAGE_SIZE, SORT_BY, LANGUAGE, MAX_ARTICLE_AGE_HOURS


def fetch_news(query: str, keyword_filters: list[str] | None = None) -> list[dict] | None:
    """
    Fetch news articles from NewsAPI.

    Args:
        query: The search term (e.g. "Russia Ukraine war")
        keyword_filters: Optional list of keywords to tag articles with

    Returns:
        A list of article dicts, or None if an error occurred.
        Each dict has keys:
            - headline
            - source
            - published_at
            - url
            - fetched_at
            - matched_keywords
    """

    # -----------------------------------------------------------
    # 1. Get the API key from environment variables
    # -----------------------------------------------------------
    api_key = os.getenv("NEWSAPI_KEY")

    if not api_key:
        print("❌ ERROR: NEWSAPI_KEY not found in environment variables.")
        print("   → Make sure your .env file contains:  NEWSAPI_KEY=your_key_here")
        return None

    # -----------------------------------------------------------
    # 2. Build the request parameters
    # -----------------------------------------------------------
    # Note: NewsAPI free tier already returns recent articles only.
    # Old article cleanup is handled by storage.py (MAX_ARTICLE_AGE_HOURS).
    params = {
        "q": query,         # Search query
        "apiKey": api_key,   # Your API key
        "pageSize": PAGE_SIZE,
        "sortBy": SORT_BY,   # Newest articles first
        "language": LANGUAGE,
    }

    # -----------------------------------------------------------
    # 3. Send the HTTP GET request with error handling
    # -----------------------------------------------------------
    try:
        print(f"🌐 Requesting articles for: \"{query}\"")
        response = requests.get(NEWSAPI_BASE_URL, params=params, timeout=30)

        # Raise an exception for HTTP errors (4xx, 5xx)
        response.raise_for_status()

    except requests.exceptions.ConnectionError:
        print("❌ ERROR: No internet connection. Check your network.")
        return None

    except requests.exceptions.Timeout:
        print("❌ ERROR: Request timed out. NewsAPI might be slow.")
        return None

    except requests.exceptions.HTTPError as e:
        print(f"❌ ERROR: HTTP error from NewsAPI: {e}")
        # Print the API error message if available
        try:
            error_body = response.json()
            print(f"   → API says: {error_body.get('message', 'No details')}")
        except Exception:
            pass
        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Unexpected request error: {e}")
        return None

    # -----------------------------------------------------------
    # 4. Parse the JSON response
    # -----------------------------------------------------------
    data = response.json()

    if data.get("status") != "ok":
        print(f"❌ ERROR: API returned status '{data.get('status')}'")
        print(f"   → Message: {data.get('message', 'No details')}")
        return None

    raw_articles = data.get("articles", [])

    if not raw_articles:
        print("ℹ️  API returned 0 articles.")
        return []

    # -----------------------------------------------------------
    # 5. Extract the fields we need and tag with keywords
    # -----------------------------------------------------------
    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cleaned_articles = []

    for article in raw_articles:
        headline = article.get("title", "").strip()
        url = article.get("url", "").strip()

        # Skip articles with missing headline or URL (sometimes happens)
        if not headline or headline == "[Removed]" or not url:
            continue

        # Check which keyword filters match (case-insensitive)
        matched = []
        if keyword_filters:
            text = (headline + " " + (article.get("description") or "")).lower()
            matched = [kw for kw in keyword_filters if kw.lower() in text]

        cleaned_articles.append({
            "headline": headline,
            "description": (article.get("description") or "").strip(),
            "source": article.get("source", {}).get("name", "Unknown"),
            "published_at": article.get("publishedAt", ""),
            "url": url,
            "fetched_at": fetched_at,
            "matched_keywords": ", ".join(matched) if matched else "",
        })

    # Sort by publication time (newest first)
    cleaned_articles.sort(key=lambda x: x["published_at"], reverse=True)

    print(f"📥 Fetched {len(cleaned_articles)} valid articles from NewsAPI.")
    return cleaned_articles
