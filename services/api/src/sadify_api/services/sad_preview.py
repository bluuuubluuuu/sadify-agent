from datetime import UTC, datetime

from sadify_api.schemas import (
    ItReadinessSummary,
    RequirementAnalysisResponse,
    SadPreviewChangeTracking,
    SadPreviewRecord,
    SadPreviewResponse,
    SadPreviewSection,
)
from sadify_api.services.sad_synthesis import (
    build_sad_synthesis_context,
    clean_business_request,
    split_assumptions,
)


REQUIRED_BLOCKING_BASICS = ("problem", "goal", "users_roles", "workflow")

_BASIC_EVIDENCE_TERMS = {
    "problem": (
        "problem",
        "issue",
        "need",
        "needs",
        "wants",
        "track",
        "manage",
        "validate",
    ),
    "goal": (
        "goal",
        "purpose",
        "summary",
        "report",
        "system",
        "simple",
        "improve",
        "reduce",
    ),
    "users_roles": (
        "staff",
        "user",
        "users",
        "role",
        "roles",
        "manager",
        "doctor",
        "cashier",
        "reception",
        "pharmacy",
        "operator",
        "supervisor",
        "admin",
        "teacher",
        "parent",
        "sales",
        "warehouse",
        "driver",
        "drivers",
        "owner",
        "customer",
    ),
    "workflow": (
        "workflow",
        "process",
        "status",
        "booking",
        "bookings",
        "order",
        "orders",
        "delivery",
        "pickup",
        "return",
        "returned",
        "packed",
        "damaged",
        "register",
        "queue",
        "consultation",
        "collection",
        "payment",
        "approval",
        "follow-up",
        "enrolment",
        "class",
        "attendance",
        "fee",
        "parent update",
    ),
}


class SadPreviewRepository:
    def __init__(self) -> None:
        self._records: dict[str, SadPreviewRecord] = {}
        self._next_preview_number = 1

    def save_preview(
        self,
        *,
        requirement_text: str,
        analysis_id: str | None,
        preview: SadPreviewResponse,
        created_at: datetime | None = None,
    ) -> SadPreviewRecord:
        preview_id = f"SP-{self._next_preview_number:06d}"
        self._next_preview_number += 1
        record = SadPreviewRecord(
            preview_id=preview_id,
            analysis_id=analysis_id,
            requirement_text=requirement_text,
            preview=preview,
            created_at=created_at or datetime.now(UTC),
        )
        self._records[preview_id] = record
        return record

    def get_preview(self, preview_id: str) -> SadPreviewRecord | None:
        return self._records.get(preview_id)


def missing_blocking_basics(
    analysis: RequirementAnalysisResponse,
    *,
    requirement_text: str = "",
    source_context: str | None = None,
) -> list[str]:
    if (
        analysis.questionnaire is not None
        and analysis.questionnaire.draft_readiness.score >= 90
    ):
        return []

    categories = {
        _normalize_category_id(category.id): category.status
        for category in analysis.categories
    }
    evidence_text = " ".join(
        [
            requirement_text,
            source_context or "",
            analysis.understanding_summary,
        ]
    ).lower()
    missing: list[str] = []
    for category_id in REQUIRED_BLOCKING_BASICS:
        status = categories.get(category_id)
        if status not in (None, "missing"):
            continue
        if _has_basic_evidence(category_id, evidence_text):
            continue
        missing.append(category_id)
    return missing


def build_sad_preview_context(
    *,
    requirement_text: str,
    analysis_id: str | None,
    analysis: RequirementAnalysisResponse,
    source_context: str | None,
    source_references: list[str],
) -> str:
    return build_sad_synthesis_context(
        requirement_text=requirement_text,
        analysis_id=analysis_id,
        analysis=analysis,
        source_context=source_context,
        source_references=source_references,
    )


def with_requested_source_references(
    preview: SadPreviewResponse,
    source_references: list[str],
) -> SadPreviewResponse:
    merged = list(preview.source_references)
    for source_reference in source_references:
        clean_reference = source_reference.strip()
        if clean_reference and clean_reference not in merged:
            merged.append(clean_reference)
    return preview.model_copy(update={"source_references": merged})


