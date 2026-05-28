from __future__ import annotations

from datetime import UTC, datetime
import re

from sadify_api.schemas import ProjectSummary
from sadify_api.services.drive_client import DriveFolderRef

ProjectRecord = ProjectSummary


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

    def _next_project_number(self, grant_id: str) -> int:
        value = self._next_project_number_by_grant.get(grant_id, 1)
        self._next_project_number_by_grant[grant_id] = value + 1
        return value

    def _next_local_folder_number(self, grant_id: str) -> int:
        value = self._next_local_folder_number_by_grant.get(grant_id, 1)
        self._next_local_folder_number_by_grant[grant_id] = value + 1
        return value


def validate_project_name(value: str) -> str:
    clean = value.strip()
    if not clean or len(clean) > 80:
        raise ValueError("invalid project name")
    if not re.fullmatch(r"[A-Za-z0-9 _-]+", clean):
        raise ValueError("invalid project name")
    return clean


def _normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


_project_repository = ProjectRepository()


def get_project_repository() -> ProjectRepository:
    return _project_repository
