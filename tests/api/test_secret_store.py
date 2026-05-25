from unittest.mock import MagicMock, patch

import pytest
from google.api_core.exceptions import NotFound

from sadify_api.services.secret_store import SecretStore


def test_get_oauth_client_secret_returns_payload_text():
    client = _client()
    client.access_secret_version.return_value = _secret_payload("client-secret")

    store = SecretStore(
        project_id="sadify",
        oauth_client_secret_name="sadify-drive-oauth-client-secret",
        client=client,
    )

    assert store.get_oauth_client_secret() == "client-secret"
    client.access_secret_version.assert_called_once_with(
        request={
            "name": "projects/sadify/secrets/sadify-drive-oauth-client-secret/versions/latest"
        }
    )


def test_put_user_refresh_token_creates_secret_when_missing():
    client = _client()
    client.get_secret.side_effect = NotFound("missing")
    store = SecretStore(project_id="sadify", client=client)

    store.put_user_refresh_token("firebase_uid-001", "refresh-token")

    client.create_secret.assert_called_once_with(
        request={
            "parent": "projects/sadify",
            "secret_id": "sadify-drive-token-firebase_uid-001",
            "secret": {"replication": {"automatic": {}}},
        }
    )
    client.add_secret_version.assert_called_once_with(
        request={
            "parent": "projects/sadify/secrets/sadify-drive-token-firebase_uid-001",
            "payload": {"data": b"refresh-token"},
        }
    )


def test_put_user_refresh_token_adds_version_when_secret_exists():
    client = _client()
    store = SecretStore(project_id="sadify", client=client)

    store.put_user_refresh_token("firebase-uid-001", "refresh-token")

    client.create_secret.assert_not_called()
    client.add_secret_version.assert_called_once()


def test_get_user_refresh_token_returns_latest_version():
    client = _client()
    client.access_secret_version.return_value = _secret_payload("refresh-token")
    store = SecretStore(project_id="sadify", client=client)

    assert store.get_user_refresh_token("firebase-uid-001") == "refresh-token"
    client.access_secret_version.assert_called_once_with(
        request={
            "name": "projects/sadify/secrets/sadify-drive-token-firebase-uid-001/versions/latest"
        }
    )


def test_get_user_refresh_token_returns_none_when_secret_missing():
    client = _client()
    client.access_secret_version.side_effect = NotFound("missing")
    store = SecretStore(project_id="sadify", client=client)

    assert store.get_user_refresh_token("firebase-uid-001") is None


def test_delete_user_secret_removes_all_versions():
    client = _client()
    store = SecretStore(project_id="sadify", client=client)

    store.delete_user_secret("firebase-uid-001")

    client.delete_secret.assert_called_once_with(
        request={"name": "projects/sadify/secrets/sadify-drive-token-firebase-uid-001"}
    )


def test_delete_user_secret_ignores_missing_secret():
    client = _client()
    client.delete_secret.side_effect = NotFound("missing")
    store = SecretStore(project_id="sadify", client=client)

    store.delete_user_secret("firebase-uid-001")

    client.delete_secret.assert_called_once()


def test_secret_store_rejects_invalid_uid_for_user_secret_name():
    store = SecretStore(project_id="sadify", client=_client())

    with pytest.raises(ValueError):
        store.put_user_refresh_token("../bad", "refresh-token")


def test_get_secret_store_uses_secret_manager_client_factory():
    with patch(
        "sadify_api.services.secret_store.secretmanager.SecretManagerServiceClient"
    ) as client_factory:
        from sadify_api.services.secret_store import get_secret_store

        store = get_secret_store(project_id="sadify", force_new=True)

    assert isinstance(store, SecretStore)
    client_factory.assert_called_once()


def _client() -> MagicMock:
    client = MagicMock()
    client.secret_path.side_effect = (
        lambda project, secret_id: f"projects/{project}/secrets/{secret_id}"
    )
    client.secret_version_path.side_effect = (
        lambda project, secret_id, version: (
            f"projects/{project}/secrets/{secret_id}/versions/{version}"
        )
    )
    return client


def _secret_payload(value: str):
    payload = MagicMock()
    payload.payload.data = value.encode("utf-8")
    return payload
