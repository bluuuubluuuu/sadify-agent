# TC-001 Requirement Input

Date Created: 2026-04-30
Last Updated: 2026-05-05
Status: Passed

## Purpose

Verify that users can enter messy requirement text and see the standard first-response structure in business-first language.

## Traceability Sources

- `docs/superpowers/development/05_development_workflow.md` - Checkpoint 3
- `docs/superpowers/development/02_agent_behavior_contract.md` - first response pattern
- `docs/superpowers/testing/test_case_index.md`

## Inputs

Messy production or operations requirement text.

## Preconditions

Local app scaffold exists.
Runtime diagnostics foundation exists.
Model provider routing foundation exists.

## Steps

1. Open the local SADify app.
2. Enter messy requirement text.
3. Submit the input.

## Expected Output

- input is accepted
- empty input is rejected clearly
- first-response structure appears
- wording is practical for a business requester, not only an IT expert
- no runtime errors appear

## Real Output

- `analyze_requirement_text` rejects empty input with a clear validation error.
- Messy requirement text produces deterministic local analysis.
- The analysis returns the standard first-response sections:
  - what SADify understands
  - readiness
  - confidence
  - what we still need to know
  - questions to confirm
  - draft option
- The Streamlit app exposes `build_analysis_view_model` for testable UI rendering.
- The `Check what is still unclear` button is enabled.
- Empty input shows `st.error`.
- Valid input renders what SADify understands, readiness, confidence, what still needs confirming, practical clarification questions, and draft guidance.
- Missing-information rows use business column headings: Area, Priority, What is unclear, Why this matters, What to answer next.
- No live model call is made yet.
- Browser testing found a `NameError: name 'st' is not defined` in `_render_analysis`.
- The render helper now receives the Streamlit module explicitly from `main()`.
- A regression test covers the render helper with a fake Streamlit module.

## Differences / Issues

- This is deterministic local analysis, not Gemini analysis.
- Completeness/confidence are first-pass heuristic values. The richer hybrid completeness engine remains a later checkpoint.
- Browser interaction initially exposed the `st` scoping bug. Automated regression coverage is now in place; rerun the app manually to confirm the UI path.

## Evidence

```text
Command: .\.venv\Scripts\pytest.exe tests\test_requirement_analysis.py
Result: 4 passed in 0.10s
```

```text
Command: .\.venv\Scripts\pytest.exe tests\test_app_shell.py tests\test_requirement_analysis.py
Result: 10 passed in 0.11s
```

```text
Command: .\.venv\Scripts\pytest.exe
Result: 24 passed in 4.30s
```

## Decision

Passed for Checkpoint 3 local requirement text input and deterministic first-response UI.

Continue to Checkpoint 4: business file extraction.
