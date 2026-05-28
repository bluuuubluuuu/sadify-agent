from datetime import UTC, datetime
from hashlib import sha256

from fastapi.testclient import TestClient

from sadify_api.config import ApiConfig
from sadify_api.main import create_app
from sadify_api.schemas import ProjectSummary, SadPreviewResponse
from sadify_api.services.auth import VerifiedFirebaseUser
from sadify_api.services.drive_client import (
    DriveFileRef,
    DriveFolder,
    DriveFolderRef,
    DriveTextFileError,
    DriveTokens,
    DriveUploadResult,
)
from sadify_api.services.drive_repo import DriveRepoRepository
from sadify_api.services.sad_preview import SadPreviewRepository
from sadify_api.services.sad_save import SadSaveRepository
from sadify_api.services.source_uploads import SourceRepository
from sadify_api.services.wiki_compose import MANAGED_WIKI_FILE_NAMES
from sadify_api.services.wiki_state import WikiState, WikiStateRepository


EXPECTED_NAMES = list(MANAGED_WIKI_FILE_NAMES)


class AcceptingTokenVerifier:
    def verify_id_token(self, id_token: str) -> VerifiedFirebaseUser:
        return VerifiedFirebaseUser(
            uid="firebase-uid-001",
            email="owner@example.com",
            display_name="Project Owner",
            provider="firebase",
        )


