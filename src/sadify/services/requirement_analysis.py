from __future__ import annotations

from dataclasses import dataclass
import re


_STANDARD_FIRST_RESPONSE_SECTIONS = (
    "Understanding summary",
    "Completeness",
    "Confidence",
    "Missing information",
    "Clarification questions",
    "Draft option",
)


@dataclass(frozen=True)
class MissingInformation:
    category: str
    severity: str
    item: str
    why_it_matters: str
    suggested_next_step: str

    def to_display_dict(self) -> dict[str, str]:
        return {
            "category": self.category,
            "severity": self.severity,
            "item": self.item,
            "why_it_matters": self.why_it_matters,
            "suggested_next_step": self.suggested_next_step,
        }


@dataclass(frozen=True)
class ClarificationQuestion:
    question_id: str
    severity: str
    question: str

    def to_display_dict(self) -> dict[str, str]:
        return {
            "question_id": self.question_id,
            "severity": self.severity,
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
            severity="[HIGH]",
            item="User roles are not clear.",
            why_it_matters="Developers need to know who uses and owns each workflow step.",
            suggested_next_step="Name the main users, reviewers, and managers.",
        ),
        question="Who are the users, reviewers, and owners involved in this process?",
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
            severity="[CRITICAL]",
            item="Current or target workflow is not described.",
            why_it_matters="The system design depends on process steps and handoffs.",
            suggested_next_step="Describe what happens from trigger to completion.",
        ),
        question="What are the current process steps from start to finish?",
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
            severity="[HIGH]",
            item="Required data fields are incomplete.",
            why_it_matters="Database, form, and validation design need concrete fields.",
            suggested_next_step="List the fields that must be captured and reported.",
        ),
        question="What exact data fields must the system capture?",
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
            severity="[HIGH]",
            item="Approval or verification rules are missing.",
            why_it_matters="Permissions and workflow states cannot be designed safely without this.",
            suggested_next_step="Define who can approve, reject, verify, or override records.",
        ),
        question="Who verifies, approves, rejects, or overrides the record?",
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
            severity="[MEDIUM]",
            item="Reporting needs are not specified.",
            why_it_matters="Output screens and exports depend on the decisions users need to make.",
            suggested_next_step="Identify reports, dashboards, or summaries users expect.",
        ),
        question="What reports, dashboards, or summaries are needed?",
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
            severity="[MEDIUM]",
            item="Exception handling is not described.",
            why_it_matters="Systems need behavior for mistakes, missing data, and unusual cases.",
            suggested_next_step="Describe what should happen when something goes wrong.",
        ),
        question="What should happen when records are wrong, missing, late, or duplicated?",
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
            severity="[HIGH]",
            item="Access and permission rules are missing.",
            why_it_matters="User roles affect security, screens, and allowed actions.",
            suggested_next_step="Define who can create, edit, view, approve, and export data.",
        ),
        question="Who can create, edit, view, approve, and export the records?",
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
            severity="[MEDIUM]",
            item="Non-functional constraints are missing.",
            why_it_matters="Reliability, security, speed, and device needs affect architecture.",
            suggested_next_step="Confirm constraints such as mobile use, offline mode, audit trail, and performance.",
        ),
        question="Are there any mobile, offline, audit, security, or performance needs?",
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
            severity=rule.missing.severity,
            question=rule.question,
        )
        for index, rule in enumerate(missing_rules[:5], start=1)
    )
