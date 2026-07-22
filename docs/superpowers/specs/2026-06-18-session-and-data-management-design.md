# Session & Data Management Design

Date: 2026-06-18
Status: Approved - ready for implementation planning

## Traceability Sources

- `CLAUDE.md` and `context.md` - local-first discipline, Google/Gemini default, doc-update rules, scope control.
- `docs/superpowers/development/03_data_model_and_output_schema.md` - Firestore collection conventions, traceability rules.
- `docs/superpowers/development/07_decision_log.md` - persistence and project-isolation decisions (TC-030 Firestore, TC-026d project isolation, TC-026e project history).
- `docs/superpowers/CURRENT.md` - post-submission MVP status; this is net-new post-MVP work, not a blocking checkpoint.
- Code read during brainstorming:
  - `services/api/src/sadify_api/services/analysis_state.py` (in-memory, non-persistent Q&A state)
  - `services/api/src/sadify_api/services/projects.py` (projects + name index; no delete today)
  - `services/api/src/sadify_api/services/sad_save.py` (saves keyed by grant_id/project_id/save_id; idempotency docs)
  - `services/api/src/sadify_api/services/source_uploads.py` (sources are ephemeral, in-memory only)
  - `services/api/src/sadify_api/services/drive_client.py` (no trash/delete method yet)
  - `services/api/src/sadify_api/routes/projects.py` (auth + live-drive context helpers)
  - `services/api/src/sadify_api/main.py` (factory DI, persistence-mode repo selection)
  - `apps/web/src/components/WorkspaceV2.tsx`, `apps/web/src/lib/hooks/useQnA.ts`, `apps/web/src/components/shell/{Sidebar,ProjectList,AccountMenu}.tsx`

## Goal

Add three independent post-submission capabilities to the MVP web app:

1. **Auto-resume per project** - reopening a project restores its in-progress Q&A and readiness, so a user can leave and come back without losing the conversation. (The unsaved SAD draft is re-generated on demand, not restored — see v1 scope below.)
2. **Delete project + Drive trash** - a user can delete a project, which removes its Firestore data (project, name index, saved-SAD history, session snapshot) and moves its Drive folder to Drive Trash (recoverable).
3. **Profile menu fix** - the account menu no longer shows a misleading "Signed in"/"Sign out" block to guests; guests get a single "Sign in with Google" action, and the signed-in menu is tidied.

## Non-Goals

- No change to Q&A carry-forward strings, questionnaire logic, readiness logic, or the SAD preview/finalize flow.
- No resume for guest (signed-out) sessions or pre-project sessions; persistence begins only once a signed-in user has an active project. This matches today's guest behavior.
- No multi-snapshot version history of in-progress sessions; one latest snapshot per project, overwritten.
- No restoration of original uploaded `File` objects after a backend restart; the snapshot carries the derived source context + references, not the binary files.
- No new deploy in this work without explicit user approval.
- No undo for delete beyond Drive Trash recovery.

## Decision Summary (from brainstorming)

- Resume model: **auto-resume per project**.
- Delete scope: **whole project + trash Drive folder** (recoverable, not permanent).
- Profile fix: **fix guest state + tidy menu**.
- Delete confirmation UX: **plain confirm dialog** (button, no typed-name), because Drive Trash makes it recoverable. Copy states what is removed and that the Drive folder is recoverable from Trash.

---

## Feature 1 - Auto-resume per project

### Storage

One latest snapshot per `(grant_id, project_id)`, overwritten on each write.

New repository unit `services/api/src/sadify_api/services/session_state.py` with two variants mirroring the existing repo pattern:

- `SessionSnapshotRepository` (in-memory, default for tests/local).
- `FirestoreSessionSnapshotRepository` (selected when `config.persistence_mode == "firestore"`).

Firestore collection: `project_sessions`, document id `safe_doc_id(grant_id, project_id)`.

### Snapshot payload

