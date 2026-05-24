import logging

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from sadify_api.schemas import (
    QuestionnairePlanSlotPointer,
    RequirementAnalysisApiResponse,
    RequirementAnalysisRequest,
    RequirementAnalysisResponse,
    SlotEvidence,
)
from sadify_api.services.analysis_state import RequirementAnalysisRepository
from sadify_api.services.gemini_structured import (
    RequirementAnalysisModel,
    parse_requirement_analysis,
)
from sadify_api.services.questionnaire_plan import (
    CANONICAL_CATEGORY_IDS,
    _slot_weight,
    cover_slot,
    create_initial_plan,
    create_plan_from_evidence,
    defer_slot,
    next_open_slot,
)
from sadify_api.services.slot_evidence import (
    derive_confidence,
    merge_evidence,
    validate_slot_evidence,
)
from sadify_api.services.questionnaire_slots import (
    best_matching_slot,
    fallback_question_for_slot,
    semantic_score_for_slot,
)

FALLBACK_CATEGORY_ORDER = (
    {"id": "users_roles", "label": "Users and staff roles"},
    {"id": "workflow", "label": "Workflow steps and exceptions"},
    {"id": "data_reports", "label": "Data fields and reports"},
    {"id": "rules", "label": "Business rules and approvals"},
)

FALLBACK_QUESTIONS_NEEDED = 2

LEGACY_TO_CANONICAL_CATEGORY_IDS = {
    "problem": "goal_scope",
    "goal_scope": "goal_scope",
    "users_roles": "users_roles",
    "workflow": "workflow_steps",
    "workflow_steps": "workflow_steps",
    "data_reports": "data_records",
    "data_records": "data_records",
    "rules": "rules_approvals",
    "rules_approvals": "rules_approvals",
}


logger = logging.getLogger(__name__)


class QuestionnaireDriftError(Exception):
    """Raised when Gemini returns structurally valid but workflow-invalid output."""


def create_analysis_router(
    model: RequirementAnalysisModel,
    repository: RequirementAnalysisRepository,
) -> APIRouter:
    router = APIRouter(prefix="/analysis", tags=["analysis"])

    @router.post("/requirement", response_model=RequirementAnalysisApiResponse)
    def analyze_requirement(
        request: RequirementAnalysisRequest,
    ) -> RequirementAnalysisApiResponse:
        prior_record = repository.latest_for_request(request)
        prior_analysis = prior_record.analysis if prior_record is not None else None
        locked_target = _locked_target_for_request(
            request, prior_analysis=prior_analysis
        )
        locked_categories = _prior_locked_categories(prior_analysis)
        validation_errors: list[str] = []
        for repair in (False, True):
            raw_json = ""
            try:
                model_requirement_text = _build_model_requirement_text(
                    request,
                    locked_target=locked_target,
                )
                raw_json = model.analyze_requirement(
                    model_requirement_text,
                    repair=repair,
                )
                analysis = _with_requested_source_references(
                    parse_requirement_analysis(raw_json),
                    request.source_references,
                )
                _validate_model_analysis(
                    analysis,
                    locked_target=locked_target,
                )
                analysis = _with_questionnaire_state(
                    analysis,
                    request,
                    fallback_used=False,
                    prior_analysis=prior_analysis,
                )
            except (ValidationError, QuestionnaireDriftError) as exc:
                validation_errors.append(
                    f"repair={repair}:{type(exc).__name__}:{_safe_exception_message(exc)[:120]}"
                )
                continue
            except Exception as exc:
                logger.exception(
                    "sadify_turn analysis_call_failed repair=%s raw_len=%d",
                    repair,
                    len(raw_json),
                )
                raise HTTPException(
                    status_code=502,
                    detail=f"Gemini analysis failed: {_safe_exception_message(exc)}",
                ) from exc

            record = repository.save_analysis(
                requirement_text=request.requirement_text,
                guest_draft_id=request.guest_draft_id,
                analysis=analysis,
            )
            _log_turn(
                record=record,
                source="gemini",
                prior=prior_record,
                locked_categories=locked_categories,
                validation_errors=validation_errors,
            )
            return RequirementAnalysisApiResponse(
                analysis_id=record.analysis_id,
                saved=True,
                analysis=record.analysis,
            )

        fallback_analysis = _fallback_requirement_analysis(
            request,
            locked_target=locked_target,
            prior_analysis=prior_analysis,
        )
        record = repository.save_analysis(
            requirement_text=request.requirement_text,
            guest_draft_id=request.guest_draft_id,
            analysis=fallback_analysis,
        )
        _log_turn(
            record=record,
            source="fallback",
            prior=prior_record,
            locked_categories=locked_categories,
            validation_errors=validation_errors,
        )
        return RequirementAnalysisApiResponse(
            analysis_id=record.analysis_id,
            saved=True,
            analysis=record.analysis,
        )

    return router


def _log_turn(
    *,
    record,
    source: str,
    prior,
    locked_categories: set[str],
    validation_errors: list[str],
) -> None:
    """One structured line per /analysis/requirement turn.

    Designed for tailing during browser smoke. Fields:
      id              this turn's analysis id
      source          'gemini' (validated) or 'fallback' (local template)
      prior           prior turn id or None
      active          active category/slot, or 'none' when draft-ready
      score           draft readiness percent
      locked          comma-separated categories already cleared (ratchet)
      errors          repair_flag:type:short_message per validation retry (if any)
    """
    questionnaire = record.analysis.questionnaire
    if questionnaire is None:
        active = "none"
        score = 0
    else:
        active = (
            f"{questionnaire.active_category_id}/"
            f"{questionnaire.active_slot_id or '-'}"
        )
        score = questionnaire.draft_readiness.score
    locked_str = ",".join(sorted(locked_categories)) or "-"
    errors_str = "|".join(validation_errors) if validation_errors else "-"
    prior_id = prior.analysis_id if prior is not None else None
    logger.warning(
        "sadify_turn id=%s source=%s prior=%s active=%s score=%d locked=%s errors=%s",
        record.analysis_id,
        source,
        prior_id,
        active,
        score,
        locked_str,
        errors_str,
    )


def _safe_exception_message(exc: Exception) -> str:
    message = str(exc).replace("\n", " ").strip()
    if len(message) > 500:
        message = f"{message[:497]}..."
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__


def _build_model_requirement_text(
    request: RequirementAnalysisRequest,
    *,
    locked_target=None,
) -> str:
    source_context = (request.source_context or "").strip()
    parts = [request.requirement_text]
    if source_context:
        parts.extend(["Uploaded source context:", source_context])
    if locked_target is not None:
        parts.extend(
            [
                "Locked questionnaire target:",
                f"active_category_id: {locked_target.category_id}",
                f"target_slot_id: {locked_target.slot_id}",
                "allowed_visible_category_ids: "
                + ", ".join(CANONICAL_CATEGORY_IDS),
                "Return the next question for this exact category and slot only.",
            ]
        )
    return "\n\n".join(parts)


