from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


KnowledgeItemType = Literal[
    "requirement",
    "entity",
    "workflow",
    "decision",
    "actor",
    "report",
    "source",
]
KnowledgeItemStatus = Literal["draft", "verified", "rejected", "archived"]
MarkdownStatus = Literal[
    "not_generated",
    "draft",
    "rule_failed",
    "quality_failed",
    "pending_human_approval",
    "verified",
    "rejected",
]
ConfidenceLabel = Literal["low", "medium", "high"]
Severity = Literal["critical", "high", "medium", "low"]
RecommendationPriority = Literal[
    "must_have",
    "should_have",
    "nice_to_have",
    "future",
]
RelationshipType = Literal[
    "relates_to",
    "depends_on",
    "conflicts_with",
    "uses_entity",
    "performed_by_actor",
    "produces_report",
    "uses_workflow",
    "supported_by_source",
    "records_decision",
]
SourceType = Literal["md", "txt", "pdf", "docx", "xlsx", "csv"]
ExtractionStatus = Literal["pending", "extracted", "failed"]
ExportType = Literal["google_doc", "pdf", "docx", "wiki_markdown"]
ExportStatus = Literal["pending", "success", "failed"]
SadVersionStatus = Literal["draft", "verified", "rejected", "archived"]
ProjectStatus = Literal["planning", "active", "archived"]

PROJECT_ID_PREFIXES = ("PROJ-",)
SOURCE_ID_PREFIXES = ("SRC-",)
KNOWLEDGE_ITEM_ID_PREFIXES = (
    "REQ-",
    "ENT-",
    "WF-",
    "DEC-",
    "ACT-",
    "REP-",
    "SRC-",
)
RELATIONSHIP_ID_PREFIXES = ("REL-",)
SAD_VERSION_ID_PREFIXES = ("SAD-",)
EXPORT_ID_PREFIXES = ("EXP-",)
KNOWLEDGE_ITEM_VERSION_ID_PREFIXES = ("KIV-",)
QUESTION_ID_PREFIXES = ("Q-",)
ASSUMPTION_ID_PREFIXES = ("ASM-",)
KNOWLEDGE_ITEM_TYPE_PREFIXES = {
    "requirement": "REQ-",
    "entity": "ENT-",
    "workflow": "WF-",
    "decision": "DEC-",
    "actor": "ACT-",
    "report": "REP-",
    "source": "SRC-",
}


class CanonicalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProjectMemory(CanonicalModel):
    summary: str
    key_actors: list[str]
    key_entities: list[str]
    key_workflows: list[str]
    known_gaps: list[str]
    last_updated_from_sad_version_id: str | None = None
    last_updated_at: datetime

    @field_validator("last_updated_from_sad_version_id")
    @classmethod
    def validate_last_updated_sad_id(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_id_prefix(
            value,
            SAD_VERSION_ID_PREFIXES,
            "last_updated_from_sad_version_id",
        )


class DriveFolders(CanonicalModel):
    root_folder_id: str | None = None
    sad_folder_id: str | None = None
    wiki_folder_id: str | None = None


class ProjectRecord(CanonicalModel):
    project_id: str
    slug: str
    title: str
    status: ProjectStatus
    owner_id: str
    owner_name: str
    created_at: datetime
    updated_at: datetime
    region: str
    project_memory: ProjectMemory
    drive: DriveFolders

    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, value: str) -> str:
        return _validate_id_prefix(value, PROJECT_ID_PREFIXES, "project_id")


class TraceabilityUnit(CanonicalModel):
    unit_type: str
    unit_name: str
    columns: list[str] = Field(default_factory=list)


class SourceRecord(CanonicalModel):
    source_id: str
    source_item_id: str
    source_type: SourceType
    original_file_name: str
    mime_type: str
    file_size_bytes: int = Field(ge=0)
    drive_file_id: str | None = None
    extraction_status: ExtractionStatus
    extracted_text_preview: str
    extraction_summary: str
    traceability_units: list[TraceabilityUnit]
    created_at: datetime
    updated_at: datetime

    @field_validator("source_id", "source_item_id")
    @classmethod
    def validate_source_ids(cls, value: str) -> str:
        return _validate_id_prefix(value, SOURCE_ID_PREFIXES, "source_id")


class OpenQuestion(CanonicalModel):
    question_id: str
    label: Literal["[OPEN QUESTION]"]
    severity: Severity
    question: str

    @field_validator("question_id")
    @classmethod
    def validate_question_id(cls, value: str) -> str:
        return _validate_id_prefix(value, QUESTION_ID_PREFIXES, "question_id")


class Assumption(CanonicalModel):
    assumption_id: str
    label: Literal["[ASSUMPTION]"]
    text: str

    @field_validator("assumption_id")
    @classmethod
    def validate_assumption_id(cls, value: str) -> str:
        return _validate_id_prefix(value, ASSUMPTION_ID_PREFIXES, "assumption_id")


class DriveFileRef(CanonicalModel):
    file_name: str | None = None
    drive_file_id: str | None = None
    url: str | None = None


