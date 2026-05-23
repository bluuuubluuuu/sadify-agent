import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from sadify_api.main import create_app
from sadify_api.schemas import RequirementAnalysisResponse, SadPreviewResponse
from sadify_api.services.sad_preview import (
    SadPreviewRepository,
    build_safe_sad_fallback_preview,
    build_sad_preview_context,
)
from sadify_api.services.gemini_structured import (
    SadPreviewModel,
    parse_sad_preview,
    sad_preview_schema,
)
from tests.api.test_gemini_structured import (
    EVENT_RENTAL_SOURCE_CONTEXT,
    TUITION_REQUEST,
    VALID_PAYLOAD as VALID_ANALYSIS,
)


VALID_PREVIEW = {
    "title": "Operational Workflow Validation",
    "temporary_notice": "Temporary preview. Review assumptions before saving.",
    "it_readiness": {
        "label": "Useful draft, needs review",
        "score": 72,
        "confidence": "Medium",
        "checklist": [
            {
                "id": "data",
                "label": "Data needed",
                "status": "ready",
                "reason": "The main source and expected records are described.",
            },
            {
                "id": "security",
                "label": "Access and security",
                "status": "needs_input",
                "reason": "User roles are known, but detailed permissions need review.",
            },
        ],
    },
    "sections": [
        {
            "title": "Problem",
            "body": "The team needs a clearer way to validate an operational workflow.",
            "source_references": ["SRC-000001"],
        },
        {
            "title": "Proposed system",
            "body": "SADify should capture the workflow, open risks, and developer-ready notes.",
            "source_references": [],
        },
    ],
    "assumptions": ["The preview is based on the current Q&A state only."],
    "open_questions": ["Who approves the final workflow before build starts?"],
    "source_references": ["SRC-000001"],
    "change_tracking": {
        "summary": "Temporary SAD preview created from current analysis.",
        "paths": [
            "SAD/preview",
            "Wiki/project-brain",
            "_SADify/manifest",
        ],
    },
}

CLINIC_REQUEST = (
    "Small clinic wants to track patient registration, queue status, doctor "
    "consultation, medicine collection, and payment in one simple system. "
    "Reception staff register patients and update queue status. Doctors record "
    "consultation notes. Pharmacy staff prepare medicine. Cashier records "
    "payment. Manager needs a daily summary of patients served, waiting time, "
    "and unpaid bills. Some patients may skip payment or leave before collecting "
    "medicine."
)

CLINIC_REQUEST_WITH_TRANSPORT_HISTORY = (
    f"{CLINIC_REQUEST}\n\n"
    "Previous question: [category: data_records][slot: critical_fields] Which "
    "details are essential on each record?\n\n"
    "Previous answer: Names or identifiers, Dates and statuses\n\n"
    "Previous readiness: 53"
)


class FakeSadPreviewModel(SadPreviewModel):
    def __init__(self, outputs: list[dict[str, object]]) -> None:
        self.outputs = outputs
        self.requests: list[tuple[str, bool]] = []

    def generate_preview(self, context: str, *, repair: bool = False) -> str:
        self.requests.append((context, repair))
        output = self.outputs.pop(0)
        return json.dumps(output)


def _analysis_with_blocking_basics() -> dict[str, object]:
    analysis = VALID_ANALYSIS.copy()
    analysis["readiness"] = {
        "label": "Ready for preview",
        "score": 76,
        "confidence": "Medium",
    }
    analysis["categories"] = [
        {"id": "problem", "label": "Problem", "status": "complete"},
        {"id": "goal", "label": "Goal", "status": "complete"},
        {"id": "users_roles", "label": "Users and roles", "status": "partial"},
        {"id": "workflow", "label": "Workflow", "status": "partial"},
        {"id": "it_readiness", "label": "IT readiness", "status": "partial"},
    ]
    return analysis


def test_parse_sad_preview_accepts_schema_valid_json():
    parsed = parse_sad_preview(json.dumps(VALID_PREVIEW))

    assert isinstance(parsed, SadPreviewResponse)
    assert parsed.it_readiness.score == 72
    assert parsed.sections[0].source_references == ["SRC-000001"]


def test_parse_sad_preview_rejects_score_outside_bounds():
    payload = VALID_PREVIEW.copy()
    payload["it_readiness"] = {
        **VALID_PREVIEW["it_readiness"],
        "score": 150,
    }

    with pytest.raises(ValidationError):
        parse_sad_preview(json.dumps(payload))


def test_sad_preview_schema_is_vertex_compatible_and_small():
    schema = sad_preview_schema()

    assert schema["type"] == "OBJECT"
    assert schema["propertyOrdering"][0] == "title"
    assert "$defs" not in schema
    assert schema["properties"]["it_readiness"]["properties"]["score"] == {
        "type": "INTEGER",
        "minimum": 0,
        "maximum": 100,
    }


