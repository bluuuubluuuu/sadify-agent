# TC-026D Project Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a Project concept so a single connected `SADify Projects` Drive folder can hold multiple isolated projects. Each project lives in its own subfolder (`SADify Projects/<Project Name>/`) containing its own `SAD/`, `Wiki/`, `Sources/`, and `_SADify/` subdirectories. SAD saves and wiki updates resolve through the user's currently active project. ID counters (SV-, SA-, SM-) reset per project; SP- preview IDs stay globally unique because `/sad/preview` and `SadPreviewRepository` remain byte-identical. The user creates projects via a name prompt on first save (or via an explicit "New project" button) and switches projects via a dropdown that lists existing app-created subfolders discovered from Drive.

**Architecture:** Add a `ProjectRepository` (in-memory, keyed by `(repo_grant_id, project_id)`) that holds project metadata and per-project ID counters. `DriveRepoRecord` gains `active_project_id`, `active_project_name`, and `available_projects` fields. New project endpoints (`POST /projects`, `POST /projects/switch`, `GET /projects`) cover create/switch/list. `DriveClient` gains `list_subfolders(parent_folder_id)` so connect can enumerate existing projects from Drive. All Drive write paths (`/sad/save`, `/sad/wiki/preview`, `/sad/wiki/update`) resolve the project subfolder via `find_or_create_folder(<project_name>, parent_folder_id=repo.repo_folder_id)` and use it as the parent for `SAD/`, `Wiki/`, etc. `SadSaveRepository` and `WikiStateRepository` re-key per `(grant_id, project_id, ...)` so cross-project state never collides.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, pytest, Next.js/React, TypeScript. No new backend dependencies. No new npm dependencies.

---

Date: 2026-05-28

Status: Draft - awaiting approval

## Traceability Sources

- `CLAUDE.md`
- `context.md`
- `docs/superpowers/CURRENT.md`
- `docs/superpowers/plans/2026-05-25-tc026b-live-drive-docs.md`
- `docs/superpowers/plans/2026-05-26-tc025-wiki-update-approval.md`
- `docs/superpowers/plans/2026-05-27-tc025b-encyclopedia-wiki.md`
- `docs/superpowers/testing/test_cases/TC-026B-mvp-live-drive-docs.md`
- `docs/superpowers/testing/test_cases/TC-025A-mvp-wiki-snapshot.md`
- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `docs/superpowers/development/04_google_cloud_setup_runbook.md`
- `docs/superpowers/development/05_development_workflow.md`
- `docs/superpowers/development/07_decision_log.md`

## Pre-Plan Decisions (locked)

| Decision | Choice |
|---|---|
| Project name UX | User types it with auto-suggested default (from `latest_preview.title` or first ~60 chars of cleaned requirement). Modal on first save in a new session. |
| Project switching | Dropdown lists existing projects + an explicit "New project" button. |
| Migration policy | Ignore pre-migration flat data at repo root. New saves write into per-project subfolders. User cleans up legacy data manually if desired. |
| Project model | Active project implicit in `DriveRepoRecord` (`active_project_id`, `active_project_name`). Save/wiki endpoints read the active project from the record; no `project_id` in their request bodies. |
| ID counters | Per-project for `SV-`, `SA-`, and `SM-` only. `SP-` preview IDs remain global and `/sad/preview` stays byte-identical. Cross-project save/artifact/manifest IDs never collide by lookup scope. |
| Project discovery | Drive `list_subfolders` call on live connect/refresh; refreshable on demand via `GET /projects`. Under `drive.file`, only app-created/opened/shared folders are discoverable; manually-created Drive folders without Picker/share grant are a future TC-026E concern. |

## Cloud Prerequisites

None new. Reuses existing live OAuth + Secret Manager + Drive API enablement from TC-026B.

## Scope Lock

In scope:

