from __future__ import annotations

import asyncio
from datetime import UTC, datetime
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
from sadify_api.schemas import (
    AuthenticatedUser,
    DevTask,
    GithubIssueDraft,
    GithubIssueSet,
)
from sadify_api.services.drive_repo import DriveRepoRepositoryProtocol
from sadify_api.services.dev_tasks import DevTaskGroundingError, extract_dev_tasks
from sadify_api.services.gemini_structured import (
    DevTaskExtractionModel,
    log_adk_event_usage,
)
from sadify_api.services.github_issue_sets import GithubIssueSetRepositoryProtocol
from sadify_api.services.projects import validate_github_repo
from sadify_api.services.sad_preview import SadPreviewRepository
from sadify_api.services.sad_save import SadSaveRepositoryProtocol


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
    model: str | BaseLlm,
    approval_store: ApprovalStore,
    save_id: str | None = None,
    preview_id: str | None = None,
    repo: str | None = None,
    user: AuthenticatedUser | None = None,
    drive_repo_repository: DriveRepoRepositoryProtocol | None = None,
    sad_save_repository: SadSaveRepositoryProtocol | None = None,
    issue_set_repository: GithubIssueSetRepositoryProtocol | None = None,
    agent_runner: GitHubIssueAgentRunner | None = None,
    mcp_toolset_factory: McpToolsetFactory | None = None,
) -> dict[str, Any]:
    target_repo = _target_repo(config, repo)
    if save_id is not None:
        if (
            user is None
            or drive_repo_repository is None
            or sad_save_repository is None
            or issue_set_repository is None
        ):
            raise RuntimeError("Saved-SAD GitHub prepare dependencies are required.")
        drive_repo, save = _owned_save(
            user=user,
            save_id=save_id,
            drive_repo_repository=drive_repo_repository,
            sad_save_repository=sad_save_repository,
        )
        existing = issue_set_repository.get(
            drive_repo.grant_id,
            drive_repo.active_project_id,
            save.save_id,
        )
        if existing is not None:
            return _awaiting_approval(
                issue_set=existing,
                analysis_session_id=analysis_session_id,
                approval_store=approval_store,
                include_extract_event=False,
            )
        preview_id = save.preview_id

    if not preview_id:
        raise GitHubIssueFlowError(
            404,
            "GITHUB_ISSUE_SET_NOT_FOUND",
            "This saved SAD was never prepared for GitHub issues and its draft is no longer available. Regenerate and save a new draft.",
        )
    if dev_task_model is None:
        raise GitHubIssueFlowError(
            503,
            "DEV_TASKS_MODEL_UNAVAILABLE",
            "Developer task extraction is unavailable for this process.",
        )
    record = preview_repository.get_preview(preview_id)
    if record is None:
        if save_id is not None:
            raise GitHubIssueFlowError(
                404,
                "GITHUB_ISSUE_SET_NOT_FOUND",
                "This saved SAD was never prepared for GitHub issues and its draft is no longer available. Regenerate and save a new draft.",
            )
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

    if save_id is not None:
        project_id = drive_repo.active_project_id
        issues = [
            _issue_from_task(
                task,
                marker=github_issue_marker(project_id, save_id, index),
            )
            for index, task in enumerate(tasks)
        ]
    else:
        issues = [
            _issue_from_task(
                task,
                marker=github_issue_marker("legacy", preview_id, index),
            )
            for index, task in enumerate(tasks)
        ]
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
    if save_id is not None:
        now = datetime.now(UTC)
        candidate = GithubIssueSet(
            grant_id=drive_repo.grant_id,
            project_id=drive_repo.active_project_id,
            save_id=save.save_id,
            preview_id=save.preview_id,
            owner_uid=user.uid,
            repo=target_repo,
            issues=[GithubIssueDraft.model_validate(issue) for issue in issues],
            created_at=now,
            updated_at=now,
        )
        stored = issue_set_repository.create_if_absent(candidate)
        return _awaiting_approval(
            issue_set=stored,
            analysis_session_id=analysis_session_id,
            approval_store=approval_store,
            include_extract_event=True,
        )

    proposed_actions = response.get("proposed_actions")
    if not isinstance(proposed_actions, list) or not proposed_actions:
        proposed_actions = [_github_issue_action(repo=target_repo, issues=issues)]
    approval_id = approval_store.create(analysis_session_id, proposed_actions)
    return _approval_response(
        approval_id=approval_id,
        repo=target_repo,
        preview_id=preview_id,
        proposed_actions=proposed_actions,
        issue_count=len(issues),
        include_extract_event=True,
    )


