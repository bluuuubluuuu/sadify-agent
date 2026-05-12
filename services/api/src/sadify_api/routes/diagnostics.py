from fastapi import APIRouter

from sadify_api.config import ApiConfig
from sadify_api.schemas import ConfigDiagnosticsResponse


def create_diagnostics_router(config: ApiConfig) -> APIRouter:
    router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])

    @router.get("/config", response_model=ConfigDiagnosticsResponse)
    def config_diagnostics() -> ConfigDiagnosticsResponse:
        return ConfigDiagnosticsResponse(
            status="ok",
            service="sadify-api",
            environment=config.environment,
            diagnostics_enabled=config.diagnostics_enabled,
            secrets="redacted",
        )

    return router
