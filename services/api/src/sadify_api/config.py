from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ApiConfig:
    environment: str
    diagnostics_enabled: bool = True
    firebase_project_id: str | None = None
    google_cloud_project: str | None = None
    google_cloud_location: str = "global"
    google_genai_use_vertexai: bool = True
    sadify_model: str = "gemini-2.5-flash"
    allowed_origins: tuple[str, ...] = ("http://localhost:3000",)


def load_api_config() -> ApiConfig:
    environment = os.getenv("SADIFY_ENV", "test").strip() or "test"
    firebase_project_id = (
        os.getenv("FIREBASE_PROJECT_ID")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or None
    )
    google_cloud_project = os.getenv("GOOGLE_CLOUD_PROJECT") or firebase_project_id
    google_cloud_location = os.getenv("GOOGLE_CLOUD_LOCATION", "global").strip()
    sadify_model = os.getenv("SADIFY_MODEL", "gemini-2.5-flash").strip()
    diagnostics_enabled = _env_bool(
        "SADIFY_ENABLE_DIAGNOSTICS",
        default=environment.lower() != "production",
    )
    allowed_origins = _env_list(
        "SADIFY_ALLOWED_ORIGINS",
        default=("http://localhost:3000",),
    )
    return ApiConfig(
        environment=environment,
        diagnostics_enabled=diagnostics_enabled,
        firebase_project_id=firebase_project_id,
        google_cloud_project=google_cloud_project,
        google_cloud_location=google_cloud_location or "global",
        google_genai_use_vertexai=_env_bool("GOOGLE_GENAI_USE_VERTEXAI", default=True),
        sadify_model=sadify_model or "gemini-2.5-flash",
        allowed_origins=allowed_origins,
    )


def _env_bool(name: str, *, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, *, default: tuple[str, ...]) -> tuple[str, ...]:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    values = tuple(
        value.strip()
        for value in raw_value.split(",")
        if value.strip()
    )
    return values or default
