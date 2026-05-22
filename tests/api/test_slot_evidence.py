from sadify_api.schemas import (
    QuestionnairePlanSlot,
    RequirementAnalysisResponse,
    SlotEvidence,
)
from sadify_api.services.slot_evidence import (
    derive_confidence,
    evidence_map,
    validate_slot_evidence,
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


def _verdict(category_id, slot_id, strength, quote="", applicability="applicable"):
    return SlotEvidence(
        category_id=category_id,
        slot_id=slot_id,
        applicability=applicability,
        strength=strength,
        evidence_quote=quote,
    )


def test_validate_keeps_verdict_with_quote_present_in_material():
    material = "Staff submit a maintenance request when a machine has an issue."
    verdicts, diagnostics = validate_slot_evidence(
        [
            _verdict(
                "workflow_steps",
                "normal_flow",
                "strong",
                "staff submit a maintenance request",
            )
        ],
        material=material,
    )
    assert verdicts[0].strength == "strong"
    assert diagnostics == []


def test_validate_downgrades_strong_verdict_with_missing_quote():
    verdicts, diagnostics = validate_slot_evidence(
        [
            _verdict(
                "workflow_steps",
                "normal_flow",
                "strong",
                "invented text not in material",
            )
        ],
        material="A team needs a tracking system.",
    )
    assert verdicts[0].strength == "partial"
    assert len(diagnostics) == 1


def test_validate_downgrades_partial_verdict_with_empty_quote_to_none():
    verdicts, diagnostics = validate_slot_evidence(
        [_verdict("workflow_steps", "normal_flow", "partial", "")],
        material="A team needs a tracking system.",
    )
    assert verdicts[0].strength == "none"
    assert len(diagnostics) == 1


def test_validate_ignores_quote_for_none_and_not_applicable():
    verdicts, diagnostics = validate_slot_evidence(
        [
            _verdict("integrations", "external_systems", "none", ""),
            _verdict(
                "integrations",
                "external_systems",
                "none",
                "",
                "not_applicable",
            ),
        ],
        material="A team needs a tracking system.",
    )
    assert diagnostics == []


def test_derive_confidence_high_when_mostly_strong_and_no_downgrades():
    verdicts = [_verdict("c", f"s{i}", "strong", "q") for i in range(10)]
    assert derive_confidence(verdicts, downgrade_count=0) == "High"


def test_derive_confidence_low_when_mostly_none():
    verdicts = [_verdict("c", f"s{i}", "none") for i in range(8)]
    verdicts += [_verdict("c", f"s{i}", "partial", "q") for i in range(2)]
    assert derive_confidence(verdicts, downgrade_count=0) == "Low"


def test_derive_confidence_low_when_two_or_more_downgrades():
    verdicts = [_verdict("c", f"s{i}", "strong", "q") for i in range(10)]
    assert derive_confidence(verdicts, downgrade_count=2) == "Low"


def test_evidence_map_keys_by_category_and_slot():
    mapping = evidence_map(
        [_verdict("goal_scope", "business_goal", "strong", "q")]
    )
    assert mapping[("goal_scope", "business_goal")].strength == "strong"
