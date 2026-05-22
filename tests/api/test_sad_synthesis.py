from sadify_api.schemas import RequirementAnalysisResponse
from sadify_api.services.sad_synthesis import (
    build_sad_synthesis_context,
    clean_business_request,
)


CLINIC_REQUEST = (
    "Small clinic wants to track patient registration, queue status, doctor "
    "consultation, medicine collection, and payment in one simple system. "
    "Reception staff register patients and update queue status. Doctors record "
    "consultation notes. Pharmacy staff prepare medicine. Cashier records "
    "payment. Manager needs a daily summary of patients served, waiting time, "
    "and unpaid bills. Some patients may skip payment or leave before collecting "
    "medicine."
)


def test_clean_business_request_strips_qna_transport_history():
    polluted = (
        "Small clinic wants to track registration and payment.\n\n"
        "Previous question: [category: data_records][slot: critical_fields] "
        "Which details are essential?\n\n"
        "Previous answer: Names or identifiers\n\n"
        "Previous readiness: 53"
    )

    assert clean_business_request(polluted) == (
        "Small clinic wants to track registration and payment."
    )


def test_synthesis_keeps_request_facts_and_answers():
    context = build_sad_synthesis_context(
        requirement_text=CLINIC_REQUEST,
        analysis_id="AN-000010",
        analysis=_clinic_analysis_with_answers(),
        source_context=None,
        source_references=["Business Request"],
    )

    assert "Confirmed request facts:" in context
    assert "patient registration" in context
    assert "queue status" in context
    assert "doctor consultation" in context
    assert "medicine collection" in context
    assert "payment" in context
    assert "Manager needs a daily summary" in context
    assert "Confirmed questionnaire answers:" in context
    assert "Unpaid visits stay open for follow-up" in context


def test_synthesis_filters_internal_diagnostics_from_user_assumptions():
    context = build_sad_synthesis_context(
        requirement_text=CLINIC_REQUEST,
        analysis_id="AN-000010",
        analysis=_clinic_fallback_analysis(),
        source_context=None,
        source_references=[],
    )

    business_section = context.split("Business-facing assumptions:", 1)[1]
    business_section = business_section.split("Business source references:", 1)[0]
    assert "Fallback was used" not in business_section
    assert "Gemini output could not be validated" not in business_section
    assert "Internal diagnostics, not for SAD assumptions:" in context
    assert "Fallback was used" in context
    assert "Business Request" in context


def _clinic_analysis_with_answers() -> RequirementAnalysisResponse:
    payload = _base_analysis_payload()
    payload["questionnaire"] = {
        "draft_readiness": {
            "label": "Ready for draft",
            "score": 100,
            "confidence": "High",
        },
        "active_category_id": "rules_approvals",
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
            },
            {
                "id": "rules_approvals",
                "label": "Business rules and approvals",
                "status": "ready",
                "visibility": "completed",
                "progress": 100,
                "questions_total": 2,
                "questions_answered": 2,
                "is_active": False,
            },
        ],
        "answers": [
            {
                "category_id": "workflow_steps",
                "slot_id": "required_handling",
                "question": "How should unpaid visits be handled?",
                "answer": "Unpaid visits stay open for follow-up",
                "is_uncertain": False,
            }
        ],
        "diagnostics": ["Gemini structured output validated"],
    }
    return RequirementAnalysisResponse.model_validate(payload)


def _clinic_fallback_analysis() -> RequirementAnalysisResponse:
    payload = _base_analysis_payload()
    payload["assumptions"] = [
        "Fallback was used because Gemini returned invalid structured analysis after retry.",
        "Gemini output could not be validated, so a same-slot fallback was used.",
        "The clinic operates as one location.",
    ]
    payload["questionnaire"] = {
        "draft_readiness": {
            "label": "Ready for draft",
            "score": 100,
            "confidence": "Low",
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
        "answers": [],
        "diagnostics": ["structured-output fallback used"],
    }
    return RequirementAnalysisResponse.model_validate(payload)


def _base_analysis_payload() -> dict[str, object]:
    return {
        "understanding_summary": "The clinic needs one simple patient flow system.",
        "readiness": {
            "label": "Fallback question ready",
            "score": 35,
            "confidence": "Low",
        },
        "categories": [
            {
                "id": "workflow_steps",
                "label": "Workflow steps",
                "status": "partial",
            }
        ],
        "next_question": {
            "text": "Which exception should be clarified?",
            "why_this_matters": "This keeps the patient flow safe.",
            "choices": [
                {"id": "skip_payment", "label": "Patient leaves without paying"},
                {"id": "skip_medicine", "label": "Patient leaves before collecting medicine"},
            ],
            "target_category": "workflow_steps",
            "target_slot_id": "required_handling",
            "selection_mode": "single",
        },
        "assumptions": [],
        "source_references": ["Business Request"],
        "proposed_extra_categories": [],
    }