New Pydantic schema `ProjectSessionSnapshot` (in `schemas.py`), all fields JSON-serializable:

```text
clean_requirement_text : str
analysis_response      : RequirementAnalysisApiResponse | None  # FULL api-response shape {analysis_id, saved, analysis}; rehydrates Q&A + readiness without re-calling Gemini
answer_history         : list[str]                              # the verbatim carry-forward transport strings from useQnA
source_context         : str                                    # derived analysis context, so post-resume backend calls keep source grounding
source_references      : list[str]                              # source ids
selected_model         : str | None
status                 : Literal["in_progress"]                 # reserved for future states; preview restore is out of scope for v1
updated_at             : datetime | None = None                 # SERVER-OWNED: omitted by PUT clients, set by the repository on upsert
```

`updated_at` is server-owned: it is `datetime | None = None` so PUT request bodies omit it (otherwise the round-trip returns 422), and `upsert()` stamps it with `datetime.now(UTC)` when absent. `source_labels` is intentionally dropped from v1 — restored source chips are not displayed, so storing labels we never read/preserve would be dead data.

Critical: `analysis_response` must store the full **`RequirementAnalysisApiResponse`** (`{analysis_id, saved, analysis}`) that `useQnA.analysisResponse` holds — NOT the inner `RequirementAnalysisResponse`. The frontend's `continueWithAnswer` reads `analysisResponse.analysis`, so the wrapper fields are required for resume to continue the Q&A.

Rationale: `answer_history` + `analysis_response` make resume survive a cold backend restart, because the Q&A carry-forward context is in-band in `answer_history`; the backend `RequirementAnalysisRepository` slot evidence is best-effort only and not required for correctness.

**Out of scope for v1 (deliberate):** the unsaved SAD draft preview is NOT restored. `useSadSave` resets its preview in a `useEffect` keyed on `[analysisId, requirementText]`; hydrating Q&A changes both, which would wipe any restored preview on the next commit. Rather than seed/guard that effect, v1 restores Q&A + readiness only; regenerating a draft after resume is a single "Quick draft" click. This keeps `useSadSave` untouched.

### Endpoints (extend the existing projects router)

- `PUT /projects/{project_id}/session` (authed) - upsert the snapshot for the active repo's grant + project. Body is the snapshot payload (without `updated_at`, which the server sets). Returns 204.
- `GET /projects/{project_id}/session` (authed) - returns the snapshot or `204 No Content` when none exists.

Both reuse the existing `_verified_user` + `_active_repo_or_error` helpers and **both validate the project exists** for the grant (404 `PROJECT_NOT_FOUND` otherwise) — the GET must do the same lookup as the PUT, not skip it. Auth/repo error codes match the existing projects router.

### Write path (frontend)

`WorkspaceV2` writes the snapshot (debounced ~800ms) when signed in AND an active project exists, after `useQnA.startAnalysis` or `useQnA.continueWithAnswer` change `qna.analysisResponse`.

Implementation: a `useProjectSession` hook (or inline effect) that serializes current `qna` + effective source state + `selectedModel` into the payload and calls `putProjectSession(idToken, projectId, payload)`. Writes are fire-and-forget with console-logged failures (never block Q&A).

**Write guards (required, to prevent data loss AND cross-project corruption):**

The naive "skip-next-write ref" is not enough: after switching project A → B, A's still-mounted Q&A state can schedule a debounced write that fires under B before B's restore completes, and a slow restore for A can hydrate A after the user already moved to B. All of the following are required:

