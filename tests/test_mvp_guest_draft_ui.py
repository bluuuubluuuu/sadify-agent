from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_guest_draft_ui_files_exist():
    expected_paths = [
        WEB_SRC / "components" / "DraftPanel.tsx",
        WEB_SRC / "lib" / "api.ts",
    ]

    missing = [str(path.relative_to(ROOT)) for path in expected_paths if not path.exists()]

    assert missing == []


def test_guest_draft_ui_exposes_safe_copy_workflow():
    shell = (WEB_SRC / "components" / "WorkspaceShell.tsx").read_text(
        encoding="utf-8"
    )
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")
    panel = (WEB_SRC / "components" / "DraftPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "DraftPanel" in shell
    assert "createGuestDraft" in api
    assert "migrateGuestDraft" in api
    assert "Start guest draft" in panel
    assert "Copy to signed-in project" in panel
    assert "Guest draft kept for audit" in panel
