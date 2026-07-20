# Session & Data Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-project session auto-resume, project deletion with Drive Trash, and a corrected profile menu to the SADify MVP web app.

**Architecture:** Mirror the existing backend repository pattern (in-memory default + Firestore variant selected by `config.persistence_mode`) for a new per-project session-snapshot store, extend the projects router with session and delete endpoints, add a Drive trash call, and restore Q&A state via a new `useQnA.hydrate` plus `WorkspaceV2`-level restored source context. `useSources`/`useSadSave` are NOT modified; the SAD draft is not restored in v1. No change to Q&A carry-forward, readiness, or finalize logic.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, Firestore, Google Drive API (`googleapiclient`), pytest; Next.js/React/TypeScript, static-source pytest UI tests, `npx tsc` + `npm run build`.

## Open Decisions (resolve before the listed task)

- **D1 — race behavioral tests: DECIDED = (b).** No new JS test runner. Still extract the write-guard decision into the pure framework-free `shouldWriteSnapshot(...)` helper so the logic is centralized and `tsc`-checked, and assert its presence/shape via the static-source pytest test. Do NOT add Vitest. Race correctness is covered by the pure helper + the rapid A→B→A manual smoke (Task 7, step 2). Skip the optional `sessionSnapshot.test.ts`/`npx vitest` steps wherever the plan marks them "if D1 = (a)".
- **D2 — deploy target (Task 7):** user chose to **redeploy the existing `sadify-api` + `sadify-web` services (same domain/URLs)** rather than stand up a parallel site. Accepted trade-off: the judged URLs will serve the updated app. No separate Firestore DB or Drive root — dev shares the submitted project's data, so do destructive (delete) smoke only on throwaway test projects/accounts, never on demo data.

## Global Constraints

- Worktree: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`
- Branch: `codex/mvp-monorepo-scaffold`
- Do not change Q&A carry-forward strings, questionnaire logic, readiness logic, or the SAD preview/finalize flow.
- Mirror the existing repo pattern: every new repository has an in-memory class and a `Firestore*` class; `main.py` selects the Firestore variant only when `firestore_client is not None`.
- Keep all new endpoints on the existing projects router and reuse its `_verified_user`, `_active_repo_or_error`, `_live_drive_context`, and `_project_error` helpers; reuse existing error codes.
- Firestore document ids use `safe_doc_id(...)`; new collection is `project_sessions`.
- Resume persistence is signed-in + active-project only. No guest persistence.
- Delete moves the Drive folder to Trash (recoverable), never permanent-deletes; skip Drive for `LOCAL-` folder ids.
- Stop after every task for user review. Commit each task only after user approval. No deploy without explicit user approval.
- Backend verify from worktree root: `..\..\.venv\Scripts\python.exe -m pytest tests/ -q`. Frontend verify: `cd apps/web; npx tsc --noEmit; npm run build`.
- Docs in `docs/` are local/gitignored; do not commit docs unless the user asks.

---

## File Structure

### New Files
- `services/api/src/sadify_api/services/session_state.py` - `ProjectSessionSnapshot` repo (in-memory + Firestore).
- `tests/api/test_session_state.py` - repo unit tests.
- `tests/api/test_project_session_routes.py` - PUT/GET session endpoint tests.
- `tests/api/test_project_delete.py` - delete cascade + Drive trash tests.
- `apps/web/src/lib/hooks/useProjectSession.ts` - snapshot serialize/write + read/hydrate orchestration.
- `apps/web/src/components/shell/ConfirmDialog.tsx` - generic confirm dialog for delete.

### Modified Files
- `services/api/src/sadify_api/schemas.py` - add `ProjectSessionSnapshot`.
- `services/api/src/sadify_api/services/projects.py` - add `delete_project` to both repos + Protocol.
- `services/api/src/sadify_api/services/sad_save.py` - add `delete_for_project` to both repos + Protocol.
- `services/api/src/sadify_api/services/drive_repo.py` - add `clear_active_project` to both repos.
- `services/api/src/sadify_api/services/drive_client.py` - add `trash_folder` + `DriveFolderTrashError`.
- `services/api/src/sadify_api/routes/projects.py` - add PUT/GET `/session` and `DELETE /{id}`; accept the session repo dependency.
- `services/api/src/sadify_api/main.py` - construct + wire `session_snapshot_repository`.
- `apps/web/src/lib/api.ts` - `putProjectSession`, `getProjectSession`, `deleteProject` + types.
- `apps/web/src/lib/hooks/useQnA.ts` - add `hydrate`; expose `answerHistory`, `cleanRequirementText`.
- `apps/web/src/components/WorkspaceV2.tsx` - wire write/restore (with guards + restored source context) + delete reset.
- `apps/web/src/components/shell/ProjectList.tsx` - delete control.
- `apps/web/src/components/shell/Sidebar.tsx` - pass `onSignIn`, delete wiring.
- `apps/web/src/components/shell/AccountMenu.tsx` - guest state + tidy.
- `tests/test_mvp_project_ui.py` / `tests/test_tc0XX_*` static UI tests - assertions for new controls.

---

## Task 1: Session snapshot repository + schema

**Files:**
- Modify: `services/api/src/sadify_api/schemas.py`
- Create: `services/api/src/sadify_api/services/session_state.py`
- Test: `tests/api/test_session_state.py`

**Interfaces:**
- Produces: `ProjectSessionSnapshot` (Pydantic, `updated_at` server-owned/optional); `SessionSnapshotRepository` and `FirestoreSessionSnapshotRepository` with `upsert(grant_id, project_id, snapshot) -> ProjectSessionSnapshot`, `get(grant_id, project_id) -> ProjectSessionSnapshot | None`, `delete(grant_id, project_id) -> None`.

- [ ] **Step 1.1: Write failing repo tests (both variants)**

Cover the in-memory AND the Firestore repo using the existing fake client in `tests/api/test_firestore_repositories.py` (import its fake-client helper; check the top of that file for the exact fixture/constructor name). In `tests/api/test_session_state.py`:

```python
from datetime import UTC, datetime
import pytest
from sadify_api.schemas import ProjectSessionSnapshot
from sadify_api.services.session_state import (
    FirestoreSessionSnapshotRepository,
    SessionSnapshotRepository,
)
# Reuse the in-repo fake Firestore client (see tests/api/test_firestore_repositories.py
# for the exact import/fixture name — e.g. a FakeFirestoreClient()).
from tests.api.test_firestore_repositories import FakeFirestoreClient  # adjust to actual name


