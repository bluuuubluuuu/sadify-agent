from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sadify_api.services.drive_client import DriveClient, DriveFileRef

DEFAULT_WIKI_MIME_TYPE = "text/markdown"


class WikiBackupError(Exception):
    pass


@dataclass(frozen=True)
class WikiBackupInfo:
    created: bool
    path: str
    file_count: int


def snapshot_existing_wiki_files(
    *,
    drive_client: DriveClient,
    access_token: str,
    repo_folder_id: str,
    existing_files: list[DriveFileRef],
    backup_root_name: str = "_SADify",
    backups_subfolder_name: str = "wiki-backups",
    now: datetime | None = None,
) -> WikiBackupInfo:
    if not existing_files:
        return WikiBackupInfo(created=False, path="", file_count=0)

    timestamp = _timestamp(now or datetime.now(UTC))
    try:
        backup_root = drive_client.find_or_create_folder(
            access_token,
            backup_root_name,
            parent_folder_id=repo_folder_id,
        )
        backup_parent = drive_client.find_or_create_folder(
            access_token,
            backups_subfolder_name,
            parent_folder_id=backup_root.folder_id,
        )
        backup_target = drive_client.find_or_create_folder(
            access_token,
            timestamp,
            parent_folder_id=backup_parent.folder_id,
        )
        for file in existing_files:
            content = drive_client.download_text_file(
                access_token=access_token,
                file_id=file.file_id,
            )
            drive_client.upload_or_replace_text_file(
                access_token=access_token,
                folder_id=backup_target.folder_id,
                name=file.name,
                mime_type=file.mime_type or DEFAULT_WIKI_MIME_TYPE,
                content=content,
                existing_file_id=None,
            )
    except Exception as exc:
        raise WikiBackupError("Could not snapshot existing wiki files.") from exc

    return WikiBackupInfo(
        created=True,
        path=f"{backup_root_name}/{backups_subfolder_name}/{timestamp}/",
        file_count=len(existing_files),
    )


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
