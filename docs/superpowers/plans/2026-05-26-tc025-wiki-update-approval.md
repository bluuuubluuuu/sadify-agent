# TC-025 Wiki Update Approval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let signed-in users update a single `Wiki/Wiki.md` Markdown file inside their connected `SADify Projects` Drive folder, composed from the latest saved SAD and project metadata. The update is gated by an explicit user click. If the remote `Wiki.md` has been edited since SADify last wrote it, the user sees a diff/warning and chooses Overwrite or Cancel. First-time writes (no remote `Wiki.md` yet) skip the modal.

**Architecture:** New backend endpoints `POST /sad/wiki/preview` (compose + remote-hash check, no write) and `POST /sad/wiki/update` (commits the write). Both live-mode-only behind the same double env gate as TC-026B (`SADIFY_DRIVE_MODE=live` + `SADIFY_DRIVE_LIVE_ENABLED=1`). New `WikiComposer` service builds Markdown from the latest `SadSaveRecord` + project metadata. `DriveClient` gains `find_file_in_folder` / `download_text_file` / `upload_or_replace_text_file` so the wiki can be read, hashed, and overwritten. A new in-memory `WikiStateRepository` remembers the last-known hash per repo so remote drift is detectable. Frontend adds an **Update wiki** button on `SadPreviewPanel` (shown only after a successful save) plus a small dialog component that renders a unified diff for the conflict case.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, pytest, Next.js/React, TypeScript. No new backend dependencies (`googleapiclient` already pulled in by TC-026B). No new npm dependencies — diff rendering is plain HTML/CSS using `diff` if already present, otherwise a hand-rolled line-by-line render.

---

Date: 2026-05-26

Status: Draft - awaiting approval

## Traceability Sources

- `CLAUDE.md`
- `context.md`
- `docs/superpowers/CURRENT.md`
- `docs/superpowers/plans/2026-05-25-tc026-local-sad-save.md`
- `docs/superpowers/plans/2026-05-25-tc026b-live-drive-docs.md`
- `docs/superpowers/testing/test_cases/TC-025-mvp-wiki-update-approval.md`
- `docs/superpowers/testing/test_cases/TC-026-mvp-drive-docs-save.md`
- `docs/superpowers/testing/test_cases/TC-026B-mvp-live-drive-docs.md`
- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `docs/superpowers/development/04_google_cloud_setup_runbook.md`
- `docs/superpowers/development/05_development_workflow.md`
- `docs/superpowers/development/07_decision_log.md`

## Pre-Plan Decisions (locked)

| Decision | Choice |
|---|---|
| Wiki format | `Wiki/Wiki.md` Markdown text file inside the existing project folder structure |
| Trigger | Manual **Update wiki** button shown only after a successful SAD save |
| Content | Latest SAD condensed + project metadata, overwrite-in-full each update |
| Conflict policy | Fetch remote `Wiki.md`, compare hash to last-known. If different, show diff and require explicit Overwrite/Cancel |
| First-time wiki | Create silently when no remote `Wiki.md` exists yet (no approval modal) |
| Local mode parity | Live mode only. Button hidden in local mode. |

## Cloud Prerequisites (already in place)

No new cloud setup needed. TC-026B already enabled the Drive API, the OAuth client, and the per-user refresh token in Secret Manager. The `Wiki/` subfolder is already created automatically by `find_or_create_folder` if it doesn't exist; we only need to extend `DriveClient` with text-file read/write.

## Scope Lock

In scope:

- Backend live-mode `POST /sad/wiki/preview` returning the proposed Markdown, the remote file's current hash (or `null`), and a `requires_confirmation: bool` flag.
- Backend live-mode `POST /sad/wiki/update` that writes the Markdown to `Wiki/Wiki.md`, optionally creating the file if missing, replacing it if present.
- Conflict detection: server reads remote hash before writing. If remote hash != client-supplied `expected_remote_hash`, return 409 unless `force_overwrite=true`.
- New `WikiComposer` service to turn `SadSaveRecord` + project metadata into Markdown.
- New `WikiStateRepository` in-memory store of `(repo_grant_id -> last_known_hash, last_updated_at)`.
- Drive client extensions for text file find/download/upload-or-replace.
- Frontend **Update wiki** button on `SadPreviewPanel` after save.
- Frontend confirmation dialog component that renders the proposed Markdown side-by-side with the remote on conflict.
- Mocked backend tests for compose, hash, write, first-time, conflict-detected, conflict-resolved-with-force, conflict-canceled, live-mode gate.
- Two new manual smoke cases (Cases 11 + 12) for first-time write and conflict-after-edit.

