# TC-026E Project Save History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose a per-project list of prior SAD saves so users can see their save history after a page refresh or when switching projects. Adds one backend endpoint (`GET /projects/{project_id}/saves`), one new frontend `ProjectHistoryPanel` component, and a callback wiring so new saves immediately appear in the list. Survives page refresh (data lives in backend memory). Lost on uvicorn restart — Firestore persistence is post-MVP.

**Architecture:** `SadSaveRepository` gains a `list_for_project(grant_id, project_id)` query returning records sorted by `created_at` descending. A new authenticated route `GET /projects/{project_id}/saves` validates the active repo + project ownership and returns the list. Frontend `ProjectHistoryPanel` fetches the list on project switch and on mount, plus refreshes after every successful `saveSadPreview()` call via a callback prop. Each history row links to the real Drive Doc URL.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, pytest, Next.js/React, TypeScript. No new backend or npm dependencies.

---

Date: 2026-05-28

Status: Draft - awaiting approval

## Traceability Sources

- `CLAUDE.md`
- `context.md`
- `docs/superpowers/CURRENT.md`
- `docs/superpowers/plans/2026-05-28-tc026d-project-isolation.md`
- `docs/superpowers/testing/test_cases/TC-026D-mvp-project-isolation.md` (forthcoming)
- `docs/superpowers/development/07_decision_log.md`

## Pre-Plan Decisions (locked)

| Decision | Choice |
|---|---|
| History scope | SAD saves only. Wiki history deferred to a future slice. |
| Storage | In-memory (existing `SadSaveRepository`). Firestore persistence is post-MVP. |
| Sort order | Most recent first (created_at descending). |
| Pagination | None for MVP. Each project rarely exceeds 10–20 saves; render all. |
| Click action | Each row links to the real Drive Doc URL (opens in new tab). Optionally expandable to show `preview_id`, `change_summary`, and source references; defer expansion UI if time-constrained. |
| Refresh triggers | Mount, project switch, after a successful new save (callback from `SadPreviewPanel`), and a manual Refresh button. |

## Cloud Prerequisites

None new. Pure in-memory plus existing live OAuth.

## Scope Lock

In scope:

- New backend endpoint `GET /projects/{project_id}/saves` returning a list of `SadSaveSummary` entries.
- Existing `SadSaveRepository` gains `list_for_project(grant_id, project_id) -> list[SadSaveRecord]`.
- New Pydantic models `SadSaveSummary` and `ProjectSavesResponse` (appended).
- Stable error codes: `PROJECT_AUTH_REQUIRED`, `PROJECT_REPO_REQUIRED`, `PROJECT_REPO_DISCONNECTED`, `PROJECT_NOT_FOUND` (reused from TC-026D where applicable).
- New frontend component `ProjectHistoryPanel`.
- Wiring in `WorkspaceShell` so history refreshes after a new SAD save.
- One new manual smoke case (Case 20).

Out of scope:

- Wiki update history.
- Firestore persistence.
- Pagination, search, or filter.
- Editing or deleting past saves from the UI.
- Bulk download.
- Showing history across all projects in one view.
- Schema changes beyond appending two new response models.

## Endpoint Contract

### `GET /projects/{project_id}/saves`

Authenticated. Works in both local and live mode (matches TC-026D).

Path parameter:

```text
project_id   — PR-XXXXXX
```

Response 200 body:

```json
{
  "project_id": "PR-000001",
  "project_name": "Pet Grooming Appointments",
  "saves": [
    {
      "save_id": "SV-000002",
      "preview_id": "SP-000002",
      "doc_url": "https://docs.google.com/document/d/.../edit",
      "doc_path": "SAD/SAD-SP-000002-SV-000002.google_doc",
      "title": "SAD Preview for Pet Grooming Appointment Management System (AN-000012)",
      "change_summary": "SAD preview SP-000002 saved to ...",
      "source_ids": ["SRC-000001"],
      "created_at": "2026-05-28T08:00:00Z"
    },
    {
      "save_id": "SV-000001",
      "preview_id": "SP-000001",
      "doc_url": "https://docs.google.com/document/d/.../edit",
      "doc_path": "SAD/SAD-SP-000001-SV-000001.google_doc",
      "title": "...",
      "change_summary": "...",
      "source_ids": ["SRC-000001"],
      "created_at": "2026-05-28T07:00:00Z"
    }
  ]
}
```

