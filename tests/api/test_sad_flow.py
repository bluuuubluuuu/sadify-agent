from datetime import UTC, datetime

import pytest

from sadify_api.config import ApiConfig
from sadify_api.schemas import (
    DriveRepoRecord,
    ProjectSummary,
    SadPreviewRequest,
    SadSaveRequest,
    WikiUpdateRequest,
)
from sadify_api.services import sad_flow
from sadify_api.services.drive_repo import DriveRepoRepository
from sadify_api.services.sad_preview import SadPreviewRepository
from sadify_api.services.sad_flow import (
    SadPreviewBlockedError,
    SadSaveFlowError,
    run_sad_preview,
    run_sad_save,
)
from sadify_api.services.sad_save import SadSaveRepository
from sadify_api.services.source_uploads import SourceRepository
from sadify_api.services.wiki_state import WikiStateRepository
from tests.api.test_gemini_structured import VALID_PAYLOAD as VALID_ANALYSIS
from tests.api.test_sad_save import (
    AcceptingTokenVerifier,
    _connect_repo,
    _create_project,
    _save_preview,
)
from tests.api.test_sad_preview import (
    FakeSadPreviewModel,
    VALID_PREVIEW,
    _analysis_with_blocking_basics,
)
from tests.api.test_wiki_routes import EXPECTED_NAMES, FakeDriveClient, _hash, _preview


def test_run_sad_preview_saves_record():
    repository = SadPreviewRepository()
    model = FakeSadPreviewModel([VALID_PREVIEW.copy()])
    request = SadPreviewRequest(
        requirement_text="Need to validate an operational workflow.",
        analysis_id="AN-000001",
        analysis=_analysis_with_blocking_basics(),
        source_context="[SRC-000001] workflow.md\nThe workflow needs approval.",
        source_references=["SRC-000001"],
    )

    record = run_sad_preview(
        request=request,
        model=model,
        repository=repository,
    )

    assert record.preview_id == "SP-000001"
    assert record.analysis_id == "AN-000001"
    assert record.preview.title == "Operational Workflow Validation"
    assert repository.get_preview("SP-000001") == record
    assert "Source context" in model.requests[0][0]
    assert model.requests[0][1] is False


def test_run_sad_preview_blocked_raises():
    repository = SadPreviewRepository()
    model = FakeSadPreviewModel([VALID_PREVIEW.copy()])
    request = SadPreviewRequest(
        requirement_text="Need to validate an operational workflow.",
        analysis_id="AN-000001",
        analysis=VALID_ANALYSIS,
        source_references=[],
    )

    with pytest.raises(SadPreviewBlockedError) as exc_info:
        run_sad_preview(
            request=request,
            model=model,
            repository=repository,
        )

    assert exc_info.value.missing_basics == ["users_roles"]
    assert repository.get_preview("SP-000001") is None
    assert model.requests == []


def test_run_sad_save_creates_local_record():
    user = AcceptingTokenVerifier().verify_id_token("firebase-test-token")
    drive_repo_repository = DriveRepoRepository()
    preview_repository = SadPreviewRepository()
    sad_save_repository = SadSaveRepository()
    source_repository = SourceRepository()
    client = _client_for_repo_setup(
        drive_repo_repository=drive_repo_repository,
        preview_repository=preview_repository,
        sad_save_repository=sad_save_repository,
        source_repository=source_repository,
    )
    _connect_repo(client)
    _create_project(client, "Operations App")
    preview_record = _save_preview(preview_repository)

    record = run_sad_save(
        user=user,
        request=SadSaveRequest(preview_id=preview_record.preview_id),
        repository=preview_repository,
        drive_repo_repository=drive_repo_repository,
        source_repository=source_repository,
        sad_save_repository=sad_save_repository,
        config=ApiConfig(environment="test"),
        drive_client=None,
        secret_store=None,
        project_repository=None,
    )

    assert record.save_id == "SV-000001"
    assert record.project_id == "PR-000001"
    assert record.preview_id == "SP-000001"
    assert record.sad_doc.file_id == "LOCAL-GDOC-000001"


