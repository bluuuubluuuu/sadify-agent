from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sadify_api.config import ApiConfig, load_api_config
from sadify_api.routes.auth import create_auth_router
from sadify_api.routes.diagnostics import create_diagnostics_router
from sadify_api.routes.health import create_health_router
from sadify_api.services.auth import FirebaseAdminTokenVerifier, TokenVerifier


def create_app(
    config: ApiConfig | None = None,
    token_verifier: TokenVerifier | None = None,
) -> FastAPI:
    config = config or load_api_config()
    token_verifier = token_verifier or FirebaseAdminTokenVerifier(config)
    app = FastAPI(title="SADify API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["authorization", "content-type"],
    )
    app.include_router(create_health_router(config))
    app.include_router(create_auth_router(token_verifier))
    if config.diagnostics_enabled:
        app.include_router(create_diagnostics_router(config))

    return app


app = create_app()
