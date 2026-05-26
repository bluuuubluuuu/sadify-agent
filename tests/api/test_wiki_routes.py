from datetime import UTC, datetime
from hashlib import sha256

from fastapi.testclient import TestClient

from sadify_api.config import ApiConfig
from sadify_api.main import create_app
from sadify_api.schemas import SadPreviewResponse
from sadify_api.services.auth import VerifiedFirebaseUser
from sadify_api.services.drive_client import (
    DriveFileRef,
    DriveFolder,
    DriveTextFileError,
    DriveTokens,
    DriveUploadResult,
)
from sadify_api.services.drive_repo import DriveRepoRepository
from sadify_api.services.sad_preview import SadPreviewRepository
from sadify_api.services.sad_save import SadSaveRepository
from sadify_api.services.source_uploads import SourceRepository
from sadify_api.services.wiki_state import WikiStateRepository
from tests.api.test_sad_preview import VALID_PREVIEW


class AcceptingTokenVerifier:
    def verify_id_token(self, id_token: str) -> VerifiedFirebaseUser:
        return VerifiedFirebaseUser(
            uid="firebase-uid-001",
            email="owner@example.com",
            display_name="Project Owner",
            provider="firebase",
        )


def test_wiki_preview_returns_first_time_write_when_remote_missing():
    client, _drive, _save, _wiki, fake_drive = _client_with_saved_sad()
    fake_drive.remote_text = None

    response = client.post("/sad/wiki/preview", headers=_auth_header(), json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["remote_exists"] is False
    assert payload["remote_hash"] is None
    assert payload["last_known_hash"] is None
    assert payload["requires_confirmation"] is False
    assert payload["remote_markdown"] is None
    assert payload["proposed_markdown"].startswith("# SADify Project Wiki")


def test_wiki_preview_returns_no_confirmation_when_hashes_match():
    remote = "# Existing Wiki"
    client, drive_repo, _save, wiki_state, fake_drive = _client_with_saved_sad()
    repo = drive_repo.get_active_repo("firebase-uid-001")
    wiki_state.record_write(
        repo.grant_id,
        file_id="wiki-file-001",
        hash_value=_hash(remote),
        updated_at=datetime(2026, 5, 26, 10, 0, tzinfo=UTC),
    )
    fake_drive.remote_text = remote

    response = client.post("/sad/wiki/preview", headers=_auth_header(), json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["remote_exists"] is True
    assert payload["remote_hash"] == _hash(remote)
    assert payload["last_known_hash"] == _hash(remote)
    assert payload["requires_confirmation"] is False
    assert payload["remote_markdown"] is None


def test_wiki_preview_returns_requires_confirmation_when_remote_drifted():
    remote = "# Edited in Drive"
    client, drive_repo, _save, wiki_state, fake_drive = _client_with_saved_sad()
    repo = drive_repo.get_active_repo("firebase-uid-001")
    wiki_state.record_write(
        repo.grant_id,
        file_id="wiki-file-001",
        hash_value=_hash("# Prior Wiki"),
        updated_at=datetime(2026, 5, 26, 10, 0, tzinfo=UTC),
    )
    fake_drive.remote_text = remote

    response = client.post("/sad/wiki/preview", headers=_auth_header(), json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["requires_confirmation"] is True
    assert payload["remote_markdown"] == remote


def test_wiki_preview_blocks_unsigned():
    client, _drive, _save, _wiki, _fake_drive = _client_with_saved_sad()

    response = client.post("/sad/wiki/preview", json={})

    assert response.status_code == 401
    assert response.json()["detail"] == {
        "code": "WIKI_AUTH_REQUIRED",
        "message": "Sign in before updating the wiki.",
    }


def test_wiki_preview_blocks_without_active_repo():
    client, _drive, _save, _wiki, _fake_drive = _client()

    response = client.post("/sad/wiki/preview", headers=_auth_header(), json={})

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "WIKI_REPO_REQUIRED"


def test_wiki_preview_blocks_when_no_prior_sad_save():
    client, _drive, _save, _wiki, _fake_drive = _client()
    _connect_repo(client)

    response = client.post("/sad/wiki/preview", headers=_auth_header(), json={})

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "WIKI_SAVE_REQUIRED"


def test_wiki_preview_blocks_when_live_mode_disabled():
    client, _drive, _save, _wiki, _fake_drive = _client(drive_live_enabled=False)
    _connect_repo(client)

    response = client.post("/sad/wiki/preview", headers=_auth_header(), json={})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "WIKI_LIVE_MODE_DISABLED"


def test_wiki_update_writes_first_time_without_force():
    client, _drive, _save, wiki_state, fake_drive = _client_with_saved_sad()
    fake_drive.remote_text = None

    response = client.post(
        "/sad/wiki/update",
        headers=_auth_header(),
        json={"expected_remote_hash": None, "force_overwrite": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["wiki_path"] == "Wiki/Wiki.md"
    assert payload["wiki_file_id"] == "wiki-file-001"
    assert payload["created_new_file"] is True
    assert fake_drive.uploaded_content.startswith("# SADify Project Wiki")
    state = wiki_state.get_state("DG-000001")
    assert state is not None
    assert state.hash == payload["wiki_hash"]


def test_wiki_update_writes_when_hashes_match():
    remote = "# Prior Wiki"
    client, _drive, _save, _wiki, fake_drive = _client_with_saved_sad()
    fake_drive.remote_text = remote

    response = client.post(
        "/sad/wiki/update",
        headers=_auth_header(),
        json={"expected_remote_hash": _hash(remote), "force_overwrite": False},
    )

    assert response.status_code == 200
    assert response.json()["created_new_file"] is False
    assert fake_drive.replaced_file_id == "wiki-file-001"


def test_wiki_update_blocks_on_conflict_when_force_false():
    remote = "# Edited in Drive"
    client, _drive, _save, _wiki, fake_drive = _client_with_saved_sad()
    fake_drive.remote_text = remote

    response = client.post(
        "/sad/wiki/update",
        headers=_auth_header(),
        json={"expected_remote_hash": _hash("# Prior Wiki"), "force_overwrite": False},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "WIKI_CONFLICT"
    assert fake_drive.uploaded_content is None


def test_wiki_update_overwrites_when_force_true():
    remote = "# Edited in Drive"
    client, _drive, _save, _wiki, fake_drive = _client_with_saved_sad()
    fake_drive.remote_text = remote

    response = client.post(
        "/sad/wiki/update",
        headers=_auth_header(),
        json={"expected_remote_hash": _hash("# Prior Wiki"), "force_overwrite": True},
    )

    assert response.status_code == 200
    assert fake_drive.uploaded_content.startswith("# SADify Project Wiki")


def test_wiki_update_records_state_after_success():
    client, _drive, _save, wiki_state, fake_drive = _client_with_saved_sad()
    fake_drive.remote_text = None

    response = client.post(
        "/sad/wiki/update",
        headers=_auth_header(),
        json={"expected_remote_hash": None, "force_overwrite": False},
    )

    assert response.status_code == 200
    state = wiki_state.get_state("DG-000001")
    assert state is not None
    assert state.file_id == "wiki-file-001"
    assert state.hash == response.json()["wiki_hash"]


def test_wiki_update_surfaces_drive_write_failure_as_502():
    client, _drive, _save, _wiki, fake_drive = _client_with_saved_sad()
    fake_drive.remote_text = None
    fake_drive.write_error = DriveTextFileError("write failed")

    response = client.post(
        "/sad/wiki/update",
        headers=_auth_header(),
        json={"expected_remote_hash": None, "force_overwrite": False},
    )

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "WIKI_WRITE_FAILED"


def test_wiki_update_writes_into_wiki_subfolder_under_project_root():
    client, _drive, _save, _wiki, fake_drive = _client_with_saved_sad()
    fake_drive.remote_text = None

    response = client.post(
        "/sad/wiki/update",
        headers=_auth_header(),
        json={"expected_remote_hash": None, "force_overwrite": False},
    )

    assert response.status_code == 200
    assert fake_drive.folder_lookups[-1] == {
        "folder_name": "Wiki",
        "parent_folder_id": "drive-folder-001",
    }
    assert fake_drive.upload_folder_id == "wiki-folder-001"
    assert fake_drive.upload_folder_id != "drive-folder-001"


def test_wiki_preview_reads_from_wiki_subfolder_not_project_root():
    client, _drive, _save, _wiki, fake_drive = _client_with_saved_sad()
    fake_drive.remote_text = "# Existing Wiki"

    response = client.post("/sad/wiki/preview", headers=_auth_header(), json={})

    assert response.status_code == 200
    assert fake_drive.folder_lookups[-1] == {
        "folder_name": "Wiki",
        "parent_folder_id": "drive-folder-001",
    }
    assert fake_drive.find_file_folder_id == "wiki-folder-001"
    assert fake_drive.find_file_folder_id != "drive-folder-001"


def _client_with_saved_sad(**kwargs):
    client, drive_repo, save_repo, wiki_state, fake_drive = _client(**kwargs)
    _connect_repo(client)
    repo = drive_repo.get_active_repo("firebase-uid-001")
    _save_sad(save_repo, repo)
    return client, drive_repo, save_repo, wiki_state, fake_drive


def _client(*, drive_live_enabled: bool = True):
    drive_repo = DriveRepoRepository()
    preview_repo = SadPreviewRepository()
    save_repo = SadSaveRepository()
    source_repo = SourceRepository()
    wiki_state = WikiStateRepository()
    fake_drive = FakeDriveClient()
    secret_store = FakeSecretStore()
    app = create_app(
        config=ApiConfig(
            environment="test",
            drive_mode="live",
            drive_live_enabled=drive_live_enabled,
            drive_folder_name="SADify Projects",
            google_oauth_client_id="client-id",
            google_oauth_client_secret_name="sadify-drive-oauth-client-secret",
        ),
        token_verifier=AcceptingTokenVerifier(),
        drive_repo_repository=drive_repo,
        sad_preview_repository=preview_repo,
        sad_save_repository=save_repo,
        source_repository=source_repo,
        drive_client=fake_drive,
        secret_store=secret_store,
        wiki_state_repository=wiki_state,
    )
    return TestClient(app), drive_repo, save_repo, wiki_state, fake_drive


def _connect_repo(client: TestClient):
    response = client.post(
        "/drive/repo/connect",
        headers=_auth_header(),
        json={
            "project_id": "PROJ-000001",
            "authorization_code": "live-auth-code",
            "repo_folder_name": "SADify Projects",
            "create_new_repo": True,
        },
    )
    assert response.status_code == 200


def _save_sad(save_repo: SadSaveRepository, repo):
    preview_repo = SadPreviewRepository()
    preview_record = preview_repo.save_preview(
        requirement_text="A workshop tracks repairs.",
        analysis_id="AN-000001",
        preview=SadPreviewResponse.model_validate(VALID_PREVIEW),
    )
    return save_repo.save_preview(
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        repo=repo,
        preview_record=preview_record,
        sources=[],
    )


def _auth_header() -> dict[str, str]:
    return {"Authorization": "Bearer firebase-test-token"}


def _hash(value: str) -> str:
    return f"sha256:{sha256(value.encode('utf-8')).hexdigest()}"


class FakeSecretStore:
    def __init__(self) -> None:
        self.refresh_tokens = {"firebase-uid-001": "refresh-token"}

    def get_oauth_client_secret(self) -> str:
        return "client-secret"

    def put_user_refresh_token(self, uid: str, refresh_token: str) -> None:
        self.refresh_tokens[uid] = refresh_token

    def get_user_refresh_token(self, uid: str) -> str | None:
        return self.refresh_tokens.get(uid)


class FakeDriveClient:
    def __init__(self) -> None:
        self.remote_text: str | None = None
        self.uploaded_content: str | None = None
        self.replaced_file_id: str | None = None
        self.write_error: Exception | None = None
        self.folder_lookups: list[dict[str, str | None]] = []
        self.find_file_folder_id: str | None = None
        self.upload_folder_id: str | None = None

    def exchange_authorization_code(self, code: str, redirect_uri: str) -> DriveTokens:
        return DriveTokens(
            access_token="access-token",
            refresh_token="refresh-token",
            expiry=datetime(2026, 5, 26, 10, 0, tzinfo=UTC),
        )

    def find_or_create_folder(
        self,
        access_token: str,
        folder_name: str,
        parent_folder_id: str | None = None,
    ) -> DriveFolder:
        self.folder_lookups.append(
            {
                "folder_name": folder_name,
                "parent_folder_id": parent_folder_id,
            }
        )
        if parent_folder_id:
            return DriveFolder(folder_id="wiki-folder-001", name=folder_name)
        return DriveFolder(folder_id="drive-folder-001", name=folder_name)

    def refresh_access_token(self, refresh_token: str) -> str:
        return "access-token"

    def find_file_in_folder(
        self,
        *,
        access_token: str,
        folder_id: str,
        name: str,
        mime_type: str | None = None,
    ) -> DriveFileRef | None:
        self.find_file_folder_id = folder_id
        if self.remote_text is None:
            return None
        return DriveFileRef(
            file_id="wiki-file-001",
            name=name,
            mime_type=mime_type,
            web_view_link="https://drive.google.com/file/d/wiki-file-001/view",
            md5_checksum=None,
        )

    def download_text_file(self, *, access_token: str, file_id: str) -> str:
        if self.remote_text is None:
            raise DriveTextFileError("missing")
        return self.remote_text

    def upload_or_replace_text_file(
        self,
        *,
        access_token: str,
        folder_id: str,
        name: str,
        mime_type: str,
        content: str,
        existing_file_id: str | None = None,
    ) -> DriveUploadResult:
        if self.write_error:
            raise self.write_error
        self.upload_folder_id = folder_id
        self.uploaded_content = content
        self.replaced_file_id = existing_file_id
        self.remote_text = content
        return DriveUploadResult(
            file_id=existing_file_id or "wiki-file-001",
            web_view_link="https://drive.google.com/file/d/wiki-file-001/view",
        )
