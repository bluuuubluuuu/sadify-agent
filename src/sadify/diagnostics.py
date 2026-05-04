from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_SENSITIVE_KEY_PARTS = (
    "api_key",
    "credential",
    "drive_folder_id",
    "folder_id",
    "password",
    "secret",
    "token",
)


@dataclass(frozen=True)
class OperationResult:
    success: bool
    action: str
    message: str
    elapsed_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


def redact_mapping(value: dict[str, Any]) -> dict[str, Any]:
    return {key: _redact_value(key, item) for key, item in value.items()}


def success_result(
    *,
    action: str,
    message: str,
    elapsed_ms: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> OperationResult:
    return OperationResult(
        success=True,
        action=action,
        message=message,
        elapsed_ms=elapsed_ms,
        metadata=redact_mapping(metadata or {}),
    )


def failure_result(
    *,
    action: str,
    message: str,
    error: Exception,
    elapsed_ms: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> OperationResult:
    return OperationResult(
        success=False,
        action=action,
        message=message,
        elapsed_ms=elapsed_ms,
        metadata=redact_mapping(metadata or {}),
        error=str(error),
    )


def _redact_value(key: str, value: Any) -> Any:
    if _is_sensitive_key(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return redact_mapping(value)
    if isinstance(value, list):
        return [_redact_value(key, item) for item in value]
    return value


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)
