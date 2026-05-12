from fastapi import APIRouter

from sadify_api.config import ApiConfig
from sadify_api.schemas import HealthResponse


def build_health_response(config: ApiConfig) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="sadify-api",
        environment=config.environment,
    )


def create_health_router(config: ApiConfig) -> APIRouter:
    router = APIRouter(tags=["health"])

    @router.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return build_health_response(config)

    return router
