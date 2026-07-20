# Recoverable GitHub Issue Creation Design

Date: 2026-06-19
Status: Approved design - ready for implementation

## Traceability Sources

- `CLAUDE.md` and `context.md` - local-first discipline, authenticated writes, scope control, documentation requirements.
- `docs/superpowers/development/02_agent_behavior_contract.md` - approval-gated agent writes and visible failure behavior.
- `docs/superpowers/development/03_data_model_and_output_schema.md` - Firestore ownership, project isolation, and durable record conventions.
- `docs/superpowers/development/07_decision_log.md` - GATE 3 approval, project isolation, Firestore persistence, and GitHub MCP decisions.
- `docs/superpowers/plans/2026-06-05-tc034-p5-github-issues-mcp.md` - current GitHub issue prepare/approve flow.
- `docs/superpowers/specs/2026-06-18-session-and-data-management-design.md` - project delete cascade and deployment bundling context.
- Repository findings verified on 2026-06-19:
  - `services/api/src/sadify_api/services/github_issue_flow.py`
  - `services/api/src/sadify_api/agent/approval.py`
  - `services/api/src/sadify_api/services/sad_preview.py`
  - `services/api/src/sadify_api/services/sad_save.py`
  - `services/api/src/sadify_api/routes/{agent,projects}.py`
  - `services/api/src/sadify_api/main.py`
  - `services/mcp/github_server.py`
  - `apps/web/src/lib/hooks/useAgentGithubIssues.ts`
  - `apps/web/src/components/{WorkspaceV2,shell/SaveHistory}.tsx`

## Goal

Make GitHub issue creation recoverable from a saved SAD after preparation or creation fails, without rerunning Q&A or regenerating the SAD. A prepared issue set becomes durable; the user can relaunch it from saved-SAD history, re-enter a GitHub PAT, approve a fresh GATE 3 action, and retry safely without duplicating issues already created by an earlier partial attempt.

## Problem

The current GitHub issue workflow is tied to volatile state:

- preparation starts only from the live preview and its in-memory `preview_id`;
- approval state is in-memory and keyed by a per-load `analysis_session_id`;
- frontend approval, issue, event, and PAT state is React-only;
- `preview_id` values come from a resetting in-memory counter and are not durable identities;
- the MCP creator posts issues sequentially with no duplicate guard.

An immediate retry works while the same approval remains in memory, because failed writes do not consume the approval. A refresh, backend restart, project switch, or closed flow loses enough state that the user must repeat Q&A and SAD generation. A partial GitHub write can also create duplicates on a later retry.

## Locked Decisions

1. A durable issue set is keyed by `(grant_id, project_id, save_id)`. `preview_id` is metadata only.
2. Prepare, relaunch, and approve are authenticated. The backend resolves the save through the caller's active Drive grant and active project.
3. The issue set is persisted after successful task extraction and before approval is returned.
4. Relaunch reads the persisted issue set and mints a fresh in-memory GATE 3 approval without rerunning task extraction.
5. GitHub PATs remain memory-only and are re-entered after state loss. They are never stored in Firestore, logs, responses, or issue-set records.
6. Duplicate detection uses deterministic markers embedded in issue bodies, not titles.
7. GitHub reads cover open and closed issues, follow pagination, and exclude pull requests.
8. Creation reports created issues, skipped issues, and totals. An all-skipped retry is successful.
9. Project deletion removes issue sets before deleting the project document.
10. Saved-SAD history shows the relaunch action only when a persisted issue set exists.
11. The issue set's repository is locked at first preparation. Relinking a project does not retarget existing sets.
12. A never-prepared saved SAD whose in-memory preview is gone returns `GITHUB_ISSUE_SET_NOT_FOUND` with guidance to regenerate and save a new draft.
13. A concurrent two-client race is accepted in v1. Sequential retries are protected; distributed locking is not added.

## Non-Goals

- Persisting GitHub PATs or OAuth credentials.
- Persisting GATE 3 approvals.
- Restoring arbitrary live preview state after backend restart.
- First-time task extraction from an old saved SAD when its preview was never prepared and is no longer in memory.
- Editing, closing, deleting, or synchronizing existing GitHub issues.
- Retargeting an existing issue set after the project GitHub repo changes.
- Distributed locking or exactly-once writes across simultaneous clients.
- Per-issue workflow states in Firestore. GitHub remains the source of truth for whether a marked issue exists.
- Changing Q&A, SAD generation, Drive save, or wiki behavior.

