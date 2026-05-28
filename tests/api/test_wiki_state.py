from datetime import UTC, datetime

from sadify_api.services.wiki_state import WikiState, WikiStateRepository


def test_get_file_state_returns_none_when_unset():
    repository = WikiStateRepository()

    assert repository.get_file_state("DG-000001", "PR-000001", "Wiki.md") is None


def test_record_file_write_persists_hash_and_timestamp_per_file():
    repository = WikiStateRepository()
    updated_at = datetime(2026, 5, 27, 10, 0, tzinfo=UTC)

    repository.record_file_write(
        "DG-000001",
        "PR-000001",
        WikiState(
            file_name="requirements.md",
            file_id="requirements-file-001",
            hash="sha256:abc",
            updated_at=updated_at,
        ),
    )

    state = repository.get_file_state("DG-000001", "PR-000001", "requirements.md")
    assert state is not None
    assert state.file_name == "requirements.md"
    assert state.file_id == "requirements-file-001"
    assert state.hash == "sha256:abc"
    assert state.updated_at == updated_at


def test_record_file_write_replaces_only_that_file_state():
    repository = WikiStateRepository()
    first_time = datetime(2026, 5, 27, 10, 0, tzinfo=UTC)
    second_time = datetime(2026, 5, 27, 11, 0, tzinfo=UTC)

    repository.record_file_write(
        "DG-000001",
        "PR-000001",
        WikiState(
            file_name="requirements.md",
            file_id="requirements-file-001",
            hash="sha256:abc",
            updated_at=first_time,
        ),
    )
    repository.record_file_write(
        "DG-000001",
        "PR-000001",
        WikiState(
            file_name="actors.md",
            file_id="actors-file-001",
            hash="sha256:def",
            updated_at=first_time,
        ),
    )
    repository.record_file_write(
        "DG-000001",
        "PR-000001",
        WikiState(
            file_name="requirements.md",
            file_id="requirements-file-002",
            hash="sha256:updated",
            updated_at=second_time,
        ),
    )

    assert repository.get_file_state("DG-000001", "PR-000001", "requirements.md").hash == "sha256:updated"
    assert repository.get_file_state("DG-000001", "PR-000001", "actors.md").hash == "sha256:def"


def test_get_all_states_returns_known_files_for_repo():
    repository = WikiStateRepository()

    repository.record_file_write(
        "DG-000001",
        "PR-000001",
        WikiState(
            file_name="Wiki.md",
            file_id="wiki-file-001",
            hash="sha256:abc",
            updated_at=datetime(2026, 5, 27, 10, 0, tzinfo=UTC),
        ),
    )
    repository.record_file_write(
        "DG-000002",
        "PR-000001",
        WikiState(
            file_name="Wiki.md",
            file_id="other-wiki-file-001",
            hash="sha256:other",
            updated_at=datetime(2026, 5, 27, 10, 0, tzinfo=UTC),
        ),
    )
    repository.record_file_write(
        "DG-000001",
        "PR-000001",
        WikiState(
            file_name="actors.md",
            file_id="actors-file-001",
            hash="sha256:def",
            updated_at=datetime(2026, 5, 27, 10, 0, tzinfo=UTC),
        ),
    )

    states = repository.get_all_states("DG-000001", "PR-000001")

    assert set(states) == {"Wiki.md", "actors.md"}
    assert states["Wiki.md"].file_id == "wiki-file-001"
    assert states["actors.md"].hash == "sha256:def"


def test_clear_states_for_repo_removes_all_entries():
    repository = WikiStateRepository()
    repository.record_file_write(
        "DG-000001",
        "PR-000001",
        WikiState(
            file_name="Wiki.md",
            file_id="wiki-file-001",
            hash="sha256:abc",
            updated_at=datetime(2026, 5, 27, 10, 0, tzinfo=UTC),
        ),
    )
    repository.record_file_write(
        "DG-000002",
        "PR-000001",
        WikiState(
            file_name="Wiki.md",
            file_id="other-wiki-file-001",
            hash="sha256:other",
            updated_at=datetime(2026, 5, 27, 10, 0, tzinfo=UTC),
        ),
    )

    repository.clear_states_for_project("DG-000001", "PR-000001")

    assert repository.get_all_states("DG-000001", "PR-000001") == {}
    assert repository.get_file_state("DG-000002", "PR-000001", "Wiki.md") is not None


def test_record_file_write_isolated_per_project():
    repository = WikiStateRepository()
    updated_at = datetime(2026, 5, 27, 10, 0, tzinfo=UTC)

    repository.record_file_write(
        "DG-000001",
        "PR-000001",
        WikiState(
            file_name="Wiki.md",
            file_id="project-one-wiki",
            hash="sha256:one",
            updated_at=updated_at,
        ),
    )
    repository.record_file_write(
        "DG-000001",
        "PR-000002",
        WikiState(
            file_name="Wiki.md",
            file_id="project-two-wiki",
            hash="sha256:two",
            updated_at=updated_at,
        ),
    )

    assert repository.get_file_state("DG-000001", "PR-000001", "Wiki.md").hash == "sha256:one"
    assert repository.get_file_state("DG-000001", "PR-000002", "Wiki.md").hash == "sha256:two"


def test_clear_states_for_project_does_not_affect_other_projects():
    repository = WikiStateRepository()
    updated_at = datetime(2026, 5, 27, 10, 0, tzinfo=UTC)
    for project_id in ("PR-000001", "PR-000002"):
        repository.record_file_write(
            "DG-000001",
            project_id,
            WikiState(
                file_name="Wiki.md",
                file_id=f"{project_id}-wiki",
                hash=f"sha256:{project_id}",
                updated_at=updated_at,
            ),
        )

    repository.clear_states_for_project("DG-000001", "PR-000001")

    assert repository.get_file_state("DG-000001", "PR-000001", "Wiki.md") is None
    assert repository.get_file_state("DG-000001", "PR-000002", "Wiki.md") is not None
