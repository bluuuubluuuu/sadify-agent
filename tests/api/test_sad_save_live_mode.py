from datetime import UTC, datetime

from fastapi.testclient import TestClient

from sadify_api.config import ApiConfig
from sadify_api.main import create_app
from sadify_api.schemas import SadPreviewResponse
from sadify_api.services.auth import VerifiedFirebaseUser
from sadify_api.services.drive_client import (
    DriveFolder,
    DriveFolderRef,
    DriveTokens,
    DriveTokenInvalidError,
    DriveUploadError,
    DriveUploadResult,
)
from sadify_api.services.drive_repo import DriveRepoRepository
from sadify_api.services.sad_preview import SadPreviewRepository
from sadify_api.services.sad_save import SadSaveRepository
from sadify_api.services.source_uploads import SourceRepository
from tests.api.test_sad_preview import VALID_PREVIEW


class AcceptingTokenVerifier:
    def verify_id_token(self, id_token: str) -> VerifiedFirebaseUser:
        return VerifiedFirebaseUser(
            uid="firebase-uid-001",
            email="owner@example.com",
            display_name="Project Owner",
            provider="firebase",
        )


def test_live_save_uploads_markdown_and_returns_real_doc_id():
    client, _save_repo, drive_client, _secret_store = _live_client()
    _connect_and_create_project(client)
    preview = _save_preview(_preview_repo(client))

    response = _save(client, preview.preview_id)

    assert response.status_code == 200
    record = response.json()["record"]
    assert record["sad_doc"]["file_id"] == "real-doc-001"
    assert drive_client.uploaded_markdown.startswith("# Operational Workflow Validation")


def test_live_save_uses_real_web_view_link():
    client, _save_repo, _drive_client, _secret_store = _live_client()
    _connect_and_create_project(client)
    preview = _save_preview(_preview_repo(client))

    response = _save(client, preview.preview_id)

    assert response.status_code == 200
    assert (
        response.json()["record"]["sad_doc"]["url"]
        == "https://docs.google.com/document/d/real-doc-001/edit"
    )


def test_live_save_returns_existing_record_on_idempotent_repeat_without_reupload():
    client, save_repo, drive_client, _secret_store = _live_client()
    _connect_and_create_project(client)
    preview = _save_preview(_preview_repo(client))

    first = _save(client, preview.preview_id)
    second = _save(client, preview.preview_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["record"]["save_id"] == second.json()["record"]["save_id"]
    assert first.json()["record"]["sad_doc"]["file_id"] == "real-doc-001"
    assert second.json()["record"]["sad_doc"]["file_id"] == "real-doc-001"
    assert drive_client.upload_count == 1
    assert save_repo.record_count() == 1


def test_live_save_blocks_when_refresh_token_missing():
    client, _save_repo, _drive_client, secret_store = _live_client()
    _connect_and_create_project(client)
    secret_store.refresh_tokens.clear()
    preview = _save_preview(_preview_repo(client))

    response = _save(client, preview.preview_id)

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "SAD_SAVE_TOKEN_MISSING",
        "message": "Reconnect Google Drive before saving.",
    }


def test_live_save_blocks_when_refresh_token_invalid():
    client, _save_repo, drive_client, _secret_store = _live_client()
    _connect_and_create_project(client)
    drive_client.refresh_error = DriveTokenInvalidError("invalid")
    preview = _save_preview(_preview_repo(client))

    response = _save(client, preview.preview_id)

    assert response.status_code == 401
    assert response.json()["detail"] == {
        "code": "SAD_SAVE_TOKEN_INVALID",
        "message": "Reconnect Google Drive to renew permission.",
    }


def test_live_save_surfaces_drive_upload_failure_as_502():
    client, _save_repo, drive_client, _secret_store = _live_client()
    drive_client.upload_error = DriveUploadError("upload failed")
    _connect_and_create_project(client)
    preview = _save_preview(_preview_repo(client))

    response = _save(client, preview.preview_id)

    assert response.status_code == 502
    assert response.json()["detail"] == {
        "code": "SAD_SAVE_DRIVE_UPLOAD_FAILED",
        "message": "Google Drive rejected the upload.",
    }


def test_live_save_persists_real_ids_into_repository():
    client, save_repo, _drive_client, _secret_store = _live_client()
    _connect_and_create_project(client)
    preview = _save_preview(_preview_repo(client))

    response = _save(client, preview.preview_id)

    assert response.status_code == 200
    saved = save_repo.get_save(response.json()["record"]["save_id"])
    assert saved is not None
    assert saved.sad_doc.file_id == "real-doc-001"
    assert saved.sad_doc.url == "https://docs.google.com/document/d/real-doc-001/edit"


def test_live_save_writes_into_active_project_sad_subfolder():
    client, _save_repo, drive_client, _secret_store = _live_client()
    _connect_and_create_project(client)
    preview = _save_preview(_preview_repo(client))

    response = _save(client, preview.preview_id)

    assert response.status_code == 200
    assert ("SAD", "project-folder-001") in drive_client.folder_lookups
    assert drive_client.uploaded_folder_id == "sad-folder-001"