def _snapshot(text: str, updated_at=None) -> ProjectSessionSnapshot:
    return ProjectSessionSnapshot(
        clean_requirement_text=text,
        analysis_response=None,
        answer_history=[],
        source_context="",
        source_references=[],
        selected_model=None,
        status="in_progress",
        updated_at=updated_at,
    )


def _repos():
    return [SessionSnapshotRepository(), FirestoreSessionSnapshotRepository(FakeFirestoreClient())]


@pytest.mark.parametrize("repo", _repos())
def test_upsert_overwrites_latest_snapshot(repo):
    repo.upsert("G1", "PR-000001", _snapshot("first"))
    repo.upsert("G1", "PR-000001", _snapshot("second"))
    stored = repo.get("G1", "PR-000001")
    assert stored is not None
    assert stored.clean_requirement_text == "second"


@pytest.mark.parametrize("repo", _repos())
def test_upsert_stamps_updated_at_when_omitted(repo):
    repo.upsert("G1", "PR-000001", _snapshot("x", updated_at=None))
    assert repo.get("G1", "PR-000001").updated_at is not None


@pytest.mark.parametrize("repo", _repos())
def test_get_returns_none_when_absent(repo):
    assert repo.get("G1", "PR-000001") is None


@pytest.mark.parametrize("repo", _repos())
def test_delete_removes_snapshot_and_is_idempotent(repo):
    repo.upsert("G1", "PR-000001", _snapshot("x"))
    repo.delete("G1", "PR-000001")
    repo.delete("G1", "PR-000001")  # no-op, must not raise
    assert repo.get("G1", "PR-000001") is None
```

If the fake client's delete/get signatures differ from the real Firestore client, adapt `FirestoreSessionSnapshotRepository` to the same surface the other Firestore repos already rely on (it is the same `collection(...).document(...).set/get/delete` API).

- [ ] **Step 1.2: Run to verify failure**

`..\..\.venv\Scripts\python.exe -m pytest tests/api/test_session_state.py -q` — expected FAIL (module/schema missing).

- [ ] **Step 1.3: Add `ProjectSessionSnapshot` schema**

In `schemas.py`, add this class AFTER `RequirementAnalysisApiResponse` (line ~292):

```python
class ProjectSessionSnapshot(ApiModel):
    clean_requirement_text: str
    analysis_response: RequirementAnalysisApiResponse | None = None
    answer_history: list[str] = Field(default_factory=list)
    source_context: str = ""
    source_references: list[str] = Field(default_factory=list)
    selected_model: str | None = None
    status: Literal["in_progress"] = "in_progress"
    updated_at: datetime | None = None  # server-owned: PUT omits it, upsert() stamps it
```

Key points:
- `analysis_response` MUST be `RequirementAnalysisApiResponse` (the `{analysis_id, saved, analysis}` wrapper at `schemas.py:288`), not the inner `RequirementAnalysisResponse` — the frontend reads `analysisResponse.analysis` on resume.
- `updated_at` is `datetime | None = None` so PUT request bodies can omit it (a required field would 422 the round-trip); `upsert()` stamps it.
- No `source_labels` and no preview field in v1 (see spec "Out of scope for v1").
- Confirm `Literal`, `Field`, and `datetime` are already imported in `schemas.py`; add any missing import.

- [ ] **Step 1.4: Implement the repository module**

In `services/session_state.py`, follow the `projects.py` structure:

```python
from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from sadify_api.schemas import ProjectSessionSnapshot
from sadify_api.services.firestore_client import safe_doc_id, snapshot_data


class SessionSnapshotRepositoryProtocol(Protocol):
    def upsert(self, grant_id: str, project_id: str, snapshot: ProjectSessionSnapshot) -> ProjectSessionSnapshot: ...
    def get(self, grant_id: str, project_id: str) -> ProjectSessionSnapshot | None: ...
    def delete(self, grant_id: str, project_id: str) -> None: ...


class SessionSnapshotRepository:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], ProjectSessionSnapshot] = {}

    def upsert(self, grant_id, project_id, snapshot):
        stored = snapshot.model_copy(update={"updated_at": snapshot.updated_at or datetime.now(UTC)})
        self._records[(grant_id, project_id)] = stored
        return stored

    def get(self, grant_id, project_id):
        return self._records.get((grant_id, project_id))

    def delete(self, grant_id, project_id):
        self._records.pop((grant_id, project_id), None)


class FirestoreSessionSnapshotRepository:
    def __init__(self, client) -> None:
        self._client = client

    def _ref(self, grant_id, project_id):
        return self._client.collection("project_sessions").document(
            safe_doc_id(grant_id, project_id)
        )

    def upsert(self, grant_id, project_id, snapshot):
        stored = snapshot.model_copy(update={"updated_at": snapshot.updated_at or datetime.now(UTC)})
        self._ref(grant_id, project_id).set(
            {**stored.model_dump(mode="json"), "grant_id": grant_id, "project_id": project_id}
        )
        return stored

    def get(self, grant_id, project_id):
        data = snapshot_data(self._ref(grant_id, project_id).get())
        if data is None:
            return None
        data.pop("grant_id", None)
        data.pop("project_id", None)
        return ProjectSessionSnapshot.model_validate(data)

    def delete(self, grant_id, project_id):
        self._ref(grant_id, project_id).delete()


