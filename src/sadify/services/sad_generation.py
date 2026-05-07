from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Sequence

from sadify.schemas import KnowledgeItemRecord, RelationshipRecord, SadVersionRecord


class SadGenerationError(ValueError):
    pass


_CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}


def generate_project_sad(
    *,
    sad_version_id: str,
    project_title: str,
    knowledge_items: Sequence[KnowledgeItemRecord],
    relationships: Sequence[RelationshipRecord],
    created_at: datetime | None = None,
    created_by: str,
    version_number: int = 1,
) -> SadVersionRecord:
    timestamp = created_at or datetime.now(UTC)
    item_groups = _group_items_by_type(knowledge_items)
    requirements = item_groups.get("requirement", [])
    if not requirements:
        raise SadGenerationError(
            "Project-level SAD generation requires at least one requirement item."
        )

    structured_sections = _build_structured_sections(
        project_title=project_title,
        item_groups=item_groups,
        relationships=relationships,
    )
    completeness_score = _aggregate_completeness(requirements)
    confidence_label = _aggregate_confidence(requirements, completeness_score)
    rendered_markdown = _render_sad_markdown(
        project_title=project_title,
        created_at=timestamp,
        completeness_score=completeness_score,
        confidence_label=confidence_label,
        structured_sections=structured_sections,
    )

    return SadVersionRecord(
        sad_version_id=sad_version_id,
        version_number=version_number,
        status="draft",
        created_at=timestamp,
        created_by=created_by,
        completeness_score=completeness_score,
        confidence_label=confidence_label,
        source_requirement_ids=[item.item_id for item in requirements],
        source_knowledge_item_ids=[item.item_id for item in knowledge_items],
        structured_sections=structured_sections,
        rendered_markdown=rendered_markdown,
        verification_result=_verification_result(),
    )


def _group_items_by_type(
    knowledge_items: Sequence[KnowledgeItemRecord],
) -> dict[str, list[KnowledgeItemRecord]]:
    item_groups: dict[str, list[KnowledgeItemRecord]] = {}
    for item in knowledge_items:
        item_groups.setdefault(item.item_type, []).append(item)
    return item_groups


def _build_structured_sections(
    *,
    project_title: str,
    item_groups: dict[str, list[KnowledgeItemRecord]],
    relationships: Sequence[RelationshipRecord],
) -> dict[str, Any]:
    requirements = item_groups.get("requirement", [])
    actors = item_groups.get("actor", [])
    entities = item_groups.get("entity", [])
    workflows = item_groups.get("workflow", [])
    decisions = item_groups.get("decision", [])
    reports = item_groups.get("report", [])
    sources = item_groups.get("source", [])

    open_questions = _open_questions(requirements)
    assumptions = _assumptions(requirements)

    return {
        "summary": _summary_section(project_title, requirements),
        "critical_gaps": _critical_gaps(open_questions),
        "functional_requirements": _functional_requirements(
            requirements=requirements,
            entities=entities,
            workflows=workflows,
            reports=reports,
        ),
        "non_functional_requirements": _non_functional_requirements(decisions),
        "business_rules": _item_section(decisions),
        "edge_cases": _edge_cases(open_questions),
        "data_entities": _item_section(entities),
        "workflows": _item_section(workflows),
        "developer_tasks": _developer_tasks(
            requirements=requirements,
            reports=reports,
            decisions=decisions,
        ),
        "assumptions": assumptions,
        "open_questions": open_questions,
        "source_traceability": _source_traceability(
            requirements=requirements,
            sources=sources,
        ),
        "stakeholders": _item_section(actors),
        "reports": _item_section(reports),
        "user_roles_permissions": _user_roles_permissions(actors, decisions),
        "integration_needs": [],
        "process_description": _process_description(workflows, relationships),
    }


def _summary_section(
    project_title: str,
    requirements: Sequence[KnowledgeItemRecord],
) -> dict[str, Any]:
    return {
        "project_title": project_title,
        "requirement_count": len(requirements),
        "source_requirement_ids": [item.item_id for item in requirements],
        "overview": (
            f"{project_title} combines {len(requirements)} requirement "
            "item(s) into a project-level SAD draft."
        ),
        "requirements": [
            {
                "requirement_id": item.item_id,
                "title": item.title,
                "summary": item.summary,
                "source_ids": item.source_ids,
            }
            for item in requirements
        ],
    }


