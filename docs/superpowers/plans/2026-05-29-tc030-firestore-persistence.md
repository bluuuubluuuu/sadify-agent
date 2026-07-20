# TC-030 Firestore Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make project, SAD-save, wiki-state, and Drive-grant data survive Cloud Run cold starts, multiple instances, and redeploys by persisting the backing repositories to Firestore Native Mode. The existing in-memory repositories remain the default (for offline pytest and local dev); a new env flag `SADIFY_PERSISTENCE=firestore` selects Firestore-backed implementations. Analysis/Q&A state stays in-memory (ephemeral working session). Read-through on demand keeps reads simple and consistent across instances.

**Architecture:** Each persisted repository becomes a small interface (Protocol/ABC) with two implementations: the current in-memory class (unchanged, default) and a new Firestore-backed class. `main.py` selects the implementation from `SADIFY_PERSISTENCE` (default `memory`). Firestore-backed repos query Firestore directly on each call (read-through), keyed by the same identifiers used today (e.g. `grant_id`, `project_id`, `save_id`, `file_name`). No in-memory cache, so every Cloud Run instance reads the same source of truth. Firestore client access is mocked in unit tests; one opt-in live smoke runs against real Firestore.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, pytest, Next.js/TypeScript. New backend dependency: `google-cloud-firestore`. No frontend changes. No new npm deps.

---

Date: 2026-05-29

Status: Completed 2026-05-30 - see testing/test_cases/TC-030-mvp-firestore-persistence.md

## Traceability Sources

- `CLAUDE.md` (Firestore Native Mode = canonical store)
- `context.md`
- `docs/superpowers/CURRENT.md`
- `docs/superpowers/development/04_google_cloud_setup_runbook.md`
- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `docs/superpowers/testing/test_cases/TC-026D-mvp-project-isolation.md`
- `docs/superpowers/testing/test_cases/TC-026E-mvp-project-history.md`
- `docs/superpowers/testing/test_cases/TC-029-analysis-session-reset.md`
- `docs/superpowers/development/07_decision_log.md`

## Pre-Plan Decisions (locked)

| Decision | Choice |
|---|---|
| Persist scope | ProjectRepository, SadSaveRepository, WikiStateRepository, DriveRepoRepository. RequirementAnalysisRepository stays in-memory. |
| Swap pattern | Repository interface + Firestore impl, env-selected via `SADIFY_PERSISTENCE=memory\|firestore` (default `memory`). |
| Read strategy | Read-through on demand (direct Firestore query per call; no in-memory cache). |
| Test approach | Mock the Firestore client in unit tests; one opt-in live smoke gated by an env flag. |

## Cloud Prerequisites (verify before Task 1; do not assume)

- Firestore **Native Mode** database exists on project `sadify`. (TC-020
  touched Firestore and `sadify-agent-sa` already holds Cloud Datastore
  User, so it may already be provisioned. VERIFY in console; if absent,
  create a Native-mode database in `asia-southeast1` and record it in the
  runbook before coding.)
- Runtime service accounts have **Cloud Datastore User** (read/write):
  - `sadify-agent-sa@sadify.iam.gserviceaccount.com` (Cloud Run runtime)
  - `firebase-adminsdk-fbsvc@sadify.iam.gserviceaccount.com` (local dev
    via GOOGLE_APPLICATION_CREDENTIALS)
- Record any new enablement / IAM in
  `04_google_cloud_setup_runbook.md` (per CLAUDE.md cloud rules).

## Scope Lock

In scope:

- New backend dependency `google-cloud-firestore`.
- `SADIFY_PERSISTENCE` config flag (default `memory`).
- Repository interfaces + Firestore implementations for: Project, SadSave,
  WikiState, DriveRepo.
- Firestore document schema for each (collection layout below).
- `main.py` selects memory vs Firestore impl from the flag.
- Unit tests with a mocked Firestore client for each Firestore repo.
- One opt-in live smoke (gated by `SADIFY_FIRESTORE_LIVE=1`) that writes
  + reads back a project/save/wiki/grant round-trip against real
  Firestore.
