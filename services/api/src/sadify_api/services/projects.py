from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import re
from typing import Protocol

from sadify_api.schemas import ProjectSummary
from sadify_api.services.drive_client import DriveFolderRef
from sadify_api.services.firestore_client import (
    next_counter,
    next_counter_in_transaction,
    run_in_transaction,
    safe_doc_id,
    snapshot_data,
)

ProjectRecord = ProjectSummary


class ProjectRepositoryProtocol(Protocol):
    def create_project(
        self,
        *,
        grant_id: str,
        name: str,
        drive_folder_id: str,
        created_at: datetime | None = None,
    ) -> ProjectRecord: ...

    def create_local_project(
        self,
        *,
        grant_id: str,
        name: str,
        created_at: datetime | None = None,
    ) -> ProjectRecord: ...

    def get_project(self, grant_id: str, project_id: str) -> ProjectRecord | None: ...

    def get_project_by_name(self, grant_id: str, name: str) -> ProjectRecord | None: ...

    def list_projects(self, grant_id: str) -> list[ProjectRecord]: ...

    def sync_from_drive(
        self,
        *,
        grant_id: str,
        drive_folders: list[DriveFolderRef],
    ) -> list[ProjectRecord]: ...

    def next_counter(self, grant_id: str, project_id: str, counter_name: str) -> int: ...

    def set_github_repo(
        self, grant_id: str, project_id: str, repo: str
    ) -> ProjectRecord | None: ...


class ProjectRepository:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], ProjectRecord] = {}
        self._order_by_grant: dict[str, list[str]] = {}
        self._next_project_number_by_grant: dict[str, int] = {}
        self._next_local_folder_number_by_grant: dict[str, int] = {}
        self._counters: dict[tuple[str, str, str], int] = {}

    def create_project(
        self,
        *,
        grant_id: str,
        name: str,
        drive_folder_id: str,
        created_at: datetime | None = None,
    ) -> ProjectRecord:
        existing = self.get_project_by_name(grant_id, name)
        if existing is not None:
            return existing

        project_id = f"PR-{self._next_project_number(grant_id):06d}"
        record = ProjectRecord(
            project_id=project_id,
            name=name.strip(),
            drive_folder_id=drive_folder_id,
            created_at=created_at or datetime.now(UTC),
        )
        self._records[(grant_id, project_id)] = record
        self._order_by_grant.setdefault(grant_id, []).append(project_id)
        return record

    def create_local_project(
        self,
        *,
        grant_id: str,
        name: str,
        created_at: datetime | None = None,
    ) -> ProjectRecord:
        existing = self.get_project_by_name(grant_id, name)
        if existing is not None:
            return existing
        folder_id = (
            f"LOCAL-PROJECT-FOLDER-{self._next_local_folder_number(grant_id):06d}"
        )
        return self.create_project(
            grant_id=grant_id,
            name=name,
            drive_folder_id=folder_id,
            created_at=created_at,
        )

    def get_project(self, grant_id: str, project_id: str) -> ProjectRecord | None:
        return self._records.get((grant_id, project_id))

    def get_project_by_name(self, grant_id: str, name: str) -> ProjectRecord | None:
        normalized = _normalize_name(name)
        for project in self.list_projects(grant_id):
            if _normalize_name(project.name) == normalized:
                return project
        return None

    def list_projects(self, grant_id: str) -> list[ProjectRecord]:
        return [
            self._records[(grant_id, project_id)]
            for project_id in self._order_by_grant.get(grant_id, [])
        ]

    def sync_from_drive(
        self,
        *,
        grant_id: str,
        drive_folders: list[DriveFolderRef],
    ) -> list[ProjectRecord]:
        existing_by_folder_id = {
            project.drive_folder_id: project
            for project in self.list_projects(grant_id)
        }
        for folder in drive_folders:
            if folder.folder_id in existing_by_folder_id:
                continue
            self.create_project(
                grant_id=grant_id,
                name=folder.name,
                drive_folder_id=folder.folder_id,
                created_at=folder.created_time,
            )
        return self.list_projects(grant_id)

    def next_counter(self, grant_id: str, project_id: str, counter_name: str) -> int:
        key = (grant_id, project_id, counter_name)
        value = self._counters.get(key, 1)
        self._counters[key] = value + 1
        return value

    def set_github_repo(
        self, grant_id: str, project_id: str, repo: str
    ) -> ProjectRecord | None:
        record = self.get_project(grant_id, project_id)
        if record is None:
            return None
        updated = record.model_copy(update={"github_repo": repo})
        self._records[(grant_id, project_id)] = updated
        return updated

    def _next_project_number(self, grant_id: str) -> int:
        value = self._next_project_number_by_grant.get(grant_id, 1)
        self._next_project_number_by_grant[grant_id] = value + 1
        return value

    def _next_local_folder_number(self, grant_id: str) -> int:
        value = self._next_local_folder_number_by_grant.get(grant_id, 1)
        self._next_local_folder_number_by_grant[grant_id] = value + 1
        return value