_session_snapshot_repository = SessionSnapshotRepository()


def get_session_snapshot_repository() -> SessionSnapshotRepository:
    return _session_snapshot_repository
```

- [ ] **Step 1.5: Verify**

`..\..\.venv\Scripts\python.exe -m pytest tests/api/test_session_state.py -q` then full suite `..\..\.venv\Scripts\python.exe -m pytest tests/ -q`. Expected: PASS, count grows only by new tests.

- [ ] **Step 1.6: Stop for user review.** Commit after approval:

```bash
git add services/api/src/sadify_api/schemas.py services/api/src/sadify_api/services/session_state.py tests/api/test_session_state.py
git commit -m "feat(api): add per-project session snapshot repository"
```

---

## Task 2: Session endpoints + DI wiring

**Files:**
- Modify: `services/api/src/sadify_api/routes/projects.py`
- Modify: `services/api/src/sadify_api/main.py`
- Test: `tests/api/test_project_session_routes.py`

**Interfaces:**
- Consumes: `SessionSnapshotRepository` (Task 1), existing `create_projects_router` signature, `_verified_user`, `_active_repo_or_error`.
- Produces: `PUT /projects/{project_id}/session` (204), `GET /projects/{project_id}/session` (`ProjectSessionSnapshot` or 204).

- [ ] **Step 2.1: Write failing endpoint tests**

In `tests/api/test_project_session_routes.py`, build the app with in-memory fakes the same way existing `tests/api/test_projects.py` does (copy its app/fixture setup), then:

```python
PAYLOAD = {
    "clean_requirement_text": "Bike rental ops",
    "analysis_response": None,
    "answer_history": ["Previous question: ...\nPrevious answer: hourly"],
    "source_context": "",
    "source_references": [],
    "selected_model": None,
    "status": "in_progress",
}  # note: no updated_at — the server stamps it


def test_put_then_get_session_round_trips(client_with_active_project):
    client, headers, project_id = client_with_active_project
    put = client.put(f"/projects/{project_id}/session", json=PAYLOAD, headers=headers)
    assert put.status_code == 204
    got = client.get(f"/projects/{project_id}/session", headers=headers)
    assert got.status_code == 200
    assert got.json()["clean_requirement_text"] == "Bike rental ops"
    assert got.json()["answer_history"][0].startswith("Previous question")
    assert got.json()["updated_at"] is not None  # server-stamped


def test_get_session_absent_returns_204(client_with_active_project):
    client, headers, project_id = client_with_active_project
    assert client.get(f"/projects/{project_id}/session", headers=headers).status_code == 204


def test_put_session_unknown_project_404(client_with_active_project):
    client, headers, _ = client_with_active_project
    resp = client.put("/projects/PR-999999/session", json=PAYLOAD, headers=headers)
    assert resp.status_code == 404


def test_get_session_unknown_project_404(client_with_active_project):
    client, headers, _ = client_with_active_project
    assert client.get("/projects/PR-999999/session", headers=headers).status_code == 404


def test_put_session_requires_auth(client_with_active_project):
    client, _, project_id = client_with_active_project
    assert client.put(f"/projects/{project_id}/session", json=PAYLOAD).status_code == 401
```

(The executor copies the fixture/app-construction helpers from `tests/api/test_projects.py`, passing a `session_snapshot_repository` fake into `create_app`.)

- [ ] **Step 2.2: Run to verify failure**

`..\..\.venv\Scripts\python.exe -m pytest tests/api/test_project_session_routes.py -q` — expected FAIL (routes + param missing).

- [ ] **Step 2.3: Thread the repo into the router**

In `routes/projects.py`, add `session_snapshot_repository` to `create_projects_router(...)` params (after `secret_store`), importing `SessionSnapshotRepository`. Add the endpoints inside the factory:

```python
@router.put("/{project_id}/session", status_code=204)
def put_project_session(
    project_id: str,
    snapshot: ProjectSessionSnapshot,
    authorization: str | None = Header(default=None),
) -> Response:
    user = _verified_user(authorization, token_verifier)
    repo = _active_repo_or_error(drive_repo_repository, user.uid)
    if project_repository.get_project(repo.grant_id, project_id) is None:
        raise _project_error(404, "PROJECT_NOT_FOUND", "Project not found in this Drive repo.")
    session_snapshot_repository.upsert(repo.grant_id, project_id, snapshot)
    return Response(status_code=204)


@router.get("/{project_id}/session")
def get_project_session(
    project_id: str,
    authorization: str | None = Header(default=None),
) -> Response:
    user = _verified_user(authorization, token_verifier)
    repo = _active_repo_or_error(drive_repo_repository, user.uid)
    if project_repository.get_project(repo.grant_id, project_id) is None:
        raise _project_error(404, "PROJECT_NOT_FOUND", "Project not found in this Drive repo.")
    snapshot = session_snapshot_repository.get(repo.grant_id, project_id)
    if snapshot is None:
        return Response(status_code=204)
    return JSONResponse(content=snapshot.model_dump(mode="json"))
