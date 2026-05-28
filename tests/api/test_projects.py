from datetime import UTC, datetime

from fastapi.testclient import TestClient

from sadify_api.config import ApiConfig
from sadify_api.main import create_app
from sadify_api.services.auth import VerifiedFirebaseUser
from sadify_api.services.drive_client import DriveFolderRef
from sadify_api.services.drive_repo import DriveRepoRepository
from sadify_api.services.projects import ProjectRepository


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
