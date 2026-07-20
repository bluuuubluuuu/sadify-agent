# TC-025B Encyclopedia Wiki Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the TC-025A single-file `Wiki/Wiki.md` snapshot with a multi-file Obsidian-style knowledge wiki per `context.md` lines 439-468. After a SAD save the user clicks **Update wiki** and SADify writes eight Markdown files into `SADify Projects/Wiki/`: one categorized note per knowledge area (`requirements.md`, `actors.md`, `workflows.md`, `entities.md`, `decisions.md`, `reports.md`, `sources.md`) plus `Wiki.md` as the index page that cross-links to every note via `[[wiki links]]`. Each note carries minimal YAML frontmatter. Before overwriting existing notes the system snapshots the current `Wiki/` tree into `_SADify/wiki-backups/<iso-timestamp>/`. Hash-based conflict detection extends per-file so the dialog can list which files drifted in Drive.

**Architecture:** Reuse the live OAuth + Secret Manager + `DriveClient` + `WikiStateRepository` infrastructure shipped in TC-025A. Rewrite `wiki_compose` from a single composer to one composer per category plus an index composer. The composer receives both the latest `SadSaveRecord` and the corresponding `SadPreviewResponse`; the preview is the required source of section bodies and fixes the TC-025A section-summary bug. Extend `WikiStateRepository` to track per-file hashes keyed by `(repo_grant_id, file_name)`. Add a `wiki_backup` service that, before the first overwrite of any existing managed wiki file, copies the eight files this slice owns into `_SADify/wiki-backups/<iso-timestamp>/`. The two existing endpoints (`POST /sad/wiki/preview`, `POST /sad/wiki/update`) keep their paths but change their response shape from singleton to list. Frontend `WikiUpdateDialog` extends to enumerate which files changed and require a single bulk **Overwrite all** confirmation.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, pytest, Next.js/React, TypeScript. No new backend dependencies (Drive API helpers exist; `hashlib`, `datetime` already used). No new npm dependencies.

---

Date: 2026-05-27

Status: Draft - awaiting approval

## Traceability Sources

- `CLAUDE.md`
- `context.md` (wiki section, lines 439-468)
- `docs/superpowers/CURRENT.md`
- `docs/superpowers/plans/2026-05-25-tc026b-live-drive-docs.md`
- `docs/superpowers/plans/2026-05-26-tc025-wiki-update-approval.md`
- `docs/superpowers/testing/test_cases/TC-025A-mvp-wiki-snapshot.md`
- `docs/superpowers/testing/test_cases/TC-026B-mvp-live-drive-docs.md`
- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `docs/superpowers/development/04_google_cloud_setup_runbook.md`
- `docs/superpowers/development/05_development_workflow.md`
- `docs/superpowers/development/07_decision_log.md`

## Pre-Plan Decisions (locked)

| Decision | Choice |
|---|---|
| File set per project | Fixed seven categories from `context.md`: `requirements.md`, `actors.md`, `workflows.md`, `entities.md`, `decisions.md`, `reports.md`, `sources.md`. Plus `Wiki.md` as the index. |
| Index `Wiki.md` content | Menu/TOC with project metadata header (project name, latest SAD link, updated timestamp) followed by a categorized list of `[[wiki links]]` to every other note. |
| `[[wiki links]]` resolution | Filename only without extension, Obsidian convention. Example: `[[actors]]`, not `[[Wiki/actors.md]]`. |
| YAML frontmatter | Minimal three fields per note: `title`, `tags` (list), `updated_at` (ISO-8601). Index `Wiki.md` also carries `project`, `repo_folder`, `latest_save_id`. |
| Conflict policy | Bulk approval. If any of the eight files has drifted, the dialog lists each changed file path and asks for a single **Overwrite all** confirmation. Cancel aborts the entire update. |
| Backup strategy | Before any overwrite, snapshot all currently known managed wiki files (the eight files this slice owns) into `_SADify/wiki-backups/<iso-timestamp>/`. User-created `.md` files in `Wiki/` are not backed up and are not overwritten. Backups are write-once, never modified. First-time wiki writes (no remote files yet) skip backup. |

## SAD-Section → Wiki-Category Mapping

