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

_MISSING_INFORMATION_COLUMN_LABELS = {
    "area": "Area",
    "priority": "Priority",
    "what_is_unclear": "What is unclear",
    "why_this_matters": "Why this matters",
    "what_to_answer_next": "What to answer next",
}


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
            "Turn a messy business request into clear questions and a "
            "developer-ready system draft."
        ),
        "project": config.google_cloud_project,
        "model": config.sadify_model,
        "model_provider": config.sadify_model_provider,
        "model_routes": model_routes,
        "provider_statuses": provider_statuses,
        "sections": [
            "Business request",
            "Readiness",
            "Questions",
            "System draft",
            "Export",
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
        st.subheader("Technical setup")
        st.write(f"Project: `{page['project']}`")
        st.write(f"Provider: `{page['model_provider']}`")
        st.write(f"Model: `{page['model']}`")
        st.write(f"Environment: `{config.sadify_env}`")
        st.subheader("Model setup")
        for route in page["model_routes"]:
            st.write(
                f"{route['task']}: `{route['provider']}` / `{route['model']}`"
            )
        st.subheader("Readiness checks")
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
        "Tell us what is happening in the business",
        placeholder=(
            "Example: Our warehouse team loses track of stock movement "
            "between receiving, picking, and dispatch..."
        ),
        height=180,
    )

    if st.button("Check what is still unclear", type="primary"):
        analysis = build_analysis_view_model(requirement_text)
        if not analysis["is_valid"]:
            st.error(analysis["validation_error"])
        else:
            _render_analysis(analysis, st)
    else:
        st.info(
            "SADify first checks whether the business request has enough "
            "detail. Draft generation comes after open questions are visible."
        )

    columns = st.columns(len(page["sections"]))
    for column, section in zip(columns, page["sections"], strict=True):
        column.metric(section, "Pending")


def _render_analysis(analysis: dict[str, object], st_module) -> None:
    st_module.subheader("What SADify understands")
    st_module.write(analysis["understanding_summary"])

    first, second, third = st_module.columns(3)
    first.metric(
        "Readiness",
        f"{analysis['completeness_score']}%",
        analysis["completeness_level"],
    )
    second.metric("Confidence", analysis["confidence_label"])
    third.metric("Current mode", analysis["analysis_mode"])
    st_module.caption(analysis["confidence_reason"])

    st_module.subheader("What we still need to know")
    missing_information = analysis["missing_information"]
    if missing_information:
        st_module.dataframe(
            _business_missing_information_rows(missing_information),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st_module.success(
            "This request includes the main business details SADify checks for."
        )

    st_module.subheader("Questions to confirm with the business")
    for question in analysis["clarification_questions"]:
        st_module.write(
            f"{question['question_id']} {question['priority']}: "
            f"{question['question']}"
        )

    if analysis["draft_allowed"]:
        st_module.info(
            "A draft can be prepared next, but any open assumptions should "
            "stay visible."
        )


def _business_missing_information_rows(
    missing_information: list[dict[str, str]],
) -> list[dict[str, str]]:
    return [
        {
            display_label: row[source_key]
            for source_key, display_label in _MISSING_INFORMATION_COLUMN_LABELS.items()
        }
        for row in missing_information
    ]


if __name__ == "__main__":
    main()
