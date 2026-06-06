"""Feature extraction using HuggingFace embeddings and Java metrics."""

from __future__ import annotations

from typing import Any

import numpy as np

from app.utils.logger import get_logger

logger = get_logger(__name__)

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
NUMERIC_FEATURE_COUNT = 3

_model = None


def _get_embedding_model():
    """
    Lazily load and cache the sentence-transformers embedding model.

    Returns:
        Loaded SentenceTransformer model instance.
    """
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
            _model = SentenceTransformer(EMBEDDING_MODEL)
        except Exception as exc:
            logger.warning(
                "Could not load embedding model (%s) — using hash-based fallback",
                exc,
            )
            _model = None
    return _model


def _hash_embedding(text: str, dim: int = EMBEDDING_DIM) -> np.ndarray:
    """
    Generate a deterministic pseudo-embedding when the model is unavailable.

    Args:
        text: Input text to embed.
        dim: Embedding dimensionality.

    Returns:
        Normalized numpy array of shape (dim,).
    """
    rng = np.random.default_rng(abs(hash(text)) % (2**32))
    vector = rng.standard_normal(dim).astype(np.float32)
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector /= norm
    return vector


def _extract_numeric_features(java_result: dict[str, Any]) -> np.ndarray:
    """
    Extract numeric features from Java analysis output.

    Args:
        java_result: Result dictionary from the Java bridge.

    Returns:
        Numpy array with line_count, complexity_score, has_assertions (0/1).
    """
    metrics = java_result.get("metrics", {})
    line_count = float(metrics.get("line_count", 0))
    complexity_score = float(metrics.get("complexity_score", 0))
    has_assertions = 1.0 if metrics.get("has_assertions", False) else 0.0
    return np.array([line_count, complexity_score, has_assertions], dtype=np.float32)


def extract_features(
    record: dict[str, Any], java_result: dict[str, Any]
) -> np.ndarray:
    """
    Extract combined feature vector for a single record.

    Args:
        record: Input record with description field.
        java_result: Java analysis result for the same record.

    Returns:
        Combined feature vector of shape (387,) — 384-dim embedding + 3 numeric features.
    """
    description = record.get("description", "")
    model = _get_embedding_model()

    if model is not None:
        embedding = model.encode(description, convert_to_numpy=True).astype(np.float32)
    else:
        embedding = _hash_embedding(description)

    numeric = _extract_numeric_features(java_result)
    combined = np.concatenate([embedding, numeric])
    return combined


def extract_features_batch(
    records: list[dict[str, Any]], java_results: list[dict[str, Any]]
) -> np.ndarray:
    """
    Extract feature matrix for a batch of records.

    Args:
        records: List of input records.
        java_results: Corresponding Java analysis results.

    Returns:
        Feature matrix of shape (n_samples, 387).
    """
    if len(records) != len(java_results):
        raise ValueError("records and java_results must have the same length")

    features = [
        extract_features(record, java_result)
        for record, java_result in zip(records, java_results)
    ]
    return np.vstack(features)
