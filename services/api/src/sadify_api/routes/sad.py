import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from fastapi import APIRouter, Header, HTTPException
from pydantic import ValidationError

logger = logging.getLogger(__name__)

from sadify_api.config import ApiConfig, load_api_config
from sadify_api.routes.auth import verify_authorization_header
from sadify_api.schemas import (
    SadPreviewApiResponse,
    SadPreviewRequest,
    SadSaveApiResponse,
    SadSaveRequest,
    DriveRepoRecord,
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
    DriveTextFileError,
    DriveTokenInvalidError,
)
from sadify_api.services.drive_repo import DriveRepoRepository
from sadify_api.services.gemini_structured import (
    SadPreviewModel,
    parse_sad_preview,
)
from sadify_api.services.sad_preview import (
    SadPreviewRepository,
    build_safe_sad_fallback_preview,
    build_sad_preview_context,
    missing_blocking_basics,
    with_requested_source_references,
)
from sadify_api.services.sad_synthesis import clean_business_request
from sadify_api.services.sad_save import (
    SadSaveDriveUploadError,
    SadSaveRepository,
    SadSaveTokenInvalidError,
    SadSaveTokenMissingError,
)
from sadify_api.services.wiki_compose import compose_wiki_markdown
from sadify_api.services.wiki_state import WikiStateRepository
from sadify_api.services.secret_store import SecretStore, get_secret_store
from sadify_api.services.source_uploads import SourceRepository

