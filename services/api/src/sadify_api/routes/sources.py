from fastapi import APIRouter, File, HTTPException, UploadFile

from sadify.extractors.business_files import (
    FileExtractionError,
    extract_requirement_source,
)
from sadify_api.schemas import SourceUploadError, SourceUploadResponse
from sadify_api.services.source_uploads import (
    SourceRepository,
    build_source_analysis_context,
)


def create_sources_router(repository: SourceRepository) -> APIRouter:
    router = APIRouter(prefix="/sources", tags=["sources"])

    @router.post("/upload", response_model=SourceUploadResponse)
    async def upload_sources(
        files: list[UploadFile] = File(...),
    ) -> SourceUploadResponse:
        if not files:
            raise HTTPException(status_code=400, detail="At least one file is required.")

        sources = []
        errors: list[SourceUploadError] = []
        for uploaded_file in files:
            filename = uploaded_file.filename or "uploaded file"
            try:
                content = await uploaded_file.read()
                extracted = extract_requirement_source(filename, content)
            except FileExtractionError as exc:
                errors.append(
                    SourceUploadError(
                        filename=filename,
                        message=str(exc),
                    )
                )
                continue

            sources.append(
                repository.save_extracted_source(
                    extracted=extracted,
                    mime_type=uploaded_file.content_type,
                )
            )

        return SourceUploadResponse(
            sources=sources,
            errors=errors,
            analysis_context=build_source_analysis_context(sources),
        )

    return router
