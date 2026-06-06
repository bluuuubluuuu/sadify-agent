import pytest

from sadify_api.config import ApiConfig
from sadify_api.services.live_drive import (
    LiveDriveServicesDisabledError,
    resolve_live_drive_services,
)


def test_resolve_live_drive_services_returns_injected_deps_when_both_provided():
    drive_client = object()
    secret_store = object()

    resolved = resolve_live_drive_services(
        _config(drive_live_enabled=False),
        drive_client,
        secret_store,
    )

    assert resolved == (drive_client, secret_store)


def test_resolve_live_drive_services_raises_when_live_drive_disabled():
    with pytest.raises(LiveDriveServicesDisabledError):
        resolve_live_drive_services(
            _config(drive_live_enabled=False),
            drive_client=None,
            secret_store=None,
        )


def test_resolve_live_drive_services_lazily_constructs_missing_deps(monkeypatch):
    from sadify_api.services import live_drive

    calls = []

    class FakeSecretStore:
        def get_oauth_client_secret(self) -> str:
            return "client-secret"

    class FakeDriveClient:
        def __init__(self, *, client_id: str, client_secret: str) -> None:
            self.client_id = client_id
            self.client_secret = client_secret

    def fake_get_secret_store(**kwargs):
        calls.append(kwargs)
        return FakeSecretStore()

    monkeypatch.setattr(live_drive, "get_secret_store", fake_get_secret_store)
    monkeypatch.setattr(live_drive, "DriveClient", FakeDriveClient)

    drive_client, secret_store = resolve_live_drive_services(
        _config(drive_live_enabled=True),
        drive_client=None,
        secret_store=None,
    )

    assert calls == [
        {
            "project_id": "sadify-test",
            "oauth_client_secret_name": "oauth-secret-name",
        }
    ]
    assert isinstance(secret_store, FakeSecretStore)
    assert isinstance(drive_client, FakeDriveClient)
    assert drive_client.client_id == "oauth-client-id"
    assert drive_client.client_secret == "client-secret"


def test_resolve_live_drive_services_reuses_drive_client_and_constructs_secret_store(
    monkeypatch,
):
    from sadify_api.services import live_drive

    drive_client = object()
    calls = []

    class FakeSecretStore:
        pass

    def fake_get_secret_store(**kwargs):
        calls.append(kwargs)
        return FakeSecretStore()

    def fail_drive_client(**_kwargs):
        raise AssertionError("DriveClient should not be constructed")

    monkeypatch.setattr(live_drive, "get_secret_store", fake_get_secret_store)
    monkeypatch.setattr(live_drive, "DriveClient", fail_drive_client)

    resolved_drive_client, resolved_secret_store = resolve_live_drive_services(
        _config(drive_live_enabled=True),
        drive_client=drive_client,
        secret_store=None,
    )

    assert resolved_drive_client is drive_client
    assert isinstance(resolved_secret_store, FakeSecretStore)
    assert calls == [
        {
            "project_id": "sadify-test",
            "oauth_client_secret_name": "oauth-secret-name",
        }
    ]


def test_resolve_live_drive_services_reuses_secret_store_and_constructs_drive_client(
    monkeypatch,
):
    from sadify_api.services import live_drive

    calls = []

    class FakeSecretStore:
        def get_oauth_client_secret(self) -> str:
            return "existing-secret"

    class FakeDriveClient:
        def __init__(self, *, client_id: str, client_secret: str) -> None:
            calls.append({"client_id": client_id, "client_secret": client_secret})

    def fail_get_secret_store(**_kwargs):
        raise AssertionError("get_secret_store should not be called")

    secret_store = FakeSecretStore()
    monkeypatch.setattr(live_drive, "get_secret_store", fail_get_secret_store)
    monkeypatch.setattr(live_drive, "DriveClient", FakeDriveClient)

    resolved_drive_client, resolved_secret_store = resolve_live_drive_services(
        _config(drive_live_enabled=True),
        drive_client=None,
        secret_store=secret_store,
    )

    assert isinstance(resolved_drive_client, FakeDriveClient)
    assert resolved_secret_store is secret_store
    assert calls == [
        {"client_id": "oauth-client-id", "client_secret": "existing-secret"}
    ]


def _config(*, drive_live_enabled: bool) -> ApiConfig:
    return ApiConfig(
        environment="test",
        google_cloud_project="sadify-test",
        google_oauth_client_id="oauth-client-id",
        google_oauth_client_secret_name="oauth-secret-name",
        drive_mode="live",
        drive_live_enabled=drive_live_enabled,
    )
