import json

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from sadify_api.agent.approval import ApprovalStore, ApprovalTokenInvalidError
from sadify_api.agent.finalize import (
    run_approved_actions,
    run_finalize,
    stream_finalize_events,
)
from sadify_api.agent.tools import AgentDeps
from sadify_api.config import ApiConfig
from sadify_api.routes.auth import verify_authorization_header
from sadify_api.schemas import (
    AgentApproveRequest,
    AgentFinalizeRequest,
    AgentFinalizeResponse,
)
from sadify_api.services.auth import TokenVerifier
from sadify_api.services.analysis_state import RequirementAnalysisRepository
from sadify_api.services.drive_client import DriveClient
from sadify_api.services.drive_repo import DriveRepoRepository
from sadify_api.services.gemini_structured import (
    RequirementAnalysisModel,
    SadPreviewModel,
    SadReviewModel,
)
from sadify_api.services.model_catalog import resolve_gemini_model
from sadify_api.services.projects import ProjectRepository
from sadify_api.services.sad_preview import SadPreviewRepository
from sadify_api.services.sad_save import SadSaveRepository
from sadify_api.services.secret_store import SecretStore
from sadify_api.services.source_uploads import SourceRepository
from sadify_api.services.wiki_state import WikiStateRepository


def create_agent_router(
    *,
    config: ApiConfig,
    analysis_model: RequirementAnalysisModel,
    analysis_repository: RequirementAnalysisRepository,
    sad_preview_model: SadPreviewModel,
    sad_preview_repository: SadPreviewRepository,
    token_verifier: TokenVerifier,
    drive_repo_repository: DriveRepoRepository,
    source_repository: SourceRepository,
    sad_save_repository: SadSaveRepository,
    drive_client: DriveClient | None,
    secret_store: SecretStore | None,
    wiki_state_repository: WikiStateRepository,
    project_repository: ProjectRepository | None,
    sad_review_model: SadReviewModel | None = None,
    approval_store: ApprovalStore | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/agent", tags=["agent"])
    approval_store = approval_store or ApprovalStore()

    @router.post("/finalize", response_model=AgentFinalizeResponse)
    def finalize(request: AgentFinalizeRequest) -> AgentFinalizeResponse:
        resolved_model = resolve_gemini_model(request.model, config)
        return AgentFinalizeResponse.model_validate(
            run_finalize(
                _agent_deps(resolved_model=resolved_model),
                analysis_session_id=request.analysis_session_id,
                model=resolved_model,
                approval_store=approval_store,
            )
        )

    @router.post("/finalize/stream")
    def finalize_stream(request: AgentFinalizeRequest) -> StreamingResponse:
        resolved_model = resolve_gemini_model(request.model, config)

        def event_lines():
            for event in stream_finalize_events(
                _agent_deps(resolved_model=resolved_model),
                analysis_session_id=request.analysis_session_id,
                model=resolved_model,
                approval_store=approval_store,
            ):
                yield json.dumps(event) + "\n"

        return StreamingResponse(
            event_lines(),
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @router.post("/approve", response_model=AgentFinalizeResponse)
    def approve(
        request: AgentApproveRequest,
        authorization: str | None = Header(default=None),
    ) -> AgentFinalizeResponse:
        user = verify_authorization_header(authorization, token_verifier)
        try:
            result = run_approved_actions(
                _agent_deps(
                    resolved_model=resolve_gemini_model(request.model, config),
                    user=user,
                ),
                analysis_session_id=request.analysis_session_id,
                approval_store=approval_store,
                approval_id=request.approval_id,
            )
        except ApprovalTokenInvalidError as exc:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "AGENT_APPROVAL_INVALID",
                    "message": "Approval token is missing, invalid, or already used.",
                },
            ) from exc
        return AgentFinalizeResponse.model_validate(result)

    def _agent_deps(
        *,
        resolved_model: str,
        user=None,
    ) -> AgentDeps:
        return AgentDeps(
            analysis_repository=analysis_repository,
            sad_preview_repository=sad_preview_repository,
            analysis_model=analysis_model,
            sad_preview_model=sad_preview_model,
            sad_review_model=sad_review_model,
            selected_model=resolved_model,
            user=user,
            drive_repo_repository=drive_repo_repository,
            source_repository=source_repository,
            sad_save_repository=sad_save_repository,
            config=config,
            drive_client=drive_client,
            secret_store=secret_store,
            wiki_state_repository=wiki_state_repository,
            project_repository=project_repository,
        )

    return router
