"""
Embeddings for article similarity.
Uses sentence-transformers (all-MiniLM-L6-v2) when available, falls back to
lightweight TF-IDF keyword-based similarity for cloud deployments where
PyTorch is too heavy.
"""

import os
import pickle
from typing import Optional

# Disable TensorFlow (we only use PyTorch) — must be set BEFORE importing transformers
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np

from app.config import settings

# ---------------------------------------------------------------------------
# Lazy-loaded model singleton
# ---------------------------------------------------------------------------
_model = None
_model_failed = False
_use_lightweight = os.environ.get("RENDER") == "true"


def _get_model():
    """Load the sentence-transformer model on first use."""
    global _model, _model_failed
    if _use_lightweight or _model_failed:
        return None
    if _model is None:
        try:
            print(f"[Embeddings] Loading model '{settings.EMBEDDING_MODEL}'…")
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(settings.EMBEDDING_MODEL)
            print("[Embeddings] Model loaded.")
        except Exception as exc:
            print(f"[Embeddings] Failed to load model: {exc}")
            _model_failed = True
            return None
    return _model


# ---------------------------------------------------------------------------
# Lightweight TF-IDF-like embedding (no external ML dependencies)
# ---------------------------------------------------------------------------

_EMBED_DIM = 384  # Same dimension as MiniLM-L6-v2 for consistency

def _lightweight_embedding(text: str) -> np.ndarray:
    """
    Generate a simple bag-of-words hash-based embedding.
    Uses hashing trick to map words to a fixed-size vector.
    Not as good as sentence-transformers, but works without PyTorch.
    """
    import re
    words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
    vec = np.zeros(_EMBED_DIM, dtype=np.float32)
    for word in words:
        # Hash each word to a position in the vector
        idx = hash(word) % _EMBED_DIM
        vec[idx] += 1.0
    # Normalise to unit vector
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_embedding(text: str) -> Optional[bytes]:
    """
    Generate an embedding for the given text.
    Returns the embedding as pickled numpy array bytes, or None if unavailable.
    """
    model = _get_model()
    if model is not None:
        try:
            embedding: np.ndarray = model.encode(text, convert_to_numpy=True)
            return pickle.dumps(embedding)
        except Exception as exc:
            print(f"[Embeddings] Encoding failed: {exc}")
            return None

    # Lightweight fallback
    if _use_lightweight or _model_failed:
        try:
            embedding = _lightweight_embedding(text)
            return pickle.dumps(embedding)
        except Exception as exc:
            print(f"[Embeddings] Lightweight encoding failed: {exc}")
            return None

    return None


def unpickle_embedding(data: bytes) -> Optional[np.ndarray]:
    """Safely unpickle an embedding from bytes."""
    if data is None:
        return None
    try:
        return pickle.loads(data)
    except Exception as exc:
        print(f"[Embeddings] Failed to unpickle embedding: {exc}")
        return None


def compute_similarity_matrix(embeddings_bytes: list[bytes]) -> np.ndarray:
    """
    Given a list of pickled embedding bytes, compute the full pairwise
    cosine similarity matrix.

    Returns an NxN numpy array where entry (i, j) is the cosine similarity
    between embedding i and embedding j.
    """
    vectors: list[np.ndarray] = []
    for eb in embeddings_bytes:
        vec = unpickle_embedding(eb)
        if vec is not None:
            vectors.append(vec.flatten())
        else:
            # Insert zero vector as placeholder
            vectors.append(np.zeros(_EMBED_DIM))

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
