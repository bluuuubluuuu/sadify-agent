# TC-026 MVP Drive Docs Save

Date Created: 2026-05-11
Last Updated: 2026-05-25
Status: Passed for local/fake save path

## Purpose

Verify that a draft-ready SAD preview can be saved as a durable project
artifact in the user's connected Drive repo.

This checkpoint is the save-path foundation. It does not approve or overwrite
the living wiki. TC-025 owns wiki update approval after TC-026 passes.

## Inputs

- Signed-in user session.
- Connected Drive repo record from TC-023.
- Draft-ready SAD preview from TC-024 / TC-028 quality flow.
- Uploaded source file record, when sources are present.
- Local/fake Drive/Docs implementation for the first slice.

## Preconditions

- TC-023 passed for the local Drive repo OAuth contract.
- TC-024 passed for local SAD preview and IT readiness.
- TC-028 plus Cycles 2A/2B passed for Q&A/SAD quality.
- No live OAuth exchange, Secret Manager write, Drive write, Docs write, or
  deployment happens without explicit user approval.

## Scope

In scope for the local-first TC-026 slice:

1. Save a selected `SP-` preview as a versioned SAD artifact record.
2. Create a fake/local Google Doc save result with stable document ID and URL.
3. Save source-file metadata and extracted text references into the export
   manifest when sources exist.
4. Save `_SADify` manifest/change-log metadata for the project repo.
5. Return save status, artifact links, and a user-facing change summary to the
   frontend.
6. Block saves when no signed-in user, no active repo, no preview, or a
   disconnected repo is present.

Out of scope until later checkpoints:

- Wiki Markdown approval or overwrite (TC-025).
- Cloud Run deployment (TC-027).
- Real Drive/Docs writes before explicit approval.
- Secret Manager refresh-token storage before least-privilege IAM is confirmed.

## Steps

1. Generate or load a draft-ready SAD preview.
2. Connect a project repo through the existing TC-023 contract.
3. Trigger "Save to project repo" from the frontend.
4. Backend validates signed-in user, active repo, and preview ID.
5. Backend creates local save records for:
   - `SAD/` Google Doc placeholder.
   - `_SADify/manifest`.
   - `_SADify/change-log`.
   - source metadata/extracted text references, when available.
6. Frontend shows saved status, document link placeholder, manifest status, and
   change summary.
7. Disconnect Drive repo and verify another save is blocked.

## Expected Output

- `/sad/save` or equivalent save endpoint returns `200 OK` for a valid signed-in
  repo + preview.
- Response includes stable IDs/URLs for the saved SAD artifact and metadata
  records.
- Save status is visible in the UI and no longer says the preview is temporary
  only after the save succeeds.
- Save attempts are rejected with clear messages when preconditions are missing.
- No real Drive/Docs/Secret Manager calls are made in local tests.
- TC-025 remains blocked until this save path passes.

## Real Output

MVP worktree `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold` now has:

- Authenticated backend `POST /sad/save`.
- Local `SadSaveRepository` with stable `SV-`, `SA-`, `SM-`, and
  `LOCAL-GDOC-` IDs.
- Idempotency on `(user_id, repo_id, preview_id, preview_revision)` so repeat
  saves return the same `SadSaveRecord`.
- Local/fake Google Doc artifact with path like
  `SAD/SAD-SP-000001-SV-000001.google_doc` and fake URL
  `https://docs.google.com/document/d/LOCAL-GDOC-000001/edit`.
- `_SADify` manifest and change-log artifacts.
- Source reference artifacts under `Sources/` when saved previews reference
  uploaded `SRC-` records.
- Stable save error codes for missing auth, missing repo, disconnected repo,
  missing preview ID, and unknown preview ID.
- Frontend `saveSadPreview(previewId, idToken)` API helper.
- Additive `Save to project repo` action in `SadPreviewPanel` after a preview
  exists.
- Workspace tracking updates after save, including save ID, fake Google Doc
  path, repo name, and linked source-reference count.

## Differences / Issues

