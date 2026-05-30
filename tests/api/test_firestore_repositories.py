from datetime import UTC, datetime
from hashlib import sha256

from fastapi.testclient import TestClient

from sadify.extractors.business_files import ExtractedRequirementSource
from sadify_api.config import ApiConfig
from sadify_api.main import create_app
from sadify_api.schemas import (
    DriveRepoConnectRequest,
    DriveRepoRecord,
    ProjectSummary,
    SadPreviewResponse,
)
from sadify_api.services.auth import VerifiedFirebaseUser
from sadify_api.services.drive_client import (
    DriveFolder,
    DriveFolderRef,
    DriveTokens,
)
from sadify_api.services.drive_repo import FirestoreDriveRepoRepository
from sadify_api.services.projects import FirestoreProjectRepository
from sadify_api.services.sad_preview import SadPreviewRepository
from sadify_api.services.sad_save import FirestoreSadSaveRepository
from sadify_api.services.source_uploads import SourceRepository
from sadify_api.services.wiki_state import FirestoreWikiStateRepository, WikiState
from tests.api.test_sad_preview import VALID_PREVIEW


def test_firestore_project_create_writes_document_and_name_index():
    client = FakeFirestoreClient()
    repository = FirestoreProjectRepository(client)

    project = repository.create_project(
        grant_id="DG-000001",
        name="Laundry Workflow",
        drive_folder_id="folder-001",
        created_at=_dt(2026, 5, 29, 9),
    )

    assert project.project_id == "PR-000001"
    assert repository.get_project("DG-000001", "PR-000001") == project
    index_id = _project_name_index_id("DG-000001", "laundry workflow")
    assert client.docs[("project_name_index", index_id)]["project_id"] == "PR-000001"


def test_firestore_project_get_by_name_dedupes_normalized_names():
    repository = FirestoreProjectRepository(FakeFirestoreClient())

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
    assert repository.get_project_by_name("DG-000001", "LAUNDRY   WORKFLOW") == first
    assert repository.list_projects("DG-000001") == [first]


def test_firestore_project_list_orders_by_creation_sequence():
    repository = FirestoreProjectRepository(FakeFirestoreClient())

    first = repository.create_project(
        grant_id="DG-000001",
        name="Project A",
        drive_folder_id="folder-a",
        created_at=_dt(2026, 5, 29, 11),
    )
    second = repository.create_project(
        grant_id="DG-000001",
        name="Project B",
        drive_folder_id="folder-b",
        created_at=_dt(2026, 5, 29, 9),
    )

    assert repository.list_projects("DG-000001") == [first, second]


def test_firestore_project_sync_from_drive_upserts_unknown_folders():
    repository = FirestoreProjectRepository(FakeFirestoreClient())
    existing = repository.create_project(
        grant_id="DG-000001",
        name="Existing",
        drive_folder_id="folder-existing",
    )

    projects = repository.sync_from_drive(
        grant_id="DG-000001",
        drive_folders=[
            DriveFolderRef(
                folder_id="folder-existing",
                name="Existing Renamed In Drive",
                created_time=_dt(2026, 5, 28, 10),
                web_view_link=None,
            ),
            DriveFolderRef(
                folder_id="folder-new",
                name="New From Drive",
                created_time=_dt(2026, 5, 28, 11),
                web_view_link=None,
            ),
        ],
    )

    assert projects[0] == existing
    assert projects[1].project_id == "PR-000002"
    assert projects[1].name == "New From Drive"
    assert projects[1].created_at == _dt(2026, 5, 28, 11)


def test_firestore_project_next_counter_increments_atomically_per_project():
    repository = FirestoreProjectRepository(FakeFirestoreClient())

    assert repository.next_counter("DG-000001", "PR-000001", "sad_save") == 1
    assert repository.next_counter("DG-000001", "PR-000001", "sad_save") == 2
    assert repository.next_counter("DG-000001", "PR-000002", "sad_save") == 1


def test_firestore_sad_save_persists_record_and_reads_by_id():
    repository = FirestoreSadSaveRepository(FakeFirestoreClient())
    preview_repo = SadPreviewRepository()
    repo = _drive_repo_record()
    preview = _save_preview(preview_repo)

    record = repository.save_preview(
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        repo=repo,
        project_id="PR-000001",
        preview_record=preview,
        sources=[],
        saved_at=_dt(2026, 5, 29, 9),
    )

    assert record.save_id == "SV-000001"
    assert repository.get_save("SV-000001") == record
    assert repository.get_save(
        "SV-000001",
        repo_grant_id="DG-000001",
        project_id="PR-000001",
    ) == record


