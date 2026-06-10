from datetime import UTC, datetime

from fastapi.testclient import TestClient

from sadify_api.config import ApiConfig
from sadify_api.main import create_app
from sadify_api.schemas import SadPreviewResponse
from sadify_api.services.auth import VerifiedFirebaseUser
from sadify_api.services.drive_client import DriveFolderRef
from sadify_api.services.drive_repo import DriveRepoRepository
from sadify_api.services.projects import ProjectRepository
from sadify_api.services.sad_preview import SadPreviewRepository
from sadify_api.services.sad_save import SadSaveRepository
from tests.api.test_sad_preview import VALID_PREVIEW


class AcceptingTokenVerifier:
    def verify_id_token(self, id_token: str) -> VerifiedFirebaseUser:
        return VerifiedFirebaseUser(
            uid="firebase-uid-001",
            email="owner@example.com",
            display_name="Project Owner",
            provider="firebase",
        )


def test_create_project_assigns_pr_id_starting_at_one():
    repository = ProjectRepository()

    project = repository.create_project(
        grant_id="DG-000001",
        name="Laundry Workflow",
        drive_folder_id="folder-001",
    )

    assert project.project_id == "PR-000001"
    assert project.name == "Laundry Workflow"
    assert project.drive_folder_id == "folder-001"
    assert project.github_repo is None


def test_set_github_repo_persists_on_project():
    repository = ProjectRepository()
    repository.create_project(
        grant_id="DG-000001",
        name="Laundry Workflow",
        drive_folder_id="folder-001",
    )

    updated = repository.set_github_repo("DG-000001", "PR-000001", "octocat/laundry")

    assert updated is not None
    assert updated.github_repo == "octocat/laundry"
    assert repository.get_project("DG-000001", "PR-000001").github_repo == "octocat/laundry"
    assert repository.set_github_repo("DG-000001", "PR-MISSING", "octocat/x") is None


def test_create_project_increments_id_per_grant():
    repository = ProjectRepository()

    first = repository.create_project(
        grant_id="DG-000001",
        name="Project A",
        drive_folder_id="folder-a",
    )
    second = repository.create_project(
        grant_id="DG-000001",
        name="Project B",
        drive_folder_id="folder-b",
    )
    other_grant = repository.create_project(
        grant_id="DG-000002",
        name="Project C",
        drive_folder_id="folder-c",
    )

    assert first.project_id == "PR-000001"
    assert second.project_id == "PR-000002"
    assert other_grant.project_id == "PR-000001"


def test_create_project_is_idempotent_for_same_normalized_name():
    repository = ProjectRepository()

    first = repository.create_project(
        grant_id="DG-000001",
        name="Laundry Workflow",
        drive_folder_id="folder-001",
    )
    second = repository.create_project(
        grant_id="DG-000001",
        name="  laundry workflow  ",
        drive_folder_id="folder-ignored",
    )

    assert second == first
    assert repository.list_projects("DG-000001") == [first]


def test_get_project_by_id_returns_record():
    repository = ProjectRepository()
    created = repository.create_project(
        grant_id="DG-000001",
        name="Laundry Workflow",
        drive_folder_id="folder-001",
    )

    assert repository.get_project("DG-000001", "PR-000001") == created


def test_get_project_by_id_returns_none_when_unknown():
    repository = ProjectRepository()

    assert repository.get_project("DG-000001", "PR-999999") is None


def test_list_projects_for_grant_returns_in_creation_order():
    repository = ProjectRepository()
    first = repository.create_project(
        grant_id="DG-000001",
        name="Project A",
        drive_folder_id="folder-a",
    )
    second = repository.create_project(
        grant_id="DG-000001",
        name="Project B",
        drive_folder_id="folder-b",
    )
    repository.create_project(
        grant_id="DG-000002",
        name="Other",
        drive_folder_id="folder-c",
    )

    assert repository.list_projects("DG-000001") == [first, second]


def test_per_project_counter_starts_at_one():
    repository = ProjectRepository()
    project = repository.create_project(
        grant_id="DG-000001",
        name="Laundry Workflow",
        drive_folder_id="folder-001",
    )

    assert repository.next_counter("DG-000001", project.project_id, "sad_save") == 1


