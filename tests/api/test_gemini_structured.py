import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from sadify_api.main import create_app
from sadify_api.schemas import RequirementAnalysisResponse
from sadify_api.services.analysis_state import RequirementAnalysisRepository
from sadify_api.services.gemini_structured import (
    RequirementAnalysisModel,
    _sad_preview_prompt,
    parse_requirement_analysis,
    requirement_analysis_schema,
)
from sadify_api.services.questionnaire_plan import canonical_required_slots
from sadify_api.routes.analysis import _fallback_question


VALID_PAYLOAD = {
    "understanding_summary": "The team needs a system to track operational work.",
    "readiness": {
        "label": "Getting started",
        "score": 35,
        "confidence": "Medium",
    },
    "categories": [
        {"id": "problem", "label": "Problem", "status": "partial"},
        {"id": "users_roles", "label": "Users/Roles", "status": "missing"},
    ],
    "next_question": {
        "text": "What business goal should this request help achieve?",
        "why_this_matters": "This clarifies the business goal.",
        "choices": [
            {"id": "reduce_delay", "label": "Reduce delays"},
            {"id": "reduce_errors", "label": "Reduce errors"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "goal_scope",
        "target_slot_id": "business_goal",
    },
    "assumptions": [],
    "source_references": [],
    "proposed_extra_categories": [],
}

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

TUITION_REQUEST = (
    "A small tuition centre wants a simple system to track student enrolment, "
    "class schedules, attendance, fee payments, and parent updates. Admin staff "
    "register students and assign them to classes. Teachers mark attendance and "
    "add short progress notes. Parents should receive updates when students are "
    "absent or fees are unpaid. The centre manager needs a weekly summary of "
    "enrolled students, attendance issues, unpaid fees, and classes that are full."
)

SIMPLE_BAKERY_REQUEST = (
    "A small bakery wants a system to track custom cake orders. Staff record "
    "customer details, cake type, pickup date, deposit, balance due, and special "
    "instructions. Bakers update preparation status. Some orders may be changed, "
    "cancelled, delayed, or unpaid. The owner needs a daily summary of new orders, "
    "ready orders, overdue pickups, unpaid balances, and cancelled orders."
)

LAUNDRY_SOURCE_CONTEXT = (
    "[SRC-000001] laundry-workflow.txt (txt)\n"
    "Summary: 759 readable characters extracted.\n"
    "Extracted text:\n"
    "A small laundry shop wants a simple system to track customer laundry orders "
    "from drop-off to pickup. Counter staff create orders, record customer "
    "contact, item count, service type, due date, payment status, and special "
    "instructions. Laundry staff update washing, drying, ironing, and packing "
    "status. Some orders are delayed, damaged, missing items, or not collected "
    "by customers. Customers should receive updates when an order is ready or "
    "delayed. The shop owner needs a daily summary of new orders, ready-for-pickup "
    "orders, overdue orders, unpaid orders, and complaints. No external systems "
    "are needed in the first version. The system should use staff login, restrict "
    "payment edits to counter staff or owner, and keep a history of status and "
    "payment changes."
)

EVENT_RENTAL_SOURCE_CONTEXT = (
    "[SRC-000001] event-rental-workflow.pdf (pdf)\n"
    "Summary: 1 PDF page checked.\n"
    "Extracted text:\n"
    "A small event rental company wants a simple system to track equipment "
    "bookings, delivery schedules, return status, damage reports, deposits, "
    "and final payments. Sales staff create booking orders and record customer "
    "details, event date, rented items, deposit amount, balance due, and "
    "delivery address. Warehouse staff prepare items and update packed, "
    "delivered, returned, and damaged status. Drivers update delivery and "
    "pickup completion. Some items may be returned late, damaged, missing, "
    "or substituted. Customers should receive updates when delivery is "
    "scheduled, items are changed, or payment is overdue. The owner needs a "
    "weekly summary of upcoming bookings, delivered orders, late returns, "
    "damaged items, unpaid balances, and item availability. No external "
    "systems are needed in the first version. The system should use staff "
    "login, restrict payment and damage adjustments to sales staff or owner, "
    "and keep a history of booking, delivery, return, payment, and damage "
    "changes."
)


class FakeRequirementAnalysisModel(RequirementAnalysisModel):
    def __init__(self, outputs: list[dict[str, object]]) -> None:
        self.outputs = outputs
        self.requests: list[tuple[str, bool]] = []

    def analyze_requirement(self, requirement_text: str, *, repair: bool = False) -> str:
        self.requests.append((requirement_text, repair))
        output = self.outputs.pop(0)
        return json.dumps(output)


def test_parse_requirement_analysis_accepts_schema_valid_json():
    parsed = parse_requirement_analysis(json.dumps(VALID_PAYLOAD))

    assert isinstance(parsed, RequirementAnalysisResponse)
    assert parsed.readiness.score == 35
    assert parsed.next_question.choices[-1].id == "not_sure"


def test_parse_requirement_analysis_rejects_score_outside_bounds():
    payload = VALID_PAYLOAD.copy()
    payload["readiness"] = {
        "label": "Impossible",
        "score": 150,
        "confidence": "High",
    }

    with pytest.raises(ValidationError):
        parse_requirement_analysis(json.dumps(payload))


def test_requirement_analysis_schema_is_vertex_compatible_and_small():
    schema = requirement_analysis_schema()

    assert schema["type"] == "OBJECT"
    assert schema["propertyOrdering"][0] == "understanding_summary"
    assert "$defs" not in schema
    assert schema["properties"]["readiness"]["properties"]["score"] == {
        "type": "INTEGER",
        "minimum": 0,
        "maximum": 100,
    }


def test_analysis_schema_includes_slot_evidence():
    schema = requirement_analysis_schema()
    assert "slot_evidence" in schema["properties"]
    assert "slot_evidence" in schema["required"]
    item = schema["properties"]["slot_evidence"]["items"]
    assert item["properties"]["strength"]["enum"] == ["none", "partial", "strong"]
    assert item["properties"]["applicability"]["enum"] == [
        "applicable",
        "not_applicable",
    ]


def test_canonical_required_slots_lists_every_required_slot():
    from sadify_api.services.questionnaire_plan import canonical_required_slots

    slots = canonical_required_slots()
    assert ("goal_scope", "business_goal") in {
        (entry[0], entry[1]) for entry in slots
    }
    assert all(len(entry) == 3 for entry in slots)


def _slot_verdict(
    category_id,
    slot_id,
    quote,
    *,
    strength="strong",
    applicability="applicable",
):
    return {
        "category_id": category_id,
        "slot_id": slot_id,
        "applicability": applicability,
        "strength": strength,
        "evidence_quote": quote if strength != "none" else "",
        "rationale": "stated in the supplied material",
    }


def _payload_with_evidence(verdicts, base_payload=None):
    payload = json.loads(json.dumps(base_payload or VALID_PAYLOAD))
    choices = payload.get("next_question", {}).get("choices", [])
    if len(choices) == 1:
        choices.append({"id": "not_sure", "label": "Not sure"})
    payload["slot_evidence"] = verdicts
    return payload


def _payload_with_strong_slots(base_payload, slot_pairs, quote):
    return _payload_with_evidence(
        [
            _slot_verdict(category_id, slot_id, quote)
            for category_id, slot_id in slot_pairs
        ],
        base_payload,
    )


def _all_required_evidence(quote):
    return [
        _slot_verdict(category_id, slot_id, quote)
        for category_id, slot_id, _label in canonical_required_slots()
    ]


def test_analysis_readiness_reflects_strong_evidence():
    strong = [
        {
            "category_id": category_id,
            "slot_id": slot_id,
            "applicability": "applicable",
            "strength": "strong",
            "evidence_quote": "track maintenance requests",
            "rationale": "stated in the request",
        }
        for category_id, slot_id, _label in __import__(
            "sadify_api.services.questionnaire_plan",
            fromlist=["canonical_required_slots"],
        ).canonical_required_slots()
    ]
    model = FakeRequirementAnalysisModel([_payload_with_evidence(strong)])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=RequirementAnalysisRepository(),
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={"requirement_text": "Track maintenance requests for company machines."},
    )

    assert response.status_code == 200
    questionnaire = response.json()["analysis"]["questionnaire"]
    assert questionnaire["draft_readiness"]["score"] >= 90


def test_analysis_readiness_low_when_no_evidence():
    model = FakeRequirementAnalysisModel([_payload_with_evidence([])])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=RequirementAnalysisRepository(),
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={"requirement_text": "We want a system for our team."},
    )

    questionnaire = response.json()["analysis"]["questionnaire"]
    assert questionnaire["draft_readiness"]["score"] < 40
    assert questionnaire["draft_readiness"]["confidence"] == "Low"


def test_analysis_downgrades_evidence_with_fabricated_quote():
    fabricated = [
        {
            "category_id": "goal_scope",
            "slot_id": "business_goal",
            "applicability": "applicable",
            "strength": "strong",
            "evidence_quote": "a sentence that is nowhere in the request",
            "rationale": "fabricated",
        }
    ]
    model = FakeRequirementAnalysisModel([_payload_with_evidence(fabricated)])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=RequirementAnalysisRepository(),
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={"requirement_text": "We want a simple internal system."},
    )

    questionnaire = response.json()["analysis"]["questionnaire"]
    diagnostics = " ".join(questionnaire["diagnostics"]).lower()
    assert "downgraded" in diagnostics


def test_sad_preview_prompt_guards_confirmed_facts_and_diagnostics():
    prompt = _sad_preview_prompt("Confirmed request facts:\nClinic flow", repair=False)

    assert "Confirmed request facts are authoritative" in prompt
    assert "Do not turn internal diagnostics into SAD assumptions" in prompt
    assert "Layer 1 draft readiness and Layer 2 IT readiness are different" in prompt