- Runbook documentation of the Firestore setup.

Out of scope:

- Persisting RequirementAnalysisRepository (analysis/Q&A stays in-memory).
- Migrating existing in-memory data (there is none durable to migrate;
  Drive files already persist and projects re-sync from Drive on connect).
- Any change to endpoint contracts, schemas (Pydantic API models), or
  frontend.
- Caching / batching / transactions beyond what a single document
  read/write needs.
- TC-027 Cloud Run deploy (separate slice; this unblocks it).

## Firestore Document Schema

Top-level collections, all documents keyed deterministically so any
instance resolves the same path. Suggested layout (Codex may adjust
naming to match existing field names, but keys must be deterministic):

```text
drive_repos/{grant_id}
  -> serialized DriveRepoRecord (incl. active_project_id,
     active_project_name, available_projects, token_store, status, ...)
  index field: owner_uid (for get_active_repo / get_latest_repo queries)

projects/{grant_id}__{project_id}
  -> serialized ProjectRecord (project_id, name, drive_folder_id,
     created_at)
  index fields: grant_id, created_at
  counters: store per-(grant_id, project_id) next-counter values either
    on the project doc or a sibling doc projects_counters/{grant_id}__{project_id}

sad_saves/{grant_id}__{project_id}__{save_id}
  -> serialized SadSaveRecord (full record incl. sad_doc, manifest,
     artifacts, source_artifact_references, idempotency_key, created_at)
  index fields: grant_id, project_id, created_at, idempotency_key

wiki_state/{grant_id}__{project_id}__{file_name}
  -> WikiState (file_name, file_id, hash, updated_at)
  index fields: grant_id, project_id
```

Serialization: use Pydantic `model_dump(mode="json")` to store and
`model_validate` to read back, so the stored shape tracks the existing
models exactly. datetimes serialize as ISO strings (Firestore also
supports native timestamps; either is fine as long as round-trip is
lossless and sort-by-created_at still works).

ID counters (SV-/SA-/SM-/PR-) currently live in the in-memory repos.
The Firestore impl must derive the next counter deterministically — either
by a Firestore transaction incrementing a counter doc, or by computing
`max(existing) + 1` from a query. Transaction-based counter is preferred
to avoid races across instances. Document the chosen approach.

## Configuration

`config.py` gains:

```python
persistence_mode: Literal["memory", "firestore"]  # from SADIFY_PERSISTENCE, default "memory"
```

`.env.example` (root + worktree) gains:

```text
SADIFY_PERSISTENCE=memory   # set to "firestore" in deployed environments
SADIFY_FIRESTORE_LIVE=      # leave empty; set to 1 only for the opt-in live smoke
```

Default `memory` keeps the entire 457-test suite and local dev offline
and unchanged.

## Files To Change

Backend (worktree `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`):

- Modify: `services/api/pyproject.toml` (add `google-cloud-firestore`)
- Modify: `requirements.txt` (mirror, if consumed by tests/CI)
- Modify: `services/api/src/sadify_api/config.py` (add `persistence_mode`)
- Create: `services/api/src/sadify_api/services/firestore_client.py`
  (thin factory `get_firestore_client(project_id)`; mockable)
- Modify: `services/api/src/sadify_api/services/projects.py`
  (extract a `ProjectRepository` Protocol/ABC if not already; keep the
  in-memory class; add `FirestoreProjectRepository`)
- Modify: `services/api/src/sadify_api/services/sad_save.py`
  (same pattern: interface + in-memory + `FirestoreSadSaveRepository`)
- Modify: `services/api/src/sadify_api/services/wiki_state.py`
  (interface + in-memory + `FirestoreWikiStateRepository`)
- Modify: `services/api/src/sadify_api/services/drive_repo.py`
  (interface + in-memory + `FirestoreDriveRepoRepository`)
- Modify: `services/api/src/sadify_api/main.py`
  (select impls from `config.persistence_mode`)
