from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any

from google.adk.tools import BaseTool, FunctionTool

from sadify_api.agent.approval import WriteApproval, WriteApprovalRequiredError
from sadify_api.config import ApiConfig
from sadify_api.schemas import (
    AuthenticatedUser,
    RequirementAnalysisRequest,
    SadPreviewRequest,
    SadSaveRequest,
    WikiUpdateRequest,
)
from sadify_api.services.analysis_flow import run_analysis_turn
from sadify_api.services.analysis_state import RequirementAnalysisRepository
from sadify_api.services.drive_client import DriveClient, DriveTokenInvalidError
from sadify_api.services.drive_repo import DriveRepoRepository
from sadify_api.services.gemini_structured import (
    RequirementAnalysisModel,
    SadPreviewModel,
    SadReviewModel,
    parse_sad_review,
)
from sadify_api.services.projects import ProjectRepository
from sadify_api.services.sad_flow import (
    SadPreviewBlockedError,
    SadSaveFlowError,
    WikiFlowContext,
    WikiFlowError,
    run_sad_preview,
    run_sad_save,
    run_wiki_update,
)
from sadify_api.services.sad_preview import SadPreviewRepository
from sadify_api.services.sad_save import SadSaveRepository
from sadify_api.services.secret_store import SecretStore
from sadify_api.services.source_uploads import SourceRepository
from sadify_api.services.wiki_state import WikiStateRepository


ToolPayload = dict[str, Any]


@dataclass(frozen=True)
class AgentDeps:
    analysis_repository: RequirementAnalysisRepository
    sad_preview_repository: SadPreviewRepository
    analysis_model: RequirementAnalysisModel
    sad_preview_model: SadPreviewModel
    sad_review_model: SadReviewModel | None = None
    selected_model: str | None = None
    max_sad_generations: int | None = None
    user: AuthenticatedUser | None = None
    write_approval: WriteApproval | None = None
    drive_repo_repository: DriveRepoRepository | None = None
    source_repository: SourceRepository | None = None
    sad_save_repository: SadSaveRepository | None = None
    config: ApiConfig | None = None
    drive_client: DriveClient | None = None
    secret_store: SecretStore | None = None
    wiki_state_repository: WikiStateRepository | None = None
    project_repository: ProjectRepository | None = None
    sad_save_runner: Callable[..., Any] | None = None
    wiki_context_builder: Callable[["AgentDeps"], WikiFlowContext] | None = None
    wiki_update_runner: Callable[..., Any] | None = None


@dataclass(frozen=True)
class AgentToolFunctions:
    get_readiness: Callable[[str], ToolPayload]
    ask_clarification: Callable[[str], ToolPayload]
    generate_sad: Callable[[str], ToolPayload]
    review_sad: Callable[[str], ToolPayload]
    save_to_drive: Callable[[str], ToolPayload]
    update_wiki: Callable[[bool], ToolPayload]


def build_agent_tools(deps: AgentDeps) -> list[BaseTool]:
    tool_functions = build_agent_tool_functions(deps)
    return [
        FunctionTool(tool_functions.get_readiness),
        FunctionTool(tool_functions.ask_clarification),
        FunctionTool(tool_functions.generate_sad),
        FunctionTool(tool_functions.review_sad),
        FunctionTool(_adk_write_tool(tool_functions.save_to_drive)),
        FunctionTool(_adk_write_tool(tool_functions.update_wiki)),
    ]


