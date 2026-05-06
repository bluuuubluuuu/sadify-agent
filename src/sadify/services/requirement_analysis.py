from __future__ import annotations

from dataclasses import dataclass

from sadify.services.completeness_scoring import (
    CompletenessScore,
    score_requirement_context,
)


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
    evidence_summary: tuple[str, ...]
    scoring_basis: str
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
            "evidence_summary": list(self.evidence_summary),
            "scoring_basis": self.scoring_basis,
            "draft_allowed": self.draft_allowed,
            "analysis_mode": self.analysis_mode,
        }


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
            evidence_summary=(),
            scoring_basis="local deterministic evidence checklist",
            draft_allowed=False,
        )

    score = score_requirement_context(normalized_text)

    return RequirementAnalysis(
        is_valid=True,
        validation_error=None,
        understanding_summary=_build_summary(normalized_text),
        completeness_score=score.score,
        completeness_level=score.level,
        confidence_label=score.confidence_label,
        confidence_reason=score.confidence_reason,
        missing_information=_build_missing_information(score),
        clarification_questions=_build_questions(score),
        evidence_summary=score.evidence_summary,
        scoring_basis=score.scoring_basis,
        draft_allowed=True,
    )


def _build_summary(text: str) -> str:
    clipped = text[:220].rstrip()
    if len(text) > len(clipped):
        clipped = f"{clipped}..."
    return f"SADify understands this as an operational requirement about: {clipped}"


def _build_missing_information(
    score: CompletenessScore,
) -> tuple[MissingInformation, ...]:
    return tuple(
        MissingInformation(
            category=category.category,
            area=category.area,
            priority=category.priority,
            what_is_unclear=category.what_is_unclear,
            why_this_matters=category.why_this_matters,
            what_to_answer_next=category.what_to_answer_next,
        )
        for category in score.missing_categories
    )


def _build_questions(
    score: CompletenessScore,
) -> tuple[ClarificationQuestion, ...]:
    return tuple(
        ClarificationQuestion(
            question_id=f"Q-{index:03}",
            priority=category.priority,
            question=category.question,
        )
        for index, category in enumerate(score.missing_categories[:5], start=1)
    )
