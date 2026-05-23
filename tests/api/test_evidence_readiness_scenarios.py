import json

from fastapi.testclient import TestClient

from sadify_api.main import create_app
from sadify_api.services.analysis_state import RequirementAnalysisRepository
from sadify_api.services.gemini_structured import RequirementAnalysisModel
from sadify_api.services.questionnaire_plan import canonical_required_slots


EVIDENCE_ANCHOR = "scenario evidence"

BASE_PAYLOAD = {
    "understanding_summary": "Summary of the business request.",
    "readiness": {"label": "Getting started", "score": 30, "confidence": "Low"},
    "categories": [
        {"id": "goal_scope", "label": "Goal", "status": "partial"},
        {"id": "users_roles", "label": "Users", "status": "missing"},
    ],
    "next_question": {
        "text": "What should the system achieve?",
        "why_this_matters": "Clarifies scope.",
        "choices": [
            {"id": "a", "label": "Track work"},
            {"id": "b", "label": "Reduce errors"},
        ],
        "target_category": "goal_scope",
        "target_slot_id": "business_goal",
    },
    "assumptions": [],
    "source_references": [],
    "proposed_extra_categories": [],
}


class FakeModel(RequirementAnalysisModel):
    def __init__(self, payload):
        self._payload = payload

    def analyze_requirement(self, requirement_text, *, repair=False):
        return json.dumps(self._payload)


def _verdict(category_id, slot_id, strength, applicability="applicable"):
    return {
        "category_id": category_id,
        "slot_id": slot_id,
        "applicability": applicability,
        "strength": strength,
        "evidence_quote": EVIDENCE_ANCHOR if strength != "none" else "",
        "rationale": "scenario verdict",
    }


def _payload(verdicts):
    payload = json.loads(json.dumps(BASE_PAYLOAD))
    payload["slot_evidence"] = verdicts
    return payload


def _client(verdicts):
    model = FakeModel(_payload(verdicts))
    return TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=RequirementAnalysisRepository(),
        )
    )


def _readiness(verdicts, requirement_text):
    response = _client(verdicts).post(
        "/analysis/requirement",
        json={"requirement_text": f"{requirement_text}\n{EVIDENCE_ANCHOR}"},
    )
    assert response.status_code == 200
    return response.json()["analysis"]["questionnaire"]["draft_readiness"]


def test_scenario_1_vague_request_scores_low():
    readiness = _readiness([], "A shop wants a system to track things.")
    assert readiness["score"] <= 30
    assert readiness["confidence"] == "Low"


def test_scenario_2_rich_request_scores_medium_to_high():
    slots = canonical_required_slots()
    verdicts = [_verdict(c, s, "strong") for c, s, _ in slots[: len(slots) - 4]]
    verdicts += [_verdict(c, s, "partial") for c, s, _ in slots[len(slots) - 4 :]]
    readiness = _readiness(verdicts, "Rich multi-paragraph workshop request.")
    assert 60 <= readiness["score"] <= 95


def test_scenario_4_broad_answers_do_not_reach_full_readiness():
    slots = canonical_required_slots()
    verdicts = [_verdict(c, s, "partial") for c, s, _ in slots]
    readiness = _readiness(verdicts, "Request plus broad vague answers.")
    assert readiness["score"] < 100


def test_scenario_5_not_applicable_category_not_penalised():
    slots = canonical_required_slots()
    all_strong = [_verdict(c, s, "strong") for c, s, _ in slots]
    with_na = [
        _verdict(c, s, "strong")
        if c != "integrations"
        else _verdict(c, s, "none", "not_applicable")
        for c, s, _ in slots
    ]
    baseline = _readiness(all_strong, "Everything covered.")
    na_case = _readiness(with_na, "No integrations needed.")
    assert na_case["score"] >= baseline["score"] - 1