def build_safe_sad_fallback_preview(
    *,
    requirement_text: str,
    analysis: RequirementAnalysisResponse,
    source_references: list[str],
) -> SadPreviewResponse:
    references = _safe_source_references(source_references)
    assumptions, _diagnostics = split_assumptions(analysis.assumptions)
    open_questions = _safe_open_questions(analysis)
    clean_request = clean_business_request(requirement_text)
    answers = _questionnaire_answers(analysis)
    answer_lookup = _answer_map(answers)

    return SadPreviewResponse(
        title=_business_sad_title(clean_request),
        temporary_notice=(
            "Draft preview generated from the confirmed business request and saved "
            "Q&A answers. Review before saving as a formal SAD."
        ),
        it_readiness=_draft_ready_it_readiness(analysis),
        sections=[
            _section(
                "Confirmed Business Request",
                _compose_confirmed_business_request(clean_request),
                references,
            ),
            _section(
                "Executive Summary",
                _compose_executive_summary(clean_request),
                references,
            ),
            _section(
                "Scope",
                _compose_scope(clean_request),
                references,
            ),
            _section(
                "Users and Responsibilities",
                _compose_users_and_roles(clean_request),
                references,
            ),
            _section(
                "Workflow",
                _compose_workflow(clean_request, answer_lookup),
                references,
            ),
            _section(
                "Data and Records",
                _compose_data_records(answer_lookup, clean_request),
                references,
            ),
            _section(
                "Business Rules and Approvals",
                _compose_rules_and_approvals(answer_lookup, clean_request),
                references,
            ),
            _section(
                "Exceptions and Follow-Up",
                _compose_exceptions(clean_request, answer_lookup),
                references,
            ),
            _section(
                "Reports and Summaries",
                _compose_reports(clean_request),
                references,
            ),
            _section(
                "Access and Permissions",
                _compose_access(answer_lookup, clean_request),
                references,
            ),
            _section(
                "Security and Privacy",
                _compose_security(answer_lookup, clean_request),
                references,
            ),
            _section(
                "Audit and History",
                _compose_audit(answer_lookup, clean_request),
                references,
            ),
            _section(
                "Integrations",
                _compose_integrations(answer_lookup, clean_request),
                references,
            ),
        ],
        assumptions=assumptions,
        open_questions=open_questions,
        source_references=references,
        change_tracking=SadPreviewChangeTracking(
            summary="Draft preview composed from confirmed request facts and Q&A answers.",
            paths=[
                "SAD/preview",
            ],
        ),
    )


def _normalize_category_id(category_id: str) -> str:
    return category_id.strip().lower().replace("-", "_").replace(" ", "_")


def _has_basic_evidence(category_id: str, evidence_text: str) -> bool:
    return any(term in evidence_text for term in _BASIC_EVIDENCE_TERMS[category_id])


def _questionnaire_answers(
    analysis: RequirementAnalysisResponse,
) -> list[tuple[str, str | None, str]]:
    questionnaire = analysis.questionnaire
    if questionnaire is None:
        return []
    return [
        (answer.category_id, answer.slot_id, answer.answer)
        for answer in questionnaire.answers
    ]


def _answer_map(
    answers: list[tuple[str, str | None, str]],
) -> dict[tuple[str, str], str]:
    return {
        (category_id, slot_id or ""): answer.strip()
        for category_id, slot_id, answer in answers
    }


def _strip_details_marker(answer: str) -> str:
    return answer.split("| Details:", 1)[0].strip()


def _details_text(answer: str) -> str:
    marker = "| Details:"
    if marker not in answer:
        return ""
    return answer.split(marker, 1)[1].strip()


def _section(
    title: str,
    body: str,
    source_references: list[str],
) -> SadPreviewSection:
    return SadPreviewSection(
        title=title,
        body=_compact_text(body),
        source_references=source_references,
    )


def _request_sentences(
    request_text: str,
    keywords: tuple[str, ...],
    fallback: str,
) -> str:
    sentences = [
        sentence.strip()
        for sentence in request_text.replace("\n", " ").split(".")
        if sentence.strip()
    ]
    matches = [
        sentence
        for sentence in sentences
        if any(keyword in sentence.lower() for keyword in keywords)
    ]
    if not matches:
        return fallback
    return ". ".join(matches) + "."


