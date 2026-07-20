# TC-026B Live Drive/Docs Save Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire SADify's existing save contract to real Google Drive and Google Docs writes, with the OAuth refresh token stored in Secret Manager. The local/fake save path (TC-026) stays fully working behind an env switch so offline tests and dev-mode UX are unaffected.

**Architecture:** A backend env switch `SADIFY_DRIVE_MODE` selects between the existing local repository behavior and a new live path. In live mode, `/drive/repo/connect` exchanges the GIS authorization code for tokens, persists the refresh token to Secret Manager (`sadify-drive-token-<uid>`), creates a `SADify Projects` Drive folder if missing, and stores the real folder ID on the `DriveRepoRecord`. `/sad/save` refreshes the access token, converts the SAD preview to Markdown, uploads it via the Drive API with MIME conversion to a Google Doc, and returns the real `file_id` + `webViewLink`. `/drive/repo/disconnect` deletes the user's token secret. The existing `SadSaveRecord` / artifact schema stays unchanged.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, pytest, Next.js/React, TypeScript. New backend dependencies: `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, `google-cloud-secret-manager`. No new npm dependencies.

---

Date: 2026-05-25

Status: Draft - awaiting approval

## Traceability Sources

- `CLAUDE.md`
- `context.md`
- `docs/superpowers/CURRENT.md`
- `docs/superpowers/plans/2026-05-25-tc026-local-sad-save.md`
- `docs/superpowers/testing/test_cases/TC-026-mvp-drive-docs-save.md`
- `docs/superpowers/testing/test_cases/TC-023-mvp-drive-repo-oauth.md`
- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `docs/superpowers/development/04_google_cloud_setup_runbook.md` (TC-026B section, completed 2026-05-25)
- `docs/superpowers/development/05_development_workflow.md`
- `docs/superpowers/development/07_decision_log.md`

## Pre-Plan Decisions (locked)

| Decision | Choice |
|---|---|
| Folder UX | Create-new only; folder name `SADify Projects` |
| Doc body | Markdown upload with Drive MIME conversion to Doc |
| Token storage | `sadify-drive-token-<firebase-uid>`, version-added on refresh |
| Local fallback | Kept behind `SADIFY_DRIVE_MODE=local\|live` env switch (default `local`) |
| Retry policy | None; Drive/Docs errors propagate as 502 with upstream message |

## Cloud Prerequisites (already completed in console on 2026-05-25)

These were verified before this plan was written. See runbook section
"TC-026B Live Drive/Docs Setup (Completed 2026-05-25)" for full detail.

- Drive API, Docs API, Secret Manager API enabled.
- OAuth Web client `SADify Web (TC-026B)` exists; Client ID
  `594758969655-0md22e7bs1hvjjg1ihpokvvtpuarq6pp.apps.googleusercontent.com`.
- Client secret stored at
  `D:\GoogleCloudHack\.secrets\sadify-drive-oauth-client.txt` AND in Secret
  Manager as `sadify-drive-oauth-client-secret` v1.
- Both `sadify-agent-sa` and `firebase-adminsdk-fbsvc` have:
  - Secret Manager Secret Accessor on `sadify-drive-oauth-client-secret`
  - Project-level Secret Manager Admin (to create `sadify-drive-token-<uid>` secrets)

## Scope Lock

In scope:

- Backend live OAuth authorization-code exchange via the existing
  GIS code from the frontend.
- Backend refresh-token persistence in Secret Manager
  (`sadify-drive-token-<uid>`).
- Backend live folder create/find via Drive API
  (`SADify Projects` folder if not already present).
- Backend live Markdown-to-Doc upload via Drive API
  (`files.create` with `mimeType=application/vnd.google-apps.document` and
  source `text/markdown`).
- Backend disconnect path: delete the user's token secret.
- `SADIFY_DRIVE_MODE=local|live` env switch with `local` as default for
  pytest and uvicorn dev runs unless `live` is explicitly set.
- Frontend env wiring of `NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID` so the
  existing live Connect Google Drive button activates and the local-dev
  button auto-hides.
- Backend tests with mocked Google clients for all live-mode branches.
- One opt-in live-mode smoke test gated by `SADIFY_TC026B_LIVE=1`.

