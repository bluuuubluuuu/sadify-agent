from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sadify_api.config import ApiConfig, load_api_config
from sadify_api.routes.analysis import create_analysis_router
from sadify_api.routes.auth import create_auth_router
from sadify_api.routes.diagnostics import create_diagnostics_router
from sadify_api.routes.drive import create_drive_router
from sadify_api.routes.drafts import create_drafts_router
from sadify_api.routes.health import create_health_router
from sadify_api.routes.sad import create_sad_router
from sadify_api.routes.sources import create_sources_router
from sadify_api.services.auth import FirebaseAdminTokenVerifier, TokenVerifier
from sadify_api.services.analysis_state import RequirementAnalysisRepository
from sadify_api.services.gemini_structured import (
    GeminiSadPreviewModel,
    GeminiRequirementAnalysisModel,
    RequirementAnalysisModel,
    SadPreviewModel,
)
from sadify_api.services.guest_drafts import GuestDraftRepository
from sadify_api.services.source_uploads import SourceRepository
from sadify_api.services.drive_repo import DriveRepoRepository
from sadify_api.services.drive_client import DriveClient
from sadify_api.services.sad_preview import SadPreviewRepository
from sadify_api.services.sad_save import SadSaveRepository
from sadify_api.services.secret_store import SecretStore
from sadify_api.services.wiki_state import (
    WikiStateRepository,
    get_wiki_state_repository,
)


def create_app(
    config: ApiConfig | None = None,
    token_verifier: TokenVerifier | None = None,
    draft_repository: GuestDraftRepository | None = None,
    analysis_model: RequirementAnalysisModel | None = None,
    analysis_repository: RequirementAnalysisRepository | None = None,
    source_repository: SourceRepository | None = None,
    drive_repo_repository: DriveRepoRepository | None = None,
    sad_preview_model: SadPreviewModel | None = None,
    sad_preview_repository: SadPreviewRepository | None = None,
    sad_save_repository: SadSaveRepository | None = None,
    drive_client: DriveClient | None = None,
    secret_store: SecretStore | None = None,
    wiki_state_repository: WikiStateRepository | None = None,
) -> FastAPI:
    config = config or load_api_config()
    token_verifier = token_verifier or FirebaseAdminTokenVerifier(config)
    draft_repository = draft_repository or GuestDraftRepository()
    analysis_model = analysis_model or GeminiRequirementAnalysisModel(config)
    analysis_repository = analysis_repository or RequirementAnalysisRepository()
    source_repository = source_repository or SourceRepository()
    drive_repo_repository = drive_repo_repository or DriveRepoRepository()
    sad_preview_model = sad_preview_model or GeminiSadPreviewModel(config)
    sad_preview_repository = sad_preview_repository or SadPreviewRepository()
    sad_save_repository = sad_save_repository or SadSaveRepository()
    wiki_state_repository = wiki_state_repository or get_wiki_state_repository()
    app = FastAPI(title="SADify API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["authorization", "content-type"],
    )
    app.include_router(create_health_router(config))
    app.include_router(create_auth_router(token_verifier))
    app.include_router(create_drafts_router(draft_repository, token_verifier))
    app.include_router(create_analysis_router(analysis_model, analysis_repository))
    app.include_router(create_sources_router(source_repository))
    app.include_router(
        create_drive_router(
            drive_repo_repository,
            token_verifier,
            config,
            drive_client,
            secret_store,
        )
    )
    app.include_router(
        create_sad_router(
            sad_preview_model,
            sad_preview_repository,
            token_verifier,
            drive_repo_repository,
            source_repository,
            sad_save_repository,
            config,
            drive_client,
            secret_store,
            wiki_state_repository,
        )
    )
    if config.diagnostics_enabled:
        app.include_router(create_diagnostics_router(config))

    return app


app = create_app()
