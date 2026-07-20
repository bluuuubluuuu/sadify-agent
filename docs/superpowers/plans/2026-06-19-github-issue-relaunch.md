# Recoverable GitHub Issue Creation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist prepared GitHub issue sets per saved SAD so users can relaunch approval after state loss and retry sequential partial writes without creating duplicate marked issues.

**Architecture:** A new in-memory/Firestore repository stores immutable prepared issue sets keyed by grant, project, and save. Authenticated prepare and relaunch routes mint ephemeral GATE 3 approvals from that durable set, while the GitHub MCP server deduplicates against paginated open/closed issue bodies using deterministic markers. Project history exposes only resumable saves, and project deletion cascades through issue sets before deleting the project.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, Firestore, Google ADK/MCP, httpx, pytest, Next.js 16, React 19, TypeScript.

Date: 2026-06-19

## Traceability Sources

- `docs/superpowers/specs/2026-06-19-github-issue-relaunch-design.md`
- `docs/superpowers/plans/2026-06-05-tc034-p5-github-issues-mcp.md`
- `docs/superpowers/specs/2026-06-18-session-and-data-management-design.md`
- `services/api/src/sadify_api/services/{github_issue_flow,sad_preview,sad_save}.py`
- `services/api/src/sadify_api/{agent/approval,routes/agent,routes/projects,main}.py`
- `services/mcp/github_server.py`
- `apps/web/src/lib/hooks/useAgentGithubIssues.ts`
- `apps/web/src/components/{WorkspaceV2,shell/SaveHistory}.tsx`

---

## Execution Preconditions

- Work only in `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold` on `codex/mvp-monorepo-scaffold`.
- Commit the already-approved Task 6 account-menu work before starting this plan.
- Keep `apps/web/next-env.d.ts` and `.next/` out of every commit.
- Use strict TDD: add the named failing tests, run them red, implement only that task, then run targeted and specified regression tests.
- Stop after every task for human review. Do not begin the next task until the previous task is approved and committed.
- Do not deploy until the user explicitly approves deployment in Task 8.

## Locked Interfaces

```python
class GithubIssueSetRepositoryProtocol(Protocol):
    def create_if_absent(self, issue_set: GithubIssueSet) -> GithubIssueSet: raise NotImplementedError
    def get(self, grant_id: str, project_id: str, save_id: str) -> GithubIssueSet | None: raise NotImplementedError
    def list_for_project(self, grant_id: str, project_id: str) -> list[GithubIssueSet]: raise NotImplementedError
    def delete_for_project(self, grant_id: str, project_id: str) -> int: raise NotImplementedError
```

```text
POST /agent/github/issues/prepare   authenticated; save_id + repo + model
POST /agent/github/issues/relaunch  authenticated; save_id; no model/repo override
POST /agent/github/issues/approve   authenticated; verifies durable set ownership and equality
```

```typescript
type GithubIssueCreationTotals = {
  requested: number;
  created: number;
  skipped: number;
};
```

---

### Task 1: GitHub Issue Set Schema And Repository

**Files:**
- Modify: `services/api/src/sadify_api/schemas.py`
- Create: `services/api/src/sadify_api/services/github_issue_sets.py`
- Create: `tests/api/test_github_issue_sets.py`

- [ ] **Step 1.1: Write failing repository contract tests**

Create parameterized tests over fresh in-memory and fake-Firestore repositories:

```python
@pytest.fixture(params=["memory", "firestore"])
def repository(request):
    if request.param == "memory":
        return GithubIssueSetRepository()
    return FirestoreGithubIssueSetRepository(FakeFirestoreClient())


def test_create_if_absent_locks_first_repo(repository):
    first = _issue_set(repo="acme/first")
    second = first.model_copy(update={"repo": "acme/second"})

    assert repository.create_if_absent(first).repo == "acme/first"
    assert repository.create_if_absent(second).repo == "acme/first"
    assert repository.get("DRG-1", "PR-1", "SV-1").repo == "acme/first"


def test_list_and_delete_are_project_scoped_and_idempotent(repository):
    repository.create_if_absent(_issue_set(project_id="PR-1", save_id="SV-1"))
    repository.create_if_absent(_issue_set(project_id="PR-1", save_id="SV-2"))
    repository.create_if_absent(_issue_set(project_id="PR-2", save_id="SV-1"))

    assert [item.save_id for item in repository.list_for_project("DRG-1", "PR-1")] == [
        "SV-1",
        "SV-2",
    ]
    assert repository.delete_for_project("DRG-1", "PR-1") == 2
    assert repository.delete_for_project("DRG-1", "PR-1") == 0
    assert repository.get("DRG-1", "PR-2", "SV-1") is not None
```

