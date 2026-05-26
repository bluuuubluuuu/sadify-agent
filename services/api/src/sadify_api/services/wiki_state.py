from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class WikiState:
    file_id: str
    hash: str
    updated_at: datetime


class WikiStateRepository:
    def __init__(self) -> None:
        self._states: dict[str, WikiState] = {}

    def get_state(self, repo_grant_id: str) -> WikiState | None:
        return self._states.get(repo_grant_id)

    def record_write(
        self,
        repo_grant_id: str,
        *,
        file_id: str,
        hash_value: str,
        updated_at: datetime,
    ) -> None:
        self._states[repo_grant_id] = WikiState(
            file_id=file_id,
            hash=hash_value,
            updated_at=updated_at,
        )


_wiki_state_repository = WikiStateRepository()


def get_wiki_state_repository() -> WikiStateRepository:
    return _wiki_state_repository