Out of scope:

- Drive Picker / folder browsing UI (folder is always
  auto-created/discovered by name).
- Doc-level styling via Docs API `batchUpdate` (Markdown conversion is
  sufficient for the demo).
- Retry/backoff on Drive errors (errors propagate as-is).
- TC-025 wiki update approval.
- TC-027 Cloud Run deployment.
- Schema changes to `DriveRepoRecord`, `SadSaveRecord`, `SadSaveArtifact`,
  `SadSaveManifest` (existing fields already accommodate real Google IDs).

## Endpoint Contract Deltas

Endpoints stay the same. Behavior changes only when
`SADIFY_DRIVE_MODE=live`.

### `POST /drive/repo/connect` — live mode

Request body unchanged. New behavior:

1. Read OAuth client secret from Secret Manager
   (`sadify-drive-oauth-client-secret`).
2. Exchange `authorization_code` with Google token endpoint.
3. On success, receive `access_token`, `refresh_token`, `expiry`.
4. Store `refresh_token` in Secret Manager:
   - If `sadify-drive-token-<uid>` does not exist, create it.
   - Add a new version with the refresh token as payload.
5. Use the access token to:
   - Search for a folder named `SADify Projects` owned by the user.
   - If not found, create it.
6. Build `DriveRepoRecord` with:
   - `repo_folder_id` = real Drive folder ID
   - `repo_folder_name` = `SADify Projects`
   - `repo_url` = `https://drive.google.com/drive/folders/<folder_id>`
   - `token_store` = `secret_manager`
   - `saves_blocked` = `false`
7. Return the record.

Stable error cases in live mode:

| Case | HTTP | Stable code | Message |
| --- | --- | --- | --- |
| Token exchange fails | 502 | `DRIVE_OAUTH_EXCHANGE_FAILED` | `Could not complete Google Drive sign-in.` |
| Folder create fails | 502 | `DRIVE_FOLDER_CREATE_FAILED` | `Could not create the SADify Projects folder.` |
| Secret Manager write fails | 502 | `DRIVE_TOKEN_PERSIST_FAILED` | `Could not securely store your Drive permission.` |

Local-mode behavior is unchanged: stub code is accepted, fake folder ID is
generated, `token_store=local_metadata_only`.

### `POST /drive/repo/disconnect` — live mode

After the existing local disconnect logic, if the disconnected record had
`token_store=secret_manager`, delete the `sadify-drive-token-<uid>` secret
(all versions). Errors deleting the secret are logged but do not block
disconnect — the local record is still marked disconnected.

### `POST /sad/save` — live mode

Validation unchanged (auth, repo state, preview lookup, idempotency).
After the local record is computed:

1. If `SADIFY_DRIVE_MODE=local`: return the local record as today.
2. If `SADIFY_DRIVE_MODE=live`:
   - Read refresh token from `sadify-drive-token-<uid>`.
   - Refresh access token via Google token endpoint.
   - Build Markdown body from `preview_record.preview` (see Task 4).
   - Upload via Drive API: `files.create` with
     `parents=[repo_folder_id]`,
     `mimeType=application/vnd.google-apps.document`,
     `name=<sad_title>`,
     body=markdown,
     source mimeType `text/markdown`.
   - Replace the artifact's `file_id` and `url` on the in-memory record
     with the real `id` and `webViewLink` from the Drive response.
   - Persist the updated record back into the repository so subsequent
     idempotent calls return the same real Drive doc.

Stable live-mode error cases:

| Case | HTTP | Stable code | Message |
| --- | --- | --- | --- |
| Missing refresh token | 409 | `SAD_SAVE_TOKEN_MISSING` | `Reconnect Google Drive before saving.` |
| Refresh token rejected | 401 | `SAD_SAVE_TOKEN_INVALID` | `Reconnect Google Drive to renew permission.` |
| Drive upload fails | 502 | `SAD_SAVE_DRIVE_UPLOAD_FAILED` | `Google Drive rejected the upload.` |

Idempotency note: the idempotency key still includes
`preview_record.created_at.isoformat()` as `preview_revision`. A repeat
save in live mode returns the existing record and does NOT re-upload to
Drive. If a previously live-saved record has a real `file_id`, it is
returned verbatim. This avoids creating duplicate Drive docs on
double-click.

