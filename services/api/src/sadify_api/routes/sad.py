import logging

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

logger = logging.getLogger(__name__)

from sadify_api.schemas import (
    SadPreviewApiResponse,
    SadPreviewRequest,
)
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


def create_sad_router(
    model: SadPreviewModel,
    repository: SadPreviewRepository,
) -> APIRouter:
    router = APIRouter(prefix="/sad", tags=["sad"])

    @router.post("/preview", response_model=SadPreviewApiResponse)
    def generate_preview(request: SadPreviewRequest) -> SadPreviewApiResponse:
        clean_request = clean_business_request(request.requirement_text)
        missing_basics = missing_blocking_basics(
            request.analysis,
            requirement_text=clean_request,
            source_context=request.source_context,
        )
        if missing_basics:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Answer the blocking basics before generating a SAD preview.",
                    "missing_basics": missing_basics,
                },
            )

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
                raw_json = model.generate_preview(context, repair=repair)
                preview = with_requested_source_references(
                    parse_sad_preview(raw_json),
                    request.source_references,
                )
            except ValidationError as exc:
                logger.warning(
                    "sad_preview_validation_failed repair=%s err=%s raw_len=%d raw_head=%r raw_tail=%r",
                    repair,
                    f"{type(exc).__name__}: {str(exc)[:500]}",
                    len(raw_json),
                    raw_json[:600],
                    raw_json[-400:] if len(raw_json) > 1000 else "",
                )
                continue
            except Exception as exc:
                logger.exception(
                    "sad_preview_call_failed repair=%s raw_len=%d", repair, len(raw_json)
                )
                raise HTTPException(
                    status_code=502,
                    detail="Gemini SAD preview failed.",
                ) from exc

            record = repository.save_preview(
                requirement_text=clean_request,
                analysis_id=request.analysis_id,
                preview=preview,
            )
            return SadPreviewApiResponse(
                preview_id=record.preview_id,
                saved=True,
                preview=record.preview,
            )

        fallback_preview = build_safe_sad_fallback_preview(
            requirement_text=clean_request,
            analysis=request.analysis,
            source_references=request.source_references,
        )
        record = repository.save_preview(
            requirement_text=clean_request,
            analysis_id=request.analysis_id,
            preview=fallback_preview,
        )
        return SadPreviewApiResponse(
            preview_id=record.preview_id,
            saved=True,
            preview=record.preview,
        )

    return router