def test_firestore_sad_save_idempotent_returns_existing_record():
    repository = FirestoreSadSaveRepository(FakeFirestoreClient())
    preview_repo = SadPreviewRepository()
    repo = _drive_repo_record()
    preview = _save_preview(preview_repo)

    first = repository.save_preview(
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        repo=repo,
        project_id="PR-000001",
        preview_record=preview,
        sources=[],
    )
    second = repository.save_preview(
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        repo=repo,
        project_id="PR-000001",
        preview_record=preview,
        sources=[],
    )

    assert second == first
    assert repository.record_count() == 1
    assert second.sad_doc.file_id == first.sad_doc.file_id


def test_firestore_sad_save_list_for_project_desc_and_source_refs():
    repository = FirestoreSadSaveRepository(FakeFirestoreClient())
    preview_repo = SadPreviewRepository()
    source_repo = SourceRepository()
    repo = _drive_repo_record()
    source = source_repo.save_extracted_source(
        extracted=ExtractedRequirementSource(
            filename="laundry.pdf",
            file_type="pdf",
            normalized_text="Laundry workflow.",
            metadata={"byte_count": 10},
        ),
        mime_type="application/pdf",
    )
    older = repository.save_preview(
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        repo=repo,
        project_id="PR-000001",
        preview_record=_save_preview(preview_repo),
        sources=[],
        saved_at=_dt(2026, 5, 29, 9),
    )
    newer = repository.save_preview(
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        repo=repo,
        project_id="PR-000001",
        preview_record=_save_preview(preview_repo, source_references=[source.source_id]),
        sources=[source],
        saved_at=_dt(2026, 5, 29, 11),
    )

    saves = repository.list_for_project(
        grant_id="DG-000001",
        project_id="PR-000001",
    )

    assert saves == [newer, older]
    assert saves[0].manifest.source_ids == ["SRC-000001"]


def test_firestore_sad_save_counters_are_isolated_per_project():
    repository = FirestoreSadSaveRepository(FakeFirestoreClient())
    preview_repo = SadPreviewRepository()
    repo = _drive_repo_record()

    first = repository.save_preview(
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        repo=repo,
        project_id="PR-000001",
        preview_record=_save_preview(preview_repo),
        sources=[],
    )
    second = repository.save_preview(
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        repo=repo,
        project_id="PR-000002",
        preview_record=_save_preview(preview_repo),
        sources=[],
    )

    assert first.save_id == "SV-000001"
    assert second.save_id == "SV-000001"
    assert repository.get_save(
        "SV-000001",
        repo_grant_id="DG-000001",
        project_id="PR-000001",
    ) == first
    assert repository.get_save(
        "SV-000001",
        repo_grant_id="DG-000001",
        project_id="PR-000002",
    ) == second


def test_firestore_wiki_state_record_get_all_and_clear_per_project():
    repository = FirestoreWikiStateRepository(FakeFirestoreClient())
    state = WikiState(
        file_name="Wiki.md",
        file_id="wiki-file-001",
        hash="sha256:abc",
        updated_at=_dt(2026, 5, 29, 9),
    )

    repository.record_file_write("DG-000001", "PR-000001", state)
    repository.record_file_write(
        "DG-000001",
        "PR-000002",
        WikiState(
            file_name="Wiki.md",
            file_id="other-wiki-file",
            hash="sha256:other",
            updated_at=_dt(2026, 5, 29, 10),
        ),
    )

    assert repository.get_file_state("DG-000001", "PR-000001", "Wiki.md") == state
    assert repository.get_all_states("DG-000001", "PR-000001") == {"Wiki.md": state}
    repository.clear_states_for_project("DG-000001", "PR-000001")
    assert repository.get_file_state("DG-000001", "PR-000001", "Wiki.md") is None
    assert repository.get_file_state("DG-000001", "PR-000002", "Wiki.md") is not None


def test_firestore_drive_repo_connect_get_active_latest_and_disconnect():
    repository = FirestoreDriveRepoRepository(FakeFirestoreClient())

    record = repository.connect_repo(
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        request=DriveRepoConnectRequest(
            project_id="PROJ-000001",
            authorization_code="local-code",
            repo_folder_name="Operations MVP",
            create_new_repo=True,
        ),
        connected_at=_dt(2026, 5, 29, 9),
    )

    assert record.grant_id == "DG-000001"
    assert record.repo_folder_id == "LOCAL-DRIVE-FOLDER-000001"
    assert repository.get_active_repo("firebase-uid-001") == record
    disconnected = repository.disconnect_repo(
        owner_uid="firebase-uid-001",
        disconnected_at=_dt(2026, 5, 29, 10),
    )
    assert disconnected is not None
    assert disconnected.status == "disconnected"
    assert disconnected.saves_blocked is True
    assert repository.get_active_repo("firebase-uid-001") is None
    assert repository.get_latest_repo("firebase-uid-001") == disconnected