Out of scope:

- Local-fake mode parity (deferred; TC-025 is live-mode-only).
- Wiki content templates beyond the single condensed-latest-SAD format.
- Per-section wiki files or multi-page wikis.
- Diff editing UI (Markdown is replaced wholesale; no in-app editor).
- Schema changes to `DriveRepoRecord`, `SadSaveRecord`, `SadSaveArtifact`,
  `SadSaveManifest`.
- TC-027 Cloud Run deployment.
- New env vars or new dependencies.

## Endpoint Contracts

Both endpoints require Firebase Authorization header + the user has an active live-mode repo (`token_store=secret_manager`).

### `POST /sad/wiki/preview` — live mode only

Request body:

```json
{}
```

Response 200 body:

```json
{
  "proposed_markdown": "# SADify Project Wiki\n\n...",
  "remote_hash": "sha256:abc...",
  "last_known_hash": "sha256:abc...",
  "requires_confirmation": false,
  "remote_exists": true,
  "remote_markdown": "<current remote text or null>"
}
```

Semantics:

- `remote_exists=false` if `Wiki/Wiki.md` does not exist yet.
- `requires_confirmation=true` iff `remote_exists=true` AND `remote_hash != last_known_hash`.
- `remote_markdown` is only populated when `requires_confirmation=true` (used by the frontend to render the diff). Otherwise `null`.

Stable rejection codes:

| Case | HTTP | Stable code | Message |
| --- | --- | --- | --- |
| Unsigned-in or invalid auth | 401 | `WIKI_AUTH_REQUIRED` | `Sign in before updating the wiki.` |
| No active repo | 409 | `WIKI_REPO_REQUIRED` | `Connect a Google Drive project repo before updating the wiki.` |
| Repo disconnected | 409 | `WIKI_REPO_DISCONNECTED` | `Reconnect Google Drive before updating the wiki.` |
| No prior SAD save in this repo | 409 | `WIKI_SAVE_REQUIRED` | `Save a SAD preview to this repo before generating a wiki.` |
| Live mode disabled | 503 | `WIKI_LIVE_MODE_DISABLED` | `Live wiki updates are disabled for this process.` |
| Drive read fails | 502 | `WIKI_REMOTE_READ_FAILED` | `Could not read the existing wiki file.` |

### `POST /sad/wiki/update` — live mode only

Request body:

```json
{
  "expected_remote_hash": "sha256:abc... or null",
  "force_overwrite": false
}
```

Semantics:

- Backend re-reads remote, computes hash, compares to `expected_remote_hash`. If they disagree AND `force_overwrite=false` AND `remote_exists=true`, return 409 `WIKI_CONFLICT`.
- On success: composes Markdown, writes to `Wiki/Wiki.md` (creates if missing, replaces if present), updates `WikiStateRepository` with the new hash + timestamp.
- First-time writes (no remote file) are allowed even if `expected_remote_hash=null` and `force_overwrite=false`.

Response 200 body:

```json
{
  "wiki_path": "Wiki/Wiki.md",
  "wiki_url": "https://drive.google.com/file/d/.../view",
  "wiki_file_id": "1abc...",
  "wiki_hash": "sha256:def...",
  "updated_at": "2026-05-26T10:00:00Z",
  "created_new_file": false
}
```

Stable rejection codes (additions to the preview set):

| Case | HTTP | Stable code | Message |
| --- | --- | --- | --- |
| Hash mismatch, no force | 409 | `WIKI_CONFLICT` | `The wiki was changed in Drive since SADify last wrote it. Confirm overwrite.` |
| Drive write fails | 502 | `WIKI_WRITE_FAILED` | `Google Drive rejected the wiki update.` |

Idempotency: same `expected_remote_hash` + same composed content + remote unchanged returns the previous response (re-computed hash will match).

## Schema Contract

No new Pydantic models on existing data types. New request/response models added in `schemas.py`:

- `WikiPreviewRequest` (empty body but keep for symmetry / future).
- `WikiPreviewResponse` (fields above).
- `WikiUpdateRequest` (`expected_remote_hash: str | None`, `force_overwrite: bool = False`).
- `WikiUpdateResponse` (fields above).

`SadSaveRepository`, `DriveRepoRecord`, `SadSaveRecord` are not touched. `WikiStateRepository` is a new in-memory dict keyed by `repo_grant_id`.

## Files To Change

Backend (worktree path
`D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`):

- Create: `services/api/src/sadify_api/services/wiki_compose.py`
- Create: `services/api/src/sadify_api/services/wiki_state.py`
- Modify: `services/api/src/sadify_api/services/drive_client.py` (add find/download/upload-or-replace text helpers)
- Modify: `services/api/src/sadify_api/routes/sad.py` (add the two endpoints)
- Modify: `services/api/src/sadify_api/main.py` (wire `WikiStateRepository`)
- Modify: `services/api/src/sadify_api/schemas.py` (add the 4 new request/response models — append-only)
- Test: `tests/api/test_wiki_compose.py`
- Test: `tests/api/test_wiki_state.py`
- Test: `tests/api/test_drive_client_text_files.py` (extension of existing drive_client tests, or a new file — match existing convention)
- Test: `tests/api/test_wiki_routes.py`

Frontend:

- Modify: `apps/web/src/lib/api.ts` (add types + `previewWikiUpdate()` + `commitWikiUpdate()`)
- Modify: `apps/web/src/components/SadPreviewPanel.tsx` (add **Update wiki** button after save)
- Create: `apps/web/src/components/WikiUpdateDialog.tsx` (new dialog component for the conflict path)
- Test: `tests/test_mvp_wiki_ui.py` (static checks like the existing UI test files)

Docs (after Task 7 passes):

- Modify: `docs/superpowers/testing/test_cases/TC-025-mvp-wiki-update-approval.md`
- Modify: `docs/superpowers/CURRENT.md`
- Modify: `docs/superpowers/testing/test_case_index.md`
- Modify: `docs/superpowers/development/07_decision_log.md`

## Task 0: Approval Gate

**Files:** Read this plan only.

- [ ] **Step 0.1: Wait for user approval.** Do not modify code until the user explicitly approves this plan.
- [ ] **Step 0.2: Confirm worktree.** Latest commit is `95d1eda chore(drive): clean up TC-026B env var naming and OAuth scope relaxation`. Working tree is clean.

## Task 1: Wiki Composer

**Files:** Create `services/wiki_compose.py`, test `tests/api/test_wiki_compose.py`.

- [ ] **Step 1.1: Write tests first.**

Cover:

```text
test_compose_includes_project_name_and_requirement_text
test_compose_links_to_latest_sad_doc_url
test_compose_lists_saved_sad_ids_in_order
test_compose_includes_one_line_section_summaries
test_compose_lists_source_file_names_when_present
test_compose_handles_no_sources
test_compose_handles_missing_assumptions
test_compose_returns_pure_markdown_with_no_html_tags
```

- [ ] **Step 1.2: Implement `compose_wiki_markdown(...)`.**

Public function:

```python
def compose_wiki_markdown(
    *,
    repo: DriveRepoRecord,
    latest_save: SadSaveRecord,
    all_saves_for_repo: list[SadSaveRecord],
    sources: list[SourceRecord],
    requirement_text: str,
) -> str
```

Output structure (final layout owned by tests):

```markdown
# SADify Project Wiki

**Project repo:** {repo.repo_folder_name}
**Updated:** {ISO timestamp}

## Latest SAD

[{latest_save.preview_id}]({latest_save.sad_doc.url})

### Requirement
{requirement_text}

### Section summaries
- **{section.title}:** {first sentence of section.body}

## Sources
- {source.original_file_name}

## Save history
- {save_id} — {save.created_at} — [doc]({save.sad_doc.url})
```

Markdown escaping reuses the existing helper from `sad_markdown.py` if it's exposed; otherwise duplicate the same backslash-escape logic for `\\ * _ ` [ ]`.

- [ ] **Step 1.3: Run tests.** Expect all 8 pass.

## Task 2: Wiki State Repository

**Files:** Create `services/wiki_state.py`, test `tests/api/test_wiki_state.py`.

- [ ] **Step 2.1: Write tests first.**

Cover:

```text
test_get_state_returns_none_when_unset
test_record_write_persists_hash_and_timestamp
test_record_write_replaces_prior_state_for_same_repo
test_independent_state_per_repo_grant_id
```

- [ ] **Step 2.2: Implement `WikiStateRepository`.**

Methods:

```python
def get_state(self, repo_grant_id: str) -> WikiState | None
def record_write(self, repo_grant_id: str, file_id: str, hash_value: str, updated_at: datetime) -> None
```

