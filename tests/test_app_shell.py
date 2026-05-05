from sadify.app import (
    _render_analysis,
    build_analysis_view_model,
    build_page_model,
    build_uploaded_sources_view_model,
    combine_requirement_context,
)
from sadify.config import AppConfig
from sadify.extractors.business_files import ExtractedRequirementSource


class FakeStreamlit:
    def __init__(self):
        self.calls = []

    def subheader(self, value):
        self.calls.append(("subheader", value))

    def write(self, *values):
        self.calls.append(("write", values))

    def columns(self, count):
        self.calls.append(("columns", count))
        return [FakeColumn(self.calls), FakeColumn(self.calls), FakeColumn(self.calls)]

    def caption(self, value):
        self.calls.append(("caption", value))

    def dataframe(self, value, *, hide_index, use_container_width):
        self.calls.append(
            ("dataframe", value, hide_index, use_container_width)
        )

    def success(self, value):
        self.calls.append(("success", value))

    def info(self, value):
        self.calls.append(("info", value))


class FakeColumn:
    def __init__(self, calls):
        self.calls = calls

    def metric(self, *values):
        self.calls.append(("metric", values))


class FakeUploadedFile:
    def __init__(self, name, content):
        self.name = name
        self._content = content

    def getvalue(self):
        return self._content


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
    assert "business request" in page["tagline"]
    assert page["model"] == "gemini-2.5-flash"
    assert page["model_provider"] == "google"
    assert page["project"] == "sadify"
    assert page["sections"] == [
        "Business request",
        "Readiness",
        "Questions",
        "System draft",
        "Export",
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
        "What SADify understands",
        "Readiness",
        "Confidence",
        "What we still need to know",
        "Questions to confirm",
        "Draft option",
    ]
    assert view_model["analysis_mode"] == "deterministic"


def test_render_analysis_uses_provided_streamlit_module():
    view_model = build_analysis_view_model(
        "Warehouse operators forget to update stock records when items move "
        "between locations."
    )
    fake_st = FakeStreamlit()

    _render_analysis(view_model, fake_st)

    assert ("subheader", "What SADify understands") in fake_st.calls
    assert ("subheader", "What we still need to know") in fake_st.calls


def test_render_analysis_uses_business_column_headings():
    view_model = build_analysis_view_model("We need a better system.")
    fake_st = FakeStreamlit()

    _render_analysis(view_model, fake_st)

    dataframe_call = next(call for call in fake_st.calls if call[0] == "dataframe")
    first_row = dataframe_call[1][0]
    assert list(first_row) == [
        "Area",
        "Priority",
        "What is unclear",
        "Why this matters",
        "What to answer next",
    ]


def test_build_uploaded_sources_view_model_extracts_files_and_reports_errors():
    view_model = build_uploaded_sources_view_model(
        [
            FakeUploadedFile(
                "warehouse.txt",
                b"Warehouse staff need to record stock movement.",
            ),
            FakeUploadedFile("photo.png", b"unsupported"),
        ]
    )

    assert view_model["sources"][0]["filename"] == "warehouse.txt"
    assert view_model["sources"][0]["file_type"] == "txt"
    assert "stock movement" in view_model["sources"][0]["normalized_text"]
    assert view_model["errors"] == [
        {
            "filename": "photo.png",
            "message": (
                "Unsupported file type '.png' for photo.png. "
                "Supported files: MD, TXT, PDF, DOCX, XLSX, CSV."
            ),
        }
    ]


def test_combine_requirement_context_keeps_manual_text_before_file_context():
    combined = combine_requirement_context(
        "Manual note from user.",
        [
            ExtractedRequirementSource(
                filename="warehouse.txt",
                file_type="txt",
                normalized_text="File note about approval.",
                metadata={},
            )
        ],
    )

    assert combined == (
        "Manual note from user.\n\n"
        "Source file: warehouse.txt\n"
        "File note about approval."
    )
