from __future__ import annotations

from typing import Protocol

from sadify_api.schemas import GithubIssueSet
from sadify_api.services.firestore_client import (
    run_in_transaction,
    safe_doc_id,
    snapshot_data,
)


class GithubIssueSetRepositoryProtocol(Protocol):
    def create_if_absent(self, issue_set: GithubIssueSet) -> GithubIssueSet: ...

    def get(
        self,
        grant_id: str,
        project_id: str,
        save_id: str,
    ) -> GithubIssueSet | None: ...

    def list_for_project(
        self,
        grant_id: str,
        project_id: str,
    ) -> list[GithubIssueSet]: ...

    def delete_for_project(self, grant_id: str, project_id: str) -> int: ...


class GithubIssueSetRepository:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str], GithubIssueSet] = {}

    def create_if_absent(self, issue_set: GithubIssueSet) -> GithubIssueSet:
        key = (issue_set.grant_id, issue_set.project_id, issue_set.save_id)
        stored = self._records.get(key)
        if stored is not None:
            return stored
        self._records[key] = issue_set
        return issue_set

    def get(
        self,
        grant_id: str,
        project_id: str,
        save_id: str,
    ) -> GithubIssueSet | None:
        return self._records.get((grant_id, project_id, save_id))

    def list_for_project(
        self,
        grant_id: str,
        project_id: str,
    ) -> list[GithubIssueSet]:
        records = [
            record
            for (record_grant_id, record_project_id, _), record in self._records.items()
            if record_grant_id == grant_id and record_project_id == project_id
        ]
        return sorted(records, key=lambda record: (record.created_at, record.save_id))

    def delete_for_project(self, grant_id: str, project_id: str) -> int:
        keys = [
            key
            for key in self._records
            if key[0] == grant_id and key[1] == project_id
        ]
        for key in keys:
            del self._records[key]
        return len(keys)


class FirestoreGithubIssueSetRepository:
    def __init__(self, client) -> None:
        self._client = client

    def _ref(self, grant_id: str, project_id: str, save_id: str):
        return self._client.collection("github_issue_sets").document(
            safe_doc_id(grant_id, project_id, save_id)
        )

    def create_if_absent(self, issue_set: GithubIssueSet) -> GithubIssueSet:
        ref = self._ref(issue_set.grant_id, issue_set.project_id, issue_set.save_id)

        def _create(transaction) -> GithubIssueSet:
            data = snapshot_data(ref.get(transaction=transaction))
            if data is not None:
                return GithubIssueSet.model_validate(data)
            transaction.set(ref, issue_set.model_dump(mode="json"))
            return issue_set

        return run_in_transaction(self._client, _create)

    def get(
        self,
        grant_id: str,
        project_id: str,
        save_id: str,
    ) -> GithubIssueSet | None:
        data = snapshot_data(self._ref(grant_id, project_id, save_id).get())
        return GithubIssueSet.model_validate(data) if data is not None else None

    def list_for_project(
        self,
        grant_id: str,
        project_id: str,
    ) -> list[GithubIssueSet]:
        snapshots = (
            self._client.collection("github_issue_sets")
            .where("grant_id", "==", grant_id)
            .where("project_id", "==", project_id)
            .stream()
        )
        records = [GithubIssueSet.model_validate(snapshot.to_dict()) for snapshot in snapshots]
        return sorted(records, key=lambda record: (record.created_at, record.save_id))

    def delete_for_project(self, grant_id: str, project_id: str) -> int:
        records = self.list_for_project(grant_id, project_id)
        for record in records:
            self._ref(grant_id, project_id, record.save_id).delete()
        return len(records)


_github_issue_set_repository = GithubIssueSetRepository()


def get_github_issue_set_repository() -> GithubIssueSetRepository:
    return _github_issue_set_repository