| Wiki note | SAD section(s) feeding it | Plus |
|---|---|---|
| `requirements.md` | `goal_scope` | `preview.assumptions`, `preview.open_questions`, raw requirement text |
| `actors.md` | `users_roles` + `access_permissions` | role table extracted from access section |
| `workflows.md` | `workflow_steps` + `exceptions_edges` | step list, handoffs, exception cases |
| `entities.md` | `data_records` | field list, status enumerations |
| `decisions.md` | `rules_approvals` + `non_functional` | triggering rules, approval paths, NFR decisions |
| `reports.md` | `reports_summaries` + `integrations` | report list, owner, external system list |
| `sources.md` | uploaded sources for the latest save | source IDs, filenames, extracted text snippets |
| `Wiki.md` (index) | metadata only | links to every other note |

Section routing rule: each `SadPreviewSection.title` is normalized
(lower-case, strip punctuation, collapse whitespace) and matched against
the table below. Multiple matches concatenate into the same category
file. Unmatched sections go into `requirements.md` under an "Other"
subsection so no content is lost.

| Normalized title contains | Routes to |
|---|---|
| `goal`, `scope` | `requirements.md` |
| `user`, `role`, `actor` | `actors.md` |
| `access`, `permission` | `actors.md` |
| `workflow`, `step`, `flow`, `handoff` | `workflows.md` |
| `exception`, `edge case` | `workflows.md` |
| `data`, `record`, `field`, `entity` | `entities.md` |
| `rule`, `approval` | `decisions.md` |
| `non-functional`, `non functional`, `nfr` | `decisions.md` |
| `report`, `summary` | `reports.md` |
| `integration` | `reports.md` |
| no match | `requirements.md` under "Other" |

`requirements.md` also always pulls in `preview.assumptions` and
`preview.open_questions` regardless of section routing.

## Cloud Prerequisites

None new. TC-026B + TC-025A already enabled Drive API, OAuth client, Secret Manager, and the `Wiki/` subfolder creation. `_SADify/` folder will be created on first backup write using the existing `find_or_create_folder(parent_folder_id=...)` helper.

## Scope Lock

In scope:

- Eight Markdown files written into `SADify Projects/Wiki/` on every update.
- Per-category content composition driven by the latest `SadSaveRecord` and its preview sections.
- Obsidian-style `[[wiki links]]` in the index and inline within notes where they cross-reference.
- YAML frontmatter on every note (minimal: title, tags, updated_at; index also carries project/repo/latest_save_id).
- Per-file hash tracking in `WikiStateRepository`.
- Backup of all currently known managed wiki files (the eight files this slice owns) to `_SADify/wiki-backups/<iso-timestamp>/` before any overwrite occurs in a given update call. User-created `.md` files in `Wiki/` are left untouched and unbacked-up.
- `POST /sad/wiki/preview` returns a list of file-level previews plus a `requires_confirmation` aggregate flag and the list of changed file names.
- `POST /sad/wiki/update` writes all eight files atomically (best-effort: if a write fails mid-batch, surface 502 with the partial state so the user can retry).
- Frontend `WikiUpdateDialog` shows the list of changed files when a conflict is detected and requires a single bulk **Overwrite all** action.
- Two new manual smoke cases (Cases 13 + 14).
- Replace the old TC-025A composer; remove `compose_wiki_markdown` and related single-file path.

Out of scope:

- Editing wiki notes from inside SADify.
- Per-file independent conflict approval. Bulk only.
- Granular partial save (any error rolls forward; user retries the whole update).
- Pagination / chunking of large notes (current SADs fit in a single Markdown body easily).
- Hosting a Obsidian vault directly; we just emit Obsidian-compatible files.
- TC-027 Cloud Run deploy.
- Schema changes to `DriveRepoRecord`, `SadSaveRecord`, `SadSaveArtifact`, `SadSaveManifest`, or any non-wiki model.

## Endpoint Contract Deltas

Endpoints stay at the same paths. Request and response shapes change to lists.

### `POST /sad/wiki/preview` — live mode only

Request body:

```json
{}
```

Response 200 body:

```json
{
  "files": [
    {
      "relative_path": "Wiki/Wiki.md",
      "name": "Wiki.md",
      "category": "index",
      "proposed_markdown": "...",
      "remote_hash": "sha256:...",
      "last_known_hash": "sha256:...",
      "remote_exists": true,
      "requires_confirmation": false,
      "remote_markdown": null
    },
    { "relative_path": "Wiki/requirements.md", ... },
    { "relative_path": "Wiki/actors.md", ... },
    { "relative_path": "Wiki/workflows.md", ... },
    { "relative_path": "Wiki/entities.md", ... },
    { "relative_path": "Wiki/decisions.md", ... },
    { "relative_path": "Wiki/reports.md", ... },
    { "relative_path": "Wiki/sources.md", ... }
  ],
  "requires_confirmation": false,
  "changed_files": [],
  "first_time_write": false
}
```

Semantics:

- `files` always contains exactly 8 entries in fixed order: `Wiki.md`, `requirements.md`, `actors.md`, `workflows.md`, `entities.md`, `decisions.md`, `reports.md`, `sources.md`.
- A file's `requires_confirmation` is `true` iff `remote_exists=true` AND `remote_hash != last_known_hash`.
- Top-level `requires_confirmation` is `true` iff any file's `requires_confirmation` is `true`.
- Top-level `changed_files` lists the `name` of each file with `requires_confirmation=true`.
- Top-level `first_time_write` is `true` iff none of the eight files exist remotely (allows the dialog to skip itself even without state).
- Each file's `remote_markdown` is populated only when that file's `requires_confirmation=true`; otherwise `null`.

Stable rejection codes (same set as TC-025A, semantics unchanged):

```text
WIKI_AUTH_REQUIRED        401
WIKI_REPO_REQUIRED        409
WIKI_REPO_DISCONNECTED    409
WIKI_SAVE_REQUIRED        409
WIKI_LIVE_MODE_DISABLED   503
WIKI_REMOTE_READ_FAILED   502
```

### `POST /sad/wiki/update` — live mode only

Request body:

```json
{
  "expected_remote_hashes": {
    "Wiki.md": "sha256:...",
    "requirements.md": "sha256:...",
    "...": "..."
  },
  "force_overwrite": false
}
```

`expected_remote_hashes` keys are file names (no path). Missing keys are treated as `null` (file did not exist client-side).

Semantics:

1. Re-read every existing remote file, recompute hashes.
2. For each file, if `remote_exists=true` AND `remote_hash != expected_remote_hashes[name]` AND `force_overwrite=false`, the entire update aborts with 409 `WIKI_CONFLICT` and a `changed_files` payload listing the conflicting names.
3. If any remote managed file exists, backup the currently known managed wiki files that exist remotely into `_SADify/wiki-backups/<iso-timestamp>/` before writing.
4. Compose all eight files in memory.
5. Write all eight files. For each: create if missing, replace if present. Record new hashes into `WikiStateRepository`.
6. Return per-file results.

Response 200 body:

```json
{
  "files": [
    {
      "relative_path": "Wiki/Wiki.md",
      "name": "Wiki.md",
      "category": "index",
      "file_id": "1abc...",
      "web_view_link": "https://drive.google.com/file/d/.../view",
      "hash": "sha256:...",
      "created_new_file": false
    },
    ...
  ],
  "backup": {
    "created": true,
    "path": "_SADify/wiki-backups/2026-05-27T10-15-30Z/",
    "file_count": 8
  },
  "updated_at": "2026-05-27T10:15:31Z"
}
```

If no backup was needed (first-time write), `backup.created=false`, `backup.file_count=0`, `backup.path=""`.

New stable rejection codes:

```text
WIKI_CONFLICT             409   detail.changed_files lists the file names that drifted
WIKI_WRITE_FAILED         502
WIKI_BACKUP_FAILED        502
```

Idempotency: a fresh `POST /sad/wiki/preview` followed by
`POST /sad/wiki/update` is repeat-safe. After a successful update,
re-running preview will see `remote_hash == last_known_hash` for every
file, so `requires_confirmation=false` and a subsequent update writes the
same content with no backup. Re-running update with stale
`expected_remote_hashes` after a successful write returns 409 because
the remote hashes have changed; the client must re-preview before
re-updating. No update-response cache.

## Schema Contract

New models added to `schemas.py` (append-only):

- `WikiFilePreview` (per-file preview entry, fields listed above).
- `WikiFileResult` (per-file write result).
- `WikiBackupInfo` (backup metadata).

