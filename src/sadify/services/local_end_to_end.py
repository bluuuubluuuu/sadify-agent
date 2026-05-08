from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol, Sequence

from sadify.diagnostics import DiagnosticsRecorder, OperationResult, timed_action
from sadify.renderers.wiki_markdown import WikiNoteDraft, render_wiki_notes
from sadify.schemas import (
    DriveFolders,
    ExportRecord,
    KnowledgeItemRecord,
    ProjectMemory,
    ProjectRecord,
    RelationshipRecord,
    SadVersionRecord,
    SourceRecord,
)
from sadify.services.export_generation import ExportPackage, prepare_export_package
from sadify.services.relationship_linking import (
    RelationshipGraph,
    build_requirement_graph,
)
from sadify.services.requirement_analysis import (
    RequirementAnalysis,
    analyze_requirement_text,
)
from sadify.services.sad_generation import generate_project_sad
from sadify.services.wiki_verification import (
    approve_wiki_draft,
    prepare_wiki_draft_for_approval,
)


class LocalEndToEndError(ValueError):
    pass


class CanonicalRepository(Protocol):
    def save_project(self, project: ProjectRecord | dict) -> ProjectRecord: ...

    def save_source(
        self,
        project_id: str,
        source: SourceRecord | dict,
    ) -> SourceRecord: ...

    def save_knowledge_item(
        self,
        project_id: str,
        knowledge_item: KnowledgeItemRecord | dict,
    ) -> KnowledgeItemRecord: ...

    def save_relationship(
        self,
        project_id: str,
        relationship: RelationshipRecord | dict,
    ) -> RelationshipRecord: ...

    def save_sad_version(
        self,
        project_id: str,
        sad_version: SadVersionRecord | dict,
    ) -> SadVersionRecord: ...

    def save_export(
        self,
        project_id: str,
        export: ExportRecord | dict,
    ) -> ExportRecord: ...


@dataclass(frozen=True)
class LocalEndToEndInput:
    project_id: str
    project_title: str
    project_slug: str
    requirement_id: str
    requirement_title: str
    requirement_text: str
    source_ids: tuple[str, ...] = field(default_factory=tuple)
    source_records: tuple[SourceRecord, ...] = field(default_factory=tuple)
    sad_version_id: str = "SAD-001"
    version_number: int = 1
    region: str = "asia-southeast1"
    owner_id: str = "local-user"
    owner_name: str = "Project Owner"
    created_by: str = "local-user"
    reviewed_by: str = "local-user"
    created_at: datetime | None = None


@dataclass(frozen=True)
class LocalEndToEndResult:
    input: LocalEndToEndInput
    project: ProjectRecord
    source_records: tuple[SourceRecord, ...]
    analysis: RequirementAnalysis
    graph: RelationshipGraph
    wiki_notes: tuple[WikiNoteDraft, ...]
    verified_items: tuple[KnowledgeItemRecord, ...]
    sad_version: SadVersionRecord
    export_package: ExportPackage
    diagnostics: tuple[OperationResult, ...]
    saved_record_counts: dict[str, int]


def run_local_end_to_end(
    workflow_input: LocalEndToEndInput,
    *,
    repository: CanonicalRepository | None = None,
) -> LocalEndToEndResult:
    timestamp = workflow_input.created_at or datetime.now(UTC)
    recorder = DiagnosticsRecorder()

    with timed_action(
        recorder,
        "local.analyze_requirement",
        "Requirement analysis completed.",
        failure_message="Requirement analysis failed.",
        metadata={"requirement_id": workflow_input.requirement_id},
    ):
        analysis = analyze_requirement_text(workflow_input.requirement_text)
        if not analysis.is_valid:
            raise LocalEndToEndError(
                analysis.validation_error or "Requirement text is not valid."
            )

    source_ids = _source_ids(workflow_input)

    with timed_action(
        recorder,
        "local.build_relationship_graph",
        "Relationship graph built.",
        failure_message="Relationship graph build failed.",
        metadata={"requirement_id": workflow_input.requirement_id},
    ):
        graph = build_requirement_graph(
            requirement_id=workflow_input.requirement_id,
            title=workflow_input.requirement_title,
            requirement_text=workflow_input.requirement_text,
            source_ids=source_ids,
            created_at=timestamp,
        )

    with timed_action(
        recorder,
        "local.render_wiki_notes",
        "Wiki notes rendered.",
        failure_message="Wiki note rendering failed.",
        metadata={"knowledge_item_count": len(graph.knowledge_items)},
    ):
        wiki_notes = render_wiki_notes(
            knowledge_items=graph.knowledge_items,
            relationships=graph.relationships,
        )

    with timed_action(
        recorder,
        "local.verify_wiki_notes",
        "Wiki notes verified and approved for local E2E.",
        failure_message="Wiki note verification failed.",
        metadata={"wiki_note_count": len(wiki_notes)},
    ):
        verified_items = _verify_and_approve_items(
            knowledge_items=graph.knowledge_items,
            wiki_notes=wiki_notes,
            reviewed_by=workflow_input.reviewed_by,
            reviewed_at=timestamp,
        )

    with timed_action(
        recorder,
        "local.generate_project_sad",
        "Project SAD generated.",
        failure_message="Project SAD generation failed.",
        metadata={"sad_version_id": workflow_input.sad_version_id},
    ):
        sad_version = generate_project_sad(
            sad_version_id=workflow_input.sad_version_id,
            project_title=workflow_input.project_title,
            knowledge_items=verified_items,
            relationships=graph.relationships,
            created_at=timestamp,
            created_by=workflow_input.created_by,
            version_number=workflow_input.version_number,
        )

    with timed_action(
        recorder,
        "local.prepare_export_package",
        "Export package prepared.",
        failure_message="Export package preparation failed.",
        metadata={"sad_version_id": sad_version.sad_version_id},
    ):
        export_package = prepare_export_package(
            sad_version=sad_version,
            wiki_notes=wiki_notes,
            project_slug=workflow_input.project_slug,
            created_at=timestamp,
            created_by=workflow_input.created_by,
        )

    project = _build_project_record(
        workflow_input=workflow_input,
        analysis=analysis,
        graph=graph,
        sad_version=sad_version,
        timestamp=timestamp,
    )
    saved_record_counts: dict[str, int] = {}
    if repository is not None:
        with timed_action(
            recorder,
            "local.persist_canonical_records",
            "Canonical records persisted.",
            failure_message="Canonical record persistence failed.",
            metadata={"project_id": workflow_input.project_id},
        ):
            saved_record_counts = _persist_records(
                repository=repository,
                project=project,
                source_records=workflow_input.source_records,
                knowledge_items=verified_items,
                relationships=graph.relationships,
                sad_version=sad_version,
                export_records=export_package.records,
            )

    return LocalEndToEndResult(
        input=workflow_input,
        project=project,
        source_records=workflow_input.source_records,
        analysis=analysis,
        graph=graph,
        wiki_notes=wiki_notes,
        verified_items=verified_items,
        sad_version=sad_version,
        export_package=export_package,
        diagnostics=tuple(recorder.results),
        saved_record_counts=saved_record_counts,
    )


