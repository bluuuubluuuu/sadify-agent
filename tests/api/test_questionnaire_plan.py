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


def test_deferring_every_required_slot_does_not_grant_readiness():
    """Deferring without evidence must not auto-grant readiness (F1: defer != covered)."""
    plan = create_initial_plan(initial_facts={})
    for category in plan.categories:
        for slot in category.slots:
            if slot.required:
                plan = defer_slot(plan, category.id, slot.id)

    assert plan.overall_readiness.score == 0


def test_partial_evidence_score_is_half():
    """F3 sanity: partial evidence weights 0.5, so a single partial slot in an
    otherwise empty plan moves the score off zero by exactly that fraction."""
    plan = create_plan_from_evidence(
        [SlotEvidence(category_id="goal_scope", slot_id="business_goal",
                      strength="partial", evidence_quote="q")]
    )
    # 19 required applicable slots total; one at 0.5 → 100 * 0.5 / 19 ≈ 3.
    assert plan.overall_readiness.score == round(100 * 0.5 / 19)


# --- One-way category ratchet --------------------------------------------


def _strong(category_id, slot_id):
    return SlotEvidence(
        category_id=category_id,
        slot_id=slot_id,
        applicability="applicable",
        strength="strong",
        evidence_quote="q",
    )


def test_category_becomes_locked_ready_when_all_required_slots_covered():
    """Once a category reaches Ready, it should carry a locked_ready flag."""
    plan = create_plan_from_evidence([
        _strong("goal_scope", "business_goal"),
        _strong("goal_scope", "in_scope_outcome"),
    ])
    assert plan.category("goal_scope").status == "ready"
    assert plan.category("goal_scope").locked_ready is True


def test_locked_ready_category_stays_ready_when_evidence_disappears():
    """Adversarial: even if a later turn's evidence is missing or downgraded,
    a once-Ready category must stay Ready and stay out of the active queue."""
    before = create_plan_from_evidence([
        _strong("goal_scope", "business_goal"),
        _strong("goal_scope", "in_scope_outcome"),
    ])
    # Carry locked_ready forward into a "next turn" plan rebuild that would
    # otherwise show goal_scope at none for both slots.
    after = create_plan_from_evidence(
        [],
        prior_locked_categories=
            {c.id for c in before.categories if c.locked_ready},
    )
    assert after.category("goal_scope").status == "ready"
    assert after.category("goal_scope").locked_ready is True


def test_next_open_slot_skips_locked_ready_categories():
    """Active-slot picker must never return a slot inside a locked category."""
    plan = create_plan_from_evidence(
        [_strong("goal_scope", "business_goal"),
         _strong("goal_scope", "in_scope_outcome")]
    )
    pointer = next_open_slot(plan)
    assert pointer is not None
    assert pointer.category_id != "goal_scope"


def test_category_does_not_lock_when_only_partially_ready():
    """A category with one partial slot is in_progress, not Ready, and must
    NOT be locked."""
    plan = create_plan_from_evidence([
        _strong("goal_scope", "business_goal"),
        SlotEvidence(category_id="goal_scope", slot_id="in_scope_outcome",
                     strength="partial", evidence_quote="q"),
    ])
    assert plan.category("goal_scope").status != "ready"
    assert plan.category("goal_scope").locked_ready is False


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