- Test: `tests/api/test_firestore_repositories.py` (mocked-client unit
  tests for all four Firestore repos)
- Test (opt-in live, gated): `tests/api/test_firestore_live_smoke.py`
- Modify docs (after Task pass):
  `docs/superpowers/development/04_google_cloud_setup_runbook.md`

No frontend changes.

## Task 0: Approval + Cloud Prerequisite Gate

- [ ] **Step 0.1: Wait for user approval.**
- [ ] **Step 0.2: Confirm worktree.** HEAD `670b5b9`, clean tree.
- [ ] **Step 0.3: Verify Firestore prerequisites in the GCP console** (or
  ask the user to): Native-mode database exists on `sadify`; both service
  accounts have Cloud Datastore User. If anything is missing, STOP and
  report what the user must enable before coding (do not enable cloud
  resources unannounced per CLAUDE.md).

## Task 1: Dependency + Config + Firestore Client Factory

- [ ] **Step 1.1:** Add `google-cloud-firestore` to pyproject + requirements.
  Verify import. List the dependency for approval (CLAUDE.md 7.1).
- [ ] **Step 1.2:** Add `persistence_mode` to `config.py` (default
  `"memory"`). Add env vars to both `.env.example` files.
- [ ] **Step 1.3:** Create `firestore_client.py` with
  `get_firestore_client(project_id)` returning a
  `google.cloud.firestore.Client`. Keep it a one-line wrapper so unit
  tests can monkeypatch it.

## Task 2: Repository Interfaces (no behaviour change)

- [ ] **Step 2.1: Tests first.** Confirm existing repository tests still
  pass after extracting interfaces (they exercise the in-memory classes,
  which stay the default). No new behaviour yet.
- [ ] **Step 2.2:** For each of Project / SadSave / WikiState / DriveRepo,
  define a Protocol (or ABC) capturing the public methods the routes
  already call. The existing in-memory class implements it unchanged.
  Do NOT alter in-memory behaviour or method signatures.
- [ ] **Step 2.3:** Run full suite — expect 457 still green.

## Task 3: Firestore Project Repository

- [ ] **Step 3.1: Tests first** (`test_firestore_repositories.py`),
  mocking the Firestore client. Cover:

```text
test_firestore_project_create_writes_document
test_firestore_project_get_reads_document
test_firestore_project_get_by_name_queries_grant
test_firestore_project_list_orders_by_created_at
test_firestore_project_sync_from_drive_upserts
test_firestore_project_next_counter_increments_atomically
```

- [ ] **Step 3.2:** Implement `FirestoreProjectRepository` matching the
  in-memory public API. Serialize via Pydantic. Counter via Firestore
  transaction on a counter doc.
- [ ] **Step 3.3:** Run tests.

## Task 4: Firestore SadSave Repository

- [ ] **Step 4.1: Tests first.** Cover:

```text
test_firestore_sad_save_persists_record
test_firestore_sad_save_idempotent_returns_existing
test_firestore_sad_save_list_for_project_desc
test_firestore_sad_save_counters_per_project
test_firestore_sad_save_get_by_id
```

- [ ] **Step 4.2:** Implement `FirestoreSadSaveRepository`. Idempotency:
  store `idempotency_key` as an indexed field; on save, query for an
  existing doc with that key first (mirrors current in-memory behaviour).
  Per-project SV-/SA-/SM- counters via transaction docs.
- [ ] **Step 4.3:** Run tests.

## Task 5: Firestore WikiState + DriveRepo Repositories

- [ ] **Step 5.1: Tests first.** Cover:

```text
test_firestore_wiki_state_record_and_get_per_file
test_firestore_wiki_state_isolated_per_project
test_firestore_drive_repo_connect_persists
test_firestore_drive_repo_get_active_and_latest
test_firestore_drive_repo_disconnect_marks_status
test_firestore_drive_repo_set_active_project_persists
```

- [ ] **Step 5.2:** Implement both Firestore repos matching their
  in-memory public APIs.
- [ ] **Step 5.3:** Run tests.

## Task 6: Wire Selection in main.py