- New `ProjectRepository` in-memory store and `ProjectRecord` model.
- New `DriveClient.list_subfolders(access_token, parent_folder_id)` helper.
- New endpoints: `GET /projects`, `POST /projects` (create), `POST /projects/switch` (set active).
- `DriveRepoRecord` extended with `active_project_id`, `active_project_name`, `available_projects: list[ProjectSummary]`. Connect populates `available_projects` from Drive and leaves `active_project_id=None` initially.
- `POST /sad/save`, `POST /sad/wiki/preview`, `POST /sad/wiki/update` all resolve via the active project subfolder. Return 409 with new stable code `PROJECT_REQUIRED` / `WIKI_PROJECT_REQUIRED` if `active_project_id` is None.
- Per-project `SV-`, `SA-`, and `SM-` ID counters in `SadSaveRepository`. Existing repository keyed by `(grant_id, project_id)`. `SP-` stays global and unchanged.
- `WikiStateRepository` keyed by `(grant_id, project_id, file_name)`.
- Frontend `ProjectPanel` with project dropdown, "New project" button, refresh button.
- `CreateProjectDialog` for naming (with auto-suggested default).
- Five new manual smoke cases (Cases 15-19).
- Stable error codes for project paths.

Out of scope:

- Project rename / delete from inside SADify (do it in Drive).
- Backfill migration of legacy flat data into a "Legacy/" subfolder.
- Multi-user collaboration on the same project.
- Project-level permissions (every project is owned by the connecting user).
- Schema changes to `SadSaveRecord`, `SadSaveManifest`, `SadSaveArtifact`, or wiki models (they continue to reference grant + file; project context comes from the active project resolution at write time).
- TC-027 Cloud Run deployment.

## Endpoint Contract Deltas

### `POST /drive/repo/connect` — extended

After existing live-mode logic that creates/locates `SADify Projects/`, also call `drive_client.list_subfolders(parent_folder_id=repo.repo_folder_id)` and populate the returned record's `available_projects`. `active_project_id` stays `None` for a fresh connect; the frontend will either:

- show the dropdown if `available_projects` is non-empty (user picks one then it triggers `POST /projects/switch`), OR
- show "Create your first project" CTA if empty (triggers `POST /projects` flow).

Response 200 body gains:

```json
{
  ...existing fields...,
  "active_project_id": null,
  "active_project_name": null,
  "available_projects": [
    { "project_id": "PR-...", "name": "Pet Grooming Appointments", "drive_folder_id": "1abc...", "created_at": "..." }
  ]
}
```

For local-mode connect: `available_projects` is empty; project create/switch paths still work and use fake folder IDs. Local project creation/switching is required so local-mode tests and manual development can exercise per-project save/wiki paths without live Drive.

### `GET /projects` (new)

Authenticated. Works in both local and live mode. In live mode, when both `SADIFY_DRIVE_MODE=live` and `SADIFY_DRIVE_LIVE_ENABLED=1` are set, it returns the up-to-date list from Drive:

```json
{
  "active_project_id": "PR-000001",
  "active_project_name": "Pet Grooming Appointments",
  "projects": [
    { "project_id": "PR-000001", "name": "Pet Grooming Appointments", "drive_folder_id": "1abc...", "created_at": "..." },
    { "project_id": "PR-000002", "name": "Laundry Workflow", "drive_folder_id": "1def...", "created_at": "..." }
  ]
}
```

Backend re-runs `list_subfolders` and reconciles app-visible Drive-side changes into local `ProjectRepository` so newly-found app-created/opened/shared projects get assigned PR- IDs. In local mode, it returns the in-memory projects for the connected grant and never calls Drive.

### `POST /projects` (new) — create a new project

Authenticated. Works in both local and live mode. Live gate only protects the actual Drive `find_or_create_folder` call. Local mode creates an in-memory project with a fake folder ID.

Request:

```json
{ "name": "Laundry Workflow" }
```

Behavior:

