from fastapi.testclient import TestClient

from sadify_api.main import create_app
from sadify_api.services.auth import VerifiedFirebaseUser
from sadify_api.services.drive_repo import DriveRepoRepository


class AcceptingTokenVerifier:
    def verify_id_token(self, id_token: str) -> VerifiedFirebaseUser:
        return VerifiedFirebaseUser(
            uid="firebase-uid-001",
            email="owner@example.com",
            display_name="Project Owner",
            provider="firebase",
        )


def test_drive_repo_connect_creates_project_locked_folder_structure():
    repository = DriveRepoRepository()
    client = TestClient(
        create_app(
            token_verifier=AcceptingTokenVerifier(),
            drive_repo_repository=repository,
        )
    )

    response = client.post(
        "/drive/repo/connect",
        headers={"Authorization": "Bearer firebase-test-token"},
        json={
            "project_id": "PROJ-000001",
            "authorization_code": "mock-authorization-code",
            "repo_folder_name": "Operations MVP",
            "create_new_repo": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "connected"
    assert payload["project_id"] == "PROJ-000001"
    assert payload["owner_uid"] == "firebase-uid-001"
    assert payload["grant_id"] == "DG-000001"
    assert payload["repo_folder_id"] == "LOCAL-DRIVE-FOLDER-000001"
    assert payload["repo_folder_name"] == "Operations MVP"
    assert payload["requested_scopes"] == [
        "https://www.googleapis.com/auth/drive.file"
    ]
    assert payload["folder_structure"] == [
        {"name": "Sources", "purpose": "Original uploaded files. Never overwrite."},
        {"name": "SAD", "purpose": "Versioned human-facing SAD Google Docs."},
        {"name": "Wiki", "purpose": "Latest living project brain."},
        {"name": "_SADify", "purpose": "Manifest, extraction text, backups, logs, and metadata."},
    ]
    assert payload["saves_blocked"] is False
    assert "mock-authorization-code" not in response.text

    saved = repository.get_active_repo("firebase-uid-001")
    assert saved is not None
    assert saved.repo_folder_id == "LOCAL-DRIVE-FOLDER-000001"


def test_drive_repo_disconnect_removes_active_save_access():
    repository = DriveRepoRepository()
    client = TestClient(
        create_app(
            token_verifier=AcceptingTokenVerifier(),
            drive_repo_repository=repository,
        )
    )
    client.post(
        "/drive/repo/connect",
        headers={"Authorization": "Bearer firebase-test-token"},
        json={
            "project_id": "PROJ-000001",
            "authorization_code": "mock-authorization-code",
            "repo_folder_id": "existing-folder-123",
            "repo_folder_name": "Existing Repo",
        },
    )

    response = client.post(
        "/drive/repo/disconnect",
        headers={"Authorization": "Bearer firebase-test-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "disconnected"
    assert payload["saves_blocked"] is True
    assert repository.get_active_repo("firebase-uid-001") is None


def test_drive_repo_connect_requires_signed_in_user():
    client = TestClient(create_app(token_verifier=AcceptingTokenVerifier()))

    response = client.post(
        "/drive/repo/connect",
        json={
            "project_id": "PROJ-000001",
            "authorization_code": "mock-authorization-code",
            "repo_folder_name": "Operations MVP",
            "create_new_repo": True,
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}
