"""Pipeline orchestrator that ties all processing stages together."""

from __future__ import annotations

import json
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.pipeline.classifier import predict
from app.pipeline.ingestion import ingest_records
from app.pipeline.java_bridge import run_java_analysis
from app.utils.logger import get_logger

load_dotenv()

logger = get_logger(__name__)

CONFIDENCE_THRESHOLD = 0.6


def _resolve_reports_path() -> Path:
    """
    Resolve reports directory from environment or default.

    Returns:
        Path to the reports directory.
    """
    env_path = os.getenv("REPORTS_PATH")
    if env_path:
        return Path(env_path)
    return Path("reports")


def _compute_accuracy_estimate(
    records: list[dict[str, str]], predictions: list[dict[str, Any]]
) -> float:
    """
    Estimate classification accuracy by comparing predictions to actual domains.

    Args:
        records: Input records with ground-truth domain labels.
        predictions: Classifier prediction results.

    Returns:
        Accuracy estimate as a float between 0 and 1.
    """
    if not records:
        return 0.0

    correct = sum(
        1
        for record, pred in zip(records, predictions)
        if record["domain"] == pred["predicted_domain"]
    )
    return round(correct / len(records), 4)


def _build_domain_breakdown(
    records: list[dict[str, str]], predictions: list[dict[str, Any]]
) -> dict[str, dict[str, float]]:
    """
    Build per-domain count and average confidence statistics.

    Args:
        records: Input records.
        predictions: Classifier predictions.

    Returns:
        Dictionary mapping domain to count and avg_confidence.
    """
    domain_data: dict[str, list[float]] = defaultdict(list)

    for record, pred in zip(records, predictions):
        domain = record["domain"]
        domain_data[domain].append(pred["confidence"])

    breakdown: dict[str, dict[str, float]] = {}
    for domain, confidences in sorted(domain_data.items()):
        breakdown[domain] = {
            "count": len(confidences),
            "avg_confidence": round(sum(confidences) / len(confidences), 4),
        }

    return breakdown


def _identify_flagged_records(
    records: list[dict[str, str]],
    java_results: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
) -> list[str]:
    """
    Identify record IDs that failed tests or have low confidence.

    Args:
        records: Input records.
        java_results: Java analysis results.
        predictions: Classifier predictions.

    Returns:
        List of flagged record IDs.
    """
    flagged: list[str] = []
    for record, java_result, pred in zip(records, java_results, predictions):
        test_status = java_result.get("test_status", "pass")
        confidence = pred["confidence"]
        if test_status == "fail" or confidence < CONFIDENCE_THRESHOLD:
            flagged.append(record["id"])
    return flagged


def _build_sample_predictions(
    records: list[dict[str, str]],
    java_results: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Build sample prediction entries for the report.

    Args:
        records: Input records.
        java_results: Java analysis results.
        predictions: Classifier predictions.
        limit: Maximum number of samples to include.

    Returns:
        List of sample prediction dictionaries.
    """
    samples: list[dict[str, Any]] = []
    for record, java_result, pred in zip(records, java_results, predictions):
        if len(samples) >= limit:
            break
        samples.append(
            {
                "id": record["id"],
                "domain": record["domain"],
                "predicted": pred["predicted_domain"],
                "confidence": pred["confidence"],
                "flags": java_result.get("flags", []),
                "test_status": java_result.get("test_status", "pass"),
                "description": record["description"][:120],
            }
        )
    return samples


def _build_flagged_details(
    records: list[dict[str, str]],
    java_results: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Build detailed flagged record entries for dashboard display.

    Args:
        records: Input records.
        java_results: Java analysis results.
        predictions: Classifier predictions.

    Returns:
        List of flagged record detail dictionaries.
    """
    flagged_ids = set(
        _identify_flagged_records(records, java_results, predictions)
    )
    details: list[dict[str, Any]] = []

    for record, java_result, pred in zip(records, java_results, predictions):
        if record["id"] in flagged_ids:
            details.append(
                {
                    "id": record["id"],
                    "domain": record["domain"],
                    "predicted_domain": pred["predicted_domain"],
                    "confidence": pred["confidence"],
                    "flags": java_result.get("flags", []),
                    "test_status": java_result.get("test_status", "pass"),
                }
            )

    return details


def run_pipeline(records: list[dict[str, Any]], job_id: str | None = None) -> dict[str, Any]:
    """
    Execute the full analysis pipeline across all stages.

    Args:
        records: Raw input records to process.
        job_id: Optional job identifier; generated if not provided.

    Returns:
        Structured pipeline report dictionary.
    """
    job_id = job_id or str(uuid.uuid4())
    stage_durations: dict[str, float] = {}
    pipeline_start = time.perf_counter()

    # Stage 1: Ingestion
    stage_start = time.perf_counter()
    validated = ingest_records(records)
    stage_durations["ingestion"] = round(time.perf_counter() - stage_start, 4)
    logger.info("Stage 1 (ingestion) completed in %.4fs", stage_durations["ingestion"])

    if not validated:
        report = {
            "job_id": job_id,
            "total_records": 0,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "accuracy_estimate": 0.0,
            "domain_breakdown": {},
            "flagged_records": [],
            "flagged_details": [],
            "sample_predictions": [],
            "stage_durations": stage_durations,
            "total_duration": round(time.perf_counter() - pipeline_start, 4),
        }
        _save_report(report, job_id)
        return report

    # Stage 2: Java bridge analysis
    stage_start = time.perf_counter()
    java_results = [run_java_analysis(record) for record in validated]
    stage_durations["java_bridge"] = round(time.perf_counter() - stage_start, 4)
    logger.info("Stage 2 (java_bridge) completed in %.4fs", stage_durations["java_bridge"])

    # Stage 3: Feature extraction (implicit in classifier predict)
    stage_start = time.perf_counter()
    predictions = predict(validated, java_results)
    stage_durations["classification"] = round(time.perf_counter() - stage_start, 4)
    logger.info(
        "Stage 3-4 (features + classification) completed in %.4fs",
        stage_durations["classification"],
    )

    # Stage 5: Generate report
    stage_start = time.perf_counter()
    accuracy = _compute_accuracy_estimate(validated, predictions)
    domain_breakdown = _build_domain_breakdown(validated, predictions)
    flagged_records = _identify_flagged_records(validated, java_results, predictions)
    sample_predictions = _build_sample_predictions(validated, java_results, predictions)
    flagged_details = _build_flagged_details(validated, java_results, predictions)

    report: dict[str, Any] = {
        "job_id": job_id,
        "total_records": len(validated),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "accuracy_estimate": accuracy,
        "domain_breakdown": domain_breakdown,
        "flagged_records": flagged_records,
        "flagged_details": flagged_details,
        "sample_predictions": sample_predictions,
        "stage_durations": stage_durations,
        "total_duration": round(time.perf_counter() - pipeline_start, 4),
    }
    stage_durations["report_generation"] = round(time.perf_counter() - stage_start, 4)
    logger.info(
        "Stage 5 (report) completed in %.4fs — total: %.4fs",
        stage_durations["report_generation"],
        report["total_duration"],
    )

    _save_report(report, job_id)
    return report


def _save_report(report: dict[str, Any], job_id: str) -> None:
    """
    Persist pipeline report to the reports directory.

    Args:
        report: Report dictionary to save.
        job_id: Job identifier used as filename.
    """
    reports_path = _resolve_reports_path()
    reports_path.mkdir(parents=True, exist_ok=True)
    report_file = reports_path / f"{job_id}.json"

    with report_file.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    logger.info("Report saved to %s", report_file)
