from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from sadify.schemas import KnowledgeItemRecord, RelationshipRecord


@dataclass(frozen=True)
class WikiNoteDraft:
    item_id: str
    item_type: str
    slug: str
    folder: str
    file_name: str
    relative_path: str
    markdown: str
    linked_item_ids: tuple[str, ...]


class WikiMarkdownRenderError(ValueError):
    pass


_FOLDERS = {
    "requirement": "requirements",
    "entity": "entities",
    "workflow": "workflows",
    "decision": "decisions",
    "actor": "actors",
    "report": "reports",
    "source": "sources",
}


def render_wiki_notes(
    *,
    knowledge_items: Sequence[KnowledgeItemRecord],
    relationships: Sequence[RelationshipRecord],
) -> tuple[WikiNoteDraft, ...]:
    items_by_id = _items_by_id(knowledge_items)
    _validate_relationship_endpoints(relationships, items_by_id)

    file_stems = {
        item.item_id: _file_stem(item)
        for item in knowledge_items
    }

    return tuple(
        _render_note(
            item=item,
            relationships=relationships,
            items_by_id=items_by_id,
            file_stems=file_stems,
        )
        for item in knowledge_items
    )


def _items_by_id(
    knowledge_items: Sequence[KnowledgeItemRecord],
) -> dict[str, KnowledgeItemRecord]:
    items_by_id: dict[str, KnowledgeItemRecord] = {}
    for item in knowledge_items:
        if item.item_id in items_by_id:
            raise WikiMarkdownRenderError(f"Duplicate knowledge item: {item.item_id}")
        items_by_id[item.item_id] = item
    return items_by_id


def _validate_relationship_endpoints(
    relationships: Sequence[RelationshipRecord],
    items_by_id: dict[str, KnowledgeItemRecord],
) -> None:
    missing_ids: list[str] = []
    for relationship in relationships:
        if relationship.source_item_id not in items_by_id:
            missing_ids.append(relationship.source_item_id)
        if relationship.target_item_id not in items_by_id:
            missing_ids.append(relationship.target_item_id)

    if missing_ids:
        unique_missing_ids = ", ".join(_ordered_unique(missing_ids))
        raise WikiMarkdownRenderError(
            f"Cannot render wiki links for missing item(s): {unique_missing_ids}"
        )


def _render_note(
    *,
    item: KnowledgeItemRecord,
    relationships: Sequence[RelationshipRecord],
    items_by_id: dict[str, KnowledgeItemRecord],
    file_stems: dict[str, str],
) -> WikiNoteDraft:
    folder = _FOLDERS[item.item_type]
    file_name = f"{file_stems[item.item_id]}.md"
    linked_item_ids = _linked_item_ids(item, relationships)
    markdown = _render_markdown(
        item=item,
        linked_item_ids=linked_item_ids,
        relationships=relationships,
        items_by_id=items_by_id,
        file_stems=file_stems,
    )

    return WikiNoteDraft(
        item_id=item.item_id,
        item_type=item.item_type,
        slug=item.slug,
        folder=folder,
        file_name=file_name,
        relative_path=f"{folder}/{file_name}",
        markdown=markdown,
        linked_item_ids=linked_item_ids,
    )


def _render_markdown(
    *,
    item: KnowledgeItemRecord,
    linked_item_ids: tuple[str, ...],
    relationships: Sequence[RelationshipRecord],
    items_by_id: dict[str, KnowledgeItemRecord],
    file_stems: dict[str, str],
) -> str:
    lines: list[str] = []
    lines.extend(_frontmatter(item, linked_item_ids))
    lines.extend(
        [
            f"# {item.title}",
            "",
            "## Summary",
            item.summary,
            "",
            "## Related Notes",
        ]
    )
    lines.extend(
        _related_note_lines(
            item=item,
            relationships=relationships,
            items_by_id=items_by_id,
            file_stems=file_stems,
        )
    )
    lines.extend(["", "## Sources"])
    lines.extend(_source_lines(item, items_by_id, file_stems))
    lines.extend(_open_question_lines(item))
    lines.extend(_assumption_lines(item))
    return "\n".join(lines).rstrip() + "\n"


