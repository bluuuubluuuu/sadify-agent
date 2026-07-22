from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web" / "src"


def _read(relative_path: str) -> str:
    path = WEB / relative_path
    assert path.exists(), f"missing frontend source: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def test_api_exposes_delete_project_with_backend_error_handling():
    source = _read("lib/api.ts")

    assert "export async function deleteProject" in source
    assert 'method: "DELETE"' in source
    assert "new BackendApiError" in source


def test_confirm_dialog_mentions_drive_trash():
    source = _read("components/shell/ConfirmDialog.tsx")

    assert "Trash" in source
    assert "busy" in source
    assert "Cancel" in source


def test_project_list_has_delete_control_and_handler():
    source = _read("components/shell/ProjectList.tsx")

    assert "onDelete" in source
    assert "Delete project" in source
    assert "projectDeleteButton" in source


def test_sidebar_passes_delete_handler_to_project_list():
    source = _read("components/shell/Sidebar.tsx")

    assert "onDeleteProject" in source
    assert "onDelete={onDeleteProject}" in source


def test_workspace_refetches_canonical_repo_and_resets_deleted_active_project():
    source = _read("components/WorkspaceV2.tsx")

    assert "deleteProject" in source
    assert "await getDriveRepoStatus(idToken)" in source
    assert "setDriveRepo(updatedRepo)" in source
    assert "deletedActiveProject" in source
    assert (
        "const deletedActiveProject =\n"
        "      project.project_id === driveRepo?.active_project_id;"
    ) in source
    assert "qna.reset()" in source
    assert "sources.reset()" in source
    assert "sadSave.dismissPreview()" in source
