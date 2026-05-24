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

    def latest_for_guest_draft(
        self, guest_draft_id: str | None
    ) -> RequirementAnalysisRecord | None:
        """Return the most recently saved analysis for this guest draft.

        Used by the analysis route to carry forward prior slot_evidence across
        turns so readiness does not regress between calls.
        """
        if not guest_draft_id:
            return None
        records = [
            record
            for record in self._analyses.values()
            if record.guest_draft_id == guest_draft_id
        ]
        if not records:
            return None
        return max(records, key=lambda record: record.created_at)
