from datetime import UTC, datetime

import pytest

from sadify_api.services.drive_client import (
    DriveFileRef,
    DriveFolder,
    DriveTextFileError,
    DriveUploadResult,
)
from sadify_api.services.wiki_backup import (
    WikiBackupError,
    snapshot_existing_wiki_files,
)


def test_backup_returns_skipped_when_no_remote_files():
    client = FakeDriveClient()

    backup = snapshot_existing_wiki_files(
        drive_client=client,
        access_token="access-token",
        repo_folder_id="repo-folder-001",
        existing_files=[],
        now=_now(),
    )

    assert backup.created is False
    assert backup.path == ""
    assert backup.file_count == 0
    assert client.folder_calls == []
    assert client.upload_calls == []


def test_backup_creates_timestamped_subfolder_in_sadify_wiki_backups():
    client = FakeDriveClient()

    snapshot_existing_wiki_files(
        drive_client=client,
        access_token="access-token",
        repo_folder_id="repo-folder-001",
        existing_files=[_file("Wiki.md")],
        now=_now(),
    )

    assert client.folder_calls == [
        ("_SADify", "repo-folder-001"),
        ("wiki-backups", "folder-_SADify"),
        ("2026-05-27T10-15-30Z", "folder-wiki-backups"),
    ]


def test_backup_copies_each_existing_remote_md_into_subfolder():
    client = FakeDriveClient()
    existing = [
        _file("Wiki.md", file_id="wiki-file-001"),
        _file("requirements.md", file_id="requirements-file-001"),
    ]

    snapshot_existing_wiki_files(
        drive_client=client,
        access_token="access-token",
        repo_folder_id="repo-folder-001",
        existing_files=existing,
        now=_now(),
    )

    assert client.download_calls == ["wiki-file-001", "requirements-file-001"]
    assert client.upload_calls == [
        ("folder-2026-05-27T10-15-30Z", "Wiki.md", "# Backup for wiki-file-001"),
        (
            "folder-2026-05-27T10-15-30Z",
            "requirements.md",
            "# Backup for requirements-file-001",
        ),
    ]


def test_backup_returns_metadata_with_path_and_file_count():
    client = FakeDriveClient()

    backup = snapshot_existing_wiki_files(
        drive_client=client,
        access_token="access-token",
        repo_folder_id="repo-folder-001",
        existing_files=[_file("Wiki.md"), _file("actors.md")],
        now=_now(),
    )

    assert backup.created is True
    assert backup.path == "_SADify/wiki-backups/2026-05-27T10-15-30Z/"
    assert backup.file_count == 2


def test_backup_propagates_drive_error_as_wiki_backup_error():
    client = FakeDriveClient(download_error=True)

    with pytest.raises(WikiBackupError):
        snapshot_existing_wiki_files(
            drive_client=client,
            access_token="access-token",
            repo_folder_id="repo-folder-001",
            existing_files=[_file("Wiki.md")],
            now=_now(),
        )


def _file(name: str, *, file_id: str | None = None) -> DriveFileRef:
    return DriveFileRef(
        file_id=file_id or f"{name}-file",
        name=name,
        mime_type="text/markdown",
        web_view_link=f"https://drive.google.com/file/d/{name}/view",
        md5_checksum="remote-md5",
    )


def _now() -> datetime:
    return datetime(2026, 5, 27, 10, 15, 30, tzinfo=UTC)


class FakeDriveClient:
    def __init__(self, *, download_error: bool = False) -> None:
        self.download_error = download_error
        self.folder_calls: list[tuple[str, str | None]] = []
        self.download_calls: list[str] = []
        self.upload_calls: list[tuple[str, str, str]] = []

    def find_or_create_folder(
        self,
        access_token: str,
        folder_name: str,
        parent_folder_id: str | None = None,
    ) -> DriveFolder:
        self.folder_calls.append((folder_name, parent_folder_id))
        return DriveFolder(folder_id=f"folder-{folder_name}", name=folder_name)

    def download_text_file(self, *, access_token: str, file_id: str) -> str:
        if self.download_error:
            raise DriveTextFileError("drive failed")
        self.download_calls.append(file_id)
        return f"# Backup for {file_id}"

    def upload_or_replace_text_file(
        self,
        *,
        access_token: str,
        folder_id: str,
        name: str,
        mime_type: str,
        content: str,
        existing_file_id: str | None = None,
    ) -> DriveUploadResult:
        self.upload_calls.append((folder_id, name, content))
        return DriveUploadResult(
            file_id=f"backup-{name}",
            web_view_link=f"https://drive.google.com/file/d/backup-{name}/view",
        )