WIKI_FILE_NAME = "Wiki.md"
WIKI_MIME_TYPE = "text/markdown"
WIKI_PATH = "Wiki/Wiki.md"


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
) -> APIRouter:
    config = config or load_api_config()
    router = APIRouter(prefix="/sad", tags=["sad"])

    @router.post("/preview", response_model=SadPreviewApiResponse)
    def generate_preview(request: SadPreviewRequest) -> SadPreviewApiResponse:
        clean_request = clean_business_request(request.requirement_text)
        missing_basics = missing_blocking_basics(
            request.analysis,
            requirement_text=clean_request,
            source_context=request.source_context,
        )
        if missing_basics:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Answer the blocking basics before generating a SAD preview.",
                    "missing_basics": missing_basics,
                },
            )

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
                raw_json = model.generate_preview(context, repair=repair)
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
                raise HTTPException(
                    status_code=502,
                    detail="Gemini SAD preview failed.",
                ) from exc

            record = repository.save_preview(
                requirement_text=clean_request,
                analysis_id=request.analysis_id,
                preview=preview,
            )
            return SadPreviewApiResponse(
                preview_id=record.preview_id,
                saved=True,
                preview=record.preview,
            )

        fallback_preview = build_safe_sad_fallback_preview(
            requirement_text=clean_request,
            analysis=request.analysis,
            source_references=request.source_references,
        )
        record = repository.save_preview(
            requirement_text=clean_request,
            analysis_id=request.analysis_id,
            preview=fallback_preview,
        )
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

        preview_id = (request.preview_id or "").strip()
        if not preview_id:
            raise _sad_save_error(
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
                raise _sad_save_error(
                    409,
                    "SAD_SAVE_REPO_DISCONNECTED",
                    "Reconnect Google Drive before saving.",
                )
            raise _sad_save_error(
                409,
                "SAD_SAVE_REPO_REQUIRED",
                "Connect a Google Drive project repo before saving.",
            )
        if repo.status == "disconnected" or repo.saves_blocked:
            raise _sad_save_error(
                409,
                "SAD_SAVE_REPO_DISCONNECTED",
                "Reconnect Google Drive before saving.",
            )

        preview_record = repository.get_preview(preview_id)
        if preview_record is None:
            raise _sad_save_error(
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
            if config.drive_mode == "live":
                live_drive_client, live_secret_store = _resolve_live_services(
                    config=config,
                    drive_client=drive_client,
                    secret_store=secret_store,
                )
            record = sad_save_repository.save_preview(
                owner_uid=user.uid,
                owner_email=user.email,
                repo=repo,
                preview_record=preview_record,
                sources=sources,
                mode=config.drive_mode,
                drive_client=live_drive_client,
                secret_store=live_secret_store,
            )
        except SadSaveTokenMissingError as exc:
            raise _sad_save_error(
                409,
                "SAD_SAVE_TOKEN_MISSING",
                "Reconnect Google Drive before saving.",
            ) from exc
        except SadSaveTokenInvalidError as exc:
            raise _sad_save_error(
                401,
                "SAD_SAVE_TOKEN_INVALID",
                "Reconnect Google Drive to renew permission.",
            ) from exc
        except SadSaveDriveUploadError as exc:
            raise _sad_save_error(
                502,
                "SAD_SAVE_DRIVE_UPLOAD_FAILED",
                "Google Drive rejected the upload.",
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
            config=config,
            drive_client=drive_client,
            secret_store=secret_store,
        )
        try:
            remote_file = context.drive_client.find_file_in_folder(
                access_token=context.access_token,
                folder_id=context.repo.repo_folder_id,
                name=WIKI_FILE_NAME,
                mime_type=WIKI_MIME_TYPE,
            )
            remote_markdown = None
            remote_hash = None
            if remote_file is not None:
                remote_markdown = context.drive_client.download_text_file(
                    access_token=context.access_token,
                    file_id=remote_file.file_id,
                )
                remote_hash = _wiki_hash(remote_markdown)
        except DriveTextFileError as exc:
            raise _wiki_error(
                502,
                "WIKI_REMOTE_READ_FAILED",
                "Could not read the existing wiki file.",
            ) from exc

        state = wiki_state_repository.get_state(context.repo.grant_id)
        last_known_hash = state.hash if state is not None else None
        remote_exists = remote_file is not None
        requires_confirmation = remote_exists and remote_hash != last_known_hash
        return WikiPreviewResponse(
            proposed_markdown=_compose_wiki(context),
            remote_hash=remote_hash,
            last_known_hash=last_known_hash,
            requires_confirmation=requires_confirmation,
            remote_exists=remote_exists,
            remote_markdown=remote_markdown if requires_confirmation else None,
        )

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
            config=config,
            drive_client=drive_client,
            secret_store=secret_store,
        )
        try:
            remote_file = context.drive_client.find_file_in_folder(
                access_token=context.access_token,
                folder_id=context.repo.repo_folder_id,
                name=WIKI_FILE_NAME,
                mime_type=WIKI_MIME_TYPE,
            )
            remote_hash = None
            if remote_file is not None:
                remote_markdown = context.drive_client.download_text_file(
                    access_token=context.access_token,
                    file_id=remote_file.file_id,
                )
                remote_hash = _wiki_hash(remote_markdown)
        except DriveTextFileError as exc:
            raise _wiki_error(
                502,
                "WIKI_REMOTE_READ_FAILED",
                "Could not read the existing wiki file.",
            ) from exc

        if (
            remote_file is not None
            and remote_hash != request.expected_remote_hash
            and not request.force_overwrite
        ):
            raise _wiki_error(
                409,
                "WIKI_CONFLICT",
                "The wiki was changed in Drive since SADify last wrote it. Confirm overwrite.",
            )

        proposed_markdown = _compose_wiki(context)
        wiki_hash = _wiki_hash(proposed_markdown)
        try:
            upload = context.drive_client.upload_or_replace_text_file(
                access_token=context.access_token,
                folder_id=context.repo.repo_folder_id,
                name=WIKI_FILE_NAME,
                mime_type=WIKI_MIME_TYPE,
                content=proposed_markdown,
                existing_file_id=remote_file.file_id if remote_file else None,
            )
        except DriveTextFileError as exc:
            raise _wiki_error(
                502,
                "WIKI_WRITE_FAILED",
                "Google Drive rejected the wiki update.",
            ) from exc

        updated_at = datetime.now(UTC)
        wiki_state_repository.record_write(
            context.repo.grant_id,
            file_id=upload.file_id,
            hash_value=wiki_hash,
            updated_at=updated_at,
        )
        return WikiUpdateResponse(
            wiki_path=WIKI_PATH,
            wiki_url=upload.web_view_link,
            wiki_file_id=upload.file_id,
            wiki_hash=wiki_hash,
            updated_at=updated_at,
            created_new_file=remote_file is None,
        )

    return router


@dataclass(frozen=True)
class _WikiRouteContext:
    repo: DriveRepoRecord
    latest_save: SadSaveRecord
    all_saves_for_repo: list[SadSaveRecord]
    sources: list[SourceRecord]
    drive_client: DriveClient
    access_token: str


def _resolve_live_services(
    *,
    config: ApiConfig,
    drive_client: DriveClient | None,
    secret_store: SecretStore | None,
) -> tuple[DriveClient, SecretStore]:
    if drive_client is not None and secret_store is not None:
        return drive_client, secret_store
    if not config.drive_live_enabled:
        raise _sad_save_error(
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
    config: ApiConfig,
    drive_client: DriveClient | None,
    secret_store: SecretStore | None,
) -> _WikiRouteContext:
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
    if config.drive_mode != "live" or not config.drive_live_enabled:
        raise _wiki_error(
            503,
            "WIKI_LIVE_MODE_DISABLED",
            "Live wiki updates are disabled for this process.",
        )

    saves = _saves_for_repo(sad_save_repository, repo.grant_id)
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
    return _WikiRouteContext(
        repo=repo,
        latest_save=latest_save,
        all_saves_for_repo=saves,
        sources=sources,
        drive_client=live_drive_client,
        access_token=access_token,
    )


def _saves_for_repo(
    sad_save_repository: SadSaveRepository,
    repo_grant_id: str,
) -> list[SadSaveRecord]:
    records = getattr(sad_save_repository, "_records", {})
    return sorted(
        [
            record
            for record in records.values()
            if record.repo_grant_id == repo_grant_id
        ],
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


def _compose_wiki(context: _WikiRouteContext) -> str:
    return compose_wiki_markdown(
        repo=context.repo,
        latest_save=context.latest_save,
        all_saves_for_repo=context.all_saves_for_repo,
        sources=context.sources,
        requirement_text=context.latest_save.manifest.requirement_text,
    )


def _wiki_hash(value: str) -> str:
    return f"sha256:{sha256(value.encode('utf-8')).hexdigest()}"


def _wiki_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )
