from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from sadify_api.services.drive_client import (
    DriveClient,
    DriveFolderCreateError,
)
from tests.api.test_drive_client import _drive_service


def test_list_subfolders_returns_empty_when_parent_has_no_subfolders():
    service = _drive_service()
    service.files.return_value.list.return_value.execute.return_value = {"files": []}

    with patch("sadify_api.services.drive_client.build", return_value=service):
        folders = DriveClient(
            client_id="client-id",
            client_secret="client-secret",
        ).list_subfolders(
            access_token="access-token",
            parent_folder_id="repo-folder-001",
        )

    assert folders == []
    list_call = service.files.return_value.list.call_args.kwargs
    assert "'repo-folder-001' in parents" in list_call["q"]
    assert "mimeType='application/vnd.google-apps.folder'" in list_call["q"]
    assert "trashed=false" in list_call["q"]


def test_list_subfolders_returns_folder_refs_with_id_name_created_time():
    service = _drive_service()
    service.files.return_value.list.return_value.execute.return_value = {
        "files": [
            {
                "id": "folder-late",
                "name": "Late Project",
                "mimeType": "application/vnd.google-apps.folder",
                "createdTime": "2026-05-28T11:00:00Z",
                "webViewLink": "https://drive.google.com/late",
            },
            {
                "id": "folder-early",
                "name": "Early Project",
                "mimeType": "application/vnd.google-apps.folder",
                "createdTime": "2026-05-28T10:00:00Z",
                "webViewLink": "https://drive.google.com/early",
            },
        ]
    }

    with patch("sadify_api.services.drive_client.build", return_value=service):
        folders = DriveClient(
            client_id="client-id",
            client_secret="client-secret",
        ).list_subfolders(
            access_token="access-token",
            parent_folder_id="repo-folder-001",
        )

    assert [folder.folder_id for folder in folders] == ["folder-early", "folder-late"]
    assert folders[0].name == "Early Project"
    assert folders[0].created_time == datetime(2026, 5, 28, 10, 0, tzinfo=UTC)
    assert folders[0].web_view_link == "https://drive.google.com/early"


def test_list_subfolders_ignores_files_only_returns_folders():
    service = _drive_service()
    service.files.return_value.list.return_value.execute.return_value = {
        "files": [
            {
                "id": "file-001",
                "name": "Not Folder",
                "mimeType": "text/markdown",
                "createdTime": "2026-05-28T10:00:00Z",
            },
            {
                "id": "folder-001",
                "name": "Project",
                "mimeType": "application/vnd.google-apps.folder",
                "createdTime": "2026-05-28T11:00:00Z",
            },
        ]
    }

    with patch("sadify_api.services.drive_client.build", return_value=service):
        folders = DriveClient(
            client_id="client-id",
            client_secret="client-secret",
        ).list_subfolders(
            access_token="access-token",
            parent_folder_id="repo-folder-001",
        )

    assert [folder.folder_id for folder in folders] == ["folder-001"]


def test_list_subfolders_excludes_trashed_folders():
    service = _drive_service()
    service.files.return_value.list.return_value.execute.return_value = {
        "files": [
            {
                "id": "folder-trashed",
                "name": "Trashed",
                "mimeType": "application/vnd.google-apps.folder",
                "trashed": True,
                "createdTime": "2026-05-28T10:00:00Z",
            },
            {
                "id": "folder-live",
                "name": "Live",
                "mimeType": "application/vnd.google-apps.folder",
                "trashed": False,
                "createdTime": "2026-05-28T11:00:00Z",
            },
        ]
    }

    with patch("sadify_api.services.drive_client.build", return_value=service):
        folders = DriveClient(
            client_id="client-id",
            client_secret="client-secret",
        ).list_subfolders(
            access_token="access-token",
            parent_folder_id="repo-folder-001",
        )

    assert [folder.folder_id for folder in folders] == ["folder-live"]


def test_list_subfolders_propagates_drive_error_as_drive_folder_create_error():
    service = _drive_service()
    service.files.return_value.list.return_value.execute.side_effect = RuntimeError(
        "drive failed"
    )

    with patch("sadify_api.services.drive_client.build", return_value=service):
        with pytest.raises(DriveFolderCreateError):
            DriveClient(
                client_id="client-id",
                client_secret="client-secret",
            ).list_subfolders(
                access_token="access-token",
                parent_folder_id="repo-folder-001",
            )
