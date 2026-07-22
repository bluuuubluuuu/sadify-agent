import pytest

from sadify_api.schemas import ProjectSessionSnapshot
from sadify_api.services.session_state import (
    FirestoreSessionSnapshotRepository,
    SessionSnapshotRepository,
)
from tests.api.test_firestore_repositories import FakeFirestoreClient


@pytest.fixture(
    params=[
        SessionSnapshotRepository,
        lambda: FirestoreSessionSnapshotRepository(FakeFirestoreClient()),
    ],
    ids=["memory", "firestore"],
)
def repo(request):
    return request.param()


def _snapshot(text: str, updated_at=None) -> ProjectSessionSnapshot:
    return ProjectSessionSnapshot(
        clean_requirement_text=text,
        analysis_response=None,
        answer_history=[],
        source_context="",
        source_references=[],
        selected_model=None,
        status="in_progress",
        updated_at=updated_at,
    )


def test_upsert_overwrites_latest_snapshot(repo):
    repo.upsert("G1", "PR-000001", _snapshot("first"))
    repo.upsert("G1", "PR-000001", _snapshot("second"))
    stored = repo.get("G1", "PR-000001")
    assert stored is not None
    assert stored.clean_requirement_text == "second"


def test_upsert_stamps_updated_at_when_omitted(repo):
    repo.upsert("G1", "PR-000001", _snapshot("x", updated_at=None))
    stored = repo.get("G1", "PR-000001")
    assert stored is not None
    assert stored.updated_at is not None


def test_get_returns_none_when_absent(repo):
    assert repo.get("G1", "PR-000001") is None


def test_delete_removes_snapshot_and_is_idempotent(repo):
    repo.upsert("G1", "PR-000001", _snapshot("x"))
    repo.delete("G1", "PR-000001")
    repo.delete("G1", "PR-000001")
    assert repo.get("G1", "PR-000001") is None