Use `FakeFirestoreClient` from `tests/api/test_firestore_repositories.py`. Each parameter case must receive a new repository instance.

- [ ] **Step 1.2: Run tests and verify red**

Run from the worktree root:

```powershell
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests/api/test_github_issue_sets.py -q
```

Expected: collection/import failure because `GithubIssueSet` and `github_issue_sets.py` do not exist.

- [ ] **Step 1.3: Add exact schemas**

Add after the existing GitHub agent request types in `schemas.py`:

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

- [ ] **Step 1.4: Implement both repositories**

Use key `(grant_id, project_id, save_id)` in memory and Firestore document ID `safe_doc_id(grant_id, project_id, save_id)` in collection `github_issue_sets`.

Firestore create-if-absent must use `run_in_transaction`:

```python
def create_if_absent(self, issue_set: GithubIssueSet) -> GithubIssueSet:
    ref = self._ref(issue_set.grant_id, issue_set.project_id, issue_set.save_id)

    def _create(transaction) -> GithubIssueSet:
        data = snapshot_data(ref.get(transaction=transaction))
        if data is not None:
            return GithubIssueSet.model_validate(data)
        transaction.set(ref, issue_set.model_dump(mode="json"))
        return issue_set

    return run_in_transaction(self._client, _create)
```

`list_for_project` filters by both `grant_id` and `project_id`, then sorts by `(created_at, save_id)`. `delete_for_project` deletes every matching document and returns the count.

- [ ] **Step 1.5: Verify targeted and repository regressions**

```powershell
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests/api/test_github_issue_sets.py tests/api/test_firestore_repositories.py -q
```

Expected: PASS.

- [ ] **Step 1.6: Stop for review; commit only after approval**

```powershell
git add services/api/src/sadify_api/schemas.py services/api/src/sadify_api/services/github_issue_sets.py tests/api/test_github_issue_sets.py
git commit -m "feat(api): persist prepared GitHub issue sets"
```

---

### Task 2: Marker-Based GitHub MCP Deduplication

**Files:**
- Modify: `services/mcp/github_server.py`
- Modify: `tests/mcp/test_github_server.py`

- [ ] **Step 2.1: Add failing MCP tests**

Extend the fake client with recorded `get` and `post` calls. Add tests covering pagination, PR exclusion, marker matching, title non-matching, all-skipped success, and partial failure:

```python
def test_create_skips_existing_marker_across_closed_issue_pages():
    marker = "<!-- sadify-github-issue:PR-1:SV-1:0 -->"
    client = FakeGitHubClient(
        get_responses=[
            FakeGitHubResponse(200, [_existing_issue(index) for index in range(100)]),
            FakeGitHubResponse(
                200,
                [
                    {"number": 101, "html_url": "https://github.test/101", "title": "Renamed", "body": marker},
                    {"number": 102, "title": "PR", "body": marker, "pull_request": {}},
                ],
            ),
        ],
        post_responses=[],
    )

    result = asyncio.run(
        create_github_issues_payload(
            _batch(marker=marker),
            configured_repo="acme/app",
            token_provider=lambda: "token",
            client_factory=lambda: client,
            approval_required=False,
        )
    )

    assert result["status"] == "created"
    assert result["totals"] == {"requested": 1, "created": 0, "skipped": 1}
    assert result["skipped_issues"][0]["number"] == 101
    assert client.post_calls == []


def test_partial_failure_returns_progress_for_safe_retry():
    client = FakeGitHubClient(
        get_responses=[FakeGitHubResponse(200, [])],
        post_responses=[
            FakeGitHubResponse(201, {"number": 1, "html_url": "https://github.test/1"}),
            FakeGitHubResponse(502, {"message": "upstream failed"}),
        ],
    )

    result = asyncio.run(_create_two_issues(client))

    assert result["status"] == "error"
    assert result["totals"] == {"requested": 2, "created": 1, "skipped": 0}
    assert [item["number"] for item in result["created_issues"]] == [1]
```

Add a separate test proving an existing issue with the same title but no marker is not skipped.

- [ ] **Step 2.2: Run tests and verify red**

```powershell
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests/mcp/test_github_server.py -q
```

Expected: FAIL because `GitHubIssue` has no marker, the client protocol has no `get`, and the response lacks created/skipped totals.

- [ ] **Step 2.3: Extend input and client contracts**

Add required `marker` to `GitHubIssue` and `get` to `AsyncGitHubClient`:

```python
class GitHubIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    marker: str = Field(min_length=1, max_length=256)
    title: str = Field(min_length=1, max_length=256)
    body: str = Field(min_length=1, max_length=65536)
    labels: list[str] = Field(default_factory=list, max_length=10)


class AsyncGitHubClient(Protocol):
    async def get(self, url: str, *, headers: dict[str, str], params: dict[str, Any]) -> Any:
        raise NotImplementedError

    async def post(self, url: str, *, headers: dict[str, str], json: dict[str, Any]) -> Any:
        raise NotImplementedError
```