class KnowledgeItemRecord(CanonicalModel):
    item_id: str
    item_type: KnowledgeItemType
    slug: str
    title: str
    status: KnowledgeItemStatus
    summary: str
    completeness_score: int = Field(ge=0, le=100)
    confidence_label: ConfidenceLabel
    problem_severity: Severity
    recommendation_priority: RecommendationPriority
    source_ids: list[str] = Field(default_factory=list)
    relationship_ids: list[str] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    markdown_current: str | None = None
    markdown_draft: str | None = None
    markdown_status: MarkdownStatus
    pending_change_summary: str | None = None
    verification_result: dict[str, Any] | None = None
    drive_file: DriveFileRef
    created_at: datetime
    updated_at: datetime

    @field_validator("item_id")
    @classmethod
    def validate_item_id(cls, value: str) -> str:
        return _validate_id_prefix(
            value,
            KNOWLEDGE_ITEM_ID_PREFIXES,
            "item_id",
        )

    @field_validator("source_ids")
    @classmethod
    def validate_source_id_list(cls, value: list[str]) -> list[str]:
        return [
            _validate_id_prefix(source_id, SOURCE_ID_PREFIXES, "source_ids")
            for source_id in value
        ]

    @field_validator("relationship_ids")
    @classmethod
    def validate_relationship_id_list(cls, value: list[str]) -> list[str]:
        return [
            _validate_id_prefix(
                relationship_id,
                RELATIONSHIP_ID_PREFIXES,
                "relationship_ids",
            )
            for relationship_id in value
        ]

    @model_validator(mode="after")
    def validate_item_id_matches_type(self) -> Self:
        expected_prefix = KNOWLEDGE_ITEM_TYPE_PREFIXES[self.item_type]
        if not self.item_id.startswith(expected_prefix):
            actual_prefix = self.item_id.split("-", 1)[0] + "-"
            raise ValueError(
                f"item_id prefix {actual_prefix} does not match "
                f"item_type {self.item_type}"
            )
        return self


class RelationshipRecord(CanonicalModel):
    relationship_id: str
    source_item_id: str
    source_item_title: str
    target_item_id: str
    target_item_title: str
    relationship_type: RelationshipType
    relationship_label: str
    explanation: str
    confidence_label: ConfidenceLabel
    evidence_source_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @field_validator("relationship_id")
    @classmethod
    def validate_relationship_id(cls, value: str) -> str:
        return _validate_id_prefix(
            value,
            RELATIONSHIP_ID_PREFIXES,
            "relationship_id",
        )

    @field_validator("source_item_id", "target_item_id")
    @classmethod
    def validate_knowledge_item_links(cls, value: str) -> str:
        return _validate_id_prefix(
            value,
            KNOWLEDGE_ITEM_ID_PREFIXES,
            "knowledge_item_id",
        )

    @field_validator("evidence_source_ids")
    @classmethod
    def validate_evidence_source_ids(cls, value: list[str]) -> list[str]:
        return [
            _validate_id_prefix(source_id, SOURCE_ID_PREFIXES, "evidence_source_ids")
            for source_id in value
        ]


class SadVersionRecord(CanonicalModel):
    sad_version_id: str
    version_number: int = Field(ge=1)
    status: SadVersionStatus
    created_at: datetime
    created_by: str
    completeness_score: int = Field(ge=0, le=100)
    confidence_label: ConfidenceLabel
    source_requirement_ids: list[str] = Field(default_factory=list)
    source_knowledge_item_ids: list[str] = Field(default_factory=list)
    structured_sections: dict[str, Any]
    rendered_markdown: str
    verification_result: dict[str, Any]

    @field_validator("sad_version_id")
    @classmethod
    def validate_sad_version_id(cls, value: str) -> str:
        return _validate_id_prefix(
            value,
            SAD_VERSION_ID_PREFIXES,
            "sad_version_id",
        )

    @field_validator("source_requirement_ids")
    @classmethod
    def validate_source_requirement_ids(cls, value: list[str]) -> list[str]:
        return [
            _validate_id_prefix(
                requirement_id,
                ("REQ-",),
                "source_requirement_ids",
            )
            for requirement_id in value
        ]

    @field_validator("source_knowledge_item_ids")
    @classmethod
    def validate_source_knowledge_item_ids(cls, value: list[str]) -> list[str]:
        return [
            _validate_id_prefix(
                item_id,
                KNOWLEDGE_ITEM_ID_PREFIXES,
                "source_knowledge_item_ids",
            )
            for item_id in value
        ]


class ExportRecord(CanonicalModel):
    export_id: str
    export_type: ExportType
    source_sad_version_id: str
    source_knowledge_item_version_ids: list[str] = Field(default_factory=list)
    file_name: str
    drive_file_id: str | None = None
    url: str | None = None
    created_at: datetime
    created_by: str
    status: ExportStatus
    error_message: str | None = None

    @field_validator("export_id")
    @classmethod
    def validate_export_id(cls, value: str) -> str:
        return _validate_id_prefix(value, EXPORT_ID_PREFIXES, "export_id")

    @field_validator("source_sad_version_id")
    @classmethod
    def validate_source_sad_version_id(cls, value: str) -> str:
        return _validate_id_prefix(
            value,
            SAD_VERSION_ID_PREFIXES,
            "source_sad_version_id",
        )

    @field_validator("source_knowledge_item_version_ids")
    @classmethod
    def validate_source_knowledge_item_version_ids(
        cls,
        value: list[str],
    ) -> list[str]:
        return [
            _validate_id_prefix(
                version_id,
                KNOWLEDGE_ITEM_VERSION_ID_PREFIXES,
                "source_knowledge_item_version_ids",
            )
            for version_id in value
        ]


def validation_error_messages(error: ValidationError) -> list[str]:
    messages: list[str] = []
    for issue in error.errors():
        location = ".".join(str(part) for part in issue["loc"])
        message = issue["msg"].removeprefix("Value error, ")
        if not location and message.startswith("item_id prefix "):
            location = "item_id"
        messages.append(f"{location}: {message}")
    return messages


def _validate_id_prefix(
    value: str,
    allowed_prefixes: tuple[str, ...],
    field_name: str,
) -> str:
    if value.startswith(allowed_prefixes):
        return value
    prefixes = ", ".join(allowed_prefixes)
    raise ValueError(f"{field_name} must start with one of {prefixes}")