def _verify_and_approve_items(
    *,
    knowledge_items: Sequence[KnowledgeItemRecord],
    wiki_notes: Sequence[WikiNoteDraft],
    reviewed_by: str,
    reviewed_at: datetime,
) -> tuple[KnowledgeItemRecord, ...]:
    notes_by_item_id = {note.item_id: note for note in wiki_notes}
    verified_items: list[KnowledgeItemRecord] = []
    for item in knowledge_items:
        prepared = prepare_wiki_draft_for_approval(
            item=item,
            note=notes_by_item_id[item.item_id],
            all_notes=wiki_notes,
        )
        if prepared.markdown_status == "pending_human_approval":
            verified_items.append(
                approve_wiki_draft(
                    prepared,
                    reviewed_by=reviewed_by,
                    reviewed_at=reviewed_at,
                )
            )
        else:
            verified_items.append(prepared)
    return tuple(verified_items)


def _build_project_record(
    *,
    workflow_input: LocalEndToEndInput,
    analysis: RequirementAnalysis,
    graph: RelationshipGraph,
    sad_version: SadVersionRecord,
    timestamp: datetime,
) -> ProjectRecord:
    return ProjectRecord(
        project_id=workflow_input.project_id,
        slug=workflow_input.project_slug,
        title=workflow_input.project_title,
        status="planning",
        owner_id=workflow_input.owner_id,
        owner_name=workflow_input.owner_name,
        created_at=timestamp,
        updated_at=timestamp,
        region=workflow_input.region,
        project_memory=ProjectMemory(
            summary=analysis.understanding_summary,
            key_actors=graph.item_titles_by_type("actor"),
            key_entities=graph.item_titles_by_type("entity"),
            key_workflows=graph.item_titles_by_type("workflow"),
            known_gaps=[item.area for item in analysis.missing_information],
            last_updated_from_sad_version_id=sad_version.sad_version_id,
            last_updated_at=timestamp,
        ),
        drive=DriveFolders(),
    )


def _persist_records(
    *,
    repository: CanonicalRepository,
    project: ProjectRecord,
    source_records: Sequence[SourceRecord],
    knowledge_items: Sequence[KnowledgeItemRecord],
    relationships: Sequence[RelationshipRecord],
    sad_version: SadVersionRecord,
    export_records: Sequence[ExportRecord],
) -> dict[str, int]:
    repository.save_project(project)
    for source_record in source_records:
        repository.save_source(project.project_id, source_record)
    for item in knowledge_items:
        repository.save_knowledge_item(project.project_id, item)
    for relationship in relationships:
        repository.save_relationship(project.project_id, relationship)
    repository.save_sad_version(project.project_id, sad_version)
    for export_record in export_records:
        repository.save_export(project.project_id, export_record)

    return {
        "projects": 1,
        "sources": len(source_records),
        "knowledge_items": len(knowledge_items),
        "relationships": len(relationships),
        "sad_versions": 1,
        "exports": len(export_records),
    }


def _source_ids(workflow_input: LocalEndToEndInput) -> tuple[str, ...]:
    source_ids = [
        *workflow_input.source_ids,
        *(source.source_id for source in workflow_input.source_records),
    ]
    return tuple(_ordered_unique(source_ids))


def _ordered_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value in seen:
            continue
        unique_values.append(value)
        seen.add(value)
    return unique_values