## Schema Contract

No new Pydantic models. Field-value semantics change only:

- `DriveRepoRecord.token_store` may now equal `secret_manager`
  (previously only `local_metadata_only`). No new literal needed because
  the field type is plain `str`.
- `SadSaveArtifact.file_id` and `url` may now hold real Google values
  (`1AbcXyz...`, `https://docs.google.com/document/d/.../edit`). Field
  types already accept these.
- `SadSaveManifest.artifact_paths` continues to hold the same
  Drive-relative paths.

Schema deviation approved 2026-05-25: `schemas.py` `token_store` Literal gains
one value `secret_manager`. Append-only; no rename or removal. The existing
`secret_manager_pending` value is preserved for the intermediate state where
token exchange succeeded but the Secret Manager write has not.

## Configuration

Backend env (`.env.example` + `.env`):

```text
SADIFY_DRIVE_MODE=local
SADIFY_GOOGLE_OAUTH_CLIENT_ID=594758969655-0md22e7bs1hvjjg1ihpokvvtpuarq6pp.apps.googleusercontent.com
SADIFY_GOOGLE_OAUTH_CLIENT_SECRET_NAME=sadify-drive-oauth-client-secret
SADIFY_DRIVE_FOLDER_NAME=SADify Projects
SADIFY_TC026B_LIVE=                       # leave empty unless running the opt-in live smoke
```

Frontend env (`apps/web/.env.local`):

```text
NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID=594758969655-0md22e7bs1hvjjg1ihpokvvtpuarq6pp.apps.googleusercontent.com
```

Default `SADIFY_DRIVE_MODE=local` ensures pytest and the default uvicorn
dev run stay offline. Setting it to `live` is what activates everything
in this plan.

## Files To Change

Backend (worktree path
`D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`):

- Create: `services/api/src/sadify_api/services/secret_store.py`
- Create: `services/api/src/sadify_api/services/drive_client.py`
- Create: `services/api/src/sadify_api/services/sad_markdown.py`
- Modify: `services/api/src/sadify_api/services/drive_repo.py`
- Modify: `services/api/src/sadify_api/services/sad_save.py`
- Modify: `services/api/src/sadify_api/routes/drive.py`
- Modify: `services/api/src/sadify_api/routes/sad.py`
- Modify: `services/api/src/sadify_api/config.py`
- Modify: `services/api/src/sadify_api/main.py`
- Modify: `services/api/pyproject.toml` (deps)
- Modify: `requirements.txt` (deps mirror, if used by tests/CI)
- Modify: `.env.example` (root)
- Modify: `.env.example` (worktree)
- Test: `tests/api/test_secret_store.py`
- Test: `tests/api/test_drive_client.py`
- Test: `tests/api/test_sad_markdown.py`
- Test: `tests/api/test_drive_repo_live_mode.py`
- Test: `tests/api/test_sad_save_live_mode.py`
- Test (opt-in live, gated by `SADIFY_TC026B_LIVE=1`):
  `tests/api/test_tc026b_live_smoke.py`

Frontend:

- Modify: `apps/web/.env.local` (or document the user-managed file)
- Modify: `apps/web/.env.example`

No frontend code changes are needed — the existing
`isGoogleOAuthConfigured()` gate and `requestDriveAuthorizationCode()`
helper already cover the live path. The local-dev button from
commit `abf2860` auto-hides when the env var is set.

Docs (after Task 8 passes):

- Modify: `docs/superpowers/testing/test_cases/TC-026-mvp-drive-docs-save.md`
  (add TC-026B addendum or create a sibling TC-026B file — see Task 8)
- Modify: `docs/superpowers/CURRENT.md`
- Modify: `docs/superpowers/testing/test_case_index.md`
- Modify: `docs/superpowers/development/07_decision_log.md`

## Task 0: Approval Gate

**Files:** Read this plan only.

- [ ] **Step 0.1: Wait for user approval**

Do not modify code or install dependencies until the user explicitly
approves this plan.

- [ ] **Step 0.2: Confirm worktree and cloud prerequisites**