def test_wiki_preview_returns_all_eight_files_first_time():
    client, _drive, _preview, _save, _wiki, fake_drive = _client_with_saved_sad()

    response = client.post("/sad/wiki/preview", headers=_auth_header(), json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["first_time_write"] is True
    assert payload["requires_confirmation"] is False
    assert payload["changed_files"] == []
    assert [file["name"] for file in payload["files"]] == EXPECTED_NAMES
    assert payload["files"][0]["relative_path"] == "Wiki/Wiki.md"
    assert payload["files"][0]["proposed_markdown"].startswith("---\n")
    assert all(file["remote_exists"] is False for file in payload["files"])
    assert fake_drive.folder_lookups[-1] == ("Wiki", "project-folder-001")
    assert [call[1] for call in fake_drive.find_file_calls] == EXPECTED_NAMES
    assert all(call[0] == "wiki-folder-001" for call in fake_drive.find_file_calls)


def test_wiki_preview_returns_no_confirmation_when_all_hashes_match():
    client, drive_repo, _preview, _save, wiki_state, fake_drive = _client_with_saved_sad()
    repo = drive_repo.get_active_repo("firebase-uid-001")
    for name in EXPECTED_NAMES:
        remote = f"# Existing {name}"
        fake_drive.remote_text_by_name[name] = remote
        wiki_state.record_file_write(
            repo.grant_id,
            repo.active_project_id,
            WikiState(
                file_name=name,
                file_id=f"remote-{name}",
                hash=_hash(remote),
                updated_at=datetime(2026, 5, 27, 9, 0, tzinfo=UTC),
            ),
        )

    response = client.post("/sad/wiki/preview", headers=_auth_header(), json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["first_time_write"] is False
    assert payload["requires_confirmation"] is False
    assert payload["changed_files"] == []
    assert all(file["remote_markdown"] is None for file in payload["files"])


def test_wiki_preview_returns_changed_file_when_remote_drifted():
    client, drive_repo, _preview, _save, wiki_state, fake_drive = _client_with_saved_sad()
    repo = drive_repo.get_active_repo("firebase-uid-001")
    fake_drive.remote_text_by_name["workflows.md"] = "# Edited in Drive"
    wiki_state.record_file_write(
        repo.grant_id,
        repo.active_project_id,
        WikiState(
            file_name="workflows.md",
            file_id="remote-workflows.md",
            hash=_hash("# Prior workflows"),
            updated_at=datetime(2026, 5, 27, 9, 0, tzinfo=UTC),
        ),
    )

    response = client.post("/sad/wiki/preview", headers=_auth_header(), json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["requires_confirmation"] is True
    assert payload["changed_files"] == ["workflows.md"]
    workflow_file = _file_payload(payload, "workflows.md")
    assert workflow_file["remote_markdown"] == "# Edited in Drive"
    assert workflow_file["remote_hash"] == _hash("# Edited in Drive")


def test_wiki_preview_blocks_unsigned():
    client, _drive, _preview, _save, _wiki, _fake_drive = _client_with_saved_sad()

    response = client.post("/sad/wiki/preview", json={})

    assert response.status_code == 401
    assert response.json()["detail"] == {
        "code": "WIKI_AUTH_REQUIRED",
        "message": "Sign in before updating the wiki.",
    }


def test_wiki_preview_blocks_without_active_repo():
    client, _drive, _preview, _save, _wiki, _fake_drive = _client()

    response = client.post("/sad/wiki/preview", headers=_auth_header(), json={})

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "WIKI_REPO_REQUIRED"


def test_wiki_preview_blocks_without_prior_sad_save():
    client, drive_repo, _preview, _save, _wiki, _fake_drive = _client()
    _connect_repo(client)
    _set_active_project(drive_repo)

    response = client.post("/sad/wiki/preview", headers=_auth_header(), json={})

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "WIKI_SAVE_REQUIRED"


def test_wiki_preview_blocks_when_saved_preview_is_no_longer_in_memory():
    client, _drive, preview_repo, _save, _wiki, _fake_drive = _client_with_saved_sad()
    preview_repo._records.clear()

    response = client.post("/sad/wiki/preview", headers=_auth_header(), json={})

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "WIKI_SAVE_REQUIRED"
    assert "regenerated" in response.json()["detail"]["message"].lower()


def test_wiki_preview_blocks_when_live_mode_disabled():
    client, drive_repo, _preview, _save, _wiki, _fake_drive = _client(drive_live_enabled=False)
    _connect_repo(client)
    _set_active_project(drive_repo)

    response = client.post("/sad/wiki/preview", headers=_auth_header(), json={})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "WIKI_LIVE_MODE_DISABLED"


def test_wiki_update_writes_all_eight_files_first_time_no_backup():
    client, _drive, _preview, _save, wiki_state, fake_drive = _client_with_saved_sad()

    response = client.post(
        "/sad/wiki/update",
        headers=_auth_header(),
        json={"expected_remote_hashes": {}, "force_overwrite": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [file["name"] for file in payload["files"]] == EXPECTED_NAMES
    assert payload["backup"] == {"created": False, "path": "", "file_count": 0}
    assert [call["name"] for call in fake_drive.wiki_upload_calls] == EXPECTED_NAMES
    assert fake_drive.backup_upload_calls == []
    assert all(call["folder_id"] == "wiki-folder-001" for call in fake_drive.wiki_upload_calls)
    for file in payload["files"]:
        state = wiki_state.get_file_state("DG-000001", "PR-000001", file["name"])
        assert state is not None
        assert state.hash == file["hash"]


def test_wiki_update_creates_backup_subfolder_when_remote_files_exist():
    client, _drive, _preview, _save, _wiki, fake_drive = _client_with_saved_sad()
    for name in EXPECTED_NAMES:
        fake_drive.remote_text_by_name[name] = f"# Remote {name}"

    response = client.post(
        "/sad/wiki/update",
        headers=_auth_header(),
        json={
            "expected_remote_hashes": {
                name: _hash(f"# Remote {name}") for name in EXPECTED_NAMES
            },
            "force_overwrite": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["backup"]["created"] is True
    assert payload["backup"]["path"].startswith("_SADify/wiki-backups/")
    assert payload["backup"]["file_count"] == 8
    assert [call["name"] for call in fake_drive.backup_upload_calls] == EXPECTED_NAMES
    assert ("_SADify", "project-folder-001") in fake_drive.folder_lookups
    assert ("wiki-backups", "sadify-folder-001") in fake_drive.folder_lookups


def test_wiki_update_blocks_with_409_conflict_when_any_file_drifts_and_force_false():
    client, _drive, _preview, _save, _wiki, fake_drive = _client_with_saved_sad()
    fake_drive.remote_text_by_name["workflows.md"] = "# Edited in Drive"

    response = client.post(
        "/sad/wiki/update",
        headers=_auth_header(),
        json={
            "expected_remote_hashes": {"workflows.md": _hash("# Prior workflows")},
            "force_overwrite": False,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "WIKI_CONFLICT"
    assert fake_drive.wiki_upload_calls == []
    assert fake_drive.backup_upload_calls == []


def test_wiki_update_changed_files_payload_lists_drifted_filenames():
    client, _drive, _preview, _save, _wiki, fake_drive = _client_with_saved_sad()
    fake_drive.remote_text_by_name["workflows.md"] = "# Edited workflow"
    fake_drive.remote_text_by_name["reports.md"] = "# Edited reports"

    response = client.post(
        "/sad/wiki/update",
        headers=_auth_header(),
        json={
            "expected_remote_hashes": {
                "workflows.md": _hash("# Prior workflow"),
                "reports.md": _hash("# Prior reports"),
            },
            "force_overwrite": False,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["changed_files"] == ["workflows.md", "reports.md"]


def test_wiki_update_overwrites_all_when_force_true_after_conflict():
    client, _drive, _preview, _save, _wiki, fake_drive = _client_with_saved_sad()
    for name in EXPECTED_NAMES:
        fake_drive.remote_text_by_name[name] = f"# Remote {name}"

    response = client.post(
        "/sad/wiki/update",
        headers=_auth_header(),
        json={
            "expected_remote_hashes": {"workflows.md": _hash("# stale")},
            "force_overwrite": True,
        },
    )

    assert response.status_code == 200
    assert [call["name"] for call in fake_drive.wiki_upload_calls] == EXPECTED_NAMES
    assert response.json()["backup"]["created"] is True


def test_wiki_update_records_per_file_hashes_after_success():
    client, _drive, _preview, _save, wiki_state, _fake_drive = _client_with_saved_sad()

    response = client.post(
        "/sad/wiki/update",
        headers=_auth_header(),
        json={"expected_remote_hashes": {}, "force_overwrite": False},
    )

    assert response.status_code == 200
    states = wiki_state.get_all_states("DG-000001", "PR-000001")
    assert set(states) == set(EXPECTED_NAMES)
    for file in response.json()["files"]:
        assert states[file["name"]].file_id == file["file_id"]
        assert states[file["name"]].hash == file["hash"]


def test_wiki_update_returns_backup_path_and_file_count():
    client, _drive, _preview, _save, _wiki, fake_drive = _client_with_saved_sad()
    fake_drive.remote_text_by_name["Wiki.md"] = "# Remote Wiki"

    response = client.post(
        "/sad/wiki/update",
        headers=_auth_header(),
        json={
            "expected_remote_hashes": {"Wiki.md": _hash("# Remote Wiki")},
            "force_overwrite": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["backup"]["path"].startswith("_SADify/wiki-backups/")
    assert response.json()["backup"]["file_count"] == 1


def test_wiki_update_surfaces_drive_write_failure_as_502():
    client, _drive, _preview, _save, _wiki, fake_drive = _client_with_saved_sad()
    fake_drive.write_error = DriveTextFileError("write failed")

    response = client.post(
        "/sad/wiki/update",
        headers=_auth_header(),
        json={"expected_remote_hashes": {}, "force_overwrite": False},
    )

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "WIKI_WRITE_FAILED"


def test_wiki_update_surfaces_backup_failure_as_502_wiki_backup_failed():
    client, _drive, _preview, _save, _wiki, fake_drive = _client_with_saved_sad()
    fake_drive.remote_text_by_name["Wiki.md"] = "# Remote Wiki"
    fake_drive.backup_error = DriveTextFileError("backup failed")

    response = client.post(
        "/sad/wiki/update",
        headers=_auth_header(),
        json={
            "expected_remote_hashes": {"Wiki.md": _hash("# Remote Wiki")},
            "force_overwrite": False,
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "WIKI_BACKUP_FAILED"
    assert fake_drive.wiki_upload_calls == []


def test_wiki_update_writes_into_wiki_subfolder_under_project_root():
    client, _drive, _preview, _save, _wiki, fake_drive = _client_with_saved_sad()

    response = client.post(
        "/sad/wiki/update",
        headers=_auth_header(),
        json={"expected_remote_hashes": {}, "force_overwrite": False},
    )

    assert response.status_code == 200
    assert ("Wiki", "project-folder-001") in fake_drive.folder_lookups
    assert all(call["folder_id"] == "wiki-folder-001" for call in fake_drive.wiki_upload_calls)


def test_wiki_preview_reads_from_wiki_subfolder_not_project_root():
    client, _drive, _preview, _save, _wiki, fake_drive = _client_with_saved_sad()
    fake_drive.remote_text_by_name["Wiki.md"] = "# Existing Wiki"

    response = client.post("/sad/wiki/preview", headers=_auth_header(), json={})

    assert response.status_code == 200
    assert ("Wiki", "project-folder-001") in fake_drive.folder_lookups
    assert fake_drive.find_file_calls[0] == ("wiki-folder-001", "Wiki.md")


def test_wiki_preview_uses_latest_save_for_active_project_only():
    client, drive_repo, preview_repo, save_repo, _wiki, _fake_drive = _client()
    _connect_repo(client)
    _create_project(client, "Front Desk Repairs")
    project_one_repo = drive_repo.get_active_repo("firebase-uid-001")
    _save_sad(
        save_repo,
        preview_repo,
        project_one_repo,
        title="Front Desk SAD",
        requirement_text="Front desk repair workflow.",
        created_at=datetime(2026, 5, 27, 9, 0, tzinfo=UTC),
    )
    _create_project(client, "Warehouse Returns")
    project_two_repo = drive_repo.get_active_repo("firebase-uid-001")
    _save_sad(
        save_repo,
        preview_repo,
        project_two_repo,
        title="Warehouse SAD",
        requirement_text="Warehouse return workflow.",
        created_at=datetime(2026, 5, 27, 10, 0, tzinfo=UTC),
    )
    response = client.post(
        "/projects/switch",
        headers=_auth_header(),
        json={"project_id": "PR-000001"},
    )
    assert response.status_code == 200

    response = client.post("/sad/wiki/preview", headers=_auth_header(), json={})

    assert response.status_code == 200
    wiki_index = _file_payload(response.json(), "Wiki.md")
    requirements = _file_payload(response.json(), "requirements.md")
    assert "SV-000001" in wiki_index["proposed_markdown"]
    assert "Front desk repair workflow" in requirements["proposed_markdown"]
    assert "Warehouse return workflow" not in requirements["proposed_markdown"]


def _client_with_saved_sad(**kwargs):
    client, drive_repo, preview_repo, save_repo, wiki_state, fake_drive = _client(**kwargs)
    _connect_repo(client)
    _create_project(client)
    repo = drive_repo.get_active_repo("firebase-uid-001")
    _save_sad(save_repo, preview_repo, repo)
    return client, drive_repo, preview_repo, save_repo, wiki_state, fake_drive


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
    return TestClient(app), drive_repo, preview_repo, save_repo, wiki_state, fake_drive


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


def _create_project(client: TestClient, name: str = "Repair Project"):
    response = client.post(
        "/projects",
        headers=_auth_header(),
        json={"name": name},
    )
    assert response.status_code == 200
    return response.json()


def _set_active_project(
    drive_repo: DriveRepoRepository,
    *,
    project_id: str = "PR-000001",
    name: str = "Repair Project",
    folder_id: str = "project-folder-001",
) -> None:
    drive_repo.set_active_project(
        grant_id="DG-000001",
        project=ProjectSummary(
            project_id=project_id,
            name=name,
            drive_folder_id=folder_id,
            created_at=datetime(2026, 5, 27, 9, 0, tzinfo=UTC),
        ),
    )


def _save_sad(
    save_repo: SadSaveRepository,
    preview_repo: SadPreviewRepository,
    repo,
    *,
    title: str = "Phone Repair SAD",
    requirement_text: str = "A workshop tracks repairs.",
    created_at: datetime = datetime(2026, 5, 27, 9, 0, tzinfo=UTC),
):
    preview_record = preview_repo.save_preview(
        requirement_text=requirement_text,
        analysis_id="AN-000001",
        preview=_preview(title=title),
        created_at=created_at,
    )
    return save_repo.save_preview(
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        repo=repo,
        project_id=repo.active_project_id,
        preview_record=preview_record,
        sources=[],
    )


def _preview(title: str = "Phone Repair SAD") -> SadPreviewResponse:
    return SadPreviewResponse.model_validate(
        {
            "title": title,
            "temporary_notice": "Temporary preview.",
            "it_readiness": {
                "label": "Layer 2",
                "score": 70,
                "confidence": "Medium",
                "checklist": [
                    {
                        "id": "data",
                        "label": "Data model",
                        "status": "needs_input",
                        "reason": "Detailed schema comes later.",
                    }
                ],
            },
            "sections": [
                {
                    "title": "Goal and Scope",
                    "body": "Track repair jobs from drop-off through collection.",
                    "source_references": [],
                },
                {
                    "title": "Users and Roles",
                    "body": "Counter staff create jobs; technicians update repair status.",
                    "source_references": [],
                },
                {
                    "title": "Workflow Steps",
                    "body": "Counter to technician to pickup desk.",
                    "source_references": [],
                },
                {
                    "title": "Data and Records",
                    "body": "Customer, device, parts, payment, and status records.",
                    "source_references": [],
                },
            ],
            "assumptions": ["SMS wording can be finalized later."],
            "open_questions": ["Confirm refund approval threshold."],
            "source_references": [],
            "change_tracking": {
                "summary": "Initial preview.",
                "paths": ["requirements"],
            },
        }
    )


def _auth_header() -> dict[str, str]:
    return {"Authorization": "Bearer firebase-test-token"}


def _hash(value: str) -> str:
    return f"sha256:{sha256(value.encode('utf-8')).hexdigest()}"


def _file_payload(payload: dict, name: str) -> dict:
    return next(file for file in payload["files"] if file["name"] == name)


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
        self.remote_text_by_name: dict[str, str] = {}
        self.write_error: Exception | None = None
        self.backup_error: Exception | None = None
        self.folder_lookups: list[tuple[str, str | None]] = []
        self.find_file_calls: list[tuple[str, str]] = []
        self.wiki_upload_calls: list[dict[str, str | None]] = []
        self.backup_upload_calls: list[dict[str, str | None]] = []
        self.download_counts: dict[str, int] = {}

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
        self.folder_lookups.append((folder_name, parent_folder_id))
        folder_ids = {
            ("SADify Projects", None): "drive-folder-001",
            ("Repair Project", "drive-folder-001"): "project-folder-001",
            ("Front Desk Repairs", "drive-folder-001"): "project-folder-001",
            ("Warehouse Returns", "drive-folder-001"): "project-folder-002",
            ("Wiki", "project-folder-001"): "wiki-folder-001",
            ("Wiki", "project-folder-002"): "wiki-folder-002",
            ("_SADify", "project-folder-001"): "sadify-folder-001",
            ("_SADify", "project-folder-002"): "sadify-folder-002",
            ("wiki-backups", "sadify-folder-001"): "wiki-backups-folder-001",
            ("wiki-backups", "sadify-folder-002"): "wiki-backups-folder-002",
        }
        folder_id = folder_ids.get((folder_name, parent_folder_id), f"backup-{folder_name}")
        return DriveFolder(folder_id=folder_id, name=folder_name)

    def list_subfolders(
        self,
        access_token: str,
        parent_folder_id: str,
    ) -> list[DriveFolderRef]:
        return []

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
        self.find_file_calls.append((folder_id, name))
        if name not in self.remote_text_by_name:
            return None
        return DriveFileRef(
            file_id=f"remote-{name}",
            name=name,
            mime_type=mime_type,
            web_view_link=f"https://drive.google.com/file/d/remote-{name}/view",
            md5_checksum=None,
        )

    def download_text_file(self, *, access_token: str, file_id: str) -> str:
        prior_downloads = self.download_counts.get(file_id, 0)
        self.download_counts[file_id] = prior_downloads + 1
        if self.backup_error and prior_downloads > 0:
            raise self.backup_error
        name = file_id.replace("remote-", "", 1)
        if name not in self.remote_text_by_name:
            raise DriveTextFileError("missing")
        return self.remote_text_by_name[name]

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
        if self.write_error and folder_id == "wiki-folder-001":
            raise self.write_error
        call = {
            "folder_id": folder_id,
            "name": name,
            "content": content,
            "existing_file_id": existing_file_id,
        }
        if folder_id == "wiki-folder-001":
            self.wiki_upload_calls.append(call)
            self.remote_text_by_name[name] = content
            file_id = existing_file_id or f"created-{name}"
        else:
            self.backup_upload_calls.append(call)
            file_id = f"backup-{name}"
        return DriveUploadResult(
            file_id=file_id,
            web_view_link=f"https://drive.google.com/file/d/{file_id}/view",
        )
