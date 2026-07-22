from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from sadify_api.schemas import ProjectSessionSnapshot
from sadify_api.services.firestore_client import safe_doc_id, snapshot_data


class SessionSnapshotRepositoryProtocol(Protocol):
    def upsert(
        self,
        grant_id: str,
        project_id: str,
        snapshot: ProjectSessionSnapshot,
    ) -> ProjectSessionSnapshot: ...

    def get(
        self,
        grant_id: str,
        project_id: str,
    ) -> ProjectSessionSnapshot | None: ...

    def delete(self, grant_id: str, project_id: str) -> None: ...


class SessionSnapshotRepository:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], ProjectSessionSnapshot] = {}

    def upsert(
        self,
        grant_id: str,
        project_id: str,
        snapshot: ProjectSessionSnapshot,
    ) -> ProjectSessionSnapshot:
        stored = snapshot.model_copy(
            update={"updated_at": snapshot.updated_at or datetime.now(UTC)}
        )
        self._records[(grant_id, project_id)] = stored
        return stored

    def get(
        self,
        grant_id: str,
        project_id: str,
    ) -> ProjectSessionSnapshot | None:
        return self._records.get((grant_id, project_id))

    def delete(self, grant_id: str, project_id: str) -> None:
        self._records.pop((grant_id, project_id), None)


class FirestoreSessionSnapshotRepository:
    def __init__(self, client) -> None:
        self._client = client

    def _ref(self, grant_id: str, project_id: str):
        return self._client.collection("project_sessions").document(
            safe_doc_id(grant_id, project_id)
        )

    def upsert(
        self,
        grant_id: str,
        project_id: str,
        snapshot: ProjectSessionSnapshot,
    ) -> ProjectSessionSnapshot:
        stored = snapshot.model_copy(
            update={"updated_at": snapshot.updated_at or datetime.now(UTC)}
        )
        self._ref(grant_id, project_id).set(
            {
                **stored.model_dump(mode="json"),
                "grant_id": grant_id,
                "project_id": project_id,
            }
        )
        return stored

    def get(
        self,
        grant_id: str,
        project_id: str,
    ) -> ProjectSessionSnapshot | None:
        data = snapshot_data(self._ref(grant_id, project_id).get())
        if data is None:
            return None
        data.pop("grant_id", None)
        data.pop("project_id", None)
        return ProjectSessionSnapshot.model_validate(data)

    def delete(self, grant_id: str, project_id: str) -> None:
        self._ref(grant_id, project_id).delete()


_session_snapshot_repository = SessionSnapshotRepository()


def get_session_snapshot_repository() -> SessionSnapshotRepository:
    return _session_snapshot_repository
