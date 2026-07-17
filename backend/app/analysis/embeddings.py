"""
Embeddings for article similarity.
Uses sentence-transformers (all-MiniLM-L6-v2) when available, falls back to
lightweight TF-IDF keyword-based similarity for cloud deployments where
PyTorch is too heavy.
"""

import numpy as np
from typing import Optional, List
from openai import OpenAI

from app.config import settings
from app.logger import logger

# Lazy-loaded client
_openai_client = None

def _get_client():
    global _openai_client
    if _openai_client is None:
        if not settings.OPENAI_API_KEY:
            return None
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client

def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generate an embedding using OpenAI text-embedding-3-small.
    Returns a list of 1536 floats.
    """
    client = _get_client()
    if client is None:
        logger.warning("No OPENAI_API_KEY set. Cannot generate embedding.")
        return None

    try:
        response = client.embeddings.create(
            input=[text],
            model=settings.OPENAI_EMBEDDING_MODEL
        )
        return response.data[0].embedding
    except Exception as exc:
        logger.error(f"OpenAI Embedding failed: {exc}")
        return None

def compute_similarity_matrix(embeddings_list: List[List[float]]) -> np.ndarray:
    """
    Given a list of raw embeddings (lists of floats), compute the full pairwise
    cosine similarity matrix.
    """
    vectors: list[np.ndarray] = []
    dim = 1536
    for emb in embeddings_list:
        if emb is not None and len(emb) == dim:
            vectors.append(np.array(emb, dtype=np.float32))
        else:
            vectors.append(np.zeros(dim, dtype=np.float32))

    if len(vectors) == 0:
        return np.array([])

    matrix = np.vstack(vectors)  # shape: (N, dim)

    # Normalise each row to unit length
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)  # avoid division by zero
    matrix_normed = matrix / norms

    # Cosine similarity = dot product of normalised vectors
    similarity = matrix_normed @ matrix_normed.T

    return similarity
