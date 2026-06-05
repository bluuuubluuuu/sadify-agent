from sadify_api.schemas import RequirementAnalysisResponse


INTERNAL_DIAGNOSTIC_TERMS = (
    "fallback",
    "gemini output",
    "structured-output",
    "retry",
    "validated",
)

REVISION_NO_FABRICATION_INSTRUCTION = (
    "Revise the draft to address these issues using only facts already in the "
    "requirement, sources, and Q&A answers. If a requested detail is not present, "
    "do NOT invent it — keep it as an assumption or open question."
)


def build_sad_synthesis_context(
    *,
    requirement_text: str,
    analysis_id: str | None,
    analysis: RequirementAnalysisResponse,
    source_context: str | None,
    source_references: list[str],
    revision_feedback: str | None = None,
) -> str:
    user_assumptions, internal_diagnostics = split_assumptions(analysis.assumptions)
    internal_diagnostics.extend(_questionnaire_diagnostics(analysis))
    source_label = ", ".join(source_references) if source_references else "Business Request"
    clean_request = clean_business_request(requirement_text)
    parts = [
        f"Analysis ID: {analysis_id or 'not saved'}",
        "",
        "Layer 1 draft readiness:",
        _draft_readiness_line(analysis),
        "",
        "Confirmed request facts:",
        clean_request,
        "",
        "Current understanding:",
        analysis.understanding_summary,
        "",
        "Cleared categories:",
        "\n".join(_cleared_category_lines(analysis)),
        "",
        "Partial-evidence slots:",
        "\n".join(_partial_evidence_lines(analysis)),
        "",
        "Deferred or unsure slots:",
        "\n".join(_deferred_slot_lines(analysis)),
        "",
        "Confirmed questionnaire answers:",
        "\n".join(_answer_lines(analysis)),
        "",
        "Unresolved items:",
        "\n".join(_unresolved_lines(analysis)),
        "",
        "Business-facing assumptions:",
        "\n".join(f"- {item}" for item in user_assumptions) or "- none",
        "",
        "Business source references:",
        source_label,
        "",
        "Source context:",
        (source_context or "").strip() or "none",
        "",
        "Internal diagnostics, not for SAD assumptions:",
        "\n".join(f"- {item}" for item in internal_diagnostics) or "- none",
    ]
    if revision_feedback:
        parts.extend(
            [
                "",
                "Revision feedback:",
                REVISION_NO_FABRICATION_INSTRUCTION,
                revision_feedback.strip(),
            ]
        )
    return "\n".join(parts)


_READY_STATUSES = {"ready", "complete"}
_CLEARED_VISIBILITIES = {"already_understood", "completed"}


def _cleared_category_lines(analysis: RequirementAnalysisResponse) -> list[str]:
    if analysis.questionnaire is None:
        return ["- none"]
    cleared = [
        f"- {category.label} ({category.id}) — source: "
        f"{'already understood' if category.visibility == 'already_understood' else 'questionnaire answer'}"
        for category in analysis.questionnaire.categories
        if category.status in _READY_STATUSES
        and category.visibility in _CLEARED_VISIBILITIES
    ]
    return cleared or ["- none"]


def _partial_evidence_lines(analysis: RequirementAnalysisResponse) -> list[str]:
    partials = [
        f"- {verdict.category_id}.{verdict.slot_id}: \"{verdict.evidence_quote}\""
        for verdict in analysis.slot_evidence
        if verdict.applicability == "applicable"
        and verdict.strength == "partial"
    ]
    return partials or ["- none"]


def _deferred_slot_lines(analysis: RequirementAnalysisResponse) -> list[str]:
    if analysis.questionnaire is None:
        return ["- none"]
    deferred = [
        f"- {answer.category_id}.{answer.slot_id or 'unknown'}: {answer.question}"
        for answer in analysis.questionnaire.answers
        if answer.is_uncertain
    ]
    return deferred or ["- none"]


def clean_business_request(requirement_text: str) -> str:
    return requirement_text.split("Previous question:", 1)[0].strip()


def split_assumptions(assumptions: list[str]) -> tuple[list[str], list[str]]:
    user_visible: list[str] = []
    diagnostics: list[str] = []
    for assumption in assumptions:
        lowered = assumption.lower()
        if any(term in lowered for term in INTERNAL_DIAGNOSTIC_TERMS):
            diagnostics.append(assumption)
        else:
            user_visible.append(assumption)
    return user_visible, diagnostics


def _draft_readiness_line(analysis: RequirementAnalysisResponse) -> str:
    if analysis.questionnaire is not None:
        readiness = analysis.questionnaire.draft_readiness
        return f"{readiness.label}, {readiness.score}%"
    return (
        f"{analysis.readiness.label}, {analysis.readiness.score}%, "
        f"{analysis.readiness.confidence} confidence"
    )


def _answer_lines(analysis: RequirementAnalysisResponse) -> list[str]:
    if analysis.questionnaire is None or not analysis.questionnaire.answers:
        return ["- none"]
    return [
        (
            f"- {answer.category_id}.{answer.slot_id or 'unknown_slot'}: "
            f"{answer.question} -> {answer.answer}"
        )
        for answer in analysis.questionnaire.answers
    ]


def _unresolved_lines(analysis: RequirementAnalysisResponse) -> list[str]:
    if analysis.questionnaire is None:
        return [
            f"- {category.label}: {category.status}"
            for category in analysis.categories
            if category.status != "complete"
        ] or ["- none"]

    unresolved = [
        f"- {category.label}: {category.status.replace('_', ' ')}"
        for category in analysis.questionnaire.categories
        if category.status in ("needed", "in_progress", "needs_later_confirmation")
    ]
    return unresolved or ["- none"]


def _questionnaire_diagnostics(analysis: RequirementAnalysisResponse) -> list[str]:
    if analysis.questionnaire is None:
        return []
    return list(analysis.questionnaire.diagnostics)