- This pass is intentionally local/fake only. No live Google Drive file,
  Google Doc, OAuth token exchange, Secret Manager token storage, or Cloud Run
  deployment happened.
- The local UI save action still depends on an active signed-in Firebase user
  and connected repo state in the running app, as expected.
- Live Drive/Docs behavior remains a future TC-026B slice after explicit user
  approval.

## Evidence

- Backend save tests: `8 passed`.
- Focused backend regression before backend commit:
  `tests/api/test_sad_save.py tests/api/test_sad_preview.py tests/api/test_drive_repo.py`
  -> `34 passed`.
- Full Python regression before backend commit: `284 passed`.
- Frontend save static tests: `5 passed`.
- TypeScript gate before frontend commit: `npx -y tsc --noEmit` exited `0`
  outside the sandbox after the sandbox blocked Node from reading
  `C:\Users\User`.
- Focused final regression:
  `tests/api/test_sad_save.py tests/api/test_sad_preview.py tests/api/test_drive_repo.py tests/test_mvp_sad_save_ui.py tests/test_mvp_sad_preview_it_readiness_ui.py tests/test_mvp_drive_repo_oauth_ui.py`
  -> `46 passed`.
- Full final Python regression: `289 passed`.
- Final TypeScript gate: `npx -y tsc --noEmit` exited `0` outside the sandbox.
- Local save-flow smoke:

```text
LOCAL_SAVE_SMOKE_PASS
save_id=SV-000001
doc_path=SAD/SAD-SP-000001-SV-000001.google_doc
source_ids=SRC-000001
disconnect_code=SAD_SAVE_REPO_DISCONNECTED
```

- Manual browser smoke on 2026-05-25 with signed-in Firebase user, mobile
  phone repair shop requirement, `laundry-workflow.pdf` upload, draft-ready
  analysis (score 100%, AN-000011), local-dev repo connect (`DG-000001` then
  `DG-000002`):

```text
Case 3 (no repo, save attempted)         POST /sad/save -> 409  SAD_SAVE_REPO_REQUIRED
Case 4 (connect + happy path save)       POST /drive/repo/connect -> 200; POST /sad/save -> 200
                                          SV-000001 / LOCAL-GDOC-000001
                                          SAD/SAD-SP-000001-SV-000001.google_doc
Case 5 (repeat save, idempotent)         POST /sad/save -> 200  (still SV-000001)
Case 6 (disconnect + save)               POST /drive/repo/disconnect -> 200
                                          POST /sad/save -> 409  SAD_SAVE_REPO_DISCONNECTED
Case 7 (reconnect + save)                POST /drive/repo/connect -> 200  (DG-000002)
                                          POST /sad/save -> 200  SV-000002 / LOCAL-GDOC-000002
Case 8 (regenerate preview + save)       POST /sad/preview -> 200  (SP-000002)
                                          Saved card disappears on regenerate (regen-reset fix)
                                          POST /sad/save -> 200  SV-000003 / LOCAL-GDOC-000003
                                          SAD/SAD-SP-000002-SV-000003.google_doc
```

- Network log was free of `googleapis.com`, `oauth2.googleapis.com`, and
  Secret Manager requests for the entire run — stop-rule honored.
- Local-dev connect affordance (commit `abf2860`) provided the only path used
  to create the backend repo record; it auto-hides when
  `NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID` is configured for the live TC-026B
  slice.
- Regen-reset frontend fix (commit `abf2860`) cleared the previously saved
  card the moment a new preview generated, preventing the "stale saved card
  on new preview" UX bug.

## Decision

Passed for the local/fake save path, confirmed by both automated regression
(290 Python tests + clean TypeScript) and a full manual browser smoke of
all six cases on 2026-05-25. TC-026 proves the product contract for saving a
draft-ready SAD preview into the connected project repo model without live
Google writes. TC-025 wiki update approval and TC-027 deployment remain out
of scope. Live Drive/Docs/OAuth/Secret Manager work is deferred to a future
TC-026B after explicit approval.