## Durable Identity

`save_id` is the user-visible durable launch identity, but save counters are scoped to a project. Therefore a GitHub issue marker must include the project identity as well as the save and issue position.

Marker format:

```text
<!-- sadify-github-issue:{project_id}:{save_id}:{issue_index} -->
```

`issue_index` is zero-based and fixed by the persisted issue ordering. The marker is appended to the prepared issue body before the set is stored. It is not shown as separate user content by GitHub.

An existing issue set is immutable. If a user wants the same SAD content sent to a different GitHub repo, they must regenerate/save a new SAD to obtain a new `save_id`, then prepare that new save. Relaunch always uses the original locked `repo` stored in the issue set.

## Data Model

### Schemas

Add the following Pydantic models to `schemas.py`:

```python
class GithubIssueDraft(ApiModel):
    marker: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=256)
    body: str = Field(min_length=1, max_length=65536)
    labels: list[str] = Field(default_factory=list, max_length=10)


class GithubIssueSet(ApiModel):
    grant_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    save_id: str = Field(min_length=1)
    preview_id: str = Field(min_length=1)
    owner_uid: str = Field(min_length=1)
    repo: str = Field(min_length=3)
    status: Literal["prepared"] = "prepared"
    issues: list[GithubIssueDraft] = Field(min_length=1, max_length=20)
    created_at: datetime
    updated_at: datetime
```

The record contains no token and no approval ID.

### Repository

Create `services/api/src/sadify_api/services/github_issue_sets.py` with:

- `GithubIssueSetRepositoryProtocol`
- `GithubIssueSetRepository` (in-memory)
- `FirestoreGithubIssueSetRepository`

Required methods:

```python
def create_if_absent(self, issue_set: GithubIssueSet) -> GithubIssueSet: raise NotImplementedError
def get(self, grant_id: str, project_id: str, save_id: str) -> GithubIssueSet | None: raise NotImplementedError
def list_for_project(self, grant_id: str, project_id: str) -> list[GithubIssueSet]: raise NotImplementedError
def delete_for_project(self, grant_id: str, project_id: str) -> int: raise NotImplementedError
```

`create_if_absent` never overwrites an existing record. Its returned value is authoritative, so concurrent preparations use whichever repo/issues were stored first.

Firestore collection: `github_issue_sets`.

Document ID:

```python
safe_doc_id(grant_id, project_id, save_id)
```

The Firestore create-if-absent operation runs in a transaction. `delete_for_project` is idempotent and returns `0` when no records exist.

## Backend API Contracts

### Prepare

`POST /agent/github/issues/prepare` remains the first-preparation endpoint but changes to authenticated saved-SAD input.

Request:

```json
{
  "analysis_session_id": "session-id",
  "save_id": "SV-000001",
  "repo": "owner/repository",
  "model": "gemini-2.5-flash"
}
```

The bearer ID token is required.

Processing order:

1. Verify Firebase authorization.
2. Resolve the caller's active Drive repo and active project.
3. Load `SadSaveRecord` using `(grant_id, project_id, save_id)` and verify `owner_uid` matches the caller.
4. If a set already exists, treat it as immutable and return a fresh approval for that stored set; do not re-extract or retarget it.
5. Load the in-memory preview using the save record's `preview_id`.
6. If the preview is absent and no set exists, return `404 GITHUB_ISSUE_SET_NOT_FOUND` with: `This saved SAD was never prepared for GitHub issues and its draft is no longer available. Regenerate and save a new draft.`
7. Extract source-grounded tasks.
8. Create deterministic markers and append each marker to its issue body.
9. Persist the issue set with the validated target repo.
10. Mint an in-memory approval whose action includes `grant_id`, `project_id`, `save_id`, locked `repo`, and issues.
11. Return `awaiting_approval`.

Persistence must complete before the approval response is returned.

### Relaunch

Add authenticated `POST /agent/github/issues/relaunch`.

Request:

```json
{
  "analysis_session_id": "new-session-id",
  "save_id": "SV-000001"
}
```

Processing order:

1. Verify Firebase authorization.
2. Resolve the active grant/project and owned save.
3. Load the issue set by `(grant_id, project_id, save_id)`.
4. Return `404 GITHUB_ISSUE_SET_NOT_FOUND` if absent.
5. Mint a fresh in-memory approval from the stored repo/issues.
6. Return `awaiting_approval` using the existing agent response envelope.

Relaunch performs no model call and accepts no repo override.

### Approve

