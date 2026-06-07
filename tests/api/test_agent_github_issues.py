import json
from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from google.adk.models import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from sadify_api.agent.approval import ApprovalStore
from sadify_api.config import ApiConfig
from sadify_api.main import create_app
from sadify_api.schemas import SadPreviewResponse
from sadify_api.services.analysis_state import RequirementAnalysisRepository
from sadify_api.services.github_issue_flow import (
    GitHubIssueFlowError,
    _call_tool_payload,
    approve_github_issues,
    build_github_mcp_toolset,
    prepare_github_issues,
    run_github_issue_prepare_agent,
)
from sadify_api.services.sad_preview import SadPreviewRepository
from tests.api.test_gemini_structured import FakeRequirementAnalysisModel
from tests.api.test_sad_preview import FakeSadPreviewModel, VALID_PREVIEW
from tests.api.test_sad_save import AcceptingTokenVerifier


class _FakeMcpResult:
    def __init__(self, *, structuredContent=None, content=None, isError=False):
        self.structuredContent = structuredContent
        self.content = content or []
        self.isError = isError


class _FakeTextContent:
    def __init__(self, text):
        self.text = text


def test_call_tool_payload_unwraps_fastmcp_result_envelope():
    inner = {"status": "created", "repo": "owner/repo", "issues": []}
    result = _FakeMcpResult(structuredContent={"result": inner})

    assert _call_tool_payload(result) == inner


def test_call_tool_payload_surfaces_real_mcp_error_text():
    result = _FakeMcpResult(
        content=[_FakeTextContent("Error executing tool: 404 Not Found")],
        isError=True,
    )

    payload = _call_tool_payload(result)

    assert payload["status"] == "error"
    assert payload["code"] == "GITHUB_MCP_ERROR"
    assert "404 Not Found" in payload["message"]


def test_build_github_mcp_toolset_uses_stdio_server_with_approval_mode():
    toolset = build_github_mcp_toolset(
        repo="acme/app",
        approval_required=True,
        token="ghp_secret",
        python_executable="python-test",
        repo_root="D:/GoogleCloudHack/.worktrees/mvp-monorepo-scaffold",
    )

    assert toolset.__class__.__name__ == "McpToolset"
    params = toolset._connection_params
    assert params.timeout == 5.0
    assert params.server_params.command == "python-test"
    assert params.server_params.args == ["-m", "services.mcp.github_server"]
    assert params.server_params.cwd == "D:/GoogleCloudHack/.worktrees/mvp-monorepo-scaffold"
    assert params.server_params.env["SADIFY_GITHUB_REPO"] == "acme/app"
    assert params.server_params.env["SADIFY_GITHUB_APPROVAL_REQUIRED"] == "true"
    assert "SADIFY_GITHUB_TOKEN" not in params.server_params.env


def test_prepare_github_issues_extracts_tasks_and_stores_agent_mcp_approval():
    preview_repository = SadPreviewRepository()
    preview_record = preview_repository.save_preview(
        requirement_text="Need a grooming appointment system.",
        analysis_id="AN-000001",
        preview=SadPreviewResponse.model_validate(VALID_PREVIEW),
    )
    dev_task_model = FakeDevTaskModel(
        [
            {
                "tasks": [
                    {
                        "priority": "high",
                        "title": "Build appointment intake",
                        "description": "Capture grooming appointment details.",
                        "source_references": ["SRC-000001"],
                    }
                ]
            }
        ]
    )
    store = ApprovalStore()
    agent_calls = []

    def fake_agent_runner(*, model, repo, issues, mcp_toolset_factory):
        agent_calls.append(
            {
                "model": model,
                "repo": repo,
                "issues": issues,
                "toolset": mcp_toolset_factory(approval_required=True),
            }
        )
        return {
            "approval_required": True,
            "tool": "create_github_issues",
            "repo": repo,
            "proposed_actions": [
                {
                    "id": "create_github_issues",
                    "label": "Create GitHub issues",
                    "repo": repo,
                    "issue_count": len(issues),
                    "issues": issues,
                }
            ],
        }

    result = prepare_github_issues(
        preview_repository=preview_repository,
        dev_task_model=dev_task_model,
        config=ApiConfig(
            environment="test",
            github_mcp_enabled=True,
            github_repo="acme/app",
            sadify_model="gemini-2.5-flash",
        ),
        analysis_session_id="session-001",
        preview_id=preview_record.preview_id,
        model="gemini-2.5-flash",
        approval_store=store,
        agent_runner=fake_agent_runner,
        mcp_toolset_factory=lambda **kwargs: {"approval_required": kwargs["approval_required"]},
    )

    assert result["status"] == "awaiting_approval"
    assert result["events"] == [
        {
            "type": "tool",
            "tool": "extract_dev_tasks",
            "summary": "Prepared 1 source-grounded developer task(s).",
        },
        {
            "type": "tool",
            "tool": "create_github_issues",
            "summary": "GitHub issue creation needs approval.",
        },
    ]
    assert result["result"]["repo"] == "acme/app"
    assert result["result"]["approval_id"].startswith("AP-")
    assert result["result"]["proposed_actions"][0]["issues"][0]["title"] == (
        "Build appointment intake"
    )
    assert agent_calls[0]["toolset"] == {"approval_required": True}
    assert dev_task_model.requests[0][1] == "gemini-2.5-flash"
    approval = store.get("session-001", result["result"]["approval_id"])
    assert approval is not None
    assert approval.actions[0]["id"] == "create_github_issues"