def test_firestore_drive_repo_set_active_project_and_available_projects_persist():
    repository = FirestoreDriveRepoRepository(FakeFirestoreClient())
    repo = repository.connect_repo(
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        request=DriveRepoConnectRequest(
            project_id="PROJ-000001",
            authorization_code="local-code",
            repo_folder_name="Operations MVP",
            create_new_repo=True,
        ),
    )
    project = ProjectSummary(
        project_id="PR-000001",
        name="Laundry Workflow",
        drive_folder_id="project-folder-001",
        created_at=_dt(2026, 5, 29, 9),
    )

    updated = repository.set_active_project(grant_id=repo.grant_id, project=project)
    refreshed = repository.set_available_projects(
        grant_id=repo.grant_id,
        projects=[project],
    )

    assert updated.active_project_id == "PR-000001"
    assert repository.get_active_repo("firebase-uid-001").active_project_id == "PR-000001"
    assert refreshed.available_projects == [project]


def test_firestore_drive_repo_live_connect_persists_secret_manager_record():
    repository = FirestoreDriveRepoRepository(FakeFirestoreClient())
    drive_client = FakeDriveClient()
    secret_store = FakeSecretStore()

    record = repository.connect_repo(
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        request=DriveRepoConnectRequest(
            project_id="PROJ-000001",
            authorization_code="live-code",
            repo_folder_name="Ignored",
            create_new_repo=True,
        ),
        mode="live",
        drive_client=drive_client,
        secret_store=secret_store,
        drive_folder_name="SADify Projects",
    )

    assert record.grant_id == "DG-000001"
    assert record.repo_folder_id == "drive-folder-001"
    assert record.token_store == "secret_manager"
    assert secret_store.refresh_tokens == {"firebase-uid-001": "refresh-token"}


def test_create_app_uses_firestore_repositories_when_configured(monkeypatch):
    firestore_client = FakeFirestoreClient()
    monkeypatch.setattr(
        "sadify_api.main.get_firestore_client",
        lambda project_id: firestore_client,
    )
    client = TestClient(
        create_app(
            config=ApiConfig(environment="test", persistence_mode="firestore"),
            token_verifier=AcceptingTokenVerifier(),
        )
    )

    response = client.post(
        "/drive/repo/connect",
        headers={"Authorization": "Bearer firebase-test-token"},
        json={
            "project_id": "PROJ-000001",
            "authorization_code": "local-code",
            "repo_folder_name": "Operations MVP",
            "create_new_repo": True,
        },
    )

    assert response.status_code == 200
    assert firestore_client.docs[("drive_repos", "DG-000001")]["grant_id"] == "DG-000001"


def _project_name_index_id(grant_id: str, normalized_name: str) -> str:
    digest = sha256(normalized_name.encode("utf-8")).hexdigest()
    return f"{grant_id}__{digest}"


def _drive_repo_record(grant_id: str = "DG-000001") -> DriveRepoRecord:
    return DriveRepoRecord(
        grant_id=grant_id,
        project_id="PROJ-000001",
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        status="connected",
        repo_folder_id=f"folder-{grant_id}",
        repo_folder_name="Operations MVP",
        repo_url=f"https://drive.google.com/drive/folders/folder-{grant_id}",
        requested_scopes=["https://www.googleapis.com/auth/drive.file"],
        folder_structure=[],
        token_store="local_metadata_only",
        saves_blocked=False,
        active_project_id="PR-000001",
        active_project_name="Project One",
        available_projects=[],
        created_at=_dt(2026, 5, 29, 8),
        updated_at=_dt(2026, 5, 29, 8),
    )


def _save_preview(
    repository: SadPreviewRepository,
    *,
    source_references: list[str] | None = None,
):
    payload = {
        **VALID_PREVIEW,
        "source_references": source_references or [],
    }
    return repository.save_preview(
        requirement_text="Need to validate an operational workflow.",
        analysis_id="AN-000001",
        preview=SadPreviewResponse.model_validate(payload),
    )


def _dt(year: int, month: int, day: int, hour: int):
    return datetime(year, month, day, hour, 0, tzinfo=UTC)


