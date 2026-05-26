from datetime import UTC, datetime

from sadify_api.services.wiki_state import WikiStateRepository


def test_get_state_returns_none_when_unset():
    repository = WikiStateRepository()

    assert repository.get_state("DG-000001") is None


def test_record_write_persists_hash_and_timestamp():
    repository = WikiStateRepository()
    updated_at = datetime(2026, 5, 26, 10, 0, tzinfo=UTC)

    repository.record_write(
        "DG-000001",
        file_id="wiki-file-001",
        hash_value="sha256:abc",
        updated_at=updated_at,
    )

    state = repository.get_state("DG-000001")
    assert state is not None
    assert state.file_id == "wiki-file-001"
    assert state.hash == "sha256:abc"
    assert state.updated_at == updated_at


def test_record_write_replaces_prior_state_for_same_repo():
    repository = WikiStateRepository()

    repository.record_write(
        "DG-000001",
        file_id="wiki-file-001",
        hash_value="sha256:abc",
        updated_at=datetime(2026, 5, 26, 10, 0, tzinfo=UTC),
    )
    repository.record_write(
        "DG-000001",
        file_id="wiki-file-002",
        hash_value="sha256:def",
        updated_at=datetime(2026, 5, 26, 11, 0, tzinfo=UTC),
    )

    state = repository.get_state("DG-000001")
    assert state is not None
    assert state.file_id == "wiki-file-002"
    assert state.hash == "sha256:def"


def test_independent_state_per_repo_grant_id():
    repository = WikiStateRepository()

    repository.record_write(
        "DG-000001",
        file_id="wiki-file-001",
        hash_value="sha256:abc",
        updated_at=datetime(2026, 5, 26, 10, 0, tzinfo=UTC),
    )
    repository.record_write(
        "DG-000002",
        file_id="wiki-file-002",
        hash_value="sha256:def",
        updated_at=datetime(2026, 5, 26, 11, 0, tzinfo=UTC),
    )

    assert repository.get_state("DG-000001").hash == "sha256:abc"
    assert repository.get_state("DG-000002").hash == "sha256:def"
