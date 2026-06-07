from __future__ import annotations

import asyncio
import inspect
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable

from google.adk.agents import Agent
from google.adk.models import BaseLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool.mcp_toolset import (
    McpToolset,
    StdioConnectionParams,
    StdioServerParameters,
)
from google.genai import types
from mcp import ClientSession
from mcp.client.stdio import (
    StdioServerParameters as ClientStdioServerParameters,
    stdio_client,
)

from sadify_api.agent.approval import ApprovalStore
from sadify_api.config import ApiConfig
from sadify_api.schemas import AuthenticatedUser, DevTask
from sadify_api.services.dev_tasks import DevTaskGroundingError, extract_dev_tasks
from sadify_api.services.gemini_structured import DevTaskExtractionModel
from sadify_api.services.sad_preview import SadPreviewRepository


CREATE_GITHUB_ISSUES = "create_github_issues"
GITHUB_TOKEN_ENV = "SADIFY_GITHUB_TOKEN"
GITHUB_REPO_ENV = "SADIFY_GITHUB_REPO"
GITHUB_APPROVAL_REQUIRED_ENV = "SADIFY_GITHUB_APPROVAL_REQUIRED"

McpToolsetFactory = Callable[..., Any]
GitHubIssueAgentRunner = Callable[..., dict[str, Any]]
GitHubMcpExecutor = Callable[..., dict[str, Any]]


class GitHubIssueFlowError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def build_github_mcp_toolset(
    *,
    repo: str,
    approval_required: bool,
    token: str | None = None,
    python_executable: str | None = None,
    repo_root: str | os.PathLike[str] | None = None,
) -> McpToolset:
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=python_executable or sys.executable,
                args=["-m", "services.mcp.github_server"],
                env=_mcp_server_env(
                    repo=repo,
                    approval_required=approval_required,
                    token=token,
                ),
                cwd=str(repo_root or _repo_root()),
            ),
            timeout=5.0,
        ),
        tool_filter=[CREATE_GITHUB_ISSUES],
    )


def prepare_github_issues(
    *,
    preview_repository: SadPreviewRepository,
    dev_task_model: DevTaskExtractionModel | None,
    config: ApiConfig,
    analysis_session_id: str,
    preview_id: str,
    model: str | BaseLlm,
    approval_store: ApprovalStore,
    repo: str | None = None,
    agent_runner: GitHubIssueAgentRunner | None = None,
    mcp_toolset_factory: McpToolsetFactory | None = None,
) -> dict[str, Any]:
    target_repo = _target_repo(config, repo)
    if dev_task_model is None:
        raise GitHubIssueFlowError(
            503,
            "DEV_TASKS_MODEL_UNAVAILABLE",
            "Developer task extraction is unavailable for this process.",
        )
    record = preview_repository.get_preview(preview_id)
    if record is None:
        raise GitHubIssueFlowError(
            404,
            "SAD_PREVIEW_NOT_FOUND",
            "Generate a SAD preview before preparing GitHub issues.",
        )

    try:
        tasks = extract_dev_tasks(
            preview=record.preview,
            model=dev_task_model,
            selected_model=model if isinstance(model, str) else None,
        )
    except DevTaskGroundingError as exc:
        raise GitHubIssueFlowError(
            422,
            "DEV_TASKS_UNGROUNDED",
            str(exc),
        ) from exc
    except Exception as exc:
        raise GitHubIssueFlowError(
            502,
            "DEV_TASKS_MODEL_ERROR",
            str(exc),
        ) from exc

    issues = [_issue_from_task(task) for task in tasks]
    if not issues:
        return {
            "status": "completed",
            "events": [
                {
                    "type": "tool",
                    "tool": "extract_dev_tasks",
                    "summary": "Prepared 0 source-grounded developer task(s).",
                }
            ],
            "result": {
                "repo": target_repo,
                "issues": [],
                "message": "No source-grounded developer tasks were generated.",
            },
        }

    factory = mcp_toolset_factory or _default_mcp_toolset_factory(target_repo)
    runner = agent_runner or run_github_issue_prepare_agent
    response = runner(
        model=model,
        repo=target_repo,
        issues=issues,
        mcp_toolset_factory=factory,
    )
    if response.get("approval_required") is not True:
        raise GitHubIssueFlowError(
            502,
            "GITHUB_AGENT_APPROVAL_MISSING",
            "The GitHub agent did not request approval before issue creation.",
        )
    proposed_actions = response.get("proposed_actions")
    if not isinstance(proposed_actions, list) or not proposed_actions:
        proposed_actions = [_github_issue_action(repo=target_repo, issues=issues)]
    approval_id = approval_store.create(analysis_session_id, proposed_actions)
    return {
        "status": "awaiting_approval",
        "events": [
            {
                "type": "tool",
                "tool": "extract_dev_tasks",
                "summary": (
                    f"Prepared {len(issues)} source-grounded developer task(s)."
                ),
            },
            {
                "type": "tool",
                "tool": CREATE_GITHUB_ISSUES,
                "summary": "GitHub issue creation needs approval.",
            },
        ],
        "result": {
            "approval_id": approval_id,
            "repo": target_repo,
            "preview_id": preview_id,
            "proposed_actions": proposed_actions,
        },
    }


