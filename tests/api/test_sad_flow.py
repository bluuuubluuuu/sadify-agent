import pytest

from sadify_api.config import ApiConfig
from sadify_api.schemas import SadPreviewRequest, SadSaveRequest
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
