# TC-026E MVP Project Save History

Date Created: 2026-05-28
Last Updated: 2026-05-29
Status: Passed (per-project save history, refresh-survival, cross-project isolation verified)

## Purpose

Expose a per-project list of prior SAD saves so users can review their
save history after a page refresh or when switching projects. The data
lives in backend memory (lost on uvicorn restart; Firestore persistence
is post-MVP). One backend endpoint, one new repository method, one new
frontend panel.

## Inputs

- Live signed-in Firebase user with an active Drive grant and at least
  one project.
- One or more prior SAD saves in the active project.

## Preconditions

- TC-026D project isolation passed.
- Live OAuth + Drive infrastructure from TC-026B in place.

## Scope

In scope:

1. `GET /projects/{project_id}/saves` returning a `ProjectSavesResponse`
   (most-recent-first list of `SadSaveSummary`).
2. `SadSaveRepository.list_for_project(grant_id, project_id)` reading the
   in-memory records, sorted descending by `created_at`.
3. New `SadSaveSummary` and `ProjectSavesResponse` Pydantic models
   (appended; nothing else touched).
4. Frontend `ProjectHistoryPanel` rendering the list with Open Doc links.
5. Auto-refresh of the panel after each successful save and on project
   switch (driven by `activeProjectId` change + a `refreshKey`).
6. Page-refresh restore: `WorkspaceShell` re-fetches `/drive/repo/status`
   on Firebase auth-state restore so the active project (and therefore
   history) reappears after F5.

Out of scope:

- Wiki update history.
- Firestore persistence (in-memory only).
- Pagination, search, edit, delete.
- Any Drive API call in the history path (metadata-only read).

## Steps

See manual smoke Case 20 below.

## Expected Output

- `GET /projects/{project_id}/saves 200` returns the project's saves,
  most-recent-first, each with `save_id`, `preview_id`, `doc_url`,
  `doc_path`, `title`, `change_summary`, `source_ids`, `created_at`.
- History endpoint enforces auth + active repo + project existence with
  `PROJECT_AUTH_REQUIRED`, `PROJECT_REPO_REQUIRED`,
  `PROJECT_REPO_DISCONNECTED`, `PROJECT_NOT_FOUND`.
- History endpoint makes NO Drive call (in-memory metadata only); works
  in both local and live mode.
- Frontend history panel refreshes after a save without page reload,
  reloads on project switch, and re-renders after a full page refresh.

## Real Output

Implementation commit: `8f1a302 feat(history): per-project save history
endpoint and UI panel`.

Automated verification on 2026-05-29:
- Full Python regression with `SADIFY_DRIVE_MODE=local`: **446 passed**
  (was 428 before TC-026E; +18 new tests).
- Frontend `npx -y tsc --noEmit`: clean.
- New backend tests: 5 for `list_for_project`, 8 for the history route.
  New frontend static tests: 4 for `ProjectHistoryPanel`.

Live manual smoke (Case 20) on 2026-05-29:

```text
Part A  build history in one project
  POST /sad/save                       409  PROJECT_REQUIRED
  POST /projects                       200  PR (Pet Grooming V2)
  POST /sad/save                       200  SV-000001
  GET  /projects/{id}/saves            200  -> 1 row in panel
  POST /sad/save                       200  SV-000002 (SP-000002)
  GET  /projects/{id}/saves            200  -> 2 rows, most-recent first

Part B  page refresh survival
  (F5 reload)
  GET  /drive/repo/status              200  active project restored
  GET  /projects/{id}/saves            200  -> both rows re-render automatically

Part C  cross-project isolation
  POST /projects                       200  Catering Events (PR-000003)
  POST /sad/save                       200  SV-000001 (SP-000003, per-project counter reset)
  GET  /projects/PR-000003/saves       200  -> 1 row (Catering)
  POST /projects/switch                200  -> Pet Grooming V2
  GET  /projects/PR-000002/saves       200  -> 2 rows (Pet Grooming)
  POST /projects/switch                200  -> Catering Events
  GET  /projects/PR-000003/saves       200  -> 1 row (Catering)
```

History always matched the active project; no cross-contamination. Open
Doc links opened the correct real Google Docs.

## Differences / Issues

1. History is in-memory; uvicorn restart wipes it. The real Google Docs
   in Drive survive, but SADify forgets they exist until re-saved.
   Firestore persistence is post-MVP.
2. `getDriveRepoStatus` failures in the auth-restore effect are swallowed
   silently (`catch { setDriveRepo(null) }`); a transient failure drops
   the UI repo/project state until the next auth change. Acceptable for
   MVP; defer.
3. History panel renders the full `change_summary` per row; verbose for
   many saves. Cosmetic; defer.

Unrelated bug surfaced during Case 20 (NOT a TC-026E defect — logged for
the next slice): analysis state is not reset when a new source or
project is analysed in the same session. Once an analysis reaches 100%
with all slots locked, subsequent analyses (`AN-000012/13/14` in the
Case 20 log) inherit the saturated locked state via carry-forward, so a
new source (catering) produced a SAD contaminated with the prior
source's content (pet grooming). This unifies three earlier symptoms
(the "I'm not sure" accepted answer, 100% with no questions on a
complete source, and cross-source content bleed) into one root cause:
no per-source/per-project analysis-state reset boundary. Tracked for a
dedicated investigation slice before TC-027.

## Evidence

- Commit `8f1a302`; 446 local-mode tests; TS clean.
- Backend↔frontend `SadSaveSummary` field types align exactly.
- History endpoint confirmed Drive-free (reads only
  `SadSaveRepository.list_for_project`).
- Live Case 20 passed all three parts; backend log shows correct
  per-project `GET /projects/{id}/saves` for every switch and refresh.
- No refresh tokens or OAuth secrets in logs.

## Decision

Passed. Per-project save history is live, survives page refresh, and is
correctly isolated across projects. The plumbing is sound. A separate
analysis-state reset bug (surfaced, not caused, by this test) is the
next priority before TC-027 deploy.
