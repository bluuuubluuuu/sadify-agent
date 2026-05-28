from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_project_ui_files_exist():
    expected_paths = [
        WEB_SRC / "components" / "ProjectPanel.tsx",
        WEB_SRC / "components" / "CreateProjectDialog.tsx",
        WEB_SRC / "lib" / "api.ts",
    ]

    missing = [str(path.relative_to(ROOT)) for path in expected_paths if not path.exists()]

    assert missing == []


def test_project_api_contract_is_wired_and_token_store_matches_backend():
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")

    assert "export type ProjectSummary" in api
    assert "export type ProjectListResponse" in api
    assert "export async function listProjects" in api
    assert "export async function createProject" in api
    assert "export async function switchProject" in api
    assert "/projects" in api
    assert "/projects/switch" in api
    assert '"secret_manager"' in api
    assert "active_project_id: string | null" in api
    assert "available_projects: ProjectSummary[]" in api


def test_workspace_mounts_project_panel_between_auth_and_drive_repo():
    shell = (WEB_SRC / "components" / "WorkspaceShell.tsx").read_text(
        encoding="utf-8"
    )

    assert 'from "./ProjectPanel"' in shell
    assert "const [driveRepo, setDriveRepo]" in shell
    assert "<ProjectPanel" in shell
    assert "repo={driveRepo}" in shell
    assert "onRepoChanged={setDriveRepo}" in shell
    assert "onProjectCreated={applyProjectCreated}" in shell
    assert shell.index("<AuthPanel />") < shell.index("<ProjectPanel")
    assert shell.index("<ProjectPanel") < shell.index("<DriveRepoPanel")


def test_project_panel_renders_refresh_switch_and_create_controls():
    panel = (WEB_SRC / "components" / "ProjectPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "listProjects" in panel
    assert "switchProject" in panel
    assert "CreateProjectDialog" in panel
    assert "No project selected" in panel
    assert "No projects yet" in panel
    assert "Refresh" in panel
    assert "Switch" in panel
    assert "New project" in panel


def test_sad_preview_project_required_opens_dialog_and_retries():
    panel = (WEB_SRC / "components" / "SadPreviewPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "CreateProjectDialog" in panel
    assert "PROJECT_REQUIRED" in panel
    assert "WIKI_PROJECT_REQUIRED" in panel
    assert "setPendingProjectAction" in panel
    assert "retryPendingProjectAction" in panel
    assert "suggestProjectName" in panel
    assert "onProjectCreated" in panel