def _with_requested_source_references(
    analysis: RequirementAnalysisResponse,
    source_references: list[str],
) -> RequirementAnalysisResponse:
    allowed = {"Business Request", *source_references}
    merged = [
        source_reference
        for source_reference in analysis.source_references
        if source_reference in allowed
    ]
    for source_reference in source_references:
        clean_reference = source_reference.strip()
        if clean_reference and clean_reference not in merged:
            merged.append(clean_reference)
    return analysis.model_copy(update={"source_references": merged})


def _validate_model_analysis(
    analysis: RequirementAnalysisResponse,
    *,
    locked_target,
) -> None:
    allowed_category_ids = set(CANONICAL_CATEGORY_IDS)
    for category in analysis.categories:
        if _canonical_category_id(category.id) not in allowed_category_ids:
            raise QuestionnaireDriftError(
                f"Unexpected visible category: {category.id}"
            )

    target_category_id = _canonical_category_id(analysis.next_question.target_category)
    if target_category_id not in allowed_category_ids:
        raise QuestionnaireDriftError(
            f"Unexpected target category: {analysis.next_question.target_category}"
        )

    empty_plan = create_initial_plan(initial_facts={})
    try:
        target_category = empty_plan.category(target_category_id)
        target_category.slot(analysis.next_question.target_slot_id)
    except KeyError as exc:
        raise QuestionnaireDriftError(
            f"Unexpected target slot: {analysis.next_question.target_slot_id}"
        ) from exc

    if locked_target is None:
        _validate_question_semantics(analysis)
        return
    _validate_question_semantics(analysis)


def _with_questionnaire_state(
    analysis: RequirementAnalysisResponse,
    request: RequirementAnalysisRequest,
    *,
    fallback_used: bool,
    prior_analysis: RequirementAnalysisResponse | None = None,
) -> RequirementAnalysisResponse:
    answers = _questionnaire_answers(request.requirement_text)
    new_verdicts, evidence_diagnostics = _validated_evidence(analysis, request)
    # Carry-forward merge: stops per-turn flicker, prevents readiness from
    # regressing when Gemini's verdict for a slot varies between calls or
    # when the fallback path returns no verdicts at all.
    prior_verdicts = (
        list(prior_analysis.slot_evidence) if prior_analysis is not None else []
    )
    edited_slots = _edited_slot_keys(prior_analysis, answers)
    verdicts = merge_evidence(
        prior=prior_verdicts, new=new_verdicts, edited_slots=edited_slots
    )
    # Ratchet: any category cleared in an earlier turn stays cleared.
    locked_categories = _prior_locked_categories(prior_analysis)
    prior_provenance = _prior_understood_via(prior_analysis)
    # Default for categories newly Ready this turn: "source" only on the
    # very first analysis (no answers yet, no prior turn); after that the
    # user has been answering, so newly Ready = "qa".
    default_new_provenance = (
        "source" if prior_analysis is None and not answers else "qa"
    )
    plan = _questionnaire_plan(
        verdicts,
        answers,
        prior_locked_categories=locked_categories,
        prior_understood_via=prior_provenance,
        default_new_provenance=default_new_provenance,
    )
    derived_confidence = derive_confidence(
        verdicts, downgrade_count=len(evidence_diagnostics)
    )
    if fallback_used:
        active_category_id = _canonical_category_id(analysis.next_question.target_category)
    else:
        active_category_id = plan.active_category_id or _canonical_category_id(
            analysis.next_question.target_category
        )
    context_text = _combined_requirement_context(request)
    if not fallback_used:
        analysis = _with_locked_question_category(
            analysis,
            plan,
            context_text=context_text,
        )
        analysis = _with_non_repeating_question(
            analysis,
            answers,
            plan,
            context_text=context_text,
        )
    category_state = _questionnaire_categories_from_plan(plan)
    draft_readiness = {
        "label": plan.overall_readiness.label,
        "score": plan.overall_readiness.score,
        "confidence": derived_confidence,
    }
    diagnostics = [
        "structured-output fallback used" if fallback_used else "Gemini structured output validated",
        f"AI confidence: {analysis.readiness.confidence}",
        f"Derived confidence: {derived_confidence}",
        *evidence_diagnostics,
    ]
    payload = analysis.model_dump()
    payload["questionnaire"] = {
        "draft_readiness": draft_readiness,
        "active_category_id": active_category_id,
        "active_slot_id": analysis.next_question.target_slot_id
        if fallback_used
        else _active_slot_id(plan) or analysis.next_question.target_slot_id,
        "active_slot_label": _active_slot_label_from_question(plan, analysis)
        if fallback_used
        else _active_slot_label(plan) or _active_slot_label_from_question(plan, analysis),
        "categories": category_state,
        "answers": answers,
        "diagnostics": diagnostics,
    }
    return RequirementAnalysisResponse.model_validate(payload)


_PARTIAL_ANSWER_CHARS = 30
_STRONG_ANSWER_CHARS = 60


def _validated_evidence(
    analysis: RequirementAnalysisResponse,
    request: RequirementAnalysisRequest,
) -> tuple[list, list[str]]:
    """Validate model slot evidence against the combined business material.

    Then apply Guard A: a slot the user has substantively answered is
    promoted to at-least-'partial' (>=30 chars) or 'strong' (>=60 chars)
    with the answer text as the quote. This stops the loop where Gemini's
    judgement misses a slot the user clearly answered. Strong verdicts
    from Gemini are never weakened — Guard A only raises the floor.
    """
    answers = _questionnaire_answers(request.requirement_text)
    material_parts = [_combined_requirement_context(request)]
    for answer in answers:
        material_parts.append(str(answer["answer"]))
    material = "\n".join(part for part in material_parts if part.strip())
    validated, diagnostics = validate_slot_evidence(
        analysis.slot_evidence, material=material
    )

    # Guard A: upgrade slots with substantive user answers.
    by_key = {(v.category_id, v.slot_id): v for v in validated}
    for answer in answers:
        slot_id = answer.get("slot_id")
        if not slot_id:
            continue
        text = str(answer["answer"]).strip()
        if len(text) < _PARTIAL_ANSWER_CHARS:
            continue
        promoted_strength = (
            "strong" if len(text) >= _STRONG_ANSWER_CHARS else "partial"
        )
        key = (str(answer["category_id"]), str(slot_id))
        existing = by_key.get(key)
        if existing is not None and existing.strength == "strong":
            continue
        if (
            existing is not None
            and existing.strength == "partial"
            and promoted_strength == "partial"
        ):
            continue
        by_key[key] = SlotEvidence(
            category_id=key[0],
            slot_id=key[1],
            applicability="applicable",
            strength=promoted_strength,
            evidence_quote=text,
            rationale="User provided a substantive free-text answer.",
        )

    return list(by_key.values()), diagnostics


