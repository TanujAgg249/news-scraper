"""
API router: Graph — returns nodes and links for the knowledge graph visualization.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Article
from app.schemas import GraphNode, GraphLink, GraphResponse
from app.analysis.embeddings import compute_similarity_matrix

router = APIRouter(prefix="/api/graph", tags=["Graph"])


@router.get("", response_model=GraphResponse)
def get_graph(
    topic_id: Optional[str] = Query(None, description="Filter by topic UUID"),
    hours: int = Query(48, ge=1, le=720, description="Look-back window in hours"),
    min_importance: float = Query(0, ge=0, le=100, description="Minimum importance score"),
    db: Session = Depends(get_db),
):
    """
    Build and return a knowledge graph of articles.

    - Nodes = articles within the time window
    - Links = pairs of articles with cosine similarity > 0.55
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    # --- Query articles ---
    query = db.query(Article).filter(Article.created_at >= cutoff)

    if topic_id:
        query = query.filter(Article.topic_id == topic_id)
    if min_importance > 0:
        query = query.filter(Article.importance_score >= min_importance)

    articles = query.order_by(Article.published_at.desc()).limit(200).all()

    if not articles:
        return GraphResponse(nodes=[], links=[])

    # --- Build nodes ---
    nodes: list[GraphNode] = []
    for art in articles:
        headline = art.headline
        if len(headline) > 80:
            headline = headline[:77] + "…"
        entities = []
        if art.entities:
            import json
            try:
                entities = json.loads(art.entities)
            except Exception:
                pass

        nodes.append(
            GraphNode(
                id=art.id,
                headline=headline,
                description=art.description,
                source=art.source,
                oil_impact=art.oil_impact or "Unknown",
                impact_reason=art.impact_reason,
                importance_score=art.importance_score or 50.0,
                event_type=art.event_type or "primary",
                published_at=art.published_at,
                url=art.url,
                location=art.location,
                latitude=art.latitude,
                longitude=art.longitude,
                entities=entities,
            )
        )

    # --- Compute links from embeddings ---
    links: list[GraphLink] = []

    # Collect embeddings (only for articles that have them)
    embeddings_bytes: list[Optional[bytes]] = [art.embedding for art in articles]

    # Filter out articles without embeddings for the matrix, but keep index mapping
    valid_indices: list[int] = []
    valid_embeddings: list[bytes] = []
    for idx, eb in enumerate(embeddings_bytes):
        if eb is not None:
            valid_indices.append(idx)
            valid_embeddings.append(eb)

    if len(valid_embeddings) >= 2:
        sim_matrix = compute_similarity_matrix(valid_embeddings)

        # Extract pairs above threshold
        threshold = 0.55
        n = len(valid_indices)
        for i in range(n):
            for j in range(i + 1, n):
                sim = float(sim_matrix[i, j])
                if sim > threshold:
                    source_art = articles[valid_indices[i]]
                    target_art = articles[valid_indices[j]]
                    links.append(
                        GraphLink(
                            source=source_art.id,
                            target=target_art.id,
                            similarity=round(sim, 4),
                        )
                    )

    return GraphResponse(nodes=nodes, links=links)