1. Validate name: 1-80 chars, `^[A-Za-z0-9 _\-]+$`, trimmed. Reject with 400 `PROJECT_NAME_INVALID` otherwise.
2. Check for collision: if a project with the same normalized name already exists in `ProjectRepository` for this grant, return the existing one (idempotent). No 409.
3. In live mode, call `find_or_create_folder(name, parent_folder_id=repo.repo_folder_id)` to create the Drive subfolder. In local mode, allocate a fake local project folder ID.
4. Assign `project_id = f"PR-{counter:06d}"`.
5. Store in `ProjectRepository`.
6. Set as the active project on the `DriveRepoRecord`.
7. Return the project record.

Response:

```json
{
  "project": { "project_id": "PR-000001", "name": "Pet Grooming Appointments", "drive_folder_id": "...", "created_at": "..." },
  "active_project_id": "PR-000001"
}
```

Stable errors:

| Case | HTTP | Code | Message |
| --- | --- | --- | --- |
| Unsigned | 401 | `PROJECT_AUTH_REQUIRED` | Sign in before creating a project. |
| No active repo / disconnected | 409 | `PROJECT_REPO_REQUIRED` / `PROJECT_REPO_DISCONNECTED` | Reconnect Google Drive. |
| Invalid name | 400 | `PROJECT_NAME_INVALID` | Project name must be 1-80 chars, letters/numbers/spaces/underscores/hyphens. |
| Drive folder create fails | 502 | `PROJECT_FOLDER_CREATE_FAILED` | Could not create the project folder in Drive. |

### `POST /projects/switch` (new) — change active project

Request:

```json
{ "project_id": "PR-000002" }
```

Behavior: look up the project, set as active on the `DriveRepoRecord`. Returns the new active state. Stable error `PROJECT_NOT_FOUND` (404) if unknown.

### `POST /sad/save` — modified

Behavior change: before composing the artifact paths, look up `active_project_id` on the user's `DriveRepoRecord`. If `None`, return 409 `PROJECT_REQUIRED`. Otherwise, resolve the project folder via `find_or_create_folder(project.name, parent_folder_id=repo.repo_folder_id)`, then resolve `SAD/` under it. ID counter scope is `(grant_id, project_id)`.

New stable error:

```text
PROJECT_REQUIRED   409   "Create or select a project before saving."
```

All other save behavior unchanged.

### `POST /sad/wiki/preview` and `POST /sad/wiki/update` — modified

Same change: require an active project; resolve `Wiki/` and `_SADify/` under the project subfolder. `WikiStateRepository` key includes `project_id`. `WIKI_PROJECT_REQUIRED` (409) is added. Save lookup for wiki context must be scoped to `(repo_grant_id, active_project_id)` so switching projects cannot show or update the wrong project's wiki.

`backup.path` in wiki update responses remains project-relative:

```text
_SADify/wiki-backups/<timestamp>/
```

The actual Drive path is:

```text
<Project Name>/_SADify/wiki-backups/<timestamp>/
```

The UI displays the short relative form.

## Schema Contract

New models in `schemas.py` (append-only):

- `ProjectSummary` — `{ project_id, name, drive_folder_id, created_at }`.
- `ProjectRecord` — same fields as ProjectSummary (use the same model if convenient).
- `CreateProjectRequest` — `{ name: str }`.
- `CreateProjectResponse` — `{ project: ProjectRecord, active_project_id: str }`.
- `SwitchProjectRequest` — `{ project_id: str }`.
- `SwitchProjectResponse` — `{ active_project_id: str, active_project_name: str }`.
- `ProjectListResponse` — `{ active_project_id: str | None, active_project_name: str | None, projects: list[ProjectSummary] }`.

`DriveRepoRecord` adds three optional fields:

```python
active_project_id: str | None = None
active_project_name: str | None = None
available_projects: list[ProjectSummary] = Field(default_factory=list)
```

Strictly additive. No existing fields renamed or removed.

## Configuration

No new env vars. The existing five live-mode env vars cover everything.

## Files To Change

Backend (worktree
`D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`):

