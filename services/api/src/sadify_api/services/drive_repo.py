from datetime import UTC, datetime
from typing import Protocol

from sadify_api.schemas import (
    DriveRepoConnectRequest,
    DriveRepoFolder,
    DriveRepoRecord,
    ProjectSummary,
)
from sadify_api.services.drive_client import (
    DRIVE_FILE_SCOPE,
    DriveClient,
    DriveFolderCreateError,
    DriveOauthExchangeError,
)
from sadify_api.services.firestore_client import (
    next_counter,
    safe_doc_id,
    snapshot_data,
)
from sadify_api.services.secret_store import SecretStore


class DriveTokenPersistError(Exception):
    pass


class DriveRepoRepositoryProtocol(Protocol):
    def connect_repo(
        self,
        *,
        owner_uid: str,
        owner_email: str | None,
        request: DriveRepoConnectRequest,
        connected_at: datetime | None = None,
        mode: str = "local",
        drive_client: DriveClient | None = None,
        secret_store: SecretStore | None = None,
        drive_folder_name: str = "SADify Projects",
    ) -> DriveRepoRecord: ...

    def disconnect_repo(
        self,
        *,
        owner_uid: str,
        disconnected_at: datetime | None = None,
    ) -> DriveRepoRecord | None: ...

    def get_active_repo(self, owner_uid: str) -> DriveRepoRecord | None: ...

    def get_latest_repo(self, owner_uid: str) -> DriveRepoRecord | None: ...

    def set_active_project(
        self,
        *,
        grant_id: str,
        project: ProjectSummary,
        updated_at: datetime | None = None,
    ) -> DriveRepoRecord: ...

    def set_available_projects(
        self,
        *,
        grant_id: str,
        projects: list[ProjectSummary],
        updated_at: datetime | None = None,
    ) -> DriveRepoRecord: ...

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
        mode: str = "local",
        drive_client: DriveClient | None = None,
        secret_store: SecretStore | None = None,
        drive_folder_name: str = "SADify Projects",
    ) -> DriveRepoRecord:
        now = connected_at or datetime.now(UTC)
        if mode == "live":
            return self._connect_live_repo(
                owner_uid=owner_uid,
                owner_email=owner_email,
                request=request,
                connected_at=now,
                drive_client=drive_client,
                secret_store=secret_store,
                drive_folder_name=drive_folder_name,
            )

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

    def _connect_live_repo(
        self,
        *,
        owner_uid: str,
        owner_email: str | None,
        request: DriveRepoConnectRequest,
        connected_at: datetime,
        drive_client: DriveClient | None,
        secret_store: SecretStore | None,
        drive_folder_name: str,
    ) -> DriveRepoRecord:
        if drive_client is None or secret_store is None:
            raise DriveOauthExchangeError("Live Drive dependencies are not configured.")

        tokens = drive_client.exchange_authorization_code(
            request.authorization_code,
            "postmessage",
        )
        if not tokens.refresh_token:
            raise DriveOauthExchangeError("Google did not return a refresh token.")

        try:
            secret_store.put_user_refresh_token(owner_uid, tokens.refresh_token)
        except Exception as exc:
            raise DriveTokenPersistError(
                "Could not securely store Drive refresh token."
            ) from exc

        folder = drive_client.find_or_create_folder(
            tokens.access_token,
            drive_folder_name,
        )
        grant_id = f"DG-{self._next_grant_number:06d}"
        self._next_grant_number += 1

        existing_active = self.get_active_repo(owner_uid)
        if existing_active:
            self.disconnect_repo(owner_uid=owner_uid, disconnected_at=connected_at)

        record = DriveRepoRecord(
            grant_id=grant_id,
            project_id=request.project_id,
            owner_uid=owner_uid,
            owner_email=owner_email,
            status="connected",
            repo_folder_id=folder.folder_id,
            repo_folder_name=folder.name,
            repo_url=f"https://drive.google.com/drive/folders/{folder.folder_id}",
            requested_scopes=[DRIVE_FILE_SCOPE],
            folder_structure=list(DEFAULT_PROJECT_REPO_STRUCTURE),
            token_store="secret_manager",
            saves_blocked=False,
            created_at=connected_at,
            updated_at=connected_at,
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

    def get_latest_repo(self, owner_uid: str) -> DriveRepoRecord | None:
        active = self.get_active_repo(owner_uid)
        if active:
            return active
        owned_records = [
            record
            for record in self._records.values()
            if record.owner_uid == owner_uid
        ]
        if not owned_records:
            return None
        return max(owned_records, key=lambda record: record.updated_at)

    def set_active_project(
        self,
        *,
        grant_id: str,
        project: ProjectSummary,
        updated_at: datetime | None = None,
    ) -> DriveRepoRecord:
        record = self._records[grant_id]
        projects = _replace_project(record.available_projects, project)
        updated = record.model_copy(
            update={
                "active_project_id": project.project_id,
                "active_project_name": project.name,
                "available_projects": projects,
                "updated_at": updated_at or datetime.now(UTC),
            }
        )
        self._records[grant_id] = updated
        return updated

    def set_available_projects(
        self,
        *,
        grant_id: str,
        projects: list[ProjectSummary],
        updated_at: datetime | None = None,
    ) -> DriveRepoRecord:
        record = self._records[grant_id]
        updated = record.model_copy(
            update={
                "available_projects": list(projects),
                "updated_at": updated_at or datetime.now(UTC),
            }
        )
        self._records[grant_id] = updated
        return updated


class FirestoreDriveRepoRepository:
    def __init__(self, client) -> None:
        self._client = client

    def connect_repo(
        self,
        *,
        owner_uid: str,
        owner_email: str | None,
        request: DriveRepoConnectRequest,
        connected_at: datetime | None = None,
        mode: str = "local",
        drive_client: DriveClient | None = None,
        secret_store: SecretStore | None = None,
        drive_folder_name: str = "SADify Projects",
    ) -> DriveRepoRecord:
        now = connected_at or datetime.now(UTC)
        if mode == "live":
            return self._connect_live_repo(
                owner_uid=owner_uid,
                owner_email=owner_email,
                request=request,
                connected_at=now,
                drive_client=drive_client,
                secret_store=secret_store,
                drive_folder_name=drive_folder_name,
            )

        grant_id = f"DG-{self._next_grant_number():06d}"
        repo_folder_id = request.repo_folder_id
        if request.create_new_repo and not repo_folder_id:
            repo_folder_id = f"LOCAL-DRIVE-FOLDER-{self._next_local_folder_number():06d}"
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
        self._store_record(record, active=True)
        return record

    def _connect_live_repo(
        self,
        *,
        owner_uid: str,
        owner_email: str | None,
        request: DriveRepoConnectRequest,
        connected_at: datetime,
        drive_client: DriveClient | None,
        secret_store: SecretStore | None,
        drive_folder_name: str,
    ) -> DriveRepoRecord:
        if drive_client is None or secret_store is None:
            raise DriveOauthExchangeError("Live Drive dependencies are not configured.")

        tokens = drive_client.exchange_authorization_code(
            request.authorization_code,
            "postmessage",
        )
        if not tokens.refresh_token:
            raise DriveOauthExchangeError("Google did not return a refresh token.")

        try:
            secret_store.put_user_refresh_token(owner_uid, tokens.refresh_token)
        except Exception as exc:
            raise DriveTokenPersistError(
                "Could not securely store Drive refresh token."
            ) from exc

        try:
            folder = drive_client.find_or_create_folder(
                tokens.access_token,
                drive_folder_name,
            )
        except DriveFolderCreateError:
            raise

        grant_id = f"DG-{self._next_grant_number():06d}"
        existing_active = self.get_active_repo(owner_uid)
        if existing_active:
            self.disconnect_repo(owner_uid=owner_uid, disconnected_at=connected_at)

        record = DriveRepoRecord(
            grant_id=grant_id,
            project_id=request.project_id,
            owner_uid=owner_uid,
            owner_email=owner_email,
            status="connected",
            repo_folder_id=folder.folder_id,
            repo_folder_name=folder.name,
            repo_url=f"https://drive.google.com/drive/folders/{folder.folder_id}",
            requested_scopes=[DRIVE_FILE_SCOPE],
            folder_structure=list(DEFAULT_PROJECT_REPO_STRUCTURE),
            token_store="secret_manager",
            saves_blocked=False,
            created_at=connected_at,
            updated_at=connected_at,
        )
        self._store_record(record, active=True)
        return record

    def disconnect_repo(
        self,
        *,
        owner_uid: str,
        disconnected_at: datetime | None = None,
    ) -> DriveRepoRecord | None:
        existing = self.get_active_repo(owner_uid)
        if existing is None:
            return None
        now = disconnected_at or datetime.now(UTC)
        disconnected = existing.model_copy(
            update={
                "status": "disconnected",
                "saves_blocked": True,
                "updated_at": now,
                "disconnected_at": now,
            }
        )
        self._store_record(disconnected, active=False)
        return disconnected

    def get_active_repo(self, owner_uid: str) -> DriveRepoRecord | None:
        snapshots = (
            self._client.collection("drive_repos")
            .where("owner_uid", "==", owner_uid)
            .where("active", "==", True)
            .stream()
        )
        records = [
            record
            for record in (self._record_from_snapshot(snapshot) for snapshot in snapshots)
            if record is not None
            and record.status == "connected"
            and record.saves_blocked is False
        ]
        if not records:
            return None
        return max(records, key=lambda record: record.updated_at)

    def get_latest_repo(self, owner_uid: str) -> DriveRepoRecord | None:
        active = self.get_active_repo(owner_uid)
        if active is not None:
            return active
        snapshots = (
            self._client.collection("drive_repos")
            .where("owner_uid", "==", owner_uid)
            .stream()
        )
        records = [
            record
            for record in (self._record_from_snapshot(snapshot) for snapshot in snapshots)
            if record is not None
        ]
        if not records:
            return None
        return max(records, key=lambda record: record.updated_at)

    def set_active_project(
        self,
        *,
        grant_id: str,
        project: ProjectSummary,
        updated_at: datetime | None = None,
    ) -> DriveRepoRecord:
        record = self._get_by_grant_id(grant_id)
        if record is None:
            raise KeyError(grant_id)
        projects = _replace_project(record.available_projects, project)
        updated = record.model_copy(
            update={
                "active_project_id": project.project_id,
                "active_project_name": project.name,
                "available_projects": projects,
                "updated_at": updated_at or datetime.now(UTC),
            }
        )
        self._store_record(updated, active=self._is_active(grant_id))
        return updated

    def set_available_projects(
        self,
        *,
        grant_id: str,
        projects: list[ProjectSummary],
        updated_at: datetime | None = None,
    ) -> DriveRepoRecord:
        record = self._get_by_grant_id(grant_id)
        if record is None:
            raise KeyError(grant_id)
        updated = record.model_copy(
            update={
                "available_projects": list(projects),
                "updated_at": updated_at or datetime.now(UTC),
            }
        )
        self._store_record(updated, active=self._is_active(grant_id))
        return updated

    def _store_record(self, record: DriveRepoRecord, *, active: bool) -> None:
        self._repo_ref(record.grant_id).set(
            {
                **record.model_dump(mode="json"),
                "active": active,
            }
        )

    def _record_from_snapshot(self, snapshot) -> DriveRepoRecord | None:
        data = snapshot_data(snapshot)
        if data is None:
            return None
        data.pop("active", None)
        return DriveRepoRecord.model_validate(data)

    def _get_by_grant_id(self, grant_id: str) -> DriveRepoRecord | None:
        return self._record_from_snapshot(self._repo_ref(grant_id).get())

    def _is_active(self, grant_id: str) -> bool:
        data = snapshot_data(self._repo_ref(grant_id).get())
        return bool(data and data.get("active") is True)

    def _repo_ref(self, grant_id: str):
        return self._client.collection("drive_repos").document(safe_doc_id(grant_id))

    def _next_grant_number(self) -> int:
        return next_counter(self._client, "drive_repo", "grant")

    def _next_local_folder_number(self) -> int:
        return next_counter(self._client, "drive_repo", "local_folder")


def _replace_project(
    projects: list[ProjectSummary],
    project: ProjectSummary,
) -> list[ProjectSummary]:
    replaced = False
    result: list[ProjectSummary] = []
    for item in projects:
        if item.project_id == project.project_id:
            result.append(project)
            replaced = True
        else:
            result.append(item)
    if not replaced:
        result.append(project)
    return result
