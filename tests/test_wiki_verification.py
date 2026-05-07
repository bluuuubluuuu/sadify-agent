from datetime import datetime, timezone

import pytest

from sadify.renderers.wiki_markdown import render_wiki_notes
from sadify.services.relationship_linking import build_requirement_graph
from sadify.services.wiki_verification import (
    WikiApprovalError,
    approve_wiki_draft,
    prepare_wiki_draft_for_approval,
    reject_wiki_draft,
    verify_wiki_note,
)


TIMESTAMP = datetime(2026, 5, 7, tzinfo=timezone.utc)


def test_verify_wiki_note_passes_structural_checks():
    _, notes = _sample_notes()
    note = _note_by_id(notes, "REQ-001")

    result = verify_wiki_note(note, all_notes=notes)

    assert result.status == "passed"
    assert result.issues == ()
    assert result.to_dict() == {"status": "passed", "issues": []}


def test_verify_wiki_note_reports_missing_sections_and_broken_links():
    _, notes = _sample_notes()
    note = _note_by_id(notes, "REQ-001")
    broken_note = note.with_markdown(
        note.markdown.replace("## Sources\n", "").replace(
            "[[ACT-001-operators]]",
            "[[ACT-404-missing]]",
        )
    )

    result = verify_wiki_note(broken_note, all_notes=notes)

    assert result.status == "failed"
    assert [issue.code for issue in result.issues] == [
        "missing_sources_section",
        "broken_wiki_link",
    ]


def test_prepare_wiki_draft_for_approval_sets_pending_fields():
    graph, notes = _sample_notes()
    item = graph.requirement
    note = _note_by_id(notes, "REQ-001")

    pending_item = prepare_wiki_draft_for_approval(
        item=item,
        note=note,
        all_notes=notes,
    )

    assert pending_item.markdown_current is None
    assert pending_item.markdown_draft == note.markdown
    assert pending_item.markdown_status == "pending_human_approval"
    assert pending_item.pending_change_summary == (
        "Generated wiki draft for Warehouse Stock Movement. "
        "Rule checks passed. Awaiting owner approval."
    )
    assert pending_item.verification_result["rule_based"]["status"] == "passed"
    assert pending_item.verification_result["gemini_quality"]["status"] == "not_run"
    assert pending_item.verification_result["human_review"]["status"] == "pending"


def test_owner_approval_promotes_draft_to_current_note():
    graph, notes = _sample_notes()
    pending_item = prepare_wiki_draft_for_approval(
        item=graph.requirement,
        note=_note_by_id(notes, "REQ-001"),
        all_notes=notes,
    )

    approved_item = approve_wiki_draft(
        pending_item,
        reviewed_by="owner@example.com",
        reviewed_at=TIMESTAMP,
    )

    assert approved_item.markdown_current == pending_item.markdown_draft
    assert approved_item.markdown_draft is None
    assert approved_item.markdown_status == "verified"
    assert approved_item.verification_result["human_review"]["status"] == "approved"
    assert approved_item.verification_result["human_review"]["reviewed_by"] == (
        "owner@example.com"
    )


def test_owner_rejection_keeps_current_note_and_records_reason():
    graph, notes = _sample_notes()
    item = graph.requirement.model_copy(
        update={"markdown_current": "# Existing verified note\n"}
    )
    pending_item = prepare_wiki_draft_for_approval(
        item=item,
        note=_note_by_id(notes, "REQ-001"),
        all_notes=notes,
    )

    rejected_item = reject_wiki_draft(
        pending_item,
        reviewed_by="owner@example.com",
        reason="Need to confirm manager report wording.",
        reviewed_at=TIMESTAMP,
    )

    assert rejected_item.markdown_current == "# Existing verified note\n"
    assert rejected_item.markdown_draft is None
    assert rejected_item.markdown_status == "rejected"
    assert rejected_item.pending_change_summary == (
        "Rejected by owner@example.com: Need to confirm manager report wording."
    )
    assert rejected_item.verification_result["human_review"]["status"] == "rejected"


def test_owner_approval_requires_pending_verified_draft():
    graph, _ = _sample_notes()

    with pytest.raises(WikiApprovalError) as exc_info:
        approve_wiki_draft(
            graph.requirement,
            reviewed_by="owner@example.com",
            reviewed_at=TIMESTAMP,
        )

    assert "pending_human_approval" in str(exc_info.value)


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


def _sample_notes():
    graph = _sample_graph()
    return graph, render_wiki_notes(
        knowledge_items=graph.knowledge_items,
        relationships=graph.relationships,
    )


def _note_by_id(notes, item_id):
    return next(note for note in notes if note.item_id == item_id)
