from sadify.config import AppConfig, load_config


def test_load_config_reads_expected_environment(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "sadify")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "asia-southeast1")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "True")
    monkeypatch.setenv("SADIFY_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("SADIFY_MODEL_PROVIDER", "google")
    monkeypatch.setenv("SADIFY_FINAL_SAD_PROVIDER", "anthropic")
    monkeypatch.setenv("SADIFY_FINAL_SAD_MODEL", "claude-sonnet-4")
    monkeypatch.setenv("SADIFY_FALLBACK_PROVIDER", "openai")
    monkeypatch.setenv("SADIFY_FALLBACK_MODEL", "gpt-5-mini")
    monkeypatch.setenv(
        "OPENAI_COMPATIBLE_BASE_URL",
        "https://openai-compatible.example/v1",
    )
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("SADIFY_ENV", "local")
    monkeypatch.setenv("SADIFY_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("SADIFY_DRIVE_ROOT_FOLDER_ID", "drive-folder-id")
    monkeypatch.setenv(
        "SADIFY_RUNTIME_SERVICE_ACCOUNT",
        "sadify-agent-sa@sadify.iam.gserviceaccount.com",
    )

    config = load_config()

    assert config == AppConfig(
        google_cloud_project="sadify",
        google_cloud_location="asia-southeast1",
        google_genai_use_vertexai=True,
        sadify_model="gemini-2.5-flash",
        sadify_model_provider="google",
        sadify_final_sad_provider="anthropic",
        sadify_final_sad_model="claude-sonnet-4",
        sadify_fallback_provider="openai",
        sadify_fallback_model="gpt-5-mini",
        openai_compatible_base_url="https://openai-compatible.example/v1",
        ollama_base_url="http://localhost:11434",
        sadify_env="local",
        sadify_log_level="DEBUG",
        sadify_drive_root_folder_id="drive-folder-id",
        sadify_runtime_service_account=(
            "sadify-agent-sa@sadify.iam.gserviceaccount.com"
        ),
    )


def test_load_config_uses_safe_local_defaults(monkeypatch):
    for key in (
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
        "GOOGLE_GENAI_USE_VERTEXAI",
        "SADIFY_MODEL",
        "SADIFY_MODEL_PROVIDER",
        "SADIFY_FINAL_SAD_PROVIDER",
        "SADIFY_FINAL_SAD_MODEL",
        "SADIFY_FALLBACK_PROVIDER",
        "SADIFY_FALLBACK_MODEL",
        "OPENAI_COMPATIBLE_BASE_URL",
        "OLLAMA_BASE_URL",
        "SADIFY_ENV",
        "SADIFY_LOG_LEVEL",
        "SADIFY_DRIVE_ROOT_FOLDER_ID",
        "SADIFY_RUNTIME_SERVICE_ACCOUNT",
    ):
        monkeypatch.delenv(key, raising=False)

    config = load_config()

    assert config.google_cloud_project == "sadify"
    assert config.google_cloud_location == "asia-southeast1"
    assert config.google_genai_use_vertexai is True
    assert config.sadify_model == "gemini-2.5-flash"
    assert config.sadify_model_provider == "google"
    assert config.sadify_final_sad_provider == "google"
    assert config.sadify_final_sad_model == "gemini-2.5-flash"
    assert config.sadify_fallback_provider is None
    assert config.sadify_fallback_model is None
    assert config.openai_compatible_base_url is None
    assert config.ollama_base_url is None
    assert config.sadify_env == "local"
    assert config.sadify_log_level == "INFO"
    assert config.sadify_drive_root_folder_id is None
