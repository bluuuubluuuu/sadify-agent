from fastapi import FastAPI

from sadify_api.config import ApiConfig, load_api_config
from sadify_api.routes.diagnostics import create_diagnostics_router
from sadify_api.routes.health import create_health_router


def create_app(config: ApiConfig | None = None) -> FastAPI:
    config = config or load_api_config()
    app = FastAPI(title="SADify API", version="0.1.0")
    app.include_router(create_health_router(config))
    if config.diagnostics_enabled:
        app.include_router(create_diagnostics_router(config))

    return app


app = create_app()