def _edited_slot_keys(
    prior_analysis: RequirementAnalysisResponse | None,
    current_answers: list[dict[str, object]],
) -> set[tuple[str, str]]:
    """Slots whose latest answer text changed vs the previous saved analysis.

    Only slots present in BOTH prior and current count as edits — a brand-new
    answer for a slot the user has not addressed before is not an edit, and
    its prior evidence (likely 'none') merges naturally with the new verdict.
    """
    if prior_analysis is None or prior_analysis.questionnaire is None:
        return set()
    prior_latest: dict[tuple[str, str], str] = {}
    for answer in prior_analysis.questionnaire.answers:
        key = (answer.category_id, answer.slot_id or "")
        prior_latest[key] = answer.answer
    edited: set[tuple[str, str]] = set()
    for answer in current_answers:
        key = (str(answer["category_id"]), str(answer.get("slot_id") or ""))
        prior_text = prior_latest.get(key)
        if prior_text is not None and prior_text != str(answer["answer"]):
            edited.add(key)
    return edited


def _with_non_repeating_question(
    analysis: RequirementAnalysisResponse,
    answers: list[dict[str, object]],
    plan,
    *,
    context_text: str,
) -> RequirementAnalysisResponse:
    if _is_uncertainty_followup_question(analysis.next_question.text):
        return analysis

    active_category_id = plan.active_category_id or _canonical_category_id(
        analysis.next_question.target_category
    )
    active_slot = _next_open_slot_in_category(plan, active_category_id)
    if active_slot is None:
        return analysis

    target_category_id = _canonical_category_id(
        analysis.next_question.target_category
    )
    # Replace ONLY when Gemini's slot doesn't match the active slot. The
    # fuzzy 70%-token-overlap check was removed: it was replacing valid
    # Gemini follow-up questions with generic templates whenever phrasing
    # rhymed with a prior question.
    should_replace = (
        target_category_id != active_category_id
        or analysis.next_question.target_slot_id != active_slot.id
    )
    if not should_replace:
        return analysis


    replacement_question = fallback_question_for_slot(
        active_category_id,
        active_slot.id,
        context_text=context_text,
    )
    assumptions = list(analysis.assumptions)
    assumptions.append(
        "Gemini repeated or drifted from the active slot, so SADify used the canonical question for that slot.",
    )
    payload = analysis.model_dump()
    payload["next_question"] = replacement_question
    payload["assumptions"] = assumptions
    return RequirementAnalysisResponse.model_validate(payload)


def _with_locked_question_category(
    analysis: RequirementAnalysisResponse,
    plan,
    *,
    context_text: str,
) -> RequirementAnalysisResponse:
    active_category_id = plan.active_category_id or _canonical_category_id(
        analysis.next_question.target_category
    )
    target_category = _canonical_category_id(analysis.next_question.target_category)
    if target_category == active_category_id:
        payload = analysis.model_dump()
        payload["next_question"]["target_category"] = active_category_id
        return RequirementAnalysisResponse.model_validate(payload)

    slot = _next_open_slot_in_category(plan, active_category_id)
    if slot is not None:
        replacement_question = fallback_question_for_slot(
            active_category_id,
            slot.id,
            context_text=context_text,
        )
    else:
        replacement_question = _fallback_question(
            _legacy_topic_from_canonical(active_category_id),
            context_text=context_text,
        )
        replacement_question["target_category"] = active_category_id
    if slot is not None:
        replacement_question["target_slot_id"] = slot.id
    assumptions = list(analysis.assumptions)
    assumptions.append(
        "Gemini proposed a different category before the active category was complete, "
        "so SADify stayed in the active category.",
    )
    payload = analysis.model_dump()
    payload["next_question"] = replacement_question
    payload["assumptions"] = assumptions
    return RequirementAnalysisResponse.model_validate(payload)


def _fallback_requirement_analysis(
    request: RequirementAnalysisRequest,
    *,
    locked_target=None,
    prior_analysis: RequirementAnalysisResponse | None = None,
) -> RequirementAnalysisResponse:
    latest_question = _latest_previous_question(request.requirement_text)
    latest_answer = _latest_previous_answer(request.requirement_text)
    category_answers = _questionnaire_answers(request.requirement_text)
    answered_counts = _category_answer_counts(category_answers)
    latest_topic = _topic_from_question(latest_question)
    if _is_not_sure(latest_answer) and latest_topic["id"] != "fallback":
        topic = latest_topic
        question = _fallback_uncertainty_question(topic)
    elif locked_target is not None:
        return _fallback_requirement_analysis_for_slot(
            request, locked_target, prior_analysis=prior_analysis
        )
    elif _is_specific_fallback_question(latest_question) and latest_topic["id"] != "fallback":
        if answered_counts.get(latest_topic["id"], 0) >= FALLBACK_QUESTIONS_NEEDED:
            topic = _next_incomplete_topic(answered_counts, latest_topic["id"])
        else:
            topic = latest_topic
        question = _fallback_question(
            topic,
            answered_counts.get(topic["id"], 0),
            context_text=_combined_requirement_context(request),
        )
    else:
        topic = _fallback_topic(latest_answer)
        if topic["id"] == "fallback":
            topic = _infer_active_topic(request.requirement_text)
        question = _fallback_question(
            topic,
            answered_counts.get(topic["id"], 0),
            context_text=_combined_requirement_context(request),
        )
    source_references = list(request.source_references)
    if not source_references:
        source_references = ["Business Request"]
    assumptions = [
        "Fallback was used because Gemini returned invalid structured analysis after retry.",
        "Fallback readiness stays low until a validated Gemini response or SAD preview confirms more detail.",
    ]
    if _is_not_sure(latest_answer):
        assumptions.append(
            "User selected not sure, so SADify is asking an easier suggested-default question.",
        )

    legacy_categories = _legacy_categories_from_counts(answered_counts)
    analysis = RequirementAnalysisResponse(
        understanding_summary=(
            "SADify kept the business request and any answers already provided, "
            "but Gemini's latest structured question could not be validated. "
            "This local fallback keeps the flow usable while the next model "
            "question is retried later."
        ),
        readiness={
            "label": "Fallback question ready",
            "score": 35,
            "confidence": "Low",
        },
        categories=legacy_categories,
        next_question=question,
        assumptions=assumptions,
        source_references=source_references,
    )
    return _with_questionnaire_state(
        analysis, request, fallback_used=True, prior_analysis=prior_analysis
    )


def _fallback_requirement_analysis_for_slot(
    request: RequirementAnalysisRequest,
    locked_target: QuestionnairePlanSlotPointer,
    *,
    prior_analysis: RequirementAnalysisResponse | None = None,
) -> RequirementAnalysisResponse:
    source_references = list(request.source_references) or ["Business Request"]
    analysis = RequirementAnalysisResponse.model_validate(
        {
            "understanding_summary": (
                "SADify kept the business request and any answers already provided, "
                "but Gemini's latest structured question could not be validated. "
                "This local fallback keeps the flow inside the locked requirement slot."
            ),
            "readiness": {
                "label": "Fallback question ready",
                "score": 35,
                "confidence": "Low",
            },
            "categories": [
                {
                    "id": locked_target.category_id,
                    "label": _label_from_category_id(locked_target.category_id),
                    "status": "partial",
                }
            ],
            "next_question": fallback_question_for_slot(
                locked_target.category_id,
                locked_target.slot_id,
                context_text=_combined_requirement_context(request),
            ),
            "assumptions": [
                "Gemini output could not be validated, so a same-slot fallback was used."
            ],
            "source_references": source_references,
            "proposed_extra_categories": [],
        }
    )
    return _with_questionnaire_state(
        analysis, request, fallback_used=True, prior_analysis=prior_analysis
    )


