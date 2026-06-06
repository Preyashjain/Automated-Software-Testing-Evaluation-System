"""Python subprocess bridge to the Java analysis core."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.utils.logger import get_logger

load_dotenv()

logger = get_logger(__name__)

DEFAULT_JAR_PATH = Path("java_core/target/testpipeline.jar")


def _resolve_jar_path() -> Path:
    """
    Resolve the Java JAR path from environment or default location.

    Returns:
        Path to the testpipeline JAR file.
    """
    env_path = os.getenv("JAVA_JAR_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_JAR_PATH


def _build_mock_result(record: dict[str, Any]) -> dict[str, Any]:
    """
    Build a mock Java analysis result for development when the JAR is unavailable.

    Args:
        record: Input record dictionary.

    Returns:
        Mock result envelope matching Java output structure.
    """
    code_snippet = record.get("code_snippet", "")
    lines = code_snippet.splitlines() if code_snippet else []
    line_count = len(lines)

    lower = code_snippet.lower()
    complexity_keywords = ("if", "else", "for", "while", "try")
    complexity_score = sum(lower.count(kw) for kw in complexity_keywords)
    has_assertions = any(
        token in lower
        for token in ("assert", "assertequals", "asserttrue", "assertfalse")
    )

    if "def " in lower or "import pytest" in lower:
        detected_language = "Python"
    elif "public class" in lower or "import java." in lower:
        detected_language = "Java"
    elif "function " in lower or "const " in lower or "=>" in lower:
        detected_language = "JS"
    else:
        detected_language = "unknown"

    flags: list[str] = []
    if complexity_score > 5:
        flags.append("high_complexity")
    if not has_assertions:
        flags.append("missing_assertions")
    if line_count < 3:
        flags.append("trivial_input")

    if not flags:
        test_status = "pass"
    elif "trivial_input" in flags or (
        "high_complexity" in flags and "missing_assertions" in flags
    ):
        test_status = "fail"
    else:
        test_status = "warn"

    return {
        "record_id": record["id"],
        "domain": record["domain"],
        "metrics": {
            "line_count": line_count,
            "complexity_score": complexity_score,
            "has_assertions": has_assertions,
            "detected_language": detected_language,
        },
        "flags": flags,
        "test_status": test_status,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }


def run_java_analysis(record: dict[str, Any]) -> dict[str, Any]:
    """
    Run Java analysis on a single record via subprocess.

    Args:
        record: Validated input record with id, domain, code_snippet, description.

    Returns:
        Parsed JSON result from the Java pipeline or a mock result if JAR is missing.
    """
    jar_path = _resolve_jar_path()

    if not jar_path.exists():
        logger.warning(
            "Java JAR not found at %s — returning mock result for record %s",
            jar_path,
            record.get("id", "unknown"),
        )
        return _build_mock_result(record)

    input_json = json.dumps(record)

    try:
        result = subprocess.run(
            ["java", "-jar", str(jar_path)],
            input=input_json,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        logger.error("Java analysis timed out for record %s", record.get("id"))
        return _build_mock_result(record)
    except FileNotFoundError:
        logger.warning("Java runtime not found — returning mock result")
        return _build_mock_result(record)

    if result.returncode != 0:
        logger.error(
            "Java analysis failed for record %s: %s",
            record.get("id"),
            result.stderr.strip(),
        )
        return _build_mock_result(record)

    try:
        output = json.loads(result.stdout.strip())
        return output
    except json.JSONDecodeError as exc:
        logger.error(
            "Failed to parse Java output for record %s: %s",
            record.get("id"),
            exc,
        )
        return _build_mock_result(record)