`POST /agent/github/issues/approve` remains authenticated. The approval action's issue-set identity is resolved again through the caller's active grant/project. Approval fails before MCP execution when:

- the approval does not exist;
- the caller no longer owns the save;
- the active grant/project differs from the approval scope;
- the durable issue set is missing;
- the approval repo or issues differ from the stored set;
- the PAT is missing.

`approve_github_issues` must use the verified user instead of discarding it. A failed MCP write leaves the approval available for immediate retry. A successful or all-skipped MCP write consumes it.

## GitHub MCP Duplicate Guard

`services/mcp/github_server.py` adds GitHub `GET` support to its client protocol.

Before any POST:

1. Fetch `GET /repos/{repo}/issues?state=all&per_page=100&page=N`.
2. Continue until a page contains fewer than 100 records.
3. Ignore records containing the `pull_request` field.
4. Read each issue body and collect SADify markers.
5. For each requested issue in persisted order:
   - if its marker exists, append it to `skipped_issues` and do not POST;
   - otherwise POST it and append the GitHub response to `created_issues`.

The request issue body already contains its marker. Titles are never used for deduplication.

Success response, including all-skipped:

```json
{
  "status": "created",
  "repo": "owner/repository",
  "created_issues": [],
  "skipped_issues": [
    {"number": 12, "url": "https://github.com/owner/repository/issues/12", "title": "Create booking validation", "marker": "<!-- sadify-github-issue:PR-1:SV-1:0 -->"}
  ],
  "totals": {"requested": 1, "created": 0, "skipped": 1}
}
```

On a mid-batch error, return `status="error"` plus the created/skipped lists and totals accumulated during that attempt. The approval remains usable. A sequential retry re-reads GitHub and skips issues created by the partial attempt.

Concurrent approvals can still both read a missing marker before either creates it. This race is accepted for v1 and must be documented in the user-facing test record; no distributed lock is added.

If a user manually removes the hidden SADify marker from an existing issue body, that issue can no longer be recognized on retry. Marker removal is an accepted v1 limitation.

## Project History And UI

### Save summary

Add `has_github_issue_set: bool` to backend and frontend `SadSaveSummary`.

`GET /projects/{project_id}/saves` loads issue sets once for the project, builds a set of their `save_id` values, and populates the flag for every save. This avoids one Firestore read per history row.

### Resume-only action

`SaveHistory` accepts:

```typescript
onCreateGithubIssues?: (save: SadSaveSummary) => void;
```

It renders `Create GitHub issues` only when `save.has_github_issue_set` is true. Never-prepared saves do not show the history action. First preparation remains in the saved live preview pane.

The callback is wired through `Sidebar` to `WorkspaceV2`. The workspace:

1. records the selected history save;
2. uses the issue set's locked repo returned by relaunch, not the project's current linked repo;
3. opens the existing GitHub token modal when no in-memory PAT is available;
4. calls relaunch first to obtain the stored locked repo and fresh approval;
5. opens `ConnectGithubModal` in locked-repo/token-only mode when a PAT must be entered; this mode cannot edit or relink the project repo;
6. presents the existing GATE 3 approval timeline after token entry, or immediately when a PAT remains in memory;
7. displays created/skipped totals on completion.

Closing the modal or refreshing may discard the PAT and approval. The history action remains available because the issue set is durable.

## Project Delete Cascade

Extend `DELETE /projects/{project_id}` persistence order:

1. Drive Trash (live mode only).
2. Saved SAD records.
3. Session snapshot.
4. GitHub issue sets.
5. Project record last.

Every repository delete is idempotent. A failure before project deletion returns `502 PROJECT_DELETE_FAILED`; retrying completes the remaining deletes. Existing GitHub issues are not deleted.

## Error Handling

| Code | HTTP | Meaning |
|---|---:|---|
| `GITHUB_ISSUE_SET_NOT_FOUND` | 404 | No durable set exists and preparation cannot be resumed. |
| `GITHUB_ISSUE_SET_SCOPE_INVALID` | 403 | The save/set does not belong to the caller's active grant/project. |
| `GITHUB_ISSUE_SET_MISMATCH` | 409 | Approval scope/repo/issues do not match the durable set. |
| `GITHUB_APPROVAL_INVALID` | 409 | Approval is missing, expired by restart, or consumed. Relaunch can mint another. |
| `GITHUB_TOKEN_MISSING` | 503 | A PAT was not supplied for the write. |
| `GITHUB_API_ERROR` | 502 | GitHub read/create failed; partial created/skipped details are returned when available. |

