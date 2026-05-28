from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class WikiState:
    file_name: str
    file_id: str
    hash: str
    updated_at: datetime


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


_wiki_state_repository = WikiStateRepository()


def get_wiki_state_repository() -> WikiStateRepository:
    return _wiki_state_repository