def test_per_project_counter_increments_independently_per_project():
    repository = ProjectRepository()
    first = repository.create_project(
        grant_id="DG-000001",
        name="Project A",
        drive_folder_id="folder-a",
    )
    second = repository.create_project(
        grant_id="DG-000001",
        name="Project B",
        drive_folder_id="folder-b",
    )

    assert repository.next_counter("DG-000001", first.project_id, "sad_save") == 1
    assert repository.next_counter("DG-000001", first.project_id, "sad_save") == 2
    assert repository.next_counter("DG-000001", second.project_id, "sad_save") == 1


def test_sync_from_drive_creates_records_for_unknown_drive_folders():
    repository = ProjectRepository()
    existing = repository.create_project(
        grant_id="DG-000001",
        name="Existing",
        drive_folder_id="folder-existing",
    )
    folders = [
        DriveFolderRef(
            folder_id="folder-existing",
            name="Existing Renamed In Drive",
            created_time=datetime(2026, 5, 28, 10, 0, tzinfo=UTC),
            web_view_link=None,
        ),
        DriveFolderRef(
            folder_id="folder-new",
            name="New From Drive",
            created_time=datetime(2026, 5, 28, 11, 0, tzinfo=UTC),
            web_view_link=None,
        ),
    ]

    projects = repository.sync_from_drive(
        grant_id="DG-000001",
        drive_folders=folders,
    )

    assert projects[0] == existing
    assert projects[1].project_id == "PR-000002"
    assert projects[1].name == "New From Drive"
    assert projects[1].created_at == datetime(2026, 5, 28, 11, 0, tzinfo=UTC)


def test_list_projects_returns_empty_for_first_time_connect():
    client, _drive_repo, _project_repo = _client_with_repos()
    _connect_repo(client)

    response = client.get("/projects", headers=_auth_header())

    assert response.status_code == 200
    assert response.json() == {
        "active_project_id": None,
        "active_project_name": None,
        "projects": [],
    }