Run:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
git status --short
git log --oneline -5
```

Expected:

```text
Latest commit is abf2860 (feat(web): add local dev connect + reset save state on preview regen).
Working tree is clean.
```

Spot-check that the cloud-setup runbook section "TC-026B Live Drive/Docs
Setup (Completed 2026-05-25)" exists in
`docs/superpowers/development/04_google_cloud_setup_runbook.md`.

Confirm `.secrets/sadify-drive-oauth-client.txt` contains a real
`CLIENT_SECRET=GOCSPX-...` value on disk (do not echo it to logs).

## Task 1: Backend Dependencies

**Files:** `services/api/pyproject.toml`, `requirements.txt` (if applicable).

- [ ] **Step 1.1: Add Python dependencies**

Add to `services/api/pyproject.toml` `[project.dependencies]`:

```text
google-api-python-client>=2.130,<3
google-auth>=2.30,<3
google-auth-oauthlib>=1.2,<2
google-cloud-secret-manager>=2.20,<3
```

If `requirements.txt` is the lockfile actually consumed by pytest/CI in
this repo, mirror the same pins there.

- [ ] **Step 1.2: Install and verify**

```cmd
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pip install -r services\api\pyproject.toml-or-equivalent
D:\GoogleCloudHack\.venv\Scripts\python.exe -c "import googleapiclient, google.auth, google_auth_oauthlib, google.cloud.secretmanager"
```

Expected: imports succeed, no resolver errors.

## Task 2: Secret Store Service

**Files:** Create `services/api/src/sadify_api/services/secret_store.py`,
test `tests/api/test_secret_store.py`.

- [ ] **Step 2.1: Write `tests/api/test_secret_store.py` first**

Use `unittest.mock` to patch
`google.cloud.secretmanager.SecretManagerServiceClient`. Cover:

```text
test_get_oauth_client_secret_returns_payload_text
test_put_user_refresh_token_creates_secret_when_missing
test_put_user_refresh_token_adds_version_when_secret_exists
test_get_user_refresh_token_returns_latest_version
test_get_user_refresh_token_returns_none_when_secret_missing
test_delete_user_secret_removes_all_versions
test_delete_user_secret_ignores_missing_secret
```

Run pytest; expect failures because the module does not exist yet.

- [ ] **Step 2.2: Implement `secret_store.py`**

Public class `SecretStore` with methods:

```python
def get_oauth_client_secret(self) -> str
def put_user_refresh_token(self, uid: str, refresh_token: str) -> None
def get_user_refresh_token(self, uid: str) -> str | None
def delete_user_secret(self, uid: str) -> None
```

Module-level factory `get_secret_store()` returns a singleton bound to
the project resolved from
`config.google_cloud_project`.

Secret name builder: `f"sadify-drive-token-{uid}"`. Validate that uid
matches `^[A-Za-z0-9_-]+$` (Firebase UIDs are alphanumeric + `_-`); raise
`ValueError` otherwise to prevent secret-name injection.

- [ ] **Step 2.3: Run tests**

Expected: all 7 tests pass. Full pytest suite still green.

## Task 3: Drive Client Service

**Files:** Create
`services/api/src/sadify_api/services/drive_client.py`, test
`tests/api/test_drive_client.py`.

- [ ] **Step 3.1: Write `tests/api/test_drive_client.py` first**

Patch `googleapiclient.discovery.build` and
`google.oauth2.credentials.Credentials.refresh`. Cover:

```text
test_exchange_authorization_code_returns_tokens
test_exchange_authorization_code_surfaces_invalid_grant_error
test_refresh_access_token_returns_new_access_token
test_refresh_access_token_propagates_invalid_token_error
test_find_or_create_folder_returns_existing_when_present
test_find_or_create_folder_creates_when_missing
test_upload_markdown_as_doc_returns_id_and_link
test_upload_markdown_as_doc_propagates_drive_error
```

- [ ] **Step 3.2: Implement `drive_client.py`**

Public class `DriveClient` with:

```python
def __init__(self, *, client_id: str, client_secret: str): ...
def exchange_authorization_code(self, code: str, redirect_uri: str) -> DriveTokens: ...
def refresh_access_token(self, refresh_token: str) -> str: ...
def find_or_create_folder(self, access_token: str, folder_name: str) -> DriveFolder: ...
def upload_markdown_as_doc(
    self,
    *,
    access_token: str,
    folder_id: str,
    title: str,
    markdown: str,
) -> DriveUploadResult: ...
```

Dataclasses `DriveTokens(access_token, refresh_token, expiry)`,
`DriveFolder(folder_id, name)`,
`DriveUploadResult(file_id, web_view_link)`.

Use `google_auth_oauthlib.flow.Flow` for code exchange and
`google.oauth2.credentials.Credentials` for refresh. Use
`googleapiclient.discovery.build("drive", "v3", ...)`. Upload via
`MediaIoBaseUpload` with `mimetype="text/markdown"` and the create call's
`body={"mimeType": "application/vnd.google-apps.document", ...}`.

- [ ] **Step 3.3: Run tests**

Expected: all 8 tests pass.

## Task 4: SAD Markdown Composer

**Files:** Create
`services/api/src/sadify_api/services/sad_markdown.py`, test
`tests/api/test_sad_markdown.py`.

- [ ] **Step 4.1: Write `tests/api/test_sad_markdown.py` first**

Use `VALID_PREVIEW` fixture from `tests/api/test_sad_preview.py`. Cover:

```text
test_compose_emits_h1_title
test_compose_emits_h2_per_section
test_compose_includes_assumptions_list_when_present
test_compose_includes_open_questions_list_when_present
test_compose_includes_source_references_footer
test_compose_handles_missing_sections_gracefully
test_compose_escapes_markdown_special_chars_in_section_text
```

- [ ] **Step 4.2: Implement `sad_markdown.py`**

Public function:

```python
def compose_sad_markdown(preview: SadPreviewResponse) -> str
```

Output structure:

```markdown
# {preview.title}

