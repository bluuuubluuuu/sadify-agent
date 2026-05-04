from sadify.app import build_analysis_view_model, build_page_model
from sadify.config import AppConfig


def test_build_page_model_describes_first_screen():
    config = AppConfig(
        google_cloud_project="sadify",
        google_cloud_location="asia-southeast1",
        google_genai_use_vertexai=True,
        sadify_model="gemini-2.5-flash",
        sadify_model_provider="google",
        sadify_final_sad_provider="google",
        sadify_final_sad_model="gemini-2.5-flash",
        sadify_fallback_provider=None,
        sadify_fallback_model=None,
        openai_compatible_base_url=None,
        ollama_base_url=None,
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
    assert page["model_provider"] == "google"
    assert page["project"] == "sadify"
    assert page["sections"] == [
        "Requirement intake",
        "Completeness and confidence",
        "Clarification questions",
        "SAD preview",
        "Exports",
    ]
    assert page["diagnostics"]["drive_folder_configured"] is True
    assert "drive-folder-id" not in str(page["diagnostics"])
    assert page["model_routes"][0]["model"] == "gemini-2.5-flash"
    assert page["model_routes"][0]["provider"] == "google"


def test_build_analysis_view_model_returns_validation_error_for_empty_input():
    view_model = build_analysis_view_model(" ")

    assert view_model["is_valid"] is False
    assert view_model["validation_error"] == (
        "Enter an operational problem before analysis."
    )


def test_build_analysis_view_model_returns_first_response_sections():
    view_model = build_analysis_view_model(
        "Warehouse operators forget to update stock records when items move "
        "between locations."
    )

    assert view_model["is_valid"] is True
    assert view_model["sections"] == [
        "Understanding summary",
        "Completeness",
        "Confidence",
        "Missing information",
        "Clarification questions",
        "Draft option",
    ]
    assert view_model["analysis_mode"] == "deterministic"