def _frontmatter(
    item: KnowledgeItemRecord,
    linked_item_ids: tuple[str, ...],
) -> list[str]:
    lines = [
        "---",
        f"id: {item.item_id}",
        f"type: {item.item_type}",
        f"slug: {item.slug}",
        f"status: {item.status}",
        f"completeness: {item.completeness_score}",
        f"confidence: {item.confidence_label}",
    ]
    lines.extend(_yaml_list("sources", item.source_ids))
    lines.extend(_yaml_list("relationships", item.relationship_ids))
    lines.extend(_yaml_list("related", linked_item_ids))
    lines.extend(["---", ""])
    return lines


def _yaml_list(label: str, values: Sequence[str]) -> list[str]:
    if not values:
        return [f"{label}: []"]

    lines = [f"{label}:"]
    lines.extend(f"  - {value}" for value in values)
    return lines


def _related_note_lines(
    *,
    item: KnowledgeItemRecord,
    relationships: Sequence[RelationshipRecord],
    items_by_id: dict[str, KnowledgeItemRecord],
    file_stems: dict[str, str],
) -> list[str]:
    lines: list[str] = []
    for relationship in relationships:
        related_item_id = _related_item_id(item.item_id, relationship)
        if related_item_id is None:
            continue

        related_item = items_by_id[related_item_id]
        lines.append(
            "- "
            f"{_wiki_link(related_item, file_stems)}"
            f" - {relationship.relationship_label}"
        )

    if not lines:
        return ["- No related notes yet."]
    return lines


def _source_lines(
    item: KnowledgeItemRecord,
    items_by_id: dict[str, KnowledgeItemRecord],
    file_stems: dict[str, str],
) -> list[str]:
    source_lines: list[str] = []
    for source_id in item.source_ids:
        source_item = items_by_id.get(source_id)
        if source_item is None:
            source_lines.append(f"- {source_id}")
            continue
        source_lines.append(f"- {_wiki_link(source_item, file_stems)}")

    if not source_lines:
        return ["- No sources linked yet."]
    return source_lines


def _open_question_lines(item: KnowledgeItemRecord) -> list[str]:
    if not item.open_questions:
        return []

    lines = ["", "## Open Questions"]
    lines.extend(
        f"- [{question.severity.upper()}] {question.question}"
        for question in item.open_questions
    )
    return lines


def _assumption_lines(item: KnowledgeItemRecord) -> list[str]:
    if not item.assumptions:
        return []

    lines = ["", "## Assumptions"]
    lines.extend(
        f"- {assumption.label} {assumption.text}"
        for assumption in item.assumptions
    )
    return lines


def _linked_item_ids(
    item: KnowledgeItemRecord,
    relationships: Sequence[RelationshipRecord],
) -> tuple[str, ...]:
    linked_ids: list[str] = []
    for relationship in relationships:
        related_item_id = _related_item_id(item.item_id, relationship)
        if related_item_id is not None:
            linked_ids.append(related_item_id)
    return tuple(_ordered_unique(linked_ids))


def _related_item_id(
    item_id: str,
    relationship: RelationshipRecord,
) -> str | None:
    if relationship.source_item_id == item_id:
        return relationship.target_item_id
    if relationship.target_item_id == item_id:
        return relationship.source_item_id
    return None


def _wiki_link(
    item: KnowledgeItemRecord,
    file_stems: dict[str, str],
) -> str:
    return f"[[{file_stems[item.item_id]}]]"


def _file_stem(item: KnowledgeItemRecord) -> str:
    return f"{item.item_id}-{item.slug}"


def _ordered_unique(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered_values: list[str] = []
    for value in values:
        if value in seen:
            continue
        ordered_values.append(value)
        seen.add(value)
    return tuple(ordered_values)