- Create: `services/api/src/sadify_api/services/projects.py`
- Create: `services/api/src/sadify_api/routes/projects.py`
- Modify: `services/api/src/sadify_api/services/drive_client.py` (add `list_subfolders`)
- Modify: `services/api/src/sadify_api/services/drive_repo.py` (active project state, populate `available_projects` on connect)
- Modify: `services/api/src/sadify_api/services/sad_save.py` (per-project SV-/SA-/SM- counters; `save_preview` takes `project_id`)
- Modify: `services/api/src/sadify_api/services/wiki_state.py` (key by `(grant_id, project_id, file_name)`)
- Modify: `services/api/src/sadify_api/routes/sad.py` (resolve active project subfolder for save + wiki paths; add `PROJECT_REQUIRED` / `WIKI_PROJECT_REQUIRED` rejections)
- Modify: `services/api/src/sadify_api/routes/drive.py` (return enriched `DriveRepoRecord` from connect)
- Modify: `services/api/src/sadify_api/main.py` (wire `ProjectRepository` and the projects router)
- Modify: `services/api/src/sadify_api/schemas.py` (append the new models; extend `DriveRepoRecord`)
- Test new: `tests/api/test_projects.py`
- Test new: `tests/api/test_drive_client_list_subfolders.py`
- Test rewrite: `tests/api/test_drive_repo.py` (active project state)
- Test rewrite: `tests/api/test_sad_save.py` (per-project counters, `PROJECT_REQUIRED`)
- Test rewrite: `tests/api/test_sad_save_live_mode.py` (project subfolder resolution)
- Test rewrite: `tests/api/test_wiki_state.py` (per-project keys)
- Test rewrite: `tests/api/test_wiki_routes.py` (project subfolder, `WIKI_PROJECT_REQUIRED`)

Frontend:

- Create: `apps/web/src/components/ProjectPanel.tsx`
- Create: `apps/web/src/components/CreateProjectDialog.tsx`
- Modify: `apps/web/src/lib/api.ts` (project types + helpers `listProjects`, `createProject`, `switchProject`; also append `"secret_manager"` to the existing `DriveRepoRecord.token_store` union)
- Modify: `apps/web/src/components/WorkspaceShell.tsx` (mount `ProjectPanel`)
- Modify: `apps/web/src/components/SadPreviewPanel.tsx` (catch `PROJECT_REQUIRED` from save/wiki; open `CreateProjectDialog` with suggested default)
- Modify: `apps/web/src/components/DriveRepoPanel.tsx` (no change in shape; `DriveRepoRecord` now carries new fields — wire to ProjectPanel state)
- Test new: `tests/test_mvp_project_ui.py`

Docs (after Task 11 passes):

- Create: `docs/superpowers/testing/test_cases/TC-026D-mvp-project-isolation.md`
- Modify: `docs/superpowers/CURRENT.md`
- Modify: `docs/superpowers/testing/test_case_index.md`
- Modify: `docs/superpowers/development/07_decision_log.md`

## Task 0: Approval Gate

- [ ] **Step 0.1: Wait for user approval.** Do not modify code until the user explicitly approves this plan.
- [ ] **Step 0.2: Confirm worktree.** Latest commit is `23107b3 feat(wiki): encyclopedia knowledge graph with per-file conflict and backup`. Working tree clean.

## Task 1: Drive Client — `list_subfolders`

**Files:** Modify `services/drive_client.py`, test new `tests/api/test_drive_client_list_subfolders.py`.

- [ ] **Step 1.1: Write tests first.** Patch `googleapiclient.discovery.build`. Cover:

```text
test_list_subfolders_returns_empty_when_parent_has_no_subfolders
test_list_subfolders_returns_folder_refs_with_id_name_created_time
test_list_subfolders_ignores_files_only_returns_folders
test_list_subfolders_excludes_trashed_folders
test_list_subfolders_propagates_drive_error_as_drive_folder_create_error
```

