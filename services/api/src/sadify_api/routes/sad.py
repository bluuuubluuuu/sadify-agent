import logging

from fastapi import APIRouter, Header, HTTPException

logger = logging.getLogger(__name__)

from sadify_api.config import ApiConfig, load_api_config
from sadify_api.routes.auth import verify_authorization_header
from sadify_api.schemas import (
    SadPreviewApiResponse,
    SadPreviewRequest,
    SadSaveApiResponse,
    SadSaveRequest,
    DriveRepoRecord,
    ProjectSummary,
    SadSaveRecord,
    SourceRecord,
    WikiPreviewRequest,
    WikiPreviewResponse,
    WikiUpdateRequest,
    WikiUpdateResponse,
)
from sadify_api.services.auth import TokenVerifier
from sadify_api.services.drive_client import (
    DriveClient,
    DriveTokenInvalidError,
)
from sadify_api.services.drive_repo import DriveRepoRepository
from sadify_api.services.gemini_structured import SadPreviewModel
from sadify_api.services.sad_flow import (
    SadPreviewBlockedError,
    SadPreviewModelError,
    SadSaveFlowError,
    WikiFlowContext,
    WikiFlowError,
    run_sad_preview,
    run_sad_save,
    run_wiki_preview,
    run_wiki_update,
)
from sadify_api.services.sad_preview import SadPreviewRepository
from sadify_api.services.sad_save import SadSaveRepository
from sadify_api.services.projects import ProjectRepository
from sadify_api.services.wiki_state import WikiStateRepository
from sadify_api.services.secret_store import SecretStore
from sadify_api.services.live_drive import (
    LiveDriveServicesDisabledError,
    resolve_live_drive_services,
)
from sadify_api.services.source_uploads import SourceRepository


def create_sad_router(
    model: SadPreviewModel,
    repository: SadPreviewRepository,
    token_verifier: TokenVerifier,
    drive_repo_repository: DriveRepoRepository,
    source_repository: SourceRepository,
    sad_save_repository: SadSaveRepository,
    config: ApiConfig | None = None,
    drive_client: DriveClient | None = None,
    secret_store: SecretStore | None = None,
    wiki_state_repository: WikiStateRepository | None = None,
    project_repository: ProjectRepository | None = None,
) -> APIRouter:
    config = config or load_api_config()
    router = APIRouter(prefix="/sad", tags=["sad"])

    @router.post("/preview", response_model=SadPreviewApiResponse)
    def generate_preview(request: SadPreviewRequest) -> SadPreviewApiResponse:
        try:
            record = run_sad_preview(
                request=request,
                model=model,
                repository=repository,
            )
        except SadPreviewBlockedError as exc:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Answer the blocking basics before generating a SAD preview.",
                    "missing_basics": exc.missing_basics,
                },
            ) from exc
        except SadPreviewModelError as exc:
            raise HTTPException(
                status_code=502,
                detail="Gemini SAD preview failed.",
            ) from exc
        return SadPreviewApiResponse(
            preview_id=record.preview_id,
            saved=True,
            preview=record.preview,
        )

    @router.post("/save", response_model=SadSaveApiResponse)
    def save_preview(
        request: SadSaveRequest,
        authorization: str | None = Header(default=None),
    ) -> SadSaveApiResponse:
        try:
            user = verify_authorization_header(authorization, token_verifier)
        except HTTPException as exc:
            if exc.status_code == 401:
                raise _sad_save_error(
                    401,
                    "SAD_SAVE_AUTH_REQUIRED",
                    "Sign in before saving the SAD preview.",
                ) from exc
            raise

        try:
            record = run_sad_save(
                user=user,
                request=request,
                repository=repository,
                drive_repo_repository=drive_repo_repository,
                source_repository=source_repository,
                sad_save_repository=sad_save_repository,
                config=config,
                drive_client=drive_client,
                secret_store=secret_store,
                project_repository=project_repository,
            )
        except SadSaveFlowError as exc:
            raise _sad_save_error(
                exc.status_code,
                exc.code,
                exc.message,
            ) from exc
        return SadSaveApiResponse(
            saved=True,
            record=record,
            message="SAD preview saved to the local project repo record.",
        )

    @router.post("/wiki/preview", response_model=WikiPreviewResponse)
    def preview_wiki_update(
        _request: WikiPreviewRequest,
        authorization: str | None = Header(default=None),
    ) -> WikiPreviewResponse:
        context = _build_wiki_context(
            authorization=authorization,
            token_verifier=token_verifier,
            drive_repo_repository=drive_repo_repository,
            sad_save_repository=sad_save_repository,
            source_repository=source_repository,
            project_repository=project_repository,
            config=config,
            drive_client=drive_client,
            secret_store=secret_store,
        )
        try:
            return run_wiki_preview(
                context=context,
                repository=repository,
                wiki_state_repository=wiki_state_repository,
            )
        except WikiFlowError as exc:
            raise _wiki_error(
                exc.status_code,
                exc.code,
                exc.message,
                changed_files=exc.changed_files,
            ) from exc

    @router.post("/wiki/update", response_model=WikiUpdateResponse)
    def update_wiki(
        request: WikiUpdateRequest,
        authorization: str | None = Header(default=None),
    ) -> WikiUpdateResponse:
        context = _build_wiki_context(
            authorization=authorization,
            token_verifier=token_verifier,
            drive_repo_repository=drive_repo_repository,
            sad_save_repository=sad_save_repository,
            source_repository=source_repository,
            project_repository=project_repository,
            config=config,
            drive_client=drive_client,
            secret_store=secret_store,
        )
        try:
            return run_wiki_update(
                context=context,
                request=request,
                repository=repository,
                wiki_state_repository=wiki_state_repository,
            )
        except WikiFlowError as exc:
            raise _wiki_error(
                exc.status_code,
                exc.code,
                exc.message,
                changed_files=exc.changed_files,
            ) from exc

    return router


