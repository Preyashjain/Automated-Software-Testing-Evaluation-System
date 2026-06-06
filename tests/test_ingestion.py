"""Tests for the ingestion pipeline module."""

from __future__ import annotations

from app.pipeline.ingestion import (
    VALID_DOMAINS,
    ingest_records,
    load_records_from_file,
    validate_record,
)


class TestValidateRecord:
    """Tests for record validation logic."""

    def test_valid_record_passes(self) -> None:
        """Valid records with all required fields should pass validation."""
        record = {
            "id": "test-001",
            "domain": "web",
            "code_snippet": "def test_x(): pass",
            "description": "A valid test record for web domain testing.",
        }
        assert validate_record(record) is True

    def test_missing_field_rejected(self) -> None:
        """Records missing required fields should be rejected."""
        record = {
            "id": "test-002",
            "domain": "api",
            "code_snippet": "pass",
        }
        assert validate_record(record) is False

    def test_bad_domain_rejected(self) -> None:
        """Records with invalid domain values should be rejected."""
        record = {
            "id": "test-003",
            "domain": "invalid_domain",
            "code_snippet": "pass",
            "description": "Record with an invalid domain value.",
        }
        assert validate_record(record) is False

    def test_empty_string_field_rejected(self) -> None:
        """Records with empty string fields should be rejected."""
        record = {
            "id": "test-004",
            "domain": "web",
            "code_snippet": "",
            "description": "Record with empty code snippet.",
        }
        assert validate_record(record) is False

    def test_all_valid_domains_accepted(self) -> None:
        """All six valid domain values should be accepted."""
        for domain in VALID_DOMAINS:
            record = {
                "id": f"test-{domain}",
                "domain": domain,
                "code_snippet": "assert True",
                "description": f"Test record for {domain} domain.",
            }
            assert validate_record(record) is True


class TestIngestRecords:
    """Tests for batch record ingestion."""

    def test_valid_records_pass_invalid_skipped(
        self, sample_records: list[dict[str, str]]
    ) -> None:
        """Valid records should be ingested; invalid ones should be skipped."""
        mixed = sample_records + [
            {"id": "bad", "domain": "unknown"},
            {
                "id": "good-mobile",
                "domain": "mobile",
                "code_snippet": "def test(): assert True",
                "description": "Valid mobile domain test record.",
            },
        ]
        result = ingest_records(mixed)
        assert len(result) == 6
        domains = {r["domain"] for r in result}
        assert "mobile" in domains

    def test_domain_normalized_to_lowercase(self) -> None:
        """Domain values should be normalized to lowercase during ingestion."""
        records = [
            {
                "id": "upper-001",
                "domain": "WEB",
                "code_snippet": "assert True",
                "description": "Test with uppercase domain value.",
            }
        ]
        result = ingest_records(records)
        assert result[0]["domain"] == "web"


class TestLoadFromFile:
    """Tests for loading records from JSON files."""

    def test_load_sample_file(self) -> None:
        """Loading a sample input file should return 20 valid records."""
        records = load_records_from_file("data/sample_inputs/domain_web.json")
        assert len(records) == 20
        assert all(r["domain"] == "web" for r in records)
