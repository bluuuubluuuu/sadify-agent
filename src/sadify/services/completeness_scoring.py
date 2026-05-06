from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ScoredCategory:
    category: str
    area: str
    weight: int
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class MissingCategory:
    category: str
    area: str
    priority: str
    what_is_unclear: str
    why_this_matters: str
    what_to_answer_next: str
    question: str


@dataclass(frozen=True)
class CompletenessScore:
    score: int
    level: str
    confidence_label: str
    confidence_reason: str
    present_categories: tuple[ScoredCategory, ...]
    missing_categories: tuple[MissingCategory, ...]
    evidence_summary: tuple[str, ...]
    scoring_basis: str = "local deterministic evidence checklist"


@dataclass(frozen=True)
class CategoryRule:
    category: str
    area: str
    weight: int
    priority: str
    keywords: tuple[str, ...]
    what_is_unclear: str
    why_this_matters: str
    what_to_answer_next: str
    question: str


_CATEGORY_RULES = (
    CategoryRule(
        category="business_problem",
        area="Business problem",
        weight=12,
        priority="Critical",
        keywords=(
            "bottleneck",
            "delay",
            "dispatch",
            "error",
            "issue",
            "lose",
            "losing",
            "mistake",
            "movement",
            "operation",
            "operational",
            "operations",
            "problem",
            "stock",
            "warehouse",
        ),
        what_is_unclear="We do not yet know what business problem should be solved.",
        why_this_matters=(
            "The system draft needs a real business pain, not only a role or topic."
        ),
        what_to_answer_next=(
            "Describe the problem people face today and what outcome should improve."
        ),
        question="What business problem should the system solve?",
    ),
    CategoryRule(
        category="people",
        area="People involved",
        weight=10,
        priority="High",
        keywords=(
            "coordinator",
            "customer",
            "manager",
            "operator",
            "staff",
            "supervisor",
            "team",
            "worker",
        ),
        what_is_unclear=(
            "We do not yet know who uses, checks, or owns this process."
        ),
        why_this_matters=(
            "The system needs to match the real responsibilities in the business."
        ),
        what_to_answer_next=(
            "Name the staff, supervisors, managers, customers, or partners involved."
        ),
        question=(
            "Who uses this process, and who is responsible for checking or approving it?"
        ),
    ),
    CategoryRule(
        category="process",
        area="Process steps",
        weight=16,
        priority="Critical",
        keywords=(
            "dispatch",
            "flow",
            "move",
            "moved",
            "movement",
            "packing",
            "picking",
            "process",
            "receiving",
            "record",
            "scan",
            "submit",
            "track",
            "update",
            "workflow",
        ),
        what_is_unclear="The start-to-finish process is not clear yet.",
        why_this_matters=(
            "SADify needs the real steps before it can describe what the system should support."
        ),
        what_to_answer_next="Explain what happens first, next, and last.",
        question="What happens first, next, and last in this process?",
    ),
    CategoryRule(
        category="details",
        area="Details to capture",
        weight=14,
        priority="High",
        keywords=(
            "block",
            "code",
            "date",
            "field",
            "item",
            "line",
            "location",
            "quantity",
            "reason",
            "remarks",
            "status",
        ),
        what_is_unclear=(
            "We do not yet know what details staff need to enter, scan, or select."
        ),
        why_this_matters="Forms, records, and reports depend on these details.",
        what_to_answer_next=(
            "List details such as item, quantity, status, date, location, reason, or remarks."
        ),
        question="What details must staff enter, scan, or select?",
    ),
    CategoryRule(
        category="approval",
        area="Checking and approval",
        weight=10,
        priority="High",
        keywords=(
            "adjustment",
            "approve",
            "approval",
            "authorize",
            "reject",
            "rejected",
            "review",
            "sign off",
            "verify",
        ),
        what_is_unclear=(
            "It is not clear who checks, approves, rejects, or changes records."
        ),
        why_this_matters=(
            "The system needs clear controls for important decisions and changes."
        ),
        what_to_answer_next=(
            "Say who can check, approve, reject, correct, or override the record."
        ),
        question="Who can check, approve, reject, correct, or override records?",
    ),
    CategoryRule(
        category="visibility",
        area="Reports and visibility",
        weight=12,
        priority="Medium",
        keywords=(
            "alert",
            "dashboard",
            "daily",
            "export",
            "monthly",
            "report",
            "summary",
            "weekly",
        ),
        what_is_unclear=(
            "We do not yet know what summaries, dashboards, or exports people need."
        ),
        why_this_matters=(
            "Reports should support the decisions managers actually make."
        ),
        what_to_answer_next=(
            "List the reports, dashboards, alerts, or exports people expect."
        ),
        question="What reports, dashboards, alerts, or exports do people need?",
    ),
    CategoryRule(
        category="exceptions",
        area="Problems and edge cases",
        weight=8,
        priority="Medium",
        keywords=(
            "duplicate",
            "error",
            "exception",
            "fail",
            "failed",
            "forget",
            "missing",
            "mistake",
            "rejected",
            "wrong",
        ),
        what_is_unclear=(
            "We do not yet know what should happen when something goes wrong."
        ),
        why_this_matters=(
            "Real operations have missing, late, duplicated, or incorrect records."
        ),
        what_to_answer_next=(
            "Describe mistakes, delays, missing data, failed scans, or unusual cases."
        ),
        question=(
            "What should happen when records are wrong, missing, late, or duplicated?"
        ),
    ),
    CategoryRule(
        category="access",
        area="Access",
        weight=10,
        priority="High",
        keywords=(
            "access",
            "admin",
            "permission",
            "role",
            "role-based",
            "who can",
        ),
        what_is_unclear=(
            "It is not clear who can create, edit, view, approve, or export records."
        ),
        why_this_matters=(
            "Different people usually need different screens and allowed actions."
        ),
        what_to_answer_next=(
            "Say what each role is allowed to do and what they should not see."
        ),
        question="Who can create, edit, view, approve, and export records?",
    ),
    CategoryRule(
        category="operating_needs",
        area="Practical operating needs",
        weight=8,
        priority="Medium",
        keywords=(
            "audit",
            "busy-hour",
            "fast",
            "history",
            "mobile",
            "offline",
            "performance",
            "secure",
            "security",
        ),
        what_is_unclear=(
            "We do not yet know practical needs such as mobile use, history, speed, or offline work."
        ),
        why_this_matters=(
            "These needs affect whether the system works well in daily operations."
        ),
        what_to_answer_next=(
            "Confirm mobile use, offline work, audit history, security, or busy-hour speed needs."
        ),
        question=(
            "Does this need to work on mobile, keep history, work offline, or stay fast during busy hours?"
        ),
    ),
)


