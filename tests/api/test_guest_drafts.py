from datetime import UTC, datetime

from fastapi.testclient import TestClient

from sadify_api.main import create_app
from sadify_api.services.auth import VerifiedFirebaseUser
from sadify_api.services.guest_drafts import (
    GuestDraftRepository,
    create_guest_draft,
)


class AcceptingTokenVerifier:
    def verify_id_token(self, id_token: str) -> VerifiedFirebaseUser:
        return VerifiedFirebaseUser(
            uid="firebase-uid-001",
            email="owner@example.com",
            display_name="Project Owner",
            provider="firebase",
        )


def test_create_guest_draft_has_auditable_owner_and_status():
    now = datetime(2026, 5, 13, tzinfo=UTC)

    draft = create_guest_draft(
        guest_session_id="guest-session-001",
        requirement_text="Need to validate a workflow idea.",
        created_at=now,
        next_number=7,
    )

    assert draft.guest_draft_id == "GD-000007"
    assert draft.owner_kind == "guest"
    assert draft.guest_session_id == "guest-session-001"
    assert draft.requirement_text == "Need to validate a workflow idea."
    assert draft.status == "active"
    assert draft.migrated_to_project_id is None
    assert draft.created_at == now
    assert draft.updated_at == now


def test_guest_draft_migration_copies_without_deleting_guest_draft():
    repository = GuestDraftRepository()
    created_at = datetime(2026, 5, 13, 9, 0, tzinfo=UTC)
    migrated_at = datetime(2026, 5, 13, 9, 5, tzinfo=UTC)
    draft = repository.create_guest_draft(
        guest_session_id="guest-session-001",
        requirement_text="Keep stock movement records clear.",
        created_at=created_at,
    )

    migration = repository.copy_to_signed_in_project(
        guest_draft_id=draft.guest_draft_id,
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        migrated_at=migrated_at,
    )

    original = repository.get_guest_draft(draft.guest_draft_id)
    project = repository.get_project_copy(migration.project.project_id)

    assert original is not None
    assert original.status == "migrated"
    assert original.migrated_to_project_id == migration.project.project_id
    assert original.requirement_text == "Keep stock movement records clear."
    assert project == migration.project
    assert project.owner_kind == "signed_in"
    assert project.owner_uid == "firebase-uid-001"
    assert project.source_guest_draft_id == draft.guest_draft_id
    assert migration.status == "copied"


def test_guest_draft_api_creates_and_migrates_with_bearer_token():
    client = TestClient(create_app(token_verifier=AcceptingTokenVerifier()))

    create_response = client.post(
        "/drafts/guest",
        json={
            "guest_session_id": "browser-session-001",
            "requirement_text": "Need a simple way to validate an idea.",
        },
    )

    assert create_response.status_code == 200
    guest_draft_id = create_response.json()["guest_draft_id"]

    migrate_response = client.post(
        f"/drafts/guest/{guest_draft_id}/migrate",
        headers={"Authorization": "Bearer firebase-test-token"},
    )

    assert migrate_response.status_code == 200
    payload = migrate_response.json()
    assert payload["status"] == "copied"
    assert payload["guest_draft"]["guest_draft_id"] == guest_draft_id
    assert payload["guest_draft"]["status"] == "migrated"
    assert payload["project"]["owner_uid"] == "firebase-uid-001"
    assert payload["project"]["source_guest_draft_id"] == guest_draft_id
    assert payload["guest_draft"]["migrated_to_project_id"] == payload["project"]["project_id"]


def test_guest_draft_migration_rejects_missing_auth():
    client = TestClient(create_app(token_verifier=AcceptingTokenVerifier()))
    create_response = client.post(
        "/drafts/guest",
        json={"guest_session_id": "browser-session-001"},
    )
    guest_draft_id = create_response.json()["guest_draft_id"]

    response = client.post(f"/drafts/guest/{guest_draft_id}/migrate")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}
