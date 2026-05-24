from collections.abc import Iterable, Mapping

from sadify_api.schemas import (
    QuestionnairePlan,
    QuestionnairePlanCategory,
    QuestionnairePlanReadiness,
    QuestionnairePlanSlot,
    QuestionnairePlanSlotPointer,
    SlotEvidence,
)

CANONICAL_CATEGORY_IDS = (
    "goal_scope",
    "users_roles",
    "workflow_steps",
    "data_records",
    "rules_approvals",
    "exceptions_edges",
    "reports_summaries",
    "access_permissions",
    "integrations",
    "non_functional",
)

_CATEGORY_BLUEPRINTS = (
    {
        "id": "goal_scope",
        "label": "Goal and scope",
        "slots": (
            ("business_goal", "Business goal", True),
            ("in_scope_outcome", "In-scope outcome", True),
            ("out_of_scope_boundary", "Out-of-scope boundary", False),
        ),
    },
    {
        "id": "users_roles",
        "label": "Users and roles",
        "slots": (
            ("primary_users", "Primary users", True),
            ("responsibilities", "Core responsibilities", True),
            ("access_boundary", "Access boundary", False),
        ),
    },
    {
        "id": "workflow_steps",
        "label": "Workflow steps",
        "slots": (
            ("normal_flow", "Normal flow", True),
            ("handoffs", "Handoffs and status changes", True),
            ("completion_condition", "Completion condition", False),
        ),
    },
    {
        "id": "data_records",
        "label": "Data and records",
        "slots": (
            ("main_records", "Main records", True),
            ("critical_fields", "Critical fields", True),
            ("reporting_linkage", "Reporting linkage", False),
        ),
    },
    {
        "id": "rules_approvals",
        "label": "Business rules and approvals",
        "slots": (
            ("triggering_rules", "Triggering rules", True),
            ("approval_path", "Approval path", True),
            ("decision_authority", "Decision authority", False),
        ),
    },
    {
        "id": "exceptions_edges",
        "label": "Exceptions and edge cases",
        "slots": (
            ("common_exception", "Common exception", True),
            ("required_handling", "Required handling", True),
            ("reconciliation", "Follow-up or reconciliation", False),
        ),
    },
    {
        "id": "reports_summaries",
        "label": "Reports and summaries",
        "slots": (
            ("needed_outputs", "Needed outputs", True),
            ("audience", "Audience", True),
            ("cadence_filters", "Cadence and filters", False),
        ),
    },
    {
        "id": "access_permissions",
        "label": "Access and permissions",
        "slots": (
            ("access_model", "Access model", True),
            ("sensitive_actions", "Sensitive actions", True),
            ("override_handling", "Override handling", False),
        ),
    },
    {
        "id": "integrations",
        "label": "Integrations",
        "slots": (
            ("external_systems", "External systems", True),
            ("data_exchange_need", "Data exchange need", False),
        ),
    },
    {
        "id": "non_functional",
        "label": "Non-functional needs",
        "slots": (
            ("security_privacy", "Security or privacy needs", True),
            ("audit_history", "Audit or history needs", True),
            ("volume_constraints", "Volume or performance constraints", False),
        ),
    },
)


def canonical_required_slots() -> list[tuple[str, str, str]]:
    """Return (category_id, slot_id, label) for every required slot."""
    entries: list[tuple[str, str, str]] = []
    for blueprint in _CATEGORY_BLUEPRINTS:
        category_id = str(blueprint["id"])
        for slot_id, label, required in blueprint["slots"]:
            if required:
                entries.append((category_id, slot_id, label))
    return entries


def create_initial_plan(
    initial_facts: Mapping[str, Iterable[str]],
    *,
    plan_id: str = "QPLAN-001",
) -> QuestionnairePlan:
    normalised_facts = {
        category_id: set(slot_ids)
        for category_id, slot_ids in initial_facts.items()
    }
    categories: list[QuestionnairePlanCategory] = []
    for display_order, blueprint in enumerate(_CATEGORY_BLUEPRINTS, start=1):
        category_id = str(blueprint["id"])
        covered_slots = normalised_facts.get(category_id, set())
        slots = [
            QuestionnairePlanSlot(
                id=slot_id,
                label=label,
                required=required,
                status="covered" if slot_id in covered_slots else "open",
                evidence_strength="strong"
                if slot_id in covered_slots
                else "none",
            )
            for slot_id, label, required in blueprint["slots"]
        ]
        # No Q&A has happened yet, so any category that is Ready here came
        # from the original requirement text / uploaded files.
        categories.append(
            _build_category(
                category_id=category_id,
                label=str(blueprint["label"]),
                display_order=display_order,
                slots=slots,
                understood_via="source",
            )
        )

    return recalculate_readiness(
        QuestionnairePlan(
            plan_id=plan_id,
            active_category_id=None,
            categories=categories,
            overall_readiness=QuestionnairePlanReadiness(
                label="Getting started",
                score=0,
            ),
        )
    )