class AcceptingTokenVerifier:
    def verify_id_token(self, id_token: str) -> VerifiedFirebaseUser:
        return VerifiedFirebaseUser(
            uid="firebase-uid-001",
            email="owner@example.com",
            display_name="Project Owner",
            provider="firebase",
        )


class FakeFirestoreClient:
    def __init__(self) -> None:
        self.docs: dict[tuple[str, str], dict] = {}

    def collection(self, name: str):
        return FakeCollection(self, name)

    def transaction(self):
        return FakeTransaction(self)


class FakeCollection:
    def __init__(self, client: FakeFirestoreClient, name: str) -> None:
        self.client = client
        self.name = name

    def document(self, doc_id: str):
        return FakeDocumentReference(self.client, self.name, doc_id)

    def where(self, field_path: str, op_string: str, value):
        return FakeQuery(self.client, self.name).where(field_path, op_string, value)

    def order_by(self, field_path: str, direction: str | None = None):
        return FakeQuery(self.client, self.name).order_by(field_path, direction)

    def stream(self):
        return FakeQuery(self.client, self.name).stream()


class FakeDocumentReference:
    def __init__(self, client: FakeFirestoreClient, collection: str, doc_id: str) -> None:
        self.client = client
        self.collection = collection
        self.id = doc_id

    @property
    def key(self) -> tuple[str, str]:
        return (self.collection, self.id)

    def get(self, transaction=None):
        return FakeSnapshot(self.id, self.client.docs.get(self.key))

    def set(self, data: dict, merge: bool = False) -> None:
        if merge and self.key in self.client.docs:
            self.client.docs[self.key] = {**self.client.docs[self.key], **data}
        else:
            self.client.docs[self.key] = dict(data)

    def delete(self) -> None:
        self.client.docs.pop(self.key, None)


class FakeSnapshot:
    def __init__(self, doc_id: str, data: dict | None) -> None:
        self.id = doc_id
        self.exists = data is not None
        self._data = dict(data or {})

    def to_dict(self) -> dict:
        return dict(self._data)


class FakeQuery:
    def __init__(
        self,
        client: FakeFirestoreClient,
        collection: str,
        filters: list[tuple[str, str, object]] | None = None,
        orderings: list[tuple[str, str | None]] | None = None,
    ) -> None:
        self.client = client
        self.collection = collection
        self.filters = filters or []
        self.orderings = orderings or []

    def where(self, field_path: str, op_string: str, value):
        return FakeQuery(
            self.client,
            self.collection,
            [*self.filters, (field_path, op_string, value)],
            self.orderings,
        )

    def order_by(self, field_path: str, direction: str | None = None):
        return FakeQuery(
            self.client,
            self.collection,
            self.filters,
            [*self.orderings, (field_path, direction)],
        )

    def stream(self):
        rows = [
            FakeSnapshot(doc_id, data)
            for (collection, doc_id), data in self.client.docs.items()
            if collection == self.collection
            and all(_matches(data, field, op, value) for field, op, value in self.filters)
        ]
        for field, direction in reversed(self.orderings):
            rows.sort(
                key=lambda snapshot: snapshot.to_dict().get(field),
                reverse=direction == "DESCENDING",
            )
        return rows


class FakeTransaction:
    def __init__(self, client: FakeFirestoreClient) -> None:
        self.client = client

    def get(self, doc_ref: FakeDocumentReference):
        return doc_ref.get(transaction=self)

    def set(self, doc_ref: FakeDocumentReference, data: dict, merge: bool = False) -> None:
        doc_ref.set(data, merge=merge)

    def delete(self, doc_ref: FakeDocumentReference) -> None:
        doc_ref.delete()

    def commit(self) -> None:
        return None


class FakeSecretStore:
    def __init__(self) -> None:
        self.refresh_tokens: dict[str, str] = {}

    def put_user_refresh_token(self, uid: str, refresh_token: str) -> None:
        self.refresh_tokens[uid] = refresh_token

    def get_user_refresh_token(self, uid: str) -> str | None:
        return self.refresh_tokens.get(uid)


class FakeDriveClient:
    def exchange_authorization_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> DriveTokens:
        return DriveTokens(
            access_token="access-token",
            refresh_token="refresh-token",
            expiry=_dt(2026, 5, 29, 9),
        )

    def find_or_create_folder(
        self,
        access_token: str,
        folder_name: str,
    ) -> DriveFolder:
        return DriveFolder(folder_id="drive-folder-001", name=folder_name)


def _matches(data: dict, field: str, op: str, value) -> bool:
    if op != "==":
        raise AssertionError(f"Unsupported fake Firestore op: {op}")
    return data.get(field) == value
