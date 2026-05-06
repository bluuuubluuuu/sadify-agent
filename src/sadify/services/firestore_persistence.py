from __future__ import annotations

import logging
from typing import Any, TypeVar

from pydantic import BaseModel

from sadify.schemas import (
    ExportRecord,
    KnowledgeItemRecord,
    ProjectRecord,
    RelationshipRecord,
    SadVersionRecord,
    SourceRecord,
)


class FirestorePersistenceError(RuntimeError):
    """Raised when SADify cannot save or read canonical records."""


CanonicalRecord = TypeVar("CanonicalRecord", bound=BaseModel)
LOGGER = logging.getLogger("sadify.firestore")


class FirestoreRepository:
    def __init__(self, client) -> None:
        self._client = client

    def save_project(self, project: ProjectRecord | dict[str, Any]) -> ProjectRecord:
        record = _coerce_model(ProjectRecord, project)
        self._save_document(
            self._project_document(record.project_id),
            record,
            f"project {record.project_id}",
        )
        return record

    def get_project(self, project_id: str) -> ProjectRecord | None:
        return self._read_document(
            self._project_document(project_id),
            ProjectRecord,
            f"project {project_id}",
        )

    def save_source(
        self,
        project_id: str,
        source: SourceRecord | dict[str, Any],
    ) -> SourceRecord:
        record = _coerce_model(SourceRecord, source)
        self._save_document(
            self._project_subcollection_document(
                project_id,
                "sources",
                record.source_id,
            ),
            record,
            f"source {record.source_id}",
        )
        return record

    def get_source(self, project_id: str, source_id: str) -> SourceRecord | None:
        return self._read_document(
            self._project_subcollection_document(project_id, "sources", source_id),
            SourceRecord,
            f"source {source_id}",
        )

    def save_knowledge_item(
        self,
        project_id: str,
        knowledge_item: KnowledgeItemRecord | dict[str, Any],
    ) -> KnowledgeItemRecord:
        record = _coerce_model(KnowledgeItemRecord, knowledge_item)
        self._save_document(
            self._project_subcollection_document(
                project_id,
                "knowledge_items",
                record.item_id,
            ),
            record,
            f"knowledge item {record.item_id}",
        )
        return record

    def get_knowledge_item(
        self,
        project_id: str,
        item_id: str,
    ) -> KnowledgeItemRecord | None:
        return self._read_document(
            self._project_subcollection_document(
                project_id,
                "knowledge_items",
                item_id,
            ),
            KnowledgeItemRecord,
            f"knowledge item {item_id}",
        )

    def save_relationship(
        self,
        project_id: str,
        relationship: RelationshipRecord | dict[str, Any],
    ) -> RelationshipRecord:
        record = _coerce_model(RelationshipRecord, relationship)
        self._save_document(
            self._project_subcollection_document(
                project_id,
                "relationships",
                record.relationship_id,
            ),
            record,
            f"relationship {record.relationship_id}",
        )
        return record

    def get_relationship(
        self,
        project_id: str,
        relationship_id: str,
    ) -> RelationshipRecord | None:
        return self._read_document(
            self._project_subcollection_document(
                project_id,
                "relationships",
                relationship_id,
            ),
            RelationshipRecord,
            f"relationship {relationship_id}",
        )

    def save_sad_version(
        self,
        project_id: str,
        sad_version: SadVersionRecord | dict[str, Any],
    ) -> SadVersionRecord:
        record = _coerce_model(SadVersionRecord, sad_version)
        self._save_document(
            self._project_subcollection_document(
                project_id,
                "sad_versions",
                record.sad_version_id,
            ),
            record,
            f"SAD version {record.sad_version_id}",
        )
        return record

    def get_sad_version(
        self,
        project_id: str,
        sad_version_id: str,
    ) -> SadVersionRecord | None:
        return self._read_document(
            self._project_subcollection_document(
                project_id,
                "sad_versions",
                sad_version_id,
            ),
            SadVersionRecord,
            f"SAD version {sad_version_id}",
        )

    def save_export(
        self,
        project_id: str,
        export: ExportRecord | dict[str, Any],
    ) -> ExportRecord:
        record = _coerce_model(ExportRecord, export)
        self._save_document(
            self._project_subcollection_document(
                project_id,
                "exports",
                record.export_id,
            ),
            record,
            f"export {record.export_id}",
        )
        return record

    def get_export(self, project_id: str, export_id: str) -> ExportRecord | None:
        return self._read_document(
            self._project_subcollection_document(project_id, "exports", export_id),
            ExportRecord,
            f"export {export_id}",
        )

    def _project_document(self, project_id: str):
        return self._client.collection("projects").document(
            _validate_project_id(project_id)
        )

    def _project_subcollection_document(
        self,
        project_id: str,
        collection_name: str,
        document_id: str,
    ):
        return (
            self._project_document(project_id)
            .collection(collection_name)
            .document(document_id)
        )

    def _save_document(
        self,
        document,
        record: BaseModel,
        description: str,
    ) -> None:
        try:
            document.set(record.model_dump(mode="json"))
        except Exception as exc:
            message = f"Could not save {description}."
            LOGGER.exception(message)
            raise FirestorePersistenceError(message) from exc

    def _read_document(
        self,
        document,
        model_type: type[CanonicalRecord],
        description: str,
    ) -> CanonicalRecord | None:
        try:
            snapshot = document.get()
            if not snapshot.exists:
                return None
            payload = snapshot.to_dict()
            if payload is None:
                return None
            return model_type.model_validate(payload)
        except Exception as exc:
            message = f"Could not read {description}."
            LOGGER.exception(message)
            raise FirestorePersistenceError(message) from exc


def _coerce_model(
    model_type: type[CanonicalRecord],
    value: CanonicalRecord | dict[str, Any],
) -> CanonicalRecord:
    if isinstance(value, model_type):
        return value
    return model_type.model_validate(value)


def _validate_project_id(project_id: str) -> str:
    if project_id.startswith("PROJ-"):
        return project_id
    raise ValueError("project_id must start with PROJ-")
