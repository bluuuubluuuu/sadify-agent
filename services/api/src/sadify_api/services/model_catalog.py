from sadify_api.config import ApiConfig
from sadify_api.schemas import ModelCatalogItem, ModelCatalogResponse


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

GEMINI_MODEL_CATALOG: tuple[dict[str, str], ...] = (
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
)


def list_gemini_models(config: ApiConfig) -> ModelCatalogResponse:
    default_model = backend_default_model(config)
    return ModelCatalogResponse(
        default=default_model,
        models=[
            ModelCatalogItem.model_validate(model)
            for model in GEMINI_MODEL_CATALOG
        ],
    )


def backend_default_model(config: ApiConfig) -> str:
    if config.sadify_model in _allowlisted_model_ids():
        return config.sadify_model

    return DEFAULT_GEMINI_MODEL


def resolve_gemini_model(requested_model: str | None, config: ApiConfig) -> str:
    if requested_model and requested_model in _allowlisted_model_ids():
        return requested_model

    return backend_default_model(config)


def _allowlisted_model_ids() -> set[str]:
    return {model["id"] for model in GEMINI_MODEL_CATALOG}
