"""Shared pytest fixtures for the automated testing system."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def test_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Configure a Streamlit-safe test environment with isolated storage paths.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Temporary directory for test artifacts.
    """
    models_dir = tmp_path / "models_store"
    reports_dir = tmp_path / "reports"
    models_dir.mkdir()
    reports_dir.mkdir()

    monkeypatch.setenv("MODELS_STORE_PATH", str(models_dir))
    monkeypatch.setenv("REPORTS_PATH", str(reports_dir))
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("STREAMLIT_SERVER_HEADLESS", "true")
    monkeypatch.delenv("JAVA_JAR_PATH", raising=False)


@pytest.fixture
def sample_records() -> list[dict[str, str]]:
    """
    Provide five sample records covering five domains (web repeated once).

    Returns:
        List of validated sample record dictionaries.
    """
    return [
        {
            "id": "rec-web-001",
            "domain": "web",
            "code_snippet": "def test_login():\n    assert page.title() == 'Login'",
            "description": "Tests the login page title renders correctly in the browser.",
        },
        {
            "id": "rec-api-001",
            "domain": "api",
            "code_snippet": "def test_health():\n    r = client.get('/api/health')\n    assert r.status_code == 200",
            "description": "Verifies the API health endpoint returns HTTP 200 status code.",
        },
        {
            "id": "rec-db-001",
            "domain": "database",
            "code_snippet": "def test_query():\n    result = db.execute('SELECT 1')\n    assert result.fetchone()[0] == 1",
            "description": "Tests database connection executes a simple SELECT query successfully.",
        },
        {
            "id": "rec-sec-001",
            "domain": "security",
            "code_snippet": "def test_xss():\n    r = client.post('/comments', json={'text': '<script>'})\n    assert '<script>' not in r.text",
            "description": "Checks XSS payloads are sanitized in user-submitted comment content.",
        },
        {
            "id": "rec-perf-001",
            "domain": "performance",
            "code_snippet": "def test_latency():\n    start = time.time()\n    client.get('/api/data')\n    assert time.time() - start < 0.5",
            "description": "Tests API response latency stays under 500ms threshold under load.",
        },
    ]


@pytest.fixture
def mock_java_results() -> list[dict[str, Any]]:
    """
    Provide mock Java bridge output for sample records.

    Returns:
        List of mock Java analysis result dictionaries.
    """
    return [
        {
            "record_id": "rec-web-001",
            "domain": "web",
            "metrics": {
                "line_count": 2,
                "complexity_score": 0,
                "has_assertions": True,
                "detected_language": "Python",
            },
            "flags": ["trivial_input"],
            "test_status": "fail",
            "processed_at": "2024-01-01T00:00:00+00:00",
        },
        {
            "record_id": "rec-api-001",
            "domain": "api",
            "metrics": {
                "line_count": 3,
                "complexity_score": 0,
                "has_assertions": True,
                "detected_language": "Python",
            },
            "flags": [],
            "test_status": "pass",
            "processed_at": "2024-01-01T00:00:00+00:00",
        },
        {
            "record_id": "rec-db-001",
            "domain": "database",
            "metrics": {
                "line_count": 3,
                "complexity_score": 0,
                "has_assertions": True,
                "detected_language": "Python",
            },
            "flags": [],
            "test_status": "pass",
            "processed_at": "2024-01-01T00:00:00+00:00",
        },
        {
            "record_id": "rec-sec-001",
            "domain": "security",
            "metrics": {
                "line_count": 3,
                "complexity_score": 0,
                "has_assertions": True,
                "detected_language": "Python",
            },
            "flags": [],
            "test_status": "pass",
            "processed_at": "2024-01-01T00:00:00+00:00",
        },
        {
            "record_id": "rec-perf-001",
            "domain": "performance",
            "metrics": {
                "line_count": 4,
                "complexity_score": 0,
                "has_assertions": True,
                "detected_language": "Python",
            },
            "flags": [],
            "test_status": "pass",
            "processed_at": "2024-01-01T00:00:00+00:00",
        },
    ]
