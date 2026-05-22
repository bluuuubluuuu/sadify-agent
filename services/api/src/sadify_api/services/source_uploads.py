from datetime import UTC, datetime
from typing import Any

from sadify.extractors.business_files import ExtractedRequirementSource
from sadify_api.schemas import SourceRecord, TraceabilityUnit


MAX_PREVIEW_CHARACTERS = 220
MAX_CONTEXT_CHARACTERS_PER_SOURCE = 2400


class SourceRepository:
    def __init__(self) -> None:
        self._sources: dict[str, SourceRecord] = {}
        self._next_source_number = 1

    def save_extracted_source(
        self,
        *,
        extracted: ExtractedRequirementSource,
        mime_type: str | None,
        created_at: datetime | None = None,
    ) -> SourceRecord:
        source_id = f"SRC-{self._next_source_number:06d}"
        self._next_source_number += 1
        now = created_at or datetime.now(UTC)
        record = SourceRecord(
            source_id=source_id,
            source_item_id=f"{source_id}:file",
            source_type=extracted.file_type,
            original_file_name=extracted.filename,
            mime_type=mime_type,
            file_size_bytes=int(extracted.metadata.get("byte_count", 0)),
            extraction_status="extracted",
            extracted_text_preview=_preview(extracted.normalized_text),
            extracted_text=extracted.normalized_text,
            extraction_summary=_extraction_summary(extracted),
            traceability_units=_traceability_units(source_id, extracted),
            created_at=now,
            updated_at=now,
        )
        self._sources[source_id] = record
        return record

    def get_source(self, source_id: str) -> SourceRecord | None:
        return self._sources.get(source_id)


def build_source_analysis_context(sources: list[SourceRecord]) -> str:
    blocks: list[str] = []
    for source in sources:
        text = source.extracted_text.strip()
        if len(text) > MAX_CONTEXT_CHARACTERS_PER_SOURCE:
            text = f"{text[:MAX_CONTEXT_CHARACTERS_PER_SOURCE].rstrip()}..."
        blocks.append(
            "\n".join(
                [
                    f"[{source.source_id}] {source.original_file_name} "
                    f"({source.source_type})",
                    f"Summary: {source.extraction_summary}",
                    "Extracted text:",
                    text,
                ]
            )
        )
    return "\n\n".join(blocks)


def _preview(text: str) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= MAX_PREVIEW_CHARACTERS:
        return normalized
    return f"{normalized[:MAX_PREVIEW_CHARACTERS].rstrip()}..."


def _extraction_summary(extracted: ExtractedRequirementSource) -> str:
    metadata = extracted.metadata
    file_type = extracted.file_type
    if file_type in {"txt", "md"}:
        return f"{metadata.get('character_count', 0)} readable characters extracted."
    if file_type == "csv":
        columns = ", ".join(metadata.get("columns", []))
        return f"{metadata.get('row_count', 0)} data rows extracted. Columns: {columns}."
    if file_type == "xlsx":
        return f"{metadata.get('sheet_count', 0)} spreadsheet sheets extracted."
    if file_type == "pdf":
        return f"{metadata.get('page_count', 0)} PDF pages checked."
    if file_type == "docx":
        return (
            f"{metadata.get('paragraph_count', 0)} paragraphs and "
            f"{metadata.get('table_count', 0)} tables extracted."
        )
    return "Readable source text extracted."


def _traceability_units(
    source_id: str,
    extracted: ExtractedRequirementSource,
) -> list[TraceabilityUnit]:
    metadata = extracted.metadata
    file_type = extracted.file_type
    if file_type == "csv":
        return [
            TraceabilityUnit(
                unit_type="csv_columns",
                unit_name=f"{source_id}:columns",
                columns=list(metadata.get("columns", [])),
                metadata={"row_count": metadata.get("row_count", 0)},
            )
        ]
    if file_type == "xlsx":
        return [
            TraceabilityUnit(
                unit_type="xlsx_sheet",
                unit_name=str(sheet.get("name", "")),
                columns=list(sheet.get("columns", [])),
                metadata=_compact_metadata(
                    {
                        "row_count": sheet.get("row_count", 0),
                        "comment_count": sheet.get("comment_count", 0),
                    }
                ),
            )
            for sheet in metadata.get("sheets", [])
        ]
    if file_type == "pdf":
        return [
            TraceabilityUnit(
                unit_type="pdf_pages",
                unit_name=f"{source_id}:pages",
                metadata=_compact_metadata(
                    {
                        "page_count": metadata.get("page_count", 0),
                        "failed_pages": metadata.get("failed_pages", []),
                    }
                ),
            )
        ]
    if file_type == "docx":
        return [
            TraceabilityUnit(
                unit_type="docx_document",
                unit_name=f"{source_id}:document",
                metadata=_compact_metadata(
                    {
                        "paragraph_count": metadata.get("paragraph_count", 0),
                        "table_count": metadata.get("table_count", 0),
                        "table_row_count": metadata.get("table_row_count", 0),
                    }
                ),
            )
        ]
    return [
        TraceabilityUnit(
            unit_type="file",
            unit_name=f"{source_id}:file",
            metadata=_compact_metadata(
                {"character_count": metadata.get("character_count", 0)}
            ),
        )
    ]


def _compact_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in metadata.items() if value not in (None, "")}
