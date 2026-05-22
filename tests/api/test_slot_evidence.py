from sadify_api.schemas import (
    QuestionnairePlanSlot,
    RequirementAnalysisResponse,
    SlotEvidence,
)


def test_slot_evidence_defaults():
    verdict = SlotEvidence(category_id="goal_scope", slot_id="business_goal")
    assert verdict.applicability == "applicable"
    assert verdict.strength == "none"
    assert verdict.evidence_quote == ""
    assert verdict.rationale == ""


def test_questionnaire_plan_slot_has_evidence_fields():
    slot = QuestionnairePlanSlot(id="business_goal", label="Business goal")
    assert slot.evidence_strength == "none"
    assert slot.applicable is True


def test_requirement_analysis_response_defaults_slot_evidence_to_empty():
    response = RequirementAnalysisResponse(
        understanding_summary="A team needs a tracking system.",
        readiness={"label": "Getting started", "score": 10, "confidence": "Low"},
        categories=[{"id": "goal_scope", "label": "Goal", "status": "missing"}],
        next_question={
            "text": "What is the goal?",
            "why_this_matters": "Clarifies the goal.",
            "choices": [
                {"id": "a", "label": "Reduce delays"},
                {"id": "b", "label": "Reduce errors"},
            ],
            "target_category": "goal_scope",
            "target_slot_id": "business_goal",
        },
        assumptions=[],
        source_references=[],
    )
    assert response.slot_evidence == []
