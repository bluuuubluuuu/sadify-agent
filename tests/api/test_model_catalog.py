import json

from fastapi.testclient import TestClient

from sadify_api.config import ApiConfig
from sadify_api.main import create_app
from sadify_api.services.model_catalog import (
    DEFAULT_GEMINI_MODEL,
    GEMINI_MODEL_CATALOG,
    backend_default_model,
    list_gemini_models,
    resolve_gemini_model,
)
from tests.api.test_gemini_structured import VALID_PAYLOAD
from tests.api.test_sad_preview import VALID_PREVIEW, _analysis_with_blocking_basics


class CapturingRequirementAnalysisModel:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def analyze_requirement(
        self,
        requirement_text: str,
        *,
        repair: bool = False,
        model: str | None = None,
    ) -> str:
        self.calls.append(
            {
                "requirement_text": requirement_text,
                "repair": repair,
                "model": model,
            }
        )
        payload = json.loads(json.dumps(VALID_PAYLOAD))
        payload.setdefault("slot_evidence", [])
        return json.dumps(payload)


class CapturingSadPreviewModel:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_preview(
        self,
        context: str,
        *,
        repair: bool = False,
        model: str | None = None,
    ) -> str:
        self.calls.append(
            {
                "context": context,
                "repair": repair,
                "model": model,
            }
        )
        return json.dumps(json.loads(json.dumps(VALID_PREVIEW)))


def test_gemini_allowlist_contains_supported_model_ids():
    assert tuple(item["id"] for item in GEMINI_MODEL_CATALOG) == (
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.5-flash-lite",
    )
    assert all(item["id"].startswith("gemini-") for item in GEMINI_MODEL_CATALOG)
    assert DEFAULT_GEMINI_MODEL == "gemini-2.5-flash"


def test_config_default_model_is_used_when_allowlisted():
    config = ApiConfig(environment="test", sadify_model="gemini-2.5-pro")

    assert backend_default_model(config) == "gemini-2.5-pro"
    assert resolve_gemini_model(None, config) == "gemini-2.5-pro"


def test_invalid_config_default_falls_back_to_backend_default():
    config = ApiConfig(environment="test", sadify_model="gemini-not-real")

    assert backend_default_model(config) == "gemini-2.5-flash"
    assert resolve_gemini_model(None, config) == "gemini-2.5-flash"
    assert resolve_gemini_model("gemini-not-real", config) == "gemini-2.5-flash"
    assert resolve_gemini_model("", config) == "gemini-2.5-flash"


def test_list_gemini_models_marks_default_and_includes_pro_hint():
    response = list_gemini_models(
        ApiConfig(environment="test", sadify_model="gemini-2.5-pro")
    )

    assert response.default == "gemini-2.5-pro"
    assert [model.id for model in response.models] == [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.5-flash-lite",
    ]
    pro_model = next(model for model in response.models if model.id == "gemini-2.5-pro")
    assert pro_model.hint == "slower, higher quality"


def test_get_models_returns_gemini_catalog():
    client = TestClient(
        create_app(ApiConfig(environment="test", sadify_model="gemini-2.5-pro"))
    )

    response = client.get("/models")

    assert response.status_code == 200
    assert response.json() == {
        "default": "gemini-2.5-pro",
        "models": [
            {
                "id": "gemini-2.5-flash",
                "label": "Gemini 2.5 Flash",
                "description": "Balanced default for SADify.",
                "hint": "",
            },
            {
                "id": "gemini-2.5-pro",
                "label": "Gemini 2.5 Pro",
                "description": "Higher quality reasoning for complex SAD drafts.",
                "hint": "slower, higher quality",
            },
            {
                "id": "gemini-2.5-flash-lite",
                "label": "Gemini 2.5 Flash-Lite",
                "description": "Fastest Gemini option for low-latency drafts.",
                "hint": "fastest",
            },
        ],
    }


def test_analysis_requirement_threads_selected_model_to_analysis_model():
    model = CapturingRequirementAnalysisModel()
    client = TestClient(create_app(analysis_model=model))

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": "Need a simple way to validate operational ideas.",
            "model": "gemini-2.5-pro",
        },
    )

    assert response.status_code == 200
    assert model.calls[0]["model"] == "gemini-2.5-pro"


def test_sad_preview_threads_selected_model_to_preview_model():
    model = CapturingSadPreviewModel()
    client = TestClient(create_app(sad_preview_model=model))

    response = client.post(
        "/sad/preview",
        json={
            "requirement_text": "Need to validate an operational workflow.",
            "analysis_id": "AN-000001",
            "analysis": json.loads(json.dumps(_analysis_with_blocking_basics())),
            "model": "gemini-2.5-pro",
            "source_context": "[SRC-000001] workflow.md\nThe workflow needs approval.",
            "source_references": ["SRC-000001"],
        },
    )

    assert response.status_code == 200
    assert model.calls[0]["model"] == "gemini-2.5-pro"