Sorted most-recent-first. Empty list when the project has no saves yet.

Stable rejection codes:

| Case | HTTP | Code | Message |
| --- | --- | --- | --- |
| Unsigned-in | 401 | `PROJECT_AUTH_REQUIRED` | `Sign in to view project history.` |
| No active repo | 409 | `PROJECT_REPO_REQUIRED` | `Connect a Google Drive project repo first.` |
| Repo disconnected | 409 | `PROJECT_REPO_DISCONNECTED` | `Reconnect Google Drive to view project history.` |
| Project not found in this repo | 404 | `PROJECT_NOT_FOUND` | `Project not found in this Drive repo.` |

## Schema Contract

Two new Pydantic models appended to `schemas.py`:

```python
class SadSaveSummary(ApiModel):
    save_id: str
    preview_id: str
    doc_url: str | None
    doc_path: str
    title: str
    change_summary: str
    source_ids: list[str]
    created_at: datetime

class ProjectSavesResponse(ApiModel):
    project_id: str
    project_name: str
    saves: list[SadSaveSummary]
```

No other models touched.

## Configuration

No new env vars.

## Files To Change

Backend (worktree `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`):

- Modify: `services/api/src/sadify_api/services/sad_save.py` (add `list_for_project`).
- Modify: `services/api/src/sadify_api/routes/projects.py` (add `GET /{project_id}/saves`).
- Modify: `services/api/src/sadify_api/schemas.py` (append `SadSaveSummary`, `ProjectSavesResponse`).
- Test: `tests/api/test_projects.py` (extend with history-list cases) OR new `tests/api/test_project_history.py`.
- Test: `tests/api/test_sad_save.py` (extend with `list_for_project` cases).

Frontend:

- Create: `apps/web/src/components/ProjectHistoryPanel.tsx`.
- Modify: `apps/web/src/lib/api.ts` (add `listProjectSaves(idToken, projectId)`, `SadSaveSummary`, `ProjectSavesResponse` types).
- Modify: `apps/web/src/components/WorkspaceShell.tsx` (mount `ProjectHistoryPanel`, refresh callback after `applySadSaved`).
- Modify: `apps/web/src/components/SadPreviewPanel.tsx` (call the refresh callback after successful save).
- Modify: `apps/web/src/components/ProjectPanel.tsx` (also refresh history on project switch).
- Test: `tests/test_mvp_project_ui.py` (extend with history static checks) OR new `tests/test_mvp_project_history_ui.py`.

Docs (after Task 6 passes):

- Create: `docs/superpowers/testing/test_cases/TC-026E-mvp-project-history.md`.
- Modify: `docs/superpowers/CURRENT.md`.
- Modify: `docs/superpowers/testing/test_case_index.md`.
- Modify: `docs/superpowers/development/07_decision_log.md`.

## Task 0: Approval Gate

- [ ] **Step 0.1: Wait for user approval.** Do not modify code until the user explicitly approves this plan.
- [ ] **Step 0.2: Confirm worktree.** Latest commit must be `928d7f7 feat(projects): per-project Drive isolation with active project switching`. Working tree clean.

## Task 1: SadSaveRepository — list_for_project

**Files:** Modify `services/sad_save.py`, extend `tests/api/test_sad_save.py`.

- [ ] **Step 1.1: Write tests first.**

Cover:

```text
test_list_for_project_returns_empty_when_no_saves_yet
test_list_for_project_returns_only_saves_for_given_project
test_list_for_project_returns_records_sorted_most_recent_first
test_list_for_project_isolated_per_repo_grant
test_list_for_project_excludes_other_projects_in_same_grant
```

- [ ] **Step 1.2: Implement.**

