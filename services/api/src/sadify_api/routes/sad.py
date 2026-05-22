from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

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
            try:
                preview = with_requested_source_references(
                    parse_sad_preview(model.generate_preview(context, repair=repair)),
                    request.source_references,
                )
            except ValidationError:
                continue
            except Exception as exc:
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
