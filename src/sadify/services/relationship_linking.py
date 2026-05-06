from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re

from sadify.schemas import DriveFileRef, KnowledgeItemRecord, RelationshipRecord
from sadify.services.completeness_scoring import score_requirement_context


@dataclass(frozen=True)
class DetectedItem:
    item_type: str
    title: str
    relationship_type: str
    evidence_terms: tuple[str, ...]
    confidence_label: str = "medium"


@dataclass(frozen=True)
class RelationshipGraph:
    requirement: KnowledgeItemRecord
    knowledge_items: tuple[KnowledgeItemRecord, ...]
    relationships: tuple[RelationshipRecord, ...]

    def item_titles_by_type(self, item_type: str) -> list[str]:
        return [
            item.title for item in self.knowledge_items if item.item_type == item_type
        ]

    def relationship_types(self) -> list[str]:
        return [link.relationship_type for link in self.relationships]


@dataclass(frozen=True)
class _DetectionRule:
    item_type: str
    title: str
    relationship_type: str
    terms: tuple[str, ...]
    confidence_label: str = "medium"


_ACTOR_RULES = (
    _DetectionRule(
        item_type="actor",
        title="Operators",
        relationship_type="performed_by_actor",
        terms=("operator", "operators"),
        confidence_label="high",
    ),
    _DetectionRule(
        item_type="actor",
        title="Supervisors",
        relationship_type="performed_by_actor",
        terms=("supervisor", "supervisors"),
        confidence_label="high",
    ),
    _DetectionRule(
        item_type="actor",
        title="Managers",
        relationship_type="performed_by_actor",
        terms=("manager", "managers"),
        confidence_label="high",
    ),
    _DetectionRule(
        item_type="actor",
        title="Admins",
        relationship_type="performed_by_actor",
        terms=("admin", "admins", "administrator", "administrators"),
        confidence_label="medium",
    ),
    _DetectionRule(
        item_type="actor",
        title="Staff",
        relationship_type="performed_by_actor",
        terms=("staff",),
        confidence_label="medium",
    ),
    _DetectionRule(
        item_type="actor",
        title="Workers",
        relationship_type="performed_by_actor",
        terms=("worker", "workers", "field worker", "field workers"),
        confidence_label="medium",
    ),
)

_ENTITY_RULES = (
    _DetectionRule(
        item_type="entity",
        title="Stock",
        relationship_type="uses_entity",
        terms=("stock",),
        confidence_label="high",
    ),
    _DetectionRule(
        item_type="entity",
        title="Location",
        relationship_type="uses_entity",
        terms=("location", "locations", "block", "blocks", "field"),
        confidence_label="medium",
    ),
)

_WORKFLOW_RULES = (
    _DetectionRule(
        item_type="workflow",
        title="Stock Movement Workflow",
        relationship_type="uses_workflow",
        terms=(
            "stock movement",
            "receiving",
            "picking",
            "packing",
            "dispatch",
        ),
        confidence_label="high",
    ),
    _DetectionRule(
        item_type="workflow",
        title="Review Workflow",
        relationship_type="uses_workflow",
        terms=("review", "approve", "approval", "reject", "rejected"),
        confidence_label="medium",
    ),
)

_REPORT_RULES = (
    _DetectionRule(
        item_type="report",
        title="Daily Dashboard",
        relationship_type="produces_report",
        terms=("daily dashboard", "daily dashboards", "dashboard", "dashboards"),
        confidence_label="high",
    ),
    _DetectionRule(
        item_type="report",
        title="Weekly Export",
        relationship_type="produces_report",
        terms=("weekly export", "weekly exports", "export", "exports"),
        confidence_label="medium",
    ),
    _DetectionRule(
        item_type="report",
        title="Daily Report",
        relationship_type="produces_report",
        terms=("daily report", "daily reports", "report", "reports"),
        confidence_label="medium",
    ),
)

_DECISION_RULES = (
    _DetectionRule(
        item_type="decision",
        title="Role-Based Access Rules",
        relationship_type="records_decision",
        terms=("role-based access", "access", "permission", "permissions"),
        confidence_label="high",
    ),
    _DetectionRule(
        item_type="decision",
        title="Audit History Rules",
        relationship_type="records_decision",
        terms=("audit history", "audit trail", "history"),
        confidence_label="medium",
    ),
)

_RULE_GROUPS = (
    _ACTOR_RULES,
    _ENTITY_RULES,
    _WORKFLOW_RULES,
    _REPORT_RULES,
    _DECISION_RULES,
)