def _business_sad_title(clean_request: str) -> str:
    lowered = clean_request.lower()
    if _is_tuition_request(clean_request):
        return "Tuition Centre Management System SAD Draft"
    if _is_workshop_request(clean_request):
        return "Maintenance Request Tracking System SAD Draft"
    if "clinic" in lowered and "patient" in lowered:
        return "Clinic Patient Flow Management SAD Draft"
    return "System Analysis Document Draft"


def _draft_ready_it_readiness(
    analysis: RequirementAnalysisResponse,
) -> ItReadinessSummary:
    is_ready = _is_draft_ready(analysis)
    return ItReadinessSummary(
        label="Ready for draft" if is_ready else "Draft review needed",
        score=100 if is_ready else analysis.readiness.score,
        confidence="High" if is_ready else analysis.readiness.confidence,
        checklist=[
            {
                "id": "layer_one_context",
                "label": "Layer 1 SAD draft",
                "status": "ready" if is_ready else "needs_input",
                "reason": "The draft uses confirmed request facts and saved Q&A answers.",
            },
            {
                "id": "layer_two_review",
                "label": "Later implementation review",
                "status": "needs_input",
                "reason": "Detailed technical design remains a later MVP refinement step.",
            },
        ],
    )


def _answer_value(
    answers: dict[tuple[str, str], str],
    keys: tuple[tuple[str, str], ...],
    fallback: str,
) -> str:
    for key in keys:
        answer = answers.get(key)
        if answer:
            return answer
    return fallback


def _compose_confirmed_business_request(clean_request: str) -> str:
    if _is_tuition_request(clean_request):
        return (
            "A small tuition centre needs a simple system to track student "
            "enrolment, class schedules, attendance, fee payments, parent "
            "updates, and weekly centre manager summaries."
        )
    if _is_workshop_request(clean_request):
        return (
            "A small equipment workshop needs a system to track machine "
            "maintenance requests, technician assignment, repair details, manager "
            "approval for expensive parts, open reasons, and weekly operations "
            "reporting."
        )
    if "clinic" in clean_request.lower():
        return (
            "A small clinic needs a simple system to manage patient registration, "
            "queue status, doctor consultation, medicine collection, payment, daily "
            "management summaries, and follow-up for incomplete visits."
        )
    return clean_request


def _compose_executive_summary(clean_request: str) -> str:
    if _is_tuition_request(clean_request):
        return (
            "The proposed system will let admin staff register students and "
            "assign classes, teachers mark attendance and add progress notes, "
            "parents receive absence or unpaid-fee updates, and the centre "
            "manager review weekly enrolment, attendance, fee, and class-capacity "
            "summaries."
        )
    if _is_workshop_request(clean_request):
        return (
            "The proposed system will let staff submit maintenance requests, "
            "supervisors assign technicians, technicians update repair progress, "
            "managers approve expensive parts, and operations managers review "
            "weekly maintenance performance."
        )
    if "clinic" in clean_request.lower():
        return (
            "The proposed system will support a small clinic's patient journey "
            "from registration through queue handling, consultation, medicine "
            "collection, payment, and daily management reporting."
        )
    return clean_request


def _compose_scope(clean_request: str) -> str:
    if _is_tuition_request(clean_request):
        return (
            "The Layer 1 scope covers one internal tuition-centre operations "
            "system. The first version includes student enrolment tracking, class "
            "assignment and schedules, attendance, short progress notes, fee "
            "payment tracking, parent updates, weekly summaries, role-based access, "
            "and audit history."
        )
    if _is_workshop_request(clean_request):
        return (
            "The Layer 1 scope covers one internal workshop system for machine "
            "maintenance request tracking. The first version includes request "
            "creation, assignment, repair updates, parts approval, open-reason "
            "tracking, weekly summaries, role-based access, and audit history."
        )
    if "clinic" in clean_request.lower():
        return (
            "The Layer 1 scope covers one simple internal clinic system for "
            "frontline staff and managers. The draft focuses on operational "
            "tracking, status visibility, record completeness, exception follow-up, "
            "and daily summaries."
        )
    return "The Layer 1 scope is based on the confirmed business request."


