from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException

from sadify_api.routes.auth import verify_authorization_header
from sadify_api.schemas import (
    GuestDraftCreateRequest,
    GuestDraftMigrationResponse,
    GuestDraftRecord,
)
from sadify_api.services.auth import TokenVerifier
from sadify_api.services.guest_drafts import (
    GuestDraftNotFoundError,
    GuestDraftRepository,
)


def create_drafts_router(
    repository: GuestDraftRepository,
    token_verifier: TokenVerifier,
) -> APIRouter:
    router = APIRouter(prefix="/drafts", tags=["drafts"])

    @router.post("/guest", response_model=GuestDraftRecord)
    def create_guest_draft(request: GuestDraftCreateRequest) -> GuestDraftRecord:
        return repository.create_guest_draft(
            guest_session_id=request.guest_session_id,
            requirement_text=request.requirement_text,
            created_at=datetime.now(UTC),
        )

    @router.post(
        "/guest/{guest_draft_id}/migrate",
        response_model=GuestDraftMigrationResponse,
    )
    def migrate_guest_draft(
        guest_draft_id: str,
        authorization: str | None = Header(default=None),
    ) -> GuestDraftMigrationResponse:
        user = verify_authorization_header(authorization, token_verifier)
        try:
            return repository.copy_to_signed_in_project(
                guest_draft_id=guest_draft_id,
                owner_uid=user.uid,
                owner_email=user.email,
                migrated_at=datetime.now(UTC),
            )
        except GuestDraftNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Guest draft not found") from exc

    return router
