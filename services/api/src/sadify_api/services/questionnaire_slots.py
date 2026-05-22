from typing import Any


SLOT_CONTRACTS: dict[tuple[str, str], dict[str, Any]] = {
    ("goal_scope", "business_goal"): {
        "terms": ("goal", "purpose", "achieve", "result", "reduce delays", "reduce errors"),
        "fallback": {
            "text": "What main result should this system help the business achieve?",
            "why_this_matters": "This gives the SAD a clear business goal.",
            "choices": [
                {"id": "reduce_delay", "label": "Reduce delays"},
                {"id": "reduce_errors", "label": "Reduce errors"},
                {"id": "improve_visibility", "label": "Improve visibility of the work"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "selection_mode": "single",
        },
    },
    ("goal_scope", "in_scope_outcome"): {
        "terms": ("include", "scope", "first version", "must support", "must cover", "outcome"),
        "fallback": {
            "text": "Which outcome must be included in the first version?",
            "why_this_matters": "This keeps the first scope clear enough to draft.",
            "choices": [
                {"id": "track_work", "label": "Track the main work from start to finish"},
                {"id": "manage_approvals", "label": "Manage approvals or decisions"},
                {"id": "produce_reports", "label": "Produce the needed summaries or reports"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "selection_mode": "single",
        },
    },
    ("users_roles", "primary_users"): {
        "terms": ("who will use", "which staff", "staff groups", "users", "reception", "doctor", "cashier"),
        "fallback": {
            "text": "Which staff groups will use this system?",
            "why_this_matters": "This identifies the main users before responsibilities are detailed.",
            "choices": [
                {"id": "frontline", "label": "Frontline staff"},
                {"id": "supervisors", "label": "Supervisors or approvers"},
                {"id": "managers", "label": "Managers or report viewers"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "selection_mode": "multiple",
        },
    },
    ("users_roles", "responsibilities"): {
        "terms": (
            "responsible",
            "responsibilities",
            "should each staff",
            "register",
            "record",
            "prepare",
            "review",
            "approve",
        ),
        "fallback": {
            "text": "What should each staff group be responsible for?",
            "why_this_matters": "This separates the daily duties of each user group.",
            "choices": [
                {"id": "capture_records", "label": "Capture or update records"},
                {"id": "review_approve", "label": "Review or approve work"},
                {"id": "prepare_fulfil", "label": "Prepare or fulfil the next step"},
                {"id": "view_reports", "label": "View summaries or reports"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "selection_mode": "multiple",
        },
    },
    ("workflow_steps", "normal_flow"): {
        "terms": ("normal flow", "main steps", "step by step", "sequence", "start to finish"),
        "fallback": {
            "text": "Which normal flow best matches the work from start to finish?",
            "why_this_matters": "The SAD needs the main sequence before handling edge cases.",
            "choices": [
                {"id": "request_approve_fulfil", "label": "Request, approve, then fulfil"},
                {"id": "register_process_close", "label": "Register, process, then close"},
                {"id": "create_review_export", "label": "Create, review, then report or export"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "selection_mode": "single",
        },
    },
    ("workflow_steps", "handoffs"): {
        "terms": ("handoff", "status change", "moves between", "next step", "after the first step"),
        "fallback": {
            "text": "When the work moves to the next step, what should happen?",
            "why_this_matters": "This clarifies handoffs and status changes between roles.",
            "choices": [
                {"id": "handoff_next_role", "label": "Hand it to the next responsible role"},
                {"id": "update_status", "label": "Update the status but keep the same owner"},
                {"id": "notify_next_role", "label": "Notify the next role before they act"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "selection_mode": "single",
        },
    },
    ("data_records", "main_records"): {
        "terms": ("records", "data", "information", "what should be stored", "which records"),
        "fallback": {
            "text": "Which main records must the system keep?",
            "why_this_matters": "This defines the core data the product must store.",
            "choices": [
                {"id": "request_records", "label": "Request or case records"},
                {"id": "person_records", "label": "Customer, patient, or staff records"},
                {"id": "transaction_records", "label": "Transaction or payment records"},
                {"id": "status_history", "label": "Status and history records"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "selection_mode": "multiple",
        },
    },
    ("data_records", "critical_fields"): {
        "terms": ("fields", "details", "attributes", "timestamps", "which details"),
        "fallback": {
            "text": "Which details are essential on each record?",
            "why_this_matters": "This clarifies the fields IT must capture from day one.",
            "choices": [
                {"id": "identifiers", "label": "Names or identifiers"},
                {"id": "dates_status", "label": "Dates and statuses"},
                {"id": "owners", "label": "Responsible staff or owner"},
                {"id": "amounts_notes", "label": "Amounts, notes, or reasons"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "selection_mode": "multiple",
        },
    },
    ("rules_approvals", "triggering_rules"): {
        "terms": ("rule", "must", "cannot", "before", "trigger"),
        "fallback": {
            "text": "Which business rule should be confirmed first?",
            "why_this_matters": "Clear rules prevent the workflow from closing in the wrong state.",
            "choices": [
                {"id": "must_complete", "label": "A record cannot be completed until key steps are done"},
                {"id": "must_review", "label": "A review is required before completion"},
                {"id": "must_alert", "label": "Staff should be alerted when a rule is broken"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "selection_mode": "single",
        },
    },
    ("rules_approvals", "approval_path"): {
        "terms": ("approval path", "move through approval", "who approves", "approval levels", "depends on amount"),
        "fallback": {
            "text": "How should a request move through approval?",
            "why_this_matters": "This clarifies the approval path and decision route.",
            "choices": [
                {"id": "single_manager", "label": "One manager approves it"},
                {"id": "multi_level", "label": "It goes through multiple approval levels"},
                {"id": "by_amount", "label": "The path depends on amount or request type"},
                {"id": "no_formal", "label": "There is no formal approval path"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "selection_mode": "single",
        },
    },
    ("rules_approvals", "decision_authority"): {
        "terms": ("expensive", "threshold", "amount", "manager approval", "approval before use", "authority"),
        "fallback": {
            "text": "What value or rule makes a part expensive enough to require manager approval?",
            "why_this_matters": "This turns the approval rule into a buildable condition for the workshop workflow.",
            "choices": [
                {"id": "fixed_amount", "label": "A fixed cost threshold, such as parts above a set amount"},
                {"id": "part_type", "label": "Certain part types always require manager approval"},
                {"id": "supervisor_flags", "label": "Supervisor flags expensive or unusual parts for approval"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "selection_mode": "single",
        },
    },
    ("exceptions_edges", "common_exception"): {
        "terms": ("exception", "edge case", "what can go wrong", "leave without", "skip"),
        "fallback": {
            "text": "Which exception should be handled first?",
            "why_this_matters": "This identifies the most important edge case to design for.",
            "choices": [
                {"id": "skipped_step", "label": "A required step is skipped"},
                {"id": "incomplete_exit", "label": "Someone leaves before the process is complete"},
                {"id": "rejected_record", "label": "A record is rejected or corrected"},
                {"id": "duplicate_record", "label": "A duplicate or wrong record is entered"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "selection_mode": "single",
        },
    },
    ("exceptions_edges", "required_handling"): {
        "terms": ("handle", "what should staff do", "when that happens", "mark incomplete", "alert", "follow-up"),
        "fallback": {
            "text": "When that exception happens, what should staff do next?",
            "why_this_matters": "This turns the exception into a buildable system action.",
            "choices": [
                {"id": "keep_open", "label": "Mark it incomplete and keep it open"},
                {"id": "alert_staff", "label": "Alert the responsible staff immediately"},
                {"id": "manual_follow_up", "label": "Allow manual follow-up later"},
                {"id": "close_flag_review", "label": "Close it but flag it for review"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "selection_mode": "single",
        },
    },
    ("reports_summaries", "needed_outputs"): {
        "terms": ("report", "summary", "dashboard", "output", "export"),
        "fallback": {
            "text": "Which output should the first version produce?",
            "why_this_matters": "This clarifies what the system must show after capturing data.",
            "choices": [
                {"id": "daily_summary", "label": "Daily summary"},
                {"id": "dashboard", "label": "Dashboard"},
                {"id": "exception_list", "label": "Exception or follow-up list"},
                {"id": "export", "label": "Weekly export"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "selection_mode": "multiple",
        },
    },
    ("reports_summaries", "audience"): {
        "terms": ("who needs", "audience", "review the output", "manager", "supervisor"),
        "fallback": {
            "text": "Who needs to review those outputs most often?",
            "why_this_matters": "This sets the audience for reports and summaries.",
            "choices": [
                {"id": "managers", "label": "Managers"},
                {"id": "supervisors", "label": "Supervisors"},
                {"id": "frontline", "label": "Frontline staff"},
                {"id": "finance_ops", "label": "Finance or operations staff"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "selection_mode": "multiple",
        },
    },
    ("access_permissions", "access_model"): {
        "terms": ("access model", "permissions", "who can access", "role-based"),
        "fallback": {
            "text": "How should access normally be organised?",
            "why_this_matters": "This defines the default permission model.",
            "choices": [
                {"id": "role_based", "label": "Role-based access"},
                {"id": "same_access", "label": "The same access for everyone"},
                {"id": "project_based", "label": "Access depends on project or site"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "selection_mode": "single",
        },
    },
    ("access_permissions", "sensitive_actions"): {
        "terms": ("sensitive", "restricted", "delete", "overwrite", "export", "share"),
        "fallback": {
            "text": "Which actions need tighter permission control?",
            "why_this_matters": "This identifies the risky actions that need protection.",
            "choices": [
                {"id": "approve", "label": "Approve or reject work"},
                {"id": "delete", "label": "Delete or overwrite records"},
                {"id": "export_share", "label": "Export or share information"},
                {"id": "admin_change", "label": "Change system settings"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "selection_mode": "multiple",
        },
    },
    ("integrations", "external_systems"): {
        "terms": ("integrate", "external system", "connect", "other system"),
        "fallback": {
            "text": "Which external systems must this connect with, if any?",
            "why_this_matters": "This decides whether the MVP must exchange data with other tools.",
            "choices": [
                {"id": "none", "label": "No external systems in the first version"},
                {"id": "accounting", "label": "Accounting or finance system"},
                {"id": "inventory", "label": "Inventory or ERP system"},
                {"id": "crm", "label": "CRM or customer system"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "selection_mode": "multiple",
        },
    },
    ("non_functional", "security_privacy"): {
        "terms": ("security", "privacy", "confidential", "sensitive data"),
        "fallback": {
            "text": "Which security or privacy need matters most?",
            "why_this_matters": "This captures the first non-functional control IT must preserve.",
            "choices": [
                {"id": "login", "label": "Secure login"},
                {"id": "restricted_data", "label": "Restrict sensitive data by role"},
                {"id": "confidentiality", "label": "Keep personal or confidential data protected"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "selection_mode": "multiple",
        },
    },
    ("non_functional", "audit_history"): {
        "terms": ("audit", "history", "log", "trace"),
        "fallback": {
            "text": "What history must the system keep?",
            "why_this_matters": "This clarifies the audit trail needed for later review.",
            "choices": [
                {"id": "edits", "label": "Edits and corrections"},
                {"id": "approvals", "label": "Approvals and decisions"},
                {"id": "status_changes", "label": "Status changes"},
                {"id": "exports", "label": "Exports or downloads"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "selection_mode": "multiple",
        },
    },
}


def fallback_question_for_slot(
    category_id: str,
    slot_id: str,
    *,
    context_text: str = "",
) -> dict[str, Any]:
    contextual = _contextual_fallback_question(category_id, slot_id, context_text)
    if contextual is not None:
        return contextual
    contract = SLOT_CONTRACTS.get((category_id, slot_id))
    if contract is None:
        raise KeyError((category_id, slot_id))
    payload = dict(contract["fallback"])
    payload["target_category"] = category_id
    payload["target_slot_id"] = slot_id
    return payload


def semantic_score_for_slot(category_id: str, slot_id: str, text: str) -> int:
    contract = SLOT_CONTRACTS.get((category_id, slot_id))
    if contract is None:
        return 0
    lowered = text.lower()
    return sum(1 for term in contract["terms"] if term in lowered)


def best_matching_slot(text: str) -> tuple[tuple[str, str] | None, int]:
    best_slot: tuple[str, str] | None = None
    best_score = 0
    for slot_key in SLOT_CONTRACTS:
        score = semantic_score_for_slot(slot_key[0], slot_key[1], text)
        if score > best_score:
            best_slot = slot_key
            best_score = score
    return best_slot, best_score


def _contextual_fallback_question(
    category_id: str,
    slot_id: str,
    context_text: str,
) -> dict[str, Any] | None:
    lowered = context_text.lower()
    is_tuition = any(
        term in lowered
        for term in ("tuition", "student", "class", "teacher", "parent", "fee", "attendance")
    )
    is_service_order = any(
        term in lowered
        for term in (
            "customer",
            "order",
            "orders",
            "booking",
            "bookings",
            "rental",
            "delivery",
            "pickup",
            "return status",
            "payment status",
            "ready-for-pickup",
        )
    )
    if is_service_order and (category_id, slot_id) == ("exceptions_edges", "required_handling"):
        return {
            "text": "What should happen when a customer order is delayed, damaged, missing items, or not collected?",
            "why_this_matters": "This turns the uploaded order exceptions into clear follow-up rules.",
            "choices": [
                {"id": "delay_notice", "label": "Notify the customer when an order is delayed"},
                {"id": "damage_review", "label": "Flag damaged or missing-item orders for owner review"},
                {"id": "not_collected_followup", "label": "Keep not-collected pickup orders open for follow-up"},
                {"id": "complaint_record", "label": "Record a complaint reason before closing the order"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": category_id,
            "target_slot_id": slot_id,
            "selection_mode": "multiple",
        }
    if is_service_order and (category_id, slot_id) == ("access_permissions", "override_handling"):
        return {
            "text": "Who can override payment or pickup status when a customer order needs correction?",
            "why_this_matters": "This protects payment and pickup changes from accidental or unauthorised edits.",
            "choices": [
                {"id": "owner_only", "label": "Only the owner can override payment or pickup status"},
                {"id": "counter_with_reason", "label": "Counter staff can correct payment status with a reason"},
                {"id": "fulfilment_status_reason", "label": "Fulfilment staff can correct work, delivery, or return status with a reason"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": category_id,
            "target_slot_id": slot_id,
            "selection_mode": "single",
        }
    if is_service_order and (category_id, slot_id) == ("non_functional", "audit_history"):
        return {
            "text": "Which customer order changes should keep history?",
            "why_this_matters": "This creates traceability for order, payment, and customer-notification changes.",
            "choices": [
                {"id": "status_history", "label": "Keep history for preparation, delivery, pickup, return, and completion status"},
                {"id": "payment_history", "label": "Keep history for payment status changes"},
                {"id": "customer_notice_history", "label": "Keep history for customer ready, changed, overdue, or delayed notifications"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": category_id,
            "target_slot_id": slot_id,
            "selection_mode": "multiple",
        }
    if is_service_order and (category_id, slot_id) == ("rules_approvals", "approval_path"):
        return {
            "text": "Is any owner approval needed before closing unusual customer orders?",
            "why_this_matters": "This avoids inventing approvals while still checking damaged, missing, or complaint cases.",
            "choices": [
                {"id": "no_formal", "label": "No formal approval is needed for normal orders"},
                {"id": "owner_damage", "label": "Owner approval is needed for damaged or missing-item orders"},
                {"id": "owner_refund", "label": "Owner approval is needed for refunds or complaints"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": category_id,
            "target_slot_id": slot_id,
            "selection_mode": "single",
        }
    if is_tuition and (category_id, slot_id) == ("rules_approvals", "triggering_rules"):
        return {
            "text": "Which parent, fee, attendance, or class rule should automatically trigger follow-up?",
            "why_this_matters": "This turns attendance, fee, and class-capacity needs into clear system rules.",
            "choices": [
                {"id": "absence_notice", "label": "A parent update is triggered when a student is absent"},
                {"id": "fee_overdue", "label": "An unpaid fee becomes a follow-up item after the due date"},
                {"id": "class_full", "label": "A class is full when enrolment reaches the class capacity"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": category_id,
            "target_slot_id": slot_id,
            "selection_mode": "multiple",
        }
    if is_tuition and (category_id, slot_id) == ("exceptions_edges", "required_handling"):
        return {
            "text": "When should parents be notified about absence or unpaid fees?",
            "why_this_matters": "This turns parent updates into clear system rules.",
            "choices": [
                {"id": "same_day_absence", "label": "Notify parents on the same day when a student is absent"},
                {"id": "after_fee_due", "label": "Notify parents when a fee remains unpaid after the due date"},
                {"id": "manager_review", "label": "Manager reviews attendance or fee issues before notification"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": category_id,
            "target_slot_id": slot_id,
            "selection_mode": "multiple",
        }
    if is_tuition and (category_id, slot_id) == ("access_permissions", "sensitive_actions"):
        return {
            "text": "Which tuition records need restricted edit access?",
            "why_this_matters": "This protects sensitive student, attendance, and payment data.",
            "choices": [
                {"id": "payment_edits", "label": "Only admin or manager can edit fee payment records"},
                {"id": "attendance_corrections", "label": "Teachers can correct attendance only with a reason"},
                {"id": "parent_contacts", "label": "Parent contact details are editable only by admin staff"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": category_id,
            "target_slot_id": slot_id,
            "selection_mode": "multiple",
        }
    if is_tuition and (category_id, slot_id) == ("non_functional", "audit_history"):
        return {
            "text": "Which tuition changes should keep an audit history?",
            "why_this_matters": "This helps the centre review sensitive changes later.",
            "choices": [
                {"id": "attendance_history", "label": "Attendance corrections keep user, reason, and timestamp"},
                {"id": "payment_history", "label": "Fee payment edits keep user, amount, and timestamp"},
                {"id": "student_profile_history", "label": "Student or parent contact changes keep user and timestamp"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": category_id,
            "target_slot_id": slot_id,
            "selection_mode": "multiple",
        }
    is_workshop = "workshop" in lowered or "maintenance request" in lowered
    if not is_workshop:
        return None
    if (category_id, slot_id) == ("rules_approvals", "decision_authority"):
        return {
            "text": "What value or rule makes a part expensive enough to require manager approval?",
            "why_this_matters": "This turns the approval rule into a buildable condition for the workshop workflow.",
            "choices": [
                {"id": "fixed_amount", "label": "A fixed cost threshold, such as parts above a set amount"},
                {"id": "part_type", "label": "Certain part types always require manager approval"},
                {"id": "supervisor_flags", "label": "Supervisor flags expensive or unusual parts for approval"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": category_id,
            "target_slot_id": slot_id,
            "selection_mode": "single",
        }
    return None