```python
def list_for_project(
    self,
    *,
    grant_id: str,
    project_id: str,
) -> list[SadSaveRecord]:
    return sorted(
        [
            record
            for record in self._records.values()
            if record.repo_grant_id == grant_id and record.project_id == project_id
        ],
        key=lambda record: record.created_at,
        reverse=True,
    )
```

- [ ] **Step 1.3: Run tests.** Expect 5 pass.

## Task 2: Schemas

**Files:** Modify `services/api/src/sadify_api/schemas.py`.

- [ ] **Step 2.1: Append `SadSaveSummary` and `ProjectSavesResponse`** as specified above.

No tests required for pure model additions; coverage comes via route tests.

## Task 3: Project History Route

**Files:** Modify `services/api/src/sadify_api/routes/projects.py`, test in `tests/api/test_projects.py` (or sibling file).

- [ ] **Step 3.1: Write route tests first.**

Cover:

```text
test_list_project_saves_returns_empty_for_new_project
test_list_project_saves_returns_saves_in_descending_order
test_list_project_saves_includes_doc_url_and_change_summary
test_list_project_saves_blocks_unsigned
test_list_project_saves_blocks_without_active_repo
test_list_project_saves_blocks_when_repo_disconnected
test_list_project_saves_returns_404_for_unknown_project_id
test_list_project_saves_isolates_across_projects
```

- [ ] **Step 3.2: Implement `GET /{project_id}/saves`.**

```python
@router.get("/{project_id}/saves", response_model=ProjectSavesResponse)
def list_project_saves(
    project_id: str,
    authorization: str | None = Header(default=None),
) -> ProjectSavesResponse:
    user = _verified_user(authorization, token_verifier)
    repo = _active_repo_or_error(drive_repo_repository, user.uid)
    project = project_repository.get_project(repo.grant_id, project_id)
    if project is None:
        raise _project_error(404, "PROJECT_NOT_FOUND", "Project not found in this Drive repo.")
    records = sad_save_repository.list_for_project(
        grant_id=repo.grant_id, project_id=project.project_id
    )
    return ProjectSavesResponse(
        project_id=project.project_id,
        project_name=project.name,
        saves=[
            SadSaveSummary(
                save_id=record.save_id,
                preview_id=record.preview_id,
                doc_url=record.sad_doc.url,
                doc_path=record.sad_doc.path,
                title=record.sad_doc.title,
                change_summary=record.change_summary,
                source_ids=[ref.source_id for ref in record.source_artifact_references],
                created_at=record.created_at,
            )
            for record in records
        ],
    )
```

- [ ] **Step 3.3: Run tests.** Expect 8 pass.

## Task 4: Frontend API helpers + ProjectHistoryPanel

**Files:** Modify `apps/web/src/lib/api.ts`. Create `apps/web/src/components/ProjectHistoryPanel.tsx`. Tests new in `tests/test_mvp_project_history_ui.py` (or extend the existing project UI test file).

- [ ] **Step 4.1: Add TS types and helper.**

```typescript
export type SadSaveSummary = {
  save_id: string;
  preview_id: string;
  doc_url: string | null;
  doc_path: string;
  title: string;
  change_summary: string;
  source_ids: string[];
  created_at: string;
};

export type ProjectSavesResponse = {
  project_id: string;
  project_name: string;
  saves: SadSaveSummary[];
};

export async function listProjectSaves(
  idToken: string,
  projectId: string,
): Promise<ProjectSavesResponse>;
```

- [ ] **Step 4.2: Write static UI tests first.** Mirror existing project UI test pattern. Cover:

```text
test_history_panel_file_exists
test_api_ts_exports_list_project_saves
test_history_panel_renders_empty_state_for_no_saves
test_history_panel_renders_save_rows_with_doc_link
test_history_panel_refreshes_on_project_switch_callback
```

- [ ] **Step 4.3: Implement `ProjectHistoryPanel`.**

Props:

```typescript
type Props = {
  activeProjectId: string | null;
  refreshKey: number;          // incremented by parent after a new save
};
```

Behavior:

```text
On mount and whenever activeProjectId or refreshKey changes, call listProjectSaves
  (skip when activeProjectId is null).
Show "No saves yet" when saves is empty.
Otherwise render a list:
  • SV-000002 · 2026-05-28 11:00 · [Open Doc ↗]
  • SV-000001 · 2026-05-28 09:00 · [Open Doc ↗]
Include a small "Refresh" button that bumps a local force-reload counter.
```

No expansion UI needed for MVP.

## Task 5: Wire WorkspaceShell + SadPreviewPanel + ProjectPanel

**Files:** Modify `apps/web/src/components/WorkspaceShell.tsx`, `SadPreviewPanel.tsx`, `ProjectPanel.tsx`.

- [ ] **Step 5.1: Add `historyRefreshKey` state in WorkspaceShell.**

```typescript
const [historyRefreshKey, setHistoryRefreshKey] = useState(0);
```

- [ ] **Step 5.2: Mount `ProjectHistoryPanel`** under `ProjectPanel` with `activeProjectId` and `refreshKey={historyRefreshKey}`.

- [ ] **Step 5.3: Wire refresh after save.**

In `WorkspaceShell.applySadSaved`, bump `setHistoryRefreshKey(prev => prev + 1)` after the existing state update.

- [ ] **Step 5.4: Wire refresh after project switch.**

In `ProjectPanel`, when the user switches projects, bump the same key (pass a `onProjectSwitched` callback through). Alternatively rely on `activeProjectId` change inside `ProjectHistoryPanel` — already covered by the dependency array. The `historyRefreshKey` bump is only needed when activeProjectId is unchanged but content changes (i.e., new save in current project).

- [ ] **Step 5.5: TypeScript gate.** `npx -y tsc --noEmit` clean.

## Task 6: Verification + Manual Smoke

- [ ] **Step 6.1: Full Python regression with `SADIFY_DRIVE_MODE=local`.** Expect baseline 428 + ~13 new tests, all green.

- [ ] **Step 6.2: TypeScript gate.** Clean.

- [ ] **Step 6.3: Live manual smoke — Case 20.**

```text
Case 20 (project save history persists across page refresh and switch):
   1. With both Pet Grooming and Catering Events existing from TC-026D
      smoke (each with 2 saves), refresh the browser page.
   2. After reload, sign in is restored automatically. ProjectPanel shows
      both projects.
   3. Pick Pet Grooming -> ProjectHistoryPanel below it renders 2 rows:
      SV-000002, SV-000001 with Doc links.
   4. Click "Open Doc ↗" on SV-000001 -> opens the real Drive Doc in new
      tab. Doc loads correctly.
   5. Switch to Catering Events -> history list updates to show its 2
      saves.
   6. Do another save in Catering Events. The history list adds the new
      SV-000003 row at the top without page refresh.
```

- [ ] **Step 6.4: Commit.** Single commit:

```text
feat(history): per-project save history endpoint and UI panel
```

## Task 7: Documentation Closure

- [ ] **Step 7.1: Create `TC-026E-mvp-project-history.md`** with full evidence.
- [ ] **Step 7.2: Update CURRENT.md.** Flip TC-026E to passed; next focus TC-027.
- [ ] **Step 7.3: Append decision-log entry.**
- [ ] **Step 7.4: Flip TC-026E row in test_case_index.md.**

## Stop Rules

- Plan not yet approved.
- Schema changes touch anything beyond the two new response models.
- Backend reads `SadSaveRepository._records` directly bypassing the new `list_for_project` method (must go through the method so future Firestore swap is a one-place change).
- A new env var or dependency seems necessary.
- Existing TC-026D / TC-026B / TC-025B tests fail after rewrites.

Honor `CLAUDE.md` sections 1, 2, 4.1, 4.2, 4.3, 5.1, 6, 7.1, 7.2, 7.3.

## Verification Summary Required Before Completion

```text
New backend test counts (sad_save list_for_project, project history route).
Frontend static test counts.
Full pytest count with SADIFY_DRIVE_MODE=local.
TypeScript --noEmit result.
Manual smoke Case 20 result.
Confirmation that history renders after page refresh.
Confirmation that history refreshes after a new save without page reload.
Confirmation that switching projects loads the correct project's history.
```
