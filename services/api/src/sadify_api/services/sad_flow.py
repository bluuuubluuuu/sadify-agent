import logging

from pydantic import ValidationError

from sadify_api.config import ApiConfig
from sadify_api.schemas import SadPreviewRecord, SadPreviewRequest, SadSaveRecord, SadSaveRequest
from sadify_api.services.auth import VerifiedFirebaseUser
from sadify_api.services.drive_client import (
    DriveClient,
    DriveFolderCreateError,
    DriveTokenInvalidError,
)
from sadify_api.services.drive_repo import DriveRepoRepository
from sadify_api.services.gemini_structured import (
    SadPreviewModel,
    parse_sad_preview,
)
from sadify_api.services.projects import ProjectRepository
from sadify_api.services.sad_preview import (
    SadPreviewRepository,
    build_safe_sad_fallback_preview,
    build_sad_preview_context,
    missing_blocking_basics,
    with_requested_source_references,
)
from sadify_api.services.sad_save import (
    SadSaveDriveUploadError,
    SadSaveRepository,
    SadSaveTokenInvalidError,
    SadSaveTokenMissingError,
)
from sadify_api.services.sad_synthesis import clean_business_request
from sadify_api.services.secret_store import SecretStore, get_secret_store
from sadify_api.services.source_uploads import SourceRepository

logger = logging.getLogger("sadify_api.routes.sad")


class SadPreviewBlockedError(Exception):
    def __init__(self, missing_basics: list[str]) -> None:
        self.missing_basics = missing_basics


class SadPreviewModelError(Exception):
    """Raised when Gemini fails non-validation during SAD preview generation."""


class SadSaveFlowError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


def run_sad_preview(
    *,
    request: SadPreviewRequest,
    model: SadPreviewModel,
    repository: SadPreviewRepository,
) -> SadPreviewRecord:
    clean_request = clean_business_request(request.requirement_text)
    missing_basics = missing_blocking_basics(
        request.analysis,
        requirement_text=clean_request,
        source_context=request.source_context,
    )
    if missing_basics:
        raise SadPreviewBlockedError(missing_basics)

    context = build_sad_preview_context(
        requirement_text=clean_request,
        analysis_id=request.analysis_id,
        analysis=request.analysis,
        source_context=request.source_context,
        source_references=request.source_references,
    )
    for repair in (False, True):
        raw_json = ""
        try:
            raw_json = _call_sad_preview_model(
                model,
                context,
                repair=repair,
                selected_model=request.model,
            )
            preview = with_requested_source_references(
                parse_sad_preview(raw_json),
                request.source_references,
            )
        except ValidationError as exc:
            logger.warning(
                "sadify_preview validation_failed repair=%s err=%s raw_len=%d",
                repair,
                f"{type(exc).__name__}:{str(exc)[:120]}",
                len(raw_json),
            )
            continue
        except Exception as exc:
            logger.exception(
                "sadify_preview call_failed repair=%s raw_len=%d",
                repair,
                len(raw_json),
            )
            raise SadPreviewModelError("Gemini SAD preview failed.") from exc

        return repository.save_preview(
            requirement_text=clean_request,
            analysis_id=request.analysis_id,
            preview=preview,
        )

    fallback_preview = build_safe_sad_fallback_preview(
        requirement_text=clean_request,
        analysis=request.analysis,
        source_references=request.source_references,
    )
    return repository.save_preview(
        requirement_text=clean_request,
        analysis_id=request.analysis_id,
        preview=fallback_preview,
    )