def relaunch_github_issues(
    *,
    analysis_session_id: str,
    save_id: str,
    user: AuthenticatedUser,
    drive_repo_repository: DriveRepoRepositoryProtocol,
    sad_save_repository: SadSaveRepositoryProtocol,
    issue_set_repository: GithubIssueSetRepositoryProtocol,
    approval_store: ApprovalStore,
) -> dict[str, Any]:
    drive_repo, save = _owned_save(
        user=user,
        save_id=save_id,
        drive_repo_repository=drive_repo_repository,
        sad_save_repository=sad_save_repository,
    )
    issue_set = issue_set_repository.get(
        drive_repo.grant_id,
        drive_repo.active_project_id,
        save.save_id,
    )
    if issue_set is None:
        raise GitHubIssueFlowError(
            404,
            "GITHUB_ISSUE_SET_NOT_FOUND",
            "No prepared GitHub issue set exists for this saved SAD. Regenerate and save a new draft.",
        )
    return _awaiting_approval(
        issue_set=issue_set,
        analysis_session_id=analysis_session_id,
        approval_store=approval_store,
        include_extract_event=False,
    )


def _owned_save(
    *,
    user: AuthenticatedUser,
    save_id: str,
    drive_repo_repository: DriveRepoRepositoryProtocol,
    sad_save_repository: SadSaveRepositoryProtocol,
):
    drive_repo = drive_repo_repository.get_active_repo(user.uid)
    if drive_repo is None or not drive_repo.active_project_id:
        raise GitHubIssueFlowError(
            409,
            "GITHUB_PROJECT_REQUIRED",
            "Select an active project before preparing GitHub issues.",
        )
    save = sad_save_repository.get_save(
        save_id,
        repo_grant_id=drive_repo.grant_id,
        project_id=drive_repo.active_project_id,
    )
    if save is None:
        raise GitHubIssueFlowError(
            404,
            "SAD_SAVE_NOT_FOUND",
            "Saved SAD not found in the active project.",
        )
    if save.owner_uid != user.uid:
        raise GitHubIssueFlowError(
            403,
            "GITHUB_ISSUE_SET_SCOPE_INVALID",
            "This saved SAD does not belong to the signed-in user.",
        )
    return drive_repo, save


def _awaiting_approval(
    *,
    issue_set: GithubIssueSet,
    analysis_session_id: str,
    approval_store: ApprovalStore,
    include_extract_event: bool,
) -> dict[str, Any]:
    issues = [issue.model_dump() for issue in issue_set.issues]
    proposed_actions = [
        _github_issue_action(
            repo=issue_set.repo,
            issues=issues,
            grant_id=issue_set.grant_id,
            project_id=issue_set.project_id,
            save_id=issue_set.save_id,
        )
    ]
    approval_id = approval_store.create(analysis_session_id, proposed_actions)
    return _approval_response(
        approval_id=approval_id,
        repo=issue_set.repo,
        preview_id=issue_set.preview_id,
        save_id=issue_set.save_id,
        proposed_actions=proposed_actions,
        issue_count=len(issues),
        include_extract_event=include_extract_event,
    )


