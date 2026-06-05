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

from sadify_api.agent.approval import (
    ApprovalStore,
    ApprovalTokenInvalidError,
    WriteApproval,
    WriteApprovalRequiredError,
)
from sadify_api.agent.finalize import (
    build_finalize_agent,
    run_approved_actions,
    run_finalize,
    stream_finalize_events,
)
from sadify_api.agent.tools import AgentDeps, build_agent_tool_functions
from sadify_api.config import ApiConfig
from sadify_api.main import create_app
from sadify_api.schemas import RequirementAnalysisResponse
from sadify_api.services.analysis_state import RequirementAnalysisRepository
from sadify_api.services.sad_flow import SadSaveFlowError, WikiFlowError
from sadify_api.services.sad_preview import SadPreviewRepository
from tests.api.test_sad_save import AcceptingTokenVerifier
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
        "save_to_drive",
        "update_wiki",
    ]
    assert "clarify first" in agent.instruction.lower()


def test_run_finalize_ready_generates_sad_and_awaits_approval():
    approval_store = ApprovalStore()
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
        approval_store=approval_store,
    )

    assert result["status"] == "awaiting_approval"
    assert [event["tool"] for event in result["events"] if event["type"] == "tool"] == [
        "get_readiness",
        "generate_sad",
    ]
    assert result["result"]["preview_id"] == "SP-000001"
    assert [action["id"] for action in result["result"]["proposed_actions"]] == [
        "save_to_drive",
        "update_wiki",
    ]
    assert approval_store.get("session-001", result["result"]["approval_id"]) is not None
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

    assert result["status"] == "awaiting_approval"
    assert [event["tool"] for event in result["events"] if event["type"] == "tool"] == [
        "get_readiness",
        "generate_sad",
        "review_sad",
        "generate_sad",
        "review_sad",
    ]
    assert result["result"]["preview_id"] == "SP-000002"
    assert [action["id"] for action in result["result"]["proposed_actions"]] == [
        "save_to_drive",
        "update_wiki",
    ]
    assert [repair for _context, repair in preview_model.requests] == [False, False]
    assert "Workflow section is too vague." in preview_model.requests[1][0]


def test_agent_generate_sad_consumes_regenerate_review_once_with_feedback():
    deps, analysis_repository, _preview_repository, _analysis_model, preview_model = (
        _finalize_deps(
            preview_outputs=[
                _preview_payload(),
                _preview_payload(),
                _preview_payload(),
            ],
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
                }
            ],
        )
    )
    record = _save_ready_analysis(analysis_repository)
    tool_functions = build_agent_tool_functions(deps)

    first = tool_functions.generate_sad(record.analysis_id)
    review = tool_functions.review_sad(first["preview_id"])
    second = tool_functions.generate_sad(record.analysis_id)
    third = tool_functions.generate_sad(record.analysis_id)

    assert review["verdict"] == "regenerate"
    assert first["preview_id"] == "SP-000001"
    assert second["preview_id"] == "SP-000002"
    assert third["preview_id"] == "SP-000002"
    assert len(preview_model.requests) == 2
    second_context = preview_model.requests[1][0]
    assert "Prior SAD draft summary:" in second_context
    assert "Review issues to address:" in second_context
    assert "Workflow section is too vague." in second_context
    assert "do NOT invent it" in second_context