- **Single source of truth for "current project":** keep `activeProjectRef` (a ref) updated **synchronously** at the top of the project-change effect, before any async work. Every write and every restore-apply checks against `activeProjectRef.current`.
- **Restoring gate:** set `restoringRef = true` synchronously when a project change begins and clear it only after that project's restore resolves and is applied. The write effect returns early while `restoringRef.current` is true.
- **Cancel pending writes on every project change:** the debounce timer is cleared whenever `active_project_id` changes (not only "on switch"). The `useProjectSession` writer exposes a `cancel()` used by the project-change effect's cleanup.
- **Stamp writes with their project:** the debounced writer captures `projectId` at schedule time AND re-checks `projectId === activeProjectRef.current` at fire time; if they differ it drops the write.
- **Discard stale restores:** when a restore GET resolves, apply it only if its `projectId === activeProjectRef.current`; otherwise discard.
- **Write only when `qna.analysisResponse` is non-null** — the empty/reset state (after "New SAD" calls `qna.reset()`) must never be written, or it would overwrite a good snapshot with an empty one.

### Restore path (frontend)

When `active_project_id` becomes non-null (project switch or first load with an active project), synchronously update `activeProjectRef`/`restoringRef`, then `GET` the snapshot. If a snapshot is returned AND its project still matches `activeProjectRef.current`:

- `useQnA.hydrate({ requirementText, analysisResponse, answerHistory })` - new method that sets `requirementText`, `cleanRequirementText`, `analysisResponse`, `answerHistory`, and clears transient `selectedChoiceIds`/`amendmentText`. `analysisResponse` is the stored `RequirementAnalysisApiResponse`.
- `WorkspaceV2` stores `restoredSourceContext` / `restoredSourceReferences` from the snapshot. It passes an **effective** source context into `useQnA` and `useSadSave`: `sources.files.length ? sources.analysisContext : restoredSourceContext` (and likewise for references). `useSources` is NOT modified; original files are not restored, and attaching a new file replaces the restored context.
- Model restore is gated on catalog availability: apply `models.setSelectedModel(snapshot.selected_model)` only when `models.isLoaded` and the id is still in `models.catalog`; otherwise retain the pending id and apply it once `isLoaded` flips true. Never set a model before the async catalog loads.

Then clear `restoringRef`.

Interaction with the existing TC-029 effect: the effect that regenerates `analysisSessionId` on project switch already runs on the same `active_project_id` change; restore does not need to preserve `analysisSessionId` because continuity rides on `answer_history` + `clean_requirement_text`.

### Edge cases

- No snapshot: behave exactly as today (empty StartBox).
- Snapshot references a model no longer in the catalog: fall back to catalog default (same rule as the existing model picker).
- "New SAD" in an active project: clears the in-memory workspace but, per the write guards, does NOT erase the persisted snapshot until a new analysis starts (which overwrites it).
- Switching away from a project mid-Q&A: the last debounced write persists; switching back restores it.
- Guest or no active project: no read, no write.

---

## Feature 2 - Delete project + Drive trash

### Backend cascade

New authed endpoint `DELETE /projects/{project_id}` on the projects router. Order of operations:

1. Resolve user + active repo (`_verified_user`, `_active_repo_or_error`); 404 `PROJECT_NOT_FOUND` if the project does not exist for the grant.
2. If `config.drive_mode == "live"` AND `drive_folder_id` is a real Drive id (does not start with `LOCAL-`): resolve `(drive_client, access_token)` via the existing `_live_drive_context` helper and call the new `DriveClient.trash_folder(access_token, folder_id)`. On Drive failure raise 502 `PROJECT_DELETE_DRIVE_FAILED` (no Firestore data is deleted, so the project stays fully consistent and the user can retry).
3. Delete Firestore/app data as an **idempotent, retry-safe cascade with the project doc deleted LAST**, each step wrapped so a persistence failure surfaces as 502 `PROJECT_DELETE_FAILED`:
   1. `sad_save_repository.delete_for_project(grant_id, project_id)` - removes all saves + their idempotency docs.
   2. `session_snapshot_repository.delete(grant_id, project_id)`.
   3. `project_repository.delete_project(grant_id, project_id)` - removes the project doc and its name-index doc. **Last**, so that if step 1 or 2 fails mid-cascade the project is still discoverable and a retried `DELETE` re-runs cleanly (every delete tolerates already-missing data).