The existing approval proposal must include `marker` for every issue.

- [ ] **Step 2.4: Implement paginated marker lookup**

Add a helper that requests `state=all`, `per_page=100`, increments `page`, rejects non-200 responses through `_github_api_error`, excludes records with `pull_request`, and maps each discovered marker to number/URL/title. Stop only when the returned page length is below 100.

Marker matching is exact substring matching against the issue body using each requested `issue.marker`. Never compare titles.

- [ ] **Step 2.5: Return the new result contract**

Every success returns:

```python
{
    "status": "created",
    "repo": allowed_repo,
    "created_issues": created,
    "skipped_issues": skipped,
    "totals": {
        "requested": len(batch.issues),
        "created": len(created),
        "skipped": len(skipped),
    },
}
```

On GET or POST failure, merge the same lists/totals into the error payload before returning. Do not include request headers or token values.

- [ ] **Step 2.6: Verify MCP tests**

```powershell
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests/mcp/test_github_server.py -q
```

Expected: PASS.

- [ ] **Step 2.7: Stop for review; commit only after approval**

```powershell
git add services/mcp/github_server.py tests/mcp/test_github_server.py
git commit -m "feat(mcp): skip previously created GitHub issues"
```

---

### Task 3: Authenticated Prepare And Durable Relaunch

**Files:**
- Modify: `services/api/src/sadify_api/schemas.py`
- Modify: `services/api/src/sadify_api/services/github_issue_flow.py`
- Modify: `services/api/src/sadify_api/routes/agent.py`
- Modify: `services/api/src/sadify_api/main.py`
- Modify: `tests/api/test_agent_github_issues.py`

- [ ] **Step 3.1: Write failing service and route tests**

Add tests for authentication, save ownership, persist-before-approval, immutable reuse, missing preview, and model-free relaunch:

```python
def test_prepare_route_requires_auth(client):
    response = client.post(
        "/agent/github/issues/prepare",
        json={"analysis_session_id": "S-1", "save_id": "SV-1", "repo": "acme/app"},
    )
    assert response.status_code == 401


def test_prepare_persists_marked_set_before_returning_approval(prepared_flow):
    result = prepared_flow.prepare(save_id="SV-1", repo="acme/app")
    stored = prepared_flow.issue_sets.get("DRG-1", "PR-1", "SV-1")

    assert result["status"] == "awaiting_approval"
    assert stored is not None
    assert stored.repo == "acme/app"
    assert stored.issues[0].marker == "<!-- sadify-github-issue:PR-1:SV-1:0 -->"
    assert stored.issues[0].body.endswith(stored.issues[0].marker)


def test_relaunch_uses_stored_set_without_model_call(prepared_flow):
    prepared_flow.seed_issue_set()
    result = prepared_flow.relaunch(save_id="SV-1", dev_task_model=_model_that_raises())

    assert result["status"] == "awaiting_approval"
    assert result["result"]["repo"] == "acme/original"
    assert result["result"]["save_id"] == "SV-1"
```

Also test:

- save not found in active project -> `404`;
- `SadSaveRecord.owner_uid != user.uid` -> `403 GITHUB_ISSUE_SET_SCOPE_INVALID`;
- no stored set and no preview -> `404 GITHUB_ISSUE_SET_NOT_FOUND` with regenerate wording;
- repeated prepare with a different repo returns approval for the first stored repo and does not invoke extraction.

- [ ] **Step 3.2: Run tests and verify red**

```powershell
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests/api/test_agent_github_issues.py -q
```

Expected: FAIL because prepare still accepts `preview_id`, lacks auth, and no relaunch route exists.

- [ ] **Step 3.3: Replace request schemas**

```python
class AgentGitHubIssuesPrepareRequest(ApiModel):
    analysis_session_id: str = Field(min_length=1)
    save_id: str = Field(min_length=1)
    repo: str | None = None
    model: str | None = None


class AgentGitHubIssuesRelaunchRequest(ApiModel):
    analysis_session_id: str = Field(min_length=1)
    save_id: str = Field(min_length=1)
```

Keep the approve request PAT comment and memory-only behavior.

- [ ] **Step 3.4: Add marker and approval helpers**

In `github_issue_flow.py`:

```python
def github_issue_marker(project_id: str, save_id: str, issue_index: int) -> str:
    return f"<!-- sadify-github-issue:{project_id}:{save_id}:{issue_index} -->"


def _approval_action(issue_set: GithubIssueSet) -> dict[str, Any]:
    return {
        "id": CREATE_GITHUB_ISSUES,
        "label": "Create GitHub issues",
        "grant_id": issue_set.grant_id,
        "project_id": issue_set.project_id,
        "save_id": issue_set.save_id,
        "repo": issue_set.repo,
        "issue_count": len(issue_set.issues),
        "issues": [issue.model_dump() for issue in issue_set.issues],
    }
```