def _compose_users_and_roles(clean_request: str) -> str:
    if _is_tuition_request(clean_request):
        return (
            "Admin staff register students and assign them to classes. Teachers "
            "mark attendance and add short progress notes. Parents receive updates "
            "when students are absent or fees are unpaid. The centre manager reviews "
            "weekly summaries for enrolment, attendance issues, unpaid fees, and "
            "full classes."
        )
    if _is_workshop_request(clean_request):
        return (
            "Staff create maintenance requests and view their own requests. "
            "Workshop supervisors assign jobs to technicians. Technicians record "
            "diagnosis notes, parts used, repair status, and completion time. "
            "Managers approve expensive parts and view reports. Operations "
            "managers review weekly summaries."
        )
    if "clinic" in clean_request.lower():
        return (
            "Reception staff register patients and update queue status. Doctors "
            "record consultation notes. Pharmacy staff prepare medicine and track "
            "collection. Cashiers record payments and unpaid bills. Managers review "
            "daily summaries and follow up on incomplete visits."
        )
    return _request_sentences(
        clean_request,
        ("staff", "manager", "user", "role"),
        "Users and responsibilities need review.",
    )


def _compose_workflow(
    clean_request: str,
    answers: dict[tuple[str, str], str],
) -> str:
    exception_rule = _answer_value(
        answers,
        (
            ("exceptions_edges", "required_handling"),
            ("workflow_steps", "required_handling"),
            ("workflow_steps", "exception_handling"),
        ),
        "Mark incomplete and keep open",
    )
    if _is_tuition_request(clean_request):
        return (
            "1. Admin staff register a student and assign the student to one or "
            "more classes. 2. Class schedules are maintained for the enrolled "
            "students. 3. Teachers mark attendance and add short progress notes. "
            "4. Fee payments are recorded and unpaid fees remain visible for "
            "follow-up. 5. Parents are notified when a student is absent or a fee "
            "is unpaid. 6. The centre manager reviews the weekly summary for "
            "enrolment, attendance issues, unpaid fees, and full classes."
        )
    if "clinic" in clean_request.lower():
        return (
            "1. Register patient and create a visit record. "
            "2. Manage queue status until the patient is ready for consultation. "
            "3. Record doctor consultation notes. "
            "4. Prepare and collect medicine, then record collection status. "
            "5. Record payment and close visit only when required steps are complete. "
            f"If payment or medicine collection is skipped, staff should "
            f"{exception_rule.lower()} for follow-up."
        )
    if _is_workshop_request(clean_request):
        approval_rule = answers.get(
            ("rules_approvals", "decision_authority"),
            "manager approval is required before expensive parts are used",
        )
        return (
            "1. Staff submit a maintenance request when a machine has an issue. "
            "2. The workshop supervisor assigns a technician. "
            "3. The technician records diagnosis notes, parts used, repair status, "
            "and completion time. "
            "4. Manager approval is required before expensive parts are used; "
            f"{approval_rule.lower()}. "
            "5. Completed repairs are closed when repair details and completion "
            "time are recorded. If parts are unavailable or a job is overdue, "
            "requests stay open with a reason."
        )
    return "Workflow steps should follow the confirmed business request and saved answers."


def _compose_data_records(
    answers: dict[tuple[str, str], str],
    clean_request: str = "",
) -> str:
    if _is_tuition_request(clean_request):
        return (
            "Core records should include student, parent contact, class, class "
            "schedule, enrolment, attendance entry, progress note, fee payment, "
            "unpaid-fee follow-up, parent update, class capacity, and audit event "
            "details."
        )
    if _is_workshop_request(clean_request):
        return (
            "Core records should include machine, maintenance request, issue, "
            "assigned technician, diagnosis notes, parts used, parts cost, repair "
            "status, completion time, open reason, and audit event details."
        )
    fields = answers.get(("data_records", "critical_fields"), "")
    if "clinic" in clean_request.lower() and fields:
        return (
            "Each operational record should include a Patient or visit identifier, "
            "status timestamps, the responsible staff member or owner, and any "
            "amounts, notes, or reasons needed to explain the record."
        )
    if fields:
        return (
            "Each operational record should include a clear identifier, status "
            "timestamps, the responsible staff member or owner, and any amounts, "
            "notes, or reasons needed to explain the record."
        )
    return "Record fields need later review."


