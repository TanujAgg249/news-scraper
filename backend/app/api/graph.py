"""
API router: Graph — returns nodes and links for the knowledge graph visualization.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Article, ArticleTopic
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
    query = db.query(Article).filter(func.coalesce(Article.published_at, Article.created_at) >= cutoff)

    if topic_id:
        query = query.join(ArticleTopic).filter(ArticleTopic.topic_id == topic_id)
    if min_importance > 0:
        query = query.filter(Article.importance_score >= min_importance)

    articles = query.order_by(func.coalesce(Article.published_at, Article.created_at).desc()).limit(200).all()

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

        # Extract pairs above threshold or with shared entities
        threshold = 0.55
        n = len(valid_indices)
        for i in range(n):
            for j in range(i + 1, n):
                sim = float(sim_matrix[i, j])
                
                # Check entity overlap
                source_node = nodes[valid_indices[i]]
                target_node = nodes[valid_indices[j]]
                source_entities = set(source_node.entities or [])
                target_entities = set(target_node.entities or [])
                shared_entities = source_entities.intersection(target_entities)
                
                # Boost similarity by 0.15 for each shared entity
                entity_boost = len(shared_entities) * 0.15
                total_sim = sim + entity_boost

                # If total sim clears threshold, link them!
                if total_sim > threshold:
                    # Cap similarity for visual weight
                    final_weight = min(total_sim, 1.0)
                    links.append(
                        GraphLink(
                            source=source_node.id,
                            target=target_node.id,
                            similarity=round(final_weight, 4),
                        )
                    )

    return GraphResponse(nodes=nodes, links=links)