def test_local_save_unchanged_when_mode_is_local():
    client, _save_repo, _drive_client, _secret_store = _local_client()
    _connect_and_create_project(client)
    preview = _save_preview(_preview_repo(client))

    response = _save(client, preview.preview_id)

    assert response.status_code == 200
    assert response.json()["record"]["sad_doc"]["file_id"] == "LOCAL-GDOC-000001"


def _live_client():
    return _client("live")


def _local_client():
    return _client("local")


def _client(mode: str):
    drive_repo = DriveRepoRepository()
    preview_repo = SadPreviewRepository()
    save_repo = SadSaveRepository()
    source_repo = SourceRepository()
    drive_client = FakeDriveClient()
    secret_store = FakeSecretStore()
    app = create_app(
        config=_config(mode),
        token_verifier=AcceptingTokenVerifier(),
        drive_repo_repository=drive_repo,
        sad_preview_repository=preview_repo,
        sad_save_repository=save_repo,
        source_repository=source_repo,
        drive_client=drive_client,
        secret_store=secret_store,
    )
    app.state.preview_repo = preview_repo
    return TestClient(app), save_repo, drive_client, secret_store


def _preview_repo(client: TestClient) -> SadPreviewRepository:
    return client.app.state.preview_repo


def _connect(client: TestClient):
    response = client.post(
        "/drive/repo/connect",
        headers=_auth_header(),
        json={
            "project_id": "PROJ-000001",
            "authorization_code": "live-auth-code",
            "repo_folder_name": "Operations MVP",
            "create_new_repo": True,
        },
    )
    assert response.status_code == 200
    return response.json()


def _connect_and_create_project(client: TestClient):
    _connect(client)
    response = client.post(
        "/projects",
        headers=_auth_header(),
        json={"name": "Operations MVP"},
    )
    assert response.status_code == 200
    return response.json()


def _save(client: TestClient, preview_id: str):
    return client.post(
        "/sad/save",
        headers=_auth_header(),
        json={"preview_id": preview_id},
    )


def _save_preview(preview_repo: SadPreviewRepository):
    return preview_repo.save_preview(
        requirement_text="Need to validate an operational workflow.",
        analysis_id="AN-000001",
        preview=SadPreviewResponse.model_validate(VALID_PREVIEW),
    )


def _config(mode: str) -> ApiConfig:
    return ApiConfig(
        environment="test",
        drive_mode=mode,
        drive_live_enabled=mode == "live",
        drive_folder_name="SADify Projects",
        google_oauth_client_id="client-id",
        google_oauth_client_secret_name="sadify-drive-oauth-client-secret",
    )


def _auth_header() -> dict[str, str]:
    return {"Authorization": "Bearer firebase-test-token"}


class FakeSecretStore:
    def __init__(self) -> None:
        self.refresh_tokens: dict[str, str] = {}

    def get_oauth_client_secret(self) -> str:
        return "client-secret"

    def put_user_refresh_token(self, uid: str, refresh_token: str) -> None:
        self.refresh_tokens[uid] = refresh_token

    def get_user_refresh_token(self, uid: str) -> str | None:
        return self.refresh_tokens.get(uid)


class FakeDriveClient:
    def __init__(self) -> None:
        self.refresh_error: Exception | None = None
        self.upload_error: Exception | None = None
        self.upload_count = 0
        self.uploaded_markdown = ""
        self.uploaded_folder_id = ""
        self.folder_lookups: list[tuple[str, str | None]] = []

    def exchange_authorization_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> DriveTokens:
        return DriveTokens(
            access_token="access-token",
            refresh_token="refresh-token",
            expiry=datetime(2026, 5, 25, tzinfo=UTC),
        )

    def find_or_create_folder(
        self,
        access_token: str,
        folder_name: str,
        parent_folder_id: str | None = None,
    ) -> DriveFolder:
        self.folder_lookups.append((folder_name, parent_folder_id))
        folder_ids = {
            ("SADify Projects", None): "drive-folder-001",
            ("Operations MVP", "drive-folder-001"): "project-folder-001",
            ("SAD", "project-folder-001"): "sad-folder-001",
        }
        return DriveFolder(
            folder_id=folder_ids.get((folder_name, parent_folder_id), "drive-folder-001"),
            name=folder_name,
        )

    def list_subfolders(
        self,
        access_token: str,
        parent_folder_id: str,
    ) -> list[DriveFolderRef]:
        return []

    def refresh_access_token(self, refresh_token: str) -> str:
        if self.refresh_error:
            raise self.refresh_error
        return "new-access-token"

    def upload_markdown_as_doc(
        self,
        *,
        access_token: str,
        folder_id: str,
        title: str,
        markdown: str,
    ) -> DriveUploadResult:
        self.upload_count += 1
        self.uploaded_markdown = markdown
        self.uploaded_folder_id = folder_id
        if self.upload_error:
            raise self.upload_error
        return DriveUploadResult(
            file_id="real-doc-001",
            web_view_link="https://docs.google.com/document/d/real-doc-001/edit",
        )
