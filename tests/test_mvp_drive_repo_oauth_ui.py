from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_drive_repo_ui_files_exist():
    expected_paths = [
        WEB_SRC / "lib" / "hooks" / "useDriveRepo.ts",
        WEB_SRC / "components" / "shell" / "AccountMenu.tsx",
        WEB_SRC / "lib" / "api.ts",
        WEB_SRC / "lib" / "googleOAuth.ts",
    ]

    missing = [str(path.relative_to(ROOT)) for path in expected_paths if not path.exists()]

    assert missing == []


def test_drive_repo_ui_wires_oauth_code_model_and_disconnect():
    use_drive = (WEB_SRC / "lib" / "hooks" / "useDriveRepo.ts").read_text(encoding="utf-8")
    account = (WEB_SRC / "components" / "shell" / "AccountMenu.tsx").read_text(encoding="utf-8")
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")
    oauth = (WEB_SRC / "lib" / "googleOAuth.ts").read_text(encoding="utf-8")

    assert "connectDriveRepo" in api
    assert "disconnectDriveRepo" in api
    assert "/drive/repo/connect" in api
    assert "/drive/repo/disconnect" in api
    assert "connectDriveRepo" in use_drive
    assert "disconnectDriveRepo" in use_drive
    assert "requestDriveAuthorizationCode" in use_drive
    assert "Connect Google Drive" in account
    assert "Disconnect Drive" in account
    assert "NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID" in oauth
    assert "initCodeClient" in oauth
    assert "https://www.googleapis.com/auth/drive.file" in oauth