def run_github_issue_prepare_agent(
    *,
    model: str | BaseLlm,
    repo: str,
    issues: list[dict[str, Any]],
    mcp_toolset_factory: McpToolsetFactory,
) -> dict[str, Any]:
    toolset = mcp_toolset_factory(approval_required=True)
    agent = Agent(
        name="sadify_github_issues",
        model=model,
        description="SADify agent that proposes GitHub issue creation via MCP.",
        instruction=(
            "Create GitHub issues only after tool-level approval. "
            "Use the create_github_issues MCP tool exactly once with the "
            "provided repo and issues. Do not add tasks or facts."
        ),
        tools=[toolset],
    )
    session_id = "github-issues-prepare"
    session_service = InMemorySessionService()
    session_service.create_session_sync(
        app_name="sadify-api",
        user_id="sadify-github",
        session_id=session_id,
    )
    runner = Runner(
        app_name="sadify-api",
        agent=agent,
        session_service=session_service,
    )
    responses: list[dict[str, Any]] = []
    try:
        for event in runner.run(
            user_id="sadify-github",
            session_id=session_id,
            new_message=_github_issue_prepare_message(repo=repo, issues=issues),
        ):
            for function_response in event.get_function_responses():
                if function_response.name == CREATE_GITHUB_ISSUES:
                    responses.append(
                        _adk_function_response_payload(
                            dict(function_response.response or {})
                        )
                    )
    finally:
        _close_toolset(toolset)
    if not responses:
        return {
            "status": "error",
            "code": "GITHUB_AGENT_NO_MCP_CALL",
            "message": "The GitHub agent did not call create_github_issues.",
        }
    return responses[-1]


