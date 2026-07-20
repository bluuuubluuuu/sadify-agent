# TC-007 Wiki Verification + Approval

Date Created: 2026-04-30
Last Updated: 2026-05-07
Status: Passed

## Purpose

Verify that wiki Markdown drafts are checked and approved before replacing verified notes.

## Traceability Sources

- `docs/superpowers/development/05_development_workflow.md` - Checkpoint 10
- `docs/superpowers/development/02_agent_behavior_contract.md` - verification and approval behavior
- `docs/superpowers/development/03_data_model_and_output_schema.md` - wiki verification fields
- `docs/superpowers/testing/test_case_index.md`

## Inputs

Generated wiki Markdown drafts from C9 plus canonical knowledge item records.

## Preconditions

Local rule-based verifier and owner approval state transitions exist. Gemini quality verification is represented in the verification payload as `not_run` for this local-first checkpoint slice.

## Steps

1. Generate a markdown draft.
2. Run local rule-based checks.
3. Record Gemini quality status as `not_run` for the local-first slice.
4. Review pending change summary.
5. Approve or reject as project owner.
6. Confirm approved drafts become current notes and rejected drafts do not overwrite current notes.

## Expected Output

- draft does not overwrite current note immediately
- rule failures block promotion
- owner approval is required
- approved draft becomes current note
- rejected draft is cleared without overwriting current note
- verification result records rule-based, Gemini quality placeholder, and human review state

## Real Output

Passed with a local deterministic wiki verification and approval service:

- Valid generated Markdown drafts pass structural rule checks.
- Missing required sections and broken wiki links fail with specific issue codes.
- Passing drafts set `markdown_draft`, `markdown_status="pending_human_approval"`, a pending change summary, and verification metadata.
- Owner approval promotes draft Markdown to `markdown_current`, clears `markdown_draft`, and sets `markdown_status="verified"`.
- Owner rejection keeps existing `markdown_current`, clears `markdown_draft`, sets `markdown_status="rejected"`, and records the rejection reason.
- Approval is blocked unless the item is pending owner approval and has a non-empty draft.

## Differences / Issues

No blocking differences for the local checkpoint. Live Gemini quality verification and Streamlit approval UI are not implemented yet; this slice records `gemini_quality.status = not_run` and keeps the approval flow service-level.

## Evidence

- `.\.venv\Scripts\pytest.exe tests\test_wiki_verification.py` -> 6 passed.
- `.\.venv\Scripts\pytest.exe tests\test_wiki_verification.py tests\test_wiki_markdown_renderer.py tests\test_canonical_schemas.py` -> 16 passed.
- `.\.venv\Scripts\pytest.exe` -> 76 passed.

## Decision

Passed. Continue to Checkpoint 11: project-level SAD generation.