def test_run_sad_save_blocks_without_active_repo():
    user = AcceptingTokenVerifier().verify_id_token("firebase-test-token")
    preview_repository = SadPreviewRepository()
    preview_record = _save_preview(preview_repository)

    with pytest.raises(SadSaveFlowError) as exc_info:
        run_sad_save(
            user=user,
            request=SadSaveRequest(preview_id=preview_record.preview_id),
            repository=preview_repository,
            drive_repo_repository=DriveRepoRepository(),
            source_repository=SourceRepository(),
            sad_save_repository=SadSaveRepository(),
            config=ApiConfig(environment="test"),
            drive_client=None,
            secret_store=None,
            project_repository=None,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "SAD_SAVE_REPO_REQUIRED"
    assert exc_info.value.message == "Connect a Google Drive project repo before saving."


def test_run_wiki_preview_returns_first_time_files():
    preview_repository, _save_repository, wiki_state, context, fake_drive = (
        _wiki_flow_fixture()
    )

    response = sad_flow.run_wiki_preview(
        context=context,
        repository=preview_repository,
        wiki_state_repository=wiki_state,
    )

    assert response.first_time_write is True
    assert response.requires_confirmation is False
    assert response.changed_files == []
    assert [file.name for file in response.files] == EXPECTED_NAMES
    assert response.files[0].relative_path == "Wiki/Wiki.md"
    assert [call[1] for call in fake_drive.find_file_calls] == EXPECTED_NAMES


def test_run_wiki_update_writes_files_and_records_state():
    preview_repository, _save_repository, wiki_state, context, fake_drive = (
        _wiki_flow_fixture()
    )

    response = sad_flow.run_wiki_update(
        context=context,
        request=WikiUpdateRequest(expected_remote_hashes={}, force_overwrite=False),
        repository=preview_repository,
        wiki_state_repository=wiki_state,
    )

    assert [file.name for file in response.files] == EXPECTED_NAMES
    assert response.backup.created is False
    assert fake_drive.backup_upload_calls == []
    assert [call["name"] for call in fake_drive.wiki_upload_calls] == EXPECTED_NAMES
    for file in response.files:
        state = wiki_state.get_file_state("DG-000001", "PR-000001", file.name)
        assert state is not None
        assert state.hash == file.hash


def test_run_wiki_update_conflict_raises_changed_files_without_writes():
    preview_repository, _save_repository, wiki_state, context, fake_drive = (
        _wiki_flow_fixture()
    )
    fake_drive.remote_text_by_name["workflows.md"] = "# Edited in Drive"

    with pytest.raises(sad_flow.WikiFlowError) as exc_info:
        sad_flow.run_wiki_update(
            context=context,
            request=WikiUpdateRequest(
                expected_remote_hashes={"workflows.md": _hash("# Prior workflows")},
                force_overwrite=False,
            ),
            repository=preview_repository,
            wiki_state_repository=wiki_state,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "WIKI_CONFLICT"
    assert (
        exc_info.value.message
        == "The wiki was changed in Drive since SADify last wrote it. Confirm overwrite."
    )
    assert exc_info.value.changed_files == ["workflows.md"]
    assert fake_drive.wiki_upload_calls == []
    assert fake_drive.backup_upload_calls == []


def _client_for_repo_setup(
    *,
    drive_repo_repository: DriveRepoRepository,
    preview_repository: SadPreviewRepository,
    sad_save_repository: SadSaveRepository,
    source_repository: SourceRepository,
):
    from fastapi.testclient import TestClient

    from sadify_api.main import create_app

    return TestClient(
        create_app(
            token_verifier=AcceptingTokenVerifier(),
            drive_repo_repository=drive_repo_repository,
            sad_preview_repository=preview_repository,
            sad_save_repository=sad_save_repository,
            source_repository=source_repository,
        )
    )


def _wiki_flow_fixture():
    now = datetime(2026, 5, 27, 9, 0, tzinfo=UTC)
    project = ProjectSummary(
        project_id="PR-000001",
        name="Repair Project",
        drive_folder_id="project-folder-001",
        created_at=now,
    )
    repo = DriveRepoRecord(
        grant_id="DG-000001",
        project_id="PROJ-000001",
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        status="connected",
        repo_folder_id="drive-folder-001",
        repo_folder_name="SADify Projects",
        repo_url="https://drive.google.com/drive/folders/drive-folder-001",
        requested_scopes=["https://www.googleapis.com/auth/drive.file"],
        folder_structure=[],
        token_store="secret_manager",
        saves_blocked=False,
        created_at=now,
        updated_at=now,
        active_project_id=project.project_id,
        active_project_name=project.name,
        available_projects=[project],
    )
    preview_repository = SadPreviewRepository()
    save_repository = SadSaveRepository()
    preview_record = preview_repository.save_preview(
        requirement_text="A workshop tracks repairs.",
        analysis_id="AN-000001",
        preview=_preview(),
        created_at=now,
    )
    save_record = save_repository.save_preview(
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        repo=repo,
        project_id=project.project_id,
        preview_record=preview_record,
        sources=[],
        saved_at=now,
    )
    fake_drive = FakeDriveClient()
    wiki_state = WikiStateRepository()
    context = sad_flow.WikiFlowContext(
        repo=repo,
        project=project,
        latest_save=save_record,
        all_saves_for_repo=[save_record],
        sources=[],
        drive_client=fake_drive,
        access_token="access-token",
    )
    return preview_repository, save_repository, wiki_state, context, fake_drive
