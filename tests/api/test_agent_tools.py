import json

from google.adk.tools import FunctionTool

from sadify_api.agent.instruction import SADIFY_AGENT_INSTRUCTION
from sadify_api.agent.tools import (
    AgentDeps,
    build_agent_tool_functions,
    build_agent_tools,
)
from sadify_api.schemas import RequirementAnalysisResponse
from sadify_api.services.analysis_state import RequirementAnalysisRepository
from sadify_api.services.sad_preview import SadPreviewRepository
from tests.api.test_gemini_structured import (
    FakeRequirementAnalysisModel,
    VALID_PAYLOAD,
)
from tests.api.test_sad_preview import (
    FakeSadPreviewModel,
    VALID_PREVIEW,
    _analysis_with_blocking_basics,
)


def test_agent_instruction_mirrors_behavior_contract_guardrails():
    instruction = SADIFY_AGENT_INSTRUCTION.lower()

    assert "clarify first" in instruction
    assert "judge readiness" in instruction
    assert "assumptions" in instruction
    assert "open questions" in instruction
    assert "without explicit approval" in instruction
    assert "traceable" in instruction
    assert "low-confidence" in instruction


def test_build_agent_tools_exposes_adk_function_tools():
    deps, *_ = _agent_deps()

    tools = build_agent_tools(deps)

    assert [tool.name for tool in tools] == [
        "get_readiness",
        "ask_clarification",
        "generate_sad",
        "review_sad",
    ]
    assert all(isinstance(tool, FunctionTool) for tool in tools)
    assert all(tool.description for tool in tools)


def test_get_readiness_returns_documented_shape_from_saved_analysis():
    deps, analysis_repository, *_ = _agent_deps()
    record = _save_analysis(analysis_repository)
    tool_functions = build_agent_tool_functions(deps)

    result = tool_functions.get_readiness(record.analysis_id)

    assert result == {
        "analysis_id": "AN-000001",
        "score": 35,
        "confidence": "Medium",
        "label": "Getting started",
        "gaps": [
            {"id": "problem", "label": "Problem", "status": "partial"},
            {"id": "users_roles", "label": "Users/Roles", "status": "missing"},
        ],
    }


def test_ask_clarification_uses_existing_analysis_engine_shape():
    deps, analysis_repository, _preview_repository, analysis_model, _preview_model = (
        _agent_deps(analysis_outputs=[_analysis_payload()])
    )
    _save_analysis(analysis_repository, analysis_session_id="session-001")
    tool_functions = build_agent_tool_functions(deps)

    result = tool_functions.ask_clarification("session-001")

    assert result == {
        "analysis_id": "AN-000002",
        "question": "What business goal should this request help achieve?",
        "why": "This clarifies the business goal.",
        "choices": [
            {"id": "reduce_delay", "label": "Reduce delays"},
            {"id": "reduce_errors", "label": "Reduce errors"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "goal_scope",
        "target_slot_id": "business_goal",
    }
    assert [repair for _text, repair in analysis_model.requests] == [False]


def test_generate_sad_uses_preview_flow_shape():
    deps, analysis_repository, preview_repository, _analysis_model, preview_model = (
        _agent_deps(preview_outputs=[_preview_payload()])
    )
    analysis = RequirementAnalysisResponse.model_validate(
        _analysis_with_blocking_basics()
    )
    record = analysis_repository.save_analysis(
        requirement_text="Need to validate an operational workflow.",
        analysis_session_id="session-001",
        analysis=analysis,
    )
    tool_functions = build_agent_tool_functions(deps)

    result = tool_functions.generate_sad(record.analysis_id)

    assert result["preview_id"] == "SP-000001"
    assert result["sections"] == [
        {
            "title": section["title"],
            "body": section["body"],
            "source_references": section["source_references"],
        }
        for section in VALID_PREVIEW["sections"]
    ]
    assert result["assumptions"] == VALID_PREVIEW["assumptions"]
    assert result["open_questions"] == VALID_PREVIEW["open_questions"]
    assert preview_repository.get_preview("SP-000001") is not None
    assert [repair for _text, repair in preview_model.requests] == [False]


def test_review_sad_returns_structured_advisory_verdict():
    deps, analysis_repository, _preview_repository, _analysis_model, _preview_model = (
        _agent_deps(
            preview_outputs=[_preview_payload()],
            review_outputs=[
                {
                    "verdict": "regenerate",
                    "issues": [
                        {
                            "severity": "high",
                            "category": "workflow",
                            "message": "Workflow is too vague for a useful SAD.",
                        }
                    ],
                }
            ],
        )
    )
    analysis = RequirementAnalysisResponse.model_validate(
        _analysis_with_blocking_basics()
    )
    record = analysis_repository.save_analysis(
        requirement_text="Need to validate an operational workflow.",
        analysis_session_id="session-001",
        analysis=analysis,
    )
    tool_functions = build_agent_tool_functions(deps)
    preview = tool_functions.generate_sad(record.analysis_id)

    result = tool_functions.review_sad(preview["preview_id"])

    assert result == {
        "preview_id": "SP-000001",
        "verdict": "regenerate",
        "issues": [
            {
                "severity": "high",
                "category": "workflow",
                "message": "Workflow is too vague for a useful SAD.",
            }
        ],
    }


def _agent_deps(
    *,
    analysis_outputs: list[dict[str, object]] | None = None,
    preview_outputs: list[dict[str, object]] | None = None,
    review_outputs: list[dict[str, object]] | None = None,
):
    analysis_repository = RequirementAnalysisRepository()
    preview_repository = SadPreviewRepository()
    analysis_model = FakeRequirementAnalysisModel(
        analysis_outputs or [_analysis_payload()]
    )
    preview_model = FakeSadPreviewModel(preview_outputs or [_preview_payload()])
    review_model = FakeSadReviewModel(review_outputs or [_review_payload()])
    return (
        AgentDeps(
            analysis_repository=analysis_repository,
            sad_preview_repository=preview_repository,
            analysis_model=analysis_model,
            sad_preview_model=preview_model,
            sad_review_model=review_model,
        ),
        analysis_repository,
        preview_repository,
        analysis_model,
        preview_model,
    )


def _save_analysis(
    repository: RequirementAnalysisRepository,
    *,
    analysis_session_id: str = "session-001",
):
    return repository.save_analysis(
        requirement_text="Need a simple way to validate operational ideas.",
        analysis_session_id=analysis_session_id,
        analysis=RequirementAnalysisResponse.model_validate(_analysis_payload()),
    )


def _analysis_payload() -> dict[str, object]:
    return json.loads(json.dumps(VALID_PAYLOAD))


def _preview_payload() -> dict[str, object]:
    return json.loads(json.dumps(VALID_PREVIEW))


def _review_payload() -> dict[str, object]:
    return {"verdict": "proceed", "issues": []}


class FakeSadReviewModel:
    def __init__(self, outputs: list[dict[str, object]]) -> None:
        self.outputs = list(outputs)
        self.requests: list[tuple[str, str | None]] = []

    def review_sad(self, context: str, *, model: str | None = None) -> str:
        self.requests.append((context, model))
        return json.dumps(self.outputs.pop(0))
