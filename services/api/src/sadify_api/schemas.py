from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(ApiModel):
    status: str
    service: str
    environment: str


class ConfigDiagnosticsResponse(HealthResponse):
    diagnostics_enabled: bool
    secrets: str


class AuthenticatedUser(ApiModel):
    uid: str
    email: str | None = None
    display_name: str | None = None
    provider: str


class AuthSessionResponse(ApiModel):
    status: str
    user: AuthenticatedUser
