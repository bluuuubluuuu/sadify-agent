from collections.abc import AsyncGenerator
import json

from google.adk.agents import Agent
from google.adk.models import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.genai import types
from fastapi.testclient import TestClient

from sadify_api.agent.finalize import build_finalize_agent, run_finalize
from sadify_api.agent.tools import AgentDeps
from sadify_api.config import ApiConfig
from sadify_api.main import create_app
from sadify_api.schemas import RequirementAnalysisResponse
from sadify_api.services.analysis_state import RequirementAnalysisRepository
from sadify_api.services.sad_preview import SadPreviewRepository
from tests.api.test_gemini_structured import FakeRequirementAnalysisModel, VALID_PAYLOAD
from tests.api.test_sad_preview import (
    FakeSadPreviewModel,
    VALID_PREVIEW,
    _analysis_with_blocking_basics,
)


def test_adk_runner_executes_function_tool_with_fake_model():
    calls: list[str] = []

    def echo_tool(value: str) -> dict[str, str]:
        """Echo a value for the ADK Runner proof."""
        calls.append(value)
        return {"echo": value}

    model = ScriptedLlm(
        responses=[
            types.Content(
                role="model",
                parts=[
                    types.Part.from_function_call(
                        name="echo_tool",
                        args={"value": "hello"},
                    )
                ],
            ),
            types.Content(
                role="model",
                parts=[types.Part.from_text(text="completed")],
            ),
        ]
    )
    agent = Agent(
        name="proof_agent",
        model=model,
        instruction="Use echo_tool once, then summarize.",
        tools=[FunctionTool(echo_tool)],
    )
    session_service = InMemorySessionService()
    session_service.create_session_sync(
        app_name="sadify-test",
        user_id="user-001",
        session_id="session-001",
    )
    runner = Runner(
        app_name="sadify-test",
        agent=agent,
        session_service=session_service,
    )

    events = list(
        runner.run(
            user_id="user-001",
            session_id="session-001",
            new_message=types.Content(
                role="user",
                parts=[types.Part.from_text(text="run proof")],
            ),
        )
    )

    assert calls == ["hello"]
    assert any(event.get_function_calls() for event in events)
    assert any(event.get_function_responses() for event in events)
    assert events[-1].is_final_response()
    assert events[-1].content.parts[0].text == "completed"


def test_build_finalize_agent_uses_adk_agent_with_task_tools():
    deps, *_ = _finalize_deps()
    model = ScriptedLlm(
        responses=[
            types.Content(role="model", parts=[types.Part.from_text(text="done")])
        ]
    )

    agent = build_finalize_agent(deps, model=model)

    assert isinstance(agent, Agent)
    assert agent.name == "sadify_finalize"
    assert agent.model is model
    assert [tool.name for tool in agent.tools] == [
        "get_readiness",
        "ask_clarification",
        "generate_sad",
        "review_sad",
    ]
    assert "clarify first" in agent.instruction.lower()


def test_run_finalize_ready_generates_sad_and_completes():
    deps, analysis_repository, _preview_repository, _analysis_model, preview_model = (
        _finalize_deps(preview_outputs=[_preview_payload()])
    )
    record = _save_ready_analysis(analysis_repository)
    model = ScriptedLlm(
        responses=[
            _function_call("get_readiness", {"analysis_id": record.analysis_id}),
            _function_call("generate_sad", {"analysis_id": record.analysis_id}),
            types.Content(
                role="model",
                parts=[types.Part.from_text(text="Draft generated.")],
            ),
        ]
    )

    result = run_finalize(
        deps,
        analysis_session_id="session-001",
        model=model,
    )

    assert result["status"] == "completed"
    assert [event["tool"] for event in result["events"] if event["type"] == "tool"] == [
        "get_readiness",
        "generate_sad",
    ]
    assert result["result"]["preview_id"] == "SP-000001"
    assert result["result"]["open_questions"] == VALID_PREVIEW["open_questions"]
    assert [repair for _context, repair in preview_model.requests] == [False]


