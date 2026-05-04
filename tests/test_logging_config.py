import io
import logging

from sadify.logging_config import configure_logging


def test_configure_logging_uses_requested_level_and_single_handler():
    stream = io.StringIO()

    logger = configure_logging("DEBUG", stream=stream)
    same_logger = configure_logging("DEBUG", stream=stream)

    assert logger is same_logger
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1


def test_logger_redacts_sensitive_extra_metadata():
    stream = io.StringIO()
    logger = configure_logging("INFO", stream=stream)

    logger.info(
        "export started",
        extra={"metadata": {"drive_folder_id": "private-drive-folder-id"}},
    )

    output = stream.getvalue()
    assert "export started" in output
    assert "private-drive-folder-id" not in output
    assert "[REDACTED]" in output
