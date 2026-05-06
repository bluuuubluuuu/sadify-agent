import pytest
from pydantic import ValidationError

from sadify.schemas import (
    ExportRecord,
    KnowledgeItemRecord,
    ProjectRecord,
    RelationshipRecord,
    SadVersionRecord,
    SourceRecord,
)
from sadify.services import FirestorePersistenceError, FirestoreRepository


def test_project_record_round_trips_through_firestore_repository():
    client = FakeFirestoreClient()
    repository = FirestoreRepository(client)
    project = ProjectRecord(**_valid_project_record())

    repository.save_project(project)

    loaded = repository.get_project("PROJ-001")
    assert loaded == project
    assert client.storage[("projects", "PROJ-001")]["title"] == (
        "Plantation Field Operations"
    )


def test_subcollection_records_round_trip_under_project():
    client = FakeFirestoreClient()
    repository = FirestoreRepository(client)
    source = SourceRecord(**_valid_source_record())
    knowledge_item = KnowledgeItemRecord(**_valid_knowledge_item_record())
    relationship = RelationshipRecord(**_valid_relationship_record())
    sad_version = SadVersionRecord(**_valid_sad_version_record())
    export = ExportRecord(**_valid_export_record())

    repository.save_source("PROJ-001", source)
    repository.save_knowledge_item("PROJ-001", knowledge_item)
    repository.save_relationship("PROJ-001", relationship)
    repository.save_sad_version("PROJ-001", sad_version)
    repository.save_export("PROJ-001", export)

    assert repository.get_source("PROJ-001", "SRC-001") == source
    assert repository.get_knowledge_item("PROJ-001", "REQ-001") == knowledge_item
    assert repository.get_relationship("PROJ-001", "REL-001") == relationship
    assert repository.get_sad_version("PROJ-001", "SAD-001") == sad_version
    assert repository.get_export("PROJ-001", "EXP-001") == export
    assert ("projects", "PROJ-001", "sources", "SRC-001") in client.storage
    assert (
        "projects",
        "PROJ-001",
        "knowledge_items",
        "REQ-001",
    ) in client.storage


def test_save_validates_dict_before_client_write():
    client = FakeFirestoreClient()
    repository = FirestoreRepository(client)
    invalid_project = _valid_project_record()
    invalid_project["project_id"] = "BAD-001"

    with pytest.raises(ValidationError):
        repository.save_project(invalid_project)

    assert client.storage == {}


def test_source_save_validates_source_id_before_client_write():
    client = FakeFirestoreClient()
    repository = FirestoreRepository(client)
    invalid_source = _valid_source_record()
    invalid_source["source_id"] = "REQ-001"

    with pytest.raises(ValidationError):
        repository.save_source("PROJ-001", invalid_source)

    assert client.storage == {}


def test_subcollection_save_validates_project_id_path_before_client_write():
    client = FakeFirestoreClient()
    repository = FirestoreRepository(client)

    with pytest.raises(ValueError, match="project_id must start with PROJ-"):
        repository.save_source("BAD-001", SourceRecord(**_valid_source_record()))

    assert client.storage == {}


def test_missing_documents_return_none():
    repository = FirestoreRepository(FakeFirestoreClient())

    assert repository.get_project("PROJ-404") is None
    assert repository.get_source("PROJ-001", "SRC-404") is None
    assert repository.get_knowledge_item("PROJ-001", "REQ-404") is None
    assert repository.get_relationship("PROJ-001", "REL-404") is None
    assert repository.get_sad_version("PROJ-001", "SAD-404") is None
    assert repository.get_export("PROJ-001", "EXP-404") is None


def test_save_client_errors_are_wrapped_with_plain_context():
    client = FakeFirestoreClient(raise_on_set=True)
    repository = FirestoreRepository(client)

    with pytest.raises(FirestorePersistenceError) as exc_info:
        repository.save_project(ProjectRecord(**_valid_project_record()))

    assert str(exc_info.value) == "Could not save project PROJ-001."
    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_save_client_errors_are_logged_with_plain_context(caplog):
    client = FakeFirestoreClient(raise_on_set=True)
    repository = FirestoreRepository(client)
    caplog.set_level("ERROR", logger="sadify.firestore")

    with pytest.raises(FirestorePersistenceError):
        repository.save_project(ProjectRecord(**_valid_project_record()))

    assert any(
        "Could not save project PROJ-001." in record.message
        for record in caplog.records
    )


def test_read_client_errors_are_wrapped_with_plain_context():
    client = FakeFirestoreClient(raise_on_get=True)
    repository = FirestoreRepository(client)

    with pytest.raises(FirestorePersistenceError) as exc_info:
        repository.get_project("PROJ-001")

    assert str(exc_info.value) == "Could not read project PROJ-001."
    assert isinstance(exc_info.value.__cause__, RuntimeError)


class FakeFirestoreClient:
    def __init__(self, *, raise_on_set=False, raise_on_get=False):
        self.storage = {}
        self.raise_on_set = raise_on_set
        self.raise_on_get = raise_on_get

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
        if self._client.raise_on_set:
            raise RuntimeError("firestore write failed")
        self._client.storage[self._path] = payload.copy()

    def get(self):
        if self._client.raise_on_get:
            raise RuntimeError("firestore read failed")
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


