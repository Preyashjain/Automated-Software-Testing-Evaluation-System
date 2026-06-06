"""Tests for the domain classification pipeline."""

from __future__ import annotations

from typing import Any

from app.pipeline.classifier import predict, train


class TestClassifier:
    """Tests for classifier training and prediction."""

    def test_train_and_predict_returns_domain_and_confidence(
        self,
        sample_records: list[dict[str, str]],
        mock_java_results: list[dict[str, Any]],
    ) -> None:
        """Train on sample data and assert predict returns domain + confidence."""
        train(sample_records, mock_java_results)
        predictions = predict(sample_records, mock_java_results)

        assert isinstance(predictions, list)
        assert len(predictions) == len(sample_records)

        for pred in predictions:
            assert "predicted_domain" in pred
            assert "confidence" in pred
            assert isinstance(pred["predicted_domain"], str)
            assert isinstance(pred["confidence"], float)
            assert 0.0 <= pred["confidence"] <= 1.0

    def test_predictions_match_known_domains(
        self,
        sample_records: list[dict[str, str]],
        mock_java_results: list[dict[str, Any]],
    ) -> None:
        """Trained classifier should predict correct domains for sample data."""
        train(sample_records, mock_java_results)
        predictions = predict(sample_records, mock_java_results)

        for record, pred in zip(sample_records, predictions):
            assert pred["predicted_domain"] == record["domain"]
