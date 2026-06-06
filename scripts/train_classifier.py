"""Training script for the domain classification pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from sklearn.model_selection import StratifiedKFold, cross_val_score

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.pipeline.classifier import _build_pipeline, train  # noqa: E402
from app.pipeline.feature_extraction import extract_features_batch  # noqa: E402
from app.pipeline.ingestion import load_records_from_directory  # noqa: E402
from app.pipeline.java_bridge import run_java_analysis  # noqa: E402
from app.utils.logger import get_logger  # noqa: E402

logger = get_logger(__name__)

SAMPLE_DATA_DIR = PROJECT_ROOT / "data" / "sample_inputs"
N_FOLDS = 5


def main() -> None:
    """Load sample data, run cross-validation, train and save the classifier."""
    logger.info("Loading sample input files from %s", SAMPLE_DATA_DIR)
    records = load_records_from_directory(SAMPLE_DATA_DIR)

    if not records:
        logger.error("No records loaded — aborting training")
        sys.exit(1)

    logger.info("Running Java analysis on %d records", len(records))
    java_results = [run_java_analysis(record) for record in records]

    logger.info("Extracting features")
    feature_matrix = extract_features_batch(records, java_results)
    labels = np.array([record["domain"] for record in records])

    pipeline = _build_pipeline()
    cv = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=42)

    fold_accuracies: list[float] = []
    for fold_idx, (train_idx, val_idx) in enumerate(cv.split(feature_matrix, labels), start=1):
        X_train = feature_matrix[train_idx]
        y_train = labels[train_idx]
        X_val = feature_matrix[val_idx]
        y_val = labels[val_idx]

        fold_pipeline = _build_pipeline()
        fold_pipeline.fit(X_train, y_train)
        score = fold_pipeline.score(X_val, y_val)
        fold_accuracies.append(score)
        print(f"Fold {fold_idx} accuracy: {score:.4f}")

    mean_accuracy = float(np.mean(fold_accuracies))
    print(f"Mean accuracy: {mean_accuracy:.2f} across 6 domains")

    logger.info("Training final model on full dataset")
    train(records, java_results)


if __name__ == "__main__":
    main()