- [ ] **Step 1.2: Implement.**

```python
def list_subfolders(
    self,
    *,
    access_token: str,
    parent_folder_id: str,
) -> list[DriveFolderRef]
```

Drive query:

```text
mimeType = 'application/vnd.google-apps.folder'
'<parent_folder_id>' in parents
trashed = false
```

Return list of `DriveFolderRef(folder_id, name, created_time, web_view_link)`. Sorted by `created_time` ascending.

- [ ] **Step 1.3: Run tests.** Expect 5 pass.

## Task 2: ProjectRepository + ProjectRecord

**Files:** Create `services/projects.py`, test `tests/api/test_projects.py`.

- [ ] **Step 2.1: Write tests first.**

Cover:

```text
test_create_project_assigns_pr_id_starting_at_one
test_create_project_increments_id_per_grant
test_create_project_is_idempotent_for_same_normalized_name
test_get_project_by_id_returns_record
test_get_project_by_id_returns_none_when_unknown
test_list_projects_for_grant_returns_in_creation_order
test_per_project_counter_starts_at_one
test_per_project_counter_increments_independently_per_project
test_sync_from_drive_creates_records_for_unknown_drive_folders
```

- [ ] **Step 2.2: Implement.**

```python
class ProjectRepository:
    def create_project(self, *, grant_id: str, name: str, drive_folder_id: str, created_at: datetime | None = None) -> ProjectRecord
    def get_project(self, grant_id: str, project_id: str) -> ProjectRecord | None
    def get_project_by_name(self, grant_id: str, name: str) -> ProjectRecord | None
    def list_projects(self, grant_id: str) -> list[ProjectRecord]
    def sync_from_drive(self, *, grant_id: str, drive_folders: list[DriveFolderRef]) -> list[ProjectRecord]
    def next_counter(self, grant_id: str, project_id: str, counter_name: str) -> int
```

Project ID assigned via per-grant counter, format `PR-000001`. `sync_from_drive` reconciles: for each Drive folder, if a record already exists with the same `drive_folder_id` it's a no-op; otherwise a new record is created with a fresh PR-ID and the project's `created_at` borrowed from Drive's `created_time`. Name normalization for collision is lowercase trim.

`next_counter` lets `SadSaveRepository` ask the project for the next SV-, SA-, SM- value scoped to that project.

- [ ] **Step 2.3: Run tests.** Expect 9 pass.

## Task 3: Schemas

**Files:** Modify `services/api/src/sadify_api/schemas.py`.

- [ ] **Step 3.1: Add new project models.**

```python
class ProjectSummary(ApiModel):
    project_id: str
    name: str
    drive_folder_id: str
    created_at: datetime

class CreateProjectRequest(ApiModel):
    name: str = Field(min_length=1, max_length=80)

class CreateProjectResponse(ApiModel):
    project: ProjectSummary
    active_project_id: str

class SwitchProjectRequest(ApiModel):
    project_id: str = Field(min_length=1)

class SwitchProjectResponse(ApiModel):
    active_project_id: str
    active_project_name: str

class ProjectListResponse(ApiModel):
    active_project_id: str | None = None
    active_project_name: str | None = None
    projects: list[ProjectSummary] = Field(default_factory=list)
```

- [ ] **Step 3.2: Extend `DriveRepoRecord` additively.**

```python
active_project_id: str | None = None
active_project_name: str | None = None
available_projects: list[ProjectSummary] = Field(default_factory=list)
```

All three default to safe empty values so old tests keep passing.

## Task 4: Projects Router

**Files:** Create `services/api/src/sadify_api/routes/projects.py`, test extension in `tests/api/test_projects.py` or a sibling route test file.

- [ ] **Step 4.1: Write route tests first.**

Cover at least:

```text
test_list_projects_returns_empty_for_first_time_connect
test_list_projects_returns_drive_synced_subfolders
test_create_project_creates_drive_folder_and_returns_pr_id
test_create_project_collision_returns_existing_idempotent
test_create_project_invalid_name_returns_400
test_create_project_sets_record_as_active
test_switch_project_updates_active_state
test_switch_project_unknown_returns_404
test_all_endpoints_block_unsigned
test_all_endpoints_block_when_no_active_repo
test_local_mode_create_project_uses_fake_folder_id
test_local_mode_switch_project_updates_active_state
```

- [ ] **Step 4.2: Implement.**

Three endpoints. Reuse the live-mode-resolver pattern from `routes/sad.py` only around actual Drive operations. Create/switch/list work in local mode without live services; local create uses fake folder IDs. Mutate `DriveRepoRecord.active_project_id` and `active_project_name` directly on the repo record stored in `DriveRepoRepository` so subsequent save/wiki calls see the updated state.

- [ ] **Step 4.3: Run tests.** Expect ≥11 pass.

## Task 5: DriveRepo Route — Enrich Connect Response

**Files:** Modify `services/api/src/sadify_api/routes/drive.py` and `services/api/src/sadify_api/services/drive_repo.py`. Tests in `tests/api/test_drive_repo.py`.

- [ ] **Step 5.1: Write/update tests.**

Cover:

```text
test_live_connect_returns_available_projects_synced_from_drive
test_live_connect_returns_empty_projects_when_drive_has_no_subfolders
test_local_connect_returns_empty_projects
test_connect_does_not_auto_activate_any_project
test_live_connect_project_listing_blocks_when_live_gate_disabled
```

- [ ] **Step 5.2: Implement.** After live connect creates the parent folder, call `drive_client.list_subfolders(parent_folder_id=record.repo_folder_id)`, then `project_repository.sync_from_drive(...)`, then populate `record.available_projects`. Leave `active_project_id=None`.

## Task 6: SadSaveRepository — Per-Project Counters

**Files:** Modify `services/sad_save.py`. Rewrite `tests/api/test_sad_save.py` (and `test_sad_save_live_mode.py` if applicable).

- [ ] **Step 6.1: Write/update tests.**

Add coverage:

```text
test_save_counter_starts_at_one_per_project
test_save_counter_increments_only_within_project
test_save_id_collision_impossible_across_projects
test_existing_idempotency_key_includes_project_id_implicitly
```

- [ ] **Step 6.2: Implement.** Add `project_id: str` parameter to `save_preview(...)`. The `save_id` format stays `SV-000001` but the counter is scoped to `(grant_id, project_id)`. Artifact (`SA-`) and manifest (`SM-`) counters are also scoped to `(grant_id, project_id)`. `SP-` remains global and unchanged. `_records` dict must include project scope (for example `(grant_id, project_id, save_id)`) so `SV-000001` from project A can never look up project B's `SV-000001`.

Idempotency key extends:

```text
(owner_uid, repo_grant_id, project_id, preview_id, preview_revision)
```

`preview_id` stays globally unique and is not a project counter.

- [ ] **Step 6.3: Run tests.** Expect all save tests green.

## Task 7: WikiStateRepository — Per-Project Keys

**Files:** Modify `services/wiki_state.py`. Rewrite `tests/api/test_wiki_state.py`.

- [ ] **Step 7.1: Write/update tests.**

```text
test_get_file_state_returns_none_when_unset_for_project
test_record_file_write_isolated_per_project
test_clear_states_for_project_does_not_affect_other_projects
```

- [ ] **Step 7.2: Implement.** Add `project_id` to all methods. Internal key becomes `(grant_id, project_id, file_name)`. Replace any `get_state(grant_id)` / `record_write(grant_id, state)` usages in the wiki routes.

## Task 8: Sad + Wiki Routes — Resolve Project Subfolder

**Files:** Modify `services/api/src/sadify_api/routes/sad.py`. Update affected tests.

- [ ] **Step 8.1: Write/update tests.**