_{preview.subtitle if any}_

## {section.title}

{section.body}

## Assumptions

- {assumption}
- ...

## Open Questions

- {question}
- ...

## Source References

- {ref}
- ...
```

Escape `\`, `*`, `_`, `` ` ``, `[`, `]` in body text via simple
backslash-escape. Skip empty lists silently.

- [ ] **Step 4.3: Run tests**

Expected: all 7 tests pass.

## Task 5: Drive Repo Live-Mode Branch

**Files:** Modify
`services/api/src/sadify_api/services/drive_repo.py`,
`services/api/src/sadify_api/routes/drive.py`,
`services/api/src/sadify_api/config.py`, test
`tests/api/test_drive_repo_live_mode.py`.

- [ ] **Step 5.1: Add config flag**

In `config.py`, add to the loader:

```python
drive_mode: Literal["local", "live"]
drive_folder_name: str
google_oauth_client_id: str
google_oauth_client_secret_name: str
```

Source from env with defaults `local`, `SADify Projects`,
`""`, `sadify-drive-oauth-client-secret`. Use empty string default for
the client ID so local mode does not require it.

- [ ] **Step 5.2: Write `test_drive_repo_live_mode.py` first**

Inject a mocked `SecretStore` and mocked `DriveClient`. Cover:

```text
test_live_connect_exchanges_code_and_stores_refresh_token
test_live_connect_creates_folder_when_missing
test_live_connect_finds_existing_folder
test_live_connect_surfaces_oauth_exchange_failure_as_502
test_live_connect_surfaces_folder_create_failure_as_502
test_live_connect_surfaces_secret_write_failure_as_502
test_live_disconnect_deletes_user_secret
test_live_disconnect_tolerates_missing_secret
test_local_connect_unchanged_when_mode_is_local
```

- [ ] **Step 5.3: Modify `DriveRepoRepository.connect_repo`**

Add a `mode: str` parameter and optional `drive_client`,
`secret_store`, `drive_folder_name`, `oauth_client_id` parameters
(injectable for tests). Default `mode="local"` preserves all existing
behavior and idempotency tests.

Live branch logic per "Endpoint Contract Deltas" → connect section above.

- [ ] **Step 5.4: Modify `routes/drive.py`**

Pass live-mode args from `config` into `repository.connect_repo()`. Map
live-mode `ValueError` subclasses (e.g.,
`DriveOauthExchangeError`, `DriveFolderCreateError`,
`DriveTokenPersistError`) to the stable error codes from the contract
table above.

