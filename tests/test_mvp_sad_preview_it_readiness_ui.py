from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_sad_preview_ui_files_exist():
    expected_paths = [
        WEB_SRC / "lib" / "hooks" / "useSadSave.ts",
        WEB_SRC / "components" / "preview" / "PreviewPane.tsx",
        WEB_SRC / "components" / "chat" / "ChatPanel.tsx",
        WEB_SRC / "lib" / "api.ts",
    ]

    missing = [str(path.relative_to(ROOT)) for path in expected_paths if not path.exists()]

    assert missing == []


def test_sad_preview_ui_wires_backend_preview_and_user_friendly_sections():
    save = (WEB_SRC / "lib" / "hooks" / "useSadSave.ts").read_text(encoding="utf-8")
    pane = (WEB_SRC / "components" / "preview" / "PreviewPane.tsx").read_text(encoding="utf-8")
    chat = (WEB_SRC / "components" / "chat" / "ChatPanel.tsx").read_text(encoding="utf-8")
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")

    assert "generateSadPreview" in api
    assert "/sad/preview" in api
    assert "generateSadPreview" in save
    assert "Generate SAD preview" in chat
    assert "Draft-ready" in pane
    assert "Temporary — not saved yet" in pane
    assert "Assumptions we made" in pane
    assert "Questions to confirm with the business" in pane


def test_sad_preview_ui_keeps_it_readiness_collapsed_and_business_first():
    pane = (WEB_SRC / "components" / "preview" / "PreviewPane.tsx").read_text(encoding="utf-8")

    assert "Review readiness checklist" in pane
    assert "isDraftReady" in pane
    assert "it_readiness.checklist" in pane


def test_sad_preview_state_resets_when_analysis_changes():
    save = (WEB_SRC / "lib" / "hooks" / "useSadSave.ts").read_text(encoding="utf-8")

    assert "useEffect" in save
    assert "setPreviewResponse(null)" in save
    assert "analysisId" in save
