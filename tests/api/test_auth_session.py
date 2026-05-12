from fastapi.testclient import TestClient

from sadify_api.main import create_app
from sadify_api.services.auth import AuthVerificationError, VerifiedFirebaseUser


class AcceptingTokenVerifier:
    def __init__(self) -> None:
        self.seen_tokens: list[str] = []

    def verify_id_token(self, id_token: str) -> VerifiedFirebaseUser:
        self.seen_tokens.append(id_token)
        return VerifiedFirebaseUser(
            uid="firebase-uid-001",
            email="owner@example.com",
            display_name="Project Owner",
            provider="firebase",
        )


class RejectingTokenVerifier:
    def verify_id_token(self, id_token: str) -> VerifiedFirebaseUser:
        raise AuthVerificationError("invalid Firebase ID token")


def test_auth_session_verifies_bearer_token_without_echoing_secret():
    verifier = AcceptingTokenVerifier()
    client = TestClient(create_app(token_verifier=verifier))

    response = client.post(
        "/auth/session",
        headers={"Authorization": "Bearer firebase-test-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "authenticated",
        "user": {
            "uid": "firebase-uid-001",
            "email": "owner@example.com",
            "display_name": "Project Owner",
            "provider": "firebase",
        },
    }
    assert verifier.seen_tokens == ["firebase-test-token"]
    assert "firebase-test-token" not in response.text


def test_auth_me_rejects_missing_bearer_token():
    client = TestClient(create_app(token_verifier=AcceptingTokenVerifier()))

    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


def test_auth_session_rejects_invalid_token():
    client = TestClient(create_app(token_verifier=RejectingTokenVerifier()))

    response = client.post(
        "/auth/session",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid authentication token"}
    assert "invalid-token" not in response.text


def test_auth_session_allows_frontend_cors_preflight():
    client = TestClient(create_app(token_verifier=AcceptingTokenVerifier()))

    response = client.options(
        "/auth/session",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "authorization" in response.headers["access-control-allow-headers"].lower()
