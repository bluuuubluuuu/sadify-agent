from datetime import datetime

from sadify_api.schemas import (
    GuestDraftMigrationResponse,
    GuestDraftRecord,
    SignedInProjectRecord,
)


class GuestDraftNotFoundError(Exception):
    pass


class GuestDraftRepository:
    def __init__(self) -> None:
        self._drafts: dict[str, GuestDraftRecord] = {}
        self._project_copies: dict[str, SignedInProjectRecord] = {}
        self._next_guest_number = 1
        self._next_project_number = 1

    def create_guest_draft(
        self,
        *,
        guest_session_id: str,
        created_at: datetime,
        requirement_text: str | None = None,
    ) -> GuestDraftRecord:
        draft = create_guest_draft(
            guest_session_id=guest_session_id,
            requirement_text=requirement_text,
            created_at=created_at,
            next_number=self._next_guest_number,
        )
        self._next_guest_number += 1
        return self.save(draft)

    def save(self, draft: GuestDraftRecord) -> GuestDraftRecord:
        self._drafts[draft.guest_draft_id] = draft
        return draft

    def get_guest_draft(self, guest_draft_id: str) -> GuestDraftRecord | None:
        return self._drafts.get(guest_draft_id)

    def get_project_copy(self, project_id: str) -> SignedInProjectRecord | None:
        return self._project_copies.get(project_id)

    def copy_to_signed_in_project(
        self,
        *,
        guest_draft_id: str,
        owner_uid: str,
        owner_email: str | None,
        migrated_at: datetime,
    ) -> GuestDraftMigrationResponse:
        draft = self.get_guest_draft(guest_draft_id)
        if draft is None:
            raise GuestDraftNotFoundError(guest_draft_id)

        if draft.migrated_to_project_id:
            existing_project = self._project_copies[draft.migrated_to_project_id]
            return GuestDraftMigrationResponse(
                status="copied",
                guest_draft=draft,
                project=existing_project,
                message="Guest draft already copied to your signed-in project.",
            )

        project_id = f"PRJ-{self._next_project_number:06d}"
        self._next_project_number += 1
        project = SignedInProjectRecord(
            project_id=project_id,
            owner_kind="signed_in",
            owner_uid=owner_uid,
            owner_email=owner_email,
            source_guest_draft_id=draft.guest_draft_id,
            requirement_text=draft.requirement_text,
            status="active",
            created_at=migrated_at,
            updated_at=migrated_at,
        )
        migrated_draft = draft.model_copy(
            update={
                "status": "migrated",
                "migrated_to_project_id": project_id,
                "updated_at": migrated_at,
            },
        )
        self._drafts[guest_draft_id] = migrated_draft
        self._project_copies[project_id] = project
        return GuestDraftMigrationResponse(
            status="copied",
            guest_draft=migrated_draft,
            project=project,
            message="Guest draft kept for audit and copied to your signed-in project.",
        )


def create_guest_draft(
    *,
    guest_session_id: str,
    created_at: datetime,
    requirement_text: str | None = None,
    next_number: int = 1,
) -> GuestDraftRecord:
    return GuestDraftRecord(
        guest_draft_id=f"GD-{next_number:06d}",
        owner_kind="guest",
        guest_session_id=guest_session_id,
        status="active",
        requirement_text=requirement_text,
        migrated_to_project_id=None,
        created_at=created_at,
        updated_at=created_at,
    )