def test_create_project_invalid_name_returns_400():
    client, _drive_repo, _project_repo = _client_with_repos()
    _connect_repo(client)

    response = client.post(
        "/projects",
        headers=_auth_header(),
        json={"name": "Bad/Name"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "PROJECT_NAME_INVALID"


def test_local_mode_create_project_uses_fake_folder_id():
    client, _drive_repo, _project_repo = _client_with_repos()
    _connect_repo(client)

    response = client.post(
        "/projects",
        headers=_auth_header(),
        json={"name": "Laundry Workflow"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["project_id"] == "PR-000001"
    assert payload["project"]["drive_folder_id"] == "LOCAL-PROJECT-FOLDER-000001"
    assert payload["active_project_id"] == "PR-000001"


def test_create_project_sets_record_as_active():
    client, drive_repo, _project_repo = _client_with_repos()
    _connect_repo(client)

    response = client.post(
        "/projects",
        headers=_auth_header(),
        json={"name": "Laundry Workflow"},
    )

    assert response.status_code == 200
    repo = drive_repo.get_active_repo("firebase-uid-001")
    assert repo is not None
    assert repo.active_project_id == "PR-000001"
    assert repo.active_project_name == "Laundry Workflow"
    assert [project.project_id for project in repo.available_projects] == ["PR-000001"]


def test_create_project_collision_returns_existing_idempotent():
    client, _drive_repo, _project_repo = _client_with_repos()
    _connect_repo(client)

    first = client.post(
        "/projects",
        headers=_auth_header(),
        json={"name": "Laundry Workflow"},
    )
    second = client.post(
        "/projects",
        headers=_auth_header(),
        json={"name": " laundry workflow "},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["project"]["project_id"] == first.json()["project"]["project_id"]
    assert second.json()["project"]["drive_folder_id"] == first.json()["project"][
        "drive_folder_id"
    ]


def test_switch_project_updates_active_state():
    client, drive_repo, _project_repo = _client_with_repos()
    _connect_repo(client)
    first = client.post(
        "/projects",
        headers=_auth_header(),
        json={"name": "Project A"},
    ).json()["project"]
    second = client.post(
        "/projects",
        headers=_auth_header(),
        json={"name": "Project B"},
    ).json()["project"]

    response = client.post(
        "/projects/switch",
        headers=_auth_header(),
        json={"project_id": first["project_id"]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "active_project_id": "PR-000001",
        "active_project_name": "Project A",
    }
    repo = drive_repo.get_active_repo("firebase-uid-001")
    assert repo is not None
    assert repo.active_project_id == first["project_id"]
    assert repo.active_project_name == "Project A"
    assert second["project_id"] == "PR-000002"


def test_switch_project_unknown_returns_404():
    client, _drive_repo, _project_repo = _client_with_repos()
    _connect_repo(client)

    response = client.post(
        "/projects/switch",
        headers=_auth_header(),
        json={"project_id": "PR-999999"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "PROJECT_NOT_FOUND"


def test_all_endpoints_block_unsigned():
    client, _drive_repo, _project_repo = _client_with_repos()

    responses = [
        client.get("/projects"),
        client.post("/projects", json={"name": "Project A"}),
        client.post("/projects/switch", json={"project_id": "PR-000001"}),
    ]

    assert [response.status_code for response in responses] == [401, 401, 401]


def test_all_endpoints_block_when_no_active_repo():
    client, _drive_repo, _project_repo = _client_with_repos()

    responses = [
        client.get("/projects", headers=_auth_header()),
        client.post(
            "/projects",
            headers=_auth_header(),
            json={"name": "Project A"},
        ),
        client.post(
            "/projects/switch",
            headers=_auth_header(),
            json={"project_id": "PR-000001"},
        ),
    ]

    assert [response.status_code for response in responses] == [409, 409, 409]
    assert all(
        response.json()["detail"]["code"] == "PROJECT_REPO_REQUIRED"
        for response in responses
    )


def test_list_project_saves_returns_empty_for_new_project():
    client, _drive_repo, _project_repo, _preview_repo, _save_repo = (
        _client_with_history_repos()
    )
    _connect_repo(client)
    project = client.post(
        "/projects",
        headers=_auth_header(),
        json={"name": "Laundry Workflow"},
    ).json()["project"]

    response = client.get(
        f"/projects/{project['project_id']}/saves",
        headers=_auth_header(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "project_id": "PR-000001",
        "project_name": "Laundry Workflow",
        "saves": [],
    }


def test_list_project_saves_returns_saves_in_descending_order():
    client, drive_repo, _project_repo, preview_repo, save_repo = (
        _client_with_history_repos()
    )
    _connect_repo(client)
    project = client.post(
        "/projects",
        headers=_auth_header(),
        json={"name": "Laundry Workflow"},
    ).json()["project"]
    older = _direct_save_for_project(
        drive_repo,
        preview_repo,
        save_repo,
        project_id=project["project_id"],
        saved_at=datetime(2026, 5, 28, 9, 0, tzinfo=UTC),
    )
    newer = _direct_save_for_project(
        drive_repo,
        preview_repo,
        save_repo,
        project_id=project["project_id"],
        saved_at=datetime(2026, 5, 28, 11, 0, tzinfo=UTC),
    )

    response = client.get(
        f"/projects/{project['project_id']}/saves",
        headers=_auth_header(),
    )

    assert response.status_code == 200
    save_ids = [save["save_id"] for save in response.json()["saves"]]
    assert save_ids == [newer.save_id, older.save_id]


def test_list_project_saves_includes_doc_url_and_change_summary():
    client, drive_repo, _project_repo, preview_repo, save_repo = (
        _client_with_history_repos()
    )
    _connect_repo(client)
    project = client.post(
        "/projects",
        headers=_auth_header(),
        json={"name": "Laundry Workflow"},
    ).json()["project"]
    record = _direct_save_for_project(
        drive_repo,
        preview_repo,
        save_repo,
        project_id=project["project_id"],
    )

    response = client.get(
        f"/projects/{project['project_id']}/saves",
        headers=_auth_header(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["saves"][0]["save_id"] == record.save_id
    assert payload["saves"][0]["preview_id"] == record.preview_id
    assert payload["saves"][0]["doc_url"] == record.sad_doc.url
    assert payload["saves"][0]["doc_path"] == record.sad_doc.path
    assert payload["saves"][0]["title"] == record.sad_doc.title
    assert payload["saves"][0]["change_summary"] == record.change_summary
    assert payload["saves"][0]["source_ids"] == []


def test_list_project_saves_blocks_unsigned():
    client, _drive_repo, _project_repo, _preview_repo, _save_repo = (
        _client_with_history_repos()
    )

    response = client.get("/projects/PR-000001/saves")

    assert response.status_code == 401
    assert response.json()["detail"] == {
        "code": "PROJECT_AUTH_REQUIRED",
        "message": "Sign in to view project history.",
    }


def test_list_project_saves_blocks_without_active_repo():
    client, _drive_repo, _project_repo, _preview_repo, _save_repo = (
        _client_with_history_repos()
    )

    response = client.get("/projects/PR-000001/saves", headers=_auth_header())

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "PROJECT_REPO_REQUIRED"


def test_list_project_saves_blocks_when_repo_disconnected():
    client, _drive_repo, _project_repo, _preview_repo, _save_repo = (
        _client_with_history_repos()
    )
    _connect_repo(client)
    client.post("/drive/repo/disconnect", headers=_auth_header())

    response = client.get("/projects/PR-000001/saves", headers=_auth_header())

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "PROJECT_REPO_DISCONNECTED"


def test_list_project_saves_returns_404_for_unknown_project_id():
    client, _drive_repo, _project_repo, _preview_repo, _save_repo = (
        _client_with_history_repos()
    )
    _connect_repo(client)

    response = client.get("/projects/PR-999999/saves", headers=_auth_header())

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "PROJECT_NOT_FOUND",
        "message": "Project not found in this Drive repo.",
    }


def test_list_project_saves_isolates_across_projects():
    client, drive_repo, _project_repo, preview_repo, save_repo = (
        _client_with_history_repos()
    )
    _connect_repo(client)
    first_project = client.post(
        "/projects",
        headers=_auth_header(),
        json={"name": "Project A"},
    ).json()["project"]
    second_project = client.post(
        "/projects",
        headers=_auth_header(),
        json={"name": "Project B"},
    ).json()["project"]
    first_record = _direct_save_for_project(
        drive_repo,
        preview_repo,
        save_repo,
        project_id=first_project["project_id"],
    )
    second_record = _direct_save_for_project(
        drive_repo,
        preview_repo,
        save_repo,
        project_id=second_project["project_id"],
    )

    first_response = client.get(
        f"/projects/{first_project['project_id']}/saves",
        headers=_auth_header(),
    )
    second_response = client.get(
        f"/projects/{second_project['project_id']}/saves",
        headers=_auth_header(),
    )

    assert [save["preview_id"] for save in first_response.json()["saves"]] == [
        first_record.preview_id
    ]
    assert [save["preview_id"] for save in second_response.json()["saves"]] == [
        second_record.preview_id
    ]


def _client_with_repos(config: ApiConfig | None = None):
    drive_repo = DriveRepoRepository()
    project_repo = ProjectRepository()
    client = TestClient(
        create_app(
            config=config,
            token_verifier=AcceptingTokenVerifier(),
            drive_repo_repository=drive_repo,
            project_repository=project_repo,
        )
    )
    return client, drive_repo, project_repo


def _client_with_history_repos():
    drive_repo = DriveRepoRepository()
    project_repo = ProjectRepository()
    preview_repo = SadPreviewRepository()
    save_repo = SadSaveRepository()
    client = TestClient(
        create_app(
            token_verifier=AcceptingTokenVerifier(),
            drive_repo_repository=drive_repo,
            project_repository=project_repo,
            sad_preview_repository=preview_repo,
            sad_save_repository=save_repo,
        )
    )
    return client, drive_repo, project_repo, preview_repo, save_repo


def _connect_repo(client: TestClient):
    response = client.post(
        "/drive/repo/connect",
        headers=_auth_header(),
        json={
            "project_id": "PROJ-000001",
            "authorization_code": "mock-authorization-code",
            "repo_folder_name": "Operations MVP",
            "create_new_repo": True,
        },
    )
    assert response.status_code == 200
    return response.json()


def _auth_header() -> dict[str, str]:
    return {"Authorization": "Bearer firebase-test-token"}


def _direct_save_for_project(
    drive_repo: DriveRepoRepository,
    preview_repo: SadPreviewRepository,
    save_repo: SadSaveRepository,
    *,
    project_id: str,
    saved_at: datetime | None = None,
):
    repo = drive_repo.get_active_repo("firebase-uid-001")
    assert repo is not None
    preview = preview_repo.save_preview(
        requirement_text="Need to validate an operational workflow.",
        analysis_id="AN-000001",
        preview=SadPreviewResponse.model_validate(VALID_PREVIEW),
    )
    return save_repo.save_preview(
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        repo=repo,
        project_id=project_id,
        preview_record=preview,
        sources=[],
        saved_at=saved_at,
    )
