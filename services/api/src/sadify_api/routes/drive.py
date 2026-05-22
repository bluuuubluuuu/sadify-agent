from fastapi import APIRouter, Header, HTTPException

from sadify_api.routes.auth import verify_authorization_header
from sadify_api.schemas import (
    DriveRepoConnectRequest,
    DriveRepoDisconnectResponse,
    DriveRepoRecord,
)
from sadify_api.services.auth import TokenVerifier
from sadify_api.services.drive_repo import DriveRepoRepository


def create_drive_router(
    repository: DriveRepoRepository,
    token_verifier: TokenVerifier,
) -> APIRouter:
    router = APIRouter(prefix="/drive", tags=["drive"])

    @router.post("/repo/connect", response_model=DriveRepoRecord)
    def connect_repo(
        request: DriveRepoConnectRequest,
        authorization: str | None = Header(default=None),
    ) -> DriveRepoRecord:
        user = verify_authorization_header(authorization, token_verifier)
        try:
            return repository.connect_repo(
                owner_uid=user.uid,
                owner_email=user.email,
                request=request,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/repo/disconnect", response_model=DriveRepoDisconnectResponse)
    def disconnect_repo(
        authorization: str | None = Header(default=None),
    ) -> DriveRepoDisconnectResponse:
        user = verify_authorization_header(authorization, token_verifier)
        repo = repository.disconnect_repo(owner_uid=user.uid)
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
