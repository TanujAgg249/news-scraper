"""
Groq LLM classifier using Llama 3.3 70B for oil market impact analysis.
"""

import json
import time
from typing import Optional

from app.config import settings
from app.logger import logger

# ---------------------------------------------------------------------------
# Groq client (lazy init)
# ---------------------------------------------------------------------------
import json
import time
from typing import Optional
from openai import OpenAI

from app.config import settings
from app.logger import logger

# ---------------------------------------------------------------------------
# OpenAI client (lazy init)
# ---------------------------------------------------------------------------
_openai_client = None

def _get_client():
    global _openai_client
    if _openai_client is None:
        if not settings.OPENAI_API_KEY:
            return None
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client

# ---------------------------------------------------------------------------
# Classification prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are an expert energy market analyst. Given a news headline and the full text of an article, analyze its directional impact on global crude oil prices (e.g. Brent crude) and its geographic relevance.

Respond ONLY with valid JSON in this exact format:
{
  "oil_impact": "Bullish" | "Bearish" | "Neutral" | "Mixed" | "Uncertain",
  "impact_reason": "One concise sentence explaining the causal chain (e.g., event -> supply/demand effect -> expected price direction)",
  "impact_confidence": 0.0 to 1.0,
  "importance_score": 1 to 100,
  "event_type": "primary" | "reaction" | "analysis" | "follow-up",
  "location": "Primary country or city this news is about",
  "latitude": 0.0,
  "longitude": 0.0,
  "entities": ["Company1", "Country2", "Person3"]
}

Definitions:
- oil_impact: "Bullish" = places upward pressure on prices, "Bearish" = places downward pressure on prices.
- impact_confidence: how confident you are in your assessment (0.0 = unsure, 1.0 = very sure)
- importance_score: how significant this news event is globally (1 = trivial, 100 = historic)
- event_type: "primary" = original event, "reaction" = market/political reaction, "analysis" = expert commentary, "follow-up" = update on previous event
- location: the primary geographic location this article is about (country or major city). If unclear, use the most relevant country.
- latitude/longitude: approximate coordinates of the location (use well-known coordinates for countries/cities)
- entities: a list of key entities mentioned (companies, pipelines, organizations, countries, people). Extract AS MANY relevant geopolitical and energy entities as you can find in the text. This is critical for graph linkages."""

def _default_classification() -> dict:
    """Return a default classification when OpenAI is unavailable."""
    return {
        "oil_impact": "Unknown",
        "impact_reason": None,
        "impact_confidence": 0.0,
        "importance_score": 50.0,
        "event_type": "primary",
        "location": None,
        "latitude": None,
        "longitude": None,
        "entities": [],
    }

# ---------------------------------------------------------------------------
# Single-article classification (OpenAI)
# ---------------------------------------------------------------------------

def classify_article(headline: str, description: Optional[str] = None) -> dict:
    client = _get_client()
    if client is None:
        logger.warning("No OPENAI_API_KEY set — using default classification.")
        return _default_classification()

    user_content = f"Headline: {headline}"
    if description:
        user_content += f"\nDescription: {description}"

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_CLASSIFIER_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=300,
            )
            raw = response.choices[0].message.content.strip()
            result = json.loads(raw)

            # Validate and clamp values
            valid_impacts = {"Bullish", "Bearish", "Neutral", "Mixed", "Uncertain"}
            if result.get("oil_impact") not in valid_impacts:
                result["oil_impact"] = "Uncertain"

            result["impact_confidence"] = max(0.0, min(1.0, float(result.get("impact_confidence", 0.5))))
            result["importance_score"] = max(1.0, min(100.0, float(result.get("importance_score", 50))))

            valid_event_types = {"primary", "reaction", "analysis", "follow-up"}
            if result.get("event_type") not in valid_event_types:
                result["event_type"] = "primary"

            if not result.get("impact_reason"):
                result["impact_reason"] = None

            if not result.get("location"):
                result["location"] = None
                
            lat = result.get("latitude")
            lng = result.get("longitude")
            try:
                lat = float(lat) if lat is not None else None
                lng = float(lng) if lng is not None else None
                if lat is not None and (lat < -90 or lat > 90): lat = None
                if lng is not None and (lng < -180 or lng > 180): lng = None
            except (TypeError, ValueError):
                lat = None
                lng = None
            result["latitude"] = lat
            result["longitude"] = lng

            entities = result.get("entities", [])
            if not isinstance(entities, list):
                entities = []
            result["entities"] = [str(e) for e in entities[:5]]

            return result

        except Exception as exc:
            logger.error(f"OpenAI API error (attempt {attempt + 1}): {exc}")
            time.sleep(1)

    logger.error("OpenAI failed. Falling back to default.")
    return _default_classification()

# ---------------------------------------------------------------------------
# Batch classification
# ---------------------------------------------------------------------------

def classify_batch(articles: list[dict]) -> list[dict]:
    """
    Classify a list of article dicts sequentially.
    Adds classification fields in-place and returns the list.
    """
    total = len(articles)
    for idx, art in enumerate(articles, 1):
        headline = art.get("headline", "")
        description = art.get("description")

        logger.info(f"Classifying {idx}/{total}: {headline[:60]}…")
        result = classify_article(headline, description)

        art["oil_impact"] = result["oil_impact"]
        art["impact_reason"] = result["impact_reason"]
        art["impact_confidence"] = result["impact_confidence"]
        art["importance_score"] = result["importance_score"]
        art["event_type"] = result["event_type"]
        art["location"] = result.get("location")
        art["latitude"] = result.get("latitude")
        art["longitude"] = result.get("longitude")
        art["entities"] = result.get("entities", [])

    return articles

# ---------------------------------------------------------------------------
# Macro Summary Generation
# ---------------------------------------------------------------------------

def generate_macro_summary(articles_text: str) -> Optional[str]:
    """
    Generate a 3-bullet macro summary of the topic based on recent articles.
    """
    client = _get_client()
    if client is None:
        return None

    prompt = (
        "You are an expert geopolitical and energy market analyst.\n"
        "Read the following recent news headlines and descriptions for a specific topic, "
        "and generate a concise, 3-bullet 'Macro Narrative Summary' that synthesizes what is currently happening.\n"
        "Focus on the big picture, market movements, and geopolitical shifts.\n\n"
        "Format exactly as 3 markdown bullet points.\n\n"
        f"Articles:\n{articles_text}"
    )

    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_CLASSIFIER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=250,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.error(f"Error generating macro summary: {exc}")
        return None


# ---------------------------------------------------------------------------
# AI Relevance Gate
# ---------------------------------------------------------------------------

def check_article_relevance(headline: str, description: Optional[str], topic_name: str) -> bool:
    """
    Quick AI check: Is this article genuinely relevant to the given topic?
    Returns True if relevant, False if not. Defaults to True on failure
    (so we never accidentally lose good articles).
    """
    client = _get_client()
    if client is None:
        return True  # fail-open: accept if AI is unavailable

    article_text = headline
    if description:
        article_text += f" — {description}"

    prompt = (
        f"Topic: \"{topic_name}\"\n"
        f"Article: \"{article_text}\"\n\n"
        "Is this article DIRECTLY and specifically relevant to the topic above? "
        "Answer only YES or NO. Nothing else."
    )

    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_CLASSIFIER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=3,
        )
        answer = response.choices[0].message.content.strip().upper()
        return answer.startswith("YES")
    except Exception as exc:
        logger.error(f"Relevance check failed: {exc}")
        return True  # fail-open: accept on error

