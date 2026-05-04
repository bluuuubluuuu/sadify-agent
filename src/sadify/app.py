from __future__ import annotations

from pathlib import Path
import sys

from dotenv import load_dotenv

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sadify.config import AppConfig, load_config
from sadify.logging_config import configure_logging
from sadify.models import build_model_routes, build_provider_statuses
from sadify.services.requirement_analysis import analyze_requirement_text


def build_page_model(config: AppConfig) -> dict[str, object]:
    model_routes = [
        route.to_display_dict() for route in build_model_routes(config).values()
    ]
    provider_statuses = [
        status.to_display_dict() for status in build_provider_statuses(config)
    ]

    return {
        "title": "SADify",
        "tagline": (
            "An AI system analyst that turns messy operational requirements "
            "into clarified, developer-ready SAD outputs."
        ),
        "project": config.google_cloud_project,
        "model": config.sadify_model,
        "model_provider": config.sadify_model_provider,
        "model_routes": model_routes,
        "provider_statuses": provider_statuses,
        "sections": [
            "Requirement intake",
            "Completeness and confidence",
            "Clarification questions",
            "SAD preview",
            "Exports",
        ],
        "diagnostics": {
            "drive_folder_configured": config.sadify_drive_root_folder_id is not None,
            "runtime_service_account_configured": (
                config.sadify_runtime_service_account is not None
            ),
        },
    }


def build_analysis_view_model(requirement_text: str) -> dict[str, object]:
    return analyze_requirement_text(requirement_text).to_display_dict()


def main() -> None:
    load_dotenv()
    config = load_config()
    logger = configure_logging(config.sadify_log_level)
    logger.info("Starting SADify Streamlit app")

    import streamlit as st

    page = build_page_model(config)

    st.set_page_config(page_title="SADify", page_icon="S", layout="wide")
    st.title(page["title"])
    st.caption(page["tagline"])

    with st.sidebar:
        st.subheader("Runtime")
        st.write(f"Project: `{page['project']}`")
        st.write(f"Provider: `{page['model_provider']}`")
        st.write(f"Model: `{page['model']}`")
        st.write(f"Environment: `{config.sadify_env}`")
        st.subheader("Model routes")
        for route in page["model_routes"]:
            st.write(
                f"{route['task']}: `{route['provider']}` / `{route['model']}`"
            )
        st.subheader("Diagnostics")
        diagnostics = page["diagnostics"]
        st.write(
            "Drive folder:",
            "configured" if diagnostics["drive_folder_configured"] else "missing",
        )
        st.write(
            "Service account:",
            (
                "configured"
                if diagnostics["runtime_service_account_configured"]
                else "missing"
            ),
        )
        with st.expander("LLM provider readiness", expanded=False):
            for status in page["provider_statuses"]:
                state = "configured" if status["configured"] else "not configured"
                st.write(f"{status['label']}: {state}")

    requirement_text = st.text_area(
        "Describe the operational problem",
        placeholder=(
            "Example: Our warehouse team keeps losing track of stock movement..."
        ),
        height=180,
    )

    if st.button("Analyze requirement", type="primary"):
        analysis = build_analysis_view_model(requirement_text)
        if not analysis["is_valid"]:
            st.error(analysis["validation_error"])
        else:
            _render_analysis(analysis)
    else:
        st.info(
            "Checkpoint 3 uses deterministic local analysis first. Live model "
            "analysis is connected after the response shape is stable."
        )

    columns = st.columns(len(page["sections"]))
    for column, section in zip(columns, page["sections"], strict=True):
        column.metric(section, "Pending")


def _render_analysis(analysis: dict[str, object]) -> None:
    st.subheader("Understanding summary")
    st.write(analysis["understanding_summary"])

    first, second, third = st.columns(3)
    first.metric(
        "Completeness",
        f"{analysis['completeness_score']}%",
        analysis["completeness_level"],
    )
    second.metric("Confidence", analysis["confidence_label"])
    third.metric("Mode", analysis["analysis_mode"])
    st.caption(analysis["confidence_reason"])

    st.subheader("Missing information")
    missing_information = analysis["missing_information"]
    if missing_information:
        st.dataframe(missing_information, hide_index=True, use_container_width=True)
    else:
        st.success("No major missing categories detected by deterministic checks.")

    st.subheader("Clarification questions")
    for question in analysis["clarification_questions"]:
        st.write(
            f"{question['question_id']} {question['severity']}: "
            f"{question['question']}"
        )

    if analysis["draft_allowed"]:
        st.info(
            "Draft generation can be offered next, but unresolved assumptions "
            "and open questions must stay visible."
        )


if __name__ == "__main__":
    main()
