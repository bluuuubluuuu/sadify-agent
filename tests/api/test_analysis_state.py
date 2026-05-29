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


def test_latest_for_session_returns_none_when_no_session_records():
    repo = RequirementAnalysisRepository()
    repo.save_analysis(
        requirement_text="Analyze",
        analysis=_minimal_analysis(),
        analysis_session_id="session-other",
    )

    assert repo.latest_for_session("session-missing") is None
    assert repo.latest_for_session("") is None


def test_latest_for_session_returns_most_recent_matching_session():
    repo = RequirementAnalysisRepository()
    older = repo.save_analysis(
        requirement_text="Analyze",
        analysis=_minimal_analysis(),
        analysis_session_id="session-a",
        created_at=datetime(2026, 5, 29, 8, 0, tzinfo=UTC),
    )
    newer = repo.save_analysis(
        requirement_text="Analyze",
        analysis=_minimal_analysis(),
        analysis_session_id="session-a",
        created_at=datetime(2026, 5, 29, 9, 0, tzinfo=UTC),
    )
    repo.save_analysis(
        requirement_text="Analyze",
        analysis=_minimal_analysis(),
        analysis_session_id="session-b",
        created_at=datetime(2026, 5, 29, 10, 0, tzinfo=UTC),
    )

    found = repo.latest_for_session("session-a")

    assert found is not None
    assert found.analysis_id == newer.analysis_id
    assert found.analysis_id != older.analysis_id


def test_latest_for_request_prefers_session_id_over_base_text():
    repo = RequirementAnalysisRepository()
    target = repo.save_analysis(
        requirement_text="Analyze",
        analysis=_minimal_analysis(),
        analysis_session_id="session-target",
        created_at=datetime(2026, 5, 29, 8, 0, tzinfo=UTC),
    )
    base_text_match = repo.save_analysis(
        requirement_text="Analyze",
        analysis=_minimal_analysis(),
        analysis_session_id="session-other",
        created_at=datetime(2026, 5, 29, 9, 0, tzinfo=UTC),
    )

    found = repo.latest_for_request(
        RequirementAnalysisRequest(
            requirement_text="Analyze",
            analysis_session_id="session-target",
        )
    )

    assert found is not None
    assert found.analysis_id == target.analysis_id
    assert found.analysis_id != base_text_match.analysis_id


def test_latest_for_request_different_session_ids_do_not_collide():
    repo = RequirementAnalysisRepository()
    first = repo.save_analysis(
        requirement_text="Analyze",
        analysis=_minimal_analysis(),
        analysis_session_id="session-grooming",
        created_at=datetime(2026, 5, 29, 8, 0, tzinfo=UTC),
    )
    second = repo.save_analysis(
        requirement_text="Analyze",
        analysis=_minimal_analysis(),
        analysis_session_id="session-catering",
        created_at=datetime(2026, 5, 29, 9, 0, tzinfo=UTC),
    )

    found_first = repo.latest_for_request(
        RequirementAnalysisRequest(
            requirement_text="Analyze",
            analysis_session_id="session-grooming",
        )
    )
    found_second = repo.latest_for_request(
        RequirementAnalysisRequest(
            requirement_text="Analyze",
            analysis_session_id="session-catering",
        )
    )
    found_fresh = repo.latest_for_request(
        RequirementAnalysisRequest(
            requirement_text="Analyze",
            analysis_session_id="session-new-source",
        )
    )

    assert found_first is not None
    assert found_first.analysis_id == first.analysis_id
    assert found_second is not None
    assert found_second.analysis_id == second.analysis_id
    assert found_fresh is None


def test_latest_for_request_same_session_id_carries_forward():
    repo = RequirementAnalysisRepository()
    saved = repo.save_analysis(
        requirement_text="Analyze",
        analysis=_minimal_analysis(),
        analysis_session_id="session-a",
    )

    found = repo.latest_for_request(
        RequirementAnalysisRequest(
            requirement_text=(
                "Analyze\n\n"
                "Previous question: [category: goal_scope][slot: business_goal] x?\n"
                "Previous answer: track orders end to end"
            ),
            analysis_session_id="session-a",
        )
    )

    assert found is not None
    assert found.analysis_id == saved.analysis_id


def test_latest_for_request_falls_back_to_base_text_when_no_session_id():
    repo = RequirementAnalysisRepository()
    saved = repo.save_analysis(
        requirement_text="Analyze",
        analysis=_minimal_analysis(),
    )

    found = repo.latest_for_request(
        RequirementAnalysisRequest(requirement_text="Analyze")
    )

    assert found is not None
    assert found.analysis_id == saved.analysis_id


def test_latest_for_request_falls_back_to_guest_draft_when_no_session_id():
    repo = RequirementAnalysisRepository()
    target = repo.save_analysis(
        requirement_text="Analyze",
        guest_draft_id="guest-target",
        analysis=_minimal_analysis(),
    )
    base_match = repo.save_analysis(
        requirement_text="Analyze",
        guest_draft_id="guest-other",
        analysis=_minimal_analysis(),
        created_at=datetime(2026, 5, 29, 9, 0, tzinfo=UTC),
    )

    found = repo.latest_for_request(
        RequirementAnalysisRequest(
            requirement_text="Analyze",
            guest_draft_id="guest-target",
        )
    )

    assert found is not None
    assert found.analysis_id == target.analysis_id
    assert found.analysis_id != base_match.analysis_id
