from datetime import datetime, timezone

from sadify.schemas import KnowledgeItemRecord, RelationshipRecord
from sadify.services.relationship_linking import build_requirement_graph


TIMESTAMP = datetime(2026, 5, 6, tzinfo=timezone.utc)


def test_build_requirement_graph_creates_canonical_items_and_relationships():
    graph = build_requirement_graph(
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

    assert all(isinstance(item, KnowledgeItemRecord) for item in graph.knowledge_items)
    assert all(isinstance(link, RelationshipRecord) for link in graph.relationships)
    assert graph.requirement.item_id == "REQ-001"
    assert graph.item_titles_by_type("actor") == [
        "Operators",
        "Supervisors",
        "Managers",
    ]
    assert "Stock" in graph.item_titles_by_type("entity")
    assert "Location" in graph.item_titles_by_type("entity")
    assert "Stock Movement Workflow" in graph.item_titles_by_type("workflow")
    assert "Daily Dashboard" in graph.item_titles_by_type("report")
    assert "Weekly Export" in graph.item_titles_by_type("report")
    assert "Role-Based Access Rules" in graph.item_titles_by_type("decision")
    assert "Source SRC-001" in graph.item_titles_by_type("source")
    assert graph.relationship_types() == [
        "performed_by_actor",
        "performed_by_actor",
        "performed_by_actor",
        "uses_entity",
        "uses_entity",
        "uses_workflow",
        "produces_report",
        "produces_report",
        "records_decision",
        "supported_by_source",
    ]
    assert graph.relationships[-1].evidence_source_ids == ["SRC-001"]


def test_graph_builder_deduplicates_repeated_people_terms():
    graph = build_requirement_graph(
        requirement_id="REQ-001",
        title="Supervisor Review",
        requirement_text="Supervisors and supervisor review records with operators.",
        created_at=TIMESTAMP,
    )

    assert graph.item_titles_by_type("actor") == ["Supervisors", "Operators"]


def test_vague_input_creates_only_requirement_item():
    graph = build_requirement_graph(
        requirement_id="REQ-001",
        title="Plantation App",
        requirement_text="Need an app.",
        created_at=TIMESTAMP,
    )

    assert [item.item_id for item in graph.knowledge_items] == ["REQ-001"]
    assert graph.relationships == ()


def test_relationship_records_have_plain_explanations_and_source_traceability():
    graph = build_requirement_graph(
        requirement_id="REQ-001",
        title="Daily Harvest Records",
        requirement_text=(
            "Field workers record harvest by block and activity. "
            "Supervisors review daily reports."
        ),
        source_ids=("SRC-001", "SRC-002"),
        created_at=TIMESTAMP,
    )

    first_link = graph.relationships[0]
    assert first_link.relationship_label == "Requirement performed by actor"
    assert "Daily Harvest Records" in first_link.explanation
    assert first_link.evidence_source_ids == ["SRC-001", "SRC-002"]
    assert all("api_key" not in link.explanation.lower() for link in graph.relationships)