```

GET validates the project exists with the same lookup as PUT (spec requires it).

Add `from fastapi import Response` and `from fastapi.responses import JSONResponse`, and import `ProjectSessionSnapshot` + `SessionSnapshotRepository`.

- [ ] **Step 2.4: Wire DI in `main.py`**

Add a `session_snapshot_repository` param to `create_app(...)` (default `None`), construct it like the others:

```python
session_snapshot_repository = session_snapshot_repository or (
    FirestoreSessionSnapshotRepository(firestore_client)
    if firestore_client is not None
    else SessionSnapshotRepository()
)
```

Import both classes from `sadify_api.services.session_state` and pass `session_snapshot_repository` into `create_projects_router(...)`.

- [ ] **Step 2.5: Verify**

`..\..\.venv\Scripts\python.exe -m pytest tests/api/test_project_session_routes.py tests/api/test_projects.py -q` then full suite. Expected: PASS.

- [ ] **Step 2.6: Stop for user review.** Commit after approval:

```bash
git add services/api/src/sadify_api/routes/projects.py services/api/src/sadify_api/main.py tests/api/test_project_session_routes.py
git commit -m "feat(api): add project session save/restore endpoints"
```

---

## Task 3: Frontend resume write + restore

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/hooks/useQnA.ts`
- Create: `apps/web/src/lib/sessionSnapshot.ts` (pure `shouldWriteSnapshot` helper)
- Create: `apps/web/src/lib/hooks/useProjectSession.ts`
- Modify: `apps/web/src/components/WorkspaceV2.tsx`
- Test: static-source pytest file (`tests/test_session_resume_ui.py`); plus, if Open Decision D1 = (a), `apps/web/src/lib/sessionSnapshot.test.ts` (Vitest) for the pure helper.

Do NOT modify `useSources.ts` or `useSadSave.ts` — they stay untouched (see spec: source context is restored at the `WorkspaceV2` level, and the SAD draft is not restored in v1).

**Interfaces:**
- Consumes: `PUT/GET /projects/{id}/session` (Task 2).
- Produces: `putProjectSession(idToken, projectId, payload)`, `getProjectSession(idToken, projectId) -> ProjectSessionSnapshot | null`; `useQnA()` additionally returns `hydrate(state)`, `answerHistory`, and `cleanRequirementText`.

- [ ] **Step 3.1: Write static-source assertions (failing)**

In the test file, assert the wiring exists in source:

```python
from pathlib import Path

WEB = Path("apps/web/src")

def test_api_exposes_session_client():
    src = (WEB / "lib/api.ts").read_text(encoding="utf-8")
    assert "putProjectSession" in src
    assert "getProjectSession" in src
    assert "deleteProject" in src  # added in Task 5, asserted together

def test_qna_exposes_hydrate():
    assert "hydrate" in (WEB / "lib/hooks/useQnA.ts").read_text(encoding="utf-8")

def test_workspace_restores_session_on_active_project():
    src = (WEB / "components/WorkspaceV2.tsx").read_text(encoding="utf-8")
    assert "getProjectSession" in src
    assert "putProjectSession" in src
```

Split the `deleteProject` assertion into the Task 5 test if you prefer task isolation.

- [ ] **Step 3.2: Run to verify failure**

`..\..\.venv\Scripts\python.exe -m pytest tests/test_session_resume_ui.py -q` — expected FAIL.

- [ ] **Step 3.3: Add API client functions + type**

First read 2-3 existing `api.ts` functions (e.g. `saveSadPreview`, `switchProject`) and copy their exact base-URL constant, header style, and error handling (`BackendApiError`). Add a `ProjectSessionSnapshot` TS interface mirroring the backend schema (with `analysis_response: RequirementAnalysisApiResponse | null`), then add `putProjectSession(idToken, projectId, snapshot): Promise<void>` (PUT, returns on 2xx, throws via the SAME error path as neighbors on non-ok) and `getProjectSession(idToken, projectId): Promise<ProjectSessionSnapshot | null>` (GET; return `null` on HTTP 204; throw on other non-ok). Do NOT invent helper names like `apiError`/`API_BASE_URL`; use whatever the existing functions use.

- [ ] **Step 3.4: Add `hydrate` to `useQnA` and expose carry-forward state**

In `useQnA.ts`, add and return `hydrate`, plus add `answerHistory` and `cleanRequirementText` to the returned object:

```ts
function hydrate(state: {
  requirementText: string;
  analysisResponse: RequirementAnalysisApiResponse | null;
  answerHistory: string[];
}) {
  setRequirementText(state.requirementText);
  setCleanRequirementText(state.requirementText);
  setAnalysisResponse(state.analysisResponse);
  setAnswerHistory(state.answerHistory);
  setSelectedChoiceIds([]);
  setAmendmentText("");
}
```

Return additions: `hydrate, answerHistory, cleanRequirementText`. Do not change any existing behavior.

- [ ] **Step 3.5: Add a pure write-guard helper + `useProjectSession` hook**

First add a pure, framework-free helper (testable without React; see Open Decision D1) in `apps/web/src/lib/sessionSnapshot.ts`:

```ts
export function shouldWriteSnapshot(args: {
  isSignedIn: boolean;
  activeProjectId: string | null;
  scheduledProjectId: string | null;   // project captured when the write was scheduled
  hasAnalysis: boolean;                 // qna.analysisResponse != null
  restoring: boolean;                   // a restore is in flight / just applied
}): boolean {
  const { isSignedIn, activeProjectId, scheduledProjectId, hasAnalysis, restoring } = args;
  if (!isSignedIn || !activeProjectId || !hasAnalysis || restoring) return false;
  return scheduledProjectId === activeProjectId; // never write a snapshot under a different project
}
```

Then create `useProjectSession.ts` exposing:
- `writeDebounced(projectId, snapshot, isCurrent)` - 800ms trailing debounce; on fire, re-check `isCurrent(projectId)` (which compares to `activeProjectRef.current`) and drop the write if false; fire-and-forget, `console.warn` on failure.
- `cancel()` - clears any pending timer (called by the project-change effect).
- `restore(projectId) -> Promise<{ projectId: string; snapshot: ProjectSessionSnapshot | null }>` - calls `getProjectSession` and echoes back the `projectId` so the caller can reject a stale response.

