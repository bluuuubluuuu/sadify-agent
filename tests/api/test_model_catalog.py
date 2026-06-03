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