Replacing models from TC-025A (these existed but their semantics change; same names retained):

- `WikiPreviewResponse` — now wraps a `list[WikiFilePreview]` plus aggregates.
- `WikiUpdateRequest` — `expected_remote_hashes: dict[str, str | None]` (was singleton `expected_remote_hash`).
- `WikiUpdateResponse` — now wraps a `list[WikiFileResult]` plus `backup` and `updated_at`.

No other model is touched. `DriveRepoRecord`, `SadSaveRecord`, etc. untouched.

## Configuration

No new env vars. No new defaults. The existing five flags from TC-026B
and TC-025A cover live mode entirely:

```text
SADIFY_DRIVE_MODE
SADIFY_DRIVE_LIVE_ENABLED
SADIFY_GOOGLE_OAUTH_CLIENT_ID
SADIFY_GOOGLE_OAUTH_CLIENT_SECRET_NAME
SADIFY_DRIVE_FOLDER_NAME
```

## Files To Change

Backend (worktree path
`D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`):

- Replace: `services/api/src/sadify_api/services/wiki_compose.py`
  (delete old `compose_wiki_markdown`, add `compose_wiki_files()` returning a list and per-category helpers).
- Create: `services/api/src/sadify_api/services/wiki_backup.py`
- Modify: `services/api/src/sadify_api/services/wiki_state.py`
  (extend storage to per-file hashes; back-compat removal of any single-file API is fine, TC-025A used same module).
- Modify: `services/api/src/sadify_api/services/drive_client.py`
  (no new helpers expected; reuse `find_or_create_folder(parent_folder_id=...)`, `find_file_in_folder`, `download_text_file`, `upload_or_replace_text_file`).
- Modify: `services/api/src/sadify_api/routes/sad.py`
  (rewrite both wiki routes to operate on the eight-file list; integrate backup step).
- Modify: `services/api/src/sadify_api/schemas.py`
  (append new models; redefine the four wiki request/response models in place).
- Modify: `services/api/src/sadify_api/main.py`
  (no change expected; existing `wiki_state_repository` injection still works).
- Test rewrite: `tests/api/test_wiki_compose.py`
  (replace single-file assertions with per-category assertions).
- Test new: `tests/api/test_wiki_backup.py`
- Test rewrite: `tests/api/test_wiki_state.py`
  (per-file hash storage).
- Test rewrite: `tests/api/test_wiki_routes.py`
  (multi-file preview + update + backup integration + bulk conflict).

Frontend:

- Modify: `apps/web/src/lib/api.ts`
  (update wiki types and helper signatures to match new request/response shapes).
- Modify: `apps/web/src/components/SadPreviewPanel.tsx`
  (update button still triggers preview; route the new list-shaped response into the dialog).
- Modify: `apps/web/src/components/WikiUpdateDialog.tsx`
  (render the list of changed files with their names; single bulk Overwrite all button).
- Modify: `tests/test_mvp_wiki_ui.py`
  (static checks updated for new types and dialog behavior).

Docs (after Task 8 passes):

- Create: `docs/superpowers/testing/test_cases/TC-025B-mvp-encyclopedia-wiki.md`
- Modify: `docs/superpowers/CURRENT.md`
- Modify: `docs/superpowers/testing/test_case_index.md`
- Modify: `docs/superpowers/development/07_decision_log.md`

## Task 0: Approval Gate

**Files:** Read this plan only.

- [ ] **Step 0.1: Wait for user approval.** Do not modify code until the user explicitly approves this plan.
- [ ] **Step 0.2: Confirm worktree.** Latest commit is `8e19296 fix(wiki): write Wiki.md into Wiki/ subfolder instead of project root`. Working tree is clean.

## Task 1: Per-Category Composers

**Files:** Replace `services/wiki_compose.py`, rewrite `tests/api/test_wiki_compose.py`.

- [ ] **Step 1.1: Write tests first.**

Cover at least:

```text
test_compose_index_renders_yaml_frontmatter_with_project_metadata
test_compose_index_links_to_every_other_note_via_wiki_links
test_compose_requirements_includes_goal_scope_assumptions_open_questions
test_compose_actors_combines_users_roles_and_access_permissions
test_compose_workflows_combines_workflow_steps_and_exceptions_edges
test_compose_entities_uses_data_records_section
test_compose_decisions_combines_rules_approvals_and_non_functional
test_compose_reports_combines_reports_summaries_and_integrations
test_compose_sources_lists_source_ids_filenames_and_snippets
test_each_note_has_minimal_yaml_frontmatter_with_title_tags_updated_at
test_compose_returns_exactly_eight_entries_in_fixed_order
test_compose_handles_missing_sections_gracefully
```

- [ ] **Step 1.2: Implement `compose_wiki_files(...)`.**

Public function:

```python
def compose_wiki_files(
    *,
    repo: DriveRepoRecord,
    latest_save: SadSaveRecord,
    latest_preview: SadPreviewResponse,
    all_saves_for_repo: list[SadSaveRecord],
    sources: list[SourceRecord],
    requirement_text: str,
    composed_at: datetime | None = None,
) -> list[WikiFileDraft]
```

`WikiFileDraft` is a dataclass with `name`, `category`, `markdown`. The function returns exactly eight drafts in fixed order: `Wiki.md`, `requirements.md`, `actors.md`, `workflows.md`, `entities.md`, `decisions.md`, `reports.md`, `sources.md`.

Each draft begins with YAML frontmatter:

```markdown
---
title: <human title>
tags: [<category>, sadify]
updated_at: <iso8601>
---
```

The index file's frontmatter also includes:

```yaml
project: <repo.repo_folder_name>
repo_folder_id: <repo.repo_folder_id>
latest_save_id: <latest_save.save_id>
```

Cross-links in the index use `[[<name-without-md>]]` (e.g., `[[actors]]`). Inline cross-links may appear in body text where natural (e.g., requirements.md mentioning `see [[actors]] for role list`).

- [ ] **Step 1.3: Run tests.** Expect ≥12 tests pass.

## Task 2: Wiki Backup Service

**Files:** Create `services/wiki_backup.py`, test `tests/api/test_wiki_backup.py`.

- [ ] **Step 2.1: Write tests first.**

Cover:

```text
test_backup_returns_skipped_when_no_remote_files
test_backup_creates_timestamped_subfolder_in_sadify_wiki_backups
test_backup_copies_each_existing_remote_md_into_subfolder
test_backup_returns_metadata_with_path_and_file_count
test_backup_propagates_drive_error_as_wiki_backup_error
```

- [ ] **Step 2.2: Implement.**

```python
def snapshot_existing_wiki_files(
    *,
    drive_client: DriveClient,
    access_token: str,
    repo_folder_id: str,
    existing_files: list[DriveFileRef],
    backup_root_name: str = "_SADify",
    backups_subfolder_name: str = "wiki-backups",
    now: datetime | None = None,
) -> WikiBackupInfo
```

Behavior:

```text
If existing_files is empty -> return WikiBackupInfo(created=False, path="", file_count=0).
Otherwise:
  - find_or_create_folder("_SADify", parent_folder_id=repo_folder_id)
  - find_or_create_folder("wiki-backups", parent_folder_id=<_SADify id>)
  - find_or_create_folder("<iso-timestamp>", parent_folder_id=<wiki-backups id>)
    where <iso-timestamp> is "YYYY-MM-DDTHH-MM-SSZ" (colon-free for Drive name safety).
  - For each existing file, download_text_file then upload_or_replace_text_file
    into the new timestamp folder under the same name and mime type.
  - Return WikiBackupInfo(created=True, path=full_relative_path, file_count=n).
```

New exception `WikiBackupError` mapped to `WIKI_BACKUP_FAILED` at the route.

- [ ] **Step 2.3: Run tests.** Expect 5 pass.

## Task 3: WikiStateRepository — Per-File Hashes

**Files:** Modify `services/wiki_state.py`, rewrite `tests/api/test_wiki_state.py`.

- [ ] **Step 3.1: Write tests first.**

Cover:

```text
test_get_file_state_returns_none_when_unset
test_record_file_write_persists_hash_and_timestamp_per_file
test_record_file_write_replaces_only_that_file_state
test_get_all_states_returns_known_files_for_repo
test_clear_states_for_repo_removes_all_entries
```

- [ ] **Step 3.2: Modify the repository.**

New shape:

```python
class WikiState:
    file_name: str
    file_id: str
    hash: str
    updated_at: datetime

class WikiStateRepository:
    def get_file_state(self, repo_grant_id: str, file_name: str) -> WikiState | None
    def get_all_states(self, repo_grant_id: str) -> dict[str, WikiState]
    def record_file_write(self, repo_grant_id: str, state: WikiState) -> None
    def clear_states_for_repo(self, repo_grant_id: str) -> None
```

The TC-025A single-file methods are removed. No back-compat shim needed (only the wiki route called the old methods; we're rewriting that route too).

- [ ] **Step 3.3: Run tests.** Expect 5 pass.

## Task 4: Schema Updates

**Files:** Modify `services/api/src/sadify_api/schemas.py`.

- [ ] **Step 4.1: Update wiki Pydantic models.**

New helper model:

```python
class WikiFilePreview(ApiModel):
    relative_path: str
    name: str
    category: Literal["index", "requirements", "actors", "workflows", "entities", "decisions", "reports", "sources"]
    proposed_markdown: str
    remote_hash: str | None
    last_known_hash: str | None
    remote_exists: bool
    requires_confirmation: bool
    remote_markdown: str | None
```

New write result:

```python
class WikiFileResult(ApiModel):
    relative_path: str
    name: str
    category: Literal[...]   # same enum
    file_id: str
    web_view_link: str
    hash: str
    created_new_file: bool
```

New backup info:

```python
class WikiBackupInfo(ApiModel):
    created: bool
    path: str
    file_count: int
```

Replace `WikiPreviewResponse`:

```python
class WikiPreviewResponse(ApiModel):
    files: list[WikiFilePreview]
    requires_confirmation: bool
    changed_files: list[str]
    first_time_write: bool
```

Replace `WikiUpdateRequest`:

```python
class WikiUpdateRequest(ApiModel):
    expected_remote_hashes: dict[str, str | None] = Field(default_factory=dict)
    force_overwrite: bool = False
```

Replace `WikiUpdateResponse`:

```python
class WikiUpdateResponse(ApiModel):
    files: list[WikiFileResult]
    backup: WikiBackupInfo
    updated_at: datetime
```

`WikiPreviewRequest` stays as-is (still empty body).

## Task 5: Route Rewrite

**Files:** Modify `services/api/src/sadify_api/routes/sad.py`, rewrite `tests/api/test_wiki_routes.py`.

- [ ] **Step 5.1: Write route tests first.**

Cover at least:

```text
test_wiki_preview_returns_eight_files_in_fixed_order_first_time
test_wiki_preview_marks_requires_confirmation_only_for_drifted_files
test_wiki_preview_first_time_write_flag_when_all_remote_missing
test_wiki_preview_blocks_unsigned_authentication
test_wiki_preview_blocks_without_active_repo
test_wiki_preview_blocks_without_prior_sad_save
test_wiki_preview_blocks_when_live_mode_disabled
test_wiki_update_writes_all_eight_files_first_time_no_backup
test_wiki_update_creates_backup_subfolder_when_remote_files_exist
test_wiki_update_blocks_with_409_conflict_when_any_file_drifts_and_force_false
test_wiki_update_changed_files_payload_lists_drifted_filenames
test_wiki_update_overwrites_all_when_force_true_after_conflict
test_wiki_update_records_per_file_hashes_after_success
test_wiki_update_returns_backup_path_and_file_count
test_wiki_update_surfaces_drive_write_failure_as_502
test_wiki_update_surfaces_backup_failure_as_502_wiki_backup_failed
```

- [ ] **Step 5.2: Rewrite `POST /sad/wiki/preview`.**

Flow:

```text
1. Resolve context (auth, repo, repo state, save existence, live gate, refresh token).
2. find_or_create_folder("Wiki", parent_folder_id=repo.repo_folder_id) -> wiki_folder.
3. For each of the eight expected file names, find_file_in_folder under wiki_folder.
4. For each file: if remote exists, download_text_file + sha256 = remote_hash.
5. Fetch the latest preview via `SadPreviewRepository.get_preview(latest_save.preview_id)`.
   If the preview is no longer in memory, return 409 `WIKI_SAVE_REQUIRED`
   with a message saying the preview must be regenerated before updating
   the wiki.
6. Compose all eight drafts via `compose_wiki_files(..., latest_preview=preview.preview)`.
7. Compute proposed_markdown hashes for each.
8. Look up last_known_hash per file from WikiStateRepository.get_file_state(repo.grant_id, name).
9. Build WikiFilePreview list. requires_confirmation per file = remote_exists AND
   remote_hash != last_known_hash.
10. Aggregate: top-level requires_confirmation = any per-file requires_confirmation.
   changed_files = [name for each file with requires_confirmation=true].
   first_time_write = no remote file existed for any of the eight names.
11. Return WikiPreviewResponse.
```

- [ ] **Step 5.3: Rewrite `POST /sad/wiki/update`.**

Flow:

```text
1. Resolve context.
2. find_or_create_folder("Wiki", parent_folder_id=repo.repo_folder_id) -> wiki_folder.
3. For each of the eight names, find_file_in_folder + (if exists) hash.
4. For each existing remote file: compare remote_hash to request.expected_remote_hashes[name].
   If any mismatch AND not request.force_overwrite -> raise WIKI_CONFLICT with
   changed_files payload.
5. existing_files = [DriveFileRef for each of the eight names that exists remotely].
6. If existing_files is non-empty:
     backup = snapshot_existing_wiki_files(...).
   else:
     backup = WikiBackupInfo(created=False, path="", file_count=0).
7. Fetch the latest preview via `SadPreviewRepository.get_preview(latest_save.preview_id)`.
   If the preview is no longer in memory, return 409 `WIKI_SAVE_REQUIRED`
   with a message saying the preview must be regenerated before updating
   the wiki.
8. Compose all eight drafts.
9. For each draft, upload_or_replace_text_file(folder_id=wiki_folder.folder_id,
   name=draft.name, mime_type="text/markdown", content=draft.markdown,
   existing_file_id=remote_file_id or None).
10. Record per-file hashes via WikiStateRepository.record_file_write.
11. Return WikiUpdateResponse with files list, backup info, and updated_at.
```

Error mapping (added or new):

```text
WIKI_CONFLICT          409  detail.changed_files = [...]
WIKI_WRITE_FAILED      502
WIKI_BACKUP_FAILED     502
```

Existing rejection codes for auth / repo / save / live-disabled / remote-read keep the same paths.

- [ ] **Step 5.4: Run all wiki tests.** Expect ≥16 wiki route tests pass plus the per-category compose tests, backup tests, and state tests.

## Task 6: Frontend Update

**Files:** Modify `apps/web/src/lib/api.ts`, `apps/web/src/components/SadPreviewPanel.tsx`, `apps/web/src/components/WikiUpdateDialog.tsx`, rewrite `tests/test_mvp_wiki_ui.py`.

- [ ] **Step 6.1: Update TypeScript types.**

Mirror the new Pydantic shapes:

```typescript
type WikiFilePreview = { ... };
type WikiFileResult = { ... };
type WikiBackupInfo = { created: boolean; path: string; file_count: number };
type WikiPreviewResponse = {
  files: WikiFilePreview[];
  requires_confirmation: boolean;
  changed_files: string[];
  first_time_write: boolean;
};
type WikiUpdateRequest = {
  expected_remote_hashes: Record<string, string | null>;
  force_overwrite: boolean;
};
type WikiUpdateResponse = {
  files: WikiFileResult[];
  backup: WikiBackupInfo;
  updated_at: string;
};
```

Update `previewWikiUpdate()` and `commitWikiUpdate()` signatures accordingly.

- [ ] **Step 6.2: Update `SadPreviewPanel`.**

The Update wiki button still calls `previewWikiUpdate()`. If
`requires_confirmation=false`, immediately call `commitWikiUpdate({expected_remote_hashes, force_overwrite: false})`. If `true`, open the dialog with the `changed_files` and per-file `WikiFilePreview` list.

- [ ] **Step 6.3: Update `WikiUpdateDialog`.**

Render a list: each entry shows the file name and (optionally) collapsed proposed vs remote text. One bulk **Overwrite all** button at the bottom, plus **Cancel**. Overwrite calls `commitWikiUpdate({expected_remote_hashes, force_overwrite: true})`.

After success, render a confirmation panel listing each written file with its `web_view_link`, plus the backup path when `backup.created=true`.

- [ ] **Step 6.4: Static UI test updates.**

Cover at least:

```text
test_wiki_ui_files_exist
test_api_ts_exports_new_list_shaped_wiki_types
test_sad_preview_panel_routes_response_into_dialog_correctly
test_wiki_dialog_lists_changed_files_when_present
test_wiki_dialog_overwrite_all_button_calls_commit_with_force_true
test_wiki_state_resets_when_preview_is_regenerated
```

- [ ] **Step 6.5: TypeScript gate.**

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web
npx -y tsc --noEmit
```

Expected: clean.

## Task 7: Verification and Manual Smoke

**Files:** None to modify.

- [ ] **Step 7.1: Full Python regression with `SADIFY_DRIVE_MODE=local`.**

Expected: 374 (TC-025A baseline) + new wiki tests + minus retired tests, all green. The number should land roughly in the 390-410 range; the assistant reviews the delta when it's reported.

- [ ] **Step 7.2: TypeScript gate.** As above. Expected clean.

- [ ] **Step 7.3: Live manual browser smoke — Cases 13 and 14.**

Drip-fed one at a time by the assistant.

```text
Case 13 (first-time encyclopedia write):
   - Sign in live, connect Drive, save at least one SAD.
   - Click Update wiki.
   - Expect no dialog (first time), backend POST /sad/wiki/preview 200
     followed by POST /sad/wiki/update 200.
   - Drive shows SADify Projects/Wiki/ with eight new files:
     Wiki.md, requirements.md, actors.md, workflows.md, entities.md,
     decisions.md, reports.md, sources.md.
   - Wiki.md is the index and includes [[wiki links]] to every other note.
   - Each note opens and shows YAML frontmatter + composed content.
   - No backup taken (first-time write).

Case 14 (conflict + backup):
   - With wiki existing from Case 13, download one wiki file (say
     workflows.md), edit it locally, re-upload via Drive UI as a
     new version.
   - In SADify, click Update wiki.
   - Expect WikiUpdateDialog open listing "workflows.md" as the only
     changed file.
   - Click Cancel -> backend log shows only the preview call.
   - Click Update wiki again, then Overwrite all -> backend log shows
     preview then update. Drive shows _SADify/wiki-backups/<timestamp>/
     containing copies of the eight pre-overwrite files (including the
     manually edited workflows.md). Wiki/workflows.md is restored to
     SADify's composed content.
```

- [ ] **Step 7.4: Commit.** Single commit, message:

```text
feat(wiki): encyclopedia knowledge graph with per-file conflict and backup
```

## Task 8: Documentation Closure

- [ ] **Step 8.1: Create `TC-025B-mvp-encyclopedia-wiki.md`.** Full evidence (Cases 13 + 14 results, file paths, backup confirmation, no live calls leaking).
- [ ] **Step 8.2: Update CURRENT.md.** Flip TC-025B to passed; next focus is TC-027.
- [ ] **Step 8.3: Append decision log entry.**
- [ ] **Step 8.4: Flip TC-025B row in test_case_index.md.**

## Stop Rules

Stop immediately if any of these happens:

- Plan is not yet approved.
- A live wiki write would happen while `SADIFY_DRIVE_MODE=local` or `SADIFY_DRIVE_LIVE_ENABLED` unset.
- Existing 374 local-mode pytest tests fail after any task.
- A schema change touches anything beyond the wiki request/response models.
- A new env var or dependency seems necessary.
- Drive API can't list or write multiple files in the same folder without rate-limit drama (unlikely for ~8 files but watch logs).

Honor `CLAUDE.md` sections 1, 2, 4.1, 4.2, 4.3, 5.1, 6, 7.1, 7.2, 7.3.

## Verification Summary Required Before Completion

```text
Backend new-module test counts (wiki_compose, wiki_backup, wiki_state).
Backend route test count (wiki_routes).
Full pytest count with SADIFY_DRIVE_MODE=local.
TypeScript --noEmit result.
Manual browser smoke results for Cases 13 and 14.
Drive console confirmation: eight files in SADify Projects/Wiki/.
Drive console confirmation: backup created in
  SADify Projects/_SADify/wiki-backups/<timestamp>/ after Case 14.
Confirmation that no refresh token or OAuth client secret appears in
  logs.
```