It resolves the Firebase id token internally (same `getFirebaseAuth().currentUser.getIdToken()` pattern the other hooks use).

- [ ] **Step 3.6: Wire into `WorkspaceV2` (race-safe)**

Add refs: `activeProjectRef` (useRef<string|null>), `restoringRef` (useRef<boolean>); and state: `restoredSourceContext`, `restoredSourceReferences`, `pendingModelRef` (useRef<string|null>).

Effective source values passed into `useQnA` and `useSadSave` instead of raw `sources.*`:

```ts
const effectiveSourceContext = sources.files.length ? sources.analysisContext : restoredSourceContext;
const effectiveSourceReferences = sources.files.length ? sources.sourceReferences : restoredSourceReferences;
```

Project-change effect (keyed on `driveRepo?.active_project_id`, signed-in only) — order matters:
1. Synchronously: `session.cancel()` (drop any pending write from the previous project); `activeProjectRef.current = activeProjectId`; `restoringRef.current = true`.
2. `await session.restore(activeProjectId)`. When it resolves, **discard if `result.projectId !== activeProjectRef.current`** (user already moved on).
3. If a fresh, matching snapshot exists: `qna.hydrate({ requirementText: snap.clean_requirement_text, analysisResponse: snap.analysis_response, answerHistory: snap.answer_history })`; set `restoredSourceContext`/`restoredSourceReferences`; for the model, if `models.isLoaded` and the id is in `models.catalog` call `models.setSelectedModel(...)`, else stash it in `pendingModelRef` for a later effect to apply once `models.isLoaded` flips true.
4. Finally `restoringRef.current = false` (in both the snapshot and no-snapshot branches, and on error).

Effect to apply a pending model once the catalog loads: keyed on `models.isLoaded`; if `pendingModelRef.current` is set and now in catalog, apply and clear it.

Write effect (debounced), keyed on `qna.analysisResponse` and `qna.cleanRequirementText`:
- Build `args` and call `shouldWriteSnapshot({ isSignedIn: auth.isSignedIn, activeProjectId: driveRepo?.active_project_id ?? null, scheduledProjectId: driveRepo?.active_project_id ?? null, hasAnalysis: qna.analysisResponse != null, restoring: restoringRef.current })`; return early if false.
- Otherwise build the payload from `qna.cleanRequirementText`, `qna.analysisResponse`, `qna.answerHistory`, `effectiveSourceContext`, `effectiveSourceReferences`, and `models.selectedModel`; `status: "in_progress"` (no `updated_at`, no labels). Call `session.writeDebounced(activeProjectId, payload, (pid) => pid === activeProjectRef.current)`.

Reset `restoredSourceContext`/`restoredSourceReferences` to empty whenever the user attaches a file (`sources.files.length > 0`) so live sources take over cleanly.

Note: the `restoringRef` gate replaces the old `skipNextWriteRef` — because the write effect returns while `restoringRef.current` is true, the restore's own `analysisResponse` change does not produce a write.

- [ ] **Step 3.7: Verify**

`..\..\.venv\Scripts\python.exe -m pytest tests/test_session_resume_ui.py -q`; then `cd apps/web; npx tsc --noEmit; npm run build`. If Open Decision D1 = (a): also `npx vitest run src/lib/sessionSnapshot.test.ts` covering: no write when `restoring`, no write when `scheduledProjectId !== activeProjectId`, no write when `hasAnalysis` is false, write when all clear. Expected: PASS / clean build.

- [ ] **Step 3.8: Stop for user review.** Commit after approval:

```bash
git add apps/web/src/lib/api.ts apps/web/src/lib/hooks/useQnA.ts apps/web/src/lib/sessionSnapshot.ts apps/web/src/lib/hooks/useProjectSession.ts apps/web/src/components/WorkspaceV2.tsx tests/test_session_resume_ui.py
git commit -m "feat(web): auto-resume in-progress session per project"
```

---

## Task 4: Delete cascade backend

**Files:**
- Modify: `services/api/src/sadify_api/services/drive_client.py`
- Modify: `services/api/src/sadify_api/services/projects.py`
- Modify: `services/api/src/sadify_api/services/sad_save.py`
- Modify: `services/api/src/sadify_api/services/drive_repo.py`
- Modify: `services/api/src/sadify_api/services/session_state.py` (already has `delete`)
- Modify: `services/api/src/sadify_api/routes/projects.py`
- Test: `tests/api/test_project_delete.py`

**Interfaces:**
- Produces: `DriveClient.trash_folder(access_token, folder_id)`; `ProjectRepository.delete_project(grant_id, project_id) -> ProjectRecord | None`; `SadSaveRepository.delete_for_project(grant_id, project_id) -> int`; `DriveRepoRepository.clear_active_project(grant_id, project_id) -> None`; `DELETE /projects/{project_id}` -> `ProjectListResponse`.

- [ ] **Step 4.1: Write failing tests**

In `tests/api/test_project_delete.py` (reuse the `tests/api/test_projects.py` app/fixture helpers + a fake Drive service that records `update` calls):