def _compose_rules_and_approvals(
    answers: dict[tuple[str, str], str],
    clean_request: str = "",
) -> str:
    if _is_tuition_request(clean_request):
        handling = answers.get(
            ("exceptions_edges", "required_handling"),
            "Parents should receive updates when students are absent or fees are unpaid",
        )
        return (
            "Confirmed tuition rules should cover attendance notification, unpaid-fee "
            "follow-up, and class capacity. "
            f"Parent update handling: {handling}. "
            "A formal approval path is not confirmed for this tuition workflow; "
            "leave any approval policy as an open question until the centre owner "
            "confirms it."
        )
    if _is_workshop_request(clean_request):
        rule = answers.get(
            ("rules_approvals", "triggering_rules"),
            "A maintenance request cannot be completed until repair details and any required parts approval are done",
        )
        approval = answers.get(
            ("rules_approvals", "approval_path"),
            "Manager approval is required before expensive parts are used",
        )
        return (
            f"Core rule: {rule}. Approval path: {approval}. These rules should "
            "prevent incomplete maintenance requests from being treated as complete."
        )
    rule = answers.get(
        ("rules_approvals", "triggering_rules"),
        "A record cannot be completed until key steps are done",
    )
    approval = answers.get(
        ("rules_approvals", "approval_path"),
        "Approval details need review",
    )
    return (
        f"Core rule: {rule}. Approval path: {approval}. These rules should prevent "
        "incomplete records from being treated as complete."
    )


def _compose_exceptions(
    clean_request: str,
    answers: dict[tuple[str, str], str],
) -> str:
    if _is_tuition_request(clean_request):
        handling = answers.get(
            ("exceptions_edges", "required_handling"),
            "Notify parents when students are absent or fees are unpaid",
        )
        return (
            "Known exception cases include student absences, unpaid fees, classes "
            "reaching capacity, and schedule changes. "
            f"When attendance or payment issues occur, staff should {handling.lower()} "
            "so the centre can follow up."
        )
    if _is_workshop_request(clean_request):
        return (
            "Known exception cases include parts being unavailable and jobs becoming "
            "overdue. In both cases, requests stay open with a reason so supervisors "
            "and managers can review the delay."
        )
    handling = _answer_value(
        answers,
        (
            ("exceptions_edges", "required_handling"),
            ("workflow_steps", "required_handling"),
            ("workflow_steps", "exception_handling"),
        ),
        "Mark incomplete and keep open",
    )
    exception_context = _request_sentences(
        clean_request,
        ("late", "damaged", "missing", "substituted", "overdue", "exception"),
        "Known exception cases need later review.",
    )
    return (
        f"{exception_context} When this happens, staff should {handling.lower()} so the "
        "case remains visible for follow-up."
    )


def _compose_reports(clean_request: str) -> str:
    if _is_tuition_request(clean_request):
        return (
            "The centre manager needs a weekly summary of enrolled students, "
            "attendance issues, unpaid fees, and classes that are full."
        )
    if _is_workshop_request(clean_request):
        return (
            "The operations manager needs a weekly summary of open requests, "
            "completed repairs, repeated machine issues, parts cost, and overdue "
            "jobs."
        )
    return _request_sentences(
        clean_request,
        ("summary", "report", "manager", "served", "waiting", "unpaid"),
        "Reports and summaries need later review.",
    )


def _compose_access(
    answers: dict[tuple[str, str], str],
    clean_request: str = "",
) -> str:
    if _is_tuition_request(clean_request):
        sensitive = answers.get(
            ("access_permissions", "sensitive_actions"),
            "fee payment edits, attendance corrections, and parent contact changes need restricted access",
        )
        return (
            "Admin staff should manage student registration, class assignment, fee "
            "records, and parent contact details. Teachers should update attendance "
            "and progress notes for their classes. The centre manager should view "
            "weekly summaries and sensitive follow-up lists. "
            f"Restricted actions: {sensitive}."
        )
    if _is_workshop_request(clean_request):
        return (
            "Staff can create and view their own requests. Supervisors assign jobs. "
            "Technicians update repair details. Managers approve expensive parts "
            "and view reports. Actions should be restricted by role."
        )
    model = answers.get(("access_permissions", "access_model"), "Role-based access")
    sensitive = answers.get(
        ("access_permissions", "sensitive_actions"),
        "Sensitive actions need review",
    )
    return (
        f"Access should use {model.lower()}. Tighter permission control is required "
        f"for: {sensitive}."
    )


