import logging

from google.api_core.exceptions import NotFound
from fastapi import APIRouter, Header, HTTPException

from sadify_api.routes.auth import verify_authorization_header
from sadify_api.config import ApiConfig, load_api_config
from sadify_api.schemas import (
    DriveRepoConnectRequest,
    DriveRepoDisconnectResponse,
    DriveRepoRecord,
)
from sadify_api.services.auth import TokenVerifier
from sadify_api.services.drive_client import (
    DriveClient,
    DriveFolderCreateError,
    DriveOauthExchangeError,
)
from sadify_api.services.drive_repo import DriveRepoRepository, DriveTokenPersistError
from sadify_api.services.secret_store import SecretStore, get_secret_store

logger = logging.getLogger(__name__)


def create_drive_router(
    repository: DriveRepoRepository,
    token_verifier: TokenVerifier,
    config: ApiConfig | None = None,
    drive_client: DriveClient | None = None,
    secret_store: SecretStore | None = None,
) -> APIRouter:
    config = config or load_api_config()
    router = APIRouter(prefix="/drive", tags=["drive"])

    @router.post("/repo/connect", response_model=DriveRepoRecord)
    def connect_repo(
        request: DriveRepoConnectRequest,
        authorization: str | None = Header(default=None),
    ) -> DriveRepoRecord:
        user = verify_authorization_header(authorization, token_verifier)
        try:
            live_drive_client = drive_client
            live_secret_store = secret_store
            if config.drive_mode == "live":
                live_drive_client, live_secret_store = _resolve_live_services(
                    config=config,
                    drive_client=drive_client,
                    secret_store=secret_store,
                )
            return repository.connect_repo(
                owner_uid=user.uid,
                owner_email=user.email,
                request=request,
                mode=config.drive_mode,
                drive_client=live_drive_client,
                secret_store=live_secret_store,
                drive_folder_name=config.drive_folder_name,
            )
        except DriveOauthExchangeError as exc:
            raise _drive_error(
                502,
                "DRIVE_OAUTH_EXCHANGE_FAILED",
                "Could not complete Google Drive sign-in.",
            ) from exc
        except DriveFolderCreateError as exc:
            raise _drive_error(
                502,
                "DRIVE_FOLDER_CREATE_FAILED",
                "Could not create the SADify Projects folder.",
            ) from exc
        except DriveTokenPersistError as exc:
            raise _drive_error(
                502,
                "DRIVE_TOKEN_PERSIST_FAILED",
                "Could not securely store your Drive permission.",
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/repo/disconnect", response_model=DriveRepoDisconnectResponse)
    def disconnect_repo(
        authorization: str | None = Header(default=None),
    ) -> DriveRepoDisconnectResponse:
        user = verify_authorization_header(authorization, token_verifier)
        repo = repository.disconnect_repo(owner_uid=user.uid)
        if (
            config.drive_mode == "live"
            and repo is not None
            and repo.token_store == "secret_manager"
        ):
            try:
                live_secret_store = secret_store or _resolve_live_services(
                    config=config,
                    drive_client=drive_client,
                    secret_store=secret_store,
                )[1]
                live_secret_store.delete_user_secret(user.uid)
            except NotFound:
                pass
            except Exception:
                logger.warning(
                    "drive_repo_disconnect_secret_delete_failed uid=%s",
                    user.uid,
                    exc_info=True,
                )
        return DriveRepoDisconnectResponse(
            status="disconnected",
            saves_blocked=True,
            repo=repo,
        )

    @router.get("/repo/status", response_model=DriveRepoRecord | None)
    def repo_status(
        authorization: str | None = Header(default=None),
    ) -> DriveRepoRecord | None:
        user = verify_authorization_header(authorization, token_verifier)
        return repository.get_active_repo(user.uid)

    return router


def _resolve_live_services(
    *,
    config: ApiConfig,
    drive_client: DriveClient | None,
    secret_store: SecretStore | None,
) -> tuple[DriveClient, SecretStore]:
    if drive_client is not None and secret_store is not None:
        return drive_client, secret_store
    if not config.tc026b_live:
        raise _drive_error(
            503,
            "DRIVE_LIVE_MODE_DISABLED",
            "Live Drive mode is disabled for this process.",
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


def _drive_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )
