from fastapi.testclient import TestClient

from sadify_api.config import ApiConfig
from sadify_api.main import create_app


def test_health_returns_backend_contract():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "sadify-api",
        "environment": "test",
    }


def test_config_diagnostics_return_only_redacted_runtime_details():
    client = TestClient(create_app(ApiConfig(environment="test")))

    response = client.get("/diagnostics/config")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "sadify-api",
        "environment": "test",
        "diagnostics_enabled": True,
        "secrets": "redacted",
    }


def test_config_diagnostics_can_be_disabled():
    client = TestClient(
        create_app(ApiConfig(environment="production", diagnostics_enabled=False))
    )

    response = client.get("/diagnostics/config")

    assert response.status_code == 404