def build_agent_tool_functions(deps: AgentDeps) -> AgentToolFunctions:
    generation_count = 0
    last_generation_payload: ToolPayload | None = None

    def get_readiness(analysis_id: str) -> ToolPayload:
        """Return draft readiness for a saved analysis before deciding next action."""
        record = deps.analysis_repository.get_analysis(analysis_id)
        if record is None:
            return {
                "analysis_id": analysis_id,
                "score": 0,
                "confidence": "Low",
                "label": "Analysis not found",
                "gaps": [
                    {
                        "id": "analysis_not_found",
                        "label": "Analysis not found",
                        "status": "missing",
                    }
                ],
            }

        analysis = record.analysis
        readiness = (
            analysis.questionnaire.draft_readiness
            if analysis.questionnaire is not None
            else analysis.readiness
        )
        return {
            "analysis_id": record.analysis_id,
            "score": readiness.score,
            "confidence": readiness.confidence,
            "label": readiness.label,
            "gaps": _readiness_gaps(analysis),
        }

    def ask_clarification(analysis_session_id: str) -> ToolPayload:
        """Ask one clarification using SADify's existing locked-slot engine."""
        prior = deps.analysis_repository.latest_for_session(analysis_session_id)
        if prior is None:
            return {
                "analysis_id": "",
                "question": "I need a saved analysis session before asking the next clarification.",
                "why": "The questionnaire engine needs prior context to choose the right slot.",
                "choices": [],
                "target_category": "",
                "target_slot_id": "",
            }

        record = run_analysis_turn(
            request=RequirementAnalysisRequest(
                requirement_text=prior.requirement_text,
                guest_draft_id=prior.guest_draft_id,
                analysis_session_id=analysis_session_id,
                model=deps.selected_model,
                source_references=prior.analysis.source_references,
            ),
            model=deps.analysis_model,
            repository=deps.analysis_repository,
        )
        question = record.analysis.next_question
        return {
            "analysis_id": record.analysis_id,
            "question": question.text,
            "why": question.why_this_matters,
            "choices": [
                {"id": choice.id, "label": choice.label}
                for choice in question.choices
            ],
            "target_category": question.target_category,
            "target_slot_id": question.target_slot_id,
        }

    def generate_sad(analysis_id: str) -> ToolPayload:
        """Generate a SAD preview from a saved analysis when readiness is sufficient."""
        nonlocal generation_count, last_generation_payload
        if (
            deps.max_sad_generations is not None
            and generation_count >= deps.max_sad_generations
        ):
            payload = dict(
                last_generation_payload
                or {
                    "preview_id": "",
                    "sections": [],
                    "assumptions": [],
                    "open_questions": [],
                }
            )
            payload["regenerate_cap_reached"] = True
            return payload

        record = deps.analysis_repository.get_analysis(analysis_id)
        if record is None:
            return {
                "preview_id": "",
                "sections": [],
                "assumptions": [],
                "open_questions": ["Run analysis before generating a SAD preview."],
                "error": "analysis_not_found",
            }

        try:
            preview_record = run_sad_preview(
                request=SadPreviewRequest(
                    requirement_text=record.requirement_text,
                    analysis_id=record.analysis_id,
                    analysis=record.analysis,
                    model=deps.selected_model,
                    source_references=record.analysis.source_references,
                ),
                model=deps.sad_preview_model,
                repository=deps.sad_preview_repository,
            )
        except SadPreviewBlockedError as exc:
            generation_count += 1
            return {
                "preview_id": "",
                "sections": [],
                "assumptions": [
                    "SAD preview is blocked until the missing basics are clarified."
                ],
                "open_questions": [
                    f"Clarify missing basic: {missing_basic}"
                    for missing_basic in exc.missing_basics
                ],
                "error": "sad_preview_blocked",
                "missing_basics": exc.missing_basics,
            }

        preview = preview_record.preview
        payload = {
            "preview_id": preview_record.preview_id,
            "sections": [section.model_dump() for section in preview.sections],
            "assumptions": list(preview.assumptions),
            "open_questions": list(preview.open_questions),
        }
        generation_count += 1
        last_generation_payload = payload
        return payload

    def review_sad(preview_id: str) -> ToolPayload:
        """Review a saved SAD preview and return an advisory quality verdict."""
        record = deps.sad_preview_repository.get_preview(preview_id)
        if record is None:
            return {
                "preview_id": preview_id,
                "verdict": "ask",
                "issues": [
                    {
                        "severity": "high",
                        "category": "preview",
                        "message": "Generate a SAD preview before reviewing it.",
                    }
                ],
            }
        if deps.sad_review_model is None:
            return {"preview_id": preview_id, "verdict": "proceed", "issues": []}

        review = parse_sad_review(
            deps.sad_review_model.review_sad(
                _review_sad_context(record),
                model=deps.selected_model,
            )
        )
        payload = {
            "preview_id": preview_id,
            "verdict": review.verdict,
            "issues": [issue.model_dump() for issue in review.issues],
        }
        if (
            payload["verdict"] == "regenerate"
            and deps.max_sad_generations is not None
            and generation_count >= deps.max_sad_generations
        ):
            payload["regenerate_cap_reached"] = True
        return payload

    def save_to_drive(preview_id: str) -> ToolPayload:
        """Save the SAD preview to Drive only after explicit approval."""
        _require_write_approval(
            deps,
            action_id="save_to_drive",
            preview_id=preview_id,
            proposed_actions=_save_and_wiki_actions(preview_id),
            tool_name="save_to_drive",
        )
        _ensure_save_deps(deps)
        runner = deps.sad_save_runner or run_sad_save
        try:
            record = runner(
                user=deps.user,
                request=SadSaveRequest(preview_id=preview_id),
                repository=deps.sad_preview_repository,
                drive_repo_repository=deps.drive_repo_repository,
                source_repository=deps.source_repository,
                sad_save_repository=deps.sad_save_repository,
                config=deps.config,
                drive_client=deps.drive_client,
                secret_store=deps.secret_store,
                project_repository=deps.project_repository,
            )
        except SadSaveFlowError as exc:
            return {
                "status": "error",
                "code": exc.code,
                "message": exc.message,
            }
        return {
            "status": "saved",
            "save_id": record.save_id,
            "preview_id": record.preview_id,
            "doc_url": record.sad_doc.url,
            "doc_path": record.sad_doc.path,
        }

    def update_wiki(force_overwrite: bool = False) -> ToolPayload:
        """Update the Drive wiki only after approval, with conflict re-approval."""
        action_id = "overwrite_wiki" if force_overwrite else "update_wiki"
        _require_write_approval(
            deps,
            action_id=action_id,
            proposed_actions=[_wiki_action(force_overwrite=force_overwrite)],
            tool_name="update_wiki",
        )
        _ensure_wiki_deps(deps)
        context_builder = deps.wiki_context_builder or _build_wiki_context
        update_runner = deps.wiki_update_runner or run_wiki_update
        try:
            response = update_runner(
                context=context_builder(deps),
                request=WikiUpdateRequest(
                    expected_remote_hashes={},
                    force_overwrite=force_overwrite,
                ),
                repository=deps.sad_preview_repository,
                wiki_state_repository=deps.wiki_state_repository,
            )
        except WikiFlowError as exc:
            if exc.code == "WIKI_CONFLICT":
                changed_files = exc.changed_files or []
                raise WriteApprovalRequiredError(
                    tool_name="update_wiki",
                    proposed_actions=[
                        {
                            "id": "overwrite_wiki",
                            "label": "Overwrite changed wiki files",
                            "changed_files": changed_files,
                            "force_overwrite": True,
                        }
                    ],
                    message="Confirm overwrite before updating changed wiki files.",
                    changed_files=changed_files,
                ) from exc
            return {
                "status": "error",
                "code": exc.code,
                "message": exc.message,
                "changed_files": exc.changed_files,
            }
        return {
            "status": "updated",
            "file_count": len(response.files),
        }

    return AgentToolFunctions(
        get_readiness=get_readiness,
        ask_clarification=ask_clarification,
        generate_sad=generate_sad,
        review_sad=review_sad,
        save_to_drive=save_to_drive,
        update_wiki=update_wiki,
    )


