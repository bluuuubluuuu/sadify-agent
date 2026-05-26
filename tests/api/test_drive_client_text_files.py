from unittest.mock import MagicMock, patch

import pytest

from sadify_api.services.drive_client import (
    DriveClient,
    DriveTextFileError,
)


def test_find_file_in_folder_returns_id_when_present():
    service = _drive_service()
    service.files.return_value.list.return_value.execute.return_value = {
        "files": [
            {
                "id": "wiki-file-001",
                "name": "Wiki.md",
                "mimeType": "text/markdown",
                "webViewLink": "https://drive.google.com/file/d/wiki-file-001/view",
                "md5Checksum": "abc",
            }
        ]
    }

    with patch("sadify_api.services.drive_client.build", return_value=service):
        ref = _client().find_file_in_folder(
            access_token="access-token",
            folder_id="folder-001",
            name="Wiki.md",
            mime_type="text/markdown",
        )

    assert ref is not None
    assert ref.file_id == "wiki-file-001"
    assert ref.name == "Wiki.md"
    assert ref.mime_type == "text/markdown"
    assert ref.web_view_link == "https://drive.google.com/file/d/wiki-file-001/view"
    assert ref.md5_checksum == "abc"


def test_find_file_in_folder_returns_none_when_absent():
    service = _drive_service()
    service.files.return_value.list.return_value.execute.return_value = {"files": []}

    with patch("sadify_api.services.drive_client.build", return_value=service):
        ref = _client().find_file_in_folder(
            access_token="access-token",
            folder_id="folder-001",
            name="Wiki.md",
        )

    assert ref is None


def test_download_text_file_returns_decoded_string():
    service = _drive_service()
    service.files.return_value.get_media.return_value.execute.return_value = (
        "# SADify Project Wiki".encode("utf-8")
    )

    with patch("sadify_api.services.drive_client.build", return_value=service):
        text = _client().download_text_file(
            access_token="access-token",
            file_id="wiki-file-001",
        )

    assert text == "# SADify Project Wiki"


def test_upload_or_replace_text_file_creates_when_missing():
    service = _drive_service()
    service.files.return_value.create.return_value.execute.return_value = {
        "id": "wiki-file-001",
        "webViewLink": "https://drive.google.com/file/d/wiki-file-001/view",
    }

    with patch("sadify_api.services.drive_client.build", return_value=service):
        result = _client().upload_or_replace_text_file(
            access_token="access-token",
            folder_id="folder-001",
            name="Wiki.md",
            mime_type="text/markdown",
            content="# Wiki",
            existing_file_id=None,
        )

    assert result.file_id == "wiki-file-001"
    service.files.return_value.create.assert_called_once()
    service.files.return_value.update.assert_not_called()


def test_upload_or_replace_text_file_updates_when_present():
    service = _drive_service()
    service.files.return_value.update.return_value.execute.return_value = {
        "id": "wiki-file-001",
        "webViewLink": "https://drive.google.com/file/d/wiki-file-001/view",
    }

    with patch("sadify_api.services.drive_client.build", return_value=service):
        result = _client().upload_or_replace_text_file(
            access_token="access-token",
            folder_id="folder-001",
            name="Wiki.md",
            mime_type="text/markdown",
            content="# Wiki",
            existing_file_id="wiki-file-001",
        )

    assert result.file_id == "wiki-file-001"
    service.files.return_value.update.assert_called_once()
    service.files.return_value.create.assert_not_called()


def test_upload_or_replace_text_file_returns_web_view_link():
    service = _drive_service()
    service.files.return_value.create.return_value.execute.return_value = {
        "id": "wiki-file-001",
        "webViewLink": "https://drive.google.com/file/d/wiki-file-001/view",
    }

    with patch("sadify_api.services.drive_client.build", return_value=service):
        result = _client().upload_or_replace_text_file(
            access_token="access-token",
            folder_id="folder-001",
            name="Wiki.md",
            mime_type="text/markdown",
            content="# Wiki",
            existing_file_id=None,
        )

    assert result.web_view_link == "https://drive.google.com/file/d/wiki-file-001/view"


def test_text_helpers_propagate_drive_errors_as_drive_text_file_error():
    service = _drive_service()
    service.files.return_value.list.return_value.execute.side_effect = RuntimeError(
        "drive failed"
    )

    with patch("sadify_api.services.drive_client.build", return_value=service):
        with pytest.raises(DriveTextFileError):
            _client().find_file_in_folder(
                access_token="access-token",
                folder_id="folder-001",
                name="Wiki.md",
            )


def _client() -> DriveClient:
    return DriveClient(client_id="client-id", client_secret="client-secret")


def _drive_service() -> MagicMock:
    return MagicMock()