- [ ] **Step 6.1:** In `main.py`, choose each repository implementation
  from `config.persistence_mode`. `memory` (default) -> existing
  in-memory classes (unchanged). `firestore` -> Firestore classes with a
  shared `get_firestore_client`.
- [ ] **Step 6.2:** Confirm `create_app(...)` still accepts injected
  repositories (so tests pass fakes) and only falls back to the
  flag-selected default when none injected.
- [ ] **Step 6.3:** Full suite green in default (memory) mode.

## Task 7: Verification + Live Smoke

- [ ] **Step 7.1:** Full Python regression, default memory mode:

```cmd
set "PYTHONPATH=services\api\src;src;."
set "SADIFY_DRIVE_MODE=local"
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest -q
```
Expect 457 + new Firestore unit tests, all green; zero existing tests
changed in behaviour.

- [ ] **Step 7.2:** TypeScript unaffected (no frontend change) — run
  `npx -y tsc --noEmit` to confirm still clean.

- [ ] **Step 7.3: Opt-in live Firestore smoke** (manual, gated):

```cmd
set "PYTHONPATH=services\api\src;src;."
set "GOOGLE_CLOUD_PROJECT=sadify"
set "GOOGLE_APPLICATION_CREDENTIALS=D:\GoogleCloudHack\.secrets\sadify-firebase-adminsdk-fbsvc-ac7a32c920.json"
set "SADIFY_FIRESTORE_LIVE=1"
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_firestore_live_smoke.py -q -s
```
Writes then reads back a project, a save, a wiki-state row, and a drive
grant against real Firestore; asserts round-trip equality; cleans up the
test docs.

- [ ] **Step 7.4: Live app restart-survival smoke (manual, by user).**
  Run uvicorn with `SADIFY_PERSISTENCE=firestore` + live Drive env.
  Create a project, save a SAD, update wiki. Restart uvicorn. Reconnect.
  Confirm the project + save history + wiki state reappear from Firestore
  (NOT empty). This is the real proof the deploy problem is solved.

- [ ] **Step 7.5: Commit.** Single commit:

```text
feat(persistence): firestore-backed repositories behind SADIFY_PERSISTENCE
```

## Task 8: Documentation Closure

- [ ] **Step 8.1:** Update `04_google_cloud_setup_runbook.md` with the
  Firestore database, mode, region, collections, and IAM.
- [ ] **Step 8.2:** Create `TC-030-mvp-firestore-persistence.md` evidence.
- [ ] **Step 8.3:** Update CURRENT.md (TC-030 passed; next TC-027).
- [ ] **Step 8.4:** Append decision-log entry.
- [ ] **Step 8.5:** Flip TC-030 row in test_case_index.

## Stop Rules

- Plan not approved.
- Firestore Native DB or Datastore User IAM is missing — STOP and report;
  do not enable cloud resources unannounced.
- Any existing test changes behaviour or fails in default memory mode.
- Schema (Pydantic API models) or endpoint contracts would change — they
  must not; persistence is behind the repository layer only.
- Frontend would need changes — it must not.
- A repository's public method signature would change (routes must keep
  calling the same methods).
- New dependency beyond `google-cloud-firestore`.
- Counter logic cannot guarantee no cross-instance ID collision — report
  before shipping (transaction-based counter is the intended fix).

Honor `CLAUDE.md` sections 1, 2, 4.1, 4.2, 4.3, 5.1, 6, 7.1, 7.2, 7.3.

## Verification Summary Required Before Completion

```text
New dependency confirmed (google-cloud-firestore only).
Firestore unit test counts (mocked client) per repository.
Full pytest count in default memory mode (457 + new, all green,
  zero existing behaviour changes).
TypeScript still clean.
Opt-in live Firestore round-trip smoke result.
Live restart-survival smoke: project + saves + wiki state persisted
  across a uvicorn restart in firestore mode.
Confirmation that analysis/Q&A state intentionally remains in-memory.
Confirmation that default memory mode behaviour is byte-identical.
```