def test_sad_preview_api_blocks_when_basics_are_missing():
    repository = SadPreviewRepository()
    model = FakeSadPreviewModel([VALID_PREVIEW.copy()])
    client = TestClient(
        create_app(
            sad_preview_model=model,
            sad_preview_repository=repository,
        )
    )

    response = client.post(
        "/sad/preview",
        json={
            "requirement_text": "Need to validate an operational workflow.",
            "analysis_id": "AN-000001",
            "analysis": VALID_ANALYSIS,
            "source_references": [],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["missing_basics"] == [
        "users_roles",
    ]
    assert repository.get_preview("SP-000001") is None
    assert model.requests == []


def test_missing_blocking_basics_blocks_when_a_required_slot_has_no_evidence():
    """Draft-ready needs >=90 score AND no applicable required slot at none."""
    from sadify_api.schemas import SlotEvidence
    from sadify_api.services.questionnaire_plan import (
        canonical_required_slots,
        create_plan_from_evidence,
    )

    slots = canonical_required_slots()
    verdicts = [
        SlotEvidence(
            category_id=category_id,
            slot_id=slot_id,
            strength="strong",
            evidence_quote="q",
        )
        for category_id, slot_id, _label in slots[:-1]
    ]
    verdicts.append(
        SlotEvidence(
            category_id=slots[-1][0],
            slot_id=slots[-1][1],
            strength="none",
        )
    )
    plan = create_plan_from_evidence(verdicts)
    assert any(
        slot.required and slot.applicable and slot.evidence_strength == "none"
        for category in plan.categories
        for slot in category.slots
    )

    analysis = VALID_ANALYSIS.copy()
    analysis["categories"] = [
        {"id": "problem", "label": "Problem", "status": "missing"},
        {"id": "goal", "label": "Goal", "status": "missing"},
        {"id": "users_roles", "label": "Users and roles", "status": "missing"},
        {"id": "workflow", "label": "Workflow", "status": "missing"},
    ]
    analysis["questionnaire"] = {
        "draft_readiness": {
            "label": plan.overall_readiness.label,
            "score": plan.overall_readiness.score,
            "confidence": "Medium",
        },
        "active_category_id": plan.active_category_id or slots[-1][0],
        "active_slot_id": slots[-1][1],
        "active_slot_label": slots[-1][2],
        "categories": [
            {
                "id": category.id,
                "label": category.label,
                "status": _questionnaire_status(category.status),
                "visibility": (
                    "completed" if category.status == "ready" else "main"
                ),
                "progress": _questionnaire_progress(category),
                "questions_total": sum(slot.required for slot in category.slots),
                "questions_answered": sum(
                    slot.required and slot.status == "covered"
                    for slot in category.slots
                ),
                "is_active": category.id == plan.active_category_id,
            }
            for category in plan.categories
        ],
        "answers": [],
        "diagnostics": ["Gemini structured output validated"],
    }
    repository = SadPreviewRepository()
    model = FakeSadPreviewModel([VALID_PREVIEW.copy()])
    client = TestClient(
        create_app(
            sad_preview_model=model,
            sad_preview_repository=repository,
        )
    )

    response = client.post(
        "/sad/preview",
        json={
            "requirement_text": "Need a system.",
            "analysis_id": "AN-000001",
            "analysis": analysis,
            "source_references": [],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["missing_basics"]
    assert repository.get_preview("SP-000001") is None
    assert model.requests == []


def test_sad_preview_api_allows_rich_request_when_one_question_state_is_still_incomplete():
    repository = SadPreviewRepository()
    model = FakeSadPreviewModel([VALID_PREVIEW.copy()])
    client = TestClient(
        create_app(
            sad_preview_model=model,
            sad_preview_repository=repository,
        )
    )
    analysis = VALID_ANALYSIS.copy()
    analysis["understanding_summary"] = (
        "The clinic requires a unified system to manage registration, queue "
        "management, consultation, medicine collection, payment, and daily reports "
        "for reception staff, doctors, pharmacy staff, cashier, and manager."
    )
    analysis["categories"] = [
        {"id": "problem", "label": "Problem", "status": "complete"},
        {"id": "workflow", "label": "Workflow", "status": "missing"},
    ]

    response = client.post(
        "/sad/preview",
        json={
            "requirement_text": (
                "Small clinic wants to track patient registration, queue status, "
                "doctor consultation, medicine collection, and payment in one simple "
                "system. Reception staff register patients and update queue status. "
                "Doctors record consultation notes. Pharmacy staff prepare medicine. "
                "Cashier records payment. Manager needs a daily summary of patients "
                "served, waiting time, and unpaid bills. Some patients may skip "
                "payment or leave before collecting medicine."
            ),
            "analysis_id": "AN-000001",
            "analysis": analysis,
            "source_references": ["Business Request"],
        },
    )

    assert response.status_code == 200
    assert response.json()["preview_id"] == "SP-000001"
    assert repository.get_preview("SP-000001") is not None


def test_sad_preview_api_allows_draft_ready_uploaded_source_with_minimal_typed_request():
    repository = SadPreviewRepository()
    model = FakeSadPreviewModel([VALID_PREVIEW.copy()])
    client = TestClient(
        create_app(
            sad_preview_model=model,
            sad_preview_repository=repository,
        )
    )
    analysis = VALID_ANALYSIS.copy()
    analysis["categories"] = [
        {"id": "problem", "label": "Problem", "status": "missing"},
        {"id": "goal", "label": "Goal", "status": "missing"},
        {"id": "users_roles", "label": "Users and roles", "status": "missing"},
        {"id": "workflow", "label": "Workflow", "status": "missing"},
    ]
    analysis["questionnaire"] = {
        "draft_readiness": {
            "label": "Ready for draft",
            "score": 100,
            "confidence": "Medium",
        },
        "active_category_id": "access_permissions",
        "active_slot_id": "override_handling",
        "active_slot_label": "Override handling",
        "categories": [
            {
                "id": "access_permissions",
                "label": "Access and permissions",
                "status": "ready",
                "visibility": "completed",
                "progress": 100,
                "questions_total": 1,
                "questions_answered": 1,
                "is_active": False,
            }
        ],
        "answers": [],
        "diagnostics": ["Gemini structured output validated"],
    }

    response = client.post(
        "/sad/preview",
        json={
            "requirement_text": (
                "Please analyse the uploaded event rental workflow and prepare "
                "the SAD preview."
            ),
            "analysis_id": "AN-000003",
            "analysis": analysis,
            "source_context": EVENT_RENTAL_SOURCE_CONTEXT,
            "source_references": ["SRC-000001"],
        },
    )

    assert response.status_code == 200
    assert response.json()["preview_id"] == "SP-000001"
    assert model.requests
    assert "event rental company" in model.requests[0][0]


def test_sad_preview_api_validates_model_output_and_saves_temporary_preview():
    repository = SadPreviewRepository()
    model = FakeSadPreviewModel([VALID_PREVIEW.copy()])
    client = TestClient(
        create_app(
            sad_preview_model=model,
            sad_preview_repository=repository,
        )
    )

    response = client.post(
        "/sad/preview",
        json={
            "requirement_text": "Need to validate an operational workflow.",
            "analysis_id": "AN-000001",
            "analysis": _analysis_with_blocking_basics(),
            "source_context": "[SRC-000001] workflow.md\nThe workflow needs approval.",
            "source_references": ["SRC-000001"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["preview_id"] == "SP-000001"
    assert payload["saved"] is True
    assert payload["preview"]["temporary_notice"].startswith("Temporary preview")
    assert payload["preview"]["it_readiness"]["checklist"][1]["status"] == "needs_input"
    assert payload["preview"]["open_questions"] == [
        "Who approves the final workflow before build starts?"
    ]
    assert payload["preview"]["source_references"] == ["SRC-000001"]
    assert payload["preview"]["change_tracking"]["paths"] == [
        "SAD/preview",
        "Wiki/project-brain",
        "_SADify/manifest",
    ]

    saved = repository.get_preview("SP-000001")
    assert saved is not None
    assert saved.analysis_id == "AN-000001"
    assert isinstance(saved.created_at, datetime)
    assert "Source context" in model.requests[0][0]


def test_sad_preview_api_repairs_once_before_saving_valid_output():
    broken_preview = VALID_PREVIEW.copy()
    broken_preview["it_readiness"] = {
        **VALID_PREVIEW["it_readiness"],
        "score": 150,
    }
    repository = SadPreviewRepository()
    model = FakeSadPreviewModel([broken_preview, VALID_PREVIEW.copy()])
    client = TestClient(
        create_app(
            sad_preview_model=model,
            sad_preview_repository=repository,
        )
    )

    response = client.post(
        "/sad/preview",
        json={
            "requirement_text": "Need to validate an operational workflow.",
            "analysis_id": "AN-000001",
            "analysis": _analysis_with_blocking_basics(),
            "source_references": [],
        },
    )

    assert response.status_code == 200
    assert response.json()["preview"]["it_readiness"]["score"] == 72
    assert model.requests[0][1] is False
    assert model.requests[1][1] is True


def test_sad_preview_api_saves_safe_fallback_after_invalid_retries():
    broken_preview = VALID_PREVIEW.copy()
    broken_preview["it_readiness"] = {
        **VALID_PREVIEW["it_readiness"],
        "score": 150,
    }
    repository = SadPreviewRepository()
    model = FakeSadPreviewModel([broken_preview, broken_preview])
    client = TestClient(
        create_app(
            sad_preview_model=model,
            sad_preview_repository=repository,
        )
    )

    response = client.post(
        "/sad/preview",
        json={
            "requirement_text": "Need to validate an operational workflow.",
            "analysis_id": "AN-000001",
            "analysis": _analysis_with_blocking_basics(),
            "source_references": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["preview_id"] == "SP-000001"
    assert payload["saved"] is True
    assert payload["preview"]["title"] == "System Analysis Document Draft"
    assert payload["preview"]["change_tracking"]["summary"] == (
        "Draft preview composed from confirmed request facts and Q&A answers."
    )
    assert payload["preview"]["source_references"] == ["Business Request"]
    assert repository.get_preview("SP-000001") is not None
    assert model.requests[0][1] is False
    assert model.requests[1][1] is True


def test_safe_sad_fallback_preview_merges_request_answers_and_diagnostics():
    analysis = _analysis_with_blocking_basics()
    analysis["assumptions"] = [
        "Fallback was used because Gemini returned invalid structured analysis after retry.",
        "The clinic operates as one location.",
    ]
    analysis["questionnaire"] = {
        "draft_readiness": {
            "label": "Ready for draft",
            "score": 100,
            "confidence": "High",
        },
        "active_category_id": "workflow_steps",
        "active_slot_id": None,
        "active_slot_label": None,
        "categories": [
            {
                "id": "workflow_steps",
                "label": "Workflow steps",
                "status": "ready",
                "visibility": "completed",
                "progress": 100,
                "questions_total": 2,
                "questions_answered": 2,
                "is_active": False,
            }
        ],
        "answers": [
            {
                "category_id": "workflow_steps",
                "slot_id": "exception_handling",
                "question": "How should incomplete visits be handled?",
                "answer": "Keep incomplete visits open for follow-up",
                "is_uncertain": False,
            }
        ],
        "diagnostics": ["structured-output fallback used"],
    }

    preview = build_safe_sad_fallback_preview(
        requirement_text=(
            "Small clinic wants to track patient registration, queue status, "
            "doctor consultation, medicine collection, and payment."
        ),
        analysis=RequirementAnalysisResponse.model_validate(analysis),
        source_references=["Business Request"],
    )

    joined_sections = "\n".join(section.body for section in preview.sections)
    assert "patient registration" in joined_sections
    assert "queue status" in joined_sections
    assert "keep incomplete visits open for follow-up" in joined_sections.lower()
    assert "Fallback was used" not in "\n".join(preview.assumptions)
    assert "The clinic operates as one location." in preview.assumptions
    assert preview.change_tracking.paths == ["SAD/preview"]


def test_safe_fallback_preview_renders_structured_sad_sections():
    analysis = _clinic_analysis_with_all_answers_and_amendments()

    preview = build_safe_sad_fallback_preview(
        requirement_text=CLINIC_REQUEST_WITH_TRANSPORT_HISTORY,
        analysis=RequirementAnalysisResponse.model_validate(analysis),
        source_references=["Business Request"],
    )

    titles = [section.title for section in preview.sections]
    assert "Confirmed Business Request" in titles
    assert "Executive Summary" in titles
    assert "Scope" in titles
    assert "Users and Responsibilities" in titles
    assert "Workflow" in titles
    assert "Data and Records" in titles
    assert "Business Rules and Approvals" in titles
    assert "Exceptions and Follow-Up" in titles
    assert "Reports and Summaries" in titles
    assert "Security and Privacy" in titles
    assert "Audit and History" in titles

    business_request = next(
        section.body
        for section in preview.sections
        if section.title == "Confirmed Business Request"
    )
    assert "Previous question:" not in business_request
    assert "Previous answer:" not in business_request
    assert "Previous readiness:" not in business_request

    joined = "\n".join(section.body for section in preview.sections)
    assert "Previous question:" not in joined
    assert "Previous answer:" not in joined
    assert "Previous readiness:" not in joined

    security = next(
        section.body
        for section in preview.sections
        if section.title == "Security and Privacy"
    )
    assert "encrypted" in security.lower()
    assert "dun downgrade" not in security
    assert "security controls must not be weakened" in security.lower()

    audit = next(
        section.body
        for section in preview.sections
        if section.title == "Audit and History"
    )
    assert "all user actions that affect system data must be recorded" in audit.lower()


def test_safe_fallback_preview_uses_business_facing_title_and_notice():
    analysis = _clinic_analysis_with_all_answers_and_amendments()

    preview = build_safe_sad_fallback_preview(
        requirement_text=CLINIC_REQUEST_WITH_TRANSPORT_HISTORY,
        analysis=RequirementAnalysisResponse.model_validate(analysis),
        source_references=["Business Request"],
    )

    visible_text = "\n".join(
        [
            preview.title,
            preview.temporary_notice,
            preview.it_readiness.label,
            preview.change_tracking.summary,
            *[section.title + "\n" + section.body for section in preview.sections],
        ]
    )

    assert "Clinic Patient Flow Management SAD Draft" == preview.title
    assert "Safe Temporary SAD Preview" not in visible_text
    assert "AI preview formatting" not in visible_text
    assert "Generated safe local preview" not in visible_text
    assert "_SADify/local-fallback" not in visible_text
    assert preview.it_readiness.score == 100
    assert preview.it_readiness.confidence == "High"


def test_safe_fallback_preview_synthesizes_sections_instead_of_repeating_request():
    analysis = _clinic_analysis_with_all_answers_and_amendments()

    preview = build_safe_sad_fallback_preview(
        requirement_text=CLINIC_REQUEST,
        analysis=RequirementAnalysisResponse.model_validate(analysis),
        source_references=["Business Request"],
    )

    section_map = {section.title: section.body for section in preview.sections}

    workflow = section_map["Workflow"]
    assert "1. Register patient" in workflow
    assert "2. Manage queue status" in workflow
    assert "3. Record doctor consultation" in workflow
    assert "4. Prepare and collect medicine" in workflow
    assert "5. Record payment and close visit" in workflow
    assert "If payment or medicine collection is skipped" in workflow

    data = section_map["Data and Records"]
    assert "Patient or visit identifier" in data
    assert "status timestamps" in data
    assert "responsible staff member" in data
    assert "amounts, notes, or reasons" in data

    request_repetition_count = sum(
        1
        for section in preview.sections
        if section.body == CLINIC_REQUEST
    )
    assert request_repetition_count == 0


def test_safe_fallback_preview_normalizes_user_amendments():
    analysis = _clinic_analysis_with_all_answers_and_amendments()

    preview = build_safe_sad_fallback_preview(
        requirement_text=CLINIC_REQUEST,
        analysis=RequirementAnalysisResponse.model_validate(analysis),
        source_references=["Business Request"],
    )

    section_map = {section.title: section.body for section in preview.sections}

    security = section_map["Security and Privacy"]
    assert "sensitive data must remain encrypted" in security.lower()
    assert "security controls must not be weakened" in security.lower()
    assert "dun downgrade" not in security
    assert "| Details:" not in security

    audit = section_map["Audit and History"]
    assert "all user actions that affect system data must be recorded" in audit.lower()
    assert "| Details:" not in audit


def test_safe_fallback_preview_synthesizes_workshop_maintenance_sad():
    analysis = _workshop_analysis_with_details()

    preview = build_safe_sad_fallback_preview(
        requirement_text=WORKSHOP_REQUEST,
        analysis=RequirementAnalysisResponse.model_validate(analysis),
        source_references=["Business Request"],
    )

    section_map = {section.title: section.body for section in preview.sections}
    joined = "\n".join(section_map.values()).lower()

    assert preview.title == "Maintenance Request Tracking System SAD Draft"
    assert "staff submit a maintenance request" in joined
    assert "supervisor assigns a technician" in joined
    assert "technician records diagnosis notes, parts used, repair status, and completion time" in joined
    assert "manager approval is required before expensive parts are used" in joined
    assert "requests stay open with a reason" in joined
    assert "weekly summary" in section_map["Reports and Summaries"].lower()
    assert "open requests" in section_map["Reports and Summaries"].lower()
    assert "completed repairs" in section_map["Reports and Summaries"].lower()
    assert "repeated machine issues" in section_map["Reports and Summaries"].lower()
    assert "parts cost" in section_map["Reports and Summaries"].lower()
    assert "overdue jobs" in section_map["Reports and Summaries"].lower()
    assert "staff can create and view their own requests" in section_map["Access and Permissions"].lower()
    assert "supervisors assign jobs" in section_map["Access and Permissions"].lower()
    assert "technicians update repair details" in section_map["Access and Permissions"].lower()
    assert "managers approve expensive parts and view reports" in section_map["Access and Permissions"].lower()
    assert "no external systems" in section_map["Integrations"].lower()
    assert "secure login" in section_map["Security and Privacy"].lower()
    assert "record every change with user and timestamp" in section_map["Audit and History"].lower()


def test_safe_fallback_preview_generic_event_request_does_not_leak_clinic_terms():
    event_request = EVENT_RENTAL_SOURCE_CONTEXT.split("Extracted text:\n", 1)[1]
    analysis = _analysis_with_blocking_basics()
    analysis["questionnaire"] = {
        "draft_readiness": {
            "label": "Ready for draft",
            "score": 100,
            "confidence": "Medium",
        },
        "active_category_id": "rules_approvals",
        "active_slot_id": None,
        "active_slot_label": None,
        "categories": _ready_questionnaire_categories(),
        "answers": [
            {
                "category_id": "data_records",
                "slot_id": "critical_fields",
                "question": "Which booking details are essential?",
                "answer": "Booking order, customer details, event date, rented items, deposit, balance due, delivery and return status",
                "is_uncertain": False,
            },
            {
                "category_id": "rules_approvals",
                "slot_id": "triggering_rules",
                "question": "Which event rental rule should be confirmed first?",
                "answer": "Booking cannot close until delivery and return status are complete",
                "is_uncertain": False,
            },
        ],
        "diagnostics": ["structured-output fallback used"],
    }

    preview = build_safe_sad_fallback_preview(
        requirement_text=event_request,
        analysis=RequirementAnalysisResponse.model_validate(analysis),
        source_references=["SRC-000001"],
    )

    visible = "\n".join(section.body for section in preview.sections).lower()
    assert "clinic" not in visible
    assert "patient" not in visible
    assert "visit" not in visible
    assert "booking" in visible
    assert "delivery" in visible


def test_safe_fallback_preview_synthesizes_tuition_sad_without_debug_leaks():
    preview = build_safe_sad_fallback_preview(
        requirement_text=TUITION_REQUEST,
        analysis=RequirementAnalysisResponse.model_validate(_tuition_analysis_with_answers()),
        source_references=["Business Request", "goal_scope.business_goal"],
    )

    visible = "\n".join(
        [
            preview.title,
            preview.temporary_notice,
            preview.change_tracking.summary,
            *preview.change_tracking.paths,
            *preview.source_references,
            *[
                section.title
                + "\n"
                + section.body
                + "\n"
                + ", ".join(section.source_references)
                for section in preview.sections
            ],
            *preview.open_questions,
            *preview.assumptions,
        ]
    )

    assert "fallback mechanism" not in visible.lower()
    assert "_SADify/local-fallback" not in visible
    assert "goal_scope.business_goal" not in visible
    assert "student enrolment" in visible.lower()
    assert "class schedules" in visible.lower()
    assert "attendance" in visible.lower()
    assert "fee" in visible.lower()
    assert "parent" in visible.lower()
    assert "multi-level approval" not in visible.lower()
    assert "incomplete visits" not in visible.lower()


def test_safe_fallback_preview_does_not_show_internal_understanding():
    analysis = _clinic_fallback_analysis_with_diagnostic_summary()

    preview = build_safe_sad_fallback_preview(
        requirement_text=CLINIC_REQUEST,
        analysis=RequirementAnalysisResponse.model_validate(analysis),
        source_references=["Business Request"],
    )

    joined = "\n".join(section.body for section in preview.sections)
    assert "SADify kept the business request" not in joined
    assert "Gemini's latest structured question could not be validated" not in joined


def test_safe_fallback_preview_does_not_promote_optional_question_as_core_gap_when_ready():
    analysis = _clinic_ready_analysis_with_optional_next_question()

    preview = build_safe_sad_fallback_preview(
        requirement_text=CLINIC_REQUEST,
        analysis=RequirementAnalysisResponse.model_validate(analysis),
        source_references=["Business Request"],
    )

    assert "Which staff access rule should be confirmed first?" not in preview.open_questions


def test_sad_preview_context_includes_questionnaire_answers():
    analysis = _analysis_with_blocking_basics()
    analysis["questionnaire"] = {
        "draft_readiness": {
            "label": "Ready for draft",
            "score": 100,
            "confidence": "High",
        },
        "active_category_id": "reports_summaries",
        "active_slot_id": None,
        "active_slot_label": None,
        "categories": [
            {
                "id": "reports_summaries",
                "label": "Reports and summaries",
                "status": "ready",
                "visibility": "completed",
                "progress": 100,
                "questions_total": 1,
                "questions_answered": 1,
                "is_active": False,
            }
        ],
        "answers": [
            {
                "category_id": "reports_summaries",
                "slot_id": "needed_outputs",
                "question": "Which summary does the manager need?",
                "answer": "Daily patients served and unpaid bills",
                "is_uncertain": False,
            }
        ],
        "diagnostics": [],
    }

    context = build_sad_preview_context(
        requirement_text="Need a clinic system.",
        analysis_id="AN-000001",
        analysis=RequirementAnalysisResponse.model_validate(analysis),
        source_context=None,
        source_references=[],
    )

    assert "Confirmed questionnaire answers:" in context
    assert "Which summary does the manager need?" in context
    assert "Daily patients served and unpaid bills" in context


def test_sad_preview_context_uses_synthesis_without_internal_fallback_assumptions():
    analysis = _analysis_with_blocking_basics()
    analysis["assumptions"] = [
        "Fallback was used because Gemini returned invalid structured analysis after retry.",
        "The clinic operates as one location.",
    ]
    analysis["questionnaire"] = {
        "draft_readiness": {
            "label": "Ready for draft",
            "score": 100,
            "confidence": "High",
        },
        "active_category_id": "workflow_steps",
        "active_slot_id": None,
        "active_slot_label": None,
        "categories": [
            {
                "id": "workflow_steps",
                "label": "Workflow steps",
                "status": "ready",
                "visibility": "completed",
                "progress": 100,
                "questions_total": 2,
                "questions_answered": 2,
                "is_active": False,
            }
        ],
        "answers": [
            {
                "category_id": "workflow_steps",
                "slot_id": "required_handling",
                "question": "How should incomplete visits be handled?",
                "answer": "Keep incomplete visits open for follow-up",
                "is_uncertain": False,
            }
        ],
        "diagnostics": ["structured-output fallback used"],
    }

    context = build_sad_preview_context(
        requirement_text=(
            "Small clinic wants to track patient registration, queue status, "
            "doctor consultation, medicine collection, and payment."
        ),
        analysis_id="AN-000010",
        analysis=RequirementAnalysisResponse.model_validate(analysis),
        source_context=None,
        source_references=["Business Request"],
    )

    assert "Confirmed request facts:" in context
    assert "Confirmed questionnaire answers:" in context
    business_section = context.split("Business-facing assumptions:", 1)[1]
    business_section = business_section.split("Business source references:", 1)[0]
    assert "Fallback was used" not in business_section
    assert "The clinic operates as one location." in business_section
    assert "Internal diagnostics, not for SAD assumptions:" in context


def _clinic_analysis_with_all_answers_and_amendments() -> dict[str, object]:
    analysis = _analysis_with_blocking_basics()
    analysis["understanding_summary"] = (
        "The clinic needs one simple system for registration, queue, consultation, "
        "medicine collection, payment, and manager reporting."
    )
    analysis["next_question"] = {
        "text": "Which staff access rule should be confirmed first?",
        "why_this_matters": "This is optional after the first draft is ready.",
        "choices": [
            {"id": "manager_approval", "label": "Require manager approval"},
            {"id": "audit_log", "label": "Allow temporary access with audit log"},
        ],
        "target_category": "access_permissions",
        "target_slot_id": "optional_access_rule",
        "selection_mode": "single",
    }
    analysis["questionnaire"] = {
        "draft_readiness": {
            "label": "Ready for draft",
            "score": 100,
            "confidence": "High",
        },
        "active_category_id": "non_functional",
        "active_slot_id": None,
        "active_slot_label": None,
        "categories": _ready_questionnaire_categories(),
        "answers": [
            {
                "category_id": "data_records",
                "slot_id": "critical_fields",
                "question": "Which details are essential on each record?",
                "answer": (
                    "Names or identifiers, Dates and statuses, Responsible staff "
                    "or owner, Amounts, notes, or reasons"
                ),
                "is_uncertain": False,
            },
            {
                "category_id": "rules_approvals",
                "slot_id": "triggering_rules",
                "question": "Which business rule should be confirmed first?",
                "answer": "A record cannot be completed until key steps are done",
                "is_uncertain": False,
            },
            {
                "category_id": "rules_approvals",
                "slot_id": "approval_path",
                "question": "How should a request move through approval?",
                "answer": "It goes through multiple approval levels",
                "is_uncertain": False,
            },
            {
                "category_id": "exceptions_edges",
                "slot_id": "required_handling",
                "question": "When that exception happens, what should staff do next?",
                "answer": "Mark it incomplete and keep it open",
                "is_uncertain": False,
            },
            {
                "category_id": "access_permissions",
                "slot_id": "access_model",
                "question": "How should access normally be organised?",
                "answer": "Role-based access",
                "is_uncertain": False,
            },
            {
                "category_id": "access_permissions",
                "slot_id": "sensitive_actions",
                "question": "Which actions need tighter permission control?",
                "answer": (
                    "Approve or reject work, Delete or overwrite records, Export "
                    "or share information, Change system settings"
                ),
                "is_uncertain": False,
            },
            {
                "category_id": "integrations",
                "slot_id": "external_systems",
                "question": "Which external systems must this connect with, if any?",
                "answer": "No external systems in the first version",
                "is_uncertain": False,
            },
            {
                "category_id": "non_functional",
                "slot_id": "security_privacy",
                "question": "Which security or privacy need matters most?",
                "answer": (
                    "Secure login, Restrict sensitive data by role, Keep personal "
                    "or confidential data protected | Details: keep all sensitive "
                    "data encrypted with optimized choice, dun downgrade"
                ),
                "is_uncertain": False,
            },
            {
                "category_id": "non_functional",
                "slot_id": "audit_history",
                "question": "What history must the system keep?",
                "answer": (
                    "Edits and corrections, Approvals and decisions, Status "
                    "changes, Exports or downloads | Details: any actions towards "
                    "the system and the data all must be recorded"
                ),
                "is_uncertain": False,
            },
        ],
        "diagnostics": ["structured-output fallback used"],
    }
    return analysis


WORKSHOP_REQUEST = (
    "A small equipment workshop wants to track maintenance requests for company "
    "machines. Staff submit a request when a machine has an issue. The workshop "
    "supervisor assigns a technician, and the technician records diagnosis notes, "
    "parts used, repair status, and completion time. Expensive parts require "
    "manager approval before use. If parts are unavailable or a job is overdue, "
    "the request stays open with a reason. The operations manager needs a weekly "
    "summary of open requests, completed repairs, repeated machine issues, parts "
    "cost, and overdue jobs. Staff can create and view their own requests, "
    "supervisors assign jobs, technicians update repair details, and managers "
    "approve expensive parts and view reports. No external systems are needed in "
    "the first version. The system must use secure login, restrict actions by "
    "role, and record every change with user and timestamp."
)


def _workshop_analysis_with_details() -> dict[str, object]:
    analysis = _analysis_with_blocking_basics()
    analysis["understanding_summary"] = (
        "The workshop needs a maintenance request tracking system for machine "
        "issues, assignment, technician repair updates, manager approvals, and "
        "weekly operations reporting."
    )
    analysis["questionnaire"] = {
        "draft_readiness": {
            "label": "Ready for draft",
            "score": 100,
            "confidence": "High",
        },
        "active_category_id": "rules_approvals",
        "active_slot_id": "decision_authority",
        "active_slot_label": "Decision authority",
        "categories": _ready_questionnaire_categories(),
        "answers": [
            {
                "category_id": "rules_approvals",
                "slot_id": "decision_authority",
                "question": "What value or rule makes a part expensive enough to require manager approval?",
                "answer": "Parts above a fixed cost threshold require manager approval",
                "is_uncertain": False,
            }
        ],
        "diagnostics": ["structured-output fallback used"],
    }
    return analysis


def _tuition_analysis_with_answers() -> dict[str, object]:
    analysis = _analysis_with_blocking_basics()
    analysis["understanding_summary"] = (
        "The tuition centre needs one simple system for enrolment, class "
        "schedules, attendance, fee payments, parent updates, and weekly manager "
        "summaries."
    )
    analysis["questionnaire"] = {
        "draft_readiness": {
            "label": "Ready for draft",
            "score": 100,
            "confidence": "High",
        },
        "active_category_id": "rules_approvals",
        "active_slot_id": None,
        "active_slot_label": None,
        "categories": _ready_questionnaire_categories(),
        "answers": [
            {
                "category_id": "rules_approvals",
                "slot_id": "approval_path",
                "question": "How should a request move through approval?",
                "answer": "It goes through multiple approval levels",
                "is_uncertain": False,
            },
            {
                "category_id": "exceptions_edges",
                "slot_id": "required_handling",
                "question": "When should parents be notified about absence or unpaid fees?",
                "answer": (
                    "Notify parents on the same day when a student is absent, "
                    "and notify parents when a fee remains unpaid after the due date"
                ),
                "is_uncertain": False,
            },
            {
                "category_id": "access_permissions",
                "slot_id": "sensitive_actions",
                "question": "Which tuition records need restricted edit access?",
                "answer": (
                    "Only admin or manager can edit fee payment records, Teachers "
                    "can correct attendance only with a reason, Parent contact "
                    "details are editable only by admin staff"
                ),
                "is_uncertain": False,
            },
        ],
        "diagnostics": ["structured-output fallback used"],
    }
    return analysis


def _clinic_fallback_analysis_with_diagnostic_summary() -> dict[str, object]:
    analysis = _clinic_analysis_with_all_answers_and_amendments()
    analysis["understanding_summary"] = (
        "SADify kept the business request and any answers already provided, but "
        "Gemini's latest structured question could not be validated."
    )
    return analysis


def _clinic_ready_analysis_with_optional_next_question() -> dict[str, object]:
    return _clinic_analysis_with_all_answers_and_amendments()


def _ready_questionnaire_categories() -> list[dict[str, object]]:
    return [
        {
            "id": category_id,
            "label": label,
            "status": "ready",
            "visibility": "completed",
            "progress": 100,
            "questions_total": 1,
            "questions_answered": 1,
            "is_active": False,
        }
        for category_id, label in [
            ("goal_scope", "Goal and scope"),
            ("users_roles", "Users and roles"),
            ("workflow_steps", "Workflow steps"),
            ("data_records", "Data and records"),
            ("rules_approvals", "Business rules and approvals"),
            ("exceptions_edges", "Exceptions and edge cases"),
            ("reports_summaries", "Reports and summaries"),
            ("access_permissions", "Access and permissions"),
            ("integrations", "Integrations"),
            ("non_functional", "Non-functional needs"),
        ]
    ]


def _questionnaire_status(plan_status: str) -> str:
    return {
        "needs_answer": "needed",
        "in_progress": "in_progress",
        "ready": "ready",
        "confirm_later": "needs_later_confirmation",
    }[plan_status]


def _questionnaire_progress(category) -> int:
    required_slots = [slot for slot in category.slots if slot.required]
    if not required_slots:
        return 100
    covered_slots = [
        slot for slot in required_slots if slot.status == "covered"
    ]
    return round(100 * len(covered_slots) / len(required_slots))
