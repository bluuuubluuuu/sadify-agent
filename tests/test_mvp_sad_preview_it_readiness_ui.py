from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_sad_preview_ui_files_exist():
    expected_paths = [
        WEB_SRC / "components" / "SadPreviewPanel.tsx",
        WEB_SRC / "components" / "WorkspaceShell.tsx",
        WEB_SRC / "lib" / "api.ts",
    ]

    missing = [str(path.relative_to(ROOT)) for path in expected_paths if not path.exists()]

    assert missing == []


def test_sad_preview_ui_wires_backend_preview_and_user_friendly_sections():
    shell = (WEB_SRC / "components" / "WorkspaceShell.tsx").read_text(
        encoding="utf-8"
    )
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")
    panel = (WEB_SRC / "components" / "SadPreviewPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "SadPreviewPanel" in shell
    assert "generateSadPreview" in api
    assert "/sad/preview" in api
    assert "Generate SAD preview" in panel
    assert "Temporary preview" in panel
    assert "Later IT readiness" not in panel
    assert "Deeper implementation check" not in panel
    assert "Assumptions" in panel
    assert "Open questions" in panel
    assert "Source refs" in panel
    assert "Tracking status" in panel


def test_sad_preview_ui_hides_fallback_diagnostics_from_normal_view():
    panel = (WEB_SRC / "components" / "SadPreviewPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "Draft-ready" in panel
    assert "Layer 1 preview" in panel
    assert "Later implementation review" in panel
    assert "Tracking status" in panel
    assert "AI preview formatting" not in panel
    assert "Generated safe local preview" not in panel


def test_sad_preview_ui_keeps_valid_preview_it_readiness_and_source_refs_collapsed():
    panel = (WEB_SRC / "components" / "SadPreviewPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "isDraftReadyPreview" in panel
    assert '<details className="it-readiness">' in panel
    assert "!isFallbackPreview && section.source_references.length > 0" not in panel
    assert "Draft-ready" in panel
    assert "Layer 1 preview" in panel


def test_sad_preview_ui_resets_stale_preview_and_hides_internal_tracking_paths():
    panel = (WEB_SRC / "components" / "SadPreviewPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "useEffect" in panel
    assert "setPreviewResponse(null)" in panel
    assert (
        'setMessage("Temporary preview only. No Google Doc or Drive file is saved here.")'
        in panel
    )
    assert 'path.startsWith("_SADify/")' in panel
    assert "Temporary draft state saved." in panel
