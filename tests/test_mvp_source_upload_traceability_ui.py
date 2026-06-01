from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_source_upload_ui_files_exist():
    expected_paths = [
        WEB_SRC / "lib" / "hooks" / "useSources.ts",
        WEB_SRC / "components" / "chat" / "AttachChips.tsx",
        WEB_SRC / "lib" / "api.ts",
    ]

    missing = [str(path.relative_to(ROOT)) for path in expected_paths if not path.exists()]

    assert missing == []


def test_source_upload_ui_wires_formdata_and_traceability_into_analysis():
    use_sources = (WEB_SRC / "lib" / "hooks" / "useSources.ts").read_text(encoding="utf-8")
    attach = (WEB_SRC / "components" / "chat" / "AttachChips.tsx").read_text(encoding="utf-8")
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")
    use_qna = (WEB_SRC / "lib" / "hooks" / "useQnA.ts").read_text(encoding="utf-8")
    workspace = (WEB_SRC / "components" / "WorkspaceV2.tsx").read_text(encoding="utf-8")

    assert "uploadSources" in api
    assert "/sources/upload" in api
    assert "new FormData()" in api
    assert '"Content-Type": "multipart/form-data"' not in api
    assert "uploadSources" in use_sources
    assert "sourceReferences" in use_sources
    assert "analysisContext" in use_sources
    assert "original_file_name" in attach
    assert "sourceContext" in use_qna
    assert "sourceReferences" in use_qna
    assert "useSources" in workspace
