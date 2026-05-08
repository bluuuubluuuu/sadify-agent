from datetime import datetime, timezone

import pytest

from sadify.app import build_analysis_view_model
from sadify.schemas import SourceRecord
from sadify.services import FirestoreRepository
from sadify.services.local_end_to_end import (
    LocalEndToEndError,
    LocalEndToEndInput,
    run_local_end_to_end,
)


TIMESTAMP = datetime(2026, 5, 8, tzinfo=timezone.utc)


def test_local_end_to_end_generates_verified_artifacts_without_cloud_calls():
    result = run_local_end_to_end(_workflow_input())

    assert result.analysis.is_valid is True
    assert result.analysis.completeness_score == 100
    assert result.graph.relationships
    assert result.sad_version.sad_version_id == "SAD-001"
    assert result.sad_version.source_requirement_ids == ["REQ-001"]
    assert result.saved_record_counts == {}
    assert all(item.markdown_status == "verified" for item in result.verified_items)
    assert all(item.markdown_current for item in result.verified_items)
    assert {"google_doc", "pdf", "docx", "wiki_markdown"}.issubset(
        set(result.export_package.export_types())
    )
    assert all(
        record.drive_file_id is None for record in result.export_package.records
    )
    assert all(operation.success for operation in result.diagnostics)


def test_local_end_to_end_persists_canonical_records_when_repository_is_supplied():
    client = FakeFirestoreClient()
    repository = FirestoreRepository(client)

    result = run_local_end_to_end(_workflow_input(), repository=repository)

    assert result.saved_record_counts == {
        "projects": 1,
        "sources": 1,
        "knowledge_items": len(result.verified_items),
        "relationships": len(result.graph.relationships),
        "sad_versions": 1,
        "exports": len(result.export_package.records),
    }
    project = repository.get_project("PROJ-001")
    assert project is not None
    assert project.project_memory.last_updated_from_sad_version_id == "SAD-001"
    assert repository.get_source("PROJ-001", "SRC-001") is not None
    requirement = repository.get_knowledge_item("PROJ-001", "REQ-001")
    assert requirement is not None
    assert requirement.markdown_status == "verified"
    assert repository.get_relationship("PROJ-001", "REL-001") is not None
    assert repository.get_sad_version("PROJ-001", "SAD-001") == result.sad_version
    assert repository.get_export("PROJ-001", "EXP-001") is not None


def test_local_end_to_end_uses_same_analysis_output_as_streamlit_wrapper():
    workflow_input = _workflow_input()

    result = run_local_end_to_end(workflow_input)

    assert result.analysis.to_display_dict() == build_analysis_view_model(
        workflow_input.requirement_text
    )


def test_local_end_to_end_rejects_empty_requirement_before_generating_outputs():
    workflow_input = LocalEndToEndInput(
        project_id="PROJ-001",
        project_title="Warehouse Operations",
        project_slug="warehouse-operations",
        requirement_id="REQ-001",
        requirement_title="Warehouse Stock Movement",
        requirement_text=" ",
        created_at=TIMESTAMP,
        created_by="local-user",
        reviewed_by="owner@example.com",
    )

    with pytest.raises(LocalEndToEndError, match="Enter an operational problem"):
        run_local_end_to_end(workflow_input)


class FakeFirestoreClient:
    def __init__(self):
        self.storage = {}

    def collection(self, name):
        return FakeCollectionReference(self, (name,))


class FakeCollectionReference:
    def __init__(self, client, path):
        self._client = client
        self._path = path

    def document(self, document_id):
        return FakeDocumentReference(self._client, self._path + (document_id,))


class FakeDocumentReference:
    def __init__(self, client, path):
        self._client = client
        self._path = path

    def collection(self, name):
        return FakeCollectionReference(self._client, self._path + (name,))

    def set(self, payload):
        self._client.storage[self._path] = payload.copy()

    def get(self):
        return FakeDocumentSnapshot(
            self._path in self._client.storage,
            self._client.storage.get(self._path),
        )


class FakeDocumentSnapshot:
    def __init__(self, exists, payload):
        self.exists = exists
        self._payload = payload

    def to_dict(self):
        if self._payload is None:
            return None
        return self._payload.copy()


def _workflow_input() -> LocalEndToEndInput:
    return LocalEndToEndInput(
        project_id="PROJ-001",
        project_title="Warehouse Operations",
        project_slug="warehouse-operations",
        requirement_id="REQ-001",
        requirement_title="Warehouse Stock Movement",
        requirement_text=(
            "Warehouse operators scan stock during receiving, picking, packing, "
            "and dispatch. They record item code, quantity, location, date, "
            "status, and remarks. Supervisors approve rejected records. "
            "Managers need daily dashboards and weekly exports. The system "
            "needs role-based access, audit history, mobile use, offline "
            "support, and safe handling when records are missing or wrong."
        ),
        source_records=(_source_record(),),
        created_at=TIMESTAMP,
        created_by="local-user",
        reviewed_by="owner@example.com",
    )


def _source_record() -> SourceRecord:
    return SourceRecord(
        source_id="SRC-001",
        source_item_id="SRC-001",
        source_type="txt",
        original_file_name="warehouse-notes.txt",
        mime_type="text/plain",
        file_size_bytes=512,
        drive_file_id=None,
        extraction_status="extracted",
        extracted_text_preview="Warehouse operators scan stock.",
        extraction_summary="Text note describing warehouse stock movement.",
        traceability_units=[],
        created_at=TIMESTAMP,
        updated_at=TIMESTAMP,
    )
