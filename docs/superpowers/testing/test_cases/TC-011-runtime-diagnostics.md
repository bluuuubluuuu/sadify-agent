# TC-011 Runtime Diagnostics

Date Created: 2026-04-30
Last Updated: 2026-05-04
Status: Passed

## Purpose

Verify that DevTools, logs, debugging output, and HTTP responses make runtime issues easy to detect.

## Traceability Sources

- `docs/superpowers/development/05_development_workflow.md` - Checkpoint 2
- `docs/superpowers/testing/test_case_index.md` - runtime diagnostics coverage
- `docs/superpowers/development/04_google_cloud_setup_runbook.md` - cloud smoke and cleanup context

## Inputs

Normal app actions and intentionally failing actions.

## Preconditions

Logging, diagnostics, and error handling exist.

## Steps

1. Run a successful action.
2. Run an action that fails validation.
3. Run an action that simulates external API failure.
4. Inspect browser console, network requests, app logs, and HTTP responses.

## Expected Output

- browser console has no unexpected errors
- failed requests show useful status and messages
- app logs include action, timing, and error context
- sensitive data is redacted
- user-facing errors are understandable

## Real Output

- `DiagnosticsRecorder` stores operation results in order and exposes failure state.
- `timed_action` records elapsed time for success and failure paths.
- Failure paths re-raise the original exception while recording a redacted diagnostic result.
- `user_facing_error` returns plain, actionable text that points to development logs.
- `configure_logging` uses a single handler and redacts sensitive metadata such as Drive folder IDs before logging.
- Streamlit page model exposes diagnostic booleans for Drive folder and service account config without exposing the actual Drive folder ID.
- Full local test suite passed.

## Differences / Issues

- Browser console and network diagnostics are not yet fully tested because the current app is still a local scaffold and has no external requests.
- Streamlit can be run manually at `http://localhost:8501`; previous browser check confirmed the Checkpoint 1 shell loaded.
- External API failure simulation is covered at the diagnostics unit level, not through real Gemini/Firestore/Drive calls yet.

## Evidence

```text
Command: .\.venv\Scripts\pytest.exe tests\test_diagnostics.py tests\test_logging_config.py -q
Result: 9 passed in 0.06s
```

```text
Command: .\.venv\Scripts\pytest.exe tests -q
Result: 17 passed in 4.44s
```

Covered test files:

```text
tests/test_diagnostics.py
tests/test_logging_config.py
tests/test_app_shell.py
```

## Decision

Passed for Checkpoint 2 local diagnostics foundation.

Continue to Checkpoint 3: requirement text input and standard first-response UI.
