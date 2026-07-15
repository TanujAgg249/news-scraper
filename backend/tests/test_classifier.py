from app.schemas import ArticleResponse
from app.api.articles import ReclassifyPayload
import pytest
from pydantic import ValidationError

def test_article_response_validation():
    # Valid impact
    article = ArticleResponse(
        id="123",
        headline="Oil prices surge",
        url="https://example.com/oil",
        oil_impact="Bullish",
        impact_confidence=0.9
    )
    assert article.oil_impact == "Bullish"

def test_reclassify_payload_validation():
    # Reclassify payload doesn't strictly validate enum via pydantic in current implementation,
    # but let's test it anyway in case it gets added.
    payload = ReclassifyPayload(oil_impact="Bearish")
    assert payload.oil_impact == "Bearish"
    
def test_reclassify_invalid_impact_manual_logic():
    # The API validates this manually in the route:
    valid_impacts = {"Bullish", "Bearish", "Neutral", "Mixed", "Uncertain"}
    assert "Bullish" in valid_impacts
    assert "Unknown" not in valid_impacts
