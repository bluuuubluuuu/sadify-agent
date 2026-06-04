import logging
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from sadify_api.schemas import (
    RequirementAnalysisRecord,
    RequirementAnalysisRequest,
)
from sadify_api.services.analysis_state import RequirementAnalysisRepository
from sadify_api.services.gemini_structured import (
    RequirementAnalysisModel,
    parse_requirement_analysis,
)

logger = logging.getLogger("sadify_api.routes.analysis")

AnalysisTurnLogger = Callable[..., None]


class AnalysisModelError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail


def run_analysis_turn(
    *,
    request: RequirementAnalysisRequest,
    model: RequirementAnalysisModel,
    repository: RequirementAnalysisRepository,
    log_turn: AnalysisTurnLogger | None = None,
) -> RequirementAnalysisRecord:
    from sadify_api.routes import analysis as analysis_helpers

    prior_record = repository.latest_for_request(request)
    prior_analysis = prior_record.analysis if prior_record is not None else None
    locked_target = analysis_helpers._locked_target_for_request(
        request,
        prior_analysis=prior_analysis,
    )
    locked_categories = analysis_helpers._prior_locked_categories(prior_analysis)
    validation_errors: list[str] = []
    for repair in (False, True):
        raw_json = ""
        try:
            model_requirement_text = analysis_helpers._build_model_requirement_text(
                request,
                locked_target=locked_target,
            )
            raw_json = analysis_helpers._call_analysis_model(
                model,
                model_requirement_text,
                repair=repair,
                selected_model=request.model,
            )
            analysis = analysis_helpers._with_requested_source_references(
                parse_requirement_analysis(raw_json),
                request.source_references,
            )
            analysis_helpers._validate_model_analysis(
                analysis,
                locked_target=locked_target,
            )
            analysis = analysis_helpers._with_questionnaire_state(
                analysis,
                request,
                fallback_used=False,
                prior_analysis=prior_analysis,
            )
        except (ValidationError, analysis_helpers.QuestionnaireDriftError) as exc:
            validation_errors.append(
                f"repair={repair}:{type(exc).__name__}:{analysis_helpers._safe_exception_message(exc)[:120]}"
            )
            continue
        except Exception as exc:
            logger.exception(
                "sadify_turn analysis_call_failed repair=%s raw_len=%d",
                repair,
                len(raw_json),
            )
            raise AnalysisModelError(
                f"Gemini analysis failed: {analysis_helpers._safe_exception_message(exc)}"
            ) from exc

        record = repository.save_analysis(
            requirement_text=request.requirement_text,
            guest_draft_id=request.guest_draft_id,
            analysis_session_id=request.analysis_session_id,
            analysis=analysis,
        )
        _log_analysis_turn(
            log_turn=log_turn,
            record=record,
            source="gemini",
            prior=prior_record,
            locked_categories=locked_categories,
            validation_errors=validation_errors,
        )
        return record

    fallback_analysis = analysis_helpers._fallback_requirement_analysis(
        request,
        locked_target=locked_target,
        prior_analysis=prior_analysis,
    )
    record = repository.save_analysis(
        requirement_text=request.requirement_text,
        guest_draft_id=request.guest_draft_id,
        analysis_session_id=request.analysis_session_id,
        analysis=fallback_analysis,
    )
    _log_analysis_turn(
        log_turn=log_turn,
        record=record,
        source="fallback",
        prior=prior_record,
        locked_categories=locked_categories,
        validation_errors=validation_errors,
    )
    return record


def _log_analysis_turn(
    *,
    log_turn: AnalysisTurnLogger | None,
    record: RequirementAnalysisRecord,
    source: str,
    prior: Any,
    locked_categories: set[str],
    validation_errors: list[str],
) -> None:
    if log_turn is None:
        return
    log_turn(
        record=record,
        source=source,
        prior=prior,
        locked_categories=locked_categories,
        validation_errors=validation_errors,
    )
