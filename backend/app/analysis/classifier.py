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
_groq_client = None
_groq_temporarily_disabled = False


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        if not settings.GROQ_API_KEY:
            return None
        from groq import Groq
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
    return _groq_client

_gemini_client = None
def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        if not settings.GEMINI_API_KEY:
            return None
        from google import genai
        _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _gemini_client


# ---------------------------------------------------------------------------
# Classification prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are an expert energy market analyst. Given a news headline and description, analyze its directional impact on global crude oil prices (e.g. Brent crude) and its geographic relevance.

Respond ONLY with valid JSON (no markdown, no extra text) in this exact format:
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
- oil_impact: "Bullish" = places upward pressure on prices, "Bearish" = places downward pressure on prices. Consider causal chains: e.g. negative geopolitical news often risks supply, making it Bullish.
- impact_confidence: how confident you are in your assessment (0.0 = unsure, 1.0 = very sure)
- importance_score: how significant this news event is globally (1 = trivial, 100 = historic)
- event_type: "primary" = original event, "reaction" = market/political reaction, "analysis" = expert commentary, "follow-up" = update on previous event
- location: the primary geographic location this article is about (country or major city). If unclear, use the most relevant country.
- latitude/longitude: approximate coordinates of the location (use well-known coordinates for countries/cities)
- entities: a list of key entities mentioned (companies, organizations, countries, people). Maximum 5 entities."""


def _default_classification() -> dict:
    """Return a default classification when Groq is unavailable."""
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
# Single-article classification (Groq)
# ---------------------------------------------------------------------------

def classify_article(headline: str, description: Optional[str] = None) -> dict:
    """
    Classify a single article using Groq LLM.
    Returns a dict with oil_impact, impact_reason, impact_confidence,
    importance_score, and event_type.

    Retries up to 3 times on rate-limit errors with exponential backoff.
    """
    global _groq_temporarily_disabled
    if _groq_temporarily_disabled:
        return classify_article_gemini(headline, description)

    client = _get_groq_client()
    if client is None:
        logger.info("No GROQ_API_KEY set — trying Gemini.")
        return classify_article_gemini(headline, description)

    user_content = f"Headline: {headline}"
    if description:
        user_content += f"\nDescription: {description}"

    last_error: Optional[Exception] = None

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.1,
                max_tokens=300,
            )
            raw = response.choices[0].message.content.strip()

            # Strip markdown code fences if present
            if raw.startswith("```"):
                lines = raw.split("\n")
                # Remove first and last lines (```json and ```)
                lines = [l for l in lines if not l.strip().startswith("```")]
                raw = "\n".join(lines)

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

            # Validate location fields
            if not result.get("location"):
                result["location"] = None
            lat = result.get("latitude")
            lng = result.get("longitude")
            try:
                lat = float(lat) if lat is not None else None
                lng = float(lng) if lng is not None else None
                if lat is not None and (lat < -90 or lat > 90):
                    lat = None
                if lng is not None and (lng < -180 or lng > 180):
                    lng = None
            except (TypeError, ValueError):
                lat = None
                lng = None
            result["latitude"] = lat
            result["longitude"] = lng

            # Validate entities
            entities = result.get("entities", [])
            if not isinstance(entities, list):
                entities = []
            result["entities"] = [str(e) for e in entities[:5]]

            return result

        except json.JSONDecodeError as exc:
            logger.error(f"JSON parse error (attempt {attempt + 1}): {exc}")
            last_error = exc
        except Exception as exc:
            error_str = str(exc).lower()
            if "rate_limit" in error_str or "429" in error_str:
                if "tokens per day" in error_str or "tpd" in error_str or "daily" in error_str:
                    logger.warning(f"Daily/TPD Rate Limit reached. Disabling Groq for this run: {exc}")
                    _groq_temporarily_disabled = True
                    return classify_article_gemini(headline, description)

                wait = 2 ** (attempt + 1)
                logger.warning(f"Rate limited. Waiting {wait}s… (attempt {attempt + 1})")
                time.sleep(wait)
                last_error = exc
            else:
                logger.error(f"Groq API error (attempt {attempt + 1}): {exc}")
                last_error = exc

    logger.error(f"All retries exhausted. Disabling Groq for this run. Last error: {last_error}")
    _groq_temporarily_disabled = True
    return classify_article_gemini(headline, description)


# ---------------------------------------------------------------------------
# Single-article classification (Gemini Fallback)
# ---------------------------------------------------------------------------

def classify_article_gemini(headline: str, description: Optional[str] = None) -> dict:
    """Fallback classifier using Gemini when Groq is rate-limited."""
    client = _get_gemini_client()
    if client is None:
        logger.info("No GEMINI_API_KEY set — using default classification.")
        return _default_classification()
        
    user_content = f"Headline: {headline}"
    if description:
        user_content += f"\nDescription: {description}"
        
    for attempt in range(2):
        try:
            from google.genai import types
            
            # Use json schema enforcement
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=f"{SYSTEM_PROMPT}\n\n{user_content}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            raw = response.text
            result = json.loads(raw)
            
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
            except:
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
            logger.error(f"Gemini API error (attempt {attempt + 1}): {exc}")
            time.sleep(1)
            
    logger.error("Gemini failed. Falling back to default.")
    return _default_classification()


# ---------------------------------------------------------------------------
# Batch classification
# ---------------------------------------------------------------------------

def classify_batch(articles: list[dict]) -> list[dict]:
    """
    Classify a list of article dicts sequentially.
    Adds classification fields in-place and returns the list.
    """
    global _groq_temporarily_disabled
    _groq_temporarily_disabled = False  # Reset at the start of a batch

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

        # Polite delay between Groq calls if not disabled
        if idx < total and not _groq_temporarily_disabled:
            time.sleep(1)

    return articles

# ---------------------------------------------------------------------------
# Macro Summary Generation
# ---------------------------------------------------------------------------

def generate_macro_summary(articles_text: str) -> Optional[str]:
    """
    Generate a 3-bullet macro summary of the topic based on recent articles.
    """
    client = _get_groq_client()
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
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=250,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.error(f"Error generating macro summary: {exc}")
        return None