```text
test_sad_save_blocks_when_no_active_project
test_sad_save_writes_into_project_subfolder
test_wiki_preview_blocks_when_no_active_project
test_wiki_preview_resolves_project_subfolder
test_wiki_update_writes_into_project_subfolder
test_wiki_backup_path_includes_project_subfolder
test_wiki_preview_uses_latest_save_for_active_project_only
```

- [ ] **Step 8.2: Implement.**

Helper `_resolve_project_folder(context)`:

1. Read `context.repo.active_project_id`. If `None`, raise the appropriate `PROJECT_REQUIRED` / `WIKI_PROJECT_REQUIRED` error.
2. Look up the project via `ProjectRepository.get_project(grant_id, active_project_id)`.
3. `find_or_create_folder(project.name, parent_folder_id=context.repo.repo_folder_id)` — should be idempotent given the project record already has the Drive folder ID.
4. Return the project folder.

Use the returned folder ID as the new "project root" for all subsequent `find_or_create_folder("SAD"/"Wiki"/"_SADify", parent_folder_id=project_folder.folder_id)` calls in save + wiki + backup paths. The backup response path remains project-relative (`_SADify/wiki-backups/<timestamp>/`), while the actual Drive path is `<Project>/_SADify/wiki-backups/<timestamp>/`.

Stable errors:

```text
PROJECT_REQUIRED         409   on /sad/save
WIKI_PROJECT_REQUIRED    409   on /sad/wiki/preview and /sad/wiki/update
```

- [ ] **Step 8.3: Run all backend tests.** Expect green.

## Task 9: Frontend — ProjectPanel + CreateProjectDialog

**Files:** Create `apps/web/src/components/ProjectPanel.tsx`, `apps/web/src/components/CreateProjectDialog.tsx`. Modify `apps/web/src/lib/api.ts`, `apps/web/src/components/WorkspaceShell.tsx`, `apps/web/src/components/SadPreviewPanel.tsx`. Test new `tests/test_mvp_project_ui.py`.

- [ ] **Step 9.1: Add TypeScript types and helpers.**

```typescript
type ProjectSummary = { project_id: string; name: string; drive_folder_id: string; created_at: string };
type ProjectListResponse = { active_project_id: string | null; active_project_name: string | null; projects: ProjectSummary[] };
export async function listProjects(idToken: string): Promise<ProjectListResponse>;
export async function createProject(idToken: string, name: string): Promise<CreateProjectResponse>;
export async function switchProject(idToken: string, projectId: string): Promise<SwitchProjectResponse>;
```

- [ ] **Step 9.2: ProjectPanel.**

Rendered between AuthPanel and DriveRepoPanel. Shows:
- Active project label (or "No project selected").
- Dropdown of available projects sourced from `DriveRepoRecord.available_projects`.
- "Switch" button (calls `switchProject` for the dropdown selection).
- "New project" button (opens `CreateProjectDialog`).
- "Refresh" button (calls `listProjects` and updates state).

Disabled when no active Drive repo.

- [ ] **Step 9.3: CreateProjectDialog.**

Plain modal with a text input pre-filled with a suggested name. Suggested name preference:

```text
1. previewResponse?.preview.title  (when SAD preview exists)
2. requirementText first 60 chars cleaned (when requirement exists)
3. "Untitled Project"
```

Submit calls `createProject(idToken, name)`, sets active, dispatches an `onProjectCreated` callback.

- [ ] **Step 9.4: SadPreviewPanel hook.**

When `saveSadPreview()` or `previewWikiUpdate()` / `commitWikiUpdate()` returns `409 PROJECT_REQUIRED` (or `WIKI_PROJECT_REQUIRED`), the panel opens `CreateProjectDialog` instead of just showing an error. After project creation, the panel retries the original action.

- [ ] **Step 9.5: TypeScript gate.** Expect clean.

## Task 10: Verification and Manual Smoke

- [ ] **Step 10.1: Full Python regression with `SADIFY_DRIVE_MODE=local`.** Expect ~387 baseline tests + the new task tests, all green.