`WikiState` dataclass holds `file_id, hash, updated_at`.

Module factory `get_wiki_state_repository()` returns a singleton — match `get_sad_save_repository()`.

- [ ] **Step 2.3: Run tests.** Expect 4 pass.

## Task 3: Drive Client Text-File Helpers

**Files:** Modify `services/drive_client.py`, extend `tests/api/test_drive_client.py` (or new file matching repo convention).

- [ ] **Step 3.1: Write tests first.** Patch `googleapiclient.discovery.build`. Cover:

```text
test_find_file_in_folder_returns_id_when_present
test_find_file_in_folder_returns_none_when_absent
test_download_text_file_returns_decoded_string
test_upload_or_replace_text_file_creates_when_missing
test_upload_or_replace_text_file_updates_when_present
test_upload_or_replace_text_file_returns_web_view_link
test_text_helpers_propagate_drive_errors_as_drive_folder_create_error_or_new_dedicated_exception
```

- [ ] **Step 3.2: Add helpers to `DriveClient`.**

```python
def find_file_in_folder(self, *, access_token: str, folder_id: str, name: str, mime_type: str | None = None) -> DriveFileRef | None
def download_text_file(self, *, access_token: str, file_id: str) -> str
def upload_or_replace_text_file(self, *, access_token: str, folder_id: str, name: str, mime_type: str, content: str, existing_file_id: str | None = None) -> DriveUploadResult
```

New dataclass `DriveFileRef(file_id, name, mime_type, web_view_link, md5_checksum)`. Reuse the existing `DriveUploadResult`.

New exception `DriveTextFileError`. Map to `WIKI_REMOTE_READ_FAILED` and `WIKI_WRITE_FAILED` at the route level.

- [ ] **Step 3.3: Run tests.** Expect 7 pass; existing drive_client tests still green.

## Task 4: Routes

**Files:** Modify `routes/sad.py`, `main.py`, `schemas.py`, test `tests/api/test_wiki_routes.py`.

- [ ] **Step 4.1: Add the 4 Pydantic models to schemas.py.** Append-only.

- [ ] **Step 4.2: Write route tests first.** Inject mocked `SecretStore`, `DriveClient`, `WikiStateRepository`. Cover:

```text
test_wiki_preview_returns_first_time_write_when_remote_missing
test_wiki_preview_returns_no_confirmation_when_hashes_match
test_wiki_preview_returns_requires_confirmation_when_remote_drifted
test_wiki_preview_blocks_unsigned
test_wiki_preview_blocks_without_active_repo
test_wiki_preview_blocks_when_no_prior_sad_save
test_wiki_preview_blocks_when_live_mode_disabled
test_wiki_update_writes_first_time_without_force
test_wiki_update_writes_when_hashes_match
test_wiki_update_blocks_on_conflict_when_force_false
test_wiki_update_overwrites_when_force_true
test_wiki_update_records_state_after_success
test_wiki_update_surfaces_drive_write_failure_as_502
```

- [ ] **Step 4.3: Implement `POST /sad/wiki/preview` and `POST /sad/wiki/update`.** Reuse the live-services resolver pattern from `routes/drive.py`. Use `compute_sha256` (new tiny helper or inline `hashlib.sha256(b).hexdigest()`) for hashing.

- [ ] **Step 4.4: Wire repository in `main.py`.** Add optional `wiki_state_repository` param; default to `get_wiki_state_repository()` singleton.

- [ ] **Step 4.5: Run all backend wiki tests.** Expect 13 pass.

## Task 5: Frontend API + Button

**Files:** Modify `apps/web/src/lib/api.ts`, `apps/web/src/components/SadPreviewPanel.tsx`, test `tests/test_mvp_wiki_ui.py`.

- [ ] **Step 5.1: Write static UI tests first.** Mirror the pattern of `tests/test_mvp_sad_save_ui.py`. Cover:

```text
test_wiki_ui_files_exist
test_api_ts_exports_wiki_preview_and_commit_functions
test_sad_preview_panel_renders_update_wiki_button_after_save
test_wiki_update_dialog_renders_diff_when_conflict_present
test_wiki_state_resets_when_preview_is_regenerated
```

- [ ] **Step 5.2: Add types and helpers to api.ts.** Append `WikiPreviewResponse`, `WikiUpdateResponse`, `previewWikiUpdate(idToken)`, `commitWikiUpdate(idToken, expectedRemoteHash, forceOverwrite)`.