def _validate_question_semantics(analysis: RequirementAnalysisResponse) -> None:
    target_category_id = _canonical_category_id(analysis.next_question.target_category)
    target_slot_id = analysis.next_question.target_slot_id
    joined_text = " ".join(
        [
            analysis.next_question.text,
            analysis.next_question.why_this_matters,
            *(choice.label for choice in analysis.next_question.choices),
        ]
    )
    target_score = semantic_score_for_slot(
        target_category_id,
        target_slot_id,
        joined_text,
    )
    best_slot, best_score = best_matching_slot(joined_text)
    if target_score <= 0:
        raise QuestionnaireDriftError(
            "Question semantics do not match the requested slot."
        )
    if best_slot is not None and best_slot != (target_category_id, target_slot_id):
        if best_score > target_score:
            raise QuestionnaireDriftError(
                "Question semantics fit a different slot better than the requested slot."
            )


def _latest_previous_answer(requirement_text: str) -> str:
    if "Previous answer:" not in requirement_text:
        return ""
    latest = requirement_text.rsplit("Previous answer:", 1)[-1].strip()
    return latest.splitlines()[0].strip()


def _latest_previous_question(requirement_text: str) -> str:
    if "Previous question:" not in requirement_text:
        return ""
    latest = requirement_text.rsplit("Previous question:", 1)[-1]
    return latest.split("Previous answer:", 1)[0].strip()


def _previous_readiness_score(requirement_text: str) -> int | None:
    marker = "Previous readiness:"
    if marker not in requirement_text:
        return None
    latest = requirement_text.rsplit(marker, 1)[-1].strip().splitlines()[0].strip()
    digits = "".join(character for character in latest if character.isdigit())
    if not digits:
        return None
    return max(0, min(100, int(digits)))


def _is_not_sure(answer: str) -> bool:
    return "not sure" in answer.lower() or "unsure" in answer.lower()


def _is_uncertainty_followup_question(question: str) -> bool:
    return question.startswith("Should SADify use a simple suggested default for ")


def _normalise_category_id(category_id: str) -> str:
    clean = "".join(
        character if character.isalnum() else "_"
        for character in category_id.strip().lower()
    )
    while "__" in clean:
        clean = clean.replace("__", "_")
    clean = clean.strip("_")
    aliases = {
        "users": "users_roles",
        "user_roles": "users_roles",
        "roles": "users_roles",
        "staff": "users_roles",
        "staff_roles": "users_roles",
        "workflow_steps": "workflow",
        "patient_flow": "workflow",
        "exceptions": "workflow",
        "edge_cases": "workflow",
        "data": "data_reports",
        "records": "data_reports",
        "reports": "data_reports",
        "reporting": "data_reports",
        "payment": "data_reports",
        "payments": "data_reports",
        "business_rules": "rules",
        "approvals": "rules",
        "business_rules_and_approvals": "rules",
    }
    return aliases.get(clean, clean or "fallback")


def _canonical_category_id(category_id: str) -> str:
    normalised = _normalise_category_id(category_id)
    return LEGACY_TO_CANONICAL_CATEGORY_IDS.get(normalised, normalised)


def _topic_by_id(category_id: str) -> dict[str, str]:
    normalised = _normalise_category_id(category_id)
    for topic in FALLBACK_CATEGORY_ORDER:
        if topic["id"] == normalised:
            return topic
    return {"id": normalised, "label": _label_from_category_id(normalised)}


def _legacy_topic_from_canonical(category_id: str) -> dict[str, str]:
    legacy_aliases = {
        "goal_scope": "users_roles",
        "workflow_steps": "workflow",
        "data_records": "data_reports",
        "rules_approvals": "rules",
    }
    return _topic_by_id(legacy_aliases.get(category_id, category_id))


def _label_from_category_id(category_id: str) -> str:
    return category_id.replace("_", " ").title()


def _questionnaire_answers(requirement_text: str) -> list[dict[str, object]]:
    answers: list[dict[str, object]] = []
    blocks = requirement_text.split("Previous question:")
    for block in blocks[1:]:
        question_text, _, answer_text = block.partition("Previous answer:")
        question = question_text.strip()
        answer = answer_text.strip().split("\n\n", 1)[0].strip()
        if not question or not answer:
            continue
        topic = _topic_from_question(question)
        if topic["id"] == "fallback":
            continue
        slot_id = _slot_marker(question)
        answers.append(
            {
                "category_id": _canonical_category_id(topic["id"]),
                "slot_id": slot_id or None,
                "question": _strip_question_markers(question),
                "answer": answer,
                "is_uncertain": _is_not_sure(answer),
            }
        )
    return answers


def _category_answer_counts(answers: list[dict[str, object]]) -> dict[str, int]:
    counted: dict[str, set[tuple[str, str]]] = {}
    for answer in answers:
        if answer.get("is_uncertain"):
            continue
        category_id = str(answer["category_id"])
        counted.setdefault(category_id, set()).add(
            (
                str(answer["question"]).strip().lower(),
                str(answer["answer"]).strip().lower(),
            )
        )
    return {
        category_id: min(len(unique_answers), FALLBACK_QUESTIONS_NEEDED)
        for category_id, unique_answers in counted.items()
    }


def _question_already_answered(
    question: str,
    category_id: str,
    slot_id: str,
    answers: list[dict[str, object]],
) -> bool:
    for answer in answers:
        if str(answer["category_id"]) != category_id:
            continue
        answer_slot_id = str(answer.get("slot_id") or "")
        if answer_slot_id and answer_slot_id != slot_id:
            continue
        if _questions_are_similar(question, str(answer["question"])):
            return True
    return False


def _questions_are_similar(left: str, right: str) -> bool:
    left_tokens = _question_tokens(left)
    right_tokens = _question_tokens(right)
    if not left_tokens or not right_tokens:
        return False
    shared = left_tokens & right_tokens
    return len(shared) / min(len(left_tokens), len(right_tokens)) >= 0.7


def _question_tokens(question: str) -> set[str]:
    stop_words = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "for",
        "how",
        "is",
        "it",
        "of",
        "or",
        "should",
        "system",
        "the",
        "this",
        "to",
        "what",
        "when",
        "which",
        "who",
        "why",
        "you",
        "your",
    }
    clean = "".join(
        character.lower() if character.isalnum() else " "
        for character in _strip_category_marker(question)
    )
    return {
        token
        for token in clean.split()
        if len(token) > 2 and token not in stop_words
    }


