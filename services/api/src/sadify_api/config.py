from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ApiConfig:
    environment: str
    diagnostics_enabled: bool = True


def load_api_config() -> ApiConfig:
    environment = os.getenv("SADIFY_ENV", "test").strip() or "test"
    diagnostics_enabled = _env_bool(
        "SADIFY_ENABLE_DIAGNOSTICS",
        default=environment.lower() != "production",
    )
    return ApiConfig(
        environment=environment,
        diagnostics_enabled=diagnostics_enabled,
    )


def _env_bool(name: str, *, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    return raw_value.strip().lower() in {"1", "true", "yes", "on"}