- [ ] **Step 5.3: Add **Update wiki** button to `SadPreviewPanel`.** Show only when `saveResponse !== null` AND `isGoogleOAuthConfigured()` is true. Reset `wikiResponse` and `wikiDialogState` in the same `useEffect` that clears save state.

## Task 6: WikiUpdateDialog Component

**Files:** Create `apps/web/src/components/WikiUpdateDialog.tsx`.

- [ ] **Step 6.1: Build the dialog.** Plain modal (no new deps). Two states:

```text
First-time / hashes match: render a brief "Wiki will be updated" confirmation and a single Update button. No diff.
Conflict: render the proposed Markdown and the remote Markdown side-by-side (or stacked on narrow viewports), with Overwrite and Cancel buttons.
```

Simple line-by-line diff helper inside the component is fine — no `diff` library dep.

- [ ] **Step 6.2: Wire dialog to SadPreviewPanel.** Update button click calls `previewWikiUpdate()`. If `requires_confirmation=false`, immediately call `commitWikiUpdate(..., expected_remote_hash, force_overwrite=false)`. If `requires_confirmation=true`, open the dialog; Overwrite triggers `commitWikiUpdate(..., expected_remote_hash, force_overwrite=true)`; Cancel closes the dialog.

- [ ] **Step 6.3: TypeScript gate.**

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web
npx -y tsc --noEmit
```

Expected: clean.

## Task 7: Verification and Manual Smoke

**Files:** None to modify.

- [ ] **Step 7.1: Full Python regression with `SADIFY_DRIVE_MODE=local`.**

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
set "PYTHONPATH=services\api\src;src;."
set "SADIFY_DRIVE_MODE=local"
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest -q
```

Expected: 332 (TC-026B baseline) + ~30 new tests, all green.

- [ ] **Step 7.2: TypeScript gate.** As above. Expected clean.

- [ ] **Step 7.3: Live manual browser smoke.** Two new cases. Drip-fed by the assistant.

```text
Case 11 (first-time wiki write):
   - Connect live repo, save a SAD, click Update wiki.
   - Expect: no dialog (first time), wiki.md created at Wiki/Wiki.md,
     saved card shows wiki URL.
   - Drive console shows Wiki/Wiki.md with composed Markdown.

Case 12 (conflict-detected wiki write):
   - With wiki existing, edit Wiki.md manually in Drive (add a line).
   - In SADify, click Update wiki.
   - Expect: dialog opens with diff. Click Cancel — backend log shows
     409 WIKI_CONFLICT, no write. Click Update wiki again, Overwrite.
     Expect 200, remote restored to composed content.
```

- [ ] **Step 7.4: Commit.** Single commit:

```text
feat(wiki): live wiki update with conflict-aware approval
```

## Task 8: Documentation Closure

- [ ] **Step 8.1: Update TC-025 evidence.** Real Output / Differences / Evidence / Decision.
- [ ] **Step 8.2: CURRENT.md.** Flip Phase 5 → fully complete; next is TC-027 deploy.
- [ ] **Step 8.3: Decision-log entry.** One row noting TC-025 wiki update approval shipped, manual + auto trigger split, conflict-aware policy.
- [ ] **Step 8.4: test_case_index.md.** Flip TC-025 row.

## Stop Rules

Stop immediately if any of these happens:

- Plan is not yet approved by the user.
- A live wiki write would happen while `SADIFY_DRIVE_MODE=local` or `SADIFY_DRIVE_LIVE_ENABLED` unset.
- Drive client text helpers require new dependencies (none should — Drive API supports text upload via existing `googleapiclient.http.MediaInMemoryUpload`).
- Schema changes are proposed beyond appending the 4 new request/response models.
- A new env var seems necessary.
- Existing 332 pytest tests fail after any task.

Honor `CLAUDE.md` sections 1, 2, 4.1, 4.2, 4.3, 5.1, 6, 7.1, 7.2, 7.3.

## Verification Summary Required Before Completion

```text
Backend new-module test counts (wiki_compose, wiki_state, drive_client text).
Backend route test count (wiki_routes).
Full pytest count with SADIFY_DRIVE_MODE=local.
TypeScript --noEmit result.
Live manual browser smoke results for Cases 11 and 12.
Confirmation that Wiki/Wiki.md exists in Drive with composed content.
Confirmation that manual remote edit triggers the conflict path and the
Cancel path leaves the remote untouched.
Confirmation that no refresh token, OAuth client secret, or wiki content
appears in logs.
```
