# TC-036 GitHub Issue Relaunch And Deduplication

Date: 2026-06-19  
Status: Pending live smoke  
Implementation branch: `codex/mvp-monorepo-scaffold`

## Purpose

Verify that a prepared GitHub issue set survives backend restart, can be relaunched from saved SAD history with a fresh GATE 3 approval, and does not create duplicate GitHub issues on sequential retries.

## Expected Result

1. Preparing GitHub issues is authenticated and scoped to an owned saved SAD.
2. The immutable prepared set is stored by `(grant_id, project_id, save_id)` and retains its original repository.
3. Relaunch performs no model/task-extraction call and creates a fresh in-memory approval.
4. Invalid PAT or MCP failure preserves the approval for retry.
5. Sequential retries read body markers from GitHub and skip existing issues.
6. Completion reports requested, created, and skipped totals, including all-skipped success.
7. Saved history exposes the action only for saves with a prepared issue set.
8. Project deletion removes local/Firestore issue-set records but never deletes remote GitHub issues.

## Automated Result

Passed on 2026-06-19:

```text
Python: 652 passed, 4 skipped, 4 warnings in 37.48s
TypeScript: npx tsc --noEmit exited 0
Frontend: npm run build compiled successfully
```

The first sandboxed full-suite run reached `650 passed, 4 skipped` and failed only because two export tests could not create their local temp directory. The exact suite passed when rerun with normal workspace permissions.

## Evidence

- Repository and Firestore contract: `tests/api/test_github_issue_sets.py`
- Authenticated prepare/relaunch/approve ownership: `tests/api/test_agent_github_issues.py`
- MCP body-marker pagination and partial-result behavior: `tests/mcp/test_github_server.py`
- History availability and delete ordering: `tests/api/test_projects.py`, `tests/api/test_project_delete.py`
- Frontend client and resume-only UI contract: `tests/test_github_issue_relaunch_ui.py`, `tests/test_tc034_github_issues_ui.py`
- Implementation commits: `074f17b`, `886bffe`, `7900680`, `65ef0a8`, `bf14135`, `1d3fee2`

## Manual Memory-Mode Recovery Smoke

Status: Not run. A throwaway GitHub repository and valid/invalid PAT inputs are required.

Required evidence:

- screenshot of visible invalid-PAT error;
- successful retry using the same approval;
- first-run created/skipped totals;
- second-run all-skipped totals;
- history showing no action for a never-prepared save.

## Firestore And Live GitHub Recovery Smoke

Status: Not run. Requires a throwaway Firestore-backed SADify project, backend restart access, and a throwaway GitHub repository.

Required evidence:

- prepared set survives backend restart;
- history relaunch mints a fresh approval;
- second approval creates no duplicates;
- project deletion removes `github_issue_sets` while remote issues remain;
- relinking the project does not change the prepared set's locked repository.

## Deviations

- No deployment was performed.
- No live GitHub or Firestore claim is made without the required throwaway credentials and screenshots.
- Automated tests use fakes for GitHub/Firestore integration boundaries; they do not replace the manual recovery smoke.

## Accepted Limitation

Marker deduplication is sequentially idempotent, not globally exactly-once. Two concurrent clients can both read GitHub before either creates an issue and then create duplicates. The v1 design accepts this read-before-write race; marker lookup and result reporting make normal retries safe.

## Decision

**Pending live smoke.** Implementation and automated regression pass. TC-036 must not be marked Passed, and deployment must not begin, until both manual smoke sections have real evidence or a human explicitly revises the release gate.