```python
def test_delete_project_cascades_and_trashes_drive(client_with_saved_project):
    client, headers, project_id, fakes = client_with_saved_project
    resp = client.delete(f"/projects/{project_id}", headers=headers)
    assert resp.status_code == 200
    assert all(p["project_id"] != project_id for p in resp.json()["projects"])
    assert fakes.project_repo.get_project(fakes.grant_id, project_id) is None
    assert fakes.sad_save_repo.list_for_project(grant_id=fakes.grant_id, project_id=project_id) == []
    assert fakes.session_repo.get(fakes.grant_id, project_id) is None
    assert fakes.drive_service.trashed_folder_ids == [fakes.drive_folder_id]


def test_delete_local_project_skips_drive(client_with_local_project):
    client, headers, project_id, fakes = client_with_local_project
    assert client.delete(f"/projects/{project_id}", headers=headers).status_code == 200
    assert fakes.drive_service.trashed_folder_ids == []


def test_delete_unknown_project_404(client_with_saved_project):
    client, headers, *_ = client_with_saved_project
    assert client.delete("/projects/PR-999999", headers=headers).status_code == 404


def test_delete_drive_failure_keeps_firestore(client_with_drive_failure):
    client, headers, project_id, fakes = client_with_drive_failure
    assert client.delete(f"/projects/{project_id}", headers=headers).status_code == 502
    assert fakes.project_repo.get_project(fakes.grant_id, project_id) is not None


def test_delete_persistence_failure_keeps_project_and_retry_succeeds(client_with_active_project):
    # Inject a sad_save_repo whose delete_for_project raises once, then succeeds.
    client, headers, project_id, fakes = client_with_active_project
    fakes.sad_save_repo.fail_next_delete = True
    first = client.delete(f"/projects/{project_id}", headers=headers)
    assert first.status_code == 502
    assert first.json()["detail"]["code"] == "PROJECT_DELETE_FAILED"
    assert fakes.project_repo.get_project(fakes.grant_id, project_id) is not None  # project deleted LAST
    second = client.delete(f"/projects/{project_id}", headers=headers)  # idempotent retry
    assert second.status_code == 200
    assert fakes.project_repo.get_project(fakes.grant_id, project_id) is None
```

Also add, with the existing fake Firestore client:
- a `DriveClient.trash_folder` unit test (mocked service) asserting `files().update(fileId=..., body={"trashed": True})` and that an API error raises `DriveFolderTrashError`;
- Firestore-variant tests for `FirestoreProjectRepository.delete_project` (removes project + name-index docs; no-op on missing) and `FirestoreSadSaveRepository.delete_for_project` (removes save docs + idempotency docs; no-op on missing).

- [ ] **Step 4.2: Run to verify failure**

`..\..\.venv\Scripts\python.exe -m pytest tests/api/test_project_delete.py -q` — expected FAIL.

- [ ] **Step 4.3: Add `DriveClient.trash_folder`**

In `drive_client.py`:

```python
class DriveFolderTrashError(Exception):
    pass


# inside DriveClient:
def trash_folder(self, access_token: str, folder_id: str) -> None:
    service = self._drive_service(access_token)
    try:
        service.files().update(fileId=folder_id, body={"trashed": True}).execute()
    except Exception as exc:
        raise DriveFolderTrashError("Could not move the project folder to Drive Trash.") from exc
```

- [ ] **Step 4.4: Add `delete_project` (both project repos + Protocol)**

In-memory: pop `(grant_id, project_id)` from `_records`, remove the id from `_order_by_grant[grant_id]` (guard if absent), return the removed record or None. Firestore: in a transaction, read the project; if missing return None (no-op); else delete `_project_ref(grant_id, project_id)` and the matching `_name_index_ref(grant_id, project.name)`, return the record. Must be idempotent (calling on an already-deleted project returns None, never raises). Add the method to `ProjectRepositoryProtocol`.

- [ ] **Step 4.5: Add `delete_for_project` (both sad-save repos + Protocol)**

In-memory: remove every `_records[(grant_id, project_id, save_id)]` and matching `_by_idempotency_key` entries; return the count (0 when none). Firestore: stream `sad_saves` where `repo_grant_id == grant_id and project_id == project_id`, delete each doc and its `sad_save_idempotency` doc (`_idempotency_hash(record.idempotency_key)` → `sad_save_idempotency/{hash}`), return the count. Idempotent: no matches → returns 0, never raises. Add to `SadSaveRepositoryProtocol`.

- [ ] **Step 4.6: Add `clear_active_project` (both drive repos)**

Add a method that nulls the active-project pointer for the grant only when it equals `project_id` (follow the existing `set_active_project` implementation in each `drive_repo.py` variant).

- [ ] **Step 4.7: Add the DELETE endpoint**

In `routes/projects.py`:

```python
@router.delete("/{project_id}", response_model=ProjectListResponse)
def delete_project(
    project_id: str,
    authorization: str | None = Header(default=None),
) -> ProjectListResponse:
    user = _verified_user(authorization, token_verifier)
    repo = _active_repo_or_error(drive_repo_repository, user.uid)
    project = project_repository.get_project(repo.grant_id, project_id)
    if project is None:
        raise _project_error(404, "PROJECT_NOT_FOUND", "Project not found in this Drive repo.")

    # 1. Drive Trash first; on failure nothing in Firestore is touched (retryable).
    if config.drive_mode == "live" and not project.drive_folder_id.startswith("LOCAL-"):
        live_drive_client, access_token = _live_drive_context(
            config=config, drive_client=drive_client, secret_store=secret_store, owner_uid=user.uid,
        )
        try:
            live_drive_client.trash_folder(access_token, project.drive_folder_id)
        except DriveFolderTrashError as exc:
            raise _project_error(502, "PROJECT_DELETE_DRIVE_FAILED", "Could not move the project folder to Drive Trash.") from exc

    # 2. Idempotent cascade; project doc LAST so a mid-cascade failure is retry-safe.
    try:
        sad_save_repository.delete_for_project(repo.grant_id, project_id)
        session_snapshot_repository.delete(repo.grant_id, project_id)
        project_repository.delete_project(repo.grant_id, project_id)
    except Exception as exc:
        raise _project_error(502, "PROJECT_DELETE_FAILED", "Could not finish deleting the project; retry.") from exc

    drive_repo_repository.clear_active_project(repo.grant_id, project_id)

    projects = project_repository.list_projects(repo.grant_id)
    drive_repo_repository.set_available_projects(grant_id=repo.grant_id, projects=projects)
    refreshed = drive_repo_repository.get_active_repo(user.uid)
    return ProjectListResponse(
        active_project_id=refreshed.active_project_id if refreshed else None,
        active_project_name=refreshed.active_project_name if refreshed else None,
        projects=projects,
    )
```