def approve_github_issues(
    *,
    config: ApiConfig,
    analysis_session_id: str,
    approval_id: str,
    approval_store: ApprovalStore,
    user: AuthenticatedUser | None = None,
    token_provider: Callable[[], str | None] | None = None,
    mcp_executor: GitHubMcpExecutor | None = None,
    mcp_toolset_factory: McpToolsetFactory | None = None,
) -> dict[str, Any]:
    del user
    target_repo = _target_repo(config, None)
    approval = approval_store.get(analysis_session_id, approval_id)
    if approval is None:
        raise GitHubIssueFlowError(
            409,
            "GITHUB_APPROVAL_INVALID",
            "Approval token is missing, invalid, or already used.",
        )
    action = _github_issue_action_from_approval(approval.actions)
    repo = str(action.get("repo") or "")
    if _normalize_repo(repo) != _normalize_repo(target_repo):
        raise GitHubIssueFlowError(
            409,
            "GITHUB_REPO_NOT_ALLOWED",
            f"This flow is configured only for repo {target_repo}.",
        )
    issues = action.get("issues")
    if not isinstance(issues, list) or not issues:
        raise GitHubIssueFlowError(
            409,
            "GITHUB_ISSUES_PAYLOAD_INVALID",
            "Approved GitHub issue payload is missing.",
        )
    token = (token_provider or _github_token)()
    if not token:
        raise GitHubIssueFlowError(
            503,
            "GITHUB_TOKEN_MISSING",
            f"Set {GITHUB_TOKEN_ENV} before creating GitHub issues.",
        )

    factory = mcp_toolset_factory or _default_mcp_toolset_factory(target_repo)
    executor = mcp_executor or call_create_github_issues_mcp
    response = executor(
        repo=target_repo,
        issues=issues,
        token=token,
        mcp_toolset_factory=factory,
    )
    if response.get("status") != "created":
        return {
            "status": "awaiting_approval",
            "events": [
                {
                    "type": "tool",
                    "tool": CREATE_GITHUB_ISSUES,
                    "summary": str(
                        response.get("message") or "GitHub issue creation failed."
                    ),
                }
            ],
            "result": {
                "approval_id": approval_id,
                "repo": target_repo,
                "proposed_actions": approval.actions,
                "error": {
                    "code": response.get("code"),
                    "message": response.get("message"),
                },
            },
        }

    approval_store.consume(analysis_session_id, approval_id)
    created = response.get("issues", [])
    issue_count = len(created) if isinstance(created, list) else 0
    return {
        "status": "completed",
        "events": [
            {
                "type": "tool",
                "tool": CREATE_GITHUB_ISSUES,
                "summary": f"Created {issue_count} GitHub issue(s).",
            }
        ],
        "result": {
            "repo": target_repo,
            "issues": created,
        },
    }


def call_create_github_issues_mcp(
    *,
    repo: str,
    issues: list[dict[str, Any]],
    token: str,
    mcp_toolset_factory: McpToolsetFactory | None = None,
) -> dict[str, Any]:
    del mcp_toolset_factory
    return asyncio.run(
        _call_create_github_issues_mcp_async(
            repo=repo,
            issues=issues,
            token=token,
        )
    )


async def _call_create_github_issues_mcp_async(
    *,
    repo: str,
    issues: list[dict[str, Any]],
    token: str,
) -> dict[str, Any]:
    params = ClientStdioServerParameters(
        command=sys.executable,
        args=["-m", "services.mcp.github_server"],
        env=_mcp_server_env(repo=repo, approval_required=False, token=token),
        cwd=str(_repo_root()),
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                CREATE_GITHUB_ISSUES,
                {"repo": repo, "issues": issues},
            )
    return _call_tool_payload(result)


def _target_repo(config: ApiConfig, requested_repo: str | None) -> str:
    if not config.github_mcp_enabled:
        raise GitHubIssueFlowError(
            503,
            "GITHUB_MCP_DISABLED",
            "GitHub issue creation is disabled for this process.",
        )
    configured = (config.github_repo or "").strip()
    if not configured:
        raise GitHubIssueFlowError(
            503,
            "GITHUB_REPO_NOT_CONFIGURED",
            "Set SADIFY_GITHUB_REPO before creating GitHub issues.",
        )
    if requested_repo and _normalize_repo(requested_repo) != _normalize_repo(configured):
        raise GitHubIssueFlowError(
            409,
            "GITHUB_REPO_NOT_ALLOWED",
            f"This flow is configured only for repo {configured}.",
        )
    return configured


def _default_mcp_toolset_factory(repo: str) -> McpToolsetFactory:
    def factory(*, approval_required: bool, token: str | None = None) -> McpToolset:
        return build_github_mcp_toolset(
            repo=repo,
            approval_required=approval_required,
            token=token,
        )

    return factory