def score_requirement_context(requirement_text: str) -> CompletenessScore:
    normalized_text = " ".join(requirement_text.split())
    word_count = len(normalized_text.split())
    if not normalized_text:
        return _build_score(0, (), word_count, "No requirement text was provided.")

    present_categories = _present_categories(normalized_text, word_count)
    raw_score = sum(category.weight for category in present_categories)
    capped_score = min(raw_score, _score_cap(present_categories, word_count))
    return _build_score(capped_score, present_categories, word_count)


def _present_categories(
    normalized_text: str,
    word_count: int,
) -> tuple[ScoredCategory, ...]:
    if word_count < 5:
        return ()

    return tuple(
        ScoredCategory(
            category=rule.category,
            area=rule.area,
            weight=rule.weight,
            evidence=_matching_keywords(normalized_text, rule.keywords),
        )
        for rule in _CATEGORY_RULES
        if _matching_keywords(normalized_text, rule.keywords)
    )


def _matching_keywords(text: str, keywords: tuple[str, ...]) -> tuple[str, ...]:
    normalized = text.lower()
    return tuple(
        match
        for keyword in keywords
        for match in [_keyword_match(normalized, keyword)]
        if match is not None
    )


def _keyword_match(text: str, keyword: str) -> str | None:
    if " " in keyword or "-" in keyword:
        return keyword if keyword in text else None
    match = re.search(rf"\b{re.escape(keyword)}s?\b", text)
    if match is None:
        return None
    return match.group(0)


def _score_cap(
    present_categories: tuple[ScoredCategory, ...],
    word_count: int,
) -> int:
    present_ids = {category.category for category in present_categories}
    cap = 100
    if word_count < 5:
        cap = min(cap, 10)
    elif word_count < 15:
        cap = min(cap, 25)
    if "process" not in present_ids:
        cap = min(cap, 55)
    if "business_problem" not in present_ids:
        cap = min(cap, 65)
    return cap


def _build_score(
    score: int,
    present_categories: tuple[ScoredCategory, ...],
    word_count: int,
    confidence_reason: str | None = None,
) -> CompletenessScore:
    missing_categories = _missing_categories(present_categories)
    return CompletenessScore(
        score=score,
        level=_completeness_level(score),
        confidence_label=_confidence_label(score, word_count, missing_categories),
        confidence_reason=confidence_reason
        or _confidence_reason(score, word_count, missing_categories),
        present_categories=present_categories,
        missing_categories=missing_categories,
        evidence_summary=_evidence_summary(present_categories),
    )


def _missing_categories(
    present_categories: tuple[ScoredCategory, ...],
) -> tuple[MissingCategory, ...]:
    present_ids = {category.category for category in present_categories}
    return tuple(
        MissingCategory(
            category=rule.category,
            area=rule.area,
            priority=rule.priority,
            what_is_unclear=rule.what_is_unclear,
            why_this_matters=rule.why_this_matters,
            what_to_answer_next=rule.what_to_answer_next,
            question=rule.question,
        )
        for rule in _CATEGORY_RULES
        if rule.category not in present_ids
    )


def _evidence_summary(
    present_categories: tuple[ScoredCategory, ...],
) -> tuple[str, ...]:
    return tuple(
        f"{category.area}: {', '.join(category.evidence[:4])}"
        for category in present_categories
    )


def _completeness_level(score: int) -> str:
    if score <= 39:
        return "Low"
    if score <= 69:
        return "Partial"
    if score <= 84:
        return "Good"
    return "Strong"


def _confidence_label(
    score: int,
    word_count: int,
    missing_categories: tuple[MissingCategory, ...],
) -> str:
    critical_missing = {
        category.category
        for category in missing_categories
        if category.priority == "Critical"
    }
    if score <= 39 or word_count < 15 or critical_missing:
        return "Low"
    if score <= 84:
        return "Medium"
    return "High"


def _confidence_reason(
    score: int,
    word_count: int,
    missing_categories: tuple[MissingCategory, ...],
) -> str:
    if word_count < 5:
        return (
            "There is too little business context to understand the request yet."
        )
    if word_count < 15:
        return (
            "The request is still very short, so the score is capped until the business context is clearer."
        )
    critical_missing = [
        category.area
        for category in missing_categories
        if category.priority == "Critical"
    ]
    if critical_missing:
        return (
            "Important context is still missing: "
            f"{', '.join(critical_missing)}."
        )
    if score <= 69:
        return (
            "Some useful business details are visible, but several areas still need confirmation."
        )
    if score <= 84:
        return (
            "The main request is understandable, with a few areas still needing confirmation."
        )
    return (
        "The request includes the main business problem, process, details, controls, visibility, and operating needs."
    )
