from __future__ import annotations

from pathlib import Path
import sys

from dotenv import load_dotenv

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sadify.config import AppConfig, load_config
from sadify.logging_config import configure_logging


def build_page_model(config: AppConfig) -> dict[str, object]:
    return {
        "title": "SADify",
        "tagline": (
            "An AI system analyst that turns messy operational requirements "
            "into clarified, developer-ready SAD outputs."
        ),
        "project": config.google_cloud_project,
        "model": config.sadify_model,
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
        st.write(f"Model: `{page['model']}`")
        st.write(f"Environment: `{config.sadify_env}`")
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

    st.text_area(
        "Describe the operational problem",
        placeholder=(
            "Example: Our warehouse team keeps losing track of stock movement..."
        ),
        height=180,
    )

    st.button("Analyze requirement", type="primary", disabled=True)
    st.info(
        "Checkpoint 1 scaffold is ready. Requirement analysis is implemented "
        "in the next checkpoints."
    )

    columns = st.columns(len(page["sections"]))
    for column, section in zip(columns, page["sections"], strict=True):
        column.metric(section, "Pending")


if __name__ == "__main__":
    main()
