import logging

from pydantic import ValidationError

from sadify_api.schemas import SadPreviewRecord, SadPreviewRequest
from sadify_api.services.gemini_structured import (
    SadPreviewModel,
    parse_sad_preview,
)
from sadify_api.services.sad_preview import (
    SadPreviewRepository,
    build_safe_sad_fallback_preview,
    build_sad_preview_context,
    missing_blocking_basics,
    with_requested_source_references,
)
from sadify_api.services.sad_synthesis import clean_business_request

logger = logging.getLogger("sadify_api.routes.sad")


class SadPreviewBlockedError(Exception):
    def __init__(self, missing_basics: list[str]) -> None:
        self.missing_basics = missing_basics


class SadPreviewModelError(Exception):
    """Raised when Gemini fails non-validation during SAD preview generation."""


def run_sad_preview(
    *,
    request: SadPreviewRequest,
    model: SadPreviewModel,
    repository: SadPreviewRepository,
) -> SadPreviewRecord:
    clean_request = clean_business_request(request.requirement_text)
    missing_basics = missing_blocking_basics(
        request.analysis,
        requirement_text=clean_request,
        source_context=request.source_context,
    )
    if missing_basics:
        raise SadPreviewBlockedError(missing_basics)

    context = build_sad_preview_context(
        requirement_text=clean_request,
        analysis_id=request.analysis_id,
        analysis=request.analysis,
        source_context=request.source_context,
        source_references=request.source_references,
    )
    for repair in (False, True):
        raw_json = ""
        try:
            raw_json = _call_sad_preview_model(
                model,
                context,
                repair=repair,
                selected_model=request.model,
            )
            preview = with_requested_source_references(
                parse_sad_preview(raw_json),
                request.source_references,
            )
        except ValidationError as exc:
            logger.warning(
                "sadify_preview validation_failed repair=%s err=%s raw_len=%d",
                repair,
                f"{type(exc).__name__}:{str(exc)[:120]}",
                len(raw_json),
            )
            continue
        except Exception as exc:
            logger.exception(
                "sadify_preview call_failed repair=%s raw_len=%d",
                repair,
                len(raw_json),
            )
            raise SadPreviewModelError("Gemini SAD preview failed.") from exc

        return repository.save_preview(
            requirement_text=clean_request,
            analysis_id=request.analysis_id,
            preview=preview,
        )

    fallback_preview = build_safe_sad_fallback_preview(
        requirement_text=clean_request,
        analysis=request.analysis,
        source_references=request.source_references,
    )
    return repository.save_preview(
        requirement_text=clean_request,
        analysis_id=request.analysis_id,
        preview=fallback_preview,
    )


def _call_sad_preview_model(
    model: SadPreviewModel,
    context: str,
    *,
    repair: bool,
    selected_model: str | None,
) -> str:
    if selected_model:
        return model.generate_preview(
            context,
            repair=repair,
            model=selected_model,
        )

    return model.generate_preview(context, repair=repair)
