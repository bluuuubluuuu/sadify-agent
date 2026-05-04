from sadify.app import build_page_model
from sadify.config import AppConfig


def test_build_page_model_describes_first_screen():
    config = AppConfig(
        google_cloud_project="sadify",
        google_cloud_location="asia-southeast1",
        google_genai_use_vertexai=True,
        sadify_model="gemini-2.5-flash",
        sadify_env="local",
        sadify_log_level="INFO",
        sadify_drive_root_folder_id="drive-folder-id",
        sadify_runtime_service_account=(
            "sadify-agent-sa@sadify.iam.gserviceaccount.com"
        ),
    )

    page = build_page_model(config)

    assert page["title"] == "SADify"
    assert "AI system analyst" in page["tagline"]
    assert page["model"] == "gemini-2.5-flash"
    assert page["project"] == "sadify"
    assert page["sections"] == [
        "Requirement intake",
        "Completeness and confidence",
        "Clarification questions",
        "SAD preview",
        "Exports",
    ]
