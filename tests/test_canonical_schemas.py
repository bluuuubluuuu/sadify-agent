import pytest
from pydantic import ValidationError

from sadify.schemas import (
    ExportRecord,
    KnowledgeItemRecord,
    ProjectMemory,
    ProjectRecord,
    RelationshipRecord,
    SadVersionRecord,
    SourceRecord,
    validation_error_messages,
)


def test_valid_canonical_records_validate():
    project = ProjectRecord(**_valid_project_record())
    source = SourceRecord(**_valid_source_record())
    knowledge_item = KnowledgeItemRecord(**_valid_knowledge_item_record())
    relationship = RelationshipRecord(**_valid_relationship_record())
    sad_version = SadVersionRecord(**_valid_sad_version_record())
    export = ExportRecord(**_valid_export_record())

    assert project.project_id == "PROJ-001"
    assert isinstance(project.project_memory, ProjectMemory)
    assert source.source_id == "SRC-001"
    assert source.traceability_units[0].unit_type == "sheet"
    assert knowledge_item.item_id == "REQ-001"
    assert knowledge_item.source_ids == ["SRC-001"]
    assert relationship.relationship_id == "REL-001"
    assert sad_version.sad_version_id == "SAD-001"
    assert export.export_id == "EXP-001"


def test_missing_required_field_identifies_the_field():
    record = _valid_project_record()
    del record["title"]

    with pytest.raises(ValidationError) as exc_info:
        ProjectRecord(**record)

    messages = validation_error_messages(exc_info.value)
    assert any(message.startswith("title:") for message in messages)


def test_bad_id_prefix_fails_with_useful_message():
    record = _valid_knowledge_item_record()
    record["item_id"] = "BAD-001"

    with pytest.raises(ValidationError) as exc_info:
        KnowledgeItemRecord(**record)

    messages = validation_error_messages(exc_info.value)
    assert messages == [
        "item_id: item_id must start with one of "
        "REQ-, ENT-, WF-, DEC-, ACT-, REP-, SRC-"
    ]


def test_knowledge_item_id_prefix_must_match_item_type():
    record = _valid_knowledge_item_record()
    record["item_id"] = "ENT-001"
    record["item_type"] = "requirement"

    with pytest.raises(ValidationError) as exc_info:
        KnowledgeItemRecord(**record)

    messages = validation_error_messages(exc_info.value)
    assert messages == [
        "item_id: item_id prefix ENT- does not match item_type requirement"
    ]


def test_invalid_enum_values_fail_validation():
    knowledge_item = _valid_knowledge_item_record()
    knowledge_item["item_type"] = "screen"
    relationship = _valid_relationship_record()
    relationship["relationship_type"] = "unknown_link"
    export = _valid_export_record()
    export["export_type"] = "spreadsheet"
    export["status"] = "complete"

    with pytest.raises(ValidationError):
        KnowledgeItemRecord(**knowledge_item)
    with pytest.raises(ValidationError):
        RelationshipRecord(**relationship)
    with pytest.raises(ValidationError):
        ExportRecord(**export)


def test_score_bounds_are_enforced():
    knowledge_item = _valid_knowledge_item_record()
    knowledge_item["completeness_score"] = 101
    sad_version = _valid_sad_version_record()
    sad_version["completeness_score"] = -1

    with pytest.raises(ValidationError):
        KnowledgeItemRecord(**knowledge_item)
    with pytest.raises(ValidationError):
        SadVersionRecord(**sad_version)


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
        "summary": (
            "Field staff need to record fertilizer application by block."
        ),
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