def _questionnaire_plan(
    verdicts: list,
    answers: list[dict[str, object]],
    *,
    prior_locked_categories: set[str] | None = None,
    prior_understood_via: dict[str, str] | None = None,
    default_new_provenance: str = "qa",
):
    plan = create_plan_from_evidence(
        verdicts,
        prior_locked_categories=prior_locked_categories,
        prior_understood_via=prior_understood_via,
        default_new_provenance=default_new_provenance,
    )
    for answer in _unique_questionnaire_answers(answers):
        if answer.get("is_uncertain"):
            category_id = str(answer["category_id"])
            slot = _slot_for_answer(plan, answer)
            if slot is not None:
                plan = defer_slot(plan, category_id, slot.id)
            continue

    # Guard B: anti-loop. If the same (category, slot) has been answered
    # 3+ times and still isn't covered, force-cover it. Stops the user
    # from being trapped on the same question forever when Gemini's
    # judgement keeps missing the slot.
    answer_counts: dict[tuple[str, str], int] = {}
    for answer in answers:
        slot_id = answer.get("slot_id")
        if not slot_id or answer.get("is_uncertain"):
            continue
        key = (str(answer["category_id"]), str(slot_id))
        answer_counts[key] = answer_counts.get(key, 0) + 1
    for (category_id, slot_id), count in answer_counts.items():
        if count < 3:
            continue
        try:
            slot = plan.category(category_id).slot(slot_id)
        except KeyError:
            continue
        if slot.status != "covered":
            plan = cover_slot(plan, category_id, slot_id)

    # Active category preference: stay where the user just answered if that
    # category still has open slots. Otherwise advance to the first open
    # category in plan order. Locked-ready categories are skipped either way.
    active_category_id = _active_category_from_answers(plan, answers)
    if active_category_id is None:
        open_slot = next_open_slot(plan)
        active_category_id = open_slot.category_id if open_slot else None
    return plan.model_copy(update={"active_category_id": active_category_id})


def _prior_locked_categories(
    prior_analysis: RequirementAnalysisResponse | None,
) -> set[str]:
    """Categories already cleared (Ready) in the previous saved turn.

    The ratchet carries these forward so a cleared category never re-opens
    no matter what the new turn's evidence says.
    """
    if prior_analysis is None or prior_analysis.questionnaire is None:
        return set()
    return {
        category.id
        for category in prior_analysis.questionnaire.categories
        if category.status == "ready"
    }


def _prior_understood_via(
    prior_analysis: RequirementAnalysisResponse | None,
) -> dict[str, str]:
    """Frozen bucket provenance from the previous saved turn.

    Reads it back off the prior visibility on the wire:
      already_understood → "source", completed → "qa". This lets the next
      turn keep each cleared category in the same bucket the user saw
      before, instead of letting carry-forward stamp everything "qa".
    """
    if prior_analysis is None or prior_analysis.questionnaire is None:
        return {}
    provenance: dict[str, str] = {}
    for category in prior_analysis.questionnaire.categories:
        if category.visibility == "already_understood":
            provenance[category.id] = "source"
        elif category.visibility == "completed":
            provenance[category.id] = "qa"
    return provenance


def _locked_target_for_request(
    request: RequirementAnalysisRequest,
    *,
    prior_analysis: RequirementAnalysisResponse | None = None,
):
    """Compute the slot the prompt should lock to BEFORE calling Gemini.

    Combines two signals so the lock matches what the post-hoc plan will
    compute (and the user sees Gemini's actual domain-aware question
    instead of a generic fallback):

    1. Carry-forward `slot_evidence` from the previous saved turn, merged
       under the monotonic rule (locked categories ratchet through).
    2. Answer-marker coverage from THIS request's Previous Q/A history,
       since Gemini hasn't yet judged those answers into slot_evidence
       for this turn.
    """
    prior_verdicts = (
        list(prior_analysis.slot_evidence)
        if prior_analysis is not None
        else []
    )
    answers = _questionnaire_answers(request.requirement_text)
    edited_slots = _edited_slot_keys(prior_analysis, answers)
    verdicts = merge_evidence(
        prior=prior_verdicts, new=[], edited_slots=edited_slots
    )
    locked = _prior_locked_categories(prior_analysis)
    prior_provenance = _prior_understood_via(prior_analysis)
    default_new_provenance = (
        "source" if prior_analysis is None and not answers else "qa"
    )
    plan = create_plan_from_evidence(
        verdicts,
        prior_locked_categories=locked,
        prior_understood_via=prior_provenance,
        default_new_provenance=default_new_provenance,
    )

    # Layer 2: answer-marker coverage. The user's submitted answers haven't
    # been judged into slot_evidence for THIS turn yet, so apply them
    # directly. Without this, the locked target ignores fresh answers and
    # the post-hoc rewrite kicks in.
    unique_answers = _unique_questionnaire_answers(answers)
    for answer in unique_answers:
        category_id = str(answer["category_id"])
        slot = _slot_for_answer(plan, answer)
        if slot is None:
            continue
        if answer.get("is_uncertain"):
            plan = defer_slot(plan, category_id, slot.id)
        else:
            plan = cover_slot(plan, category_id, slot.id)

    # Strict-order rule: stay in the category of the user's most recent
    # answer (if still not ready) instead of jumping back to an earlier
    # unanswered category. Combined with the ratchet, this gives the
    # "no revert, no pop-up" behavior the user asked for.
    active_category_id = _active_category_from_answers(plan, unique_answers)
    if active_category_id is not None:
        slot = _next_open_slot_in_category(plan, active_category_id)
        if slot is not None:
            return QuestionnairePlanSlotPointer(
                category_id=active_category_id,
                slot_id=slot.id,
            )

    open_slot = next_open_slot(plan)
    if open_slot is not None:
        return open_slot
    return _refinement_target_from_request(request, plan)