class FirestoreProjectRepository:
    def __init__(self, client) -> None:
        self._client = client

    def create_project(
        self,
        *,
        grant_id: str,
        name: str,
        drive_folder_id: str,
        created_at: datetime | None = None,
    ) -> ProjectRecord:
        clean_name = name.strip()
        index_ref = self._name_index_ref(grant_id, clean_name)

        def _create(transaction) -> ProjectRecord:
            index_data = snapshot_data(index_ref.get(transaction=transaction))
            if index_data:
                existing = self.get_project(grant_id, str(index_data["project_id"]))
                if existing is not None:
                    return existing

            project_number = next_counter_in_transaction(
                self._client,
                transaction,
                "project",
                grant_id,
                "project",
            )
            project_id = f"PR-{project_number:06d}"
            record = ProjectRecord(
                project_id=project_id,
                name=clean_name,
                drive_folder_id=drive_folder_id,
                created_at=created_at or datetime.now(UTC),
            )
            transaction.set(
                self._project_ref(grant_id, project_id),
                {
                    **record.model_dump(mode="json"),
                    "grant_id": grant_id,
                    "order": project_number,
                },
            )
            transaction.set(
                index_ref,
                {
                    "grant_id": grant_id,
                    "normalized_name": _normalize_name(clean_name),
                    "project_id": project_id,
                    "project_doc_id": self._project_doc_id(grant_id, project_id),
                },
            )
            return record

        return run_in_transaction(self._client, _create)

    def create_local_project(
        self,
        *,
        grant_id: str,
        name: str,
        created_at: datetime | None = None,
    ) -> ProjectRecord:
        existing = self.get_project_by_name(grant_id, name)
        if existing is not None:
            return existing
        folder_number = next_counter(
            self._client,
            "project",
            grant_id,
            "local_folder",
        )
        return self.create_project(
            grant_id=grant_id,
            name=name,
            drive_folder_id=f"LOCAL-PROJECT-FOLDER-{folder_number:06d}",
            created_at=created_at,
        )

    def get_project(self, grant_id: str, project_id: str) -> ProjectRecord | None:
        data = snapshot_data(self._project_ref(grant_id, project_id).get())
        if data is None:
            return None
        return _project_from_data(data)

    def get_project_by_name(self, grant_id: str, name: str) -> ProjectRecord | None:
        data = snapshot_data(self._name_index_ref(grant_id, name).get())
        if data is None:
            return None
        return self.get_project(grant_id, str(data["project_id"]))

    def list_projects(self, grant_id: str) -> list[ProjectRecord]:
        snapshots = (
            self._client.collection("projects")
            .where("grant_id", "==", grant_id)
            .stream()
        )
        rows = [snapshot.to_dict() for snapshot in snapshots]
        rows.sort(key=lambda row: int(row.get("order", 0)))
        return [_project_from_data(row) for row in rows]

    def sync_from_drive(
        self,
        *,
        grant_id: str,
        drive_folders: list[DriveFolderRef],
    ) -> list[ProjectRecord]:
        existing_by_folder_id = {
            project.drive_folder_id: project
            for project in self.list_projects(grant_id)
        }
        for folder in drive_folders:
            if folder.folder_id in existing_by_folder_id:
                continue
            self.create_project(
                grant_id=grant_id,
                name=folder.name,
                drive_folder_id=folder.folder_id,
                created_at=folder.created_time,
            )
        return self.list_projects(grant_id)

    def next_counter(self, grant_id: str, project_id: str, counter_name: str) -> int:
        return next_counter(
            self._client,
            "project",
            grant_id,
            project_id,
            counter_name,
        )

    def set_github_repo(
        self, grant_id: str, project_id: str, repo: str
    ) -> ProjectRecord | None:
        ref = self._project_ref(grant_id, project_id)
        data = snapshot_data(ref.get())
        if data is None:
            return None
        ref.set({"github_repo": repo}, merge=True)
        return _project_from_data({**data, "github_repo": repo})

    def _project_ref(self, grant_id: str, project_id: str):
        return self._client.collection("projects").document(
            self._project_doc_id(grant_id, project_id)
        )

    def _name_index_ref(self, grant_id: str, name: str):
        return self._client.collection("project_name_index").document(
            safe_doc_id(grant_id, _name_digest(name))
        )

    def _project_doc_id(self, grant_id: str, project_id: str) -> str:
        return safe_doc_id(grant_id, project_id)


def validate_project_name(value: str) -> str:
    clean = value.strip()
    if not clean or len(clean) > 80:
        raise ValueError("invalid project name")
    if not re.fullmatch(r"[A-Za-z0-9 _-]+", clean):
        raise ValueError("invalid project name")
    return clean


def validate_github_repo(value: str) -> str:
    clean = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", clean):
        raise ValueError("invalid GitHub repo (expected owner/name)")
    return clean


def _normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _name_digest(value: str) -> str:
    return sha256(_normalize_name(value).encode("utf-8")).hexdigest()


def _project_from_data(data: dict) -> ProjectRecord:
    return ProjectRecord.model_validate(
        {
            "project_id": data["project_id"],
            "name": data["name"],
            "drive_folder_id": data["drive_folder_id"],
            "created_at": data["created_at"],
            "github_repo": data.get("github_repo"),
        }
    )


_project_repository = ProjectRepository()


def get_project_repository() -> ProjectRepository:
    return _project_repository
