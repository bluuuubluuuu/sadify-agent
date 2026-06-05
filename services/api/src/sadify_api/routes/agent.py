from fastapi import APIRouter

from sadify_api.agent.finalize import run_finalize
from sadify_api.agent.tools import AgentDeps
from sadify_api.config import ApiConfig
from sadify_api.schemas import AgentFinalizeRequest, AgentFinalizeResponse
from sadify_api.services.analysis_state import RequirementAnalysisRepository
from sadify_api.services.gemini_structured import (
    RequirementAnalysisModel,
    SadPreviewModel,
)
from sadify_api.services.model_catalog import resolve_gemini_model
from sadify_api.services.sad_preview import SadPreviewRepository


def create_agent_router(
    *,
    config: ApiConfig,
    analysis_model: RequirementAnalysisModel,
    analysis_repository: RequirementAnalysisRepository,
    sad_preview_model: SadPreviewModel,
    sad_preview_repository: SadPreviewRepository,
) -> APIRouter:
    router = APIRouter(prefix="/agent", tags=["agent"])

    @router.post("/finalize", response_model=AgentFinalizeResponse)
    def finalize(request: AgentFinalizeRequest) -> AgentFinalizeResponse:
        resolved_model = resolve_gemini_model(request.model, config)
        return AgentFinalizeResponse.model_validate(
            run_finalize(
                AgentDeps(
                    analysis_repository=analysis_repository,
                    sad_preview_repository=sad_preview_repository,
                    analysis_model=analysis_model,
                    sad_preview_model=sad_preview_model,
                    selected_model=resolved_model,
                ),
                analysis_session_id=request.analysis_session_id,
                model=resolved_model,
            )
        )

    return router
