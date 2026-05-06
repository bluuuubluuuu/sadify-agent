from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Protocol, Sequence

from dotenv import load_dotenv

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sadify.config import AppConfig, load_config
from sadify.extractors.business_files import (
    ExtractedRequirementSource,
    FileExtractionError,
    extract_requirement_source,
)
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


class UploadedBusinessFile(Protocol):
    name: str

    def getvalue(self) -> bytes: ...


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


def build_uploaded_sources_view_model(
    uploaded_files: Sequence[UploadedBusinessFile] | None,
) -> dict[str, Any]:
    source_objects: list[ExtractedRequirementSource] = []
    errors: list[dict[str, str]] = []

    for uploaded_file in uploaded_files or []:
        try:
            source_objects.append(
                extract_requirement_source(
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                )
            )
        except FileExtractionError as exc:
            errors.append(
                {
                    "filename": uploaded_file.name,
                    "message": str(exc),
                }
            )

    return {
        "source_objects": source_objects,
        "sources": [source.to_display_dict() for source in source_objects],
        "source_summaries": _source_summary_rows(source_objects),
        "errors": errors,
    }


def combine_requirement_context(
    requirement_text: str,
    extracted_sources: Sequence[ExtractedRequirementSource],
) -> str:
    parts = [requirement_text.strip()] if requirement_text.strip() else []
    for source in extracted_sources:
        parts.append(
            f"Source file: {source.filename}\n{source.normalized_text}"
        )
    return "\n\n".join(parts)


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
    uploaded_files = st.file_uploader(
        "Add business files",
        type=["md", "txt", "pdf", "docx", "xlsx", "csv"],
        accept_multiple_files=True,
    )
    uploaded_sources = build_uploaded_sources_view_model(uploaded_files)
    _render_uploaded_sources(uploaded_sources, st)

    if st.button("Check what is still unclear", type="primary"):
        analysis_context = combine_requirement_context(
            requirement_text,
            uploaded_sources["source_objects"],
        )
        analysis = build_analysis_view_model(analysis_context)
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
    if analysis["evidence_summary"]:
        with st_module.expander("Why this score", expanded=False) as evidence_panel:
            evidence_panel.caption(analysis["scoring_basis"])
            for evidence in analysis["evidence_summary"]:
                evidence_panel.write(evidence)

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


def _source_summary_rows(
    sources: Sequence[ExtractedRequirementSource],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in sources:
        rows.append(
            {
                "File": source.filename,
                "Type": source.file_type.upper(),
                "Readable content": _source_size_label(source),
            }
        )
    return rows


def _source_size_label(source: ExtractedRequirementSource) -> str:
    metadata = source.metadata
    if source.file_type == "pdf":
        return f"{metadata['page_count']} page(s)"
    if source.file_type == "docx":
        return f"{metadata['paragraph_count']} paragraph(s)"
    if source.file_type == "xlsx":
        return f"{metadata['sheet_count']} sheet(s)"
    if source.file_type == "csv":
        return f"{metadata['row_count']} row(s)"
    return f"{metadata['character_count']} character(s)"


def _render_uploaded_sources(uploaded_sources: dict[str, Any], st_module) -> None:
    if uploaded_sources["source_summaries"]:
        st_module.subheader("Files SADify can read")
        st_module.dataframe(
            uploaded_sources["source_summaries"],
            hide_index=True,
            use_container_width=True,
        )
        with st_module.expander("Extracted file context", expanded=False):
            for source in uploaded_sources["sources"]:
                st_module.caption(f"{source['filename']} ({source['file_type']})")
                st_module.text(source["normalized_text"])

    for error in uploaded_sources["errors"]:
        st_module.error(f"{error['filename']}: {error['message']}")


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
