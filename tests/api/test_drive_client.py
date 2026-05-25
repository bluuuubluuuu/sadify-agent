from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from sadify_api.services.drive_client import (
    DriveClient,
    DriveFolderCreateError,
    DriveOauthExchangeError,
    DriveTokenInvalidError,
    DriveUploadError,
)


def test_exchange_authorization_code_returns_tokens():
    flow = MagicMock()
    flow.credentials.token = "access-token"
    flow.credentials.refresh_token = "refresh-token"
    flow.credentials.expiry = datetime(2026, 5, 25, tzinfo=UTC)

    with patch(
        "sadify_api.services.drive_client.Flow.from_client_config",
        return_value=flow,
    ) as flow_factory:
        tokens = DriveClient(
            client_id="client-id",
            client_secret="client-secret",
        ).exchange_authorization_code("auth-code", "http://localhost:3000")

    assert tokens.access_token == "access-token"
    assert tokens.refresh_token == "refresh-token"
    assert tokens.expiry == datetime(2026, 5, 25, tzinfo=UTC)
    flow_factory.assert_called_once()
    flow.fetch_token.assert_called_once_with(code="auth-code")


def test_exchange_authorization_code_surfaces_invalid_grant_error():
    flow = MagicMock()
    flow.fetch_token.side_effect = RuntimeError("invalid_grant")

    with patch(
        "sadify_api.services.drive_client.Flow.from_client_config",
        return_value=flow,
    ):
        with pytest.raises(DriveOauthExchangeError):
            DriveClient(
                client_id="client-id",
                client_secret="client-secret",
            ).exchange_authorization_code("bad-code", "http://localhost:3000")


def test_refresh_access_token_returns_new_access_token():
    with patch("sadify_api.services.drive_client.Credentials") as credentials_cls:
        credentials = credentials_cls.return_value
        credentials.token = "new-access-token"

        token = DriveClient(
            client_id="client-id",
            client_secret="client-secret",
        ).refresh_access_token("refresh-token")

    assert token == "new-access-token"
    credentials.refresh.assert_called_once()


def test_refresh_access_token_propagates_invalid_token_error():
    with patch("sadify_api.services.drive_client.Credentials") as credentials_cls:
        credentials_cls.return_value.refresh.side_effect = RuntimeError("invalid")

        with pytest.raises(DriveTokenInvalidError):
            DriveClient(
                client_id="client-id",
                client_secret="client-secret",
            ).refresh_access_token("bad-refresh-token")


def test_find_or_create_folder_returns_existing_when_present():
    service = _drive_service()
    service.files.return_value.list.return_value.execute.return_value = {
        "files": [{"id": "folder-123", "name": "SADify Projects"}]
    }

    with patch("sadify_api.services.drive_client.build", return_value=service):
        folder = DriveClient(
            client_id="client-id",
            client_secret="client-secret",
        ).find_or_create_folder("access-token", "SADify Projects")

    assert folder.folder_id == "folder-123"
    assert folder.name == "SADify Projects"
    service.files.return_value.create.assert_not_called()


def test_find_or_create_folder_creates_when_missing():
    service = _drive_service()
    service.files.return_value.list.return_value.execute.return_value = {"files": []}
    service.files.return_value.create.return_value.execute.return_value = {
        "id": "folder-456",
        "name": "SADify Projects",
    }

    with patch("sadify_api.services.drive_client.build", return_value=service):
        folder = DriveClient(
            client_id="client-id",
            client_secret="client-secret",
        ).find_or_create_folder("access-token", "SADify Projects")

    assert folder.folder_id == "folder-456"
    assert folder.name == "SADify Projects"
    create_call = service.files.return_value.create.call_args.kwargs
    assert create_call["body"]["mimeType"] == "application/vnd.google-apps.folder"
    assert create_call["body"]["name"] == "SADify Projects"


def test_find_or_create_folder_surfaces_create_failure():
    service = _drive_service()
    service.files.return_value.list.return_value.execute.return_value = {"files": []}
    service.files.return_value.create.return_value.execute.side_effect = RuntimeError(
        "drive rejected"
    )

    with patch("sadify_api.services.drive_client.build", return_value=service):
        with pytest.raises(DriveFolderCreateError):
            DriveClient(
                client_id="client-id",
                client_secret="client-secret",
            ).find_or_create_folder("access-token", "SADify Projects")


def test_upload_markdown_as_doc_returns_id_and_link():
    service = _drive_service()
    service.files.return_value.create.return_value.execute.return_value = {
        "id": "doc-123",
        "webViewLink": "https://docs.google.com/document/d/doc-123/edit",
    }

    with patch("sadify_api.services.drive_client.build", return_value=service):
        result = DriveClient(
            client_id="client-id",
            client_secret="client-secret",
        ).upload_markdown_as_doc(
            access_token="access-token",
            folder_id="folder-123",
            title="Laundry SAD",
            markdown="# Laundry SAD",
        )

    assert result.file_id == "doc-123"
    assert result.web_view_link == "https://docs.google.com/document/d/doc-123/edit"
    create_call = service.files.return_value.create.call_args.kwargs
    assert create_call["body"] == {
        "name": "Laundry SAD",
        "parents": ["folder-123"],
        "mimeType": "application/vnd.google-apps.document",
    }
    assert create_call["fields"] == "id,webViewLink"


def test_upload_markdown_as_doc_propagates_drive_error():
    service = _drive_service()
    service.files.return_value.create.return_value.execute.side_effect = RuntimeError(
        "upload failed"
    )

    with patch("sadify_api.services.drive_client.build", return_value=service):
        with pytest.raises(DriveUploadError):
            DriveClient(
                client_id="client-id",
                client_secret="client-secret",
            ).upload_markdown_as_doc(
                access_token="access-token",
                folder_id="folder-123",
                title="Laundry SAD",
                markdown="# Laundry SAD",
            )


def _drive_service() -> MagicMock:
    return MagicMock()
