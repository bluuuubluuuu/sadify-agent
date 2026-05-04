from sadify.config import AppConfig, load_config


def test_load_config_reads_expected_environment(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "sadify")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "asia-southeast1")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "True")
    monkeypatch.setenv("SADIFY_MODEL", "gemini-2.5-flash")
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
    assert config.sadify_env == "local"
    assert config.sadify_log_level == "INFO"
    assert config.sadify_drive_root_folder_id is None