Create a single helper that mints approval and returns the common `awaiting_approval` envelope from a stored set. Both prepare and relaunch must use it.

- [ ] **Step 3.5: Implement authenticated saved-SAD prepare**

Change `prepare_github_issues` inputs to include verified `user`, `drive_repo_repository`, `sad_save_repository`, and `issue_set_repository`. Resolve active repo/project, then call:

```python
save = sad_save_repository.get_save(
    save_id,
    repo_grant_id=drive_repo.grant_id,
    project_id=drive_repo.active_project_id,
)
```

Reject missing or wrong-owner saves before reading previews. If a set exists, return a fresh approval for it. Otherwise extract tasks from `save.preview_id`, create marked `GithubIssueDraft` values, call `create_if_absent`, and mint approval from the returned stored record.

- [ ] **Step 3.6: Implement relaunch service and route**

`relaunch_github_issues` resolves the same owned save and loads the issue set. It performs no model resolution and no extraction. Add:

```python
@router.post("/github/issues/relaunch", response_model=AgentFinalizeResponse)
def relaunch_github_issue_creation(
    request: AgentGitHubIssuesRelaunchRequest,
    authorization: str | None = Header(default=None),
) -> AgentFinalizeResponse:
    user = verify_authorization_header(authorization, token_verifier)
    return AgentFinalizeResponse.model_validate(
        relaunch_github_issues(
            analysis_session_id=request.analysis_session_id,
            save_id=request.save_id,
            user=user,
            drive_repo_repository=drive_repo_repository,
            sad_save_repository=sad_save_repository,
            issue_set_repository=github_issue_set_repository,
            approval_store=approval_store,
        )
    )
```

Prepare must receive and verify the same authorization header.

- [ ] **Step 3.7: Wire persistence-mode DI**

Add optional `github_issue_set_repository` to `create_app`, choose `FirestoreGithubIssueSetRepository(firestore_client)` when Firestore is active, otherwise `GithubIssueSetRepository()`, and pass it to the agent router. Keep the resolved instance in `create_app`; Task 5 adds the project-router parameter when history and delete behavior begin consuming it.

- [ ] **Step 3.8: Verify targeted backend tests**

```powershell
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests/api/test_agent_github_issues.py tests/api/test_github_issue_sets.py -q
```

Expected: PASS.

- [ ] **Step 3.9: Stop for review; commit only after approval**

```powershell
git add services/api/src/sadify_api/schemas.py services/api/src/sadify_api/services/github_issue_flow.py services/api/src/sadify_api/routes/agent.py services/api/src/sadify_api/main.py tests/api/test_agent_github_issues.py
git commit -m "feat(api): relaunch prepared GitHub issue approvals"
```

---

### Task 4: Approval Ownership And Created/Skipped Results

**Files:**
- Modify: `services/api/src/sadify_api/services/github_issue_flow.py`
- Modify: `services/api/src/sadify_api/routes/agent.py`
- Modify: `tests/api/test_agent_github_issues.py`

- [ ] **Step 4.1: Write failing approval integrity tests**

```python
def test_approve_rejects_different_owner_without_calling_mcp(approval_flow):
    approval_flow.seed_issue_set(owner_uid="owner-1")
    approval_id = approval_flow.mint_approval(user_uid="owner-1")

    with pytest.raises(GitHubIssueFlowError) as exc_info:
        approval_flow.approve(approval_id=approval_id, user_uid="owner-2")

    assert exc_info.value.code == "GITHUB_ISSUE_SET_SCOPE_INVALID"
    assert approval_flow.mcp_calls == []


def test_approve_rejects_mutated_approval_payload(approval_flow):
    approval_flow.seed_issue_set(repo="acme/original")
    approval_id = approval_flow.mint_mutated_approval(repo="acme/other")

    with pytest.raises(GitHubIssueFlowError) as exc_info:
        approval_flow.approve(approval_id=approval_id, user_uid="owner-1")

    assert exc_info.value.code == "GITHUB_ISSUE_SET_MISMATCH"


def test_all_skipped_is_success_and_consumes_approval(approval_flow):
    approval_id = approval_flow.mint_approval(user_uid="owner-1")
    approval_flow.mcp_response = {
        "status": "created",
        "repo": "acme/app",
        "created_issues": [],
        "skipped_issues": [{"number": 7, "marker": "marker"}],
        "totals": {"requested": 1, "created": 0, "skipped": 1},
    }

    result = approval_flow.approve(approval_id=approval_id, user_uid="owner-1")

    assert result["status"] == "completed"
    assert result["result"]["totals"]["skipped"] == 1
    assert approval_flow.approval_store.get("S-1", approval_id) is None
```