- [ ] **Step 10.2: TypeScript gate.** Clean.

- [ ] **Step 10.3: Live manual browser smoke — Cases 15-19.** Drip-fed.

```text
Case 15 (first project create + save):
   - Disconnect Drive, delete SADify Projects folder in Drive (clean
     slate), restart uvicorn, sign in, reconnect.
   - ProjectPanel shows empty "No projects yet".
   - Generate SAD, click Save -> 409 PROJECT_REQUIRED -> CreateProjectDialog
     opens with suggested name.
   - Confirm. Save retries automatically -> Drive shows SADify Projects/
     <Project Name>/SAD/SAD-SP-<global>-SV-000001.google_doc.

Case 16 (second project alongside first):
   - Same session. Click "New project". Type a different name. Submit.
   - Generate a new SAD with a different requirement. Save.
   - Drive shows two sibling project folders, each with its own SAD/.

Case 17 (project switch + wiki update):
   - Switch to project 1 via dropdown.
   - Click Update wiki. 8 files write into project 1's Wiki/.
   - Switch to project 2. Click Update wiki. 8 files write into project
     2's Wiki/. Project 1's wiki is untouched.

Case 18 (counter isolation):
   - In project 1, save preview again -> SV-000002 expected (counter
     increments within project 1).
   - In project 2, save preview again -> SV-000002 expected (counter
     in project 2 also increments from its own 1).

Case 19 (app-created project discovery):
   - Create a fresh project via the SADify UI.
   - Click Refresh in ProjectPanel.
   - Dropdown still shows the app-created project alongside the prior
     projects.
   - Switch to it. Click Save (with a fresh requirement) -> writes into
     <Project Name>/SAD/SAD-SP-<global>-SV-000001.google_doc.
   - NOTE: folders created manually in the Drive UI are not visible to the
     app under the current drive.file scope unless opened/shared with the
     app. Drive Picker or a broader scope is future TC-026E.
```

- [ ] **Step 10.4: Commit.** Single commit:

```text
feat(projects): per-project Drive isolation with active project switching
```

## Task 11: Documentation Closure

- [ ] **Step 11.1: Create `TC-026D-mvp-project-isolation.md`.**
- [ ] **Step 11.2: Update CURRENT.md.** Flip TC-026D status; next focus TC-027.
- [ ] **Step 11.3: Append decision log entry.**
- [ ] **Step 11.4: Update test_case_index.md.**

## Stop Rules

- Plan not yet approved.
- A live Drive write would happen while `SADIFY_DRIVE_MODE=local` or `SADIFY_DRIVE_LIVE_ENABLED` unset.
- An existing TC-026B / TC-025A / TC-025B test fails after rewrites. Do not delete tests to make builds pass.
- Schema changes touch any field outside `DriveRepoRecord` additions and the new project models.
- A new env var or dependency seems necessary.
- Project name validation regex differs from what's specified.
- Per-project counter logic accidentally lets IDs collide across projects (a `save_id="SV-000001"` from project A must not look up project B's record).
- `/sad/preview` or `SadPreviewRepository` changes are proposed; SP- IDs are explicitly out of scope.

Honor `CLAUDE.md` sections 1, 2, 4.1, 4.2, 4.3, 5.1, 6, 7.1, 7.2, 7.3.

## Verification Summary Required Before Completion

```text
New test counts (projects, drive_client_list_subfolders).
Updated test counts (drive_repo, sad_save, sad_save_live_mode, wiki_state, wiki_routes).
Full pytest count with SADIFY_DRIVE_MODE=local.
TypeScript --noEmit result.
Manual browser smoke results for Cases 15-19.
Drive console confirmation: two sibling project subfolders exist with
  their own SAD/ and Wiki/ trees; counters are isolated.
Drive console confirmation: an app-created project subfolder appears in
  the ProjectPanel dropdown after Refresh.
Confirmation that no refresh token, OAuth client secret, or wiki/sad
  content appears in logs.
```