Backend errors must not include PAT values. Frontend errors remain visible in the GitHub timeline/modal and must not force the user back through Q&A.

## Components And Files

Backend:

- `schemas.py` - issue-set and request/response contracts; history flag.
- `services/github_issue_sets.py` - in-memory and Firestore repositories.
- `services/github_issue_flow.py` - saved-SAD preparation, relaunch, ownership checks, approval execution, result mapping.
- `routes/agent.py` - authenticated prepare/relaunch/approve endpoints.
- `routes/projects.py` - history availability and delete cascade.
- `main.py` - persistence-mode repository selection and DI.
- `services/mcp/github_server.py` - marker-based GitHub deduplication.

Frontend:

- `lib/api.ts` - saved-SAD prepare/relaunch contracts and created/skipped totals.
- `lib/hooks/useAgentGithubIssues.ts` - selected-save relaunch and recoverable state handling.
- `components/shell/SaveHistory.tsx` - resume-only action.
- `components/shell/Sidebar.tsx` - callback pass-through.
- `components/WorkspaceV2.tsx` - modal/relaunch orchestration.
- `components/agent/ConnectGithubModal.tsx` - locked-repo/token-only relaunch mode.
- `components/agent/AgentTimeline.tsx` - created/skipped completion summary.

## Testing

### Repository tests

Test both in-memory and Firestore variants for:

- create-if-absent persistence;
- immutable first-write/repo lock;
- scoped get/list;
- idempotent `delete_for_project`.

### Backend flow and route tests

- prepare requires authentication;
- prepare rejects a save outside the active grant/project;
- successful prepare persists before approval is returned;
- repeated prepare reuses the stored set without model extraction;
- missing preview and missing set return `GITHUB_ISSUE_SET_NOT_FOUND`;
- relaunch performs no model call and returns a fresh approval;
- approve rejects cross-user, cross-project, missing-set, and mismatched-set actions;
- failed creation preserves approval;
- success/all-skipped consumes approval;
- project history sets `has_github_issue_set` correctly;
- project deletion removes issue sets and remains retry-safe.

### MCP tests

- scans open and closed issues through multiple pages;
- excludes pull requests;
- skips matching body markers regardless of title;
- does not skip matching titles without markers;
- creates only missing markers;
- all-skipped returns success;
- partial failure reports accumulated created/skipped results;
- token never appears in errors or payloads.

### Frontend static and build tests

- prepare sends bearer auth and `save_id`;
- relaunch client/hook exist;
- history action appears only behind `has_github_issue_set`;
- callback is wired through Sidebar to WorkspaceV2;
- completion UI displays created and skipped totals;
- `npx tsc --noEmit` and `npm run build` pass.

### Manual smoke

1. Save a SAD and prepare GitHub issues.
2. Cause or simulate a failed write after preparation.
3. Refresh the app.
4. Open the saved SAD history action.
5. Re-enter PAT, approve, and create.
6. Retry again and verify every previously created marker is skipped with no duplicate issue.
7. Confirm a never-prepared save has no history action.
8. Confirm relinking the project does not retarget an existing set.

## Documentation

- Add `TC-036-github-issue-relaunch.md` with expected behavior, real output, evidence, and pass/fail decision.
- Update `docs/superpowers/testing/test_case_index.md`.
- Add decision-log entries for durable issue sets, immutable repo lock, marker deduplication, and the accepted concurrent race.
- Update `docs/superpowers/development/02_agent_behavior_contract.md` for recoverable GATE 3 behavior.
- Update `docs/superpowers/development/03_data_model_and_output_schema.md` with `github_issue_sets`.
- Update `context.md` with the durable issue-set and relaunch data flow.
- Bundle deployment with the parked session/data-management release. Deployment remains blocked until explicit user approval.

## Acceptance Criteria

- A prepared saved SAD can relaunch issue creation after frontend/backend volatile state is lost.
- Relaunch does not rerun Q&A, SAD generation, or developer-task extraction.
- Every write is authenticated and scoped to the caller's active grant/project/save.
- PATs and approvals remain non-durable.
- Sequential retries do not duplicate issues whose SADify markers remain in their issue bodies.
- All-skipped is reported as successful.
- Saved history exposes only genuinely resumable issue sets.
- Project deletion removes issue-set records but never deletes GitHub issues.
- In-memory and Firestore modes pass the same repository contract tests.
- Full Python suite, TypeScript check, and production build remain green.
