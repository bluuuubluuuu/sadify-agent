import os
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from sadify_api.config import load_api_config
from sadify_api.schemas import (
    DriveRepoConnectRequest,
    DriveRepoRecord,
    ProjectSummary,
    SadPreviewResponse,
)
from sadify_api.services.firestore_client import get_firestore_client, safe_doc_id
from sadify_api.services.drive_repo import FirestoreDriveRepoRepository
from sadify_api.services.projects import FirestoreProjectRepository
from sadify_api.services.sad_preview import SadPreviewRepository
from sadify_api.services.sad_save import (
    FirestoreSadSaveRepository,
    _idempotency_hash,
    _idempotency_key,
)
from sadify_api.services.wiki_state import FirestoreWikiStateRepository, WikiState
from tests.api.test_sad_preview import VALID_PREVIEW


pytestmark = pytest.mark.skipif(
    os.getenv("SADIFY_FIRESTORE_LIVE") != "1",
    reason="Set SADIFY_FIRESTORE_LIVE=1 to run the opt-in Firestore smoke.",
)


def test_firestore_live_project_round_trip():
    client = get_firestore_client(load_api_config().google_cloud_project)
    repository = FirestoreProjectRepository(client)
    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    grant_id = f"DG-FIRESTORE-SMOKE-{suffix}"
    project_name = f"Firestore Smoke {suffix}"

    try:
        project = repository.create_project(
            grant_id=grant_id,
            name=project_name,
            drive_folder_id=f"folder-{suffix}",
        )

        assert repository.get_project(grant_id, project.project_id) == project
        assert repository.get_project_by_name(grant_id, project_name) == project
        assert repository.list_projects(grant_id) == [project]
    finally:
        _delete_doc(client, "projects", safe_doc_id(grant_id, "PR-000001"))
        _delete_doc(
            client,
            "project_name_index",
            safe_doc_id(grant_id, _name_digest(project_name)),
        )
        _delete_doc(client, "counters", safe_doc_id("project", grant_id, "project"))


def test_firestore_live_sad_save_round_trip():
    client = get_firestore_client(load_api_config().google_cloud_project)
    repository = FirestoreSadSaveRepository(client)
    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    grant_id = f"DG-FIRESTORE-SMOKE-{suffix}"
    project_id = "PR-000001"
    owner_uid = f"smoke-uid-{suffix}"
    repo = _drive_repo_record(grant_id, project_id)
    preview = SadPreviewRepository().save_preview(
        requirement_text="Need to validate an operational workflow.",
        analysis_id="AN-FIRESTORE-SMOKE",
        preview=SadPreviewResponse.model_validate(VALID_PREVIEW),
    )

    try:
        record = repository.save_preview(
            owner_uid=owner_uid,
            owner_email="owner@example.com",
            repo=repo,
            project_id=project_id,
            preview_record=preview,
            sources=[],
        )

        assert record.save_id == "SV-000001"
        assert (
            repository.get_save(
                record.save_id, repo_grant_id=grant_id, project_id=project_id
            )
            == record
        )
        assert repository.list_for_project(
            grant_id=grant_id, project_id=project_id
        ) == [record]

        # Idempotent re-save returns the same record (no duplicate).
        again = repository.save_preview(
            owner_uid=owner_uid,
            owner_email="owner@example.com",
            repo=repo,
            project_id=project_id,
            preview_record=preview,
            sources=[],
        )
        assert again == record
    finally:
        _delete_doc(
            client, "sad_saves", safe_doc_id(grant_id, project_id, "SV-000001")
        )
        idempotency_key = _idempotency_key(
            owner_uid=owner_uid,
            repo_grant_id=grant_id,
            project_id=project_id,
            preview_id=preview.preview_id,
            preview_revision=preview.created_at.isoformat(),
        )
        _delete_doc(
            client, "sad_save_idempotency", _idempotency_hash(idempotency_key)
        )
        for name in ("sad_save", "manifest", "artifact"):
            _delete_doc(
                client,
                "counters",
                safe_doc_id("sad_save", grant_id, project_id, name),
            )


def test_firestore_live_wiki_state_round_trip():
    client = get_firestore_client(load_api_config().google_cloud_project)
    repository = FirestoreWikiStateRepository(client)
    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    grant_id = f"DG-FIRESTORE-SMOKE-{suffix}"
    project_id = "PR-000001"
    state = WikiState(
        file_name="Wiki.md",
        file_id=f"wiki-{suffix}",
        hash=f"sha256:{suffix}",
        updated_at=datetime.now(UTC),
    )

    try:
        repository.record_file_write(grant_id, project_id, state)

        assert repository.get_file_state(grant_id, project_id, "Wiki.md") == state
        assert repository.get_all_states(grant_id, project_id) == {"Wiki.md": state}
    finally:
        repository.clear_states_for_project(grant_id, project_id)
        assert repository.get_file_state(grant_id, project_id, "Wiki.md") is None


def test_firestore_live_drive_repo_round_trip():
    client = get_firestore_client(load_api_config().google_cloud_project)
    repository = FirestoreDriveRepoRepository(client)
    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    owner_uid = f"smoke-uid-{suffix}"
    record = None

    try:
        record = repository.connect_repo(
            owner_uid=owner_uid,
            owner_email="owner@example.com",
            request=DriveRepoConnectRequest(
                project_id="PROJ-FIRESTORE-SMOKE",
                authorization_code="local-code",
                repo_folder_name="Firestore Smoke Repo",
                create_new_repo=True,
            ),
            mode="local",
        )

        assert repository.get_active_repo(owner_uid) == record
        assert repository.get_latest_repo(owner_uid) == record

        project = ProjectSummary(
            project_id="PR-000001",
            name="Firestore Smoke Project",
            drive_folder_id="smoke-project-folder",
            created_at=datetime.now(UTC),
        )
        updated = repository.set_active_project(grant_id=record.grant_id, project=project)
        assert updated.active_project_id == "PR-000001"
        assert (
            repository.get_active_repo(owner_uid).active_project_id == "PR-000001"
        )
    finally:
        # The global drive_repo grant/local_folder counter docs
        # (counters/drive_repo__grant, counters/drive_repo__local_folder) are
        # intentionally left in Firestore. They are shared sequence docs (like
        # counters/sad_save__fake_doc); deleting them after a live smoke could
        # cause future DG-/LOCAL-DRIVE-FOLDER ID reuse. Only the per-run
        # drive_repos record is cleaned up.
        if record is not None:
            _delete_doc(client, "drive_repos", safe_doc_id(record.grant_id))


def _drive_repo_record(grant_id: str, project_id: str) -> DriveRepoRecord:
    return DriveRepoRecord(
        grant_id=grant_id,
        project_id=project_id,
        owner_uid="smoke-owner",
        owner_email="owner@example.com",
        status="connected",
        repo_folder_id=f"folder-{grant_id}",
        repo_folder_name="Firestore Smoke Repo",
        repo_url=f"https://drive.google.com/drive/folders/folder-{grant_id}",
        requested_scopes=["https://www.googleapis.com/auth/drive.file"],
        folder_structure=[],
        token_store="local_metadata_only",
        saves_blocked=False,
        active_project_id=project_id,
        active_project_name="Firestore Smoke Project",
        available_projects=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _delete_doc(client, collection: str, doc_id: str) -> None:
    client.collection(collection).document(doc_id).delete()


def _name_digest(value: str) -> str:
    normalized = " ".join(value.strip().lower().split())
    return sha256(normalized.encode("utf-8")).hexdigest()
