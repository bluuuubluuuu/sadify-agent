import logging

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
)
from sadify_api.services.auth import TokenVerifier
from sadify_api.services.drive_client import DriveClient
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
from sadify_api.services.secret_store import SecretStore, get_secret_store
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

    return router


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
