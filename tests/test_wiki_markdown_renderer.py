from datetime import datetime, timezone

import pytest

from sadify.renderers.wiki_markdown import (
    WikiMarkdownRenderError,
    render_wiki_notes,
)
from sadify.schemas import KnowledgeItemRecord
from sadify.services.relationship_linking import build_requirement_graph


TIMESTAMP = datetime(2026, 5, 7, tzinfo=timezone.utc)


def test_render_wiki_notes_creates_grouped_markdown_drafts():
    graph = _sample_graph()

    notes = render_wiki_notes(
        knowledge_items=graph.knowledge_items,
        relationships=graph.relationships,
    )

    requirement_note = _note_by_id(notes, "REQ-001")
    source_note = _note_by_id(notes, "SRC-001")

    assert requirement_note.folder == "requirements"
    assert requirement_note.file_name == "REQ-001-warehouse-stock-movement.md"
    assert requirement_note.relative_path == (
        "requirements/REQ-001-warehouse-stock-movement.md"
    )
    assert source_note.folder == "sources"
    assert source_note.relative_path == "sources/SRC-001-source-src-001.md"


def test_requirement_note_contains_frontmatter_sections_and_wiki_links():
    graph = _sample_graph()

    notes = render_wiki_notes(
        knowledge_items=graph.knowledge_items,
        relationships=graph.relationships,
    )

    requirement_note = _note_by_id(notes, "REQ-001")

    assert requirement_note.markdown.startswith("---\n")
    assert "id: REQ-001\n" in requirement_note.markdown
    assert "type: requirement\n" in requirement_note.markdown
    assert "slug: warehouse-stock-movement\n" in requirement_note.markdown
    assert "status: draft\n" in requirement_note.markdown
    assert "sources:\n  - SRC-001\n" in requirement_note.markdown
    assert "# Warehouse Stock Movement\n" in requirement_note.markdown
    assert "## Summary\n" in requirement_note.markdown
    assert "## Related Notes\n" in requirement_note.markdown
    assert "[[ACT-001-operators]]" in requirement_note.markdown
    assert "[[ENT-001-stock]]" in requirement_note.markdown
    assert "[[WF-001-stock-movement-workflow]]" in requirement_note.markdown
    assert "[[REP-001-daily-dashboard]]" in requirement_note.markdown
    assert "[[DEC-001-role-based-access-rules]]" in requirement_note.markdown
    assert "[[SRC-001-source-src-001]]" in requirement_note.markdown
    assert requirement_note.linked_item_ids == (
        "ACT-001",
        "ACT-002",
        "ACT-003",
        "ENT-001",
        "ENT-002",
        "WF-001",
        "REP-001",
        "REP-002",
        "DEC-001",
        "SRC-001",
    )


def test_note_includes_open_questions_and_assumptions():
    graph = _sample_graph()
    item_data = graph.requirement.model_dump()
    item_data["open_questions"] = [
        {
            "question_id": "Q-001",
            "label": "[OPEN QUESTION]",
            "severity": "high",
            "question": "Who approves stock adjustments?",
        }
    ]
    item_data["assumptions"] = [
        {
            "assumption_id": "ASM-001",
            "label": "[ASSUMPTION]",
            "text": "Supervisors review rejected records.",
        }
    ]
    requirement = KnowledgeItemRecord(**item_data)
    items = (requirement,) + tuple(
        item for item in graph.knowledge_items if item.item_id != "REQ-001"
    )

    notes = render_wiki_notes(
        knowledge_items=items,
        relationships=graph.relationships,
    )

    markdown = _note_by_id(notes, "REQ-001").markdown
    assert "## Open Questions\n" in markdown
    assert "- [HIGH] Who approves stock adjustments?\n" in markdown
    assert "## Assumptions\n" in markdown
    assert "- [ASSUMPTION] Supervisors review rejected records.\n" in markdown


def test_renderer_rejects_relationships_with_missing_items():
    graph = _sample_graph()
    items = tuple(item for item in graph.knowledge_items if item.item_id != "ACT-001")

    with pytest.raises(WikiMarkdownRenderError) as exc_info:
        render_wiki_notes(
            knowledge_items=items,
            relationships=graph.relationships,
        )

    assert "ACT-001" in str(exc_info.value)


def _sample_graph():
    return build_requirement_graph(
        requirement_id="REQ-001",
        title="Warehouse Stock Movement",
        requirement_text=(
            "Warehouse operators scan stock during receiving, picking, packing, "
            "and dispatch. They record item code, quantity, location, date, "
            "status, and remarks. Supervisors approve adjustments and rejected "
            "records. Managers need daily dashboards and weekly exports. The "
            "system needs role-based access and audit history."
        ),
        source_ids=("SRC-001",),
        created_at=TIMESTAMP,
    )


def _note_by_id(notes, item_id):
    return next(note for note in notes if note.item_id == item_id)
