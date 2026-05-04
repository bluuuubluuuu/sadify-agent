from __future__ import annotations

from dataclasses import dataclass
import os


_DRIVE_PLACEHOLDERS = {
    "",
    "replace-with-your-drive-folder-id",
    "your-drive-folder-id",
}


@dataclass(frozen=True)
class AppConfig:
    google_cloud_project: str
    google_cloud_location: str
    google_genai_use_vertexai: bool
    sadify_model: str
    sadify_model_provider: str
    sadify_final_sad_provider: str
    sadify_final_sad_model: str
    sadify_fallback_provider: str | None
    sadify_fallback_model: str | None
    openai_compatible_base_url: str | None
    ollama_base_url: str | None
    sadify_env: str
    sadify_log_level: str
    sadify_drive_root_folder_id: str | None
    sadify_runtime_service_account: str | None


def load_config() -> AppConfig:
    drive_folder_id = os.getenv("SADIFY_DRIVE_ROOT_FOLDER_ID", "").strip()
    if drive_folder_id in _DRIVE_PLACEHOLDERS:
        drive_folder_id = None

    sadify_model = os.getenv("SADIFY_MODEL", "gemini-2.5-flash").strip()
    sadify_model_provider = _provider_env("SADIFY_MODEL_PROVIDER", "google")

    return AppConfig(
        google_cloud_project=os.getenv("GOOGLE_CLOUD_PROJECT", "sadify").strip(),
        google_cloud_location=os.getenv(
            "GOOGLE_CLOUD_LOCATION", "asia-southeast1"
        ).strip(),
        google_genai_use_vertexai=_env_bool("GOOGLE_GENAI_USE_VERTEXAI", True),
        sadify_model=sadify_model,
        sadify_model_provider=sadify_model_provider,
        sadify_final_sad_provider=_provider_env(
            "SADIFY_FINAL_SAD_PROVIDER", sadify_model_provider
        ),
        sadify_final_sad_model=os.getenv(
            "SADIFY_FINAL_SAD_MODEL", sadify_model
        ).strip(),
        sadify_fallback_provider=_optional_provider_env("SADIFY_FALLBACK_PROVIDER"),
        sadify_fallback_model=_optional_env("SADIFY_FALLBACK_MODEL"),
        openai_compatible_base_url=_optional_env("OPENAI_COMPATIBLE_BASE_URL"),
        ollama_base_url=_optional_env("OLLAMA_BASE_URL"),
        sadify_env=os.getenv("SADIFY_ENV", "local").strip(),
        sadify_log_level=os.getenv("SADIFY_LOG_LEVEL", "INFO").strip().upper(),
        sadify_drive_root_folder_id=drive_folder_id,
        sadify_runtime_service_account=_optional_env(
            "SADIFY_RUNTIME_SERVICE_ACCOUNT"
        ),
    )


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _provider_env(name: str, default: str) -> str:
    return os.getenv(name, default).strip().lower().replace("-", "_")


def _optional_provider_env(name: str) -> str | None:
    value = _optional_env(name)
    if value is None:
        return None
    return value.lower().replace("-", "_")


def _optional_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None
