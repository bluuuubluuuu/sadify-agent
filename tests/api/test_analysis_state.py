"""Repository carry-forward lookup tests.

Signed-in flow has no guest_draft_id; the route still needs to find the prior
analysis to carry slot evidence forward. The fallback is base-requirement-text
matching: turns inside the same session share the immutable original prompt
(everything before the first 'Previous question:' marker).
"""

from datetime import UTC, datetime

from sadify_api.schemas import (
    RequirementAnalysisRequest,
    RequirementAnalysisResponse,
)
from sadify_api.services.analysis_state import RequirementAnalysisRepository


def _minimal_analysis() -> RequirementAnalysisResponse:
    return RequirementAnalysisResponse.model_validate(
        {
            "understanding_summary": "stub",
            "readiness": {
                "label": "Getting started",
                "score": 0,
                "confidence": "Low",
            },
            "categories": [
                {"id": "goal_scope", "label": "Goal", "status": "missing"}
            ],
            "next_question": {
                "text": "What is the goal?",
                "why_this_matters": "Clarifies the goal.",
                "choices": [
                    {"id": "a", "label": "x"},
                    {"id": "b", "label": "y"},
                ],
                "target_category": "goal_scope",
                "target_slot_id": "business_goal",
            },
            "assumptions": [],
            "source_references": [],
        }
    )


def test_latest_for_request_finds_prior_via_base_text_when_no_guest_draft_id():
    """Signed-in turns share base text; the lookup must match on it."""
    base = "A small laundry shop needs a system to track orders."
    repo = RequirementAnalysisRepository()
    saved = repo.save_analysis(
        requirement_text=base,
        guest_draft_id=None,
        analysis=_minimal_analysis(),
        created_at=datetime.now(UTC),
    )

    turn2 = RequirementAnalysisRequest(
        requirement_text=(
            f"{base}\n\n"
            "Previous question: [category: goal_scope][slot: business_goal] x?\n"
            "Previous answer: track orders end to end"
        )
    )
    found = repo.latest_for_request(turn2)
    assert found is not None
    assert found.analysis_id == saved.analysis_id


def test_latest_for_request_does_not_match_different_base_text():
    repo = RequirementAnalysisRepository()
    repo.save_analysis(
        requirement_text="Bakery custom cake orders system.",
        analysis=_minimal_analysis(),
    )
    other = RequirementAnalysisRequest(
        requirement_text="Workshop maintenance request tracking."
    )
    assert repo.latest_for_request(other) is None


def test_latest_for_request_prefers_guest_draft_match_over_base_text():
    """When both keys would match, the explicit guest_draft_id wins."""
    repo = RequirementAnalysisRepository()
    repo.save_analysis(
        requirement_text="Shared base text for two drafts.",
        guest_draft_id="g-other",
        analysis=_minimal_analysis(),
    )
    target = repo.save_analysis(
        requirement_text="Shared base text for two drafts.",
        guest_draft_id="g-mine",
        analysis=_minimal_analysis(),
    )
    request = RequirementAnalysisRequest(
        requirement_text="Shared base text for two drafts.",
        guest_draft_id="g-mine",
    )
    found = repo.latest_for_request(request)
    assert found is not None
    assert found.analysis_id == target.analysis_id


def test_latest_for_request_returns_most_recent_on_multiple_matches():
    base = "A team needs an analyzer."
    repo = RequirementAnalysisRepository()
    older = repo.save_analysis(
        requirement_text=base,
        analysis=_minimal_analysis(),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    newer = repo.save_analysis(
        requirement_text=base,
        analysis=_minimal_analysis(),
        created_at=datetime(2026, 6, 1, tzinfo=UTC),
    )
    found = repo.latest_for_request(
        RequirementAnalysisRequest(requirement_text=base)
    )
    assert found is not None
    assert found.analysis_id == newer.analysis_id
    assert found.analysis_id != older.analysis_id