def test_analysis_api_validates_model_output_and_saves_state():
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([VALID_PAYLOAD.copy()])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "guest_draft_id": "GD-000001",
            "requirement_text": "Need a simple way to validate operational ideas.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_id"] == "AN-000001"
    assert payload["saved"] is True
    assert payload["analysis"]["readiness"]["score"] == 35
    assert payload["analysis"]["next_question"]["choices"][-1]["id"] == "not_sure"
    assert payload["analysis"]["questionnaire"]["active_category_id"] == "goal_scope"
    assert payload["analysis"]["questionnaire"]["draft_readiness"]["score"] >= 0

    saved = repository.get_analysis("AN-000001")
    assert saved is not None
    assert saved.guest_draft_id == "GD-000001"
    assert saved.analysis.next_question.target_category == "goal_scope"
    assert isinstance(saved.created_at, datetime)
    assert [repair for _, repair in model.requests] == [False]
    assert "Need a simple way to validate operational ideas." in model.requests[0][0]
    assert "active_category_id: goal_scope" in model.requests[0][0]


def test_analysis_api_locks_first_turn_to_first_open_slot_in_plan_order():
    wrong_first_turn_payload = VALID_PAYLOAD.copy()
    wrong_first_turn_payload["next_question"] = {
        "text": "Who will use this system most often?",
        "why_this_matters": "This defines roles and permissions.",
        "choices": [
            {"id": "frontline", "label": "Frontline staff"},
            {"id": "supervisor", "label": "Supervisors"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "users_roles",
        "target_slot_id": "primary_users",
    }
    repaired_payload = VALID_PAYLOAD.copy()
    repaired_payload["next_question"] = {
        "text": "What outcome should this request help the business reach?",
        "why_this_matters": "This clarifies the business goal.",
        "choices": [
            {"id": "reduce_delay", "label": "Reduce delays"},
            {"id": "reduce_errors", "label": "Reduce errors"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "goal_scope",
        "target_slot_id": "business_goal",
    }
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel(
        [wrong_first_turn_payload, repaired_payload]
    )
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={"requirement_text": "Need help clarifying a new request."},
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["questionnaire"]["active_category_id"] == "goal_scope"
    assert analysis["questionnaire"]["active_slot_id"] == "business_goal"
    assert analysis["next_question"]["target_category"] == "goal_scope"
    assert analysis["next_question"]["target_slot_id"] == "business_goal"
    assert [repair for _, repair in model.requests] == [False]
    assert "active_category_id: goal_scope" in model.requests[0][0]
    assert "target_slot_id: business_goal" in model.requests[0][0]


def test_analysis_api_seeds_initial_slots_from_clear_clinic_request():
    clinic_payload = VALID_PAYLOAD.copy()
    clinic_payload["next_question"] = {
        "text": "Which fields are most important to capture first?",
        "why_this_matters": "This clarifies the first record design.",
        "choices": [
            {"id": "patient", "label": "Patient registration fields"},
            {"id": "payment", "label": "Payment and unpaid bill fields"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "data_records",
        "target_slot_id": "critical_fields",
    }
    clinic_payload = _payload_with_strong_slots(
        clinic_payload,
        [
            ("goal_scope", "business_goal"),
            ("goal_scope", "in_scope_outcome"),
            ("users_roles", "primary_users"),
            ("users_roles", "responsibilities"),
            ("workflow_steps", "normal_flow"),
            ("workflow_steps", "handoffs"),
            ("data_records", "main_records"),
        ],
        "Small clinic",
    )
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([clinic_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Small clinic wants to track patient registration, queue status, "
                "doctor consultation, medicine collection, and payment in one simple "
                "system. Reception staff register patients and update queue status. "
                "Doctors record consultation notes. Pharmacy staff prepare medicine. "
                "Cashier records payment. Manager needs a daily summary of patients "
                "served, waiting time, and unpaid bills. Some patients may skip payment "
                "or leave before collecting medicine."
            )
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    categories = {
        category["id"]: category
        for category in analysis["questionnaire"]["categories"]
    }
    assert analysis["questionnaire"]["draft_readiness"]["score"] > 0
    assert categories["goal_scope"]["visibility"] == "already_understood"
    assert categories["users_roles"]["visibility"] == "already_understood"
    assert categories["workflow_steps"]["visibility"] == "already_understood"
    assert categories["data_records"]["status"] == "in_progress"
    assert analysis["questionnaire"]["active_category_id"] == "data_records"
    assert analysis["questionnaire"]["active_slot_id"] == "critical_fields"


def test_analysis_api_rich_workshop_request_seeds_evidence_and_asks_missing_detail():
    generic_workflow_payload = VALID_PAYLOAD.copy()
    generic_workflow_payload["next_question"] = {
        "text": "Which normal flow best matches the work from start to finish?",
        "why_this_matters": "The SAD needs the main sequence before handling edge cases.",
        "choices": [
            {"id": "request_approve_fulfil", "label": "Request, approve, then fulfil"},
            {"id": "register_process_close", "label": "Register, process, then close"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "workflow_steps",
        "target_slot_id": "normal_flow",
    }
    generic_workflow_payload = _payload_with_strong_slots(
        generic_workflow_payload,
        [
            ("goal_scope", "business_goal"),
            ("goal_scope", "in_scope_outcome"),
            ("users_roles", "primary_users"),
            ("users_roles", "responsibilities"),
            ("workflow_steps", "normal_flow"),
            ("workflow_steps", "handoffs"),
            ("data_records", "main_records"),
            ("data_records", "critical_fields"),
            ("rules_approvals", "triggering_rules"),
            ("exceptions_edges", "common_exception"),
            ("exceptions_edges", "required_handling"),
            ("reports_summaries", "needed_outputs"),
            ("reports_summaries", "audience"),
            ("access_permissions", "access_model"),
            ("access_permissions", "sensitive_actions"),
            ("integrations", "external_systems"),
            ("non_functional", "security_privacy"),
            ("non_functional", "audit_history"),
        ],
        "maintenance requests",
    )
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel(
        [generic_workflow_payload, generic_workflow_payload]
    )
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={"requirement_text": WORKSHOP_REQUEST},
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    categories = {
        category["id"]: category
        for category in analysis["questionnaire"]["categories"]
    }
    assert categories["rules_approvals"]["status"] == "in_progress"
    assert categories["exceptions_edges"]["status"] == "ready"
    assert categories["access_permissions"]["status"] == "ready"
    assert categories["integrations"]["status"] == "ready"
    assert categories["non_functional"]["status"] == "ready"
    assert analysis["questionnaire"]["active_category_id"] == "rules_approvals"
    assert analysis["questionnaire"]["active_slot_id"] == "approval_path"
    assert "approval" in analysis["next_question"]["text"].lower()
    assert "normal flow" not in analysis["next_question"]["text"].lower()


def test_analysis_api_tuition_request_skips_generic_goal_and_asks_domain_rule():
    generic_payload = VALID_PAYLOAD.copy()
    generic_payload["next_question"] = {
        "text": "What main result should this system help the business achieve?",
        "why_this_matters": "This gives the SAD a clear business goal.",
        "choices": [{"id": "reduce_delay", "label": "Reduce delays"}],
        "target_category": "goal_scope",
        "target_slot_id": "business_goal",
    }
    generic_payload = _payload_with_strong_slots(
        generic_payload,
        [
            ("goal_scope", "business_goal"),
            ("goal_scope", "in_scope_outcome"),
            ("users_roles", "primary_users"),
            ("users_roles", "responsibilities"),
            ("workflow_steps", "normal_flow"),
            ("workflow_steps", "handoffs"),
            ("data_records", "main_records"),
            ("data_records", "critical_fields"),
            ("rules_approvals", "triggering_rules"),
            ("rules_approvals", "approval_path"),
            ("exceptions_edges", "common_exception"),
            ("reports_summaries", "needed_outputs"),
            ("reports_summaries", "audience"),
        ],
        "A small tuition centre",
    )
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([generic_payload, generic_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={"requirement_text": TUITION_REQUEST},
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["questionnaire"]["active_category_id"] in {
        "rules_approvals",
        "exceptions_edges",
        "access_permissions",
        "non_functional",
    }
    assert analysis["questionnaire"]["active_slot_id"] != "business_goal"
    question_text = analysis["next_question"]["text"].lower()
    assert "main result" not in question_text
    assert any(
        term in question_text
        for term in ("parent", "absence", "fee", "class", "attendance", "access")
    )
    choice_text = " ".join(
        choice["label"].lower() for choice in analysis["next_question"]["choices"]
    )
    assert any(
        term in choice_text
        for term in ("parent", "fee", "absence", "attendance", "class")
    )


def test_analysis_api_uses_uploaded_source_context_for_domain_question_replacement():
    generic_payload = VALID_PAYLOAD.copy()
    generic_payload["next_question"] = {
        "text": "What main result should this system help the business achieve?",
        "why_this_matters": "This gives the SAD a clear business goal.",
        "choices": [{"id": "reduce_delay", "label": "Reduce delays"}],
        "target_category": "goal_scope",
        "target_slot_id": "business_goal",
    }
    generic_payload = _payload_with_strong_slots(
        generic_payload,
        [
            ("goal_scope", "business_goal"),
            ("goal_scope", "in_scope_outcome"),
            ("users_roles", "primary_users"),
            ("users_roles", "responsibilities"),
            ("workflow_steps", "normal_flow"),
            ("workflow_steps", "handoffs"),
            ("data_records", "main_records"),
            ("data_records", "critical_fields"),
            ("rules_approvals", "triggering_rules"),
            ("rules_approvals", "approval_path"),
            ("exceptions_edges", "common_exception"),
            ("reports_summaries", "needed_outputs"),
            ("reports_summaries", "audience"),
        ],
        "customer laundry orders",
    )
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([generic_payload, generic_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Please analyse the uploaded laundry shop workflow and ask the "
                "next important question."
            ),
            "source_context": LAUNDRY_SOURCE_CONTEXT,
            "source_references": ["SRC-000001"],
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["source_references"] == ["SRC-000001"]
    assert analysis["questionnaire"]["active_category_id"] in {
        "exceptions_edges",
        "access_permissions",
        "non_functional",
        "rules_approvals",
    }
    question_text = analysis["next_question"]["text"].lower()
    assert "main result" not in question_text
    assert any(
        term in question_text
        for term in ("order", "customer", "payment", "delayed", "damaged", "pickup")
    )
    choice_text = " ".join(
        choice["label"].lower() for choice in analysis["next_question"]["choices"]
    )
    assert any(
        term in choice_text
        for term in ("order", "customer", "payment", "delayed", "damaged", "pickup")
    )


def test_analysis_api_uploaded_source_followup_does_not_repeat_broad_question():
    repeated_payload = VALID_PAYLOAD.copy()
    repeated_payload["next_question"] = {
        "text": "What main result should this system help the business achieve?",
        "why_this_matters": "This gives the SAD a clear business goal.",
        "choices": [{"id": "reduce_delay", "label": "Reduce delays"}],
        "target_category": "goal_scope",
        "target_slot_id": "business_goal",
    }
    repeated_payload = _payload_with_strong_slots(
        repeated_payload,
        [
            ("goal_scope", "business_goal"),
            ("goal_scope", "in_scope_outcome"),
            ("users_roles", "primary_users"),
            ("users_roles", "responsibilities"),
            ("workflow_steps", "normal_flow"),
            ("workflow_steps", "handoffs"),
            ("data_records", "main_records"),
            ("data_records", "critical_fields"),
            ("rules_approvals", "triggering_rules"),
            ("rules_approvals", "approval_path"),
            ("exceptions_edges", "common_exception"),
            ("reports_summaries", "needed_outputs"),
            ("reports_summaries", "audience"),
        ],
        "customer laundry orders",
    )
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([repeated_payload, repeated_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Please analyse the uploaded laundry shop workflow and ask the "
                "next important question.\n\n"
                "Previous question: [category: goal_scope][slot: business_goal] "
                "What main result should this system help the business achieve?\n"
                "Previous answer: Improve visibility of customer orders\n\n"
                "Previous readiness: 37"
            ),
            "source_context": LAUNDRY_SOURCE_CONTEXT,
            "source_references": ["SRC-000001"],
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    question_text = analysis["next_question"]["text"].lower()
    assert "what main result should this system help the business achieve" not in question_text
    assert any(
        term in question_text
        for term in ("order", "customer", "payment", "delayed", "damaged", "pickup")
    )


def test_analysis_api_service_order_readiness_reflects_explicit_evidence():
    rich_payload = VALID_PAYLOAD.copy()
    rich_payload["next_question"] = {
        "text": "What main result should this system help the business achieve?",
        "why_this_matters": "This gives the SAD a clear business goal.",
        "choices": [{"id": "reduce_delay", "label": "Reduce delays"}],
        "target_category": "goal_scope",
        "target_slot_id": "business_goal",
    }
    sparse_payload = json.loads(json.dumps(rich_payload))
    rich_payload = _payload_with_strong_slots(
        rich_payload,
        [
            ("goal_scope", "business_goal"),
            ("goal_scope", "in_scope_outcome"),
            ("users_roles", "primary_users"),
            ("users_roles", "responsibilities"),
            ("workflow_steps", "normal_flow"),
            ("workflow_steps", "handoffs"),
            ("data_records", "main_records"),
            ("data_records", "critical_fields"),
            ("rules_approvals", "triggering_rules"),
            ("exceptions_edges", "common_exception"),
            ("exceptions_edges", "required_handling"),
            ("reports_summaries", "needed_outputs"),
            ("reports_summaries", "audience"),
            ("access_permissions", "access_model"),
            ("access_permissions", "sensitive_actions"),
            ("integrations", "external_systems"),
            ("non_functional", "security_privacy"),
            ("non_functional", "audit_history"),
        ],
        "A small event rental company",
    )
    sparse_payload = _payload_with_strong_slots(
        sparse_payload,
        [
            ("goal_scope", "business_goal"),
            ("goal_scope", "in_scope_outcome"),
            ("users_roles", "primary_users"),
            ("users_roles", "responsibilities"),
            ("workflow_steps", "normal_flow"),
            ("reports_summaries", "needed_outputs"),
            ("reports_summaries", "audience"),
        ],
        "A small event rental company",
    )
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([rich_payload, sparse_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )
    rich_event_request = EVENT_RENTAL_SOURCE_CONTEXT.split("Extracted text:\n", 1)[1]
    sparse_event_request = (
        "A small event rental company wants to track customer bookings. "
        "Sales staff create booking orders. Warehouse staff prepare items. "
        "Drivers deliver and pick up items. Some items may be damaged or "
        "returned late. The owner needs a weekly summary."
    )

    rich_response = client.post(
        "/analysis/requirement",
        json={"requirement_text": rich_event_request},
    )
    sparse_response = client.post(
        "/analysis/requirement",
        json={"requirement_text": sparse_event_request},
    )

    assert rich_response.status_code == 200
    assert sparse_response.status_code == 200
    rich_analysis = rich_response.json()["analysis"]
    sparse_analysis = sparse_response.json()["analysis"]
    assert (
        rich_analysis["questionnaire"]["draft_readiness"]["score"]
        > sparse_analysis["questionnaire"]["draft_readiness"]["score"]
    )
    assert rich_analysis["questionnaire"]["draft_readiness"]["score"] < 100
    assert sparse_analysis["questionnaire"]["draft_readiness"]["score"] < 80
    assert rich_analysis["questionnaire"]["active_category_id"] == "rules_approvals"
    assert rich_analysis["questionnaire"]["active_slot_id"] == "approval_path"
    assert "approval" in rich_analysis["next_question"]["text"].lower()
    rich_categories = {
        category["id"]: category
        for category in rich_analysis["questionnaire"]["categories"]
    }
    sparse_categories = {
        category["id"]: category
        for category in sparse_analysis["questionnaire"]["categories"]
    }
    assert rich_categories["access_permissions"]["status"] == "ready"
    assert rich_categories["integrations"]["status"] == "ready"
    assert rich_categories["non_functional"]["status"] == "ready"
    assert sparse_categories["access_permissions"]["status"] == "needed"
    assert sparse_categories["integrations"]["status"] == "needed"
    assert sparse_categories["non_functional"]["status"] == "needed"


def test_analysis_api_simple_order_context_does_not_inherit_rich_source_readiness():
    generic_payload = VALID_PAYLOAD.copy()
    generic_payload["next_question"] = {
        "text": "What main result should this system help the business achieve?",
        "why_this_matters": "This gives the SAD a clear business goal.",
        "choices": [{"id": "reduce_delay", "label": "Reduce delays"}],
        "target_category": "goal_scope",
        "target_slot_id": "business_goal",
    }
    generic_payload = _payload_with_strong_slots(
        generic_payload,
        [
            ("goal_scope", "business_goal"),
            ("goal_scope", "in_scope_outcome"),
            ("users_roles", "primary_users"),
            ("users_roles", "responsibilities"),
            ("workflow_steps", "normal_flow"),
            ("workflow_steps", "handoffs"),
            ("data_records", "main_records"),
            ("data_records", "critical_fields"),
            ("reports_summaries", "needed_outputs"),
            ("reports_summaries", "audience"),
            ("exceptions_edges", "common_exception"),
        ],
        "A small bakery",
    )
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([generic_payload, generic_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={"requirement_text": SIMPLE_BAKERY_REQUEST},
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["questionnaire"]["draft_readiness"]["score"] < 80
    assert analysis["questionnaire"]["active_category_id"] == "rules_approvals"
    assert analysis["questionnaire"]["active_slot_id"] == "triggering_rules"
    visible_question = " ".join(
        [
            analysis["next_question"]["text"],
            *[choice["label"] for choice in analysis["next_question"]["choices"]],
        ]
    ).lower()
    assert "owner approval needed before closing unusual customer orders" not in visible_question


def test_analysis_fallback_question_uses_event_source_context_not_clinic_template():
    question = _fallback_question(
        {"id": "users_roles", "label": "Users and staff roles"},
        context_text=EVENT_RENTAL_SOURCE_CONTEXT,
    )

    visible = " ".join(
        [
            str(question["text"]),
            str(question["why_this_matters"]),
            *[choice["label"] for choice in question["choices"]],
        ]
    ).lower()
    assert "clinic" not in visible
    assert "patient" not in visible
    assert "doctor" not in visible
    assert "pharmacy" not in visible
    assert "event" in visible or "booking" in visible or "delivery" in visible
    assert "sales" in visible
    assert "warehouse" in visible


def test_analysis_api_broad_preset_labels_do_not_complete_responsibilities():
    drifted_payload = VALID_PAYLOAD.copy()
    drifted_payload["next_question"] = {
        "text": "Which normal flow best matches the work from start to finish?",
        "why_this_matters": "This checks workflow after roles.",
        "choices": [
            {"id": "request_approve_fulfil", "label": "Request, approve, then fulfil"},
            {"id": "register_process_close", "label": "Register, process, then close"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "workflow_steps",
        "target_slot_id": "normal_flow",
    }
    drifted_payload = _payload_with_strong_slots(
        drifted_payload,
        [
            ("goal_scope", "business_goal"),
            ("goal_scope", "in_scope_outcome"),
            ("users_roles", "primary_users"),
        ],
        "Need a better internal system",
    )
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([drifted_payload, drifted_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Need a better internal system.\n\n"
                "Previous question: [category: goal_scope][slot: business_goal] "
                "What main result should this system help the business achieve?\n"
                "Previous answer: Reduce delays\n\n"
                "Previous question: [category: goal_scope][slot: in_scope_outcome] "
                "Which outcome must be included in the first version?\n"
                "Previous answer: Track the main work from start to finish\n\n"
                "Previous question: [category: users_roles][slot: primary_users] "
                "Which staff groups will use this system?\n"
                "Previous answer: Frontline staff\n\n"
                "Previous question: [category: users_roles][slot: responsibilities] "
                "What should each staff group be responsible for?\n"
                "Previous answer: Capture or update records"
            )
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    users_category = next(
        category
        for category in analysis["questionnaire"]["categories"]
        if category["id"] == "users_roles"
    )
    assert users_category["status"] == "in_progress"
    assert analysis["questionnaire"]["active_category_id"] == "users_roles"
    assert analysis["questionnaire"]["active_slot_id"] == "responsibilities"


def test_analysis_api_broad_answers_do_not_make_draft_ready():
    payload = VALID_PAYLOAD.copy()
    payload["next_question"] = {
        "text": "Which main records must the system keep?",
        "why_this_matters": "This defines the core data the product must store.",
        "choices": [
            {"id": "request_records", "label": "Request or case records"},
            {"id": "person_records", "label": "Customer, patient, or staff records"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "data_records",
        "target_slot_id": "main_records",
    }
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([payload, payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Need a better internal system.\n\n"
                "Previous question: [category: goal_scope][slot: business_goal] "
                "What main result should this system help the business achieve?\n"
                "Previous answer: Reduce delays\n\n"
                "Previous question: [category: goal_scope][slot: in_scope_outcome] "
                "Which outcome must be included in the first version?\n"
                "Previous answer: Track the main work from start to finish\n\n"
                "Previous question: [category: users_roles][slot: primary_users] "
                "Which staff groups will use this system?\n"
                "Previous answer: Frontline staff\n\n"
                "Previous question: [category: users_roles][slot: responsibilities] "
                "What should each staff group be responsible for?\n"
                "Previous answer: Staff create requests, supervisors review work, and managers view reports.\n\n"
                "Previous question: [category: workflow_steps][slot: normal_flow] "
                "Which normal flow best matches the work from start to finish?\n"
                "Previous answer: A request is created, assigned, updated, and closed.\n\n"
                "Previous question: [category: workflow_steps][slot: handoffs] "
                "When the work moves to the next step, what should happen?\n"
                "Previous answer: Hand it to the next responsible role\n\n"
                "Previous question: [category: data_records][slot: main_records] "
                "Which main records must the system keep?\n"
                "Previous answer: Request or case records\n\n"
                "Previous question: [category: data_records][slot: critical_fields] "
                "Which details are essential on each record?\n"
                "Previous answer: Names or identifiers\n\n"
                "Previous question: [category: rules_approvals][slot: triggering_rules] "
                "Which business rule should be confirmed first?\n"
                "Previous answer: Staff should be alerted when a rule is broken\n\n"
                "Previous question: [category: rules_approvals][slot: approval_path] "
                "How should a request move through approval?\n"
                "Previous answer: One manager approves it\n\n"
                "Previous question: [category: exceptions_edges][slot: common_exception] "
                "Which exception should be handled first?\n"
                "Previous answer: A required step is skipped\n\n"
                "Previous question: [category: exceptions_edges][slot: required_handling] "
                "When that exception happens, what should staff do next?\n"
                "Previous answer: Allow manual follow-up later\n\n"
                "Previous question: [category: reports_summaries][slot: needed_outputs] "
                "Which output should the first version produce?\n"
                "Previous answer: Daily summary\n\n"
                "Previous question: [category: reports_summaries][slot: audience] "
                "Who needs to review those outputs most often?\n"
                "Previous answer: Managers\n\n"
                "Previous question: [category: access_permissions][slot: access_model] "
                "How should access normally be organised?\n"
                "Previous answer: Role-based access\n\n"
                "Previous question: [category: access_permissions][slot: sensitive_actions] "
                "Which actions need tighter permission control?\n"
                "Previous answer: Delete or overwrite records\n\n"
                "Previous question: [category: integrations][slot: external_systems] "
                "Which external systems must this connect with, if any?\n"
                "Previous answer: No external systems in the first version\n\n"
                "Previous question: [category: non_functional][slot: security_privacy] "
                "Which security or privacy need matters most?\n"
                "Previous answer: Secure login\n\n"
                "Previous question: [category: non_functional][slot: audit_history] "
                "What history must the system keep?\n"
                "Previous answer: Edits and corrections"
            )
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["questionnaire"]["draft_readiness"]["score"] < 100


def test_analysis_api_clinic_flow_advances_by_plan_after_seeded_context():
    clinic_first_payload = VALID_PAYLOAD.copy()
    clinic_first_payload["next_question"] = {
        "text": "Which details are essential on each patient record?",
        "why_this_matters": "This clarifies critical fields.",
        "choices": [
            {"id": "identifiers", "label": "Names or identifiers"},
            {"id": "dates_status", "label": "Dates and statuses"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "data_records",
        "target_slot_id": "critical_fields",
    }
    clinic_second_payload = VALID_PAYLOAD.copy()
    clinic_second_payload["next_question"] = {
        "text": "Which business rule should be confirmed first?",
        "why_this_matters": "This clarifies workflow rules.",
        "choices": [
            {"id": "must_complete", "label": "A record cannot be completed until key steps are done"},
            {"id": "must_review", "label": "A review is required before completion"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "rules_approvals",
        "target_slot_id": "triggering_rules",
    }
    clinic_first_payload = _payload_with_strong_slots(
        clinic_first_payload,
        [
            ("goal_scope", "business_goal"),
            ("goal_scope", "in_scope_outcome"),
            ("users_roles", "primary_users"),
            ("users_roles", "responsibilities"),
            ("workflow_steps", "normal_flow"),
            ("workflow_steps", "handoffs"),
            ("data_records", "main_records"),
        ],
        "Small clinic",
    )
    clinic_second_payload = _payload_with_strong_slots(
        clinic_second_payload,
        [
            ("goal_scope", "business_goal"),
            ("goal_scope", "in_scope_outcome"),
            ("users_roles", "primary_users"),
            ("users_roles", "responsibilities"),
            ("workflow_steps", "normal_flow"),
            ("workflow_steps", "handoffs"),
            ("data_records", "main_records"),
            ("data_records", "critical_fields"),
        ],
        "Small clinic",
    )
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([clinic_first_payload, clinic_second_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )
    clinic_request = (
        "Small clinic wants to track patient registration, queue status, "
        "doctor consultation, medicine collection, and payment in one simple "
        "system. Reception staff register patients and update queue status. "
        "Doctors record consultation notes. Pharmacy staff prepare medicine. "
        "Cashier records payment. Manager needs a daily summary of patients "
        "served, waiting time, and unpaid bills. Some patients may skip payment "
        "or leave before collecting medicine."
    )

    first_response = client.post(
        "/analysis/requirement",
        json={"requirement_text": clinic_request},
    )
    assert first_response.status_code == 200
    first_analysis = first_response.json()["analysis"]
    first_categories = [
        category["id"]
        for category in first_analysis["questionnaire"]["categories"]
    ]

    second_response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                f"{clinic_request}\n\n"
                "Previous question: [category: data_records][slot: critical_fields] "
                "Which details are essential on each patient record?\n"
                "Previous answer: Names or identifiers, Dates and statuses"
            )
        },
    )

    assert second_response.status_code == 200
    second_analysis = second_response.json()["analysis"]
    second_categories = [
        category["id"]
        for category in second_analysis["questionnaire"]["categories"]
    ]
    assert first_categories == second_categories
    assert first_analysis["questionnaire"]["active_category_id"] == "data_records"
    assert first_analysis["questionnaire"]["active_slot_id"] == "critical_fields"
    assert second_analysis["questionnaire"]["active_category_id"] == "rules_approvals"
    assert second_analysis["questionnaire"]["active_slot_id"] == "triggering_rules"
    assert (
        second_analysis["questionnaire"]["draft_readiness"]["score"]
        > first_analysis["questionnaire"]["draft_readiness"]["score"]
    )


def test_analysis_api_uses_explicit_slot_markers_in_answer_history():
    payload = VALID_PAYLOAD.copy()
    payload["next_question"] = {
        "text": "What happens after the first workflow step?",
        "why_this_matters": "This clarifies handoffs.",
        "choices": [
            {"id": "handoff", "label": "A handoff occurs"},
            {"id": "same_staff", "label": "The same staff continue"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "workflow_steps",
        "target_slot_id": "handoffs",
    }
    payload = _payload_with_strong_slots(
        payload,
        [("workflow_steps", "normal_flow")],
        "Keep the patient moving to the next step",
    )
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Small clinic needs a simple workflow system.\n\n"
                "Previous question: [category: workflow_steps][slot: normal_flow] "
                "What should happen when staff need access outside their normal role?\n"
                "Previous answer: Keep the patient moving to the next step"
            )
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["questionnaire"]["active_category_id"] == "workflow_steps"
    assert analysis["questionnaire"]["active_slot_id"] == "handoffs"
    assert analysis["questionnaire"]["answers"][0]["category_id"] == "workflow_steps"
    assert analysis["questionnaire"]["answers"][0]["slot_id"] == "normal_flow"


def test_analysis_api_recalculates_readiness_from_plan_coverage():
    low_progress_payload = VALID_PAYLOAD.copy()
    low_progress_payload["readiness"] = {
        "label": "Fallback-looking low score",
        "score": 35,
        "confidence": "Medium",
    }
    low_progress_payload["categories"] = [
        {"id": "users_roles", "label": "Users/Roles", "status": "missing"},
        {"id": "workflow", "label": "Workflow", "status": "missing"},
    ]
    low_progress_payload["next_question"] = {
        "text": "What happens after the first workflow step?",
        "why_this_matters": "This clarifies handoffs.",
        "choices": [
            {"id": "handoff", "label": "A handoff occurs"},
            {"id": "same_staff", "label": "The same staff continue"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "workflow",
        "target_slot_id": "handoffs",
    }
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([low_progress_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Small clinic needs a simple workflow system.\n\n"
                "Previous question: [category: workflow] What does simple mean to your clinic?\n"
                "Previous answer: Easy to learn and use for staff\n\n"
                "Previous readiness: 84"
            )
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["questionnaire"]["draft_readiness"]["score"] < 84
    assert analysis["questionnaire"]["draft_readiness"]["label"] == "Getting started"


def test_analysis_api_uses_canonical_questionnaire_labels_and_order():
    payload = VALID_PAYLOAD.copy()
    payload["categories"] = [
        {"id": "workflow", "label": "Workflow Management", "status": "partial"},
        {"id": "users_roles", "label": "User Roles and Permissions", "status": "missing"},
    ]
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={"requirement_text": "Need a better clinic workflow."},
    )

    assert response.status_code == 200
    categories = response.json()["analysis"]["questionnaire"]["categories"]
    assert [category["id"] for category in categories[:4]] == [
        "goal_scope",
        "users_roles",
        "workflow_steps",
        "data_records",
    ]
    assert [category["label"] for category in categories[:4]] == [
        "Goal and scope",
        "Users and roles",
        "Workflow steps",
        "Data and records",
    ]


def test_analysis_api_keeps_unfinished_active_category_when_model_drifts():
    drifted_payload = VALID_PAYLOAD.copy()
    drifted_payload["categories"] = [
        {"id": "workflow", "label": "Workflow", "status": "missing"},
        {"id": "users_roles", "label": "Users/Roles", "status": "partial"},
    ]
    drifted_payload["next_question"] = {
        "text": "Which workflow exception matters most?",
        "why_this_matters": "This clarifies the patient flow.",
        "choices": [
            {"id": "skip_payment", "label": "Patient leaves without paying"},
            {"id": "skip_medicine", "label": "Patient leaves before medicine collection"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "workflow",
        "target_slot_id": "normal_flow",
    }
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([drifted_payload, drifted_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Small clinic needs a simple workflow system.\n\n"
                "Previous question: [category: users_roles] Which staff access rule should be confirmed first?\n"
                "Previous answer: Reception can register and update queue status"
            )
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["questionnaire"]["active_category_id"] == "users_roles"
    assert analysis["next_question"]["target_category"] == "users_roles"


def test_analysis_api_repairs_when_model_targets_wrong_locked_slot():
    wrong_slot_payload = VALID_PAYLOAD.copy()
    wrong_slot_payload["next_question"] = {
        "text": "Which staff use the system?",
        "why_this_matters": "This clarifies roles.",
        "choices": [
            {"id": "reception", "label": "Reception"},
            {"id": "doctor", "label": "Doctor"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "users_roles",
        "target_slot_id": "primary_users",
    }
    wrong_slot_payload = _payload_with_strong_slots(
        wrong_slot_payload,
        [("users_roles", "primary_users")],
        "Reception",
    )
    repaired_payload = VALID_PAYLOAD.copy()
    repaired_payload["next_question"] = {
        "text": "What should each staff group be responsible for?",
        "why_this_matters": "This clarifies responsibilities.",
        "choices": [
            {"id": "register", "label": "Register patients"},
            {"id": "consult", "label": "Record consultation notes"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "users_roles",
        "target_slot_id": "responsibilities",
    }
    repository = RequirementAnalysisRepository()
    repaired_payload = _payload_with_strong_slots(
        repaired_payload,
        [("users_roles", "primary_users")],
        "Reception",
    )
    model = FakeRequirementAnalysisModel([wrong_slot_payload, repaired_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Small clinic needs a simple workflow system.\n\n"
                "Previous question: [category: users_roles] Which staff use the system?\n"
                "Previous answer: Reception"
            )
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["next_question"]["target_category"] == "users_roles"
    assert analysis["next_question"]["target_slot_id"] == "responsibilities"
    assert [repair for _, repair in model.requests] == [False]
    assert "Locked questionnaire target:" in model.requests[0][0]
    assert "active_category_id: users_roles" in model.requests[0][0]
    assert "target_slot_id: responsibilities" in model.requests[0][0]


def test_analysis_api_uses_same_slot_fallback_when_repair_still_drifts():
    wrong_slot_payload = VALID_PAYLOAD.copy()
    wrong_slot_payload["next_question"] = {
        "text": "Which staff use the system?",
        "why_this_matters": "This clarifies roles.",
        "choices": [
            {"id": "reception", "label": "Reception"},
            {"id": "doctor", "label": "Doctor"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "users_roles",
        "target_slot_id": "primary_users",
    }
    wrong_slot_payload = _payload_with_strong_slots(
        wrong_slot_payload,
        [("users_roles", "primary_users")],
        "Reception",
    )
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([wrong_slot_payload, wrong_slot_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Small clinic needs a simple workflow system.\n\n"
                "Previous question: [category: users_roles] Which staff use the system?\n"
                "Previous answer: Reception"
            )
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["next_question"]["target_category"] == "users_roles"
    assert analysis["next_question"]["target_slot_id"] == "responsibilities"
    assert "drifted" in " ".join(analysis["assumptions"]).lower()


def test_analysis_api_repairs_semantic_drift_even_when_slot_ids_are_valid():
    wrong_semantic_payload = VALID_PAYLOAD.copy()
    wrong_semantic_payload["next_question"] = {
        "text": "What should happen when staff need access outside their normal role?",
        "why_this_matters": "This clarifies access exceptions.",
        "choices": [
            {"id": "manager_approval", "label": "Require manager approval"},
            {"id": "temporary_access", "label": "Allow temporary access with audit log"},
            {"id": "block_access", "label": "Block access outside the role"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "rules_approvals",
        "target_slot_id": "approval_path",
    }
    wrong_semantic_payload = _payload_with_strong_slots(
        wrong_semantic_payload,
        [("rules_approvals", "triggering_rules")],
        "Requests above budget need approval",
    )
    repaired_payload = VALID_PAYLOAD.copy()
    repaired_payload["next_question"] = {
        "text": "How should a request move through approval?",
        "why_this_matters": "This clarifies the approval path.",
        "choices": [
            {"id": "single_manager", "label": "One manager approves it"},
            {"id": "multi_level", "label": "It goes through multiple approval levels"},
            {"id": "by_amount", "label": "The path depends on amount or request type"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "rules_approvals",
        "target_slot_id": "approval_path",
    }
    repository = RequirementAnalysisRepository()
    repaired_payload = _payload_with_strong_slots(
        repaired_payload,
        [("rules_approvals", "triggering_rules")],
        "Requests above budget need approval",
    )
    model = FakeRequirementAnalysisModel(
        [wrong_semantic_payload, repaired_payload]
    )
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Need a purchasing workflow.\n\n"
                "Previous question: [category: rules_approvals][slot: triggering_rules] "
                "Which business rule should be confirmed first?\n"
                "Previous answer: Requests above budget need approval"
            )
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["next_question"]["text"] == repaired_payload["next_question"]["text"]
    assert [repair for _, repair in model.requests] == [False, True]


def test_analysis_api_uses_same_slot_fallback_when_repair_keeps_semantic_drift():
    wrong_semantic_payload = VALID_PAYLOAD.copy()
    wrong_semantic_payload["next_question"] = {
        "text": "What should happen when staff need access outside their normal role?",
        "why_this_matters": "This clarifies access exceptions.",
        "choices": [
            {"id": "manager_approval", "label": "Require manager approval"},
            {"id": "temporary_access", "label": "Allow temporary access with audit log"},
            {"id": "block_access", "label": "Block access outside the role"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "rules_approvals",
        "target_slot_id": "approval_path",
    }
    wrong_semantic_payload = _payload_with_strong_slots(
        wrong_semantic_payload,
        [("rules_approvals", "triggering_rules")],
        "Requests above budget need approval",
    )
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel(
        [wrong_semantic_payload, wrong_semantic_payload]
    )
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Need a purchasing workflow.\n\n"
                "Previous question: [category: rules_approvals][slot: triggering_rules] "
                "Which business rule should be confirmed first?\n"
                "Previous answer: Requests above budget need approval"
            )
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["next_question"]["target_category"] == "rules_approvals"
    assert analysis["next_question"]["target_slot_id"] == "approval_path"
    assert "approval" in analysis["next_question"]["text"].lower()
    assert "access outside" not in analysis["next_question"]["text"].lower()
    assert "fallback" in " ".join(analysis["assumptions"]).lower()


def test_analysis_api_rejects_relabelled_question_from_already_covered_slot():
    wrong_semantic_payload = VALID_PAYLOAD.copy()
    wrong_semantic_payload["next_question"] = {
        "text": "Which staff groups use this system?",
        "why_this_matters": "This identifies users.",
        "choices": [
            {"id": "reception", "label": "Reception"},
            {"id": "doctor", "label": "Doctors"},
            {"id": "pharmacy", "label": "Pharmacy"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "users_roles",
        "target_slot_id": "responsibilities",
    }
    wrong_semantic_payload = _payload_with_strong_slots(
        wrong_semantic_payload,
        [("users_roles", "primary_users")],
        "Reception",
    )
    repaired_payload = VALID_PAYLOAD.copy()
    repaired_payload["next_question"] = {
        "text": "What should each staff group be responsible for?",
        "why_this_matters": "This clarifies responsibilities.",
        "choices": [
            {"id": "register", "label": "Register patients"},
            {"id": "consult", "label": "Record consultation notes"},
            {"id": "dispense", "label": "Prepare medicine"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "users_roles",
        "target_slot_id": "responsibilities",
    }
    repository = RequirementAnalysisRepository()
    repaired_payload = _payload_with_strong_slots(
        repaired_payload,
        [("users_roles", "primary_users")],
        "Reception",
    )
    model = FakeRequirementAnalysisModel(
        [wrong_semantic_payload, repaired_payload]
    )
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Small clinic needs a simple workflow system.\n\n"
                "Previous question: [category: users_roles][slot: primary_users] "
                "Which staff groups use this system?\n"
                "Previous answer: Reception, doctors, pharmacy"
            )
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["next_question"]["text"] == repaired_payload["next_question"]["text"]
    assert [repair for _, repair in model.requests] == [False, True]


def test_analysis_api_keeps_active_slot_when_multiple_answers_belong_to_same_slot():
    responsibilities_payload = VALID_PAYLOAD.copy()
    responsibilities_payload["next_question"] = {
        "text": "What should each staff group be responsible for?",
        "why_this_matters": "This clarifies responsibilities.",
        "choices": [
            {"id": "register", "label": "Register patients"},
            {"id": "consult", "label": "Record consultation notes"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "users_roles",
        "target_slot_id": "responsibilities",
    }
    responsibilities_payload = _payload_with_strong_slots(
        responsibilities_payload,
        [("users_roles", "primary_users")],
        "Reception and doctors",
    )
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([responsibilities_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Small clinic needs a simple workflow system.\n\n"
                "Previous question: [category: users_roles][slot: primary_users] "
                "Which staff groups use this system?\n"
                "Previous answer: Reception and doctors\n\n"
                "Previous question: [category: users_roles][slot: primary_users] "
                "Which staff members use this system every day?\n"
                "Previous answer: Reception, doctors, and pharmacy"
            )
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["questionnaire"]["active_category_id"] == "users_roles"
    assert analysis["questionnaire"]["active_slot_id"] == "responsibilities"
    assert analysis["next_question"]["target_category"] == "users_roles"
    assert analysis["next_question"]["target_slot_id"] == "responsibilities"


def test_analysis_api_does_not_skip_uncovered_category_from_model_complete_claim():
    drifted_payload = VALID_PAYLOAD.copy()
    drifted_payload["categories"] = [
        {"id": "goal_scope", "label": "Goal and scope", "status": "complete"},
        {"id": "users_roles", "label": "Users and roles", "status": "complete"},
        {"id": "workflow_steps", "label": "Workflow steps", "status": "complete"},
    ]
    drifted_payload["next_question"] = {
        "text": "Which staff groups will use this system?",
        "why_this_matters": "This identifies the main users.",
        "choices": [
            {"id": "frontline", "label": "Frontline staff"},
            {"id": "managers", "label": "Managers"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "users_roles",
        "target_slot_id": "primary_users",
    }
    drifted_payload = _payload_with_strong_slots(
        drifted_payload,
        [
            ("goal_scope", "business_goal"),
            ("goal_scope", "in_scope_outcome"),
        ],
        "Need a better internal system",
    )
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([drifted_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Need a better internal system.\n\n"
                "Previous question: [category: goal_scope][slot: business_goal] "
                "What main result should this system help the business achieve?\n"
                "Previous answer: Reduce delays\n\n"
                "Previous question: [category: goal_scope][slot: in_scope_outcome] "
                "Which outcome must be included in the first version?\n"
                "Previous answer: Track the main work from start to finish"
            )
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["questionnaire"]["active_category_id"] == "users_roles"
    assert analysis["questionnaire"]["active_slot_id"] == "primary_users"
    assert analysis["next_question"]["target_category"] == "users_roles"
    assert analysis["next_question"]["target_slot_id"] == "primary_users"
    assert [repair for _, repair in model.requests] == [False]


def test_analysis_api_latest_uncertain_answer_defers_only_its_slot():
    responsibilities_payload = VALID_PAYLOAD.copy()
    responsibilities_payload["next_question"] = {
        "text": "What should each staff group be responsible for?",
        "why_this_matters": "This clarifies responsibilities.",
        "choices": [
            {"id": "capture_records", "label": "Capture or update records"},
            {"id": "review_approve", "label": "Review or approve work"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "users_roles",
        "target_slot_id": "responsibilities",
    }
    responsibilities_payload = _payload_with_strong_slots(
        responsibilities_payload,
        [
            ("goal_scope", "business_goal"),
            ("goal_scope", "in_scope_outcome"),
            ("users_roles", "primary_users"),
        ],
        "Need a better internal system",
    )
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([responsibilities_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Need a better internal system.\n\n"
                "Previous question: [category: goal_scope][slot: business_goal] "
                "What main result should this system help the business achieve?\n"
                "Previous answer: Reduce delays\n\n"
                "Previous question: [category: goal_scope][slot: in_scope_outcome] "
                "Which outcome must be included in the first version?\n"
                "Previous answer: Track the main work from start to finish\n\n"
                "Previous question: [category: users_roles][slot: primary_users] "
                "Which staff groups will use this system?\n"
                "Previous answer: Frontline staff\n\n"
                "Previous question: [category: users_roles][slot: primary_users] "
                "Which staff groups will use this system?\n"
                "Previous answer: I'm not sure yet"
            )
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    categories = {
        category["id"]: category
        for category in analysis["questionnaire"]["categories"]
    }
    assert categories["goal_scope"]["status"] == "ready"
    assert categories["users_roles"]["status"] == "needs_later_confirmation"
    assert analysis["questionnaire"]["active_category_id"] == "users_roles"
    assert analysis["questionnaire"]["active_slot_id"] == "responsibilities"


def test_analysis_api_keeps_extra_category_as_suggestion_only():
    payload = VALID_PAYLOAD.copy()
    payload["proposed_extra_categories"] = [
        {
            "id": "supplier_orders",
            "label": "Supplier orders",
            "reason": "The request mentions suppliers after the core flow is clarified.",
        }
    ]
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={"requirement_text": "Need a purchasing workflow."},
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    category_ids = [category["id"] for category in analysis["questionnaire"]["categories"]]
    assert "supplier_orders" not in category_ids
    assert analysis["proposed_extra_categories"][0]["id"] == "supplier_orders"


def test_analysis_api_repairs_when_model_adds_unapproved_visible_category():
    extra_category_payload = VALID_PAYLOAD.copy()
    extra_category_payload["categories"] = [
        {"id": "problem", "label": "Problem", "status": "partial"},
        {"id": "purchase_requests", "label": "Purchase Requests", "status": "missing"},
    ]
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([extra_category_payload, VALID_PAYLOAD.copy()])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={"requirement_text": "Need a better purchasing workflow."},
    )

    assert response.status_code == 200
    assert [repair for _, repair in model.requests] == [False, True]
    assert "Need a better purchasing workflow." in model.requests[0][0]
    assert "active_category_id: goal_scope" in model.requests[0][0]


def test_analysis_api_filters_non_business_source_references():
    payload = VALID_PAYLOAD.copy()
    payload["source_references"] = ["Business Request", "Previous Answer"]
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": "Need a better approval workflow.",
            "source_references": ["SRC-000001"],
        },
    )

    assert response.status_code == 200
    assert response.json()["analysis"]["source_references"] == [
        "Business Request",
        "SRC-000001",
    ]


def test_analysis_api_skips_repeated_valid_model_question():
    repeated_payload = VALID_PAYLOAD.copy()
    repeated_payload["categories"] = [
        {"id": "workflow", "label": "Workflow Management", "status": "partial"},
        {"id": "users_roles", "label": "User Roles", "status": "missing"},
    ]
    repeated_payload["next_question"] = {
        "text": "You mentioned wanting a simple system. What does simple mean to your clinic?",
        "why_this_matters": "This helps prioritize the design.",
        "choices": [
            {"id": "easy", "label": "Easy to learn and use for staff"},
            {"id": "quick", "label": "Quick to set up"},
            {"id": "essential", "label": "Only essential features"},
            {"id": "not_sure", "label": "Unsure"},
        ],
        "target_category": "workflow",
        "target_slot_id": "handoffs",
    }
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([repeated_payload, repeated_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Small clinic needs a simple workflow system.\n\n"
                "Previous question: [category: workflow] What does simple mean to your clinic?\n"
                "Previous answer: Easy to learn and use for staff"
            )
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["next_question"]["text"] != repeated_payload["next_question"]["text"]
    assert "simple" not in analysis["next_question"]["text"].lower()
    assert "fallback" in " ".join(analysis["assumptions"]).lower()


def test_analysis_api_repairs_once_before_saving_valid_output():
    broken_payload = VALID_PAYLOAD.copy()
    broken_payload["readiness"] = {
        "label": "Impossible",
        "score": 150,
        "confidence": "High",
    }
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([broken_payload, VALID_PAYLOAD.copy()])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={"requirement_text": "Need a better approval workflow."},
    )

    assert response.status_code == 200
    assert response.json()["analysis"]["readiness"]["score"] == 35
    assert repository.get_analysis("AN-000001") is not None
    assert [repair for _, repair in model.requests] == [False, True]
    assert "Need a better approval workflow." in model.requests[0][0]
    assert "active_category_id: goal_scope" in model.requests[0][0]


def test_analysis_api_uses_local_fallback_when_model_output_stays_invalid():
    broken_payload = VALID_PAYLOAD.copy()
    broken_payload["readiness"] = {
        "label": "Impossible",
        "score": 150,
        "confidence": "High",
    }
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([broken_payload, broken_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Small clinic needs patient registration, queue, consultation, "
                "medicine collection, payment, and exception tracking."
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_id"] == "AN-000001"
    assert payload["analysis"]["readiness"]["confidence"] == "Low"
    assert payload["analysis"]["next_question"]["target_category"] == "goal_scope"
    assert payload["analysis"]["questionnaire"]["active_category_id"] == "goal_scope"
    assert "fallback" in payload["analysis"]["assumptions"][0].lower()
    assert repository.get_analysis("AN-000001") is not None


def test_analysis_api_fallback_does_not_increase_readiness_by_repeated_answers():
    broken_payload = VALID_PAYLOAD.copy()
    broken_payload["readiness"] = {
        "label": "Impossible",
        "score": 150,
        "confidence": "High",
    }
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([broken_payload, broken_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Small clinic needs a simple workflow system.\n\n"
                "Previous question: [category: data_reports] Which data fields matter most?\n"
                "Previous answer: Payment and unpaid bill fields\n\n"
                "Previous question: [category: data_reports] Which data fields matter most?\n"
                "Previous answer: Payment and unpaid bill fields"
            )
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    data_category = next(
        category
        for category in analysis["questionnaire"]["categories"]
        if category["id"] == "data_records"
    )
    assert data_category["questions_answered"] == 0
    assert data_category["progress"] == 0
    assert analysis["questionnaire"]["draft_readiness"]["score"] <= 25


def test_analysis_api_ignores_legacy_selected_focus_without_slot_markers():
    broken_payload = VALID_PAYLOAD.copy()
    broken_payload["readiness"] = {
        "label": "Impossible",
        "score": 150,
        "confidence": "High",
    }
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([broken_payload, broken_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Small clinic needs a simple workflow system.\n\n"
                "Previous question: Which part should SADify clarify next?\n"
                "Previous answer: Business rules and approvals"
            )
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["next_question"]["target_category"] == "goal_scope"
    assert analysis["questionnaire"]["active_category_id"] == "goal_scope"


def test_analysis_api_fallback_stays_in_category_after_one_specific_answer():
    broken_payload = VALID_PAYLOAD.copy()
    broken_payload["readiness"] = {
        "label": "Impossible",
        "score": 150,
        "confidence": "High",
    }
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([broken_payload, broken_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Small clinic needs a simple workflow system.\n\n"
                "Previous question: [category: users_roles] Which staff access rule should be confirmed first?\n"
                "Previous answer: Reception can register and update queue status"
            )
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["next_question"]["target_category"] == "users_roles"
    assert analysis["questionnaire"]["active_category_id"] == "users_roles"
    users_category = next(
        category
        for category in analysis["questionnaire"]["categories"]
        if category["id"] == "users_roles"
    )
    assert users_category["status"] == "needed"
    assert users_category["questions_answered"] == 0
    assert users_category["progress"] == 0
    assert analysis["questionnaire"]["answers"][0]["category_id"] == "users_roles"


def test_analysis_api_fallback_moves_after_category_has_enough_answers():
    broken_payload = VALID_PAYLOAD.copy()
    broken_payload["readiness"] = {
        "label": "Impossible",
        "score": 150,
        "confidence": "High",
    }
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([broken_payload, broken_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Small clinic needs a simple workflow system.\n\n"
                "Previous question: [category: workflow] Which workflow exception should be clarified first?\n"
                "Previous answer: Patient leaves without paying\n\n"
                "Previous question: [category: workflow] After this workflow exception happens, what should staff do next?\n"
                "Previous answer: Alert the responsible staff immediately"
            )
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["next_question"]["target_category"] != "workflow_steps"
    workflow_category = next(
        category
        for category in analysis["questionnaire"]["categories"]
        if category["id"] == "workflow_steps"
    )
    assert workflow_category["status"] == "needed"
    assert workflow_category["progress"] == 0


def test_analysis_api_fallback_not_sure_asks_easier_uncertainty_question():
    broken_payload = VALID_PAYLOAD.copy()
    broken_payload["readiness"] = {
        "label": "Impossible",
        "score": 150,
        "confidence": "High",
    }
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([broken_payload, broken_payload])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Small clinic needs a simple workflow system.\n\n"
                "Previous question: Which staff access rule should be confirmed first?\n"
                "Previous answer: I'm not sure yet"
            )
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["next_question"]["target_category"] == "users_roles"
    assert analysis["next_question"]["selection_mode"] == "single"
    assert analysis["questionnaire"]["active_category_id"] == "users_roles"
    users_category = next(
        category
        for category in analysis["questionnaire"]["categories"]
        if category["id"] == "users_roles"
    )
    assert users_category["status"] == "needs_later_confirmation"
    assert users_category["progress"] == 0
    assert analysis["questionnaire"]["answers"][0]["is_uncertain"] is True
    assert "not sure" in " ".join(analysis["assumptions"]).lower()
    assert any(choice["id"] == "yes" for choice in analysis["next_question"]["choices"])
    assert any(choice["id"] == "no" for choice in analysis["next_question"]["choices"])


def test_requirement_analysis_schema_exposes_selection_mode_and_choice_status():
    schema = requirement_analysis_schema()
    question = schema["properties"]["next_question"]
    choice = question["properties"]["choices"]["items"]

    assert question["properties"]["target_slot_id"] == {"type": "STRING"}
    assert question["properties"]["selection_mode"] == {
        "type": "STRING",
        "enum": ["single", "multiple"],
    }
    assert choice["properties"]["is_disabled"] == {"type": "BOOLEAN"}
    assert choice["properties"]["status_label"] == {"type": "STRING"}
    assert schema["properties"]["proposed_extra_categories"]["items"]["properties"][
        "id"
    ] == {"type": "STRING"}


def test_analysis_api_surfaces_safe_model_failure_detail_in_dev():
    class FailingModel(RequirementAnalysisModel):
        def analyze_requirement(
            self,
            requirement_text: str,
            *,
            repair: bool = False,
        ) -> str:
            raise RuntimeError("diagnostic failure without secret")

    client = TestClient(create_app(analysis_model=FailingModel()))

    response = client.post(
        "/analysis/requirement",
        json={"requirement_text": "Need a better approval workflow."},
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Gemini analysis failed: RuntimeError: diagnostic failure without secret"
    }


def test_analysis_carries_prior_evidence_when_new_turn_returns_no_verdicts():
    """Turn 1 establishes a strong slot; turn 2 returns empty slot_evidence
    (simulating Gemini flicker or fallback). Carry-forward must preserve the
    prior strong evidence so readiness does not regress to zero."""
    requirement_text = "A small bakery needs a system to track orders."

    turn1 = json.loads(json.dumps(VALID_PAYLOAD))
    turn1["slot_evidence"] = [
        {
            "category_id": "goal_scope",
            "slot_id": "business_goal",
            "applicability": "applicable",
            "strength": "strong",
            "evidence_quote": "needs a system to track orders",
            "rationale": "explicit goal in the request",
        }
    ]

    turn2 = json.loads(json.dumps(VALID_PAYLOAD))
    turn2["slot_evidence"] = []  # model "forgot" or fallback path

    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([turn1, turn2])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    r1 = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": requirement_text,
            "guest_draft_id": "g-bakery",
        },
    )
    assert r1.status_code == 200
    score1 = r1.json()["analysis"]["questionnaire"]["draft_readiness"]["score"]
    assert score1 > 0

    r2 = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                f"{requirement_text}\n\n"
                "Previous question: [category: goal_scope][slot: business_goal] "
                "What is the business goal?\n"
                "Previous answer: Track customer cake orders end to end"
            ),
            "guest_draft_id": "g-bakery",
        },
    )
    assert r2.status_code == 200
    score2 = r2.json()["analysis"]["questionnaire"]["draft_readiness"]["score"]
    # Carry-forward: turn 2's empty verdicts must not wipe turn 1's coverage.
    assert score2 >= score1


def test_analysis_edit_to_prior_answer_resets_only_that_slot():
    """Editing a slot's answer should let the new verdict override the prior
    strong one for THAT slot, while other strong slots stay strong."""
    text = "A small bakery needs a system to track orders."

    turn1 = json.loads(json.dumps(VALID_PAYLOAD))
    turn1["slot_evidence"] = [
        {
            "category_id": "goal_scope",
            "slot_id": "business_goal",
            "applicability": "applicable",
            "strength": "strong",
            "evidence_quote": "needs a system to track orders",
            "rationale": "explicit goal",
        },
        {
            "category_id": "goal_scope",
            "slot_id": "in_scope_outcome",
            "applicability": "applicable",
            "strength": "strong",
            "evidence_quote": "track orders",
            "rationale": "in-scope outcome",
        },
        {
            "category_id": "users_roles",
            "slot_id": "primary_users",
            "applicability": "applicable",
            "strength": "strong",
            "evidence_quote": "needs a system to track orders",
            "rationale": "answer establishes users",
        },
    ]

    # Turn 2 re-judges the EDITED slot as none (with no quote). With edit
    # reset, that slot must drop. goal_scope must stay strong via carry-forward.
    turn2 = json.loads(json.dumps(VALID_PAYLOAD))
    turn2["slot_evidence"] = [
        {
            "category_id": "users_roles",
            "slot_id": "primary_users",
            "applicability": "applicable",
            "strength": "none",
            "evidence_quote": "",
            "rationale": "user edited and the new answer is vague",
        },
    ]

    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([turn1, turn2])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    r1 = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                f"{text}\n\n"
                "Previous question: [category: users_roles][slot: primary_users] "
                "Who uses it?\n"
                "Previous answer: Counter staff and owner"
            ),
            "guest_draft_id": "g-edit",
        },
    )
    assert r1.status_code == 200

    # Turn 2: same slot, DIFFERENT answer text → counts as an edit.
    r2 = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                f"{text}\n\n"
                "Previous question: [category: users_roles][slot: primary_users] "
                "Who uses it?\n"
                "Previous answer: Unsure"
            ),
            "guest_draft_id": "g-edit",
        },
    )
    assert r2.status_code == 200
    categories = {
        c["id"]: c
        for c in r2.json()["analysis"]["questionnaire"]["categories"]
    }
    # goal_scope kept its prior strong verdict (not edited)
    assert categories["goal_scope"]["weakest_slot_strength"] in ("partial", "strong")
    # users_roles dropped because the edited slot's prior was reset
    assert categories["users_roles"]["weakest_slot_strength"] == "none"


def test_signed_in_flow_carries_prior_evidence_without_guest_draft_id():
    """Signed-in flow sends no guest_draft_id. The repository must still
    match the prior turn by base requirement text, so readiness does not
    regress between turns."""
    base = "A small bakery needs a system to track custom cake orders."

    turn1 = json.loads(json.dumps(VALID_PAYLOAD))
    turn1["slot_evidence"] = [
        {
            "category_id": "goal_scope",
            "slot_id": "business_goal",
            "applicability": "applicable",
            "strength": "strong",
            "evidence_quote": "track custom cake orders",
            "rationale": "explicit goal",
        },
        {
            "category_id": "goal_scope",
            "slot_id": "in_scope_outcome",
            "applicability": "applicable",
            "strength": "strong",
            "evidence_quote": "track custom cake orders",
            "rationale": "in-scope outcome",
        },
    ]

    # Turn 2 drifts: marks the previously-strong goal slot as not_applicable
    # AND returns empty for the others. Carry-forward + rigid applicability
    # rule must keep turn 1's strong verdicts intact.
    turn2 = json.loads(json.dumps(VALID_PAYLOAD))
    turn2["slot_evidence"] = [
        {
            "category_id": "goal_scope",
            "slot_id": "business_goal",
            "applicability": "not_applicable",
            "strength": "none",
            "evidence_quote": "",
            "rationale": "drift",
        },
    ]

    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([turn1, turn2])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    # Turn 1 — signed-in: NO guest_draft_id.
    r1 = client.post("/analysis/requirement", json={"requirement_text": base})
    assert r1.status_code == 200
    score1 = r1.json()["analysis"]["questionnaire"]["draft_readiness"]["score"]
    assert score1 > 0

    # Turn 2 — same session: base text matches, no guest_draft_id.
    r2 = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                f"{base}\n\n"
                "Previous question: [category: goal_scope][slot: in_scope_outcome] "
                "What outcomes?\n"
                "Previous answer: Faster order processing"
            )
        },
    )
    assert r2.status_code == 200
    questionnaire = r2.json()["analysis"]["questionnaire"]
    score2 = questionnaire["draft_readiness"]["score"]
    # Carry-forward via base-text lookup must keep turn 1's strong evidence
    # intact even though the new turn would have wiped it.
    assert score2 >= score1, (
        f"signed-in carry-forward regressed: turn1={score1} turn2={score2}"
    )
    # The drift verdict (not_applicable) must NOT kill the previously strong slot.
    categories = {c["id"]: c for c in questionnaire["categories"]}
    assert categories["goal_scope"]["weakest_slot_strength"] == "strong"


def test_ratchet_keeps_cleared_category_cleared_across_drift_turn():
    """Once a category is cleared (Ready), a later drift turn that judges
    its slots weakly must NOT re-open it. This is the user-facing
    'no revert, no pop-up' guarantee."""
    base = "A bakery needs to track cake orders end to end."
    turn1 = json.loads(json.dumps(VALID_PAYLOAD))
    turn1["slot_evidence"] = [
        {
            "category_id": "goal_scope",
            "slot_id": "business_goal",
            "applicability": "applicable",
            "strength": "strong",
            "evidence_quote": "track cake orders",
            "rationale": "explicit",
        },
        {
            "category_id": "goal_scope",
            "slot_id": "in_scope_outcome",
            "applicability": "applicable",
            "strength": "strong",
            "evidence_quote": "track cake orders",
            "rationale": "in-scope",
        },
    ]
    # Turn 2 adversarially marks BOTH goal_scope slots as none, plus drift
    # to not_applicable on one of them.
    turn2 = json.loads(json.dumps(VALID_PAYLOAD))
    turn2["slot_evidence"] = [
        {
            "category_id": "goal_scope",
            "slot_id": "business_goal",
            "applicability": "not_applicable",
            "strength": "none",
            "evidence_quote": "",
            "rationale": "drift",
        },
        {
            "category_id": "goal_scope",
            "slot_id": "in_scope_outcome",
            "applicability": "applicable",
            "strength": "none",
            "evidence_quote": "",
            "rationale": "drift",
        },
    ]

    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([turn1, turn2])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    r1 = client.post("/analysis/requirement", json={"requirement_text": base})
    assert r1.status_code == 200
    cats1 = {c["id"]: c for c in r1.json()["analysis"]["questionnaire"]["categories"]}
    assert cats1["goal_scope"]["status"] == "ready"

    r2 = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                f"{base}\n\n"
                "Previous question: [category: users_roles][slot: primary_users] "
                "Who uses it?\n"
                "Previous answer: Counter staff and bakers"
            )
        },
    )
    assert r2.status_code == 200
    questionnaire = r2.json()["analysis"]["questionnaire"]
    cats2 = {c["id"]: c for c in questionnaire["categories"]}
    # Ratchet invariant: goal_scope stays Ready despite the drift verdict.
    assert cats2["goal_scope"]["status"] == "ready"
    # Active slot must never wander back to a cleared category.
    assert questionnaire["active_category_id"] != "goal_scope"


# --- Guards A & B: anti-loop for slots Gemini's judgement keeps missing ---


def _empty_evidence_payload(target_category, target_slot_id, question_text):
    payload = json.loads(json.dumps(VALID_PAYLOAD))
    payload["next_question"] = {
        "text": question_text,
        "why_this_matters": "Follow-up.",
        "choices": [
            {"id": "a", "label": "Option A"},
            {"id": "b", "label": "Option B"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": target_category,
        "target_slot_id": target_slot_id,
    }
    payload["slot_evidence"] = []  # Gemini misses this slot entirely
    return payload


def test_guard_a_long_substantive_answer_covers_slot_when_gemini_misses_it():
    """Guard A: a >=60-char free-text answer covers the slot even if
    Gemini returned no slot_evidence for it. Stops the workflow_steps
    stuck loop the user hit in the laundry test."""
    p1 = _empty_evidence_payload(
        "workflow_steps",
        "normal_flow",
        "What are the main steps in processing a customer's order?",
    )
    p2 = _empty_evidence_payload(
        "workflow_steps",
        "normal_flow",
        "What are the main steps in processing a customer's order?",
    )
    model = FakeRequirementAnalysisModel([p1, p2])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=RequirementAnalysisRepository(),
        )
    )
    # Turn 1: prime the prior so slot/category markers are in scope.
    r1 = client.post(
        "/analysis/requirement",
        json={"requirement_text": "Small laundry shop wants order tracking."},
    )
    assert r1.status_code == 200
    # Turn 2: user submits a long, substantive answer for normal_flow.
    long_answer = (
        "Customer drops off laundry and an order is created, staff wash, "
        "dry, iron and pack the items, customer picks up and pays."
    )
    assert len(long_answer) >= 60
    r2 = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": (
                "Small laundry shop wants order tracking.\n\n"
                "Previous question: [category: workflow_steps] "
                "[slot: normal_flow] What are the main steps?\n"
                f"Previous answer: {long_answer}"
            )
        },
    )
    assert r2.status_code == 200
    cats = {
        c["id"]: c
        for c in r2.json()["analysis"]["questionnaire"]["categories"]
    }
    assert cats["workflow_steps"]["questions_answered"] >= 1
    # The active slot must advance off normal_flow now that it's covered.
    active_slot = r2.json()["analysis"]["questionnaire"]["active_slot_id"]
    assert active_slot != "normal_flow" or (
        cats["workflow_steps"]["status"] in {"ready", "in_progress"}
    )


def test_guard_b_three_repeated_answers_force_cover_the_slot():
    """Guard B: even with short generic answers (below Guard A's threshold),
    the third repeat of the same (category, slot) force-covers the slot so
    the user is never trapped in an infinite loop."""
    p = _empty_evidence_payload(
        "workflow_steps",
        "normal_flow",
        "Which normal flow best matches the work?",
    )
    model = FakeRequirementAnalysisModel([p, p, p, p])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=RequirementAnalysisRepository(),
        )
    )
    client.post(
        "/analysis/requirement",
        json={"requirement_text": "Small laundry shop wants order tracking."},
    )
    short_answer = "register process close"  # 22 chars, below Guard A
    prior_block = (
        "Previous question: [category: workflow_steps] "
        "[slot: normal_flow] Which normal flow best matches the work?\n"
        f"Previous answer: {short_answer}\n\n"
    )
    for repeat in range(1, 4):
        body = (
            "Small laundry shop wants order tracking.\n\n"
            + prior_block * repeat
        )
        resp = client.post(
            "/analysis/requirement", json={"requirement_text": body}
        )
        assert resp.status_code == 200
    final = resp.json()["analysis"]["questionnaire"]
    cats = {c["id"]: c for c in final["categories"]}
    # After the 3rd repeat, normal_flow must be covered by the anti-loop
    # backstop — questions_answered for workflow_steps reflects coverage.
    assert cats["workflow_steps"]["questions_answered"] >= 1