def _mcp_server_env(
    *,
    repo: str,
    approval_required: bool,
    token: str | None,
) -> dict[str, str]:
    env = dict(os.environ)
    env[GITHUB_REPO_ENV] = repo
    env[GITHUB_APPROVAL_REQUIRED_ENV] = "true" if approval_required else "false"
    if approval_required:
        env.pop(GITHUB_TOKEN_ENV, None)
    elif token:
        env[GITHUB_TOKEN_ENV] = token
    return env


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for parent in start.parents:
        if (parent / "services" / "mcp" / "github_server.py").exists():
            return parent
    raise RuntimeError("Could not locate SADify repository root for MCP server.")


def _github_issue_prepare_message(
    *,
    repo: str,
    issues: list[dict[str, Any]],
) -> types.Content:
    prompt = (
        "Prepare GitHub issue creation for these SADify developer tasks.\n"
        "Call create_github_issues exactly once with this repo and issue list. "
        "The MCP tool is approval-gated in this run, so it must return an "
        "approval-required proposal instead of creating issues.\n\n"
        f"repo: {repo}\n"
        "issues JSON:\n"
        f"{json.dumps(issues, ensure_ascii=True)}"
    )
    return types.Content(role="user", parts=[types.Part.from_text(text=prompt)])


def _issue_from_task(task: DevTask) -> dict[str, Any]:
    return {
        "title": task.title,
        "body": (
            f"Priority: {task.priority}\n\n"
            f"{task.description}\n\n"
            "Source references: "
            f"{', '.join(task.source_references)}"
        ),
        "labels": ["sadify", f"priority-{task.priority}"],
    }


def _github_issue_action(repo: str, issues: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": CREATE_GITHUB_ISSUES,
        "label": "Create GitHub issues",
        "repo": repo,
        "issue_count": len(issues),
        "issues": issues,
    }


def _github_issue_action_from_approval(
    actions: list[dict[str, object]],
) -> dict[str, object]:
    for action in actions:
        if action.get("id") == CREATE_GITHUB_ISSUES:
            return action
    raise GitHubIssueFlowError(
        409,
        "GITHUB_APPROVAL_INVALID",
        "Approval token is not valid for GitHub issue creation.",
    )


def _github_token() -> str | None:
    return os.getenv(GITHUB_TOKEN_ENV)


def _call_tool_payload(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        # FastMCP wraps a bare dict return under {"result": {...}} to fit the
        # generated object schema; unwrap it back to the tool's own payload.
        if list(structured.keys()) == ["result"] and isinstance(
            structured["result"], dict
        ):
            return structured["result"]
        return structured
    text_chunks: list[str] = []
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            text_chunks.append(text)
            continue
        if isinstance(payload, dict):
            return payload
    # Surface the real MCP failure (tool exception, bad repo/PAT) instead of a
    # generic message — failures must be visible and explained plainly.
    detail = " ".join(chunk.strip() for chunk in text_chunks if chunk.strip())
    is_error = bool(getattr(result, "isError", False))
    return {
        "status": "error",
        "code": "GITHUB_MCP_ERROR" if is_error else "GITHUB_MCP_RESPONSE_INVALID",
        "message": (
            f"GitHub MCP error: {detail}"
            if detail
            else "GitHub MCP server returned an unexpected response."
        ),
    }


def _adk_function_response_payload(response: dict[str, Any]) -> dict[str, Any]:
    structured = response.get("structuredContent") or response.get(
        "structured_content"
    )
    if isinstance(structured, dict):
        return structured
    content = response.get("content")
    if isinstance(content, list):
        for item in content:
            text = item.get("text") if isinstance(item, dict) else None
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
    return response


def _close_toolset(toolset: Any) -> None:
    close = getattr(toolset, "close", None)
    if close is None:
        return
    result = close()
    if inspect.isawaitable(result):
        asyncio.run(result)


def _normalize_repo(repo: str) -> str:
    return repo.strip().lower()