def _readiness_gaps(analysis) -> list[dict[str, str]]:
    if analysis.questionnaire is not None:
        return [
            {
                "id": category.id,
                "label": category.label,
                "status": category.status,
            }
            for category in analysis.questionnaire.categories
            if category.status != "ready"
        ]
    return [
        {
            "id": category.id,
            "label": category.label,
            "status": category.status,
        }
        for category in analysis.categories
        if category.status != "complete"
    ]


def _review_sad_context(record) -> str:
    return (
        "Requirement text:\n"
        f"{record.requirement_text}\n\n"
        f"Analysis ID: {record.analysis_id or ''}\n\n"
        "SAD preview JSON:\n"
        f"{record.preview.model_dump_json()}"
    )


def _require_write_approval(
    deps: AgentDeps,
    *,
    action_id: str,
    proposed_actions: list[dict[str, object]],
    tool_name: str,
    preview_id: str | None = None,
) -> None:
    if deps.write_approval is None or not deps.write_approval.allows(
        action_id,
        preview_id=preview_id,
    ):
        raise WriteApprovalRequiredError(
            tool_name=tool_name,
            preview_id=preview_id,
            proposed_actions=proposed_actions,
        )


def _adk_write_tool(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except WriteApprovalRequiredError as exc:
            return {
                "approval_required": True,
                "tool": exc.tool_name,
                "preview_id": exc.preview_id,
                "proposed_actions": exc.proposed_actions,
                "message": exc.message,
                "changed_files": exc.changed_files,
            }

    return wrapped


def _save_and_wiki_actions(preview_id: str) -> list[dict[str, object]]:
    return [
        {
            "id": "save_to_drive",
            "label": "Save SAD to Google Drive",
            "preview_id": preview_id,
        },
        {
            "id": "update_wiki",
            "label": "Update project wiki",
            "preview_id": preview_id,
        },
    ]


def _wiki_action(*, force_overwrite: bool) -> dict[str, object]:
    if force_overwrite:
        return {
            "id": "overwrite_wiki",
            "label": "Overwrite changed wiki files",
            "force_overwrite": True,
        }
    return {
        "id": "update_wiki",
        "label": "Update project wiki",
        "force_overwrite": False,
    }


def _ensure_save_deps(deps: AgentDeps) -> None:
    if deps.sad_save_runner is not None:
        if deps.user is None:
            raise RuntimeError("Missing agent save dependencies: user")
        return
    missing = [
        name
        for name, value in {
            "user": deps.user,
            "drive_repo_repository": deps.drive_repo_repository,
            "source_repository": deps.source_repository,
            "sad_save_repository": deps.sad_save_repository,
            "config": deps.config,
        }.items()
        if value is None
    ]
    if missing:
        raise RuntimeError(f"Missing agent save dependencies: {', '.join(missing)}")


def _ensure_wiki_deps(deps: AgentDeps) -> None:
    if deps.wiki_context_builder is not None and deps.wiki_update_runner is not None:
        return
    missing = [
        name
        for name, value in {
            "user": deps.user,
            "drive_repo_repository": deps.drive_repo_repository,
            "source_repository": deps.source_repository,
            "sad_save_repository": deps.sad_save_repository,
            "config": deps.config,
            "wiki_state_repository": deps.wiki_state_repository,
        }.items()
        if value is None
    ]
    if missing:
        raise RuntimeError(f"Missing agent wiki dependencies: {', '.join(missing)}")


def _build_wiki_context(deps: AgentDeps) -> WikiFlowContext:
    assert deps.user is not None
    assert deps.drive_repo_repository is not None
    assert deps.source_repository is not None
    assert deps.sad_save_repository is not None
    assert deps.config is not None

    repo = deps.drive_repo_repository.get_active_repo(deps.user.uid)
    if repo is None or repo.status == "disconnected" or repo.saves_blocked:
        raise WikiFlowError(
            409,
            "WIKI_REPO_REQUIRED",
            "Connect a Google Drive project repo before updating the wiki.",
        )
    project = _active_project(deps, repo)
    if deps.config.drive_mode != "live" or not deps.config.drive_live_enabled:
        raise WikiFlowError(
            503,
            "WIKI_LIVE_MODE_DISABLED",
            "Live wiki updates are disabled for this process.",
        )
    saves = sorted(
        deps.sad_save_repository.list_for_project(
            grant_id=repo.grant_id,
            project_id=project.project_id,
        ),
        key=lambda record: record.created_at,
    )
    if not saves:
        raise WikiFlowError(
            409,
            "WIKI_SAVE_REQUIRED",
            "Save a SAD preview to this repo before generating a wiki.",
        )
    latest_save = saves[-1]
    sources = [
        source
        for source_id in latest_save.manifest.source_ids
        if (source := deps.source_repository.get_source(source_id)) is not None
    ]
    drive_client = deps.drive_client
    secret_store = deps.secret_store
    if drive_client is None or secret_store is None:
        raise WikiFlowError(
            503,
            "WIKI_LIVE_MODE_DISABLED",
            "Live wiki updates are disabled for this process.",
        )
    refresh_token = secret_store.get_user_refresh_token(deps.user.uid)
    if not refresh_token:
        raise WikiFlowError(
            409,
            "WIKI_REPO_DISCONNECTED",
            "Reconnect Google Drive before updating the wiki.",
        )
    try:
        access_token = drive_client.refresh_access_token(refresh_token)
    except DriveTokenInvalidError as exc:
        raise WikiFlowError(
            409,
            "WIKI_REPO_DISCONNECTED",
            "Reconnect Google Drive before updating the wiki.",
        ) from exc
    return WikiFlowContext(
        repo=repo,
        project=project,
        latest_save=latest_save,
        all_saves_for_repo=saves,
        sources=sources,
        drive_client=drive_client,
        access_token=access_token,
    )


def _active_project(deps: AgentDeps, repo) -> Any:
    if not repo.active_project_id:
        raise WikiFlowError(
            409,
            "WIKI_PROJECT_REQUIRED",
            "Create or select a project before updating the wiki.",
        )
    if deps.project_repository is not None:
        project = deps.project_repository.get_project(
            repo.grant_id,
            repo.active_project_id,
        )
        if project is not None:
            return project
    for project in repo.available_projects:
        if project.project_id == repo.active_project_id:
            return project
    raise WikiFlowError(
        409,
        "WIKI_PROJECT_REQUIRED",
        "Create or select a project before updating the wiki.",
    )
