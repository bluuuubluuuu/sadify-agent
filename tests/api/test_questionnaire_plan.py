from sadify_api.schemas import SlotEvidence
from sadify_api.services.questionnaire_plan import (
    CANONICAL_CATEGORY_IDS,
    cover_slot,
    create_initial_plan,
    create_plan_from_evidence,
    defer_slot,
    next_open_slot,
    reopen_slot,
)


def test_plan_uses_canonical_categories_and_frozen_order():
    plan = create_initial_plan(
        initial_facts={
            "workflow_steps": {"normal_flow", "handoffs"},
        }
    )

    assert [category.id for category in plan.categories] == list(CANONICAL_CATEGORY_IDS)
    assert plan.category("workflow_steps").visibility == "already_understood"
    assert plan.category("workflow_steps").status == "ready"


def test_readiness_uses_required_slot_coverage_not_question_count():
    plan = create_initial_plan(initial_facts={})
    updated = cover_slot(plan, "users_roles", "primary_users")

    assert updated.category("users_roles").status == "in_progress"
    assert updated.overall_readiness.score > plan.overall_readiness.score


def test_initial_fact_coverage_counts_toward_weighted_readiness():
    empty_plan = create_initial_plan(initial_facts={})
    seeded_plan = create_initial_plan(
        initial_facts={"workflow_steps": {"normal_flow"}}
    )
    slot = seeded_plan.category("workflow_steps").slot("normal_flow")

    assert slot.status == "covered"
    assert slot.evidence_strength == "strong"
    assert seeded_plan.overall_readiness.score > empty_plan.overall_readiness.score


def test_next_open_slot_stays_in_first_unresolved_category():
    plan = create_initial_plan(initial_facts={})
    first_slot = next_open_slot(plan)
    updated = cover_slot(plan, "goal_scope", "business_goal")
    second_slot = next_open_slot(updated)

    assert first_slot is not None
    assert (first_slot.category_id, first_slot.slot_id) == (
        "goal_scope",
        "business_goal",
    )
    assert second_slot is not None
    assert (second_slot.category_id, second_slot.slot_id) == (
        "goal_scope",
        "in_scope_outcome",
    )


def test_deferred_slots_can_be_reopened_without_touching_other_categories():
    plan = create_initial_plan(initial_facts={})
    deferred = defer_slot(plan, "goal_scope", "business_goal")
    reopened = reopen_slot(deferred, "goal_scope", "business_goal")

    assert deferred.category("goal_scope").status == "confirm_later"
    assert deferred.category("goal_scope").slot("business_goal").status == "confirm_later"
    assert reopened.category("goal_scope").slot("business_goal").status == "open"
    assert reopened.category("users_roles").status == "needs_answer"


def _verdict(category_id, slot_id, strength, applicability="applicable"):
    return SlotEvidence(
        category_id=category_id,
        slot_id=slot_id,
        applicability=applicability,
        strength=strength,
        evidence_quote="quote" if strength != "none" else "",
    )


def test_create_plan_from_evidence_sets_slot_strength():
    plan = create_plan_from_evidence(
        [_verdict("goal_scope", "business_goal", "strong")]
    )
    slot = plan.category("goal_scope").slot("business_goal")
    assert slot.evidence_strength == "strong"
    assert slot.status == "covered"


def test_partial_evidence_keeps_slot_open_and_scores_half():
    strong_plan = create_plan_from_evidence(
        [_verdict("goal_scope", "business_goal", "strong")]
    )
    partial_plan = create_plan_from_evidence(
        [_verdict("goal_scope", "business_goal", "partial")]
    )
    assert partial_plan.category("goal_scope").slot("business_goal").status == "open"
    assert 0 < partial_plan.overall_readiness.score < strong_plan.overall_readiness.score


def test_not_applicable_slots_leave_the_readiness_denominator():
    integrations = [
        _verdict("integrations", "external_systems", "none", "not_applicable"),
    ]
    baseline = create_plan_from_evidence([])
    with_na = create_plan_from_evidence(integrations)
    assert with_na.category("integrations").visibility == "not_applicable"
    assert with_na.overall_readiness.score >= baseline.overall_readiness.score


def test_next_open_slot_skips_not_applicable_slots():
    plan = create_plan_from_evidence(
        [_verdict("goal_scope", "business_goal", "none", "not_applicable")]
    )
    pointer = next_open_slot(plan)
    assert pointer is not None
    assert (pointer.category_id, pointer.slot_id) != ("goal_scope", "business_goal")