def test_run_finalize_reviews_weak_draft_regenerates_once_then_completes():
    deps, analysis_repository, _preview_repository, _analysis_model, preview_model = (
        _finalize_deps(
            preview_outputs=[_preview_payload(), _preview_payload()],
            review_outputs=[
                {
                    "verdict": "regenerate",
                    "issues": [
                        {
                            "severity": "high",
                            "category": "workflow",
                            "message": "Workflow section is too vague.",
                        }
                    ],
                },
                {"verdict": "proceed", "issues": []},
            ],
        )
    )
    record = _save_ready_analysis(analysis_repository)
    model = ScriptedLlm(
        responses=[
            _function_call("get_readiness", {"analysis_id": record.analysis_id}),
            _function_call("generate_sad", {"analysis_id": record.analysis_id}),
            _function_call("review_sad", {"preview_id": "SP-000001"}),
            _function_call("generate_sad", {"analysis_id": record.analysis_id}),
            _function_call("review_sad", {"preview_id": "SP-000002"}),
            types.Content(
                role="model",
                parts=[types.Part.from_text(text="Reviewed draft generated.")],
            ),
        ]
    )

    result = run_finalize(
        deps,
        analysis_session_id="session-001",
        model=model,
    )

    assert result["status"] == "completed"
    assert [event["tool"] for event in result["events"] if event["type"] == "tool"] == [
        "get_readiness",
        "generate_sad",
        "review_sad",
        "generate_sad",
        "review_sad",
    ]
    assert result["result"]["preview_id"] == "SP-000002"
    assert result["result"]["review"]["verdict"] == "proceed"
    assert [repair for _context, repair in preview_model.requests] == [False, False]


def test_run_finalize_honors_regenerate_cap_and_surfaces_remaining_issues():
    deps, analysis_repository, _preview_repository, _analysis_model, preview_model = (
        _finalize_deps(
            preview_outputs=[_preview_payload(), _preview_payload(), _preview_payload()],
            review_outputs=[
                {
                    "verdict": "regenerate",
                    "issues": [
                        {
                            "severity": "medium",
                            "category": "reports",
                            "message": "Reporting details are weak.",
                        }
                    ],
                },
                {
                    "verdict": "regenerate",
                    "issues": [
                        {
                            "severity": "medium",
                            "category": "permissions",
                            "message": "Permissions are still vague.",
                        }
                    ],
                },
                {
                    "verdict": "regenerate",
                    "issues": [
                        {
                            "severity": "high",
                            "category": "workflow",
                            "message": "Workflow still needs tightening.",
                        }
                    ],
                },
            ],
        )
    )
    record = _save_ready_analysis(analysis_repository)
    model = ScriptedLlm(
        responses=[
            _function_call("get_readiness", {"analysis_id": record.analysis_id}),
            _function_call("generate_sad", {"analysis_id": record.analysis_id}),
            _function_call("review_sad", {"preview_id": "SP-000001"}),
            _function_call("generate_sad", {"analysis_id": record.analysis_id}),
            _function_call("review_sad", {"preview_id": "SP-000002"}),
            _function_call("generate_sad", {"analysis_id": record.analysis_id}),
            _function_call("review_sad", {"preview_id": "SP-000003"}),
            _function_call("generate_sad", {"analysis_id": record.analysis_id}),
            types.Content(
                role="model",
                parts=[types.Part.from_text(text="Proceed with best capped draft.")],
            ),
        ]
    )

    result = run_finalize(
        deps,
        analysis_session_id="session-001",
        model=model,
    )

    assert result["status"] == "completed"
    assert [event["tool"] for event in result["events"] if event["type"] == "tool"] == [
        "get_readiness",
        "generate_sad",
        "review_sad",
        "generate_sad",
        "review_sad",
        "generate_sad",
        "review_sad",
        "generate_sad",
    ]
    assert result["result"]["preview_id"] == "SP-000003"
    assert result["result"]["review"]["regenerate_cap_reached"] is True
    assert "Review remaining issue: Workflow still needs tightening." in result[
        "result"
    ]["open_questions"]
    assert len(preview_model.requests) == 3


def test_run_finalize_review_ask_verdict_returns_asked_clarification():
    deps, analysis_repository, _preview_repository, _analysis_model, _preview_model = (
        _finalize_deps(
            preview_outputs=[_preview_payload()],
            review_outputs=[
                {
                    "verdict": "ask",
                    "issues": [
                        {
                            "severity": "high",
                            "category": "scope",
                            "message": "The scope needs a human answer before finalizing.",
                        }
                    ],
                }
            ],
        )
    )
    record = _save_ready_analysis(analysis_repository)
    model = ScriptedLlm(
        responses=[
            _function_call("get_readiness", {"analysis_id": record.analysis_id}),
            _function_call("generate_sad", {"analysis_id": record.analysis_id}),
            _function_call("review_sad", {"preview_id": "SP-000001"}),
            types.Content(
                role="model",
                parts=[types.Part.from_text(text="Need clarification.")],
            ),
        ]
    )

    result = run_finalize(
        deps,
        analysis_session_id="session-001",
        model=model,
    )

    assert result["status"] == "asked_clarification"
    assert result["result"]["verdict"] == "ask"
    assert result["result"]["issues"][0]["message"] == (
        "The scope needs a human answer before finalizing."
    )


