from datetime import UTC, datetime

from sadify_api.schemas import (
    RequirementAnalysisRecord,
    RequirementAnalysisResponse,
)


class RequirementAnalysisRepository:
    def __init__(self) -> None:
        self._analyses: dict[str, RequirementAnalysisRecord] = {}
        self._next_analysis_number = 1

    def save_analysis(
        self,
        *,
        requirement_text: str,
        analysis: RequirementAnalysisResponse,
        guest_draft_id: str | None = None,
        created_at: datetime | None = None,
    ) -> RequirementAnalysisRecord:
        analysis_id = f"AN-{self._next_analysis_number:06d}"
        self._next_analysis_number += 1
        record = RequirementAnalysisRecord(
            analysis_id=analysis_id,
            guest_draft_id=guest_draft_id,
            requirement_text=requirement_text,
            analysis=analysis,
            created_at=created_at or datetime.now(UTC),
        )
        self._analyses[analysis_id] = record
        return record

    def get_analysis(self, analysis_id: str) -> RequirementAnalysisRecord | None:
        return self._analyses.get(analysis_id)