def _unique_questionnaire_answers(
    answers: list[dict[str, object]],
) -> list[dict[str, object]]:
    unique_answers: list[dict[str, object]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for answer in answers:
        key = (
            str(answer["category_id"]),
            str(answer.get("slot_id") or ""),
            str(answer["question"]).strip().lower(),
            str(answer["answer"]).strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique_answers.append(answer)
    return unique_answers


def _refinement_target_from_request(
    request: RequirementAnalysisRequest,
    plan,
) -> QuestionnairePlanSlotPointer | None:
    text = _combined_requirement_context(request).lower()
    if any(term in text for term in ("customer", "order", "orders", "booking", "bookings", "pickup", "payment status")):
        for category_id, slot_id in (
            ("exceptions_edges", "required_handling"),
            ("access_permissions", "override_handling"),
            ("non_functional", "audit_history"),
            ("rules_approvals", "approval_path"),
        ):
            try:
                slot = plan.category(category_id).slot(slot_id)
            except KeyError:
                continue
            if slot.status == "open":
                return QuestionnairePlanSlotPointer(
                    category_id=category_id,
                    slot_id=slot_id,
                )
    if any(term in text for term in ("tuition", "student", "parent", "fee", "attendance")):
        for category_id, slot_id in (
            ("exceptions_edges", "required_handling"),
            ("rules_approvals", "triggering_rules"),
            ("access_permissions", "sensitive_actions"),
            ("non_functional", "audit_history"),
        ):
            try:
                slot = plan.category(category_id).slot(slot_id)
            except KeyError:
                continue
            if slot.status == "open":
                return QuestionnairePlanSlotPointer(
                    category_id=category_id,
                    slot_id=slot_id,
                )
    if not ("workshop" in text or "maintenance request" in text):
        return None
    if "expensive" in text and "approval" in text:
        try:
            slot = plan.category("rules_approvals").slot("decision_authority")
        except KeyError:
            return None
        if slot.status == "open":
            return QuestionnairePlanSlotPointer(
                category_id="rules_approvals",
                slot_id="decision_authority",
            )
    return None


def _base_requirement_text(requirement_text: str) -> str:
    return requirement_text.split("Previous question:", 1)[0].strip()


def _combined_requirement_context(request: RequirementAnalysisRequest) -> str:
    parts = [_base_requirement_text(request.requirement_text)]
    if request.source_context:
        parts.append(request.source_context)
    return "\n".join(part for part in parts if part.strip())


def _active_category_from_answers(
    plan,
    answers: list[dict[str, object]],
) -> str | None:
    if not answers:
        return None
    latest_category_id = str(answers[-1]["category_id"])
    try:
        latest_category = plan.category(latest_category_id)
    except KeyError:
        return None
    if latest_category.status != "ready":
        return latest_category_id
    return None


def _next_open_slot_in_category(plan, category_id: str):
    try:
        category = plan.category(category_id)
    except KeyError:
        return None
    for slot in category.slots:
        if slot.required and slot.status == "open":
            return slot
    return None


def _slot_for_answer(plan, answer: dict[str, object]):
    category_id = str(answer["category_id"])
    explicit_slot_id = str(answer.get("slot_id") or "")
    if explicit_slot_id:
        try:
            return plan.category(category_id).slot(explicit_slot_id)
        except KeyError:
            return None
    return _next_open_slot_in_category(plan, category_id)


_STRENGTH_RANK = {"none": 0, "partial": 1, "strong": 2}


def _weakest_slot_strength(slots) -> str:
    """Return the weakest evidence strength among the given slots.

    A user-deferred ('confirm_later') slot is intentional and is treated as
    'strong' for the purpose of this signal — defer should not look like a
    missing-evidence gap to the SAD-preview gate.
    """
    strengths = [
        "strong" if slot.status == "confirm_later" else slot.evidence_strength
        for slot in slots
    ]
    if not strengths:
        return "strong"
    return min(strengths, key=lambda s: _STRENGTH_RANK.get(s, 2))


def _questionnaire_categories_from_plan(plan) -> list[dict[str, object]]:
    status_map = {
        "needs_answer": "needed",
        "in_progress": "in_progress",
        "ready": "ready",
        "confirm_later": "needs_later_confirmation",
    }
    categories: list[dict[str, object]] = []
    for category in sorted(plan.categories, key=lambda item: item.display_order):
        required_slots = [slot for slot in category.slots if slot.required]
        applicable_required = [slot for slot in required_slots if slot.applicable]
        covered_slots = [slot for slot in required_slots if slot.status == "covered"]
        # F3: per-category progress mirrors the global weighted score so the
        # headline % and the per-row % cannot contradict each other.
        progress = (
            round(
                100
                * sum(_slot_weight(slot) for slot in applicable_required)
                / len(applicable_required)
            )
            if applicable_required
            else 100
        )
        categories.append(
            {
                "id": category.id,
                "label": category.label,
                "status": status_map[category.status],
                "visibility": category.visibility,
                "progress": progress,
                "questions_total": len(required_slots),
                "questions_answered": len(covered_slots),
                "is_active": category.id == plan.active_category_id,
                "weakest_slot_strength": _weakest_slot_strength(applicable_required),
            }
        )
    return categories


def _active_slot_id(plan) -> str | None:
    if plan.active_category_id is None:
        return None
    slot = _next_open_slot_in_category(plan, plan.active_category_id)
    return slot.id if slot else None


def _active_slot_label(plan) -> str | None:
    if plan.active_category_id is None:
        return None
    slot = _next_open_slot_in_category(plan, plan.active_category_id)
    return slot.label if slot else None


def _active_slot_label_from_question(plan, analysis: RequirementAnalysisResponse) -> str | None:
    try:
        category = plan.category(analysis.next_question.target_category)
        return category.slot(analysis.next_question.target_slot_id).label
    except KeyError:
        return None


def _readiness_label(score: int) -> str:
    if score >= 90:
        return "Ready for draft"
    if score >= 70:
        return "Mostly ready"
    if score >= 40:
        return "In progress"
    return "Getting started"


def _legacy_categories_from_counts(
    answer_counts: dict[str, int],
) -> list[dict[str, str]]:
    categories: list[dict[str, str]] = []
    for topic in FALLBACK_CATEGORY_ORDER:
        count = answer_counts.get(topic["id"], 0)
        status = (
            "complete"
            if count >= FALLBACK_QUESTIONS_NEEDED
            else "partial"
            if count > 0
            else "missing"
        )
        categories.append(
            {
                "id": topic["id"],
                "label": topic["label"],
                "status": status,
            }
        )
    return categories


def _infer_active_topic(requirement_text: str) -> dict[str, str]:
    latest_answer = _latest_previous_answer(requirement_text)
    topic = _fallback_topic(latest_answer)
    if topic["id"] != "fallback":
        return topic
    text = requirement_text.lower()
    if any(keyword in text for keyword in ("approval", "approve", "rule")):
        return _topic_by_id("rules")
    if any(
        keyword in text
        for keyword in (
            "workflow",
            "process",
            "queue",
            "registration",
            "consultation",
            "medicine",
            "exception",
            "leave",
            "leaves",
            "skip",
        )
    ):
        return _topic_by_id("workflow")
    if any(keyword in text for keyword in ("data", "field", "report", "payment", "bill")):
        return _topic_by_id("data_reports")
    if any(keyword in text for keyword in ("user", "role", "staff", "doctor", "cashier")):
        return _topic_by_id("users_roles")
    return _topic_by_id("users_roles")


def _next_incomplete_topic(
    answer_counts: dict[str, int],
    current_category_id: str,
) -> dict[str, str]:
    topic_ids = [topic["id"] for topic in FALLBACK_CATEGORY_ORDER]
    if current_category_id in topic_ids:
        start = topic_ids.index(current_category_id) + 1
        ordered_ids = topic_ids[start:] + topic_ids[:start]
    else:
        ordered_ids = topic_ids
    for topic_id in ordered_ids:
        if answer_counts.get(topic_id, 0) < FALLBACK_QUESTIONS_NEEDED:
            return _topic_by_id(topic_id)
    return _topic_by_id(current_category_id)


def _fallback_topic(latest_answer: str) -> dict[str, str]:
    answer = latest_answer.lower()
    if any(keyword in answer for keyword in ("rule", "approval", "approvals")):
        return _topic_by_id("rules")
    if any(keyword in answer for keyword in ("data", "report", "field", "bill")):
        return _topic_by_id("data_reports")
    if any(keyword in answer for keyword in ("workflow", "step", "exception")):
        return _topic_by_id("workflow")
    if any(keyword in answer for keyword in ("user", "role", "staff")):
        return _topic_by_id("users_roles")
    return {"id": "fallback", "label": "Next clarification"}


def _topic_from_question(question: str) -> dict[str, str]:
    marker = _category_marker(question)
    if marker:
        return _topic_by_id(marker)
    text = question.lower()
    if (
        "workflow" in text
        or "exception" in text
        or "patient leaves" in text
        or "queue" in text
        or "medicine collection" in text
    ):
        return _topic_by_id("workflow")
    if "business rule" in text or "approval" in text:
        return _topic_by_id("rules")
    if "data" in text or "report" in text or "payment" in text or "bill" in text:
        return _topic_by_id("data_reports")
    if "staff access" in text or "role" in text or "users and staff roles" in text:
        return _topic_by_id("users_roles")
    return {"id": "fallback", "label": "Next clarification"}


def _category_marker(question: str) -> str:
    markers, _ = _question_markers(question)
    category_id = markers.get("category", "")
    return _normalise_category_id(category_id) if category_id else ""


def _slot_marker(question: str) -> str:
    markers, _ = _question_markers(question)
    return markers.get("slot", "")


def _strip_category_marker(question: str) -> str:
    return _strip_question_markers(question)


def _strip_question_markers(question: str) -> str:
    _, remainder = _question_markers(question)
    return remainder


def _question_markers(question: str) -> tuple[dict[str, str], str]:
    remaining = question.strip()
    markers: dict[str, str] = {}
    while remaining.startswith("["):
        marker_text, separator, remainder = remaining[1:].partition("]")
        if not separator or ":" not in marker_text:
            break
        marker_name, _, marker_value = marker_text.partition(":")
        marker_key = marker_name.strip().lower()
        if marker_key not in {"category", "slot"}:
            break
        markers[marker_key] = marker_value.strip()
        remaining = remainder.lstrip()
    return markers, remaining or question.strip()


def _is_specific_fallback_question(question: str) -> bool:
    return _topic_from_question(question)["id"] != "fallback"


def _answered_fallback_topics(requirement_text: str) -> set[str]:
    answered: set[str] = set()
    blocks = requirement_text.split("Previous question:")
    for block in blocks[1:]:
        question, _, answer = block.partition("Previous answer:")
        topic = _topic_from_question(question.strip())
        if topic["id"] != "fallback" and answer.strip() and not _is_not_sure(answer):
            answered.add(topic["id"])
    return answered


def _fallback_menu_question(answered_topics: set[str]) -> dict[str, object]:
    choices = [
        _menu_choice("users_roles", "Users and staff roles", answered_topics),
        _menu_choice("workflow", "Workflow steps and exceptions", answered_topics),
        _menu_choice("data_reports", "Data fields and reports", answered_topics),
        _menu_choice("rules", "Business rules and approvals", answered_topics),
        {"id": "not_sure", "label": "I'm not sure yet"},
    ]
    return {
        "text": "Which part should SADify clarify next before preparing the SAD?",
        "why_this_matters": (
            "Choosing the next focus keeps the analysis moving even when the "
            "model question refresh needs a retry."
        ),
        "choices": choices,
        "target_category": "fallback",
        "target_slot_id": "category_selection",
        "selection_mode": "single",
    }


def _menu_choice(
    choice_id: str,
    label: str,
    answered_topics: set[str],
) -> dict[str, object]:
    is_answered = choice_id in answered_topics
    return {
        "id": choice_id,
        "label": label,
        "is_disabled": is_answered,
        "status_label": "Answered locally" if is_answered else "",
    }


def _fallback_question(
    topic: dict[str, str],
    answered_count: int = 0,
    *,
    context_text: str = "",
) -> dict[str, object]:
    topic_id = topic["id"]
    if answered_count > 0:
        return _fallback_followup_question(topic)
    contextual_question = _contextual_legacy_fallback_question(topic_id, context_text)
    if contextual_question is not None:
        return contextual_question
    if topic_id == "rules":
        return {
            "text": "Which business rule should be confirmed first?",
            "why_this_matters": (
                "Clear rules prevent the workflow from closing in "
                "the wrong state."
            ),
            "choices": [
                {
                    "id": "complete_after_key_steps",
                    "label": "The record cannot be completed until key steps are done",
                },
                {
                    "id": "payment_before_close",
                    "label": "Payment status must be checked before closing",
                },
                {
                    "id": "manager_review",
                    "label": "Manager review is needed for unusual or unresolved cases",
                },
                {
                    "id": "staff_alert",
                    "label": "Staff should receive an alert when a rule is broken",
                },
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": "rules",
            "target_slot_id": "triggering_rules",
            "selection_mode": "single",
        }
    if topic_id == "data_reports":
        return {
            "text": "Which data or report detail should be confirmed first?",
            "why_this_matters": (
                "The SAD needs clear fields and report definitions before IT can "
                "design screens or database tables."
            ),
            "choices": [
                {"id": "record_fields", "label": "Core record fields"},
                {"id": "status_timestamps", "label": "Status and timestamp fields"},
                {"id": "staff_owner", "label": "Responsible staff or owner fields"},
                {"id": "payment_fields", "label": "Payment or amount fields"},
                {"id": "summary_report", "label": "Manager summary report fields"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": "data_reports",
            "target_slot_id": "main_records",
            "selection_mode": "multiple",
        }
    if topic_id == "workflow":
        return {
            "text": "Which workflow exception should be clarified first?",
            "why_this_matters": (
                "Exception handling decides what staff should do when the normal "
                "workflow is interrupted."
            ),
            "choices": [
                {"id": "skipped_step", "label": "A required step is skipped"},
                {"id": "unresolved_record", "label": "A record cannot be completed yet"},
                {"id": "status_change", "label": "A status changes unexpectedly"},
                {"id": "wrong_record", "label": "A duplicate or wrong record is entered"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": "workflow",
            "target_slot_id": "normal_flow",
            "selection_mode": "single",
        }
    if topic_id == "users_roles":
        return {
            "text": "Which staff access rule should be confirmed first?",
            "why_this_matters": (
                "Role access decides who can view, edit, approve, and report on "
                "operational records."
            ),
            "choices": [
                {"id": "frontline", "label": "Frontline staff can create and update records"},
                {"id": "fulfilment", "label": "Fulfilment staff can update work status"},
                {"id": "finance", "label": "Finance or counter staff can record payments"},
                {"id": "manager", "label": "Managers can view reports and review exceptions"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": "users_roles",
            "target_slot_id": "primary_users",
            "selection_mode": "multiple",
        }
    return _fallback_followup_question(_topic_by_id("users_roles"))


def _contextual_legacy_fallback_question(
    topic_id: str,
    context_text: str,
) -> dict[str, object] | None:
    lowered = context_text.lower()
    is_event_rental = any(
        term in lowered
        for term in (
            "event rental",
            "equipment booking",
            "equipment bookings",
            "rented items",
            "delivery schedule",
            "return status",
        )
    )
    is_service_order = is_event_rental or any(
        term in lowered
        for term in (
            "customer order",
            "customer orders",
            "booking order",
            "booking orders",
            "pickup",
            "payment status",
        )
    )
    if not is_service_order:
        return None

    if topic_id == "users_roles":
        return {
            "text": "Which staff access rule should be confirmed first?",
            "why_this_matters": (
                "Role access decides who can create bookings, update fulfilment, "
                "adjust payments or damages, and view reports."
            ),
            "choices": [
                {"id": "sales", "label": "Sales staff can create bookings and record customer details"},
                {"id": "warehouse", "label": "Warehouse staff can update item preparation and return status"},
                {"id": "drivers", "label": "Drivers can update delivery and pickup completion"},
                {"id": "owner", "label": "Owner can view reports and approve restricted adjustments"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": "users_roles",
            "target_slot_id": "primary_users",
            "selection_mode": "multiple",
        }
    if topic_id == "workflow":
        return {
            "text": "Which event rental exception should be clarified first?",
            "why_this_matters": (
                "Exception handling decides what staff should do when delivery, "
                "return, payment, or item status does not follow the normal flow."
            ),
            "choices": [
                {"id": "late_return", "label": "Items are returned late"},
                {"id": "damaged_missing", "label": "Items are damaged or missing"},
                {"id": "substituted_items", "label": "Rented items need substitution"},
                {"id": "payment_overdue", "label": "Payment is overdue"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": "workflow",
            "target_slot_id": "normal_flow",
            "selection_mode": "single",
        }
    if topic_id == "data_reports":
        return {
            "text": "Which booking, item, payment, or report detail should be confirmed first?",
            "why_this_matters": (
                "The SAD needs clear fields before IT can design booking, "
                "delivery, return, and reporting screens."
            ),
            "choices": [
                {"id": "booking_fields", "label": "Booking order and event details"},
                {"id": "item_status", "label": "Rented item delivery, return, and damage status"},
                {"id": "payment_fields", "label": "Deposit, balance due, and final payment fields"},
                {"id": "weekly_report", "label": "Owner weekly summary fields"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": "data_reports",
            "target_slot_id": "main_records",
            "selection_mode": "multiple",
        }
    if topic_id == "rules":
        return {
            "text": "Which event rental rule should be confirmed first?",
            "why_this_matters": (
                "Clear rules prevent bookings from closing before delivery, "
                "return, damage, and payment issues are handled."
            ),
            "choices": [
                {"id": "delivery_return_complete", "label": "Booking cannot close until delivery and return status are complete"},
                {"id": "payment_complete", "label": "Final payment or balance due must be checked before closing"},
                {"id": "damage_adjustment", "label": "Damage or payment adjustments need sales staff or owner control"},
                {"id": "customer_update", "label": "Customers should be updated for changed items or overdue payment"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": "rules",
            "target_slot_id": "triggering_rules",
            "selection_mode": "single",
        }
    return None


def _fallback_followup_question(topic: dict[str, str]) -> dict[str, object]:
    topic_id = topic["id"]
    if topic_id == "workflow":
        return {
            "text": "After this workflow exception happens, what should staff do next?",
            "why_this_matters": (
                "This turns the exception into an action IT can build into the "
                "screen, alert, or follow-up list."
            ),
            "choices": [
                {"id": "keep_open", "label": "Mark it incomplete and keep it open"},
                {"id": "alert_staff", "label": "Alert the responsible staff immediately"},
                {"id": "manual_follow_up", "label": "Allow manual follow-up later"},
                {"id": "close_flag_review", "label": "Close it but flag it for review"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": "workflow",
            "target_slot_id": "handoffs",
            "selection_mode": "single",
        }
    if topic_id == "users_roles":
        return {
            "text": "What should happen when staff need access outside their normal role?",
            "why_this_matters": (
                "This clarifies whether access exceptions are blocked, approved, "
                "or logged for review."
            ),
            "choices": [
                {"id": "manager_approval", "label": "Require manager approval"},
                {"id": "temporary_access", "label": "Allow temporary access with audit log"},
                {"id": "block_access", "label": "Block access outside the role"},
                {"id": "admin_only", "label": "Only an admin can change access"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": "users_roles",
            "target_slot_id": "responsibilities",
            "selection_mode": "single",
        }
    if topic_id == "data_reports":
        return {
            "text": "Which detail must appear in the first report or list?",
            "why_this_matters": (
                "The first report/list decides which fields must be captured "
                "from day one."
            ),
            "choices": [
                {"id": "status", "label": "Current status for each record"},
                {"id": "timestamps", "label": "Start and end timestamps"},
                {"id": "owner", "label": "Responsible staff or owner"},
                {"id": "amounts", "label": "Amounts, totals, or unpaid balance"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": "data_reports",
            "target_slot_id": "critical_fields",
            "selection_mode": "multiple",
        }
    if topic_id == "rules":
        return {
            "text": "Who should approve an exception or override?",
            "why_this_matters": (
                "Approval ownership prevents unclear responsibility when a normal "
                "rule cannot be followed."
            ),
            "choices": [
                {"id": "manager", "label": "Manager approves it"},
                {"id": "supervisor", "label": "Supervisor approves it"},
                {"id": "system_admin", "label": "System admin approves it"},
                {"id": "no_approval", "label": "No approval, only audit logging"},
                {"id": "not_sure", "label": "I'm not sure yet"},
                {"id": "other", "label": "Other / not listed"},
            ],
            "target_category": "rules",
            "target_slot_id": "approval_path",
            "selection_mode": "single",
        }
    return _fallback_followup_question(_topic_by_id("users_roles"))


def _fallback_uncertainty_question(topic: dict[str, str]) -> dict[str, object]:
    return {
        "text": f"Should SADify use a simple suggested default for {topic['label'].lower()}?",
        "why_this_matters": (
            "When you are not sure, SADify can either use a clearly marked "
            "assumption or leave the item open for later confirmation."
        ),
        "choices": [
            {"id": "yes", "label": "Yes, suggest a default and mark it as an assumption"},
            {"id": "no", "label": "No, keep this as an open question"},
            {"id": "other", "label": "Other / not listed"},
        ],
        "target_category": topic["id"],
        "target_slot_id": _fallback_slot_id(topic["id"], 0),
        "selection_mode": "single",
    }


def _fallback_slot_id(topic_id: str, answered_count: int) -> str:
    if topic_id == "rules":
        return "approval_path" if answered_count > 0 else "triggering_rules"
    if topic_id == "data_reports":
        return "critical_fields" if answered_count > 0 else "main_records"
    if topic_id == "workflow":
        return "handoffs" if answered_count > 0 else "normal_flow"
    return "responsibilities" if answered_count > 0 else "primary_users"