def _functional_requirements(
    *,
    requirements: Sequence[KnowledgeItemRecord],
    entities: Sequence[KnowledgeItemRecord],
    workflows: Sequence[KnowledgeItemRecord],
    reports: Sequence[KnowledgeItemRecord],
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = [
        {
            "requirement_id": item.item_id,
            "priority": item.recommendation_priority,
            "statement": (
                f"The system shall support {item.title} based on the "
                "captured business requirement."
            ),
            "source_ids": item.source_ids,
        }
        for item in requirements
    ]
    sections.extend(
        {
            "requirement_id": item.item_id,
            "priority": item.recommendation_priority,
            "statement": f"The system shall record and maintain {item.title}.",
            "source_ids": item.source_ids,
        }
        for item in entities
    )
    sections.extend(
        {
            "requirement_id": item.item_id,
            "priority": item.recommendation_priority,
            "statement": f"The system shall support the {item.title}.",
            "source_ids": item.source_ids,
        }
        for item in workflows
    )
    sections.extend(
        {
            "requirement_id": item.item_id,
            "priority": item.recommendation_priority,
            "statement": f"The system shall produce {item.title}.",
            "source_ids": item.source_ids,
        }
        for item in reports
    )
    return sections


def _non_functional_requirements(
    decisions: Sequence[KnowledgeItemRecord],
) -> list[dict[str, Any]]:
    non_functional = [
        {
            "source_item_id": item.item_id,
            "requirement": (
                f"The system should enforce {item.title.lower()} consistently."
            ),
            "source_ids": item.source_ids,
        }
        for item in decisions
    ]
    non_functional.append(
        {
            "source_item_id": None,
            "requirement": (
                "The draft must remain reviewable before production use and "
                "must keep source traceability visible."
            ),
            "source_ids": [],
        }
    )
    return non_functional


def _item_section(
    items: Sequence[KnowledgeItemRecord],
) -> list[dict[str, Any]]:
    return [
        {
            "item_id": item.item_id,
            "title": item.title,
            "summary": item.summary,
            "confidence_label": item.confidence_label,
            "source_ids": item.source_ids,
        }
        for item in items
    ]


def _open_questions(
    requirements: Sequence[KnowledgeItemRecord],
) -> list[dict[str, str]]:
    questions: list[dict[str, str]] = []
    for requirement in requirements:
        questions.extend(
            {
                "requirement_id": requirement.item_id,
                "severity": question.severity,
                "question": question.question,
            }
            for question in requirement.open_questions
        )
    return questions


def _assumptions(
    requirements: Sequence[KnowledgeItemRecord],
) -> list[dict[str, str]]:
    assumptions: list[dict[str, str]] = []
    for requirement in requirements:
        assumptions.extend(
            {
                "requirement_id": requirement.item_id,
                "text": assumption.text,
            }
            for assumption in requirement.assumptions
        )
    return assumptions


def _critical_gaps(open_questions: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    return [
        question
        for question in open_questions
        if question["severity"] in {"critical", "high"}
    ]


def _edge_cases(open_questions: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    if not open_questions:
        return []
    return [
        {
            "requirement_id": question["requirement_id"],
            "description": (
                "Resolve this open question before treating related exception "
                f"handling as final: {question['question']}"
            ),
        }
        for question in open_questions
    ]


def _developer_tasks(
    *,
    requirements: Sequence[KnowledgeItemRecord],
    reports: Sequence[KnowledgeItemRecord],
    decisions: Sequence[KnowledgeItemRecord],
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = [
        {
            "task_id": f"TASK-{index:03d}",
            "title": f"Design and build {item.title}",
            "priority": item.recommendation_priority,
            "source_item_ids": [item.item_id],
        }
        for index, item in enumerate(requirements, start=1)
    ]
    next_index = len(tasks) + 1
    for item in tuple(reports) + tuple(decisions):
        tasks.append(
            {
                "task_id": f"TASK-{next_index:03d}",
                "title": f"Implement {item.title}",
                "priority": item.recommendation_priority,
                "source_item_ids": [item.item_id],
            }
        )
        next_index += 1
    return tasks


def _source_traceability(
    *,
    requirements: Sequence[KnowledgeItemRecord],
    sources: Sequence[KnowledgeItemRecord],
) -> list[dict[str, Any]]:
    explicit_source_ids = [source.item_id for source in sources]
    requirement_source_ids = [
        source_id
        for requirement in requirements
        for source_id in requirement.source_ids
    ]
    source_ids = _ordered_unique(explicit_source_ids + requirement_source_ids)
    source_titles = {source.item_id: source.title for source in sources}

    return [
        {
            "source_id": source_id,
            "title": source_titles.get(source_id, f"Source {source_id}"),
            "linked_requirement_ids": [
                requirement.item_id
                for requirement in requirements
                if source_id in requirement.source_ids
            ],
        }
        for source_id in source_ids
    ]


def _user_roles_permissions(
    actors: Sequence[KnowledgeItemRecord],
    decisions: Sequence[KnowledgeItemRecord],
) -> list[dict[str, Any]]:
    access_decisions = [
        decision
        for decision in decisions
        if "access" in decision.title.lower() or "permission" in decision.title.lower()
    ]
    return [
        {
            "actor_id": actor.item_id,
            "actor": actor.title,
            "permission_note": (
                "Confirm allowed create, view, edit, approve, and export actions."
            ),
            "decision_item_ids": [decision.item_id for decision in access_decisions],
        }
        for actor in actors
    ]


def _process_description(
    workflows: Sequence[KnowledgeItemRecord],
    relationships: Sequence[RelationshipRecord],
) -> list[dict[str, Any]]:
    workflow_ids = {workflow.item_id for workflow in workflows}
    return [
        {
            "workflow_id": workflow.item_id,
            "title": workflow.title,
            "description": workflow.summary,
            "relationship_ids": [
                relationship.relationship_id
                for relationship in relationships
                if relationship.target_item_id in workflow_ids
                and relationship.target_item_id == workflow.item_id
            ],
        }
        for workflow in workflows
    ]


def _aggregate_completeness(
    requirements: Sequence[KnowledgeItemRecord],
) -> int:
    return round(
        sum(requirement.completeness_score for requirement in requirements)
        / len(requirements)
    )


def _aggregate_confidence(
    requirements: Sequence[KnowledgeItemRecord],
    completeness_score: int,
) -> str:
    weakest_confidence = min(
        requirements,
        key=lambda item: _CONFIDENCE_ORDER[item.confidence_label],
    ).confidence_label
    if weakest_confidence == "low" or completeness_score <= 39:
        return "low"
    if weakest_confidence == "high" and completeness_score >= 85:
        return "high"
    return "medium"


def _render_sad_markdown(
    *,
    project_title: str,
    created_at: datetime,
    completeness_score: int,
    confidence_label: str,
    structured_sections: dict[str, Any],
) -> str:
    lines = [
        f"# {project_title} System Analysis And Design",
        "",
        f"Generated: {created_at.isoformat()}",
        "Status: Draft",
        "",
        "## Requirement Summary",
    ]
    lines.extend(_requirement_summary_lines(structured_sections["summary"]))
    lines.extend(
        [
            "",
            "## Completeness And Confidence",
            f"- Completeness: {completeness_score}%",
            f"- Confidence: {confidence_label}",
            (
                "- Requirements included: "
                f"{structured_sections['summary']['requirement_count']}"
            ),
            "",
            "## Critical Gaps And Open Questions",
        ]
    )
    lines.extend(_open_question_lines(structured_sections["open_questions"]))
    lines.extend(
        [
            "",
            "## Problem Statement",
            structured_sections["summary"]["overview"],
            "",
            "## Stakeholders",
        ]
    )
    lines.extend(_item_lines(structured_sections["stakeholders"]))
    lines.extend(["", "## Current Workflow"])
    lines.extend(_item_lines(structured_sections["workflows"]))
    lines.extend(["", "## Proposed Workflow"])
    lines.extend(_proposed_workflow_lines(structured_sections["workflows"]))
    lines.extend(["", "## Functional Requirements"])
    lines.extend(_statement_lines(structured_sections["functional_requirements"]))
    lines.extend(["", "## Non-Functional Requirements"])
    lines.extend(_statement_lines(structured_sections["non_functional_requirements"]))
    lines.extend(["", "## User Roles And Permissions"])
    lines.extend(_permission_lines(structured_sections["user_roles_permissions"]))
    lines.extend(["", "## Business Rules"])
    lines.extend(_item_lines(structured_sections["business_rules"]))
    lines.extend(["", "## Edge Cases And Exception Handling"])
    lines.extend(_edge_case_lines(structured_sections["edge_cases"]))
    lines.extend(["", "## Data Entities"])
    lines.extend(_item_lines(structured_sections["data_entities"]))
    lines.extend(["", "## Integration Needs"])
    lines.extend(_integration_lines(structured_sections["integration_needs"]))
    lines.extend(["", "## DFD-Style Process Description"])
    lines.extend(_process_lines(structured_sections["process_description"]))
    lines.extend(["", "## Developer Task Breakdown"])
    lines.extend(_task_lines(structured_sections["developer_tasks"]))
    lines.extend(["", "## Assumptions"])
    lines.extend(_assumption_lines(structured_sections["assumptions"]))
    lines.extend(["", "## Source Traceability"])
    lines.extend(_source_traceability_lines(structured_sections["source_traceability"]))
    return "\n".join(lines).rstrip() + "\n"


def _requirement_summary_lines(summary: dict[str, Any]) -> list[str]:
    return [
        f"- {requirement['requirement_id']}: {requirement['title']} - "
        f"{requirement['summary']}"
        for requirement in summary["requirements"]
    ]


def _open_question_lines(open_questions: Sequence[dict[str, str]]) -> list[str]:
    if not open_questions:
        return ["- No open questions recorded in canonical items."]
    return [
        "- "
        f"{question['requirement_id']} "
        f"[{question['severity'].upper()}] "
        f"[OPEN QUESTION] {question['question']}"
        for question in open_questions
    ]


def _item_lines(items: Sequence[dict[str, Any]]) -> list[str]:
    if not items:
        return ["- Not confirmed yet."]
    return [
        f"- {item['item_id']}: {item['title']} - {item['summary']}"
        for item in items
    ]


def _proposed_workflow_lines(workflows: Sequence[dict[str, Any]]) -> list[str]:
    if not workflows:
        return ["- Proposed workflow is not confirmed yet."]
    return [
        f"- Support {workflow['title']} with source-traceable records and review."
        for workflow in workflows
    ]


def _statement_lines(statements: Sequence[dict[str, Any]]) -> list[str]:
    if not statements:
        return ["- Not confirmed yet."]
    lines: list[str] = []
    for statement in statements:
        source_label = (
            statement.get("requirement_id")
            or statement.get("source_item_id")
            or "GENERAL"
        )
        statement_text = statement.get("statement") or statement["requirement"]
        lines.append(f"- {source_label}: {statement_text}")
    return lines


def _permission_lines(permissions: Sequence[dict[str, Any]]) -> list[str]:
    if not permissions:
        return ["- Roles and permissions are not confirmed yet."]
    return [
        f"- {permission['actor_id']}: {permission['actor']} - "
        f"{permission['permission_note']}"
        for permission in permissions
    ]


def _edge_case_lines(edge_cases: Sequence[dict[str, str]]) -> list[str]:
    if not edge_cases:
        return ["- No unresolved exception-handling questions recorded yet."]
    return [
        f"- {edge_case['requirement_id']}: {edge_case['description']}"
        for edge_case in edge_cases
    ]


def _integration_lines(integration_needs: Sequence[dict[str, Any]]) -> list[str]:
    if not integration_needs:
        return ["- No integration needs confirmed yet."]
    return [
        f"- {item['title']}: {item['summary']}"
        for item in integration_needs
    ]


def _process_lines(processes: Sequence[dict[str, Any]]) -> list[str]:
    if not processes:
        return ["- Process description is not confirmed yet."]
    return [
        f"- {process['workflow_id']}: {process['title']} - {process['description']}"
        for process in processes
    ]


def _task_lines(tasks: Sequence[dict[str, Any]]) -> list[str]:
    if not tasks:
        return ["- No developer tasks generated yet."]
    return [
        f"- {task['task_id']} [{task['priority']}]: {task['title']} "
        f"(source: {', '.join(task['source_item_ids'])})"
        for task in tasks
    ]


def _assumption_lines(assumptions: Sequence[dict[str, str]]) -> list[str]:
    if not assumptions:
        return ["- No assumptions recorded in canonical items."]
    return [
        f"- {assumption['requirement_id']}: [ASSUMPTION] {assumption['text']}"
        for assumption in assumptions
    ]


def _source_traceability_lines(sources: Sequence[dict[str, Any]]) -> list[str]:
    if not sources:
        return ["- No source files linked yet."]
    return [
        f"- {source['source_id']}: {source['title']} -> "
        f"{', '.join(source['linked_requirement_ids']) or 'no requirement link'}"
        for source in sources
    ]


def _verification_result() -> dict[str, Any]:
    return {
        "schema_validation": {
            "status": "passed",
            "issues": [],
        },
        "sad_quality_check": {
            "status": "not_run",
            "issues": [],
            "reason": (
                "Live final-SAD model quality verification is deferred for "
                "the local-first C11 slice."
            ),
        },
    }


def _ordered_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value in seen:
            continue
        unique_values.append(value)
        seen.add(value)
    return unique_values