_ITEM_PREFIXES = {
    "actor": "ACT-",
    "entity": "ENT-",
    "workflow": "WF-",
    "report": "REP-",
    "decision": "DEC-",
}

_LABELS = {
    "performed_by_actor": "Requirement performed by actor",
    "uses_entity": "Requirement uses entity",
    "uses_workflow": "Requirement uses workflow",
    "produces_report": "Requirement produces report",
    "records_decision": "Requirement records decision",
    "supported_by_source": "Requirement supported by source",
}

_EXPLANATION_VERBS = {
    "performed_by_actor": "is performed or affected by",
    "uses_entity": "uses or records",
    "uses_workflow": "depends on",
    "produces_report": "produces or needs",
    "records_decision": "must reflect",
    "supported_by_source": "is supported by",
}


def build_requirement_graph(
    *,
    requirement_id: str,
    title: str,
    requirement_text: str,
    source_ids: tuple[str, ...] = (),
    created_at: datetime | None = None,
) -> RelationshipGraph:
    timestamp = created_at or datetime.now(UTC)
    normalized_text = " ".join(requirement_text.split())
    source_id_list = list(source_ids)

    detected_items: list[DetectedItem] = []
    if len(normalized_text.split()) >= 5:
        detected_items = _detect_items(normalized_text)

    source_items = tuple(
        DetectedItem(
            item_type="source",
            title=f"Source {source_id}",
            relationship_type="supported_by_source",
            evidence_terms=(source_id,),
            confidence_label="high",
        )
        for source_id in source_ids
    )
    all_detected_items = tuple(detected_items) + source_items
    item_ids = _assign_item_ids(all_detected_items)
    relationship_ids = [
        f"REL-{index:03d}" for index in range(1, len(all_detected_items) + 1)
    ]

    requirement = _build_knowledge_item(
        item_id=requirement_id,
        item_type="requirement",
        title=title,
        summary=_requirement_summary(normalized_text),
        relationship_ids=relationship_ids,
        source_ids=source_id_list,
        created_at=timestamp,
        completeness_score=_requirement_score(normalized_text),
        confidence_label=_requirement_confidence(normalized_text),
        problem_severity="high",
        recommendation_priority="must_have",
    )

    relationships = tuple(
        _build_relationship(
            relationship_id=relationship_id,
            requirement=requirement,
            target_item_id=item_ids[detected_item],
            detected_item=detected_item,
            evidence_source_ids=source_id_list,
            created_at=timestamp,
        )
        for relationship_id, detected_item in zip(relationship_ids, all_detected_items)
    )

    relationship_id_by_target = {
        relationship.target_item_id: relationship.relationship_id
        for relationship in relationships
    }
    knowledge_items = (requirement,) + tuple(
        _build_knowledge_item(
            item_id=item_ids[detected_item],
            item_type=detected_item.item_type,
            title=detected_item.title,
            summary=_detected_item_summary(detected_item),
            relationship_ids=[
                relationship_id_by_target[item_ids[detected_item]]
            ],
            source_ids=source_id_list,
            created_at=timestamp,
            completeness_score=_detected_item_score(detected_item),
            confidence_label=detected_item.confidence_label,
            problem_severity="medium",
            recommendation_priority="should_have",
        )
        for detected_item in all_detected_items
    )

    return RelationshipGraph(
        requirement=requirement,
        knowledge_items=knowledge_items,
        relationships=relationships,
    )


def _detect_items(requirement_text: str) -> list[DetectedItem]:
    detected_items: list[DetectedItem] = []
    seen: set[tuple[str, str]] = set()

    for rules in _RULE_GROUPS:
        group_matches: list[tuple[int, int, DetectedItem]] = []
        for rule in rules:
            matched_terms = _matching_terms(requirement_text, rule.terms)
            if not matched_terms:
                continue

            identity = (rule.item_type, _slugify(rule.title))
            if identity in seen:
                continue

            group_matches.append(
                (
                    _earliest_term_position(requirement_text, matched_terms),
                    len(group_matches),
                    DetectedItem(
                        item_type=rule.item_type,
                        title=rule.title,
                        relationship_type=rule.relationship_type,
                        evidence_terms=matched_terms,
                        confidence_label=rule.confidence_label,
                    ),
                )
            )
            seen.add(identity)

        group_matches.sort(key=lambda match: (match[0], match[1]))
        if rules[0].item_type in {"workflow", "decision"} and group_matches:
            detected_items.append(group_matches[0][2])
        else:
            detected_items.extend(
                detected_item for _, _, detected_item in group_matches
            )

    return detected_items


