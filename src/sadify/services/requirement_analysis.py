from __future__ import annotations

from dataclasses import dataclass
import re


_STANDARD_FIRST_RESPONSE_SECTIONS = (
    "What SADify understands",
    "Readiness",
    "Confidence",
    "What we still need to know",
    "Questions to confirm",
    "Draft option",
)


@dataclass(frozen=True)
class MissingInformation:
    category: str
    area: str
    priority: str
    what_is_unclear: str
    why_this_matters: str
    what_to_answer_next: str

    def to_display_dict(self) -> dict[str, str]:
        return {
            "area": self.area,
            "priority": self.priority,
            "what_is_unclear": self.what_is_unclear,
            "why_this_matters": self.why_this_matters,
            "what_to_answer_next": self.what_to_answer_next,
        }


@dataclass(frozen=True)
class ClarificationQuestion:
    question_id: str
    priority: str
    question: str

    def to_display_dict(self) -> dict[str, str]:
        return {
            "question_id": self.question_id,
            "priority": self.priority,
            "question": self.question,
        }


@dataclass(frozen=True)
class RequirementAnalysis:
    is_valid: bool
    validation_error: str | None
    understanding_summary: str
    completeness_score: int
    completeness_level: str
    confidence_label: str
    confidence_reason: str
    missing_information: tuple[MissingInformation, ...]
    clarification_questions: tuple[ClarificationQuestion, ...]
    draft_allowed: bool
    analysis_mode: str = "deterministic"

    def to_display_dict(self) -> dict[str, object]:
        return {
            "sections": standard_first_response_sections(),
            "is_valid": self.is_valid,
            "validation_error": self.validation_error,
            "understanding_summary": self.understanding_summary,
            "completeness_score": self.completeness_score,
            "completeness_level": self.completeness_level,
            "confidence_label": self.confidence_label,
            "confidence_reason": self.confidence_reason,
            "missing_information": [
                item.to_display_dict() for item in self.missing_information
            ],
            "clarification_questions": [
                question.to_display_dict()
                for question in self.clarification_questions
            ],
            "draft_allowed": self.draft_allowed,
            "analysis_mode": self.analysis_mode,
        }


@dataclass(frozen=True)
class RequirementCategoryRule:
    category: str
    keywords: tuple[str, ...]
    missing: MissingInformation
    question: str


_CATEGORY_RULES = (
    RequirementCategoryRule(
        category="Actors",
        keywords=(
            "admin",
            "coordinator",
            "customer",
            "manager",
            "operator",
            "staff",
            "supervisor",
            "team",
            "user",
            "worker",
        ),
        missing=MissingInformation(
            category="Actors",
            area="People involved",
            priority="High",
            what_is_unclear=(
                "We do not yet know who uses, checks, or owns this process."
            ),
            why_this_matters=(
                "The system needs to match the real responsibilities in the business."
            ),
            what_to_answer_next=(
                "Name the staff, supervisors, managers, customers, or partners involved."
            ),
        ),
        question=(
            "Who uses this process, and who is responsible for checking or approving it?"
        ),
    ),
    RequirementCategoryRule(
        category="Workflow",
        keywords=(
            "check",
            "flow",
            "move",
            "moved",
            "process",
            "record",
            "submit",
            "track",
            "update",
            "workflow",
        ),
        missing=MissingInformation(
            category="Workflow",
            area="Process steps",
            priority="Critical",
            what_is_unclear="The start-to-finish process is not clear yet.",
            why_this_matters=(
                "SADify needs the real steps before it can describe what the system should support."
            ),
            what_to_answer_next="Explain what happens first, next, and last.",
        ),
        question="What happens first, next, and last in this process?",
    ),
    RequirementCategoryRule(
        category="Data fields",
        keywords=(
            "block",
            "date",
            "field",
            "item",
            "line",
            "location",
            "quantity",
            "record",
            "stock",
            "status",
        ),
        missing=MissingInformation(
            category="Data fields",
            area="Details to capture",
            priority="High",
            what_is_unclear=(
                "We do not yet know what details staff need to enter, scan, or select."
            ),
            why_this_matters=(
                "Forms, records, and reports depend on these details."
            ),
            what_to_answer_next=(
                "List details such as item, quantity, status, date, location, reason, or remarks."
            ),
        ),
        question="What details must staff enter, scan, or select?",
    ),
    RequirementCategoryRule(
        category="Approval rules",
        keywords=(
            "approve",
            "approval",
            "authorize",
            "reject",
            "review",
            "sign off",
            "verify",
        ),
        missing=MissingInformation(
            category="Approval rules",
            area="Checking and approval",
            priority="High",
            what_is_unclear=(
                "It is not clear who checks, approves, rejects, or changes records."
            ),
            why_this_matters=(
                "The system needs clear controls for important decisions and changes."
            ),
            what_to_answer_next=(
                "Say who can check, approve, reject, correct, or override the record."
            ),
        ),
        question="Who can check, approve, reject, correct, or override records?",
    ),
    RequirementCategoryRule(
        category="Reports",
        keywords=(
            "dashboard",
            "daily",
            "monthly",
            "report",
            "summary",
            "weekly",
        ),
        missing=MissingInformation(
            category="Reports",
            area="Reports and visibility",
            priority="Medium",
            what_is_unclear=(
                "We do not yet know what summaries, dashboards, or exports people need."
            ),
            why_this_matters=(
                "Reports should support the decisions managers actually make."
            ),
            what_to_answer_next=(
                "List the reports, dashboards, alerts, or exports people expect."
            ),
        ),
        question="What reports, dashboards, alerts, or exports do people need?",
    ),
    RequirementCategoryRule(
        category="Exceptions",
        keywords=(
            "error",
            "exception",
            "fail",
            "forget",
            "missing",
            "mistake",
            "offline",
            "sometimes",
        ),
        missing=MissingInformation(
            category="Exceptions",
            area="Problems and edge cases",
            priority="Medium",
            what_is_unclear=(
                "We do not yet know what should happen when something goes wrong."
            ),
            why_this_matters=(
                "Real operations have missing, late, duplicated, or incorrect records."
            ),
            what_to_answer_next=(
                "Describe mistakes, delays, missing data, failed scans, or unusual cases."
            ),
        ),
        question=(
            "What should happen when records are wrong, missing, late, or duplicated?"
        ),
    ),
    RequirementCategoryRule(
        category="Permissions",
        keywords=(
            "access",
            "admin",
            "permission",
            "role",
            "who can",
        ),
        missing=MissingInformation(
            category="Permissions",
            area="Access",
            priority="High",
            what_is_unclear=(
                "It is not clear who can create, edit, view, approve, or export records."
            ),
            why_this_matters=(
                "Different people usually need different screens and allowed actions."
            ),
            what_to_answer_next=(
                "Say what each role is allowed to do and what they should not see."
            ),
        ),
        question="Who can create, edit, view, approve, and export records?",
    ),
    RequirementCategoryRule(
        category="Non-functional constraints",
        keywords=(
            "audit",
            "fast",
            "mobile",
            "offline",
            "performance",
            "secure",
            "security",
        ),
        missing=MissingInformation(
            category="Non-functional constraints",
            area="Practical operating needs",
            priority="Medium",
            what_is_unclear=(
                "We do not yet know practical needs such as mobile use, history, speed, or offline work."
            ),
            why_this_matters=(
                "These needs affect whether the system works well in daily operations."
            ),
            what_to_answer_next=(
                "Confirm mobile use, offline work, audit history, security, or busy-hour speed needs."
            ),
        ),
        question=(
            "Does this need to work on mobile, keep history, work offline, or stay fast during busy hours?"
        ),
    ),
)