def _approval_response(
    *,
    approval_id: str,
    repo: str,
    preview_id: str,
    proposed_actions: list[dict[str, Any]],
    issue_count: int,
    include_extract_event: bool,
    save_id: str | None = None,
) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    if include_extract_event:
        events.append(
            {
                "type": "tool",
                "tool": "extract_dev_tasks",
                "summary": f"Prepared {issue_count} source-grounded developer task(s).",
            }
        )
    events.append(
        {
            "type": "tool",
            "tool": CREATE_GITHUB_ISSUES,
            "summary": "GitHub issue creation needs approval.",
        }
    )
    result: dict[str, Any] = {
        "approval_id": approval_id,
        "repo": repo,
        "preview_id": preview_id,
        "proposed_actions": proposed_actions,
    }
    if save_id is not None:
        result["save_id"] = save_id
    return {"status": "awaiting_approval", "events": events, "result": result}


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
            log_adk_event_usage(
                model if isinstance(model, str) else getattr(model, "model", "adk"),
                event,
            )
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
    drive_repo_repository: DriveRepoRepositoryProtocol | None = None,
    sad_save_repository: SadSaveRepositoryProtocol | None = None,
    issue_set_repository: GithubIssueSetRepositoryProtocol | None = None,
    github_token: str | None = None,
    token_provider: Callable[[], str | None] | None = None,
    mcp_executor: GitHubMcpExecutor | None = None,
    mcp_toolset_factory: McpToolsetFactory | None = None,
) -> dict[str, Any]:
    approval = approval_store.get(analysis_session_id, approval_id)
    if approval is None:
        raise GitHubIssueFlowError(
            409,
            "GITHUB_APPROVAL_INVALID",
            "Approval token is missing, invalid, or already used.",
        )
    action = _github_issue_action_from_approval(approval.actions)
    secure = any(
        dependency is not None
        for dependency in (
            drive_repo_repository,
            sad_save_repository,
            issue_set_repository,
        )
    )
    issue_set: GithubIssueSet | None = None
    if secure:
        if (
            user is None
            or drive_repo_repository is None
            or sad_save_repository is None
            or issue_set_repository is None
        ):
            raise RuntimeError("Secure GitHub approval dependencies are required.")
        save_id = str(action.get("save_id") or "")
        drive_repo, save = _owned_save(
            user=user,
            save_id=save_id,
            drive_repo_repository=drive_repo_repository,
            sad_save_repository=sad_save_repository,
        )
        action_grant_id = str(action.get("grant_id") or "")
        action_project_id = str(action.get("project_id") or "")
        if (
            action_grant_id != drive_repo.grant_id
            or action_project_id != drive_repo.active_project_id
        ):
            raise GitHubIssueFlowError(
                403,
                "GITHUB_ISSUE_SET_SCOPE_INVALID",
                "The approval does not belong to the active project.",
            )
        issue_set = issue_set_repository.get(
            drive_repo.grant_id,
            drive_repo.active_project_id,
            save.save_id,
        )
        if issue_set is None:
            raise GitHubIssueFlowError(
                404,
                "GITHUB_ISSUE_SET_NOT_FOUND",
                "The prepared GitHub issue set no longer exists. Relaunch it from saved SAD history.",
            )
        stored_issues = [issue.model_dump() for issue in issue_set.issues]
        if action.get("repo") != issue_set.repo or action.get("issues") != stored_issues:
            raise GitHubIssueFlowError(
                409,
                "GITHUB_ISSUE_SET_MISMATCH",
                "The approval no longer matches the prepared GitHub issue set.",
            )
        target_repo = _target_repo(config, issue_set.repo)
        issues = stored_issues
    else:
        target_repo = _target_repo(config, str(action.get("repo") or ""))
        issues = action.get("issues")
    if not isinstance(issues, list) or not issues:
        raise GitHubIssueFlowError(
            409,
            "GITHUB_ISSUES_PAYLOAD_INVALID",
            "Approved GitHub issue payload is missing.",
        )
    if token_provider is not None:
        token = token_provider()
    else:
        token = (github_token or "").strip() or _github_token()
    if not token:
        raise GitHubIssueFlowError(
            503,
            "GITHUB_TOKEN_MISSING",
            "Paste your GitHub token to create issues.",
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
        if secure:
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
                    "save_id": issue_set.save_id,
                    "proposed_actions": approval.actions,
                    "created_issues": response.get("created_issues", []),
                    "skipped_issues": response.get("skipped_issues", []),
                    "totals": response.get("totals"),
                    "error": {
                        "code": response.get("code"),
                        "message": response.get("message"),
                    },
                },
            }
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
    if secure:
        created = response.get("created_issues", [])
        skipped = response.get("skipped_issues", [])
        totals = response.get("totals") or {
            "requested": len(issues),
            "created": len(created) if isinstance(created, list) else 0,
            "skipped": len(skipped) if isinstance(skipped, list) else 0,
        }
        return {
            "status": "completed",
            "events": [
                {
                    "type": "tool",
                    "tool": CREATE_GITHUB_ISSUES,
                    "summary": (
                        f"Created {totals['created']} and skipped "
                        f"{totals['skipped']} existing GitHub issue(s)."
                    ),
                }
            ],
            "result": {
                "repo": target_repo,
                "save_id": issue_set.save_id,
                "created_issues": created,
                "skipped_issues": skipped,
                "totals": totals,
            },
        }
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
    requested = (requested_repo or "").strip()
    if requested:
        # Per-user: the caller supplies their own owner/repo. Validate the format;
        # the user's token already scopes which repos can actually be written.
        try:
            return validate_github_repo(requested)
        except ValueError as exc:
            raise GitHubIssueFlowError(
                422,
                "GITHUB_REPO_INVALID",
                "Enter your repository as owner/name (e.g. octocat/hello-world).",
            ) from exc
    configured = (config.github_repo or "").strip()
    if not configured:
        raise GitHubIssueFlowError(
            503,
            "GITHUB_REPO_NOT_CONFIGURED",
            "Connect your GitHub repository before creating issues.",
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


def github_issue_marker(project_id: str, save_id: str, issue_index: int) -> str:
    return f"<!-- sadify-github-issue:{project_id}:{save_id}:{issue_index} -->"


def _issue_from_task(task: DevTask, *, marker: str) -> dict[str, Any]:
    return {
        "marker": marker,
        "title": task.title,
        "body": (
            f"Priority: {task.priority}\n\n"
            f"{task.description}\n\n"
            "Source references: "
            f"{', '.join(task.source_references)}\n\n"
            f"{marker}"
        ),
        "labels": ["sadify", f"priority-{task.priority}"],
    }


def _github_issue_action(
    repo: str,
    issues: list[dict[str, Any]],
    *,
    grant_id: str | None = None,
    project_id: str | None = None,
    save_id: str | None = None,
) -> dict[str, Any]:
    action = {
        "id": CREATE_GITHUB_ISSUES,
        "label": "Create GitHub issues",
        "repo": repo,
        "issue_count": len(issues),
        "issues": issues,
    }
    if grant_id is not None and project_id is not None and save_id is not None:
        action.update(
            {
                "grant_id": grant_id,
                "project_id": project_id,
                "save_id": save_id,
            }
        )
    return action


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