Retain and update the existing test proving an MCP error preserves approval. Assert its result contains partial created/skipped/totals.

- [ ] **Step 4.2: Run tests and verify red**

```powershell
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests/api/test_agent_github_issues.py -q
```

Expected: FAIL because approve discards `user` and maps only `response["issues"]`.

- [ ] **Step 4.3: Enforce durable-set equality before MCP**

Resolve the caller's active grant/project and owned save. Load the durable set named by the approval action. Compare locked repo and normalized issue dictionaries exactly. Any difference raises `409 GITHUB_ISSUE_SET_MISMATCH`. Missing set raises `404 GITHUB_ISSUE_SET_NOT_FOUND`. Scope/owner mismatch raises `403 GITHUB_ISSUE_SET_SCOPE_INVALID`.

- [ ] **Step 4.4: Map created/skipped/totals without losing retry state**

On `status != "created"`, preserve approval and return `awaiting_approval` with:

```python
"result": {
    "approval_id": approval_id,
    "repo": target_repo,
    "save_id": issue_set.save_id,
    "proposed_actions": approval.actions,
    "created_issues": response.get("created_issues", []),
    "skipped_issues": response.get("skipped_issues", []),
    "totals": response.get("totals"),
    "error": {"code": response.get("code"), "message": response.get("message")},
}
```

On success, consume approval and return the same created/skipped/totals fields with `status="completed"`. Event summary must say both counts, including `Created 0 and skipped 3 existing GitHub issue(s).`

- [ ] **Step 4.5: Verify targeted tests**

```powershell
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests/api/test_agent_github_issues.py tests/mcp/test_github_server.py -q
```

Expected: PASS.

- [ ] **Step 4.6: Stop for review; commit only after approval**

```powershell
git add services/api/src/sadify_api/services/github_issue_flow.py services/api/src/sadify_api/routes/agent.py tests/api/test_agent_github_issues.py
git commit -m "fix(api): bind GitHub approvals to owned issue sets"
```

---

### Task 5: Project History Availability And Delete Cascade

**Files:**
- Modify: `services/api/src/sadify_api/schemas.py`
- Modify: `services/api/src/sadify_api/routes/projects.py`
- Modify: `services/api/src/sadify_api/main.py` only if Task 3 did not already pass the repository to the project router
- Modify: `tests/api/test_projects.py`
- Modify: `tests/api/test_project_delete.py`

- [ ] **Step 5.1: Write failing history and delete tests**

```python
def test_project_history_marks_only_saves_with_issue_sets(project_client):
    project_client.seed_save("SV-1")
    project_client.seed_save("SV-2")
    project_client.seed_issue_set("SV-2")

    response = project_client.client.get(
        f"/projects/{project_client.project_id}/saves",
        headers=project_client.headers,
    )

    flags = {item["save_id"]: item["has_github_issue_set"] for item in response.json()["saves"]}
    assert flags == {"SV-1": False, "SV-2": True}


def test_delete_project_removes_issue_sets_before_project(project_delete_client):
    project_delete_client.seed_issue_set()
    response = project_delete_client.delete_project()

    assert response.status_code == 200
    assert project_delete_client.issue_sets.list_for_project(
        project_delete_client.grant_id,
        project_delete_client.project_id,
    ) == []
    assert project_delete_client.calls.index("delete_issue_sets") < project_delete_client.calls.index("delete_project")
```

Add a failure-once issue-set repository test proving `PROJECT_DELETE_FAILED`, retained project document, and successful retry.

- [ ] **Step 5.2: Run tests and verify red**

```powershell
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests/api/test_projects.py tests/api/test_project_delete.py -q
```

Expected: FAIL because summaries lack the flag and delete does not call the new repository.

- [ ] **Step 5.3: Add history flag and one-query population**

Add `has_github_issue_set: bool = False` to `SadSaveSummary`. In `list_project_saves`, call `list_for_project` once, build:

```python
prepared_save_ids = {
    issue_set.save_id
    for issue_set in github_issue_set_repository.list_for_project(repo.grant_id, project.project_id)
}
```

Set `has_github_issue_set=record.save_id in prepared_save_ids` for each summary.

- [ ] **Step 5.4: Insert issue-set deletion before project deletion**

The persistence section must be exactly ordered:

```python
sad_save_repository.delete_for_project(repo.grant_id, project_id)
session_snapshot_repository.delete(repo.grant_id, project_id)
github_issue_set_repository.delete_for_project(repo.grant_id, project_id)
project_repository.delete_project(repo.grant_id, project_id)
```

