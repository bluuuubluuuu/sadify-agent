from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sadify_api.config import ApiConfig, load_api_config
from sadify_api.routes.agent import create_agent_router
from sadify_api.routes.analysis import create_analysis_router
from sadify_api.routes.auth import create_auth_router
from sadify_api.routes.diagnostics import create_diagnostics_router
from sadify_api.routes.drive import create_drive_router
from sadify_api.routes.drafts import create_drafts_router
from sadify_api.routes.health import create_health_router
from sadify_api.routes.models import create_models_router
from sadify_api.routes.projects import create_projects_router
from sadify_api.routes.sad import create_sad_router
from sadify_api.routes.sources import create_sources_router
from sadify_api.services.auth import FirebaseAdminTokenVerifier, TokenVerifier
from sadify_api.services.analysis_state import RequirementAnalysisRepository
from sadify_api.services.gemini_structured import (
    DevTaskExtractionModel,
    GeminiDevTaskExtractionModel,
    GeminiSadReviewModel,
    GeminiSadPreviewModel,
    GeminiRequirementAnalysisModel,
    RequirementAnalysisModel,
    SadPreviewModel,
    SadReviewModel,
)
from sadify_api.services.guest_drafts import GuestDraftRepository
from sadify_api.services.source_uploads import SourceRepository
from sadify_api.services.drive_repo import (
    DriveRepoRepository,
    FirestoreDriveRepoRepository,
)
from sadify_api.services.drive_client import DriveClient
from sadify_api.services.firestore_client import get_firestore_client
from sadify_api.services.sad_preview import SadPreviewRepository
from sadify_api.services.sad_save import FirestoreSadSaveRepository, SadSaveRepository
from sadify_api.services.secret_store import SecretStore
from sadify_api.services.session_state import (
    FirestoreSessionSnapshotRepository,
    SessionSnapshotRepository,
)
from sadify_api.services.projects import FirestoreProjectRepository, ProjectRepository
from sadify_api.services.wiki_state import (
    FirestoreWikiStateRepository,
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
    sad_review_model: SadReviewModel | None = None,
    dev_task_model: DevTaskExtractionModel | None = None,
    sad_preview_repository: SadPreviewRepository | None = None,
    sad_save_repository: SadSaveRepository | None = None,
    drive_client: DriveClient | None = None,
    secret_store: SecretStore | None = None,
    wiki_state_repository: WikiStateRepository | None = None,
    project_repository: ProjectRepository | None = None,
    session_snapshot_repository: SessionSnapshotRepository | None = None,
) -> FastAPI:
    config = config or load_api_config()
    firestore_client = None
    if config.persistence_mode == "firestore":
        firestore_client = get_firestore_client(config.google_cloud_project)
    token_verifier = token_verifier or FirebaseAdminTokenVerifier(config)
    draft_repository = draft_repository or GuestDraftRepository()
    analysis_model = analysis_model or GeminiRequirementAnalysisModel(config)
    analysis_repository = analysis_repository or RequirementAnalysisRepository()
    source_repository = source_repository or SourceRepository()
    drive_repo_repository = drive_repo_repository or (
        FirestoreDriveRepoRepository(firestore_client)
        if firestore_client is not None
        else DriveRepoRepository()
    )
    sad_preview_model = sad_preview_model or GeminiSadPreviewModel(config)
    sad_review_model = sad_review_model or GeminiSadReviewModel(config)
    dev_task_model = dev_task_model or GeminiDevTaskExtractionModel(config)
    sad_preview_repository = sad_preview_repository or SadPreviewRepository()
    sad_save_repository = sad_save_repository or (
        FirestoreSadSaveRepository(firestore_client)
        if firestore_client is not None
        else SadSaveRepository()
    )
    wiki_state_repository = wiki_state_repository or (
        FirestoreWikiStateRepository(firestore_client)
        if firestore_client is not None
        else get_wiki_state_repository()
    )
    project_repository = project_repository or (
        FirestoreProjectRepository(firestore_client)
        if firestore_client is not None
        else ProjectRepository()
    )
    session_snapshot_repository = session_snapshot_repository or (
        FirestoreSessionSnapshotRepository(firestore_client)
        if firestore_client is not None
        else SessionSnapshotRepository()
    )
    app = FastAPI(title="SADify API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["authorization", "content-type"],
    )
    app.include_router(create_health_router(config))
    app.include_router(create_models_router(config))
    app.include_router(
        create_agent_router(
            config=config,
            analysis_model=analysis_model,
            analysis_repository=analysis_repository,
            sad_preview_model=sad_preview_model,
            sad_preview_repository=sad_preview_repository,
            token_verifier=token_verifier,
            drive_repo_repository=drive_repo_repository,
            source_repository=source_repository,
            sad_save_repository=sad_save_repository,
            drive_client=drive_client,
            secret_store=secret_store,
            wiki_state_repository=wiki_state_repository,
            project_repository=project_repository,
            sad_review_model=sad_review_model,
            dev_task_model=dev_task_model,
        )
    )
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
            project_repository,
        )
    )
    app.include_router(
        create_projects_router(
            drive_repo_repository,
            project_repository,
            sad_save_repository,
            token_verifier,
            config,
            drive_client,
            secret_store,
            session_snapshot_repository,
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
            project_repository,
        )
    )
    if config.diagnostics_enabled:
        app.include_router(create_diagnostics_router(config))

    return app


app = create_app()
