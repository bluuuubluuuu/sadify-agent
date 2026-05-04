import pytest

from sadify.diagnostics import (
    DiagnosticsRecorder,
    failure_result,
    redact_mapping,
    success_result,
    timed_action,
    user_facing_error,
)


def test_redact_mapping_hides_secret_and_folder_values():
    redacted = redact_mapping(
        {
            "normal": "visible",
            "api_key": "private-api-key",
            "access_token": "private-token",
            "drive_folder_id": "private-drive-folder-id",
            "nested": {"password": "private-password", "safe": "ok"},
        }
    )

    assert redacted == {
        "normal": "visible",
        "api_key": "[REDACTED]",
        "access_token": "[REDACTED]",
        "drive_folder_id": "[REDACTED]",
        "nested": {"password": "[REDACTED]", "safe": "ok"},
    }


def test_success_result_keeps_safe_metadata():
    result = success_result(
        action="load_config",
        message="Loaded configuration",
        elapsed_ms=12.4,
        metadata={"project": "sadify"},
    )

    assert result.success is True
    assert result.action == "load_config"
    assert result.message == "Loaded configuration"
    assert result.elapsed_ms == 12.4
    assert result.metadata == {"project": "sadify"}
    assert result.error is None


def test_failure_result_redacts_error_metadata():
    result = failure_result(
        action="export_doc",
        message="Export failed",
        error=RuntimeError("boom"),
        elapsed_ms=34.1,
        metadata={"drive_folder_id": "private-drive-folder-id"},
    )

    assert result.success is False
    assert result.action == "export_doc"
    assert result.message == "Export failed"
    assert result.error == "boom"
    assert result.metadata == {"drive_folder_id": "[REDACTED]"}


def test_recorder_stores_redacted_results_in_order():
    recorder = DiagnosticsRecorder()

    recorder.record(
        success_result(
            action="load_config",
            message="Loaded",
            metadata={"drive_folder_id": "private-drive-folder-id"},
        )
    )
    recorder.record(
        failure_result(
            action="export_doc",
            message="Failed",
            error=RuntimeError("nope"),
            metadata={"api_key": "private-api-key"},
        )
    )

    assert [result.action for result in recorder.results] == [
        "load_config",
        "export_doc",
    ]
    assert recorder.has_failures is True
    assert recorder.results[0].metadata == {"drive_folder_id": "[REDACTED]"}
    assert recorder.results[1].metadata == {"api_key": "[REDACTED]"}


def test_timed_action_records_success():
    recorder = DiagnosticsRecorder()

    with timed_action(recorder, "load_config", "Loaded config"):
        value = "ok"

    assert value == "ok"
    assert len(recorder.results) == 1
    result = recorder.results[0]
    assert result.success is True
    assert result.action == "load_config"
    assert result.message == "Loaded config"
    assert result.elapsed_ms is not None
    assert result.elapsed_ms >= 0


def test_timed_action_records_failure_and_reraises():
    recorder = DiagnosticsRecorder()

    with pytest.raises(ValueError, match="bad config"):
        with timed_action(
            recorder,
            "load_config",
            "Loaded config",
            failure_message="Could not load config",
            metadata={"token": "private-token"},
        ):
            raise ValueError("bad config")

    assert len(recorder.results) == 1
    result = recorder.results[0]
    assert result.success is False
    assert result.action == "load_config"
    assert result.message == "Could not load config"
    assert result.error == "bad config"
    assert result.metadata == {"token": "[REDACTED]"}


def test_user_facing_error_is_plain_and_actionable():
    result = failure_result(
        action="model_call",
        message="Gemini request failed",
        error=TimeoutError("request timed out"),
    )

    assert user_facing_error(result) == (
        "Gemini request failed. Check the development logs for model_call."
    )
