from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from sadify_api.config import ApiConfig
from sadify_api.main import create_app
from sadify_api.schemas import (
    DriveRepoConnectRequest,
    GithubIssueDraft,
    GithubIssueSet,
    ProjectSessionSnapshot,
    ProjectSummary,
)
from sadify_api.services.auth import VerifiedFirebaseUser
from sadify_api.services.drive_client import DriveClient
from sadify_api.services.drive_repo import (
    DriveRepoRepository,
    FirestoreDriveRepoRepository,
)
from sadify_api.services.github_issue_sets import GithubIssueSetRepository
from sadify_api.services.projects import (
    FirestoreProjectRepository,
    ProjectRepository,
)
from sadify_api.services.sad_preview import SadPreviewRepository
from sadify_api.services.sad_save import (
    FirestoreSadSaveRepository,
    SadSaveRepository,
    _idempotency_hash,
)
from sadify_api.services.session_state import SessionSnapshotRepository
from tests.api.test_firestore_repositories import (
    FakeFirestoreClient,
    _drive_repo_record,
    _save_preview,
)


class AcceptingTokenVerifier:
    def verify_id_token(self, id_token: str) -> VerifiedFirebaseUser:
        return VerifiedFirebaseUser(
            uid="firebase-uid-001",
            email="owner@example.com",
            display_name="Project Owner",
            provider="firebase",
        )


class RecordingDriveClient:
    def __init__(self, *, fail_trash: bool = False) -> None:
        self.fail_trash = fail_trash
        self.trashed_folder_ids: list[str] = []

    def refresh_access_token(self, refresh_token: str) -> str:
        return "access-token"

    def trash_folder(self, access_token: str, folder_id: str) -> None:
        if self.fail_trash:
            from sadify_api.services.drive_client import DriveFolderTrashError

            raise DriveFolderTrashError("trash failed")
        self.trashed_folder_ids.append(folder_id)


class FakeSecretStore:
    def get_user_refresh_token(self, uid: str) -> str | None:
        return "refresh-token"


class FailOnceSadSaveRepository(SadSaveRepository):
    def __init__(self) -> None:
        super().__init__()
        self.fail_next_delete = False

    def delete_for_project(self, grant_id: str, project_id: str) -> int:
        if self.fail_next_delete:
            self.fail_next_delete = False
            raise RuntimeError("forced delete failure")
        return super().delete_for_project(grant_id, project_id)


class FailOnceGithubIssueSetRepository(GithubIssueSetRepository):
    def __init__(self) -> None:
        super().__init__()
        self.fail_next_delete = False

    def delete_for_project(self, grant_id: str, project_id: str) -> int:
        if self.fail_next_delete:
            self.fail_next_delete = False
            raise RuntimeError("forced issue-set delete failure")
        return super().delete_for_project(grant_id, project_id)


@dataclass
class DeleteFakes:
    grant_id: str
    drive_folder_id: str
    drive_repo: DriveRepoRepository
    project_repo: ProjectRepository
    sad_save_repo: SadSaveRepository
    issue_set_repo: GithubIssueSetRepository
    save_id: str
    session_repo: SessionSnapshotRepository
    drive_service: RecordingDriveClient