def test_run_finalize_tighten_existing_draft_does_not_redraw_and_awaits_approval():
    deps, analysis_repository, _preview_repository, _analysis_model, preview_model = (
        _finalize_deps(
            preview_outputs=[_preview_payload(), _preview_payload()],
            review_outputs=[
                {
                    "verdict": "tighten",
                    "issues": [
                        {
                            "severity": "medium",
                            "category": "reports",
                            "message": "Report wording can be tighter.",
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
            _function_call("generate_sad", {"analysis_id": record.analysis_id}),
            types.Content(
                role="model",
                parts=[types.Part.from_text(text="Keeping the tightened draft.")],
            ),
        ]
    )

    result = run_finalize(
        deps,
        analysis_session_id="session-001",
        model=model,
    )

    assert result["status"] == "awaiting_approval"
    assert result["result"]["preview_id"] == "SP-000001"
    assert len(preview_model.requests) == 1
    assert (
        "Review remaining issue: Report wording can be tighter."
        in result["result"]["open_questions"]
    )


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

    assert result["status"] == "awaiting_approval"
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
    assert [action["id"] for action in result["result"]["proposed_actions"]] == [
        "save_to_drive",
        "update_wiki",
    ]
    assert len(preview_model.requests) == 3


def test_run_finalize_review_ask_with_draft_folds_gaps_and_awaits_approval():
    # Option A: when a draft exists, a review verdict of "ask" is treated like
    # "tighten" — its gaps become open questions and the flow proceeds to
    # approval instead of re-interrogating the user.
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
                parts=[types.Part.from_text(text="Proceeding with the best draft.")],
            ),
        ]
    )

    result = run_finalize(
        deps,
        analysis_session_id="session-001",
        model=model,
    )

    assert result["status"] == "awaiting_approval"
    assert result["result"]["preview_id"] == "SP-000001"
    assert result["result"]["approval_id"].startswith("AP-")
    assert (
        "Review remaining issue: The scope needs a human answer before finalizing."
        in result["result"]["open_questions"]
    )


def test_run_finalize_draft_with_stray_clarification_still_awaits_approval():
    # The agent freelanced an ask_clarification after producing a reviewed
    # draft; the draft must win (no dead-end re-ask).
    deps, analysis_repository, _preview_repository, _analysis_model, _preview_model = (
        _finalize_deps(
            preview_outputs=[_preview_payload()],
            analysis_outputs=[_analysis_payload()],
            review_outputs=[
                {
                    "verdict": "tighten",
                    "issues": [
                        {
                            "severity": "low",
                            "category": "users_roles",
                            "message": "Confirm the primary users.",
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
            _function_call(
                "ask_clarification", {"analysis_session_id": "session-001"}
            ),
            types.Content(
                role="model",
                parts=[types.Part.from_text(text="Asking just in case.")],
            ),
        ]
    )

    result = run_finalize(
        deps,
        analysis_session_id="session-001",
        model=model,
    )

    assert result["status"] == "awaiting_approval"
    assert result["result"]["preview_id"] == "SP-000001"
    assert [action["id"] for action in result["result"]["proposed_actions"]] == [
        "save_to_drive",
        "update_wiki",
    ]


def test_run_finalize_unapproved_write_returns_approval_request_without_writes():
    calls = []

    def fake_save_runner(**kwargs):
        calls.append(kwargs)
        return FakeSaveRecord(
            save_id="SV-SHOULD-NOT-WRITE",
            preview_id=kwargs["request"].preview_id,
        )

    approval_store = ApprovalStore()
    deps, analysis_repository, _preview_repository, _analysis_model, _preview_model = (
        _finalize_deps(sad_save_runner=fake_save_runner)
    )
    record = _save_ready_analysis(analysis_repository)
    model = ScriptedLlm(
        responses=[
            _function_call("get_readiness", {"analysis_id": record.analysis_id}),
            _function_call("generate_sad", {"analysis_id": record.analysis_id}),
            _function_call("review_sad", {"preview_id": "SP-000001"}),
            _function_call("save_to_drive", {"preview_id": "SP-000001"}),
            types.Content(
                role="model",
                parts=[types.Part.from_text(text="Approval required.")],
            ),
        ]
    )

    result = run_finalize(
        deps,
        analysis_session_id="session-001",
        model=model,
        approval_store=approval_store,
    )

    assert result["status"] == "awaiting_approval"
    assert result["result"]["preview_id"] == "SP-000001"
    assert result["result"]["approval_id"].startswith("AP-")
    assert [action["id"] for action in result["result"]["proposed_actions"]] == [
        "save_to_drive",
        "update_wiki",
    ]
    assert calls == []
    assert approval_store.get("session-001", result["result"]["approval_id"]) is not None


def test_run_approved_actions_executes_save_and_wiki_without_llm_and_consumes_token():
    save_calls = []
    wiki_calls = []

    def fake_save_runner(**kwargs):
        save_calls.append(kwargs)
        return FakeSaveRecord(
            save_id="SV-APPROVED",
            preview_id=kwargs["request"].preview_id,
        )

    def fake_wiki_context_builder(_deps):
        return object()

    def fake_wiki_update_runner(**kwargs):
        wiki_calls.append(kwargs)
        return FakeWikiUpdateResponse(file_count=2)

    approval_store = ApprovalStore()
    approval_id = approval_store.create(
        "session-001",
        [
            {
                "id": "save_to_drive",
                "label": "Save SAD to Google Drive",
                "preview_id": "SP-000001",
            },
            {
                "id": "update_wiki",
                "label": "Update project wiki",
                "preview_id": "SP-000001",
            },
        ],
    )
    deps, analysis_repository, _preview_repository, _analysis_model, _preview_model = (
        _finalize_deps(
            sad_save_runner=fake_save_runner,
            wiki_context_builder=fake_wiki_context_builder,
            wiki_update_runner=fake_wiki_update_runner,
        )
    )
    _save_ready_analysis(analysis_repository)

    result = run_approved_actions(
        deps,
        analysis_session_id="session-001",
        approval_store=approval_store,
        approval_id=approval_id,
    )

    assert result["status"] == "completed"
    assert [action["tool"] for action in result["result"]["actions"]] == [
        "save_to_drive",
        "update_wiki",
    ]
    assert save_calls[0]["request"].preview_id == "SP-000001"
    assert wiki_calls[0]["request"].force_overwrite is False
    assert approval_store.get("session-001", approval_id) is None


def test_run_approved_actions_hard_write_error_leaves_token_for_retry():
    save_calls = []

    def fake_save_runner(**kwargs):
        save_calls.append(kwargs)
        raise SadSaveFlowError(
            409,
            "SAD_SAVE_REPO_REQUIRED",
            "Connect a Google Drive project repo before saving.",
        )

    approval_store = ApprovalStore()
    approval_id = approval_store.create(
        "session-001",
        [
            {
                "id": "save_to_drive",
                "label": "Save SAD to Google Drive",
                "preview_id": "SP-000001",
            }
        ],
    )
    deps, analysis_repository, _preview_repository, _analysis_model, _preview_model = (
        _finalize_deps(sad_save_runner=fake_save_runner)
    )
    _save_ready_analysis(analysis_repository)

    result = run_approved_actions(
        deps,
        analysis_session_id="session-001",
        approval_store=approval_store,
        approval_id=approval_id,
    )

    assert result["status"] == "awaiting_approval"
    assert result["result"]["error"]["code"] == "SAD_SAVE_REPO_REQUIRED"
    assert len(save_calls) == 1
    assert approval_store.get("session-001", approval_id) is not None


def test_run_approved_actions_missing_token_refuses_without_write():
    calls = []

    def fake_save_runner(**kwargs):
        calls.append(kwargs)
        return FakeSaveRecord(
            save_id="SV-SHOULD-NOT-WRITE",
            preview_id=kwargs["request"].preview_id,
        )

    deps, *_ = _finalize_deps(sad_save_runner=fake_save_runner)

    try:
        run_approved_actions(
            deps,
            analysis_session_id="session-001",
            approval_store=ApprovalStore(),
            approval_id="AP-missing",
        )
    except ApprovalTokenInvalidError:
        pass
    else:
        raise AssertionError("missing approval token must be refused")

    assert calls == []


def test_write_tool_mismatched_preview_refuses_without_write():
    calls = []

    def fake_save_runner(**kwargs):
        calls.append(kwargs)
        return FakeSaveRecord(
            save_id="SV-SHOULD-NOT-WRITE",
            preview_id=kwargs["request"].preview_id,
        )

    deps, *_ = _finalize_deps(
        write_approval=WriteApproval(
            approval_id="AP-test",
            actions=[
                {
                    "id": "save_to_drive",
                    "label": "Save SAD to Google Drive",
                    "preview_id": "SP-000001",
                }
            ],
        ),
        sad_save_runner=fake_save_runner,
    )
    tool_functions = build_agent_tool_functions(deps)

    try:
        tool_functions.save_to_drive("SP-000002")
    except WriteApprovalRequiredError:
        pass
    else:
        raise AssertionError("mismatched preview approval must be refused")

    assert calls == []


def test_run_approved_actions_wiki_conflict_consumes_original_and_reapproves():
    def fake_wiki_context_builder(_deps):
        return object()

    def fake_wiki_update_runner(**kwargs):
        raise WikiFlowError(
            409,
            "WIKI_CONFLICT",
            "The wiki was changed in Drive since SADify last wrote it. Confirm overwrite.",
            changed_files=["workflows.md"],
        )

    approval_store = ApprovalStore()
    approval_id = approval_store.create(
        "session-001",
        [
            {
                "id": "update_wiki",
                "label": "Update project wiki",
                "preview_id": "SP-000001",
            }
        ],
    )
    deps, analysis_repository, _preview_repository, _analysis_model, _preview_model = (
        _finalize_deps(
            wiki_context_builder=fake_wiki_context_builder,
            wiki_update_runner=fake_wiki_update_runner,
        )
    )
    _save_ready_analysis(analysis_repository)

    result = run_approved_actions(
        deps,
        analysis_session_id="session-001",
        approval_store=approval_store,
        approval_id=approval_id,
    )

    assert result["status"] == "awaiting_approval"
    assert result["result"]["changed_files"] == ["workflows.md"]
    assert result["result"]["proposed_actions"] == [
        {
            "id": "overwrite_wiki",
            "label": "Overwrite changed wiki files",
            "changed_files": ["workflows.md"],
            "force_overwrite": True,
        }
    ]
    assert approval_store.get("session-001", approval_id) is None
    assert approval_store.get("session-001", result["result"]["approval_id"]) is not None


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


def test_run_finalize_blocked_basics_still_asks_clarification():
    deps, analysis_repository, _preview_repository, analysis_model, preview_model = (
        _finalize_deps(analysis_outputs=[_analysis_payload()])
    )
    record = _save_analysis(analysis_repository, analysis_session_id="session-003")
    model = ScriptedLlm(
        responses=[
            _function_call("get_readiness", {"analysis_id": record.analysis_id}),
            _function_call("generate_sad", {"analysis_id": record.analysis_id}),
            _function_call(
                "ask_clarification",
                {"analysis_session_id": "session-003"},
            ),
            types.Content(
                role="model",
                parts=[types.Part.from_text(text="Clarification requested.")],
            ),
        ]
    )

    result = run_finalize(
        deps,
        analysis_session_id="session-003",
        model=model,
    )

    assert result["status"] == "asked_clarification"
    assert result["result"]["question"] == (
        "What business goal should this request help achieve?"
    )
    assert preview_model.requests == []
    assert [repair for _text, repair in analysis_model.requests] == [False]


def test_agent_finalize_route_resolves_model_and_returns_response(monkeypatch):
    captured = {}

    def fake_run_finalize(
        deps,
        *,
        analysis_session_id: str,
        model: str,
        approval_store,
    ):
        captured["deps"] = deps
        captured["analysis_session_id"] = analysis_session_id
        captured["model"] = model
        captured["approval_store"] = approval_store
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


def test_agent_approve_route_requires_auth_and_passes_approval(monkeypatch):
    captured = {}

    def fake_run_approved_actions(
        deps,
        *,
        analysis_session_id: str,
        approval_store,
        approval_id: str | None = None,
    ):
        captured["deps"] = deps
        captured["analysis_session_id"] = analysis_session_id
        captured["approval_store"] = approval_store
        captured["approval_id"] = approval_id
        return {
            "status": "completed",
            "events": [
                {
                    "type": "tool",
                    "tool": "save_to_drive",
                    "summary": "Saved SAD preview.",
                }
            ],
            "result": {"actions": [{"tool": "save_to_drive"}]},
        }

    from sadify_api.routes import agent as agent_route

    monkeypatch.setattr(agent_route, "run_approved_actions", fake_run_approved_actions)
    client = TestClient(
        create_app(
            config=ApiConfig(environment="test", sadify_model="gemini-2.5-flash"),
            token_verifier=AcceptingTokenVerifier(),
            analysis_repository=RequirementAnalysisRepository(),
            sad_preview_repository=SadPreviewRepository(),
        )
    )

    response = client.post(
        "/agent/approve",
        headers={"Authorization": "Bearer firebase-test-token"},
        json={
            "analysis_session_id": "session-route",
            "approval_id": "AP-route",
            "model": "not-in-catalog",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert captured["analysis_session_id"] == "session-route"
    assert captured["approval_id"] == "AP-route"
    assert captured["deps"].user.uid == "firebase-uid-001"


def test_stream_finalize_events_yields_ordered_events_then_terminal():
    deps, analysis_repository, _preview_repository, _analysis_model, _preview_model = (
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
    store = ApprovalStore()

    items = list(
        stream_finalize_events(
            deps,
            analysis_session_id="session-001",
            model=model,
            approval_store=store,
        )
    )

    *events, terminal = items
    tool_events = [item for item in events if item["type"] == "tool"]
    assert [item["tool"] for item in tool_events] == ["get_readiness", "generate_sad"]
    # Every tool event carries derived reasoning, not just a tool name.
    assert all(item["reasoning"] for item in tool_events)
    assert terminal["type"] == "status"
    assert terminal["status"] == "awaiting_approval"
    assert terminal["result"]["preview_id"] == "SP-000001"
    assert terminal["result"]["approval_id"].startswith("AP-")
    assert [action["id"] for action in terminal["result"]["proposed_actions"]] == [
        "save_to_drive",
        "update_wiki",
    ]
    assert store.get("session-001", terminal["result"]["approval_id"]) is not None


def test_finalize_stream_route_returns_ndjson_event_stream(monkeypatch):
    def fake_stream_finalize_events(
        deps,
        *,
        analysis_session_id: str,
        model: str,
        approval_store,
    ):
        yield {
            "type": "tool",
            "tool": "get_readiness",
            "summary": "Ready for preview: 76% readiness, Medium confidence.",
            "reasoning": "Requirement readiness 76% with Medium confidence.",
        }
        yield {
            "type": "status",
            "status": "awaiting_approval",
            "result": {"preview_id": "SP-ROUTE", "approval_id": "AP-ROUTE"},
        }

    from sadify_api.routes import agent as agent_route

    monkeypatch.setattr(
        agent_route, "stream_finalize_events", fake_stream_finalize_events
    )
    client = TestClient(
        create_app(
            config=ApiConfig(environment="test", sadify_model="gemini-2.5-flash"),
            analysis_repository=RequirementAnalysisRepository(),
            sad_preview_repository=SadPreviewRepository(),
        )
    )

    response = client.post(
        "/agent/finalize/stream",
        json={"analysis_session_id": "session-route", "model": "not-in-catalog"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    lines = [line for line in response.text.split("\n") if line.strip()]
    parsed = [json.loads(line) for line in lines]
    assert parsed[0]["tool"] == "get_readiness"
    assert parsed[0]["reasoning"]
    assert parsed[-1]["type"] == "status"
    assert parsed[-1]["status"] == "awaiting_approval"
    assert parsed[-1]["result"]["approval_id"] == "AP-ROUTE"


def test_run_finalize_drafts_when_agent_only_checks_readiness():
    # Weak models (e.g. Flash-Lite) sometimes call get_readiness then stop
    # without drafting. The deterministic safety-net must still produce a draft
    # so finalize never returns a phantom approval with no approval_id.
    deps, analysis_repository, _preview_repository, _analysis_model, preview_model = (
        _finalize_deps(preview_outputs=[_preview_payload()])
    )
    record = _save_ready_analysis(analysis_repository)
    model = ScriptedLlm(
        responses=[
            _function_call("get_readiness", {"analysis_id": record.analysis_id}),
            types.Content(
                role="model",
                parts=[types.Part.from_text(text="Readiness looks strong.")],
            ),
        ]
    )

    result = run_finalize(
        deps,
        analysis_session_id="session-001",
        model=model,
    )

    assert result["status"] == "awaiting_approval"
    assert result["result"]["approval_id"].startswith("AP-")
    assert result["result"]["preview_id"] == "SP-000001"
    tool_events = [e["tool"] for e in result["events"] if e["type"] == "tool"]
    assert "get_readiness" in tool_events
    assert "generate_sad" in tool_events  # produced by the safety-net
    assert len(preview_model.requests) == 1


def test_stream_finalize_drafts_when_agent_only_checks_readiness():
    deps, analysis_repository, _preview_repository, _analysis_model, _preview_model = (
        _finalize_deps(preview_outputs=[_preview_payload()])
    )
    record = _save_ready_analysis(analysis_repository)
    model = ScriptedLlm(
        responses=[
            _function_call("get_readiness", {"analysis_id": record.analysis_id}),
            types.Content(
                role="model",
                parts=[types.Part.from_text(text="Readiness looks strong.")],
            ),
        ]
    )
    store = ApprovalStore()

    items = list(
        stream_finalize_events(
            deps,
            analysis_session_id="session-001",
            model=model,
            approval_store=store,
        )
    )

    *events, terminal = items
    tool_events = [e["tool"] for e in events if e["type"] == "tool"]
    assert "generate_sad" in tool_events  # safety-net draft is streamed
    assert terminal["type"] == "status"
    assert terminal["status"] == "awaiting_approval"
    assert terminal["result"]["approval_id"].startswith("AP-")
    assert terminal["result"]["preview_id"] == "SP-000001"


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
    write_approval: WriteApproval | None = None,
    sad_save_runner=None,
    wiki_context_builder=None,
    wiki_update_runner=None,
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
            user=FakeUser(),
            write_approval=write_approval,
            sad_save_runner=sad_save_runner,
            wiki_context_builder=wiki_context_builder,
            wiki_update_runner=wiki_update_runner,
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


class FakeUser:
    uid = "firebase-uid-001"
    email = "owner@example.com"


class FakeArtifact:
    def __init__(self, save_id: str) -> None:
        self.url = f"https://docs.example/{save_id}"
        self.path = f"SAD/{save_id}"


class FakeSaveRecord:
    def __init__(self, *, save_id: str, preview_id: str) -> None:
        self.save_id = save_id
        self.preview_id = preview_id
        self.sad_doc = FakeArtifact(save_id)


class FakeWikiUpdateResponse:
    def __init__(self, *, file_count: int) -> None:
        self.files = [object() for _index in range(file_count)]
