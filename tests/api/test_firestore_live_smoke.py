import os
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from sadify_api.config import load_api_config
from sadify_api.services.firestore_client import get_firestore_client, safe_doc_id
from sadify_api.services.projects import FirestoreProjectRepository


pytestmark = pytest.mark.skipif(
    os.getenv("SADIFY_FIRESTORE_LIVE") != "1",
    reason="Set SADIFY_FIRESTORE_LIVE=1 to run the opt-in Firestore smoke.",
)


def test_firestore_live_project_round_trip():
    client = get_firestore_client(load_api_config().google_cloud_project)
    repository = FirestoreProjectRepository(client)
    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    grant_id = f"DG-FIRESTORE-SMOKE-{suffix}"
    project_name = f"Firestore Smoke {suffix}"

    try:
        project = repository.create_project(
            grant_id=grant_id,
            name=project_name,
            drive_folder_id=f"folder-{suffix}",
        )

        assert repository.get_project(grant_id, project.project_id) == project
        assert repository.get_project_by_name(grant_id, project_name) == project
        assert repository.list_projects(grant_id) == [project]
    finally:
        _delete_doc(client, "projects", safe_doc_id(grant_id, "PR-000001"))
        _delete_doc(
            client,
            "project_name_index",
            safe_doc_id(grant_id, _name_digest(project_name)),
        )
        _delete_doc(client, "counters", safe_doc_id("project", grant_id, "project"))


def _delete_doc(client, collection: str, doc_id: str) -> None:
    client.collection(collection).document(doc_id).delete()


def _name_digest(value: str) -> str:
    normalized = " ".join(value.strip().lower().split())
    return sha256(normalized.encode("utf-8")).hexdigest()
