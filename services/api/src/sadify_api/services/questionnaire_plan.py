from collections.abc import Iterable, Mapping

from sadify_api.schemas import (
    QuestionnairePlan,
    QuestionnairePlanCategory,
    QuestionnairePlanReadiness,
    QuestionnairePlanSlot,
    QuestionnairePlanSlotPointer,
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
            )
            for slot_id, label, required in blueprint["slots"]
        ]
        categories.append(
            _build_category(
                category_id=category_id,
                label=str(blueprint["label"]),
                display_order=display_order,
                slots=slots,
                initial_visibility=True,
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
    return _update_slot(plan, category_id, slot_id, "covered")


def defer_slot(
    plan: QuestionnairePlan,
    category_id: str,
    slot_id: str,
) -> QuestionnairePlan:
    return _update_slot(plan, category_id, slot_id, "confirm_later")


def reopen_slot(
    plan: QuestionnairePlan,
    category_id: str,
    slot_id: str,
) -> QuestionnairePlan:
    return _update_slot(plan, category_id, slot_id, "open")


def next_open_slot(plan: QuestionnairePlan) -> QuestionnairePlanSlotPointer | None:
    for category in sorted(plan.categories, key=lambda item: item.display_order):
        if category.visibility in {"already_understood", "completed", "suggested"}:
            continue
        for slot in category.slots:
            if slot.required and slot.status == "open":
                return QuestionnairePlanSlotPointer(
                    category_id=category.id,
                    slot_id=slot.id,
                )
    return None


def recalculate_readiness(plan: QuestionnairePlan) -> QuestionnairePlan:
    categories = [_refresh_category(category) for category in plan.categories]
    required_slots = [
        slot
        for category in categories
        for slot in category.slots
        if slot.required
    ]
    covered_slots = [slot for slot in required_slots if slot.status == "covered"]
    score = round(100 * len(covered_slots) / len(required_slots)) if required_slots else 100
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


def _update_slot(
    plan: QuestionnairePlan,
    category_id: str,
    slot_id: str,
    status: str,
) -> QuestionnairePlan:
    categories: list[QuestionnairePlanCategory] = []
    for category in plan.categories:
        if category.id != category_id:
            categories.append(category)
            continue
        slots = [
            slot.model_copy(update={"status": status})
            if slot.id == slot_id
            else slot
            for slot in category.slots
        ]
        if not any(slot.id == slot_id for slot in category.slots):
            raise KeyError(slot_id)
        categories.append(category.model_copy(update={"slots": slots}))
    if not any(category.id == category_id for category in plan.categories):
        raise KeyError(category_id)
    return recalculate_readiness(plan.model_copy(update={"categories": categories}))


def _build_category(
    *,
    category_id: str,
    label: str,
    display_order: int,
    slots: list[QuestionnairePlanSlot],
    initial_visibility: bool,
) -> QuestionnairePlanCategory:
    status = _category_status(slots)
    visibility = "main"
    if initial_visibility and status == "ready":
        visibility = "already_understood"
    return QuestionnairePlanCategory(
        id=category_id,
        label=label,
        display_order=display_order,
        visibility=visibility,
        status=status,
        slots=slots,
    )


def _refresh_category(category: QuestionnairePlanCategory) -> QuestionnairePlanCategory:
    status = _category_status(category.slots)
    visibility = category.visibility
    if visibility == "already_understood" and status != "ready":
        visibility = "main"
    elif visibility == "main" and status == "ready":
        visibility = "completed"
    elif visibility == "completed" and status != "ready":
        visibility = "main"
    return category.model_copy(update={"status": status, "visibility": visibility})


def _category_status(slots: list[QuestionnairePlanSlot]) -> str:
    required_slots = [slot for slot in slots if slot.required]
    if all(slot.status == "covered" for slot in required_slots):
        return "ready"
    if any(slot.status == "confirm_later" for slot in required_slots):
        return "confirm_later"
    if any(slot.status == "covered" for slot in required_slots):
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
