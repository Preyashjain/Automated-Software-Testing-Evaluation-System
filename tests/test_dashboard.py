"""Tests for the Streamlit dashboard module."""

import pandas as pd

from app.dashboard import streamlit_app


class TestDashboard:
    """Tests for dashboard helper functions and structure."""

    def test_key_functions_exist(self) -> None:
        """Dashboard module should expose all required helper functions."""
        required_functions = [
            "get_empty_state_message",
            "parse_uploaded_json",
            "build_summary_metrics",
            "build_domain_chart_data",
            "build_flagged_dataframe",
            "style_flagged_dataframe",
            "render_summary_metrics",
            "render_domain_breakdown",
            "render_flagged_records",
            "render_sample_predictions",
            "run_dashboard",
        ]
        for func_name in required_functions:
            assert hasattr(streamlit_app, func_name), f"Missing function: {func_name}"
            assert callable(getattr(streamlit_app, func_name))

    def test_empty_state_message(self) -> None:
        """Empty state message should guide the user to upload and run."""
        message = streamlit_app.get_empty_state_message()
        assert isinstance(message, str)
        assert "upload" in message.lower()

    def test_build_summary_metrics(self) -> None:
        """Summary metrics should return expected keys and types."""
        report = {
            "total_records": 10,
            "accuracy_estimate": 0.9,
            "flagged_records": ["id-1", "id-2"],
            "domain_breakdown": {"web": {"count": 5, "avg_confidence": 0.85}},
        }
        metrics = streamlit_app.build_summary_metrics(report)

        assert metrics["total_records"] == 10
        assert metrics["accuracy_estimate"] == 0.9
        assert metrics["flagged_records"] == 2
        assert metrics["domains_covered"] == 1

    def test_build_domain_chart_data(self) -> None:
        """Domain chart data should return a DataFrame with expected columns."""
        report = {
            "domain_breakdown": {
                "web": {"count": 5, "avg_confidence": 0.85},
                "api": {"count": 3, "avg_confidence": 0.92},
            }
        }
        df = streamlit_app.build_domain_chart_data(report)

        assert isinstance(df, pd.DataFrame)
        assert "domain" in df.columns
        assert "count" in df.columns
        assert "avg_confidence" in df.columns
        assert len(df) == 2

    def test_build_flagged_dataframe(self) -> None:
        """Flagged dataframe should format flags as comma-separated strings."""
        report = {
            "flagged_details": [
                {
                    "id": "rec-1",
                    "domain": "web",
                    "predicted_domain": "web",
                    "confidence": 0.45,
                    "flags": ["missing_assertions"],
                    "test_status": "warn",
                }
            ]
        }
        df = streamlit_app.build_flagged_dataframe(report)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert df.iloc[0]["flags"] == "missing_assertions"

    def test_style_flagged_dataframe_empty(self) -> None:
        """Styling an empty dataframe should return the original DataFrame."""
        df = pd.DataFrame()
        result = streamlit_app.style_flagged_dataframe(df)
        assert isinstance(result, pd.DataFrame)
        assert result.empty