def _seed_delete_client(
    *,
    live: bool,
    drive_failure: bool = False,
    fail_once: bool = False,
    fail_issue_once: bool = False,
):
    drive_repo = DriveRepoRepository()
    project_repo = ProjectRepository()
    sad_save_repo = FailOnceSadSaveRepository() if fail_once else SadSaveRepository()
    issue_set_repo = (
        FailOnceGithubIssueSetRepository()
        if fail_issue_once
        else GithubIssueSetRepository()
    )
    session_repo = SessionSnapshotRepository()
    drive_service = RecordingDriveClient(fail_trash=drive_failure)
    repo = drive_repo.connect_repo(
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        request=DriveRepoConnectRequest(
            project_id="PROJ-000001",
            authorization_code="mock-code",
            repo_folder_name="Operations MVP",
            create_new_repo=True,
        ),
    )
    drive_folder_id = "drive-project-folder-001" if live else "LOCAL-PROJECT-FOLDER-000001"
    project = project_repo.create_project(
        grant_id=repo.grant_id,
        name="Bike Rental",
        drive_folder_id=drive_folder_id,
    )
    active_repo = drive_repo.set_active_project(grant_id=repo.grant_id, project=project)
    preview = _save_preview(SadPreviewRepository())
    saved = sad_save_repo.save_preview(
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        repo=active_repo,
        project_id=project.project_id,
        preview_record=preview,
        sources=[],
    )
    now = datetime.now(UTC)
    issue_set_repo.create_if_absent(
        GithubIssueSet(
            grant_id=repo.grant_id,
            project_id=project.project_id,
            save_id=saved.save_id,
            preview_id=saved.preview_id,
            owner_uid="firebase-uid-001",
            repo="octocat/bike-rental",
            issues=[
                GithubIssueDraft(
                    marker=f"<!-- sadify-github-issue:{project.project_id}:{saved.save_id}:0 -->",
                    title="Implement bike rental",
                    body="Implement the saved workflow.",
                )
            ],
            created_at=now,
            updated_at=now,
        )
    )
    session_repo.upsert(
        repo.grant_id,
        project.project_id,
        ProjectSessionSnapshot(clean_requirement_text="Bike rental ops"),
    )
    config = ApiConfig(
        environment="test",
        drive_mode="live" if live else "local",
        drive_live_enabled=live,
        google_oauth_client_id="client-id",
    )
    client = TestClient(
        create_app(
            config=config,
            token_verifier=AcceptingTokenVerifier(),
            drive_repo_repository=drive_repo,
            project_repository=project_repo,
            sad_save_repository=sad_save_repo,
            session_snapshot_repository=session_repo,
            github_issue_set_repository=issue_set_repo,
            drive_client=drive_service,
            secret_store=FakeSecretStore(),
        )
    )
    fakes = DeleteFakes(
        grant_id=repo.grant_id,
        drive_folder_id=drive_folder_id,
        drive_repo=drive_repo,
        project_repo=project_repo,
        sad_save_repo=sad_save_repo,
        issue_set_repo=issue_set_repo,
        save_id=saved.save_id,
        session_repo=session_repo,
        drive_service=drive_service,
    )
    return client, {"Authorization": "Bearer firebase-test-token"}, project.project_id, fakes


@pytest.fixture
def client_with_saved_project():
    return _seed_delete_client(live=True)


@pytest.fixture
def client_with_local_project():
    return _seed_delete_client(live=False)


@pytest.fixture
def client_with_drive_failure():
    return _seed_delete_client(live=True, drive_failure=True)


@pytest.fixture
def client_with_active_project():
    return _seed_delete_client(live=False, fail_once=True)


@pytest.fixture
def client_with_issue_delete_failure():
    return _seed_delete_client(live=False, fail_issue_once=True)


def test_delete_project_cascades_and_trashes_drive(client_with_saved_project):
    client, headers, project_id, fakes = client_with_saved_project
    response = client.delete(f"/projects/{project_id}", headers=headers)
    assert response.status_code == 200
    assert all(project["project_id"] != project_id for project in response.json()["projects"])
    assert response.json()["active_project_id"] is None
    assert fakes.project_repo.get_project(fakes.grant_id, project_id) is None
    assert fakes.sad_save_repo.list_for_project(
        grant_id=fakes.grant_id,
        project_id=project_id,
    ) == []
    assert fakes.session_repo.get(fakes.grant_id, project_id) is None
    assert fakes.issue_set_repo.get(fakes.grant_id, project_id, fakes.save_id) is None
    assert fakes.drive_service.trashed_folder_ids == [fakes.drive_folder_id]


def test_delete_local_project_skips_drive(client_with_local_project):
    client, headers, project_id, fakes = client_with_local_project
    assert client.delete(f"/projects/{project_id}", headers=headers).status_code == 200
    assert fakes.drive_service.trashed_folder_ids == []