def standard_first_response_sections() -> list[str]:
    return list(_STANDARD_FIRST_RESPONSE_SECTIONS)


def analyze_requirement_text(requirement_text: str) -> RequirementAnalysis:
    normalized_text = " ".join(requirement_text.split())
    if not normalized_text:
        return RequirementAnalysis(
            is_valid=False,
            validation_error="Enter an operational problem before analysis.",
            understanding_summary="",
            completeness_score=0,
            completeness_level="Low",
            confidence_label="Low",
            confidence_reason="No requirement text was provided.",
            missing_information=(),
            clarification_questions=(),
            draft_allowed=False,
        )

    present_categories = {
        rule.category
        for rule in _CATEGORY_RULES
        if _contains_any_keyword(normalized_text, rule.keywords)
    }
    missing_rules = tuple(
        rule for rule in _CATEGORY_RULES if rule.category not in present_categories
    )
    score = round((len(present_categories) / len(_CATEGORY_RULES)) * 100)

    return RequirementAnalysis(
        is_valid=True,
        validation_error=None,
        understanding_summary=_build_summary(normalized_text),
        completeness_score=score,
        completeness_level=_completeness_level(score),
        confidence_label=_confidence_label(score),
        confidence_reason=_confidence_reason(score, len(normalized_text.split())),
        missing_information=tuple(rule.missing for rule in missing_rules),
        clarification_questions=_build_questions(missing_rules),
        draft_allowed=True,
    )


def _contains_any_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    normalized = text.lower()
    return any(_keyword_matches(normalized, keyword) for keyword in keywords)


def _keyword_matches(text: str, keyword: str) -> bool:
    if " " in keyword:
        return keyword in text
    return re.search(rf"\b{re.escape(keyword)}s?\b", text) is not None


def _build_summary(text: str) -> str:
    clipped = text[:220].rstrip()
    if len(text) > len(clipped):
        clipped = f"{clipped}..."
    return f"SADify understands this as an operational requirement about: {clipped}"


def _completeness_level(score: int) -> str:
    if score <= 39:
        return "Low"
    if score <= 69:
        return "Partial"
    if score <= 84:
        return "Good"
    return "Strong"


def _confidence_label(score: int) -> str:
    if score <= 39:
        return "Low"
    if score <= 84:
        return "Medium"
    return "High"


def _confidence_reason(score: int, word_count: int) -> str:
    if score <= 39:
        return "Only a small amount of the required analysis context is visible."
    if word_count < 20:
        return "The requirement is short, so the deterministic analysis needs confirmation."
    return "The main problem is understandable, but missing categories still need confirmation."


def _build_questions(
    missing_rules: tuple[RequirementCategoryRule, ...],
) -> tuple[ClarificationQuestion, ...]:
    return tuple(
        ClarificationQuestion(
            question_id=f"Q-{index:03}",
            priority=rule.missing.priority,
            question=rule.question,
        )
        for index, rule in enumerate(missing_rules[:5], start=1)
    )
