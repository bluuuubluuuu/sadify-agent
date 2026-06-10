from datetime import UTC, datetime

from fastapi.testclient import TestClient
from google.api_core.exceptions import NotFound

from sadify_api.config import ApiConfig
from sadify_api.main import create_app
from sadify_api.services.auth import VerifiedFirebaseUser
from sadify_api.services.drive_client import (
    DriveFolder,
    DriveFolderCreateError,
    DriveFolderRef,
    DriveOauthExchangeError,
    DriveTokens,
)
from sadify_api.services.drive_repo import DriveRepoRepository


class AcceptingTokenVerifier:
    def verify_id_token(self, id_token: str) -> VerifiedFirebaseUser:
        return VerifiedFirebaseUser(
            uid="firebase-uid-001",
            email="owner@example.com",
            display_name="Project Owner",
            provider="firebase",
        )


def test_live_connect_exchanges_code_and_stores_refresh_token():
    client, _repo, drive_client, secret_store = _live_client()

    response = _connect(client)

    assert response.status_code == 200
    payload = response.json()
    assert payload["repo_folder_id"] == "drive-folder-001"
    assert payload["repo_folder_name"] == "SADify Projects"
    assert payload["repo_url"] == "https://drive.google.com/drive/folders/drive-folder-001"
    assert payload["token_store"] == "secret_manager"
    assert payload["saves_blocked"] is False
    assert drive_client.exchanged_code == "live-auth-code"
    assert drive_client.exchanged_redirect_uri == "postmessage"
    assert secret_store.refresh_tokens == {"firebase-uid-001": "refresh-token"}


def test_live_connect_creates_folder_when_missing():
    client, _repo, drive_client, _secret_store = _live_client(
        folder_id="created-folder-001"
    )

    response = _connect(client)

    assert response.status_code == 200
    assert response.json()["repo_folder_id"] == "created-folder-001"
    assert drive_client.folder_name == "SADify Projects"


def test_live_connect_finds_existing_folder():
    client, _repo, drive_client, _secret_store = _live_client(
        folder_id="existing-folder-001"
    )

    response = _connect(client)

    assert response.status_code == 200
    assert response.json()["repo_folder_id"] == "existing-folder-001"
    assert drive_client.folder_name == "SADify Projects"


def test_live_connect_surfaces_oauth_exchange_failure_as_502():
    client, _repo, _drive_client, _secret_store = _live_client(
        drive_error=DriveOauthExchangeError("bad code")
    )

    response = _connect(client)

    assert response.status_code == 502
    assert response.json()["detail"] == {
        "code": "DRIVE_OAUTH_EXCHANGE_FAILED",
        "message": "Could not complete Google Drive sign-in.",
    }


def test_live_connect_surfaces_folder_create_failure_as_502():
    client, _repo, _drive_client, _secret_store = _live_client(
        folder_error=DriveFolderCreateError("folder failed")
    )

    response = _connect(client)

    assert response.status_code == 502
    assert response.json()["detail"] == {
        "code": "DRIVE_FOLDER_CREATE_FAILED",
        "message": "Could not create the SADify Projects folder.",
    }


def test_live_connect_surfaces_secret_write_failure_as_502():
    client, _repo, _drive_client, _secret_store = _live_client(secret_write_error=True)

    response = _connect(client)

    assert response.status_code == 502
    assert response.json()["detail"] == {
        "code": "DRIVE_TOKEN_PERSIST_FAILED",
        "message": "Could not securely store your Drive permission.",
    }


def test_live_disconnect_deletes_user_secret():
    client, _repo, _drive_client, secret_store = _live_client()
    assert _connect(client).status_code == 200

    response = client.post("/drive/repo/disconnect", headers=_auth_header())

    assert response.status_code == 200
    assert response.json()["repo"]["status"] == "disconnected"
    assert secret_store.deleted_uids == ["firebase-uid-001"]


def test_live_disconnect_tolerates_missing_secret():
    client, _repo, _drive_client, secret_store = _live_client()
    secret_store.delete_error = NotFound("missing")
    assert _connect(client).status_code == 200

    response = client.post("/drive/repo/disconnect", headers=_auth_header())

    assert response.status_code == 200
    assert response.json()["repo"]["status"] == "disconnected"


def test_local_connect_unchanged_when_mode_is_local():
    repository = DriveRepoRepository()
    client = TestClient(
        create_app(
            config=_config("local"),
            token_verifier=AcceptingTokenVerifier(),
            drive_repo_repository=repository,
        )
    )

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
    payload = response.json()
    assert payload["repo_folder_id"] == "LOCAL-DRIVE-FOLDER-000001"
    assert payload["repo_folder_name"] == "Operations MVP"
    assert payload["token_store"] == "local_metadata_only"
    assert payload["available_projects"] == []
    assert payload["active_project_id"] is None


def test_live_connect_returns_available_projects_synced_from_drive():
    client, _repo, drive_client, _secret_store = _live_client(
        subfolders=[
            DriveFolderRef(
                folder_id="project-folder-001",
                name="Project A",
                created_time=datetime(2026, 5, 28, 10, 0, tzinfo=UTC),
                web_view_link="https://drive.google.com/project-a",
            )
        ]
    )

    response = _connect(client)

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_project_id"] is None
    assert payload["active_project_name"] is None
    assert payload["available_projects"] == [
        {
            "project_id": "PR-000001",
            "name": "Project A",
            "drive_folder_id": "project-folder-001",
            "created_at": "2026-05-28T10:00:00Z",
            "github_repo": None,
        }
    ]
    assert drive_client.listed_parent_folder_id == "drive-folder-001"


