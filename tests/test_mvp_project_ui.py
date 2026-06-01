from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_project_ui_files_exist():
    expected_paths = [
        WEB_SRC / "lib" / "hooks" / "useProjects.ts",
        WEB_SRC / "lib" / "hooks" / "useSaveHistory.ts",
        WEB_SRC / "components" / "shell" / "ProjectList.tsx",
        WEB_SRC / "components" / "shell" / "SaveHistory.tsx",
        WEB_SRC / "components" / "shell" / "CreateProjectDialog.tsx",
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


def test_project_list_and_hooks_render_switch_and_create_controls():
    use_projects = (WEB_SRC / "lib" / "hooks" / "useProjects.ts").read_text(encoding="utf-8")
    project_list = (WEB_SRC / "components" / "shell" / "ProjectList.tsx").read_text(encoding="utf-8")
    sidebar = (WEB_SRC / "components" / "shell" / "Sidebar.tsx").read_text(encoding="utf-8")

    assert "listProjects" in use_projects
    assert "switchProject" in use_projects
    assert "createProject" in use_projects
    assert "New project" in project_list
    assert "onSwitch" in project_list
    assert "useProjects" in sidebar


def test_sad_preview_project_required_opens_dialog_and_retries():
    save = (WEB_SRC / "lib" / "hooks" / "useSadSave.ts").read_text(encoding="utf-8")
    workspace = (WEB_SRC / "components" / "WorkspaceV2.tsx").read_text(encoding="utf-8")

    assert "PROJECT_REQUIRED" in save
    assert "WIKI_PROJECT_REQUIRED" in save
    assert "pendingProjectAction" in save
    assert "suggestProjectName" in save
    assert "CreateProjectDialog" in workspace


def test_api_ts_exports_list_project_saves():
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")

    assert "export type SadSaveSummary" in api
    assert "export type ProjectSavesResponse" in api
    assert "export async function listProjectSaves" in api
    assert "/projects/${projectId}/saves" in api


def test_save_history_renders_rows_and_refreshes():
    use_history = (WEB_SRC / "lib" / "hooks" / "useSaveHistory.ts").read_text(encoding="utf-8")
    save_history = (WEB_SRC / "components" / "shell" / "SaveHistory.tsx").read_text(encoding="utf-8")
    workspace = (WEB_SRC / "components" / "WorkspaceV2.tsx").read_text(encoding="utf-8")

    assert "listProjectSaves" in use_history
    assert "activeProjectId" in use_history
    assert "refreshKey" in use_history
    assert "No saves yet" in use_history
    assert "save.save_id" in save_history
    assert "doc_url" in save_history
    assert "historyRefreshKey" in workspace