Same wiring on `disconnect`.

- [ ] **Step 5.5: Run tests**

Expected: all 9 new tests pass. Existing
`tests/api/test_drive_repo.py` still passes unchanged.

## Task 6: SAD Save Live-Mode Branch

**Files:** Modify `services/api/src/sadify_api/services/sad_save.py`,
`services/api/src/sadify_api/routes/sad.py`, test
`tests/api/test_sad_save_live_mode.py`.

- [ ] **Step 6.1: Write `test_sad_save_live_mode.py` first**

Inject mocked `SecretStore` and `DriveClient`. Cover:

```text
test_live_save_uploads_markdown_and_returns_real_doc_id
test_live_save_uses_real_web_view_link
test_live_save_returns_existing_record_on_idempotent_repeat_without_reupload
test_live_save_blocks_when_refresh_token_missing
test_live_save_blocks_when_refresh_token_invalid
test_live_save_surfaces_drive_upload_failure_as_502
test_live_save_persists_real_ids_into_repository
test_local_save_unchanged_when_mode_is_local
```

- [ ] **Step 6.2: Modify `SadSaveRepository.save_preview`**

Add `mode`, `drive_client`, `secret_store`, optional injection args.
Default `mode="local"` keeps TC-026 behavior.

Live branch logic per "Endpoint Contract Deltas" → save section above.
Use `sad_markdown.compose_sad_markdown` to build the body.

Idempotent repeat must not re-upload; if the cached record has a real
`file_id`, return it.

- [ ] **Step 6.3: Modify `routes/sad.py`**

Pass live-mode args from `config`. Map live-mode errors to:

```text
SAD_SAVE_TOKEN_MISSING        → 409
SAD_SAVE_TOKEN_INVALID        → 401
SAD_SAVE_DRIVE_UPLOAD_FAILED  → 502
```

- [ ] **Step 6.4: Run tests**

Expected: all 8 new tests pass. Existing
`tests/api/test_sad_save.py` still passes unchanged.

## Task 7: Frontend Env Wiring

**Files:** `apps/web/.env.local` (user-owned, not committed),
`apps/web/.env.example`.

- [ ] **Step 7.1: Document the env in `.env.example`**

Append:

```text
NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID=
```

with a comment that setting it activates the live OAuth path and hides
the local-dev connect button.

- [ ] **Step 7.2: No code changes**

The existing `isGoogleOAuthConfigured()` gate and
`requestDriveAuthorizationCode()` flow already cover the live path. The
local-dev button auto-hides via `!isGoogleOAuthConfigured()`.

- [ ] **Step 7.3: TypeScript gate**

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web
npx -y tsc --noEmit
```

Expected: clean, no errors.

## Task 8: Verification and Manual Smoke

**Files:** None to modify. Pure verification.

- [ ] **Step 8.1: Full Python regression with `SADIFY_DRIVE_MODE=local`**

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
set "PYTHONPATH=services\api\src;src;."
set "SADIFY_DRIVE_MODE=local"
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest -q
```

Expected: previous 290 + new tests pass; existing TC-026 tests untouched
in behavior.

- [ ] **Step 8.2: Opt-in live smoke (manual, not part of regression)**

User runs this only when ready to verify against real Drive:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
set "PYTHONPATH=services\api\src;src;."
set "SADIFY_DRIVE_MODE=live"
set "SADIFY_TC026B_LIVE=1"
set "GOOGLE_APPLICATION_CREDENTIALS=D:\GoogleCloudHack\.secrets\sadify-firebase-adminsdk-fbsvc-ac7a32c920.json"
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_tc026b_live_smoke.py -q -s
```

Expected: a real Drive folder and Doc are created; test asserts real
`file_id` shape and `https://docs.google.com/document/d/.../edit` URL.

- [ ] **Step 8.3: Manual browser smoke**

Set `NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID` in `apps/web/.env.local`. Set
`SADIFY_DRIVE_MODE=live` for the backend. Restart both servers.

Run the same 6 cases as TC-026, plus two new live-only cases:

```text
Case 9 (live happy path): real OAuth consent shown, real Drive folder
   created (or reused), saved card shows real .google.com URL that opens
   a real Doc with SAD content.
Case 10 (live disconnect): token secret is deleted from Secret Manager;
   the gcloud-cli check `gcloud secrets versions list
   sadify-drive-token-<uid>` returns empty.
```

Drip-fed one case at a time per the saved manual-smoke pattern.

- [ ] **Step 8.4: Commit**

Single commit per slice (backend then frontend if needed), message:

```text
feat(drive): live drive/docs save behind SADIFY_DRIVE_MODE=live
```

## Task 9: Documentation Closure

**Files:**
`docs/superpowers/testing/test_cases/TC-026-mvp-drive-docs-save.md`
or new `TC-026B-*.md`,
`docs/superpowers/CURRENT.md`,
`docs/superpowers/testing/test_case_index.md`,
`docs/superpowers/development/07_decision_log.md`.

- [ ] **Step 9.1: Decide doc location**

Either append a "TC-026B Live Slice" section to TC-026, OR create a
sibling `TC-026B-mvp-live-drive-docs.md` test case. Recommended: sibling
file so the live slice has its own evidence trail and Decision row.

- [ ] **Step 9.2: Fill in evidence**

Record:

```text
Backend test counts (mocked live mode).
Full pytest count with SADIFY_DRIVE_MODE=local.
TypeScript clean.
Opt-in live smoke result with real file_id and web_view_link.
Manual browser smoke results for Cases 9 and 10.
Secret Manager state after disconnect (versions deleted).
```

- [ ] **Step 9.3: Update CURRENT.md**

Flip Phase 5 status: TC-026B live Drive/Docs save passed. Next slice is
TC-025 wiki update approval (now has a real save target).

- [ ] **Step 9.4: Append decision-log entry**

```text
2026-MM-DD | TC-026B live Drive/Docs save shipped behind SADIFY_DRIVE_MODE=live | Live path uses real Drive folder + Markdown→Doc upload + Secret Manager refresh tokens; local mode preserved for offline tests | TC-026B, CURRENT, test index, runbook
```

- [ ] **Step 9.5: Flip test_case_index row**

Add or update a TC-026B row with date and passed/blocked status.

## Stop Rules

Stop immediately if any of these happens:

- Plan is not yet approved by the user.
- Cloud setup runbook section "TC-026B Live Drive/Docs Setup" is missing
  or incomplete.
- `D:\GoogleCloudHack\.secrets\sadify-drive-oauth-client.txt` does not
  contain a real `CLIENT_SECRET=GOCSPX-...` value.
- Any backend dependency install fails or pulls a new transitive
  dependency in a way that breaks the existing 290-test baseline.
- An attempt is made to call live Google APIs while
  `SADIFY_DRIVE_MODE=local` or while `SADIFY_TC026B_LIVE` is unset.
- Refresh token would be written to disk or logs at any point.
- Schema changes are proposed beyond field-value semantics (any new
  Pydantic field or Literal needs explicit user approval).
- The local-fake save behavior changes in any way under
  `SADIFY_DRIVE_MODE=local`.

Honor `CLAUDE.md` sections 1, 2, 4.1, 4.2, 4.3, 5.1, 6, 7.1, 7.2, 7.3
throughout execution. In practical terms:

```text
Read current docs and code before editing.
Tests before implementation for every new module.
No silent dependency installs; list and justify each one.
No new env vars beyond those listed in this plan.
Existing 290 tests must remain green in local mode.
No live Google call may happen without SADIFY_DRIVE_MODE=live AND
SADIFY_TC026B_LIVE=1 both set.
Refresh tokens live in Secret Manager only; never written to disk,
.env files, or logs.
```

## Verification Summary Required Before Completion

```text
Backend new-module test counts (secret_store, drive_client, sad_markdown).
Backend live-mode test counts (drive_repo, sad_save).
Full pytest count with SADIFY_DRIVE_MODE=local.
TypeScript --noEmit result.
Opt-in live smoke pass evidence (real file_id, real webViewLink, folder
URL).
Manual browser smoke pass for Cases 9 and 10.
Confirmation that local-mode behavior is unchanged from TC-026 baseline.
Confirmation that no refresh token appears on disk, in logs, or in any
.env file at any point.
```