Keep Drive Trash first and project deletion last. Do not delete remote GitHub issues.

- [ ] **Step 5.5: Verify project regressions**

```powershell
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests/api/test_projects.py tests/api/test_project_delete.py tests/api/test_project_session_routes.py -q
```

Expected: PASS.

- [ ] **Step 5.6: Stop for review; commit only after approval**

```powershell
git add services/api/src/sadify_api/schemas.py services/api/src/sadify_api/routes/projects.py services/api/src/sadify_api/main.py tests/api/test_projects.py tests/api/test_project_delete.py
git commit -m "feat(api): expose resumable GitHub issue sets in history"
```

---

### Task 6: Frontend Authenticated Prepare And Relaunch Hook

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/hooks/useAgentGithubIssues.ts`
- Modify: `tests/test_tc034_github_issues_ui.py`
- Create: `tests/test_github_issue_relaunch_ui.py`

- [ ] **Step 6.1: Write failing static-source tests**

```python
def test_prepare_is_saved_sad_scoped_and_authenticated():
    api = _read("lib/api.ts")
    hook = _read("lib/hooks/useAgentGithubIssues.ts")
    assert "saveId: string" in api
    assert "previewId: string" not in _prepare_function(api)
    assert 'Authorization: `Bearer ${idToken}`' in _prepare_function(api)
    assert "getFirebaseAuth().currentUser" in hook


def test_api_and_hook_expose_relaunch():
    api = _read("lib/api.ts")
    hook = _read("lib/hooks/useAgentGithubIssues.ts")
    assert "relaunchAgentGithubIssues" in api
    assert "/agent/github/issues/relaunch" in api
    assert "async function relaunch" in hook


def test_result_contract_has_created_skipped_totals():
    api = _read("lib/api.ts")
    hook = _read("lib/hooks/useAgentGithubIssues.ts")
    for token in ("created_issues", "skipped_issues", "totals"):
        assert token in api
        assert token in hook
```

- [ ] **Step 6.2: Run tests and verify red**

```powershell
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests/test_github_issue_relaunch_ui.py tests/test_tc034_github_issues_ui.py -q
```

Expected: FAIL because prepare still sends `preview_id`, has no bearer token, and relaunch does not exist.

- [ ] **Step 6.3: Update API types and calls**

Add typed result fields:

```typescript
export type GithubIssueCreationTotals = {
  requested: number;
  created: number;
  skipped: number;
};

export type AgentGithubIssueResult = {
  approval_id?: string;
  save_id?: string;
  preview_id?: string;
  repo?: string;
  proposed_actions?: AgentProposedAction[];
  created_issues?: Array<Record<string, unknown>>;
  skipped_issues?: Array<Record<string, unknown>>;
  totals?: GithubIssueCreationTotals;
  error?: { code?: string; message?: string };
};
```

Change prepare to accept `idToken`, `saveId`, repo, and model, sending `save_id` with bearer auth. Add `relaunchAgentGithubIssues({analysisSessionId, saveId}, idToken)` using the neighboring `BackendApiError` pattern.

- [ ] **Step 6.4: Update the hook**

Export the API result type instead of duplicating it locally. `prepare(saveId, repo)` and `relaunch(saveId)` both require a current Firebase user, fetch an ID token, update events/status/result, and surface auth failures consistently.

`relaunch` returns the parsed result so `WorkspaceV2` can read the locked repo immediately:

```typescript
async function relaunch(saveId: string): Promise<AgentGithubIssueResult | null> {
  const user = getFirebaseAuth().currentUser;
  if (!user) {
    setError("Sign in with Google before creating GitHub issues.");
    return null;
  }
  const idToken = await user.getIdToken();
  const response = await relaunchAgentGithubIssues(
    { analysisSessionId, saveId },
    idToken,
  );
  const nextResult = (response.result ?? null) as AgentGithubIssueResult | null;
  setEvents(response.events);
  setStatus(response.status);
  setResult(nextResult);
  setIsOpen(true);
  return nextResult;
}
```

- [ ] **Step 6.5: Verify static tests and TypeScript**

```powershell
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests/test_github_issue_relaunch_ui.py tests/test_tc034_github_issues_ui.py -q
Set-Location apps/web
npx tsc --noEmit
```

Expected: PASS and clean TypeScript.

- [ ] **Step 6.6: Stop for review; commit only after approval**

```powershell
git add apps/web/src/lib/api.ts apps/web/src/lib/hooks/useAgentGithubIssues.ts tests/test_tc034_github_issues_ui.py tests/test_github_issue_relaunch_ui.py
git commit -m "feat(web): add recoverable GitHub issue relaunch client"
```

---

### Task 7: Resume-Only History UI And Completion Summary

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/components/shell/SaveHistory.tsx`
- Modify: `apps/web/src/components/shell/Sidebar.tsx`
- Modify: `apps/web/src/components/WorkspaceV2.tsx`
- Modify: `apps/web/src/components/agent/ConnectGithubModal.tsx`
- Modify: `apps/web/src/components/agent/AgentTimeline.tsx`
- Modify: the existing CSS module files used by those components only where required
- Modify: `tests/test_github_issue_relaunch_ui.py`