def test_prepare_agent_invokes_create_github_issues_through_stdio_mcp_toolset():
    issues = [
        {
            "title": "Build appointment intake",
            "body": "Priority: high\n\nCapture grooming appointment details.\n\nSource references: SRC-000001",
            "labels": ["sadify", "priority-high"],
        }
    ]
    model = ScriptedLlm(
        responses=[
            types.Content(
                role="model",
                parts=[
                    types.Part.from_function_call(
                        name="create_github_issues",
                        args={"repo": "acme/app", "issues": issues},
                    )
                ],
            ),
            types.Content(role="model", parts=[types.Part.from_text(text="done")]),
        ]
    )

    result = run_github_issue_prepare_agent(
        model=model,
        repo="acme/app",
        issues=issues,
        mcp_toolset_factory=lambda **kwargs: build_github_mcp_toolset(
            repo="acme/app",
            approval_required=kwargs["approval_required"],
        ),
    )

    assert result["approval_required"] is True
    assert result["tool"] == "create_github_issues"
    assert result["proposed_actions"][0]["issues"] == issues
    assert model.requests_seen


def test_prepare_github_issues_disabled_refuses_before_extract_or_mcp():
    preview_repository = SadPreviewRepository()
    preview_record = preview_repository.save_preview(
        requirement_text="Need a grooming appointment system.",
        analysis_id="AN-000001",
        preview=SadPreviewResponse.model_validate(VALID_PREVIEW),
    )
    dev_task_model = FakeDevTaskModel([{"tasks": []}])
    calls = []

    with pytest.raises(GitHubIssueFlowError) as exc_info:
        prepare_github_issues(
            preview_repository=preview_repository,
            dev_task_model=dev_task_model,
            config=ApiConfig(environment="test", github_mcp_enabled=False),
            analysis_session_id="session-001",
            preview_id=preview_record.preview_id,
            model="gemini-2.5-flash",
            approval_store=ApprovalStore(),
            agent_runner=lambda **_kwargs: calls.append("agent"),
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "GITHUB_MCP_DISABLED"
    assert dev_task_model.requests == []
    assert calls == []


def test_approve_github_issues_consumes_valid_token_and_executes_same_mcp_tool():
    store = ApprovalStore()
    approval_id = store.create(
        "session-001",
        [
            {
                "id": "create_github_issues",
                "label": "Create GitHub issues",
                "repo": "acme/app",
                "issue_count": 1,
                "issues": [
                    {
                        "title": "Build appointment intake",
                        "body": "Priority: high\n\nCapture grooming appointment details.\n\nSource references: SRC-000001",
                        "labels": ["sadify", "priority-high"],
                    }
                ],
            }
        ],
    )
    mcp_calls = []

    def fake_mcp_executor(*, repo, issues, token, mcp_toolset_factory):
        mcp_calls.append(
            {
                "repo": repo,
                "issues": issues,
                "token": token,
                "toolset": mcp_toolset_factory(approval_required=False, token=token),
            }
        )
        return {
            "status": "created",
            "repo": repo,
            "issues": [
                {
                    "number": 7,
                    "url": "https://github.com/acme/app/issues/7",
                    "title": "Build appointment intake",
                }
            ],
        }

    result = approve_github_issues(
        config=ApiConfig(
            environment="test",
            github_mcp_enabled=True,
            github_repo="acme/app",
        ),
        analysis_session_id="session-001",
        approval_id=approval_id,
        approval_store=store,
        token_provider=lambda: "ghp_secret",
        mcp_executor=fake_mcp_executor,
        mcp_toolset_factory=lambda **kwargs: {"approval_required": kwargs["approval_required"]},
    )

    assert result == {
        "status": "completed",
        "events": [
            {
                "type": "tool",
                "tool": "create_github_issues",
                "summary": "Created 1 GitHub issue(s).",
            }
        ],
        "result": {
            "repo": "acme/app",
            "issues": [
                {
                    "number": 7,
                    "url": "https://github.com/acme/app/issues/7",
                    "title": "Build appointment intake",
                }
            ],
        },
    }
    assert store.get("session-001", approval_id) is None
    assert mcp_calls[0]["toolset"] == {"approval_required": False}
    assert mcp_calls[0]["token"] == "ghp_secret"

    with pytest.raises(GitHubIssueFlowError) as exc_info:
        approve_github_issues(
            config=ApiConfig(
                environment="test",
                github_mcp_enabled=True,
                github_repo="acme/app",
            ),
            analysis_session_id="session-001",
            approval_id=approval_id,
            approval_store=store,
            token_provider=lambda: "ghp_secret",
            mcp_executor=fake_mcp_executor,
            mcp_toolset_factory=lambda **kwargs: {
                "approval_required": kwargs["approval_required"]
            },
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "GITHUB_APPROVAL_INVALID"
    assert len(mcp_calls) == 1


def test_approve_github_issues_invalid_token_refuses_before_mcp():
    mcp_calls = []

    with pytest.raises(GitHubIssueFlowError) as exc_info:
        approve_github_issues(
            config=ApiConfig(
                environment="test",
                github_mcp_enabled=True,
                github_repo="acme/app",
            ),
            analysis_session_id="session-001",
            approval_id="AP-missing",
            approval_store=ApprovalStore(),
            token_provider=lambda: "ghp_secret",
            mcp_executor=lambda **_kwargs: mcp_calls.append("mcp"),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "GITHUB_APPROVAL_INVALID"
    assert mcp_calls == []


def test_approve_github_issues_missing_pat_refuses_before_mcp_and_preserves_token():
    store = ApprovalStore()
    approval_id = store.create(
        "session-001",
        [
            {
                "id": "create_github_issues",
                "label": "Create GitHub issues",
                "repo": "acme/app",
                "issue_count": 1,
                "issues": [
                    {
                        "title": "Build appointment intake",
                        "body": "Priority: high\n\nCapture grooming appointment details.\n\nSource references: SRC-000001",
                        "labels": ["sadify", "priority-high"],
                    }
                ],
            }
        ],
    )
    mcp_calls = []

    with pytest.raises(GitHubIssueFlowError) as exc_info:
        approve_github_issues(
            config=ApiConfig(
                environment="test",
                github_mcp_enabled=True,
                github_repo="acme/app",
            ),
            analysis_session_id="session-001",
            approval_id=approval_id,
            approval_store=store,
            token_provider=lambda: "",
            mcp_executor=lambda **_kwargs: mcp_calls.append("mcp"),
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "GITHUB_TOKEN_MISSING"
    assert store.get("session-001", approval_id) is not None
    assert mcp_calls == []


def test_agent_github_prepare_and_approve_routes(monkeypatch):
    captured = {}

    def fake_prepare(**kwargs):
        captured["prepare"] = kwargs
        return {
            "status": "awaiting_approval",
            "events": [
                {
                    "type": "tool",
                    "tool": "create_github_issues",
                    "summary": "GitHub issue creation needs approval.",
                }
            ],
            "result": {
                "approval_id": "AP-route",
                "repo": "acme/app",
                "proposed_actions": [],
            },
        }

    def fake_approve(**kwargs):
        captured["approve"] = kwargs
        return {
            "status": "completed",
            "events": [
                {
                    "type": "tool",
                    "tool": "create_github_issues",
                    "summary": "Created 1 GitHub issue(s).",
                }
            ],
            "result": {"repo": "acme/app", "issues": []},
        }

    from sadify_api.routes import agent as agent_route

    monkeypatch.setattr(agent_route, "prepare_github_issues", fake_prepare)
    monkeypatch.setattr(agent_route, "approve_github_issues", fake_approve)
    client = TestClient(
        create_app(
            config=ApiConfig(
                environment="test",
                sadify_model="gemini-2.5-flash",
                github_mcp_enabled=True,
                github_repo="acme/app",
            ),
            token_verifier=AcceptingTokenVerifier(),
            analysis_model=FakeRequirementAnalysisModel([]),
            sad_preview_model=FakeSadPreviewModel([]),
            analysis_repository=RequirementAnalysisRepository(),
            sad_preview_repository=SadPreviewRepository(),
        )
    )

    prepare_response = client.post(
        "/agent/github/issues/prepare",
        json={
            "analysis_session_id": "session-route",
            "preview_id": "SP-ROUTE",
            "model": "not-in-catalog",
        },
    )
    approve_response = client.post(
        "/agent/github/issues/approve",
        headers={"Authorization": "Bearer firebase-test-token"},
        json={
            "analysis_session_id": "session-route",
            "approval_id": "AP-route",
            "model": "not-in-catalog",
        },
    )

    assert prepare_response.status_code == 200
    assert prepare_response.json()["status"] == "awaiting_approval"
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "completed"
    assert captured["prepare"]["preview_id"] == "SP-ROUTE"
    assert captured["prepare"]["model"] == "gemini-2.5-flash"
    assert captured["approve"]["approval_id"] == "AP-route"
    assert captured["approve"]["user"].uid == "firebase-uid-001"


class FakeDevTaskModel:
    def __init__(self, outputs: list[dict[str, object]]) -> None:
        self.outputs = list(outputs)
        self.requests: list[tuple[str, str | None]] = []

    def extract_dev_tasks(self, context: str, *, model: str | None = None) -> str:
        self.requests.append((context, model))
        return json.dumps(self.outputs.pop(0))


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
