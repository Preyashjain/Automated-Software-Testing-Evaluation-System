"""Tests for the Java bridge subprocess module."""

import json
from unittest.mock import MagicMock, patch

from app.pipeline.java_bridge import _build_mock_result, run_java_analysis


class TestJavaBridge:
    """Tests for Java analysis bridge functionality."""

    def test_mock_result_has_correct_keys(self) -> None:
        """Mock result should contain all required envelope keys."""
        record = {
            "id": "test-001",
            "domain": "web",
            "code_snippet": "def test_x():\n    assert True",
            "description": "A simple web test.",
        }
        result = _build_mock_result(record)

        assert "record_id" in result
        assert "domain" in result
        assert "metrics" in result
        assert "flags" in result
        assert "test_status" in result
        assert "processed_at" in result

        metrics = result["metrics"]
        assert "line_count" in metrics
        assert "complexity_score" in metrics
        assert "has_assertions" in metrics
        assert "detected_language" in metrics

    def test_mock_result_detects_flags(self) -> None:
        """Mock result should flag trivial input for short snippets."""
        record = {
            "id": "test-002",
            "domain": "api",
            "code_snippet": "x=1",
            "description": "Trivial snippet.",
        }
        result = _build_mock_result(record)
        assert "trivial_input" in result["flags"]
        assert result["test_status"] == "fail"

    @patch("app.pipeline.java_bridge._resolve_jar_path")
    @patch("subprocess.run")
    def test_subprocess_call_returns_parsed_json(
        self, mock_run: MagicMock, mock_jar_path: MagicMock
    ) -> None:
        """Subprocess call should parse and return JSON output with correct keys."""
        mock_jar_path.return_value.exists.return_value = True

        expected = {
            "record_id": "test-003",
            "domain": "database",
            "metrics": {
                "line_count": 3,
                "complexity_score": 1,
                "has_assertions": True,
                "detected_language": "Python",
            },
            "flags": [],
            "test_status": "pass",
            "processed_at": "2024-01-01T00:00:00+00:00",
        }
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(expected),
            stderr="",
        )

        record = {
            "id": "test-003",
            "domain": "database",
            "code_snippet": "def test_q():\n    assert db.query()",
            "description": "Database query test.",
        }
        result = run_java_analysis(record)

        assert result["record_id"] == "test-003"
        assert result["test_status"] == "pass"
        mock_run.assert_called_once()

    @patch("app.pipeline.java_bridge._resolve_jar_path")
    def test_graceful_fallback_when_jar_missing(
        self, mock_jar_path: MagicMock
    ) -> None:
        """Bridge should return mock result when JAR file is not found."""
        mock_jar_path.return_value.exists.return_value = False

        record = {
            "id": "test-004",
            "domain": "security",
            "code_snippet": "def test_auth():\n    assert token.valid",
            "description": "Security auth test.",
        }
        result = run_java_analysis(record)

        assert result["record_id"] == "test-004"
        assert "metrics" in result
        assert "test_status" in result