def _earliest_term_position(text: str, terms: tuple[str, ...]) -> int:
    normalized = text.lower()
    positions = [
        position
        for term in terms
        for position in [_term_position(normalized, term)]
        if position is not None
    ]
    return min(positions) if positions else len(normalized)


def _term_position(text: str, term: str) -> int | None:
    if " " in term or "-" in term:
        position = text.find(term)
        return position if position >= 0 else None

    match = re.search(rf"\b{re.escape(term)}s?\b", text)
    if match is None:
        return None
    return match.start()


def _matching_terms(text: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    normalized = text.lower()
    matches: list[str] = []
    for term in terms:
        if _term_matches(normalized, term):
            matches.append(term)
    return tuple(matches)


def _term_matches(text: str, term: str) -> bool:
    if " " in term or "-" in term:
        return term in text
    return re.search(rf"\b{re.escape(term)}s?\b", text) is not None


def _assign_item_ids(detected_items: tuple[DetectedItem, ...]) -> dict[DetectedItem, str]:
    counters = {item_type: 0 for item_type in _ITEM_PREFIXES}
    item_ids: dict[DetectedItem, str] = {}

    for detected_item in detected_items:
        if detected_item.item_type == "source":
            item_ids[detected_item] = detected_item.evidence_terms[0]
            continue

        counters[detected_item.item_type] += 1
        prefix = _ITEM_PREFIXES[detected_item.item_type]
        item_ids[detected_item] = f"{prefix}{counters[detected_item.item_type]:03d}"

    return item_ids


def _build_knowledge_item(
    *,
    item_id: str,
    item_type: str,
    title: str,
    summary: str,
    relationship_ids: list[str],
    source_ids: list[str],
    created_at: datetime,
    completeness_score: int,
    confidence_label: str,
    problem_severity: str,
    recommendation_priority: str,
) -> KnowledgeItemRecord:
    return KnowledgeItemRecord(
        item_id=item_id,
        item_type=item_type,
        slug=_slugify(title),
        title=title,
        status="draft",
        summary=summary,
        completeness_score=completeness_score,
        confidence_label=confidence_label,
        problem_severity=problem_severity,
        recommendation_priority=recommendation_priority,
        source_ids=source_ids,
        relationship_ids=relationship_ids,
        open_questions=[],
        assumptions=[],
        markdown_current=None,
        markdown_draft=None,
        markdown_status="not_generated",
        pending_change_summary=None,
        verification_result=None,
        drive_file=DriveFileRef(),
        created_at=created_at,
        updated_at=created_at,
    )


def _build_relationship(
    *,
    relationship_id: str,
    requirement: KnowledgeItemRecord,
    target_item_id: str,
    detected_item: DetectedItem,
    evidence_source_ids: list[str],
    created_at: datetime,
) -> RelationshipRecord:
    relationship_type = detected_item.relationship_type
    return RelationshipRecord(
        relationship_id=relationship_id,
        source_item_id=requirement.item_id,
        source_item_title=requirement.title,
        target_item_id=target_item_id,
        target_item_title=detected_item.title,
        relationship_type=relationship_type,
        relationship_label=_LABELS[relationship_type],
        explanation=_relationship_explanation(requirement.title, detected_item),
        confidence_label=detected_item.confidence_label,
        evidence_source_ids=evidence_source_ids,
        created_at=created_at,
        updated_at=created_at,
    )


def _relationship_explanation(
    requirement_title: str,
    detected_item: DetectedItem,
) -> str:
    verb = _EXPLANATION_VERBS[detected_item.relationship_type]
    return f"{requirement_title} {verb} {detected_item.title}."


def _requirement_score(requirement_text: str) -> int:
    return score_requirement_context(requirement_text).score


def _requirement_confidence(requirement_text: str) -> str:
    return score_requirement_context(requirement_text).confidence_label.lower()


def _detected_item_score(detected_item: DetectedItem) -> int:
    if detected_item.confidence_label == "high":
        return 80
    return 60


def _requirement_summary(requirement_text: str) -> str:
    if not requirement_text:
        return "Requirement captured without additional business context."
    return _clip_text(requirement_text, 180)


def _detected_item_summary(detected_item: DetectedItem) -> str:
    evidence = ", ".join(detected_item.evidence_terms[:3])
    if detected_item.item_type == "source":
        return f"Source evidence linked to the requirement: {detected_item.title}."
    return (
        f"Detected {detected_item.item_type} in the requirement: "
        f"{detected_item.title}. Evidence: {evidence}."
    )


def _clip_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "untitled"