def create_plan_from_evidence(
    verdicts: list[SlotEvidence],
    *,
    plan_id: str = "QPLAN-001",
    prior_locked_categories: set[str] | None = None,
    prior_understood_via: Mapping[str, str] | None = None,
    default_new_provenance: str = "qa",
) -> QuestionnairePlan:
    """Build a questionnaire plan from validated slot evidence verdicts.

    Each verdict sets a slot's evidence_strength and applicable flag. A slot
    is covered for Q&A flow only when its strength is strong; partial slots
    stay open so they still get a question.

    `prior_locked_categories` carries forward the one-way ratchet across
    turns: any category that was ever Ready stays Ready, with its slots
    forced covered and visibility locked. This is what stops category
    reversal — once cleared, a category cannot be re-opened.

    `prior_understood_via` carries forward the frozen "source" vs "qa"
    provenance so the Already-understood vs Completed-areas bucket label
    never flips between turns. New categories that become Ready in this
    turn are tagged with `default_new_provenance` ("qa" in the live flow
    because the user has just answered something; "source" only on the
    very first analysis turn before any answers exist).
    """
    locked = set(prior_locked_categories or set())
    provenance_in = dict(prior_understood_via or {})
    by_slot = {
        (verdict.category_id, verdict.slot_id): verdict for verdict in verdicts
    }
    categories: list[QuestionnairePlanCategory] = []
    for display_order, blueprint in enumerate(_CATEGORY_BLUEPRINTS, start=1):
        category_id = str(blueprint["id"])
        is_locked = category_id in locked
        slots: list[QuestionnairePlanSlot] = []
        for slot_id, label, required in blueprint["slots"]:
            verdict = by_slot.get((category_id, slot_id))
            strength = verdict.strength if verdict else "none"
            applicable = (
                verdict.applicability == "applicable" if verdict else True
            )
            if is_locked and required and applicable:
                # Ratchet: a locked-ready category's required slots are
                # forced covered + strong regardless of this turn's verdict.
                strength = "strong"
                status = "covered"
            else:
                status = "covered" if strength == "strong" else "open"
            slots.append(
                QuestionnairePlanSlot(
                    id=slot_id,
                    label=label,
                    required=required,
                    status=status,
                    evidence_strength=strength,
                    applicable=applicable,
                )
            )
        will_be_ready = is_locked or _category_status(slots) == "ready"
        understood_via: str | None = provenance_in.get(category_id)
        if understood_via is None and will_be_ready:
            understood_via = default_new_provenance
        categories.append(
            _build_category(
                category_id=category_id,
                label=str(blueprint["label"]),
                display_order=display_order,
                slots=slots,
                understood_via=understood_via,
                locked_ready=is_locked,
            )
        )
    return recalculate_readiness(
        QuestionnairePlan(
            plan_id=plan_id,
            active_category_id=None,
            categories=categories,
            overall_readiness=QuestionnairePlanReadiness(
                label="Getting started",
                score=0,
            ),
        )
    )


def cover_slot(
    plan: QuestionnairePlan,
    category_id: str,
    slot_id: str,
) -> QuestionnairePlan:
    return _update_slot(
        plan, category_id, slot_id, "covered", evidence_strength="strong"
    )


def defer_slot(
    plan: QuestionnairePlan,
    category_id: str,
    slot_id: str,
) -> QuestionnairePlan:
    return _update_slot(plan, category_id, slot_id, "confirm_later")


def dismiss_slot(
    plan: QuestionnairePlan,
    category_id: str,
    slot_id: str,
) -> QuestionnairePlan:
    """Mark a slot as covered WITHOUT changing its evidence strength.

    Used by the anti-loop backstop: when the user has answered the same
    slot 2+ times, remove it from the question queue, but don't fake
    'strong' evidence — keep whatever Gemini/Guard A actually judged so
    the readiness score still reflects real evidence quality.
    """
    return _update_slot(plan, category_id, slot_id, "covered")


def reopen_slot(
    plan: QuestionnairePlan,
    category_id: str,
    slot_id: str,
) -> QuestionnairePlan:
    return _update_slot(
        plan, category_id, slot_id, "open", evidence_strength="none"
    )


def next_open_slot(plan: QuestionnairePlan) -> QuestionnairePlanSlotPointer | None:
    for category in sorted(plan.categories, key=lambda item: item.display_order):
        # Ratchet: locked-ready categories are out of the active queue forever.
        if category.locked_ready:
            continue
        if category.visibility in {"already_understood", "completed", "suggested"}:
            continue
        for slot in category.slots:
            if slot.required and slot.applicable and slot.status == "open":
                return QuestionnairePlanSlotPointer(
                    category_id=category.id,
                    slot_id=slot.id,
                )
    return None


