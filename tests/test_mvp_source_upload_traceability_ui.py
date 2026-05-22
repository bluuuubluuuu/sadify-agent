from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_source_upload_ui_files_exist():
    expected_paths = [
        WEB_SRC / "components" / "SourceUploadPanel.tsx",
        WEB_SRC / "components" / "WorkspaceShell.tsx",
        WEB_SRC / "lib" / "api.ts",
    ]

    missing = [str(path.relative_to(ROOT)) for path in expected_paths if not path.exists()]

    assert missing == []


def test_source_upload_ui_wires_formdata_and_traceability_into_analysis():
    shell = (WEB_SRC / "components" / "WorkspaceShell.tsx").read_text(
        encoding="utf-8"
    )
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")
    panel = (WEB_SRC / "components" / "SourceUploadPanel.tsx").read_text(
        encoding="utf-8"
    )
    analysis_panel = (WEB_SRC / "components" / "AnalysisPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "SourceUploadPanel" in shell
    assert "setSourceUpload" in shell
    assert "sourceContext" in shell
    assert "sourceReferences" in shell
    assert "uploadSources" in api
    assert "/sources/upload" in api
    assert "new FormData()" in api
    assert '"Content-Type": "multipart/form-data"' not in api
    assert "Upload source files" in panel
    assert "Source traceability" in panel
    assert "Unsupported files" in panel
    assert "sourceContext" in analysis_panel
    assert "sourceReferences" in analysis_panel