def _resolve_live_services(
    *,
    config: ApiConfig,
    drive_client: DriveClient | None,
    secret_store: SecretStore | None,
) -> tuple[DriveClient, SecretStore]:
    try:
        return resolve_live_drive_services(config, drive_client, secret_store)
    except LiveDriveServicesDisabledError as exc:
        raise _sad_save_error(
            503,
            "SAD_SAVE_LIVE_MODE_DISABLED",
            "Live Drive save is disabled for this process.",
        ) from exc


def _sad_save_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def _build_wiki_context(
    *,
    authorization: str | None,
    token_verifier: TokenVerifier,
    drive_repo_repository: DriveRepoRepository,
    sad_save_repository: SadSaveRepository,
    source_repository: SourceRepository,
    project_repository: ProjectRepository | None,
    config: ApiConfig,
    drive_client: DriveClient | None,
    secret_store: SecretStore | None,
) -> WikiFlowContext:
    try:
        user = verify_authorization_header(authorization, token_verifier)
    except HTTPException as exc:
        if exc.status_code == 401:
            raise _wiki_error(
                401,
                "WIKI_AUTH_REQUIRED",
                "Sign in before updating the wiki.",
            ) from exc
        raise

    repo = drive_repo_repository.get_active_repo(user.uid)
    if repo is None:
        latest_repo = drive_repo_repository.get_latest_repo(user.uid)
        if latest_repo and (
            latest_repo.status == "disconnected" or latest_repo.saves_blocked
        ):
            raise _wiki_error(
                409,
                "WIKI_REPO_DISCONNECTED",
                "Reconnect Google Drive before updating the wiki.",
            )
        raise _wiki_error(
            409,
            "WIKI_REPO_REQUIRED",
            "Connect a Google Drive project repo before updating the wiki.",
        )
    if repo.status == "disconnected" or repo.saves_blocked:
        raise _wiki_error(
            409,
            "WIKI_REPO_DISCONNECTED",
            "Reconnect Google Drive before updating the wiki.",
        )
    project = _active_project_or_error(
        repo=repo,
        project_repository=project_repository,
    )
    if config.drive_mode != "live" or not config.drive_live_enabled:
        raise _wiki_error(
            503,
            "WIKI_LIVE_MODE_DISABLED",
            "Live wiki updates are disabled for this process.",
        )

    saves = _saves_for_project(
        sad_save_repository,
        repo.grant_id,
        project.project_id,
    )
    if not saves:
        raise _wiki_error(
            409,
            "WIKI_SAVE_REQUIRED",
            "Save a SAD preview to this repo before generating a wiki.",
        )
    latest_save = saves[-1]
    sources = _sources_for_save(source_repository, latest_save)
    live_drive_client, live_secret_store = _resolve_live_services(
        config=config,
        drive_client=drive_client,
        secret_store=secret_store,
    )
    refresh_token = live_secret_store.get_user_refresh_token(user.uid)
    if not refresh_token:
        raise _wiki_error(
            409,
            "WIKI_REPO_DISCONNECTED",
            "Reconnect Google Drive before updating the wiki.",
        )
    try:
        access_token = live_drive_client.refresh_access_token(refresh_token)
    except DriveTokenInvalidError as exc:
        raise _wiki_error(
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
        drive_client=live_drive_client,
        access_token=access_token,
    )


def _active_project_or_error(
    *,
    repo: DriveRepoRecord,
    project_repository: ProjectRepository | None,
) -> ProjectSummary:
    if not repo.active_project_id:
        raise _wiki_error(
            409,
            "WIKI_PROJECT_REQUIRED",
            "Create or select a project before updating the wiki.",
        )
    if project_repository is not None:
        project = project_repository.get_project(repo.grant_id, repo.active_project_id)
        if project is not None:
            return project
    project = next(
        (
            candidate
            for candidate in repo.available_projects
            if candidate.project_id == repo.active_project_id
        ),
        None,
    )
    if project is None:
        raise _wiki_error(
            409,
            "WIKI_PROJECT_REQUIRED",
            "Create or select a project before updating the wiki.",
        )
    return project


def _saves_for_project(
    sad_save_repository: SadSaveRepository,
    repo_grant_id: str,
    project_id: str,
) -> list[SadSaveRecord]:
    return sorted(
        sad_save_repository.list_for_project(
            grant_id=repo_grant_id,
            project_id=project_id,
        ),
        key=lambda record: record.created_at,
    )


def _sources_for_save(
    source_repository: SourceRepository,
    save: SadSaveRecord,
) -> list[SourceRecord]:
    sources = []
    seen = set()
    for source_id in save.manifest.source_ids:
        if source_id in seen:
            continue
        source = source_repository.get_source(source_id)
        if source is None:
            continue
        sources.append(source)
        seen.add(source_id)
    return sources


def _wiki_error(
    status_code: int,
    code: str,
    message: str,
    *,
    changed_files: list[str] | None = None,
) -> HTTPException:
    detail = {"code": code, "message": message}
    if changed_files is not None:
        detail["changed_files"] = changed_files
    return HTTPException(
        status_code=status_code,
        detail=detail,
    )
