import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from pydantic import ValidationError

from sadify_api.config import ApiConfig
from sadify_api.schemas import (
    DriveRepoRecord,
    ProjectSummary,
    SadPreviewRecord,
    SadPreviewRequest,
    SadPreviewResponse,
    SadSaveRecord,
    SadSaveRequest,
    SourceRecord,
    WikiBackupInfo,
    WikiFilePreview,
    WikiFileResult,
    WikiPreviewResponse,
    WikiUpdateRequest,
    WikiUpdateResponse,
)
from sadify_api.services.auth import VerifiedFirebaseUser
from sadify_api.services.drive_client import (
    DriveClient,
    DriveFolderCreateError,
    DriveTextFileError,
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
from sadify_api.services.wiki_backup import WikiBackupError, snapshot_existing_wiki_files
from sadify_api.services.wiki_compose import MANAGED_WIKI_FILE_NAMES, compose_wiki_files
from sadify_api.services.wiki_state import WikiState, WikiStateRepository

logger = logging.getLogger("sadify_api.routes.sad")

WIKI_FOLDER_NAME = "Wiki"
WIKI_MIME_TYPE = "text/markdown"


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


class WikiFlowError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        changed_files: list[str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.changed_files = changed_files


@dataclass(frozen=True)
class WikiFlowContext:
    repo: DriveRepoRecord
    project: ProjectSummary
    latest_save: SadSaveRecord
    all_saves_for_repo: list[SadSaveRecord]
    sources: list[SourceRecord]
    drive_client: DriveClient
    access_token: str


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


def run_wiki_preview(
    *,
    context: WikiFlowContext,
    repository: SadPreviewRepository,
    wiki_state_repository: WikiStateRepository,
) -> WikiPreviewResponse:
    try:
        wiki_folder = _wiki_folder(context)
        remote_files = _read_remote_wiki_files(context, wiki_folder.folder_id)
    except (DriveFolderCreateError, DriveTextFileError) as exc:
        raise WikiFlowError(
            502,
            "WIKI_REMOTE_READ_FAILED",
            "Could not read the existing wiki files.",
        ) from exc

    latest_preview = _latest_preview_or_error(
        repository,
        context.latest_save.preview_id,
    )
    drafts = _compose_wiki(context, latest_preview.preview)
    files: list[WikiFilePreview] = []
    changed_files: list[str] = []
    for draft in drafts:
        remote = remote_files.get(draft.name)
        state = wiki_state_repository.get_file_state(
            context.repo.grant_id,
            context.project.project_id,
            draft.name,
        )
        last_known_hash = state.hash if state is not None else None
        requires_confirmation = remote is not None and remote["hash"] != last_known_hash
        if requires_confirmation:
            changed_files.append(draft.name)
        files.append(
            WikiFilePreview(
                relative_path=_wiki_relative_path(draft.name),
                name=draft.name,
                category=draft.category,
                proposed_markdown=draft.markdown,
                remote_hash=remote["hash"] if remote is not None else None,
                last_known_hash=last_known_hash,
                remote_exists=remote is not None,
                requires_confirmation=requires_confirmation,
                remote_markdown=remote["markdown"] if requires_confirmation else None,
            )
        )
    return WikiPreviewResponse(
        files=files,
        requires_confirmation=bool(changed_files),
        changed_files=changed_files,
        first_time_write=not remote_files,
    )


def run_wiki_update(
    *,
    context: WikiFlowContext,
    request: WikiUpdateRequest,
    repository: SadPreviewRepository,
    wiki_state_repository: WikiStateRepository,
) -> WikiUpdateResponse:
    try:
        wiki_folder = _wiki_folder(context)
        remote_files = _read_remote_wiki_files(context, wiki_folder.folder_id)
    except (DriveFolderCreateError, DriveTextFileError) as exc:
        raise WikiFlowError(
            502,
            "WIKI_REMOTE_READ_FAILED",
            "Could not read the existing wiki files.",
        ) from exc

    changed_files = [
        name
        for name, remote in remote_files.items()
        if remote["hash"] != request.expected_remote_hashes.get(name)
    ]
    if changed_files and not request.force_overwrite:
        raise WikiFlowError(
            409,
            "WIKI_CONFLICT",
            "The wiki was changed in Drive since SADify last wrote it. Confirm overwrite.",
            changed_files=changed_files,
        )

    latest_preview = _latest_preview_or_error(
        repository,
        context.latest_save.preview_id,
    )
    drafts = _compose_wiki(context, latest_preview.preview)
    existing_files = [remote["file"] for remote in remote_files.values()]
    try:
        backup = snapshot_existing_wiki_files(
            drive_client=context.drive_client,
            access_token=context.access_token,
            repo_folder_id=context.project.drive_folder_id,
            existing_files=existing_files,
        )
    except WikiBackupError as exc:
        raise WikiFlowError(
            502,
            "WIKI_BACKUP_FAILED",
            "Could not snapshot existing wiki files before overwrite.",
        ) from exc

    updated_at = datetime.now(UTC)
    files: list[WikiFileResult] = []
    try:
        for draft in drafts:
            remote = remote_files.get(draft.name)
            wiki_hash = _wiki_hash(draft.markdown)
            upload = context.drive_client.upload_or_replace_text_file(
                access_token=context.access_token,
                folder_id=wiki_folder.folder_id,
                name=draft.name,
                mime_type=WIKI_MIME_TYPE,
                content=draft.markdown,
                existing_file_id=remote["file"].file_id if remote else None,
            )
            wiki_state_repository.record_file_write(
                context.repo.grant_id,
                context.project.project_id,
                WikiState(
                    file_name=draft.name,
                    file_id=upload.file_id,
                    hash=wiki_hash,
                    updated_at=updated_at,
                ),
            )
            files.append(
                WikiFileResult(
                    relative_path=_wiki_relative_path(draft.name),
                    name=draft.name,
                    category=draft.category,
                    file_id=upload.file_id,
                    web_view_link=upload.web_view_link,
                    hash=wiki_hash,
                    created_new_file=remote is None,
                )
            )
    except (DriveFolderCreateError, DriveTextFileError) as exc:
        raise WikiFlowError(
            502,
            "WIKI_WRITE_FAILED",
            "Google Drive rejected the wiki update.",
        ) from exc

    return WikiUpdateResponse(
        files=files,
        backup=WikiBackupInfo(
            created=backup.created,
            path=backup.path,
            file_count=backup.file_count,
        ),
        updated_at=updated_at,
    )


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


def _latest_preview_or_error(
    repository: SadPreviewRepository,
    preview_id: str,
) -> SadPreviewRecord:
    preview_record = repository.get_preview(preview_id)
    if preview_record is None:
        raise WikiFlowError(
            409,
            "WIKI_SAVE_REQUIRED",
            "The SAD preview must be regenerated before updating the wiki.",
        )
    return preview_record


def _wiki_folder(context: WikiFlowContext):
    return context.drive_client.find_or_create_folder(
        access_token=context.access_token,
        folder_name=WIKI_FOLDER_NAME,
        parent_folder_id=context.project.drive_folder_id,
    )


def _read_remote_wiki_files(
    context: WikiFlowContext,
    wiki_folder_id: str,
) -> dict[str, dict[str, object]]:
    remote_files: dict[str, dict[str, object]] = {}
    for name in MANAGED_WIKI_FILE_NAMES:
        remote_file = context.drive_client.find_file_in_folder(
            access_token=context.access_token,
            folder_id=wiki_folder_id,
            name=name,
            mime_type=WIKI_MIME_TYPE,
        )
        if remote_file is None:
            continue
        remote_markdown = context.drive_client.download_text_file(
            access_token=context.access_token,
            file_id=remote_file.file_id,
        )
        remote_files[name] = {
            "file": remote_file,
            "markdown": remote_markdown,
            "hash": _wiki_hash(remote_markdown),
        }
    return remote_files


def _compose_wiki(
    context: WikiFlowContext,
    latest_preview: SadPreviewResponse,
):
    return compose_wiki_files(
        repo=context.repo,
        latest_save=context.latest_save,
        latest_preview=latest_preview,
        all_saves_for_repo=context.all_saves_for_repo,
        sources=context.sources,
        requirement_text=context.latest_save.manifest.requirement_text,
    )


def _wiki_relative_path(name: str) -> str:
    return f"{WIKI_FOLDER_NAME}/{name}"


def _wiki_hash(value: str) -> str:
    return f"sha256:{sha256(value.encode('utf-8')).hexdigest()}"
