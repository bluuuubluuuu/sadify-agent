from datetime import UTC, datetime

from sadify_api.schemas import (
    RequirementAnalysisRecord,
    RequirementAnalysisRequest,
    RequirementAnalysisResponse,
)


def _base_requirement_text(requirement_text: str) -> str:
    """The immutable prompt from before any 'Previous question:' append.

    All turns inside one session share this prefix, so it is a stable session
    key when no guest_draft_id is available (signed-in flow).
    """
    return requirement_text.split("Previous question:", 1)[0].strip()


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
        analysis_session_id: str | None = None,
        created_at: datetime | None = None,
    ) -> RequirementAnalysisRecord:
        analysis_id = f"AN-{self._next_analysis_number:06d}"
        self._next_analysis_number += 1
        record = RequirementAnalysisRecord(
            analysis_id=analysis_id,
            guest_draft_id=guest_draft_id,
            analysis_session_id=analysis_session_id,
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
        """Return the most recently saved analysis for this guest draft."""
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

    def latest_for_session(
        self, session_id: str | None
    ) -> RequirementAnalysisRecord | None:
        """Return the most recently saved analysis for this explicit session."""
        if not session_id:
            return None
        records = [
            record
            for record in self._analyses.values()
            if record.analysis_session_id == session_id
        ]
        if not records:
            return None
        return max(records, key=lambda record: record.created_at)

    def latest_for_request(
        self, request: RequirementAnalysisRequest
    ) -> RequirementAnalysisRecord | None:
        """Find the most recent analysis for this session.

        Priority:
          1. explicit analysis_session_id (frontend-owned reset boundary);
          2. explicit guest_draft_id (guest flow);
          3. matching base requirement text (legacy signed-in flow, where the request
             carries no draft id but the base prompt is stable across turns).

        Used by /analysis/requirement to carry slot_evidence forward across
        turns, so readiness does not regress on model flicker or fallback.
        """
        if request.analysis_session_id:
            return self.latest_for_session(request.analysis_session_id)
        by_draft = self.latest_for_guest_draft(request.guest_draft_id)
        if by_draft is not None:
            return by_draft
        base = _base_requirement_text(request.requirement_text)
        if not base:
            return None
        matches = [
            record
            for record in self._analyses.values()
            if _base_requirement_text(record.requirement_text) == base
        ]
        if not matches:
            return None
        return max(matches, key=lambda record: record.created_at)