def recalculate_readiness(plan: QuestionnairePlan) -> QuestionnairePlan:
    categories = [_refresh_category(category) for category in plan.categories]
    # Cycle 2A: fixed denominator. Score over ALL canonical required slots —
    # not_applicable counts as resolved (weight 1.0). This stops the
    # percentage from dropping when a slot transitions from not_applicable
    # to applicable+none, which previously grew the denominator without
    # adding to the numerator.
    required_slots = [
        slot
        for category in categories
        for slot in category.slots
        if slot.required
    ]
    score = (
        round(
            100
            * sum(_slot_weight(slot) for slot in required_slots)
            / len(required_slots)
        )
        if required_slots
        else 100
    )
    active_slot = next_open_slot(
        plan.model_copy(update={"categories": categories})
    )
    active_category_id = active_slot.category_id if active_slot else None
    return plan.model_copy(
        update={
            "active_category_id": active_category_id,
            "categories": categories,
            "overall_readiness": QuestionnairePlanReadiness(
                label=_readiness_label(score),
                score=score,
            ),
        }
    )


def _slot_weight(slot: QuestionnairePlanSlot) -> float:
    # Cycle 2A: not_applicable is a real resolution — the slot is off the
    # table, so it counts as fully covered toward readiness. Otherwise
    # weight by evidence strength. Deferring ("confirm_later") parks the
    # question without earning credit on its own; the SAD-preview gate
    # decides separately whether deferred gaps block the draft.
    if not slot.applicable:
        return 1.0
    if slot.evidence_strength == "strong":
        return 1.0
    if slot.evidence_strength == "partial":
        return 0.5
    return 0.0


def _update_slot(
    plan: QuestionnairePlan,
    category_id: str,
    slot_id: str,
    status: str,
    *,
    evidence_strength: str | None = None,
) -> QuestionnairePlan:
    categories: list[QuestionnairePlanCategory] = []
    for category in plan.categories:
        if category.id != category_id:
            categories.append(category)
            continue
        if not any(slot.id == slot_id for slot in category.slots):
            raise KeyError(slot_id)
        slots = []
        for slot in category.slots:
            if slot.id != slot_id:
                slots.append(slot)
                continue
            update: dict[str, object] = {"status": status}
            if evidence_strength is not None:
                update["evidence_strength"] = evidence_strength
            slots.append(slot.model_copy(update=update))
        categories.append(category.model_copy(update={"slots": slots}))
    if not any(category.id == category_id for category in plan.categories):
        raise KeyError(category_id)
    return recalculate_readiness(plan.model_copy(update={"categories": categories}))


def _derive_visibility(
    slots: list[QuestionnairePlanSlot],
    status: str,
    locked_ready: bool,
    understood_via: str | None,
) -> str:
    required_slots = [slot for slot in slots if slot.required]
    if required_slots and all(not slot.applicable for slot in required_slots):
        return "not_applicable"
    if locked_ready or status == "ready":
        # "source" = learned from the original requirement / uploads;
        # anything else (including unset) reads as Q&A-cleared.
        return "already_understood" if understood_via == "source" else "completed"
    return "main"


def _build_category(
    *,
    category_id: str,
    label: str,
    display_order: int,
    slots: list[QuestionnairePlanSlot],
    locked_ready: bool = False,
    understood_via: str | None = None,
) -> QuestionnairePlanCategory:
    status = _category_status(slots)
    if locked_ready:
        status = "ready"
    visibility = _derive_visibility(slots, status, locked_ready, understood_via)
    return QuestionnairePlanCategory(
        id=category_id,
        label=label,
        display_order=display_order,
        visibility=visibility,
        status=status,
        slots=slots,
        locked_ready=locked_ready,
        understood_via=understood_via,
    )


def _refresh_category(category: QuestionnairePlanCategory) -> QuestionnairePlanCategory:
    # Ratchet: a category that was ever Ready stays Ready forever.
    if category.locked_ready:
        visibility = _derive_visibility(
            category.slots, "ready", True, category.understood_via
        )
        return category.model_copy(
            update={"status": "ready", "visibility": visibility}
        )

    status = _category_status(category.slots)
    # First time this category reaches Ready in this session → engage the
    # ratchet. From here on it cannot regress.
    locked_ready = status == "ready"
    visibility = _derive_visibility(
        category.slots, status, locked_ready, category.understood_via
    )
    return category.model_copy(
        update={
            "status": status,
            "visibility": visibility,
            "locked_ready": locked_ready,
        }
    )


def _category_status(slots: list[QuestionnairePlanSlot]) -> str:
    required_slots = [slot for slot in slots if slot.required]
    applicable_required = [slot for slot in required_slots if slot.applicable]
    if not applicable_required:
        return "ready"
    if all(slot.status == "covered" for slot in applicable_required):
        return "ready"
    if any(slot.status == "confirm_later" for slot in applicable_required):
        return "confirm_later"
    if any(slot.status == "covered" for slot in applicable_required):
        return "in_progress"
    return "needs_answer"


def _readiness_label(score: int) -> str:
    if score >= 90:
        return "Ready for draft"
    if score >= 70:
        return "Mostly ready"
    if score >= 40:
        return "In progress"
    return "Getting started"
