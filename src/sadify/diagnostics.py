from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from time import perf_counter
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


@dataclass
class DiagnosticsRecorder:
    results: list[OperationResult] = field(default_factory=list)

    def record(self, result: OperationResult) -> OperationResult:
        safe_result = OperationResult(
            success=result.success,
            action=result.action,
            message=result.message,
            elapsed_ms=result.elapsed_ms,
            metadata=redact_mapping(result.metadata),
            error=result.error,
        )
        self.results.append(safe_result)
        return safe_result

    @property
    def has_failures(self) -> bool:
        return any(not result.success for result in self.results)


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


@contextmanager
def timed_action(
    recorder: DiagnosticsRecorder,
    action: str,
    success_message: str,
    *,
    failure_message: str | None = None,
    metadata: dict[str, Any] | None = None,
):
    started_at = perf_counter()
    try:
        yield
    except Exception as error:
        elapsed_ms = (perf_counter() - started_at) * 1000
        recorder.record(
            failure_result(
                action=action,
                message=failure_message or success_message,
                error=error,
                elapsed_ms=elapsed_ms,
                metadata=metadata,
            )
        )
        raise
    else:
        elapsed_ms = (perf_counter() - started_at) * 1000
        recorder.record(
            success_result(
                action=action,
                message=success_message,
                elapsed_ms=elapsed_ms,
                metadata=metadata,
            )
        )


def user_facing_error(result: OperationResult) -> str:
    return f"{result.message}. Check the development logs for {result.action}."


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
