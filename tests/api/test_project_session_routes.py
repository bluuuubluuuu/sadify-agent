import pytest
from fastapi.testclient import TestClient

from sadify_api.main import create_app
from sadify_api.services.auth import VerifiedFirebaseUser
from sadify_api.services.drive_repo import DriveRepoRepository
from sadify_api.services.projects import ProjectRepository
from sadify_api.services.session_state import SessionSnapshotRepository


PAYLOAD = {
    "clean_requirement_text": "Bike rental ops",
    "analysis_response": None,
    "answer_history": ["Previous question: ...\nPrevious answer: hourly"],
    "source_context": "",
    "source_references": [],
    "selected_model": None,
    "status": "in_progress",
}


class AcceptingTokenVerifier:
    def verify_id_token(self, id_token: str) -> VerifiedFirebaseUser:
        return VerifiedFirebaseUser(
            uid="firebase-uid-001",
            email="owner@example.com",
            display_name="Project Owner",
            provider="firebase",
        )


@pytest.fixture
def client_with_active_project():
    client = TestClient(
        create_app(
            token_verifier=AcceptingTokenVerifier(),
            drive_repo_repository=DriveRepoRepository(),
            project_repository=ProjectRepository(),
            session_snapshot_repository=SessionSnapshotRepository(),
        )
    )
    headers = {"Authorization": "Bearer firebase-test-token"}
    connected = client.post(
        "/drive/repo/connect",
        headers=headers,
        json={
            "project_id": "PROJ-000001",
            "authorization_code": "mock-authorization-code",
            "repo_folder_name": "Operations MVP",
            "create_new_repo": True,
        },
    )
    assert connected.status_code == 200
    created = client.post(
        "/projects",
        headers=headers,
        json={"name": "Bike Rental"},
    )
    assert created.status_code == 200
    return client, headers, created.json()["project"]["project_id"]


def test_put_then_get_session_round_trips(client_with_active_project):
    client, headers, project_id = client_with_active_project
    put = client.put(f"/projects/{project_id}/session", json=PAYLOAD, headers=headers)
    assert put.status_code == 204

    got = client.get(f"/projects/{project_id}/session", headers=headers)
    assert got.status_code == 200
    assert got.json()["clean_requirement_text"] == "Bike rental ops"
    assert got.json()["answer_history"][0].startswith("Previous question")
    assert got.json()["updated_at"] is not None


def test_get_session_absent_returns_204(client_with_active_project):
    client, headers, project_id = client_with_active_project
    assert client.get(f"/projects/{project_id}/session", headers=headers).status_code == 204


def test_put_session_unknown_project_404(client_with_active_project):
    client, headers, _ = client_with_active_project
    response = client.put(
        "/projects/PR-999999/session",
        json=PAYLOAD,
        headers=headers,
    )
    assert response.status_code == 404


def test_get_session_unknown_project_404(client_with_active_project):
    client, headers, _ = client_with_active_project
    assert client.get("/projects/PR-999999/session", headers=headers).status_code == 404


def test_put_session_requires_auth(client_with_active_project):
    client, _, project_id = client_with_active_project
    assert client.put(f"/projects/{project_id}/session", json=PAYLOAD).status_code == 401