def run_sad_save(
    *,
    user: VerifiedFirebaseUser,
    request: SadSaveRequest,
    repository: SadPreviewRepository,
    drive_repo_repository: DriveRepoRepository,
    source_repository: SourceRepository,
    sad_save_repository: SadSaveRepository,
    config: ApiConfig,
    drive_client: DriveClient | None,
    secret_store: SecretStore | None,
    project_repository: ProjectRepository | None,
) -> SadSaveRecord:
    preview_id = (request.preview_id or "").strip()
    if not preview_id:
        raise SadSaveFlowError(
            400,
            "SAD_SAVE_PREVIEW_REQUIRED",
            "Generate a SAD preview before saving.",
        )

    repo = drive_repo_repository.get_active_repo(user.uid)
    if repo is None:
        latest_repo = drive_repo_repository.get_latest_repo(user.uid)
        if latest_repo and (
            latest_repo.status == "disconnected" or latest_repo.saves_blocked
        ):
            raise SadSaveFlowError(
                409,
                "SAD_SAVE_REPO_DISCONNECTED",
                "Reconnect Google Drive before saving.",
            )
        raise SadSaveFlowError(
            409,
            "SAD_SAVE_REPO_REQUIRED",
            "Connect a Google Drive project repo before saving.",
        )
    if repo.status == "disconnected" or repo.saves_blocked:
        raise SadSaveFlowError(
            409,
            "SAD_SAVE_REPO_DISCONNECTED",
            "Reconnect Google Drive before saving.",
        )
    if not repo.active_project_id:
        raise SadSaveFlowError(
            409,
            "PROJECT_REQUIRED",
            "Create or select a project before saving.",
        )
    project = None
    if project_repository is not None:
        project = project_repository.get_project(
            repo.grant_id,
            repo.active_project_id,
        )
        if project is None:
            raise SadSaveFlowError(
                409,
                "PROJECT_REQUIRED",
                "Create or select a project before saving.",
            )
    if project is None:
        project = next(
            (
                candidate
                for candidate in repo.available_projects
                if candidate.project_id == repo.active_project_id
            ),
            None,
        )
    if project is None:
        raise SadSaveFlowError(
            409,
            "PROJECT_REQUIRED",
            "Create or select a project before saving.",
        )

    preview_record = repository.get_preview(preview_id)
    if preview_record is None:
        raise SadSaveFlowError(
            404,
            "SAD_SAVE_PREVIEW_NOT_FOUND",
            "This SAD preview is no longer available. Generate it again before saving.",
        )

    sources = []
    seen_source_ids = set()
    for source_reference in preview_record.preview.source_references:
        source_id = source_reference.strip()
        if not source_id.startswith("SRC-") or source_id in seen_source_ids:
            continue
        source = source_repository.get_source(source_id)
        if source is None:
            continue
        sources.append(source)
        seen_source_ids.add(source_id)

    try:
        live_drive_client = drive_client
        live_secret_store = secret_store
        target_folder_id = None
        if config.drive_mode == "live":
            live_drive_client, live_secret_store = _resolve_live_sad_save_services(
                config=config,
                drive_client=drive_client,
                secret_store=secret_store,
            )
            refresh_token = live_secret_store.get_user_refresh_token(user.uid)
            if not refresh_token:
                raise SadSaveTokenMissingError("Drive refresh token is missing.")
            try:
                access_token = live_drive_client.refresh_access_token(refresh_token)
            except DriveTokenInvalidError as exc:
                raise SadSaveTokenInvalidError(
                    "Drive refresh token is invalid or expired."
                ) from exc
            try:
                sad_folder = live_drive_client.find_or_create_folder(
                    access_token=access_token,
                    folder_name="SAD",
                    parent_folder_id=project.drive_folder_id,
                )
            except DriveFolderCreateError as exc:
                raise SadSaveDriveUploadError(
                    "Google Drive rejected the upload."
                ) from exc
            target_folder_id = sad_folder.folder_id
        return sad_save_repository.save_preview(
            owner_uid=user.uid,
            owner_email=user.email,
            repo=repo,
            project_id=repo.active_project_id,
            preview_record=preview_record,
            sources=sources,
            mode=config.drive_mode,
            drive_client=live_drive_client,
            secret_store=live_secret_store,
            target_folder_id=target_folder_id,
        )
    except SadSaveTokenMissingError as exc:
        raise SadSaveFlowError(
            409,
            "SAD_SAVE_TOKEN_MISSING",
            "Reconnect Google Drive before saving.",
        ) from exc
    except SadSaveTokenInvalidError as exc:
        raise SadSaveFlowError(
            401,
            "SAD_SAVE_TOKEN_INVALID",
            "Reconnect Google Drive to renew permission.",
        ) from exc
    except SadSaveDriveUploadError as exc:
        raise SadSaveFlowError(
            502,
            "SAD_SAVE_DRIVE_UPLOAD_FAILED",
            "Google Drive rejected the upload.",
        ) from exc


def _call_sad_preview_model(
    model: SadPreviewModel,
    context: str,
    *,
    repair: bool,
    selected_model: str | None,
) -> str:
    if selected_model:
        return model.generate_preview(
            context,
            repair=repair,
            model=selected_model,
        )

    return model.generate_preview(context, repair=repair)


def _resolve_live_sad_save_services(
    *,
    config: ApiConfig,
    drive_client: DriveClient | None,
    secret_store: SecretStore | None,
) -> tuple[DriveClient, SecretStore]:
    if drive_client is not None and secret_store is not None:
        return drive_client, secret_store
    if not config.drive_live_enabled:
        raise SadSaveFlowError(
            503,
            "SAD_SAVE_LIVE_MODE_DISABLED",
            "Live Drive save is disabled for this process.",
        )

    resolved_secret_store = secret_store or get_secret_store(
        project_id=config.google_cloud_project,
        oauth_client_secret_name=config.google_oauth_client_secret_name,
    )
    resolved_drive_client = drive_client or DriveClient(
        client_id=config.google_oauth_client_id,
        client_secret=resolved_secret_store.get_oauth_client_secret(),
    )
    return resolved_drive_client, resolved_secret_store
