# TC-009 Export Generation

Date Created: 2026-04-30
Last Updated: 2026-05-11
Status: Passed

## Purpose

Verify Google Docs, PDF, DOCX, and wiki Markdown export behavior.

## Traceability Sources

- `docs/superpowers/development/05_development_workflow.md` - Checkpoint 12
- `docs/superpowers/development/04_google_cloud_setup_runbook.md` - Google Docs and Drive setup
- `docs/superpowers/development/03_data_model_and_output_schema.md` - export records
- `docs/superpowers/testing/test_case_index.md`

## Inputs

Verified SAD version and verified wiki notes.

## Preconditions

Checkpoint 11 project-level SAD generation is complete.
Wiki Markdown notes can already be generated locally.

## Steps

1. Export SAD to Google Docs.
2. Export SAD to PDF.
3. Export SAD to DOCX.
4. Export wiki Markdown files to Drive.
5. Review export records.

## Expected Output

- each export creates a file or documented error
- files are placed in correct folders
- URLs/Drive IDs are saved
- export records reference source versions

## Real Output

Implemented `sadify.services.export_generation.prepare_export_package` and `write_export_package`.

The local-first export package creates:

- Google-Doc-import HTML artifact under `sad/`
- valid PDF artifact under `sad/`
- valid DOCX artifact under `sad/`
- wiki Markdown artifacts under `wiki/`
- one canonical `ExportRecord` per artifact
- stable export IDs starting at `EXP-001`
- source SAD version traceability
- safe local materialization that rejects paths outside the chosen output directory

No real Google Drive or Google Docs API write was run in this checkpoint.

## Differences / Issues

The generated Google Docs artifact is an HTML import source, not a live Google Doc yet.

Drive IDs and URLs remain `None` until a Drive upload/conversion connector is added and explicitly tested.

## Evidence

Automated verification:

```text
Command: .\.venv\Scripts\pytest.exe tests\test_export_generation.py -q
Result: 5 passed in 1.28s

Command: .\.venv\Scripts\pytest.exe tests\test_export_generation.py tests\test_sad_generation.py tests\test_wiki_markdown_renderer.py tests\test_canonical_schemas.py -q
Result: 19 passed in 1.32s

Command: .\.venv\Scripts\pytest.exe
Result: 85 passed in 6.61s
```

## Decision

Passed for the local-first export generation slice.

Historical next step from 2026-05-08 was Checkpoint 13: local end-to-end test.

Current update on 2026-05-11: Checkpoint 13 has passed. Proceed to Checkpoint 14: Cloud Run deployment preparation and deployment.
