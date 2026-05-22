import json

from fastapi.testclient import TestClient

from sadify_api.main import create_app
from sadify_api.services.analysis_state import RequirementAnalysisRepository
from sadify_api.services.gemini_structured import RequirementAnalysisModel
from sadify_api.services.source_uploads import SourceRepository


VALID_ANALYSIS_PAYLOAD = {
    "understanding_summary": "The source describes a workflow that needs clearer tracking.",
    "readiness": {
        "label": "Enough to ask the next question",
        "score": 45,
        "confidence": "Medium",
    },
    "categories": [
        {"id": "goal_scope", "label": "Goal and scope", "status": "partial"},
    ],
    "next_question": {
        "text": "What main result should this system help the business achieve?",
        "why_this_matters": "This gives the SAD a clear business goal.",
        "choices": [
            {"id": "reduce_delay", "label": "Reduce delays"},
            {"id": "reduce_errors", "label": "Reduce errors"},
            {"id": "not_sure", "label": "I'm not sure yet"},
        ],
        "target_category": "goal_scope",
        "target_slot_id": "business_goal",
    },
    "assumptions": [],
    "source_references": [],
    "proposed_extra_categories": [],
}


class CapturingAnalysisModel(RequirementAnalysisModel):
    def __init__(self) -> None:
        self.requests: list[tuple[str, bool]] = []

    def analyze_requirement(self, requirement_text: str, *, repair: bool = False) -> str:
        self.requests.append((requirement_text, repair))
        return json.dumps(VALID_ANALYSIS_PAYLOAD)


def test_source_upload_api_extracts_text_and_returns_traceability_metadata():
    repository = SourceRepository()
    client = TestClient(create_app(source_repository=repository))

    response = client.post(
        "/sources/upload",
        files=[
            (
                "files",
                (
                    "warehouse-flow.txt",
                    b"Operators scan item codes before dispatch.",
                    "text/plain",
                ),
            ),
            (
                "files",
                (
                    "stock.csv",
                    b"sku,status\nA-1,received\nB-2,packed\n",
                    "text/csv",
                ),
            ),
        ],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["errors"] == []
    assert [source["source_id"] for source in payload["sources"]] == [
        "SRC-000001",
        "SRC-000002",
    ]
    assert payload["sources"][0]["source_item_id"] == "SRC-000001:file"
    assert payload["sources"][0]["source_type"] == "txt"
    assert payload["sources"][0]["original_file_name"] == "warehouse-flow.txt"
    assert payload["sources"][0]["extraction_status"] == "extracted"
    assert "Operators scan item codes" in payload["sources"][0]["extracted_text_preview"]
    assert payload["sources"][1]["traceability_units"][0]["unit_type"] == "csv_columns"
    assert payload["sources"][1]["traceability_units"][0]["columns"] == [
        "sku",
        "status",
    ]
    assert "[SRC-000001]" in payload["analysis_context"]
    assert "Operators scan item codes" in payload["analysis_context"]
    assert repository.get_source("SRC-000001") is not None


def test_source_upload_api_reports_unsupported_files_without_losing_valid_sources():
    client = TestClient(create_app(source_repository=SourceRepository()))

    response = client.post(
        "/sources/upload",
        files=[
            (
                "files",
                (
                    "workflow.txt",
                    b"Keep audit history for every movement.",
                    "text/plain",
                ),
            ),
            (
                "files",
                (
                    "diagram.png",
                    b"not a supported source",
                    "image/png",
                ),
            ),
        ],
    )

    assert response.status_code == 200
    payload = response.json()
    assert [source["original_file_name"] for source in payload["sources"]] == [
        "workflow.txt"
    ]
    assert payload["errors"][0]["filename"] == "diagram.png"
    assert "Supported files" in payload["errors"][0]["message"]


def test_analysis_api_accepts_source_context_and_keeps_source_references_traceable():
    repository = RequirementAnalysisRepository()
    model = CapturingAnalysisModel()
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=repository,
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": "Need a warehouse component system.",
            "source_context": "[SRC-000001] workflow.txt\nOperators scan item codes.",
            "source_references": ["SRC-000001"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis"]["source_references"] == ["SRC-000001"]
    assert repository.get_analysis("AN-000001").analysis.source_references == [
        "SRC-000001"
    ]
    assert len(model.requests) == 1
    request_text, repair = model.requests[0]
    assert repair is False
    assert "Need a warehouse component system." in request_text
    assert "Uploaded source context:" in request_text
    assert "[SRC-000001] workflow.txt" in request_text
    assert "Operators scan item codes." in request_text
    assert "Locked questionnaire target:" in request_text
    assert "active_category_id: goal_scope" in request_text
    assert "target_slot_id: business_goal" in request_text
