from datetime import UTC, datetime, timedelta

import pytest

from sadify_api.schemas import GithubIssueDraft, GithubIssueSet
from sadify_api.services.github_issue_sets import (
    FirestoreGithubIssueSetRepository,
    GithubIssueSetRepository,
)
from tests.api.test_firestore_repositories import FakeFirestoreClient


@pytest.fixture(
    params=[
        GithubIssueSetRepository,
        lambda: FirestoreGithubIssueSetRepository(FakeFirestoreClient()),
    ],
    ids=["memory", "firestore"],
)
def repo(request):
    return request.param()


def _issue_set(
    *,
    project_id: str = "PR-1",
    save_id: str = "SV-1",
    github_repo: str = "acme/first",
    created_at: datetime | None = None,
) -> GithubIssueSet:
    now = created_at or datetime(2026, 6, 19, tzinfo=UTC)
    marker = f"<!-- sadify-github-issue:{project_id}:{save_id}:0 -->"
    return GithubIssueSet(
        grant_id="DRG-1",
        project_id=project_id,
        save_id=save_id,
        preview_id="SP-1",
        owner_uid="user-1",
        repo=github_repo,
        status="prepared",
        issues=[
            GithubIssueDraft(
                marker=marker,
                title="Create booking validation",
                body=f"Validate booking requests.\n\n{marker}",
                labels=["sadify"],
            )
        ],
        created_at=now,
        updated_at=now,
    )


def test_create_if_absent_locks_first_repo(repo):
    first = _issue_set(github_repo="acme/first")
    second = first.model_copy(update={"repo": "acme/second"})

    assert repo.create_if_absent(first).repo == "acme/first"
    assert repo.create_if_absent(second).repo == "acme/first"
    stored = repo.get("DRG-1", "PR-1", "SV-1")
    assert stored is not None
    assert stored.repo == "acme/first"


def test_get_returns_none_when_issue_set_is_missing(repo):
    assert repo.get("DRG-1", "PR-1", "SV-missing") is None


def test_list_for_project_is_scoped_and_ordered(repo):
    base = datetime(2026, 6, 19, tzinfo=UTC)
    repo.create_if_absent(_issue_set(save_id="SV-2", created_at=base + timedelta(seconds=1)))
    repo.create_if_absent(_issue_set(save_id="SV-1", created_at=base))
    repo.create_if_absent(_issue_set(project_id="PR-2", save_id="SV-1"))

    records = repo.list_for_project("DRG-1", "PR-1")

    assert [record.save_id for record in records] == ["SV-1", "SV-2"]


def test_delete_for_project_is_scoped_and_idempotent(repo):
    repo.create_if_absent(_issue_set(save_id="SV-1"))
    repo.create_if_absent(_issue_set(save_id="SV-2"))
    repo.create_if_absent(_issue_set(project_id="PR-2", save_id="SV-1"))

    assert repo.delete_for_project("DRG-1", "PR-1") == 2
    assert repo.delete_for_project("DRG-1", "PR-1") == 0
    assert repo.get("DRG-1", "PR-2", "SV-1") is not None