def test_delete_unknown_project_404(client_with_saved_project):
    client, headers, _, _ = client_with_saved_project
    response = client.delete("/projects/PR-999999", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "PROJECT_NOT_FOUND"


def test_delete_drive_failure_keeps_app_data(client_with_drive_failure):
    client, headers, project_id, fakes = client_with_drive_failure
    response = client.delete(f"/projects/{project_id}", headers=headers)
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "PROJECT_DELETE_DRIVE_FAILED"
    assert fakes.project_repo.get_project(fakes.grant_id, project_id) is not None
    assert fakes.sad_save_repo.list_for_project(
        grant_id=fakes.grant_id,
        project_id=project_id,
    )
    assert fakes.session_repo.get(fakes.grant_id, project_id) is not None
    assert fakes.issue_set_repo.get(fakes.grant_id, project_id, fakes.save_id) is not None


def test_delete_persistence_failure_keeps_project_and_retry_succeeds(
    client_with_active_project,
):
    client, headers, project_id, fakes = client_with_active_project
    fakes.sad_save_repo.fail_next_delete = True
    first = client.delete(f"/projects/{project_id}", headers=headers)
    assert first.status_code == 502
    assert first.json()["detail"]["code"] == "PROJECT_DELETE_FAILED"
    assert fakes.project_repo.get_project(fakes.grant_id, project_id) is not None

    second = client.delete(f"/projects/{project_id}", headers=headers)
    assert second.status_code == 200
    assert fakes.project_repo.get_project(fakes.grant_id, project_id) is None


def test_delete_issue_set_failure_keeps_project_and_retry_succeeds(
    client_with_issue_delete_failure,
):
    client, headers, project_id, fakes = client_with_issue_delete_failure
    fakes.issue_set_repo.fail_next_delete = True

    first = client.delete(f"/projects/{project_id}", headers=headers)

    assert first.status_code == 502
    assert first.json()["detail"]["code"] == "PROJECT_DELETE_FAILED"
    assert fakes.project_repo.get_project(fakes.grant_id, project_id) is not None
    assert fakes.issue_set_repo.get(
        fakes.grant_id, project_id, fakes.save_id
    ) is not None

    second = client.delete(f"/projects/{project_id}", headers=headers)
    assert second.status_code == 200
    assert fakes.project_repo.get_project(fakes.grant_id, project_id) is None


def test_drive_client_trash_folder_updates_trashed_flag(monkeypatch):
    service = MagicMock()
    client = DriveClient(client_id="client-id", client_secret="client-secret")
    monkeypatch.setattr(client, "_drive_service", lambda _access_token: service)
    client.trash_folder("access-token", "folder-001")
    service.files.return_value.update.assert_called_once_with(
        fileId="folder-001",
        body={"trashed": True},
    )
    service.files.return_value.update.return_value.execute.assert_called_once_with()


def test_drive_client_trash_folder_wraps_api_error(monkeypatch):
    from sadify_api.services.drive_client import DriveFolderTrashError

    service = MagicMock()
    service.files.return_value.update.return_value.execute.side_effect = RuntimeError("api")
    client = DriveClient(client_id="client-id", client_secret="client-secret")
    monkeypatch.setattr(client, "_drive_service", lambda _access_token: service)
    with pytest.raises(DriveFolderTrashError):
        client.trash_folder("access-token", "folder-001")


@pytest.fixture(params=["memory", "firestore"])
def project_repository(request):
    if request.param == "memory":
        return ProjectRepository()
    return FirestoreProjectRepository(FakeFirestoreClient())


def test_delete_project_repository_removes_record_and_name_index(project_repository):
    project = project_repository.create_project(
        grant_id="DG-000001",
        name="Bike Rental",
        drive_folder_id="folder-001",
    )
    assert project_repository.delete_project("DG-000001", project.project_id) == project
    assert project_repository.get_project("DG-000001", project.project_id) is None
    assert project_repository.get_project_by_name("DG-000001", project.name) is None
    assert project_repository.delete_project("DG-000001", project.project_id) is None


@pytest.fixture(params=["memory", "firestore"])
def sad_save_repository(request):
    if request.param == "memory":
        return SadSaveRepository(), None
    client = FakeFirestoreClient()
    return FirestoreSadSaveRepository(client), client


def test_delete_for_project_removes_save_and_idempotency(sad_save_repository):
    repository, firestore_client = sad_save_repository
    preview = _save_preview(SadPreviewRepository())
    record = repository.save_preview(
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        repo=_drive_repo_record(),
        project_id="PR-000001",
        preview_record=preview,
        sources=[],
    )
    assert repository.delete_for_project("DG-000001", "PR-000001") == 1
    assert repository.list_for_project(
        grant_id="DG-000001",
        project_id="PR-000001",
    ) == []
    assert repository.delete_for_project("DG-000001", "PR-000001") == 0
    if firestore_client is not None:
        assert (
            "sad_save_idempotency",
            _idempotency_hash(record.idempotency_key),
        ) not in firestore_client.docs


@pytest.fixture(params=["memory", "firestore"])
def drive_repo_repository(request):
    if request.param == "memory":
        return DriveRepoRepository()
    return FirestoreDriveRepoRepository(FakeFirestoreClient())


def test_clear_active_project_only_clears_matching_pointer(drive_repo_repository):
    repo = drive_repo_repository.connect_repo(
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        request=DriveRepoConnectRequest(
            project_id="PROJ-000001",
            authorization_code="mock-code",
            repo_folder_name="Operations MVP",
            create_new_repo=True,
        ),
    )
    project = ProjectSummary(
        project_id="PR-000001",
        name="Bike Rental",
        drive_folder_id="folder-001",
        created_at=datetime.now(UTC),
    )
    drive_repo_repository.set_active_project(grant_id=repo.grant_id, project=project)
    drive_repo_repository.clear_active_project(repo.grant_id, "PR-OTHER")
    assert drive_repo_repository.get_active_repo("firebase-uid-001").active_project_id == project.project_id
    drive_repo_repository.clear_active_project(repo.grant_id, project.project_id)
    active = drive_repo_repository.get_active_repo("firebase-uid-001")
    assert active.active_project_id is None
    assert active.active_project_name is None
    drive_repo_repository.clear_active_project(repo.grant_id, project.project_id)
