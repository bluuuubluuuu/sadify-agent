from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_drive_repo_ui_files_exist():
    expected_paths = [
        WEB_SRC / "components" / "DriveRepoPanel.tsx",
        WEB_SRC / "components" / "WorkspaceShell.tsx",
        WEB_SRC / "lib" / "api.ts",
        WEB_SRC / "lib" / "googleOAuth.ts",
    ]

    missing = [str(path.relative_to(ROOT)) for path in expected_paths if not path.exists()]

    assert missing == []


def test_drive_repo_ui_wires_oauth_code_model_and_disconnect():
    shell = (WEB_SRC / "components" / "WorkspaceShell.tsx").read_text(
        encoding="utf-8"
    )
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")
    panel = (WEB_SRC / "components" / "DriveRepoPanel.tsx").read_text(
        encoding="utf-8"
    )
    oauth = (WEB_SRC / "lib" / "googleOAuth.ts").read_text(encoding="utf-8")

    assert "DriveRepoPanel" in shell
    assert "connectDriveRepo" in api
    assert "disconnectDriveRepo" in api
    assert "/drive/repo/connect" in api
    assert "/drive/repo/disconnect" in api
    assert "Project repo" in panel
    assert "Connect Google Drive" in panel
    assert "Disconnect Google Drive" in panel
    assert "Configuration needed" in panel
    assert "NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID" in oauth
    assert "initCodeClient" in oauth
    assert "https://www.googleapis.com/auth/drive.file" in oauth
