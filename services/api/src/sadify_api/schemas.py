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