def test_live_connect_returns_empty_projects_when_drive_has_no_subfolders():
    client, _repo, _drive_client, _secret_store = _live_client(subfolders=[])

    response = _connect(client)

    assert response.status_code == 200
    assert response.json()["available_projects"] == []


def test_connect_does_not_auto_activate_any_project():
    client, repository, _drive_client, _secret_store = _live_client(
        subfolders=[
            DriveFolderRef(
                folder_id="project-folder-001",
                name="Project A",
                created_time=datetime(2026, 5, 28, 10, 0, tzinfo=UTC),
                web_view_link=None,
            )
        ]
    )

    response = _connect(client)

    assert response.status_code == 200
    assert response.json()["active_project_id"] is None
    repo = repository.get_active_repo("firebase-uid-001")
    assert repo is not None
    assert repo.active_project_id is None


def test_live_connect_project_listing_blocks_when_live_gate_disabled():
    repository = DriveRepoRepository()
    client = TestClient(
        create_app(
            config=_config("live", drive_live_enabled=False),
            token_verifier=AcceptingTokenVerifier(),
            drive_repo_repository=repository,
        )
    )

    response = _connect(client)

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "DRIVE_LIVE_MODE_DISABLED"


def _live_client(
    *,
    folder_id: str = "drive-folder-001",
    drive_error: Exception | None = None,
    folder_error: Exception | None = None,
    secret_write_error: bool = False,
    subfolders: list[DriveFolderRef] | None = None,
):
    repository = DriveRepoRepository()
    drive_client = FakeDriveClient(
        folder_id=folder_id,
        drive_error=drive_error,
        folder_error=folder_error,
        subfolders=subfolders,
    )
    secret_store = FakeSecretStore(secret_write_error=secret_write_error)
    client = TestClient(
        create_app(
            config=_config("live"),
            token_verifier=AcceptingTokenVerifier(),
            drive_repo_repository=repository,
            drive_client=drive_client,
            secret_store=secret_store,
        )
    )
    return client, repository, drive_client, secret_store


def _connect(client: TestClient):
    return client.post(
        "/drive/repo/connect",
        headers=_auth_header(),
        json={
            "project_id": "PROJ-000001",
            "authorization_code": "live-auth-code",
            "repo_folder_name": "Ignored in live mode",
            "create_new_repo": True,
        },
    )


def _config(mode: str, *, drive_live_enabled: bool = False) -> ApiConfig:
    return ApiConfig(
        environment="test",
        drive_mode=mode,
        drive_folder_name="SADify Projects",
        google_oauth_client_id="client-id",
        google_oauth_client_secret_name="sadify-drive-oauth-client-secret",
        drive_live_enabled=drive_live_enabled,
    )


def _auth_header() -> dict[str, str]:
    return {"Authorization": "Bearer firebase-test-token"}


class FakeSecretStore:
    def __init__(self, *, secret_write_error: bool = False) -> None:
        self.secret_write_error = secret_write_error
        self.refresh_tokens: dict[str, str] = {}
        self.deleted_uids: list[str] = []
        self.delete_error: Exception | None = None

    def get_oauth_client_secret(self) -> str:
        return "client-secret"

    def put_user_refresh_token(self, uid: str, refresh_token: str) -> None:
        if self.secret_write_error:
            raise RuntimeError("secret write failed")
        self.refresh_tokens[uid] = refresh_token

    def get_user_refresh_token(self, uid: str) -> str | None:
        return self.refresh_tokens.get(uid)

    def delete_user_secret(self, uid: str) -> None:
        self.deleted_uids.append(uid)
        if self.delete_error:
            raise self.delete_error


class FakeDriveClient:
    def __init__(
        self,
        *,
        folder_id: str,
        drive_error: Exception | None = None,
        folder_error: Exception | None = None,
        subfolders: list[DriveFolderRef] | None = None,
    ) -> None:
        self.folder_id = folder_id
        self.drive_error = drive_error
        self.folder_error = folder_error
        self.exchanged_code: str | None = None
        self.exchanged_redirect_uri: str | None = None
        self.folder_name: str | None = None
        self.subfolders = subfolders
        self.listed_parent_folder_id: str | None = None

    def exchange_authorization_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> DriveTokens:
        if self.drive_error:
            raise self.drive_error
        self.exchanged_code = code
        self.exchanged_redirect_uri = redirect_uri
        return DriveTokens(
            access_token="access-token",
            refresh_token="refresh-token",
            expiry=datetime(2026, 5, 25, tzinfo=UTC),
        )

    def find_or_create_folder(
        self,
        access_token: str,
        folder_name: str,
    ) -> DriveFolder:
        if self.folder_error:
            raise self.folder_error
        self.folder_name = folder_name
        return DriveFolder(folder_id=self.folder_id, name=folder_name)

    def refresh_access_token(self, refresh_token: str) -> str:
        return "access-token"

    def list_subfolders(
        self,
        *,
        access_token: str,
        parent_folder_id: str,
    ) -> list[DriveFolderRef]:
        self.listed_parent_folder_id = parent_folder_id
        return list(self.subfolders or [])
