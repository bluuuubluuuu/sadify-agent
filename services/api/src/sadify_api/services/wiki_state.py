from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sadify_api.services.firestore_client import safe_doc_id, snapshot_data


@dataclass(frozen=True)
class WikiState:
    file_name: str
    file_id: str
    hash: str
    updated_at: datetime


class WikiStateRepositoryProtocol(Protocol):
    def get_file_state(
        self,
        repo_grant_id: str,
        project_id: str,
        file_name: str,
    ) -> WikiState | None: ...

    def get_all_states(
        self,
        repo_grant_id: str,
        project_id: str,
    ) -> dict[str, WikiState]: ...

    def record_file_write(
        self,
        repo_grant_id: str,
        project_id: str,
        state: WikiState,
    ) -> None: ...

    def clear_states_for_project(self, repo_grant_id: str, project_id: str) -> None: ...


class WikiStateRepository:
    def __init__(self) -> None:
        self._states: dict[tuple[str, str, str], WikiState] = {}

    def get_file_state(
        self,
        repo_grant_id: str,
        project_id: str,
        file_name: str,
    ) -> WikiState | None:
        return self._states.get((repo_grant_id, project_id, file_name))

    def get_all_states(
        self,
        repo_grant_id: str,
        project_id: str,
    ) -> dict[str, WikiState]:
        return {
            file_name: state
            for (grant_id, stored_project_id, file_name), state in self._states.items()
            if grant_id == repo_grant_id and stored_project_id == project_id
        }

    def record_file_write(
        self,
        repo_grant_id: str,
        project_id: str,
        state: WikiState,
    ) -> None:
        self._states[(repo_grant_id, project_id, state.file_name)] = state

    def clear_states_for_project(self, repo_grant_id: str, project_id: str) -> None:
        for key in list(self._states):
            if key[0] == repo_grant_id and key[1] == project_id:
                del self._states[key]


class FirestoreWikiStateRepository:
    def __init__(self, client) -> None:
        self._client = client

    def get_file_state(
        self,
        repo_grant_id: str,
        project_id: str,
        file_name: str,
    ) -> WikiState | None:
        data = snapshot_data(
            self._state_ref(repo_grant_id, project_id, file_name).get()
        )
        if data is None:
            return None
        return _state_from_data(data)

    def get_all_states(
        self,
        repo_grant_id: str,
        project_id: str,
    ) -> dict[str, WikiState]:
        snapshots = (
            self._client.collection("wiki_state")
            .where("repo_grant_id", "==", repo_grant_id)
            .where("project_id", "==", project_id)
            .stream()
        )
        states = [_state_from_data(snapshot.to_dict()) for snapshot in snapshots]
        return {state.file_name: state for state in states}

    def record_file_write(
        self,
        repo_grant_id: str,
        project_id: str,
        state: WikiState,
    ) -> None:
        self._state_ref(repo_grant_id, project_id, state.file_name).set(
            {
                "repo_grant_id": repo_grant_id,
                "project_id": project_id,
                "file_name": state.file_name,
                "file_id": state.file_id,
                "hash": state.hash,
                "updated_at": state.updated_at.isoformat(),
            }
        )

    def clear_states_for_project(self, repo_grant_id: str, project_id: str) -> None:
        snapshots = (
            self._client.collection("wiki_state")
            .where("repo_grant_id", "==", repo_grant_id)
            .where("project_id", "==", project_id)
            .stream()
        )
        for snapshot in snapshots:
            self._client.collection("wiki_state").document(snapshot.id).delete()

    def _state_ref(self, repo_grant_id: str, project_id: str, file_name: str):
        return self._client.collection("wiki_state").document(
            safe_doc_id(repo_grant_id, project_id, file_name)
        )


def _state_from_data(data: dict) -> WikiState:
    updated_at = data["updated_at"]
    if isinstance(updated_at, str):
        updated_at = datetime.fromisoformat(updated_at)
    return WikiState(
        file_name=str(data["file_name"]),
        file_id=str(data["file_id"]),
        hash=str(data["hash"]),
        updated_at=updated_at,
    )


_wiki_state_repository = WikiStateRepository()


def get_wiki_state_repository() -> WikiStateRepository:
    return _wiki_state_repository