Import `DriveFolderTrashError`. (Confirm `set_available_projects` and `get_active_repo` exist as used; they are already used elsewhere in this router.) Every delete method (`delete_for_project`, session `delete`, `delete_project`, `clear_active_project`) MUST no-op when the data is already gone, so a retried `DELETE` after a partial failure runs cleanly.

- [ ] **Step 4.8: Verify**

`..\..\.venv\Scripts\python.exe -m pytest tests/api/test_project_delete.py tests/api/test_projects.py tests/api/test_drive_repo_live_mode.py -q` then full suite. Expected: PASS.

- [ ] **Step 4.9: Stop for user review.** Commit after approval:

```bash
git add services/api/src/sadify_api/services/drive_client.py services/api/src/sadify_api/services/projects.py services/api/src/sadify_api/services/sad_save.py services/api/src/sadify_api/services/drive_repo.py services/api/src/sadify_api/routes/projects.py tests/api/test_project_delete.py
git commit -m "feat(api): delete project with cascade and Drive trash"
```

---

## Task 5: Delete UI

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/components/shell/ConfirmDialog.tsx`
- Modify: `apps/web/src/components/shell/ProjectList.tsx`
- Modify: `apps/web/src/components/shell/Sidebar.tsx`
- Modify: `apps/web/src/components/WorkspaceV2.tsx`
- Test: `tests/test_mvp_project_ui.py` (extend) or `tests/test_project_delete_ui.py`

**Interfaces:**
- Consumes: `DELETE /projects/{id}` (Task 4).
- Produces: `deleteProject(idToken, projectId) -> ProjectListResponse`.

- [ ] **Step 5.1: Write static-source assertions (failing)**

```python
def test_project_list_has_delete_control():
    src = (WEB / "components/shell/ProjectList.tsx").read_text(encoding="utf-8")
    assert "Delete project" in src

def test_confirm_dialog_mentions_drive_trash():
    src = (WEB / "components/shell/ConfirmDialog.tsx").read_text(encoding="utf-8")
    assert "Trash" in src

def test_api_exposes_delete_project():
    assert "deleteProject" in (WEB / "lib/api.ts").read_text(encoding="utf-8")
```

- [ ] **Step 5.2: Run to verify failure** — expected FAIL.

- [ ] **Step 5.3: Add `deleteProject` to `api.ts`**

Add `deleteProject(idToken, projectId): Promise<ProjectListResponse>` doing a `DELETE /projects/{projectId}` with the bearer auth header, returning the parsed `ProjectListResponse` on success and throwing through the SAME `BackendApiError` path as the neighboring functions (e.g. `switchProject`). Reuse the existing base-URL constant and error handling — do not invent helper names.

- [ ] **Step 5.4: Add `ConfirmDialog`**

A small modal mirroring `CreateProjectDialog` styling: title, message, Cancel + a destructive confirm button, `busy` state. Message prop carries the Drive-Trash copy.

- [ ] **Step 5.5: Add the delete control to `ProjectList`**

Add an `onDelete?: (projectId: string) => void` prop and a hover-revealed trash icon-button per project with `aria-label={`Delete project ${project.name}`}`. Wire it to open the confirm dialog at the `Sidebar`/`WorkspaceV2` level (lift the deleting-project id into state).

- [ ] **Step 5.6: Wire `Sidebar` + `WorkspaceV2`**

`Sidebar` passes through an `onDeleteProject` handler. `WorkspaceV2` (which owns `driveRepo`) implements it: open `ConfirmDialog`; on confirm call `deleteProject(idToken, projectId)`, then refetch `getDriveRepoStatus(idToken)` and `setDriveRepo(...)` for the canonical record (do NOT hand-map `ProjectListResponse` into `DriveRepoRecord`). If the deleted project was the active one, reset the workspace (`qna.reset()`, `sources.reset()`, `sadSave.dismissPreview()`).

- [ ] **Step 5.7: Verify**

`..\..\.venv\Scripts\python.exe -m pytest tests/test_project_delete_ui.py -q`; `cd apps/web; npx tsc --noEmit; npm run build`.

- [ ] **Step 5.8: Stop for user review.** Commit after approval:

```bash
git add apps/web/src/lib/api.ts apps/web/src/components/shell/ConfirmDialog.tsx apps/web/src/components/shell/ProjectList.tsx apps/web/src/components/shell/Sidebar.tsx apps/web/src/components/WorkspaceV2.tsx tests/test_project_delete_ui.py
git commit -m "feat(web): delete project with confirm dialog"
```

---

## Task 6: Profile menu fix

**Files:**
- Modify: `apps/web/src/components/shell/AccountMenu.tsx`
- Modify: `apps/web/src/components/shell/Sidebar.tsx`
- Modify: `apps/web/src/components/WorkspaceV2.tsx`
- Test: `tests/test_account_menu_ui.py`

**Interfaces:**
- Produces: `AccountMenu` accepts `onSignIn: () => void`; guest branch renders sign-in, signed-in branch unchanged except de-duplicated identity.

- [ ] **Step 6.1: Write static-source assertions (failing)**

```python
def test_account_menu_has_guest_sign_in():
    src = (WEB / "components/shell/AccountMenu.tsx").read_text(encoding="utf-8")
    assert "Sign in with Google" in src
    assert "onSignIn" in src

def test_sidebar_passes_sign_in_to_account_menu():
    src = (WEB / "components/shell/Sidebar.tsx").read_text(encoding="utf-8")
    assert "onSignIn" in src
