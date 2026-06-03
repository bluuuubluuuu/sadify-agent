from fastapi import APIRouter

from sadify_api.config import ApiConfig
from sadify_api.schemas import ModelCatalogResponse
from sadify_api.services.model_catalog import list_gemini_models


def create_models_router(config: ApiConfig) -> APIRouter:
    router = APIRouter(tags=["models"])

    @router.get("/models", response_model=ModelCatalogResponse)
    def models() -> ModelCatalogResponse:
        return list_gemini_models(config)

    return router