4. Clear the active-project pointer if it referenced the deleted project (`drive_repo_repository.clear_active_project(grant_id, project_id)`), then return the updated project list.

This is a documented idempotent cascade, not a single cross-collection transaction — that matches the existing per-repository pattern (no repo spans collections), and idempotency makes a partial-failure retry safe. Each delete method must no-op on missing data so retries never error.

Response: `ProjectListResponse` (reusing the existing schema) reflecting the post-delete state.

Sources are not persisted per project (ephemeral in-memory store), so there is nothing to delete there.

### New repository methods

- `DriveClient.trash_folder(access_token, folder_id)` - `files().update(fileId=folder_id, body={"trashed": True})`; raises a typed `DriveFolderTrashError` on failure.
- `ProjectRepository.delete_project` / `FirestoreProjectRepository.delete_project(grant_id, project_id) -> ProjectRecord | None` - returns the removed record (for the folder id) or None; Firestore variant deletes both the project doc and the name-index doc in a transaction.
- `SadSaveRepository.delete_for_project` / `FirestoreSadSaveRepository.delete_for_project(grant_id, project_id) -> int` - returns count removed; Firestore variant deletes matching `sad_saves` docs and their `sad_save_idempotency` docs.
- `SessionSnapshotRepository.delete` / Firestore variant `(grant_id, project_id) -> None`.
- `DriveRepoRepository.clear_active_project` / Firestore variant `(grant_id, project_id) -> None` - nulls the active pointer only when it matches.

### Frontend

- `deleteProject(idToken, projectId)` in `api.ts` -> `DELETE /projects/{id}`, returns the updated project list.
- `ProjectList` gains a trash icon-button per project (hover-revealed, `aria-label="Delete project {name}"`).
- A confirm dialog (reuse/extend `CreateProjectDialog` styling or a small `ConfirmDialog`) with copy: "Delete {name}? This removes its saved SADs and history, and moves its Drive folder to Trash (recoverable for 30 days)." Buttons: Cancel / Delete.
- On confirm: call `deleteProject(idToken, projectId)`, then refetch `getDriveRepoStatus(idToken)` and `setDriveRepo(...)` for the canonical `DriveRepoRecord` (do not hand-map the `ProjectListResponse` into the repo record — different shapes). If the deleted project was the active one, reset the workspace (`qna.reset()`, `sources.reset()`, `sadSave.dismissPreview()`).

---

## Feature 3 - Profile menu fix (`AccountMenu`)

### Guest (no `name` and no `email`)

- Do not render the "Signed in" header, the identity row, the Drive section, or "Sign out".
- Render a single primary menu item "Sign in with Google" wired to a new `onSignIn` prop.
- The collapsed row shows a neutral avatar (e.g. `?`) and the label "Guest" with a "Sign in" chip instead of the Drive/Connect chip.

### Signed-in

- One identity row only (remove the duplicate name shown in both the collapsed row header and the menu identity row).
- Keep Drive connect/disconnect and Sign out.

### Wiring

- `Sidebar` passes `onSignIn` down to `AccountMenu`; `WorkspaceV2`/`Sidebar` source it from `useAuth().signIn` (the same call `StartBox` already uses).
- No change to `useAuth`.

---

## Data Flow (Feature 1)

```text
User answers a question (useQnA.continueWithAnswer resolves)
  -> WorkspaceV2 debounced effect (signed in + active project)
  -> putProjectSession(idToken, projectId, snapshot)
  -> PUT /projects/{id}/session  -> SessionSnapshotRepository.upsert (memory or Firestore)

User selects a project later
  -> active_project_id changes
  -> TC-029 effect regenerates analysisSessionId
  -> getProjectSession(idToken, projectId)
  -> GET /projects/{id}/session -> snapshot
  -> useQnA.hydrate(analysisResponse, answerHistory) + WorkspaceV2 restoredSourceContext
  -> conversation + readiness reappear; user continues answering (SAD draft is re-generated on demand)
```

