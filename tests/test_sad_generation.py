from datetime import datetime, timezone

import pytest

from sadify.schemas import Assumption, OpenQuestion, SadVersionRecord
from sadify.services.relationship_linking import build_requirement_graph
from sadify.services.sad_generation import SadGenerationError, generate_project_sad


TIMESTAMP = datetime(2026, 5, 7, tzinfo=timezone.utc)


def test_generate_project_sad_creates_canonical_version_record():
    graph = _sample_graph()

    sad = generate_project_sad(
        sad_version_id="SAD-001",
        project_title="Warehouse Operations",
        knowledge_items=graph.knowledge_items,
        relationships=graph.relationships,
        created_at=TIMESTAMP,
        created_by="local-user",
    )

    assert isinstance(sad, SadVersionRecord)
    assert sad.sad_version_id == "SAD-001"
    assert sad.version_number == 1
    assert sad.status == "draft"
    assert sad.source_requirement_ids == ["REQ-001"]
    assert "REQ-001" in sad.source_knowledge_item_ids
    assert "ACT-001" in sad.source_knowledge_item_ids
    assert "SRC-001" in sad.source_knowledge_item_ids
    assert sad.completeness_score == 100
    assert sad.confidence_label == "high"
    assert sad.verification_result["schema_validation"]["status"] == "passed"
    assert sad.verification_result["sad_quality_check"]["status"] == "not_run"


def test_generated_sad_markdown_contains_required_sections_and_traceability():
    graph = _sample_graph()

    sad = generate_project_sad(
        sad_version_id="SAD-001",
        project_title="Warehouse Operations",
        knowledge_items=graph.knowledge_items,
        relationships=graph.relationships,
        created_at=TIMESTAMP,
        created_by="local-user",
    )

    markdown = sad.rendered_markdown
    assert markdown.startswith("# Warehouse Operations System Analysis And Design")
    for heading in (
        "## Requirement Summary",
        "## Completeness And Confidence",
        "## Critical Gaps And Open Questions",
        "## Stakeholders",
        "## Functional Requirements",
        "## Developer Task Breakdown",
        "## Source Traceability",
    ):
        assert heading in markdown
    assert "REQ-001" in markdown
    assert "SRC-001" in markdown
    assert "Operators" in markdown
    assert "Daily Dashboard" in markdown


def test_generated_sad_keeps_assumptions_and_open_questions_visible():
    graph = _sample_graph()
    requirement = graph.requirement.model_copy(
        update={
            "open_questions": [
                OpenQuestion(
                    question_id="Q-001",
                    label="[OPEN QUESTION]",
                    severity="high",
                    question="Who owns final stock adjustment approval?",
                )
            ],
            "assumptions": [
                Assumption(
                    assumption_id="ASM-001",
                    label="[ASSUMPTION]",
                    text="Supervisors are assumed to review rejected records.",
                )
            ],
        }
    )
    knowledge_items = (requirement,) + graph.knowledge_items[1:]

    sad = generate_project_sad(
        sad_version_id="SAD-001",
        project_title="Warehouse Operations",
        knowledge_items=knowledge_items,
        relationships=graph.relationships,
        created_at=TIMESTAMP,
        created_by="local-user",
    )

    assert sad.structured_sections["open_questions"] == [
        {
            "requirement_id": "REQ-001",
            "severity": "high",
            "question": "Who owns final stock adjustment approval?",
        }
    ]
    assert sad.structured_sections["assumptions"] == [
        {
            "requirement_id": "REQ-001",
            "text": "Supervisors are assumed to review rejected records.",
        }
    ]
    assert (
        "[OPEN QUESTION] Who owns final stock adjustment approval?"
        in sad.rendered_markdown
    )
    assert (
        "[ASSUMPTION] Supervisors are assumed to review rejected records."
        in sad.rendered_markdown
    )


def test_generate_project_sad_requires_at_least_one_requirement():
    graph = _sample_graph()
    non_requirement_items = tuple(
        item for item in graph.knowledge_items if item.item_type != "requirement"
    )

    with pytest.raises(SadGenerationError) as exc_info:
        generate_project_sad(
            sad_version_id="SAD-001",
            project_title="Warehouse Operations",
            knowledge_items=non_requirement_items,
            relationships=graph.relationships,
            created_at=TIMESTAMP,
            created_by="local-user",
        )

    assert "at least one requirement" in str(exc_info.value)


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
