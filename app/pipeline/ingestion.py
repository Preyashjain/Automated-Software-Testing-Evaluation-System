"""Structured input loading and validation for pipeline records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)

REQUIRED_FIELDS = ("id", "domain", "code_snippet", "description")
VALID_DOMAINS = frozenset(
    {"web", "api", "database", "security", "performance", "mobile"}
)


def validate_record(record: dict[str, Any]) -> bool:
    """
    Validate a single record against required fields and domain constraints.

    Args:
        record: Dictionary representing an input record.

    Returns:
        True if the record is valid, False otherwise.
    """
    if not isinstance(record, dict):
        logger.warning("Skipping record: expected dict, got %s", type(record).__name__)
        return False

    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        logger.warning(
            "Skipping record %s: missing fields %s",
            record.get("id", "unknown"),
            missing,
        )
        return False

    for field in REQUIRED_FIELDS:
        value = record[field]
        if not isinstance(value, str) or not value.strip():
            logger.warning(
                "Skipping record %s: field '%s' must be a non-empty string",
                record.get("id", "unknown"),
                field,
            )
            return False

    domain = record["domain"].strip().lower()
    if domain not in VALID_DOMAINS:
        logger.warning(
            "Skipping record %s: invalid domain '%s'",
            record.get("id", "unknown"),
            record["domain"],
        )
        return False

    return True


def clean_record(record: dict[str, Any]) -> dict[str, str]:
    """
    Return a cleaned copy of a validated record with normalized domain.

    Args:
        record: Validated input record.

    Returns:
        Cleaned record dictionary.
    """
    return {
        "id": record["id"].strip(),
        "domain": record["domain"].strip().lower(),
        "code_snippet": record["code_snippet"].strip(),
        "description": record["description"].strip(),
    }


def load_records_from_file(file_path: str | Path) -> list[dict[str, str]]:
    """
    Load and validate records from a JSON file.

    Args:
        file_path: Path to a JSON file containing a list of records.

    Returns:
        List of validated and cleaned record dictionaries.
    """
    path = Path(file_path)
    if not path.exists():
        logger.error("Input file not found: %s", path)
        return []

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON in %s: %s", path, exc)
        return []

    if not isinstance(data, list):
        logger.error("Expected a JSON array in %s", path)
        return []

    validated: list[dict[str, str]] = []
    for record in data:
        if validate_record(record):
            validated.append(clean_record(record))

    logger.info(
        "Loaded %d valid records from %s (%d skipped)",
        len(validated),
        path.name,
        len(data) - len(validated),
    )
    return validated


def load_records_from_directory(directory: str | Path) -> list[dict[str, str]]:
    """
    Load and validate records from all JSON files in a directory.

    Args:
        directory: Directory containing JSON input files.

    Returns:
        Combined list of validated records.
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        logger.error("Input directory not found: %s", dir_path)
        return []

    all_records: list[dict[str, str]] = []
    for json_file in sorted(dir_path.glob("*.json")):
        if json_file.name.startswith("."):
            continue
        all_records.extend(load_records_from_file(json_file))

    logger.info("Total records loaded from %s: %d", dir_path, len(all_records))
    return all_records


def ingest_records(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    """
    Validate and clean a list of in-memory records.

    Args:
        records: Raw record dictionaries.

    Returns:
        List of validated and cleaned records.
    """
    validated: list[dict[str, str]] = []
    for record in records:
        if validate_record(record):
            validated.append(clean_record(record))
        else:
            logger.warning("Skipped invalid record during ingestion")

    logger.info("Ingested %d of %d records", len(validated), len(records))
    return validated