## Error Handling

- Snapshot write failures are non-blocking and logged to console; Q&A never breaks because a save failed.
- Snapshot read failure (network/500) falls back to the empty StartBox; no crash.
- `GET /session` with no snapshot returns 204 and the frontend treats it as "fresh project".
- Delete: Drive trash failure returns 502 `PROJECT_DELETE_DRIVE_FAILED` and leaves Firestore intact (consistent, retryable). A Firestore deletion failure at any cascade step surfaces as 502 `PROJECT_DELETE_FAILED`; because the project doc is deleted last and every delete is idempotent, the client can safely retry the same `DELETE`.
- All new endpoints keep the existing projects-router auth/repo error codes (`PROJECT_AUTH_REQUIRED`, `PROJECT_REPO_REQUIRED`, `PROJECT_REPO_DISCONNECTED`, `PROJECT_NOT_FOUND`).

## Testing

Backend (pytest). **Both the in-memory AND the Firestore variant must be tested** for every new repo method, using the existing fake Firestore client (`tests/api/test_firestore_repositories.py`):

- Session repo (in-memory + Firestore): upsert overwrites prior snapshot; upsert stamps `updated_at` when omitted; get returns latest; get-missing returns None; delete removes it; delete-missing is a no-op.
- `PUT/GET /projects/{id}/session`: round-trips a snapshot (PUT body omits `updated_at`, response carries it); **both** PUT and GET return 404 for an unknown project; 401 without auth; GET returns 204 when absent.
- `DriveClient.trash_folder` issues a `files().update(fileId=..., body={"trashed": True})` (mocked Drive service); raises `DriveFolderTrashError` on API failure.
- `delete_project` (in-memory + Firestore) removes project + name-index and no-ops on missing; `delete_for_project` (both) removes saves + idempotency and no-ops on missing; session delete removes snapshot.
- `DELETE /projects/{id}`: cascades all stores; trashes a real Drive folder in live mode; skips Drive for `LOCAL-` folders; returns updated list; clears active pointer when the deleted project was active; Drive failure leaves Firestore intact (502 `PROJECT_DELETE_DRIVE_FAILED`); a forced failure at the saves step and at the session step both return 502 `PROJECT_DELETE_FAILED` and leave the project doc intact (project deleted last), and a retry then succeeds.

Frontend:

- Static-source pytest checks (matching repo convention): `api.ts` exposes `putProjectSession`/`getProjectSession`/`deleteProject`; `useQnA` exposes `hydrate`/`answerHistory`/`cleanRequirementText`; `WorkspaceV2` wires guarded write + restore; `ProjectList` renders a delete control; `ConfirmDialog` copy mentions Drive Trash; `AccountMenu` renders "Sign in with Google" for guests and a single identity row when signed in.
- **Behavioral race tests** for the debounced-write cancellation, stale-restore rejection, and "New SAD" no-write paths cannot be proven by static-string checks. This needs a JS test runner (the repo has none today). See the open decision in the plan: either (a) extract the write-guard decision into a pure, framework-free TS helper and add a minimal Vitest test for just that, or (b) rely on careful implementation + manual smoke. Resolve before Task 3.

Verification commands (from the worktree root `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`):

- Backend: `..\..\.venv\Scripts\python.exe -m pytest tests/ -q`
- Frontend static: included in the same suite.
- Typecheck/build: `cd apps/web; npx tsc --noEmit; npm run build`

## Documentation

This work uses:

- Spec: `docs/superpowers/specs/2026-06-18-session-and-data-management-design.md`
- Plan: `docs/superpowers/plans/2026-06-18-session-and-data-management.md`
- New test case: `docs/superpowers/testing/test_cases/TC-035-session-and-data-management.md` (to be created during execution).
- Decision log: add a decision for project deletion semantics (Drive Trash, recoverable) and per-project session snapshots.

Docs in `docs/` are local/gitignored; do not commit them unless the user asks.