```

- [ ] **Step 6.2: Run to verify failure** — expected FAIL.

- [ ] **Step 6.3: Update `AccountMenu`**

Add `onSignIn` to props. Compute `isSignedIn = Boolean(name || email)`. When not signed in:
- collapsed row: avatar `?`, label "Guest", a "Sign in" chip (not the Drive/Connect chip);
- open menu: a single primary "Sign in with Google" item calling `onSignIn`, no "Signed in" header, no Drive section, no "Sign out".

When signed in: keep one identity row (remove the duplicate name from the menu body, keeping the collapsed-row header), keep Drive connect/disconnect and Sign out.

- [ ] **Step 6.4: Wire `onSignIn`**

`Sidebar` gains an `onSignIn` prop passed to `AccountMenu`; `WorkspaceV2` passes `onSignIn={() => void auth.signIn().catch(() => undefined)}` (same call `StartBox` uses).

- [ ] **Step 6.5: Verify**

`..\..\.venv\Scripts\python.exe -m pytest tests/test_account_menu_ui.py -q`; `cd apps/web; npx tsc --noEmit; npm run build`.

- [ ] **Step 6.6: Stop for user review.** Commit after approval:

```bash
git add apps/web/src/components/shell/AccountMenu.tsx apps/web/src/components/shell/Sidebar.tsx apps/web/src/components/WorkspaceV2.tsx tests/test_account_menu_ui.py
git commit -m "feat(web): fix guest profile menu and tidy account menu"
```

---

## Task 7: Local smoke + docs closure

**Files:** Local ignored docs only.

- [ ] **Step 7.1: Full regression**

`..\..\.venv\Scripts\python.exe -m pytest tests/ -q`; `cd apps/web; npx tsc --noEmit; npm run build`. Report the suite count and build result.

- [ ] **Step 7.2: Manual browser smoke (user-run, narrated case by case)**

1. Sign in, connect Drive, create project, run partial Q&A, refresh / switch project → conversation + readiness restore.
2. Switch A → B → A rapidly mid-answer → each project shows only its own conversation; no cross-contamination, no lost progress; "New SAD" then navigate away and back → the prior saved snapshot is NOT wiped.
3. Delete a **throwaway test** project → it disappears, its Drive folder is in Trash, and the active workspace resets if it was active. (Do NOT delete demo/submission data — dev shares the submitted Firestore/Drive.)
4. Sign out → profile menu shows "Sign in with Google", not "Sign out".

(The SAD draft is re-generated with one "Quick draft" click after resume; it is not auto-restored in v1.)

- [ ] **Step 7.3: Docs closure (do not commit unless user asks)**

Create `docs/superpowers/testing/test_cases/TC-035-session-and-data-management.md` with expected/real/evidence/decision; add a decision-log entry for delete semantics (Drive Trash, recoverable) and per-project session snapshots; update `CURRENT.md` and `test_case_index.md`.

- [ ] **Step 7.4: Deploy only on explicit user approval.** Per Open Decision D2, **redeploy the existing `sadify-api` then `sadify-web` services** (same URLs/domain) with the TC-027 two-service mechanics — no new services, no new data store. Prod runs Firestore persistence (`SADIFY_PERSISTENCE=firestore`), so the new `project_sessions` collection and the delete cascade are durable across instances; keep `--max-instances 1` only if the in-memory fallback is ever used. Confirm CORS (`SADIFY_ALLOWED_ORIGINS`) and Firebase authorized domains are unchanged (same domain).

---

## Self-Review

- Spec coverage:
  - Feature 1 resume: Tasks 1-3 (repo, endpoints, frontend write/restore).
  - Feature 2 delete: Tasks 4-5 (backend cascade + Drive trash, UI).
  - Feature 3 profile: Task 6.
  - Smoke + docs: Task 7.
- Type consistency: `ProjectSessionSnapshot.analysis_response` is `RequirementAnalysisApiResponse` (wrapper) in schema (1.3), TS type (3.3), and matches `useQnA.analysisResponse`; `updated_at` is server-owned/optional so PUT bodies omit it; `delete_project`, `delete_for_project`, `clear_active_project`, `trash_folder` names are used consistently in Task 4 and the DELETE route.
- Resolved review findings: server-owned `updated_at` (no 422); GET `/session` validates project existence; both PUT and GET 404 tests; Firestore-variant tests for the session repo and the delete methods; race-safe write/restore (current-project ref, restoring gate, cancel-on-change, fire-time project check, stale-restore discard) via a pure `shouldWriteSnapshot` helper; idempotent delete cascade with the project doc last + 502 `PROJECT_DELETE_FAILED` + retry test; model restore gated on `models.isLoaded`; `source_labels` dropped; preview-restore promises removed from goal + smoke.
- Risk controls:
  - Resume is signed-in + active-project only; guest path untouched.
  - SAD draft preview is intentionally NOT restored (avoids the `useSadSave` reset-effect conflict); Q&A + readiness restore, draft re-generates on demand.
  - Write effect is guarded against empty/`null` analysis, the restoring window, and wrong-project writes — so "New SAD" and rapid project switches cannot clobber or cross-contaminate a snapshot.
  - Snapshot write is fire-and-forget; Q&A never blocks on persistence.
  - Delete trashes (recoverable), aborts before Firestore writes if Drive trash fails, deletes the project doc last, is idempotent (retry-safe), and the UI refetches Drive status rather than mapping shapes.
  - Both in-memory and Firestore variants are implemented and tested for every new repo method.
- Open decisions D1 (race behavioral tests / Vitest) and D2 (same-domain redeploy) are recorded at the top; D1 must be answered before Task 3.
- Review stops: stop after each task; commit only after user review; no deploy without explicit approval.
```