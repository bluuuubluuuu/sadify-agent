from datetime import UTC, datetime

from sadify_api.schemas import (
    DriveRepoConnectRequest,
    DriveRepoFolder,
    DriveRepoRecord,
)


DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"

DEFAULT_PROJECT_REPO_STRUCTURE = [
    DriveRepoFolder(
        name="Sources",
        purpose="Original uploaded files. Never overwrite.",
    ),
    DriveRepoFolder(
        name="SAD",
        purpose="Versioned human-facing SAD Google Docs.",
    ),
    DriveRepoFolder(
        name="Wiki",
        purpose="Latest living project brain.",
    ),
    DriveRepoFolder(
        name="_SADify",
        purpose="Manifest, extraction text, backups, logs, and metadata.",
    ),
]


class DriveRepoRepository:
    def __init__(self) -> None:
        self._records: dict[str, DriveRepoRecord] = {}
        self._active_by_owner: dict[str, str] = {}
        self._next_grant_number = 1
        self._next_local_folder_number = 1

    def connect_repo(
        self,
        *,
        owner_uid: str,
        owner_email: str | None,
        request: DriveRepoConnectRequest,
        connected_at: datetime | None = None,
    ) -> DriveRepoRecord:
        now = connected_at or datetime.now(UTC)
        grant_id = f"DG-{self._next_grant_number:06d}"
        self._next_grant_number += 1
        repo_folder_id = request.repo_folder_id
        if request.create_new_repo and not repo_folder_id:
            repo_folder_id = f"LOCAL-DRIVE-FOLDER-{self._next_local_folder_number:06d}"
            self._next_local_folder_number += 1
        if not repo_folder_id:
            raise ValueError("Select an existing folder or create a new project repo.")

        existing_active = self.get_active_repo(owner_uid)
        if existing_active:
            self.disconnect_repo(owner_uid=owner_uid, disconnected_at=now)

        record = DriveRepoRecord(
            grant_id=grant_id,
            project_id=request.project_id,
            owner_uid=owner_uid,
            owner_email=owner_email,
            status="connected",
            repo_folder_id=repo_folder_id,
            repo_folder_name=request.repo_folder_name,
            repo_url=f"https://drive.google.com/drive/folders/{repo_folder_id}",
            requested_scopes=[DRIVE_FILE_SCOPE],
            folder_structure=list(DEFAULT_PROJECT_REPO_STRUCTURE),
            token_store="local_metadata_only",
            saves_blocked=False,
            created_at=now,
            updated_at=now,
        )
        self._records[grant_id] = record
        self._active_by_owner[owner_uid] = grant_id
        return record

    def disconnect_repo(
        self,
        *,
        owner_uid: str,
        disconnected_at: datetime | None = None,
    ) -> DriveRepoRecord | None:
        grant_id = self._active_by_owner.pop(owner_uid, None)
        if not grant_id:
            return None

        existing = self._records[grant_id]
        now = disconnected_at or datetime.now(UTC)
        disconnected = existing.model_copy(
            update={
                "status": "disconnected",
                "saves_blocked": True,
                "updated_at": now,
                "disconnected_at": now,
            }
        )
        self._records[grant_id] = disconnected
        return disconnected

    def get_active_repo(self, owner_uid: str) -> DriveRepoRecord | None:
        grant_id = self._active_by_owner.get(owner_uid)
        if not grant_id:
            return None
        return self._records.get(grant_id)
