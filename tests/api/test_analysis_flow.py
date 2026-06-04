import json

from sadify_api.schemas import RequirementAnalysisRequest
from sadify_api.services.analysis_state import RequirementAnalysisRepository
from sadify_api.services.analysis_flow import run_analysis_turn
from tests.api.test_gemini_structured import FakeRequirementAnalysisModel, VALID_PAYLOAD


def test_run_analysis_turn_gemini_path_saves_record():
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([_payload()])
    request = RequirementAnalysisRequest(
        guest_draft_id="GD-000001",
        requirement_text="Need a simple way to validate operational ideas.",
    )

    record = run_analysis_turn(
        request=request,
        model=model,
        repository=repository,
    )

    assert record.analysis_id == "AN-000001"
    assert record.guest_draft_id == "GD-000001"
    assert record.analysis.next_question.target_category == "goal_scope"
    assert record.analysis.questionnaire is not None
    assert record.analysis.questionnaire.active_category_id == "goal_scope"
    assert repository.get_analysis("AN-000001") == record
    assert [repair for _, repair in model.requests] == [False]


def test_run_analysis_turn_fallback_path_saves_fallback_record():
    broken_payload = _payload()
    broken_payload["readiness"] = {
        "label": "Impossible",
        "score": 150,
        "confidence": "High",
    }
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([broken_payload, broken_payload])
    request = RequirementAnalysisRequest(
        requirement_text="Small clinic needs patient registration and queue tracking.",
    )

    record = run_analysis_turn(
        request=request,
        model=model,
        repository=repository,
    )

    assert record.analysis_id == "AN-000001"
    assert record.analysis.readiness.confidence == "Low"
    assert record.analysis.next_question.target_category == "goal_scope"
    assert record.analysis.questionnaire is not None
    assert record.analysis.questionnaire.active_category_id == "goal_scope"
    assert "fallback" in record.analysis.assumptions[0].lower()
    assert repository.get_analysis("AN-000001") == record
    assert [repair for _, repair in model.requests] == [False, True]


def _payload() -> dict[str, object]:
    return json.loads(json.dumps(VALID_PAYLOAD))
