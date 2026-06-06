"""Scikit-learn classification pipeline for domain prediction."""

from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Any

import numpy as np
from dotenv import load_dotenv
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.pipeline.feature_extraction import extract_features_batch
from app.utils.logger import get_logger

load_dotenv()

logger = get_logger(__name__)

DEFAULT_MODEL_PATH = Path("models_store/classifier.pkl")


class FeatureVectorTransformer(BaseEstimator, TransformerMixin):
    """Custom transformer that converts precomputed feature vectors to a numpy matrix."""

    def __init__(self) -> None:
        """Initialize the feature vector transformer."""
        self._feature_matrix: np.ndarray | None = None

    def fit(self, X: np.ndarray, y: Any = None) -> "FeatureVectorTransformer":
        """
        Store the feature matrix for transformation.

        Args:
            X: Feature matrix of shape (n_samples, n_features).
            y: Unused target labels.

        Returns:
            Fitted transformer instance.
        """
        self._feature_matrix = np.asarray(X, dtype=np.float32)
        return self

    def transform(self, X: np.ndarray | None = None) -> np.ndarray:
        """
        Return the stored feature matrix.

        Args:
            X: Optional override feature matrix.

        Returns:
            Feature matrix as numpy array.
        """
        if X is not None:
            return np.asarray(X, dtype=np.float32)
        if self._feature_matrix is None:
            raise ValueError("Feature matrix not set. Call fit() first.")
        return self._feature_matrix


def _resolve_model_path() -> Path:
    """
    Resolve classifier model path from environment or default.

    Returns:
        Path to the classifier pickle file.
    """
    env_path = os.getenv("MODELS_STORE_PATH")
    if env_path:
        return Path(env_path) / "classifier.pkl"
    return DEFAULT_MODEL_PATH


def _build_pipeline() -> Pipeline:
    """
    Build the scikit-learn classification pipeline.

    Returns:
        Configured Pipeline with feature transformer and logistic regression.
    """
    return Pipeline(
        steps=[
            ("features", FeatureVectorTransformer()),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    max_iter=2000,
                    C=10.0,
                    solver="lbfgs",
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )


def train(
    records: list[dict[str, Any]], java_results: list[dict[str, Any]]
) -> Pipeline:
    """
    Train the domain classifier and save to disk.

    Args:
        records: Training records with domain labels.
        java_results: Corresponding Java analysis results.

    Returns:
        Fitted sklearn Pipeline.
    """
    logger.info("Training classifier on %d records", len(records))

    feature_matrix = extract_features_batch(records, java_results)
    labels = np.array([record["domain"] for record in records])

    pipeline = _build_pipeline()
    pipeline.fit(feature_matrix, labels)

    model_path = _resolve_model_path()
    model_path.parent.mkdir(parents=True, exist_ok=True)
    with model_path.open("wb") as handle:
        pickle.dump(pipeline, handle)

    logger.info("Classifier saved to %s", model_path)
    return pipeline


def _load_pipeline() -> Pipeline | None:
    """
    Load a trained classifier pipeline from disk.

    Returns:
        Loaded Pipeline or None if not found.
    """
    model_path = _resolve_model_path()
    if not model_path.exists():
        logger.warning("Classifier model not found at %s", model_path)
        return None

    with model_path.open("rb") as handle:
        return pickle.load(handle)


def predict(
    records: list[dict[str, Any]], java_results: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Predict domain labels and confidence scores for records.

    Args:
        records: Input records to classify.
        java_results: Corresponding Java analysis results.

    Returns:
        List of dicts with predicted_domain and confidence keys per record.
    """
    pipeline = _load_pipeline()
    feature_matrix = extract_features_batch(records, java_results)

    if pipeline is None:
        logger.warning("No trained model — using domain labels as fallback predictions")
        return [
            {"predicted_domain": record["domain"], "confidence": 0.5}
            for record in records
        ]

    probabilities = pipeline.predict_proba(feature_matrix)
    predictions = pipeline.predict(feature_matrix)
    classes = pipeline.named_steps["classifier"].classes_

    results: list[dict[str, Any]] = []
    for i, predicted in enumerate(predictions):
        class_index = list(classes).index(predicted)
        confidence = float(probabilities[i][class_index])
        results.append(
            {
                "predicted_domain": str(predicted),
                "confidence": round(confidence, 4),
            }
        )

    return results
