from sadify.config import AppConfig
from sadify.models import (
    ModelTask,
    build_model_routes,
    build_provider_statuses,
    supported_provider_ids,
)


def test_supported_provider_ids_cover_google_and_common_llm_bases():
    assert supported_provider_ids() == [
        "google",
        "openai",
        "anthropic",
        "openai_compatible",
        "ollama",
        "huggingface",
    ]


def test_build_model_routes_keeps_current_gemini_model_as_default():
    routes = build_model_routes(_config())

    analysis_route = routes[ModelTask.REQUIREMENT_ANALYSIS]
    final_route = routes[ModelTask.FINAL_SAD]

    assert analysis_route.provider == "google"
    assert analysis_route.model == "gemini-2.5-flash"
    assert final_route.provider == "google"
    assert final_route.model == "gemini-2.5-flash"
    assert ModelTask.FALLBACK not in routes


def test_build_model_routes_allows_final_and_fallback_overrides():
    config = _config(
        sadify_final_sad_provider="anthropic",
        sadify_final_sad_model="claude-sonnet-4",
        sadify_fallback_provider="openai",
        sadify_fallback_model="gpt-5-mini",
    )

    routes = build_model_routes(config)

    assert routes[ModelTask.REQUIREMENT_ANALYSIS].provider == "google"
    assert routes[ModelTask.FINAL_SAD].provider == "anthropic"
    assert routes[ModelTask.FINAL_SAD].model == "claude-sonnet-4"
    assert routes[ModelTask.FALLBACK].provider == "openai"
    assert routes[ModelTask.FALLBACK].model == "gpt-5-mini"


def test_provider_statuses_report_configuration_without_secrets(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "private-openai-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "private-anthropic-key")
    monkeypatch.setenv("HF_TOKEN", "private-hf-token")

    statuses = build_provider_statuses(
        _config(
            openai_compatible_base_url="https://llm-router.example/v1",
            ollama_base_url="http://localhost:11434",
        )
    )
    statuses_by_id = {status.provider: status for status in statuses}

    assert statuses_by_id["google"].configured is True
    assert statuses_by_id["openai"].configured is True
    assert statuses_by_id["anthropic"].configured is True
    assert statuses_by_id["huggingface"].configured is True
    assert statuses_by_id["openai_compatible"].configured is True
    assert statuses_by_id["ollama"].configured is True
    assert "private" not in str(statuses)


def _config(**overrides) -> AppConfig:
    values = {
        "google_cloud_project": "sadify",
        "google_cloud_location": "asia-southeast1",
        "google_genai_use_vertexai": True,
        "sadify_model": "gemini-2.5-flash",
        "sadify_model_provider": "google",
        "sadify_final_sad_provider": "google",
        "sadify_final_sad_model": "gemini-2.5-flash",
        "sadify_fallback_provider": None,
        "sadify_fallback_model": None,
        "openai_compatible_base_url": None,
        "ollama_base_url": None,
        "sadify_env": "local",
        "sadify_log_level": "INFO",
        "sadify_drive_root_folder_id": "drive-folder-id",
        "sadify_runtime_service_account": (
            "sadify-agent-sa@sadify.iam.gserviceaccount.com"
        ),
    }
    values.update(overrides)
    return AppConfig(**values)