def test_run_finalize_not_ready_asks_one_clarification_and_stops():
    deps, analysis_repository, _preview_repository, analysis_model, _preview_model = (
        _finalize_deps(analysis_outputs=[_analysis_payload()])
    )
    record = _save_analysis(analysis_repository, analysis_session_id="session-002")
    model = ScriptedLlm(
        responses=[
            _function_call("get_readiness", {"analysis_id": record.analysis_id}),
            _function_call(
                "ask_clarification",
                {"analysis_session_id": "session-002"},
            ),
            types.Content(
                role="model",
                parts=[types.Part.from_text(text="Clarification requested.")],
            ),
        ]
    )

    result = run_finalize(
        deps,
        analysis_session_id="session-002",
        model=model,
    )

    assert result["status"] == "asked_clarification"
    assert [event["tool"] for event in result["events"] if event["type"] == "tool"] == [
        "get_readiness",
        "ask_clarification",
    ]
    assert result["result"]["question"] == (
        "What business goal should this request help achieve?"
    )
    assert [repair for _text, repair in analysis_model.requests] == [False]


def test_agent_finalize_route_resolves_model_and_returns_response(monkeypatch):
    captured = {}

    def fake_run_finalize(deps, *, analysis_session_id: str, model: str):
        captured["deps"] = deps
        captured["analysis_session_id"] = analysis_session_id
        captured["model"] = model
        return {
            "status": "completed",
            "events": [
                {
                    "type": "tool",
                    "tool": "generate_sad",
                    "summary": "Generated a SAD preview.",
                }
            ],
            "result": {"preview_id": "SP-ROUTE"},
        }

    from sadify_api.routes import agent as agent_route

    monkeypatch.setattr(agent_route, "run_finalize", fake_run_finalize)
    client = TestClient(
        create_app(
            config=ApiConfig(environment="test", sadify_model="gemini-2.5-flash"),
            analysis_repository=RequirementAnalysisRepository(),
            sad_preview_repository=SadPreviewRepository(),
        )
    )

    response = client.post(
        "/agent/finalize",
        json={"analysis_session_id": "session-route", "model": "not-in-catalog"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "completed",
        "events": [
            {
                "type": "tool",
                "tool": "generate_sad",
                "summary": "Generated a SAD preview.",
                "reasoning": None,
            }
        ],
        "result": {"preview_id": "SP-ROUTE"},
    }
    assert captured["analysis_session_id"] == "session-route"
    assert captured["model"] == "gemini-2.5-flash"


class ScriptedLlm(BaseLlm):
    responses: list[types.Content]
    requests_seen: list[LlmRequest]

    def __init__(self, responses: list[types.Content], model: str = "scripted") -> None:
        super().__init__(model=model, responses=responses, requests_seen=[])

    async def generate_content_async(
        self,
        llm_request: LlmRequest,
        stream: bool = False,
    ) -> AsyncGenerator[LlmResponse, None]:
        del stream
        self.requests_seen.append(llm_request)
        yield LlmResponse(content=self.responses.pop(0), partial=False)


def _finalize_deps(
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
    analysis_session_id: str,
):
    return repository.save_analysis(
        requirement_text="Need a simple way to validate operational ideas.",
        analysis_session_id=analysis_session_id,
        analysis=RequirementAnalysisResponse.model_validate(_analysis_payload()),
    )


def _save_ready_analysis(repository: RequirementAnalysisRepository):
    return repository.save_analysis(
        requirement_text="Need to validate an operational workflow.",
        analysis_session_id="session-001",
        analysis=RequirementAnalysisResponse.model_validate(
            _analysis_with_blocking_basics()
        ),
    )


def _function_call(name: str, args: dict[str, object]) -> types.Content:
    return types.Content(
        role="model",
        parts=[types.Part.from_function_call(name=name, args=args)],
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