- [ ] **Step 7.1: Write failing UI wiring tests**

```python
def test_history_action_is_resume_only():
    api = _read("lib/api.ts")
    history = _read("components/shell/SaveHistory.tsx")
    assert "has_github_issue_set: boolean" in api
    assert "save.has_github_issue_set" in history
    assert "Create GitHub issues" in history
    assert "onCreateGithubIssues" in history


def test_resume_wires_history_to_relaunch_and_locked_modal():
    sidebar = _read("components/shell/Sidebar.tsx")
    workspace = _read("components/WorkspaceV2.tsx")
    modal = _read("components/agent/ConnectGithubModal.tsx")
    assert "onCreateGithubIssues" in sidebar
    assert "githubIssues.relaunch" in workspace
    assert "lockedRepo" in workspace
    assert "repoLocked" in modal
    assert "disabled={repoLocked}" in modal


def test_timeline_displays_created_and_skipped_totals():
    timeline = _read("components/agent/AgentTimeline.tsx")
    assert "totals.created" in timeline
    assert "totals.skipped" in timeline
```

- [ ] **Step 7.2: Run tests and verify red**

```powershell
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests/test_github_issue_relaunch_ui.py -q
```

Expected: FAIL because history has no callback/flag rendering and the modal has no locked mode.

- [ ] **Step 7.3: Add resume-only history action**

Add `has_github_issue_set: boolean` to frontend `SadSaveSummary`. `SaveHistory` accepts `onCreateGithubIssues?: (save: SadSaveSummary) => void` and renders an icon/text button only inside:

```tsx
{save.has_github_issue_set && onCreateGithubIssues ? (
  <button
    type="button"
    aria-label={`Create GitHub issues from ${save.save_id}`}
    onClick={() => onCreateGithubIssues(save)}
  >
    <Icon name="openExternal" size={13} />
    Create GitHub issues
  </button>
) : null}
```

Do not render a disabled action for never-prepared saves.

- [ ] **Step 7.4: Add locked-repo modal mode**

`ConnectGithubModal` gains `repoLocked?: boolean`. When true, the repo input displays the relaunch result's repo, is disabled, and explanatory copy says the prepared set is locked to that repository. Submission still returns token and repo, but `WorkspaceV2` must not call `setProjectGithubRepo` in relaunch mode.

- [ ] **Step 7.5: Wire Sidebar and WorkspaceV2**

Pass `onCreateGithubIssues` through Sidebar into SaveHistory. In WorkspaceV2:

```typescript
async function handleResumeGithubIssues(save: SadSaveSummary) {
  const result = await githubIssues.relaunch(save.save_id);
  const lockedRepo = result?.repo;
  if (!lockedRepo) {
    return;
  }
  setGithubResumeRepo(lockedRepo);
  if (!githubIssues.hasToken) {
    setGithubConnectError("");
    setGithubConnectOpen(true);
  }
}
```

The modal submit handler branches on `githubResumeRepo`:

- relaunch mode: set the in-memory token, close modal, clear `githubResumeRepo`, leave project linkage unchanged;
- fresh prepare mode: retain current repo-linking behavior, then call `githubIssues.prepare(sadSave.record?.save_id ?? null, updated.github_repo)`.

Change the live preview prepare call from `sadSave.previewId` to `sadSave.record?.save_id ?? null`.

- [ ] **Step 7.6: Render completion totals**

In GitHub mode, `AgentTimeline` reads `result.totals`. Completed copy must distinguish created and skipped values, including all-skipped success. Keep the list of newly created issue links and add a plain skipped count; skipped issues need not duplicate the full issue list.

- [ ] **Step 7.7: Verify frontend tests and build**

```powershell
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests/test_github_issue_relaunch_ui.py tests/test_tc034_github_issues_ui.py tests/test_mvp_project_ui.py -q
Set-Location apps/web
npx tsc --noEmit
npm run build
```

Expected: PASS, clean TypeScript, successful production build.

- [ ] **Step 7.8: Stop for review; commit only after approval**

Stage only files changed by this task and exclude `next-env.d.ts`/`.next`:

```powershell
git add apps/web/src/lib/api.ts apps/web/src/components/shell/SaveHistory.tsx apps/web/src/components/shell/Sidebar.tsx apps/web/src/components/WorkspaceV2.tsx apps/web/src/components/agent/ConnectGithubModal.tsx apps/web/src/components/agent/AgentTimeline.tsx tests/test_github_issue_relaunch_ui.py
git commit -m "feat(web): relaunch GitHub issues from saved SAD history"
```

If CSS modules changed, add only the exact changed CSS module paths to this command after reviewing their diffs.

---

### Task 8: Full Regression, Manual Recovery Smoke, Documentation, And Deploy Hold

**Files:**
- Modify: `context.md`
- Create: `docs/superpowers/testing/test_cases/TC-036-github-issue-relaunch.md`
- Modify: `docs/superpowers/testing/test_case_index.md`
- Modify: `docs/superpowers/development/02_agent_behavior_contract.md`
- Modify: `docs/superpowers/development/03_data_model_and_output_schema.md`
- Modify: `docs/superpowers/development/07_decision_log.md`
- Modify: `docs/superpowers/CURRENT.md`

- [ ] **Step 8.1: Run the full automated regression**

From the worktree root:

```powershell
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests/ -q
Set-Location apps/web
npx tsc --noEmit
npm run build
```

Expected: all Python tests pass with only documented skips/warnings, TypeScript exits 0, and Next production build completes.

- [ ] **Step 8.2: Run local memory-mode recovery smoke**

Verify:

1. Save a SAD and prepare its issue set.
2. Submit an invalid PAT and observe a visible error without losing the approval.
3. Submit a valid PAT and create issues.
4. Close/reopen the history flow within the same process and verify existing markers are skipped.
5. Confirm created/skipped totals are accurate.
6. Confirm a never-prepared save has no history action.

Record exact outputs and screenshots in TC-036.

- [ ] **Step 8.3: Run Firestore/live GitHub recovery smoke using throwaway data**

Use a throwaway SADify project and throwaway GitHub repository. Do not use submission/demo data.

1. Prepare a set in Firestore mode.
2. Restart backend and refresh frontend.
3. Relaunch from saved history and enter PAT again.
4. Create issues, then relaunch and approve again.
5. Verify the second run reports all issues skipped and GitHub contains no duplicates.
6. Delete the throwaway SADify project and verify `github_issue_sets` records are gone while GitHub issues remain.
7. Relink a project repo and verify an existing set still displays/uses its original locked repo.

- [ ] **Step 8.4: Write documentation closure**

TC-036 must include expected result, real result, evidence, deviations, concurrent-race limitation, and pass/fail decision. Update:

- agent behavior: durable relaunch still requires fresh GATE 3 approval;
- data model: `github_issue_sets` schema and ownership key;
- architecture/data flow: durable issue-set storage, relaunch, and marker lookup;
- decision log: immutable repo lock, body-marker dedup, no title matching, accepted concurrent race;
- test index and CURRENT status.

Do not claim pass before the live smoke evidence exists.

- [ ] **Step 8.5: Run one final regression after documentation-only edits**

Documentation edits do not require rebuilding code, but rerun `git diff --check` and confirm source worktree status contains no generated files intended for commit.

- [ ] **Step 8.6: Stop for review and deployment decision**

Do not deploy automatically. Report:

- exact pytest summary;
- TypeScript/build result;
- TC-036 decision and evidence paths;
- known accepted concurrent race;
- proposed deployment order: existing `sadify-api`, then existing `sadify-web`.

Bundle this deployment with the parked session/data-management release only after explicit user approval.

---

## Self-Review

- **Spec coverage:** Task 1 covers durable storage; Task 2 covers marker dedup and partial results; Tasks 3-4 cover authenticated prepare/relaunch/approve and GATE 3 integrity; Task 5 covers history availability and delete cascade; Tasks 6-7 cover frontend relaunch; Task 8 covers evidence, docs, and deploy hold.
- **Identity consistency:** repository key is `(grant_id, project_id, save_id)`; marker is `(project_id, save_id, issue_index)` because save IDs are project-scoped; `preview_id` is metadata only.
- **Repo lock:** `create_if_absent` and every relaunch use the first stored repo. A different repo requires a new saved SAD/new `save_id`.
- **Secret safety:** no schema, repository, approval result, or log persists the PAT. Frontend keeps it in hook state only.
- **Retry safety:** failed MCP writes preserve approval; refresh/backend restart uses relaunch; sequential retries re-read GitHub markers; all-skipped is success.
- **Scope boundary:** never-prepared cold saves are not made fully resumable; the history action appears only when a set exists.
- **Delete safety:** issue sets are deleted before the project document; remote GitHub issues are never deleted.
- **Known risk:** simultaneous clients can still race between marker read and issue creation; accepted for v1 and tested/documented as a limitation rather than silently claimed as exactly-once.
