"""Streamlit results dashboard for the automated testing pipeline."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.pipeline.orchestrator import run_pipeline  # noqa: E402


def get_empty_state_message() -> str:
    """
    Return the message shown when no pipeline results exist.

    Returns:
        Empty state message string.
    """
    return "No results yet — upload a file and run the pipeline"


def parse_uploaded_json(uploaded_file: Any) -> list[dict[str, Any]]:
    """
    Parse an uploaded JSON file into a list of records.

    Args:
        uploaded_file: Streamlit uploaded file object.

    Returns:
        List of record dictionaries.

    Raises:
        ValueError: If the JSON is invalid or not a list.
    """
    content = uploaded_file.getvalue().decode("utf-8")
    data = json.loads(content)
    if not isinstance(data, list):
        raise ValueError("Uploaded JSON must be a list of records")
    return data


def build_summary_metrics(report: dict[str, Any]) -> dict[str, Any]:
    """
    Extract summary metric values from a pipeline report.

    Args:
        report: Pipeline report dictionary.

    Returns:
        Dictionary with summary metric values.
    """
    return {
        "total_records": report.get("total_records", 0),
        "accuracy_estimate": report.get("accuracy_estimate", 0.0),
        "flagged_records": len(report.get("flagged_records", [])),
        "domains_covered": len(report.get("domain_breakdown", {})),
    }


def build_domain_chart_data(report: dict[str, Any]) -> pd.DataFrame:
    """
    Build domain breakdown data for bar charts.

    Args:
        report: Pipeline report dictionary.

    Returns:
        DataFrame with domain, count, and avg_confidence columns.
    """
    breakdown = report.get("domain_breakdown", {})
    rows = [
        {
            "domain": domain,
            "count": stats["count"],
            "avg_confidence": stats["avg_confidence"],
        }
        for domain, stats in breakdown.items()
    ]
    return pd.DataFrame(rows)


def build_flagged_dataframe(report: dict[str, Any]) -> pd.DataFrame:
    """
    Build a DataFrame of flagged records for tabular display.

    Args:
        report: Pipeline report dictionary.

    Returns:
        DataFrame with flagged record details.
    """
    details = report.get("flagged_details", [])
    if not details:
        return pd.DataFrame(
            columns=["id", "domain", "predicted_domain", "confidence", "flags", "test_status"]
        )
    df = pd.DataFrame(details)
    df["flags"] = df["flags"].apply(
        lambda f: ", ".join(f) if isinstance(f, list) else str(f)
    )
    return df


def style_flagged_dataframe(df: pd.DataFrame) -> Any:
    """
    Apply conditional styling to highlight failed test rows in red.

    Args:
        df: Flagged records DataFrame.

    Returns:
        Styled pandas Styler object or original DataFrame if empty.
    """
    if df.empty:
        return df

    def highlight_fail(row: pd.Series) -> list[str]:
        if row.get("test_status") == "fail":
            return ["background-color: #ffcccc"] * len(row)
        return [""] * len(row)

    return df.style.apply(highlight_fail, axis=1)


def render_summary_metrics(report: dict[str, Any]) -> None:
    """
    Render summary metric cards in the Streamlit main area.

    Args:
        report: Pipeline report dictionary.
    """
    metrics = build_summary_metrics(report)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Records", metrics["total_records"])
    col2.metric("Accuracy Estimate", f"{metrics['accuracy_estimate']:.1%}")
    col3.metric("Flagged Records", metrics["flagged_records"])
    col4.metric("Domains Covered", metrics["domains_covered"])


def render_domain_breakdown(report: dict[str, Any]) -> None:
    """
    Render domain breakdown bar charts.

    Args:
        report: Pipeline report dictionary.
    """
    chart_data = build_domain_chart_data(report)
    if chart_data.empty:
        st.info("No domain data available.")
        return

    st.subheader("Domain Breakdown")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Record Count by Domain**")
        count_df = chart_data.set_index("domain")[["count"]]
        st.bar_chart(count_df)

    with col2:
        st.markdown("**Average Confidence by Domain**")
        conf_df = chart_data.set_index("domain")[["avg_confidence"]]
        st.bar_chart(conf_df)


def render_flagged_records(report: dict[str, Any]) -> None:
    """
    Render the flagged records table with conditional highlighting.

    Args:
        report: Pipeline report dictionary.
    """
    st.subheader("Flagged Records")
    df = build_flagged_dataframe(report)
    if df.empty:
        st.success("No flagged records — all tests passed with sufficient confidence.")
        return
    styled = style_flagged_dataframe(df)
    st.dataframe(styled, use_container_width=True)


def render_sample_predictions(report: dict[str, Any]) -> None:
    """
    Render expandable sample prediction cards with confidence progress bars.

    Args:
        report: Pipeline report dictionary.
    """
    st.subheader("Sample Predictions")
    samples = report.get("sample_predictions", [])
    if not samples:
        st.info("No sample predictions available.")
        return

    for sample in samples:
        title = f"{sample['id']} — {sample.get('predicted', 'N/A')}"
        with st.expander(title):
            st.write(f"**Actual Domain:** {sample.get('domain', 'N/A')}")
            st.write(f"**Predicted Domain:** {sample.get('predicted', 'N/A')}")
            st.write(f"**Test Status:** {sample.get('test_status', 'N/A')}")
            flags = sample.get("flags", [])
            st.write(f"**Flags:** {', '.join(flags) if flags else 'None'}")
            if "description" in sample:
                st.write(f"**Description:** {sample['description']}")
            confidence = float(sample.get("confidence", 0.0))
            st.write(f"**Confidence:** {confidence:.1%}")
            st.progress(min(max(confidence, 0.0), 1.0))


def run_dashboard() -> None:
    """Render the full Streamlit dashboard application."""
    st.set_page_config(
        page_title="Automated Testing & Evaluation System",
        page_icon="🧪",
        layout="wide",
    )

    st.title("Automated Software Testing & Evaluation System")
    st.markdown("Upload JSON test records, run the pipeline, and explore results.")

    if "pipeline_report" not in st.session_state:
        st.session_state.pipeline_report = None

    with st.sidebar:
        st.header("Pipeline Controls")
        uploaded_file = st.file_uploader(
            "Upload JSON Records",
            type=["json"],
            help="Upload a JSON file containing a list of test records.",
        )

        run_clicked = st.button("Run Pipeline", type="primary", use_container_width=True)

        if run_clicked:
            if uploaded_file is None:
                st.error("Please upload a JSON file first.")
            else:
                try:
                    records = parse_uploaded_json(uploaded_file)
                    with st.spinner("Running pipeline..."):
                        job_id = str(uuid.uuid4())
                        report = run_pipeline(records, job_id=job_id)
                        st.session_state.pipeline_report = report
                    st.success(f"Pipeline completed — Job ID: {job_id[:8]}...")
                except (json.JSONDecodeError, ValueError) as exc:
                    st.error(f"Invalid input: {exc}")
                except Exception as exc:
                    st.error(f"Pipeline failed: {exc}")

    report = st.session_state.pipeline_report

    if report is None:
        st.info(get_empty_state_message())
        return

    render_summary_metrics(report)
    st.divider()
    render_domain_breakdown(report)
    st.divider()
    render_flagged_records(report)
    st.divider()
    render_sample_predictions(report)


if __name__ == "__main__":
    run_dashboard()