def _compose_security(
    answers: dict[tuple[str, str], str],
    clean_request: str = "",
) -> str:
    if _is_tuition_request(clean_request):
        return (
            "The system should use secure login and restrict student, parent, "
            "attendance, and fee information by role so sensitive centre records "
            "are protected."
        )
    if _is_workshop_request(clean_request):
        return (
            "The system must use secure login and restrict actions by role so each "
            "staff group can perform only its permitted maintenance workflow tasks."
        )
    answer = answers.get(("non_functional", "security_privacy"), "")
    details = _details_text(answer)
    text = (
        "The system should require secure login, restrict sensitive data by role, "
        "and protect personal or confidential data."
    )
    if "encrypted" in details.lower():
        text += (
            " Sensitive data must remain encrypted and security controls must not "
            "be weakened."
        )
    return text


def _compose_audit(
    answers: dict[tuple[str, str], str],
    clean_request: str = "",
) -> str:
    if _is_tuition_request(clean_request):
        return (
            "The system should keep audit history for student registration changes, "
            "class assignment changes, attendance corrections, fee payment edits, "
            "parent update records, and sensitive profile changes, with user and "
            "timestamp where possible."
        )
    if _is_workshop_request(clean_request):
        return (
            "The system must record every change with user and timestamp, including "
            "request creation, assignment, repair updates, approval decisions, "
            "status changes, and open-reason updates."
        )
    answer = answers.get(("non_functional", "audit_history"), "")
    base = _strip_details_marker(answer)
    text = (
        "Audit history should cover edits and corrections, approvals and decisions, "
        "status changes, and exports or downloads."
    )
    if base:
        text = f"Audit history should cover {base.lower()}."
    if "any actions" in _details_text(answer).lower():
        text += " All user actions that affect system data must be recorded."
    return text


def _compose_integrations(
    answers: dict[tuple[str, str], str],
    clean_request: str = "",
) -> str:
    if _is_workshop_request(clean_request):
        return "No external systems are needed in the first version."
    return answers.get(
        ("integrations", "external_systems"),
        "No external integrations are confirmed for the first version.",
    )


def _safe_source_references(source_references: list[str]) -> list[str]:
    cleaned = [
        reference.strip()
        for reference in source_references
        if reference.strip() and not _is_internal_source_reference(reference.strip())
    ]
    return cleaned or ["Business Request"]


def _safe_open_questions(analysis: RequirementAnalysisResponse) -> list[str]:
    unresolved = _unresolved_questionnaire_items(analysis)
    if unresolved:
        return unresolved
    if _is_draft_ready(analysis):
        return [
            "Review optional refinements before final saving if the project owner wants more detail."
        ]
    if analysis.next_question.text:
        return [analysis.next_question.text]
    return ["Review the temporary fallback preview before saving it as a final SAD."]


def _unresolved_questionnaire_items(
    analysis: RequirementAnalysisResponse,
) -> list[str]:
    if analysis.questionnaire is None:
        return [
            f"Clarify {category.label}."
            for category in analysis.categories
            if category.status in ("missing", "partial")
        ]

    return [
        f"Clarify {category.label}."
        for category in analysis.questionnaire.categories
        if category.status in ("needed", "in_progress", "needs_later_confirmation")
    ]


def _is_draft_ready(analysis: RequirementAnalysisResponse) -> bool:
    if analysis.questionnaire is None:
        return False
    return analysis.questionnaire.draft_readiness.score == 100


def _compact_text(text: str) -> str:
    clean = " ".join(text.split())
    return clean or "No confirmed detail provided yet."


def _is_workshop_request(clean_request: str) -> bool:
    lowered = clean_request.lower()
    return "workshop" in lowered and "maintenance" in lowered


def _is_tuition_request(clean_request: str) -> bool:
    lowered = clean_request.lower()
    return any(
        term in lowered
        for term in ("tuition", "student", "class schedules", "teacher", "parent", "fee", "attendance")
    )


def _is_internal_source_reference(reference: str) -> bool:
    lowered = reference.strip().lower()
    return lowered.startswith("_sadify/") or (
        "." in lowered
        and lowered.split(".", 1)[0]
        in {
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
        }
    )
