from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import os
from typing import Mapping

from sadify.config import AppConfig


class ModelTask(StrEnum):
    REQUIREMENT_ANALYSIS = "requirement_analysis"
    FINAL_SAD = "final_sad"
    FALLBACK = "fallback"


@dataclass(frozen=True)
class ModelRoute:
    task: ModelTask
    provider: str
    model: str

    def to_display_dict(self) -> dict[str, str]:
        return {
            "task": self.task.value.replace("_", " ").title(),
            "provider": self.provider,
            "model": self.model,
        }


@dataclass(frozen=True)
class ProviderStatus:
    provider: str
    label: str
    configured: bool
    configuration_hint: str

    def to_display_dict(self) -> dict[str, str | bool]:
        return {
            "provider": self.provider,
            "label": self.label,
            "configured": self.configured,
            "configuration_hint": self.configuration_hint,
        }


@dataclass(frozen=True)
class ProviderSpec:
    provider: str
    label: str
    secret_env_name: str | None
    configuration_hint: str


_PROVIDER_SPECS = (
    ProviderSpec(
        provider="google",
        label="Google Gemini / Vertex AI",
        secret_env_name="GOOGLE_API_KEY",
        configuration_hint="Default route. Uses Vertex AI project settings when GOOGLE_GENAI_USE_VERTEXAI=True.",
    ),
    ProviderSpec(
        provider="openai",
        label="OpenAI GPT",
        secret_env_name="OPENAI_API_KEY",
        configuration_hint="Set OPENAI_API_KEY before enabling this route.",
    ),
    ProviderSpec(
        provider="anthropic",
        label="Anthropic Claude",
        secret_env_name="ANTHROPIC_API_KEY",
        configuration_hint="Set ANTHROPIC_API_KEY before enabling this route.",
    ),
    ProviderSpec(
        provider="openai_compatible",
        label="OpenAI-compatible endpoint",
        secret_env_name="OPENAI_COMPATIBLE_API_KEY",
        configuration_hint="Set OPENAI_COMPATIBLE_BASE_URL, and an API key if the endpoint requires one.",
    ),
    ProviderSpec(
        provider="ollama",
        label="Ollama / local model",
        secret_env_name=None,
        configuration_hint="Set OLLAMA_BASE_URL when running a local model server.",
    ),
    ProviderSpec(
        provider="huggingface",
        label="Hugging Face Inference Provider",
        secret_env_name="HF_TOKEN",
        configuration_hint="Set HF_TOKEN before enabling this route.",
    ),
)


def supported_provider_ids() -> list[str]:
    return [spec.provider for spec in _PROVIDER_SPECS]


def build_model_routes(config: AppConfig) -> dict[ModelTask, ModelRoute]:
    routes = {
        ModelTask.REQUIREMENT_ANALYSIS: ModelRoute(
            task=ModelTask.REQUIREMENT_ANALYSIS,
            provider=config.sadify_model_provider,
            model=config.sadify_model,
        ),
        ModelTask.FINAL_SAD: ModelRoute(
            task=ModelTask.FINAL_SAD,
            provider=config.sadify_final_sad_provider,
            model=config.sadify_final_sad_model,
        ),
    }

    if config.sadify_fallback_provider and config.sadify_fallback_model:
        routes[ModelTask.FALLBACK] = ModelRoute(
            task=ModelTask.FALLBACK,
            provider=config.sadify_fallback_provider,
            model=config.sadify_fallback_model,
        )

    return routes


def build_provider_statuses(
    config: AppConfig,
    environ: Mapping[str, str] | None = None,
) -> list[ProviderStatus]:
    env = environ or os.environ
    statuses: list[ProviderStatus] = []

    for spec in _PROVIDER_SPECS:
        configured = _is_provider_configured(spec.provider, config, env)
        statuses.append(
            ProviderStatus(
                provider=spec.provider,
                label=spec.label,
                configured=configured,
                configuration_hint=spec.configuration_hint,
            )
        )

    return statuses


def _is_provider_configured(
    provider: str,
    config: AppConfig,
    env: Mapping[str, str],
) -> bool:
    if provider == "google":
        if config.google_genai_use_vertexai:
            return bool(config.google_cloud_project and config.google_cloud_location)
        return _has_env_value(env, "GOOGLE_API_KEY")
    if provider == "openai":
        return _has_env_value(env, "OPENAI_API_KEY")
    if provider == "anthropic":
        return _has_env_value(env, "ANTHROPIC_API_KEY")
    if provider == "openai_compatible":
        return config.openai_compatible_base_url is not None
    if provider == "ollama":
        return config.ollama_base_url is not None
    if provider == "huggingface":
        return _has_env_value(env, "HF_TOKEN")
    return False


def _has_env_value(env: Mapping[str, str], key: str) -> bool:
    return bool(env.get(key, "").strip())
