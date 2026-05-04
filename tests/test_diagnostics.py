from sadify.diagnostics import failure_result, redact_mapping, success_result


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
