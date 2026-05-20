"""
analyzer.py - Oil Market Impact Analyzer
==========================================

This module handles:
1. Connecting to the Google Gemini API (using the new google.genai SDK)
2. Sending each article's headline + description to the LLM
3. Classifying the likely impact on oil markets:
   - "Bullish"  → likely to push oil prices UP   (green)
   - "Bearish"  → likely to push oil prices DOWN  (red)
   - "Neutral"  → no significant impact expected   (orange)
4. Returning a short reasoning for each classification

Handles free-tier rate limits (15 RPM) with automatic retry + backoff.
"""

import os
import time

from google import genai

from scraper.config import GEMINI_MODEL, ANALYSIS_PROMPT_TEMPLATE


def _create_client():
    """
    Create a Gemini client with the API key from environment variables.
    Returns the client, or None if the key is missing.
    """
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY not found in environment variables.")
        print("   → Make sure your .env file contains:  GEMINI_API_KEY=your_key_here")
        return None

    return genai.Client(api_key=api_key)


def analyze_oil_impact(articles: list[dict]) -> list[dict]:
    """
    Analyze each article's potential impact on oil markets using Gemini.

    Args:
        articles: List of article dicts (must have 'headline' key)

    Returns:
        The same list with two new keys added to each article:
            - oil_impact: "Bullish", "Bearish", or "Neutral"
            - impact_reason: A short 1-sentence explanation
    """

    client = _create_client()

    if client is None:
        # If Gemini isn't configured, mark everything as "Unknown"
        for article in articles:
            article["oil_impact"] = "Unknown"
            article["impact_reason"] = "Gemini API key not configured"
        return articles

    print(f"\n🧠 Analyzing oil market impact for {len(articles)} articles...")
    print("   (Free tier: ~15 requests/min — this may take a few minutes)\n")

    for i, article in enumerate(articles):
        headline = article.get("headline", "")
        description = article.get("description", "")

        # Build the prompt
        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            headline=headline,
            description=description or "No description available",
        )

        # Try up to 3 times with increasing backoff
        success = False
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                )
                result_text = response.text.strip()

                # Parse the response — expect format: "IMPACT | Reason"
                impact, reason = _parse_response(result_text)

                article["oil_impact"] = impact
                article["impact_reason"] = reason

                # Progress indicator
                symbol = {"Bullish": "🟢", "Bearish": "🔴", "Neutral": "🟠"}.get(impact, "⚪")
                print(f"   {symbol} [{i+1}/{len(articles)}] {impact}: {headline[:60]}...")

                success = True
                break  # Success — exit retry loop

            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                    # Rate limited — wait and retry
                    wait_time = (attempt + 1) * 15  # 15s, 30s, 45s
                    print(f"   ⏳ [{i+1}/{len(articles)}] Rate limited, waiting {wait_time}s (attempt {attempt+1}/3)...")
                    time.sleep(wait_time)
                else:
                    # Non-rate-limit error — don't retry
                    print(f"   ⚠️  [{i+1}/{len(articles)}] Analysis failed: {error_str[:120]}")
                    break

        if not success:
            article["oil_impact"] = "Unknown"
            article["impact_reason"] = "Analysis failed after retries"

        # Delay between requests to stay within 15 RPM free tier limit
        if i < len(articles) - 1:
            time.sleep(5)

    # Summary
    counts = {"Bullish": 0, "Bearish": 0, "Neutral": 0, "Unknown": 0}
    for a in articles:
        impact = a.get("oil_impact", "Unknown")
        counts[impact] = counts.get(impact, 0) + 1

    print(f"\n📊 Impact Summary: "
          f"🟢 {counts['Bullish']} Bullish | "
          f"🔴 {counts['Bearish']} Bearish | "
          f"🟠 {counts['Neutral']} Neutral | "
          f"⚪ {counts['Unknown']} Unknown")

    return articles


def _parse_response(text: str) -> tuple[str, str]:
    """
    Parse the LLM response into (impact, reason).

    Expected format from the prompt:
        "Bullish | Oil supply disruption likely due to sanctions"

    Falls back gracefully if format is unexpected.
    """
    # Try to split on pipe character
    if "|" in text:
        parts = text.split("|", 1)
        impact_raw = parts[0].strip()
        reason = parts[1].strip()
    else:
        # No pipe — try to detect the impact from the text
        impact_raw = text
        reason = text

    # Normalize the impact label
    impact_lower = impact_raw.lower()
    if "bullish" in impact_lower:
        return "Bullish", reason
    elif "bearish" in impact_lower:
        return "Bearish", reason
    elif "neutral" in impact_lower:
        return "Neutral", reason
    else:
        # Couldn't determine — default to Neutral
        return "Neutral", reason
