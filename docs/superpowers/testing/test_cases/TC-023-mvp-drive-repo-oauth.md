# TC-023 MVP Drive Repo OAuth

Date Created: 2026-05-11
Last Updated: 2026-05-14
Status: Passed

## Purpose

Verify user-owned Drive repo selection/creation, Drive/Docs OAuth grant storage, persistent grant use, and Disconnect Google Drive.

## Inputs

- Signed-in Google user
- Drive/Docs OAuth consent flow
- Existing or newly created Drive folder
- Backend token store

## Preconditions

TC-019 passed.

## API / Docs Preflight

Official docs checked before coding:

- Google Identity Services authorization model: `https://developers.google.com/identity/oauth2/web/guides/choose-authorization-model`
- Google Identity Services code model: `https://developers.google.com/identity/oauth2/web/guides/use-code-model`
- Google Identity Services JavaScript reference: `https://developers.google.com/identity/oauth2/web/reference/js-reference`
- Google Picker overview: `https://developers.google.com/workspace/drive/picker/guides/overview`
- Drive folder create and folder parents: `https://developers.google.com/workspace/drive/api/guides/folder`
- Drive search files/folders: `https://developers.google.com/workspace/drive/api/guides/search-files`
- Google OAuth scopes: `https://developers.google.com/identity/protocols/oauth2/scopes`

Preflight decision:

- For persistent backend Drive/Docs access, SADify should use the Google Identity Services authorization code model, not the browser token model, because code flow supports backend exchange and refresh-token storage.
- Scope intent remains least-privilege first: `https://www.googleapis.com/auth/drive.file` for app-created/selected Drive files and folders. Docs creation may later require `https://www.googleapis.com/auth/documents` during the save checkpoint.
- TC-023 local implementation should prove the backend-mediated grant contract, repo record, folder structure planning, and disconnect behavior before real Drive writes.
- Live OAuth requires a Google OAuth Web Client ID and backend client secret/token exchange setup. If those are missing, UI must show configuration-needed state rather than pretending the repo is connected.
- No Cloud Run deployment, Firestore cloud write, Secret Manager write, or Drive folder write should happen in this checkpoint unless explicitly approved.

## Steps

1. Sign in.
2. Connect project repo.
3. Request Drive/Docs permission only during repo connection.
4. Select existing folder or create new folder.
5. Store grant securely through backend token store.
6. Disconnect Google Drive.
7. Confirm grant is revoked/deleted and saves are blocked.

## Expected Output

User owns the selected project repo, backend can use the stored grant, and disconnect removes save access without repeated login.

## Real Output

MVP worktree `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold` now has:

- Backend `/drive/repo/connect`, `/drive/repo/disconnect`, and `/drive/repo/status` routes.
- Signed-in-only Drive repo actions protected by Firebase bearer-token verification.
- Local `DriveRepoRepository` grant records with stable `DG-` IDs, owner UID/email, repo folder ID/name, requested scopes, repo URL, folder structure, and save-blocking state.
- Planned project repo folder structure:
  - `Sources`: original uploaded files, never overwrite.
  - `SAD`: versioned human-facing SAD Google Docs.
  - `Wiki`: latest living project brain.
  - `_SADify`: manifest, extraction text, backups, logs, and metadata.
- Authorization codes are accepted by the backend contract but are not returned in responses.
- Disconnect removes the active repo for that owner and marks saves blocked.
- Frontend `DriveRepoPanel` between draft and source upload sections.
- Frontend Google Identity Services authorization-code client helper using `https://www.googleapis.com/auth/drive.file`.
- Config-aware UI: when `NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID` is missing, the connect button is disabled and the UI shows `Configuration needed`.

## Differences / Issues

- This checkpoint proves the local OAuth/repo contract and UI readiness, not the live Google OAuth exchange.
- No refresh token was exchanged or stored yet. Token storage is still `local_metadata_only`.
- No Secret Manager write happened.
- No real Drive folder, Google Doc, wiki file, source file, or manifest was created.
- Live OAuth still needs a Google OAuth Web Client ID, approved redirect/origin setup, backend OAuth client secret/token exchange, and a secure token store.
- Google Picker/select-existing-folder is not wired yet; this slice supports the backend contract and create-new-repo path placeholder.
- Deployed two-service smoke remains deferred until the deployment checkpoint.

## Evidence

- API/docs preflight recorded above using official Google Identity Services, Drive, Picker, and OAuth scope docs.
- Red test first: `pytest tests/api/test_drive_repo.py tests/test_mvp_drive_repo_oauth_ui.py -q` initially failed with `ModuleNotFoundError: No module named 'sadify_api.services.drive_repo'`.
- Focused tests after implementation: `5 passed in 1.17s`.
- Full Python regression: `127 passed in 9.81s`.
- TypeScript check: `node ...\typescript\bin\tsc -p ...\apps\web\tsconfig.json --noEmit` exited `0`.
- Production build: `npm --prefix ...\apps\web run build` completed successfully.
- Browser smoke on `http://127.0.0.1:3011/` found `Project repo`, `Connect Google Drive`, `Disconnect Google Drive`, and `Configuration needed`, with zero console warnings/errors.
- Temporary smoke server on port `3011` was stopped after validation.

## Decision

Passed for the local MVP-08 gate. Stop here and wait for user approval before MVP-09 / TC-024 SAD preview and IT readiness.