def _valid_project_record() -> dict:
    return {
        "project_id": "PROJ-001",
        "slug": "plantation-field-operations",
        "title": "Plantation Field Operations",
        "status": "planning",
        "owner_id": "local-user",
        "owner_name": "Project Owner",
        "created_at": "2026-05-06T00:00:00Z",
        "updated_at": "2026-05-06T00:00:00Z",
        "region": "asia-southeast1",
        "project_memory": {
            "summary": "Clarify operational requirements for field work.",
            "key_actors": [],
            "key_entities": [],
            "key_workflows": [],
            "known_gaps": [],
            "last_updated_from_sad_version_id": None,
            "last_updated_at": "2026-05-06T00:00:00Z",
        },
        "drive": {
            "root_folder_id": None,
            "sad_folder_id": None,
            "wiki_folder_id": None,
        },
    }


def _valid_source_record() -> dict:
    return {
        "source_id": "SRC-001",
        "source_item_id": "SRC-001",
        "source_type": "xlsx",
        "original_file_name": "fertilizer_log_april.xlsx",
        "mime_type": (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        "file_size_bytes": 204800,
        "drive_file_id": None,
        "extraction_status": "extracted",
        "extracted_text_preview": "Sheet April Records contains block and date.",
        "extraction_summary": "Spreadsheet records fertilizer applications.",
        "traceability_units": [
            {
                "unit_type": "sheet",
                "unit_name": "April Records",
                "columns": ["Block", "Date", "Fertilizer Type", "Worker"],
            }
        ],
        "created_at": "2026-05-06T00:00:00Z",
        "updated_at": "2026-05-06T00:00:00Z",
    }


def _valid_knowledge_item_record() -> dict:
    return {
        "item_id": "REQ-001",
        "item_type": "requirement",
        "slug": "fertilizer-application-logging",
        "title": "Fertilizer Application Logging",
        "status": "draft",
        "summary": "Field staff need to record fertilizer application by block.",
        "completeness_score": 72,
        "confidence_label": "medium",
        "problem_severity": "high",
        "recommendation_priority": "must_have",
        "source_ids": ["SRC-001"],
        "relationship_ids": ["REL-001"],
        "open_questions": [
            {
                "question_id": "Q-001",
                "label": "[OPEN QUESTION]",
                "severity": "high",
                "question": "Who verifies the fertilizer record?",
            }
        ],
        "assumptions": [
            {
                "assumption_id": "ASM-001",
                "label": "[ASSUMPTION]",
                "text": "Field supervisors review fertilizer records.",
            }
        ],
        "markdown_current": None,
        "markdown_draft": None,
        "markdown_status": "not_generated",
        "pending_change_summary": None,
        "verification_result": None,
        "drive_file": {
            "file_name": None,
            "drive_file_id": None,
            "url": None,
        },
        "created_at": "2026-05-06T00:00:00Z",
        "updated_at": "2026-05-06T00:00:00Z",
    }


def _valid_relationship_record() -> dict:
    return {
        "relationship_id": "REL-001",
        "source_item_id": "REQ-001",
        "source_item_title": "Fertilizer Application Logging",
        "target_item_id": "ENT-001",
        "target_item_title": "Field Block",
        "relationship_type": "uses_entity",
        "relationship_label": "Requirement uses entity",
        "explanation": "Fertilizer records are captured by field block.",
        "confidence_label": "high",
        "evidence_source_ids": ["SRC-001"],
        "created_at": "2026-05-06T00:00:00Z",
        "updated_at": "2026-05-06T00:00:00Z",
    }


def _valid_sad_version_record() -> dict:
    return {
        "sad_version_id": "SAD-001",
        "version_number": 1,
        "status": "draft",
        "created_at": "2026-05-06T00:00:00Z",
        "created_by": "local-user",
        "completeness_score": 78,
        "confidence_label": "medium",
        "source_requirement_ids": ["REQ-001"],
        "source_knowledge_item_ids": ["REQ-001", "ENT-001"],
        "structured_sections": {
            "summary": {},
            "critical_gaps": [],
            "functional_requirements": [],
            "non_functional_requirements": [],
            "business_rules": [],
            "edge_cases": [],
            "data_entities": [],
            "workflows": [],
            "developer_tasks": [],
            "assumptions": [],
            "open_questions": [],
            "source_traceability": [],
        },
        "rendered_markdown": "# System Analysis and Design\n\nDraft.",
        "verification_result": {
            "schema_validation": {"status": "passed", "issues": []},
            "sad_quality_check": {"status": "passed", "issues": []},
        },
    }


def _valid_export_record() -> dict:
    return {
        "export_id": "EXP-001",
        "export_type": "google_doc",
        "source_sad_version_id": "SAD-001",
        "source_knowledge_item_version_ids": ["KIV-001"],
        "file_name": "SAD-v1-plantation-field-operations",
        "drive_file_id": "drive-file-id",
        "url": "https://docs.google.com/document/d/example",
        "created_at": "2026-05-06T00:00:00Z",
        "created_by": "local-user",
        "status": "success",
        "error_message": None,
    }
