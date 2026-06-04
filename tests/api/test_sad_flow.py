import pytest

from sadify_api.schemas import SadPreviewRequest
from sadify_api.services.sad_preview import SadPreviewRepository
from sadify_api.services.sad_flow import SadPreviewBlockedError, run_sad_preview
from tests.api.test_gemini_structured import VALID_PAYLOAD as VALID_ANALYSIS
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
