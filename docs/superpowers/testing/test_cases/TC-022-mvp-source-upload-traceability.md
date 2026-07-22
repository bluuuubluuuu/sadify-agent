# TC-022 MVP Source Upload Traceability

Date Created: 2026-05-11
Last Updated: 2026-05-13
Status: Passed

## Purpose

Verify web source upload, readable text extraction, source metadata, and traceability references.

## Inputs

- MD/TXT, PDF, DOCX, XLSX, CSV sample files
- Existing source extraction services

## Preconditions

TC-018 and TC-021 passed. Official docs checked before coding:

- FastAPI Request Files: `https://fastapi.tiangolo.com/tutorial/request-files/`
- MDN FormData: `https://developer.mozilla.org/en-US/docs/Web/API/FormData`

## Steps

1. Upload supported files in the web app.
2. Extract readable content through the backend.
3. Save source metadata and extracted text state.
4. Confirm Gemini analysis references source IDs where relevant.
5. Confirm unsupported files show clear errors.

## Expected Output

Original source metadata and extracted text are captured, and generated analysis can trace claims to source files.

## Real Output

MVP worktree `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold` now has:

- FastAPI `/sources/upload` endpoint for multipart source uploads.
- Explicit `python-multipart` dependency.
- Backend in-memory `SourceRepository` with stable `SRC-000001` IDs, extracted text, preview, summaries, and traceability units.
- Supported file extraction through the existing local MD/TXT/PDF/DOCX/XLSX/CSV extractor.
- Clear unsupported-file errors returned without losing valid uploaded sources.
- Analysis request support for `source_context` and `source_references`.
- Deterministic merge of provided source IDs into saved analysis `source_references`.
- Next.js `SourceUploadPanel` wired into the workspace before `AnalysisPanel`.
- Analysis panel shows attached source-reference count and returned source refs.

## Differences / Issues

- No real Firestore or Drive source persistence yet; source records are local backend state for this checkpoint.
- No Google Drive folder write happened in TC-022.
- To avoid extra cloud credit, this checkpoint did not run another live Gemini call. Source-reference propagation was verified with a fake structured model, while `/sources/upload` was verified through local API tests and local API smoke.
- Codex Browser could validate the rendered source panel and no-file interaction. File-picker upload itself was validated through backend multipart API smoke and automated tests.
- Deployed two-service smoke remains deferred until the deployment checkpoint.

## Evidence

- Red test first: `pytest tests/api/test_source_uploads.py tests/test_mvp_source_upload_traceability_ui.py -q` initially failed with `ModuleNotFoundError: No module named 'sadify_api.services.source_uploads'`.
- Focused tests after implementation: `5 passed in 1.25s`.
- Full Python regression: `122 passed in 8.71s`.
- TypeScript check: `node ...\typescript\bin\tsc -p ...\apps\web\tsconfig.json --noEmit` exited `0`.
- Production build: `npm --prefix ...\apps\web run build` completed successfully.
- Local API smoke on `http://127.0.0.1:8010/sources/upload` returned `HTTP 200` with `SRC-000001`, `extraction_status=extracted`, `traceability_units[0].unit_type=file`, and an `analysis_context` containing `[SRC-000001]`.
- Browser smoke on `http://127.0.0.1:3010/` showed `Upload source files` and `Question flow`, zero console warnings/errors, and the no-file upload click showed `Choose at least one MD, TXT, PDF, DOCX, XLSX, or CSV file.`
- Temporary smoke servers on ports `8010` and `3010` were stopped after validation.

## Decision

Passed for the local MVP-07 gate. Stop here and wait for user approval before MVP-08 / TC-023 Drive repo OAuth.
