from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_guest_draft_ui_files_exist():
    expected_paths = [
        WEB_SRC / "components" / "WorkspaceV2.tsx",
        WEB_SRC / "lib" / "api.ts",
    ]

    missing = [str(path.relative_to(ROOT)) for path in expected_paths if not path.exists()]

    assert missing == []


def test_guest_path_and_migration_api_available():
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")
    workspace = (WEB_SRC / "components" / "WorkspaceV2.tsx").read_text(encoding="utf-8")

    # Guest draft + migration API remain available for future use.
    assert "createGuestDraft" in api
    assert "migrateGuestDraft" in api
    # Simplified guest path: type and run the analysis, sign in to save.
    assert "Sign in with Google to save" in workspace
    assert "startAnalysis" in workspace
