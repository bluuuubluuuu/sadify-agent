# TC-034 P5 GitHub Issues via MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one real Track-1 MCP external action: after the SADify Analyst Agent finalizes and the user approves, it creates traceable GitHub Issues from the generated SAD through a FastMCP stdio server.

**Architecture:** Keep the existing ADK finalize agent and approval store as the control plane. Add a narrow `extract_dev_tasks` tool that derives source-grounded developer tasks from the approved SAD preview, then expose GitHub issue creation through a separate FastMCP stdio server wired into ADK via `McpToolset`. Extend the deterministic `/agent/approve` executor so GitHub writes use the same single-use approval-token gate as Drive/wiki writes.

**Tech Stack:** Python 3.13, FastAPI, Google ADK `Agent`/`Runner`/`FunctionTool`/`McpToolset`, FastMCP over stdio, Pydantic schemas, pytest, Next.js/React static UI tests, GitHub REST API behind the MCP server only.

---

## Fixed Rails

- Worktree: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`
- Branch: `codex/mvp-monorepo-scaffold`
- Deadline: June 12, 2026 08:00 MYT.
- Do not change Q&A carry-forward, questionnaire logic, readiness logic, or SAD preview manual flow.
- Do not weaken GATE 3. GitHub issue creation is a write and must require a matching single-use approval token.
- Do not call GitHub's REST API directly from the agent or route. GitHub writes must go through a FastMCP server connected by ADK `McpToolset`.
- Do not hard-code or commit GitHub PATs. Use env locally; use Secret Manager or env at deploy time.
- Do not deploy without explicit user approval.
- Stop after every task for user review. Commit each code task only after user review/approval.
- Run the full backend suite after every task; run frontend `npx tsc --noEmit` and `npm run build` after frontend changes.

## User Input Gate

Before Task 2 live/local smoke can run, request from the user:

- GitHub test repository, for example `owner/repo`.
- GitHub token:
  - classic PAT with `repo` scope, or
  - fine-grained PAT with Issues: read/write for the selected repo.

Local env names to use in implementation:

```powershell
$env:SADIFY_GITHUB_REPO="owner/repo"
$env:SADIFY_GITHUB_TOKEN="ghp_..."
```

Deploy env/secret design to confirm before deploy:

- `SADIFY_GITHUB_REPO`
- `SADIFY_GITHUB_TOKEN_SECRET_NAME` or Secret Manager-backed equivalent

## File Structure

### New Files

- `services/api/src/sadify_api/services/live_drive.py`
  Shared live Drive/Secret resolution helper used by the agent and SAD route.

- `services/api/src/sadify_api/services/dev_tasks.py`
  Structured developer-task extraction and deterministic source-reference validation.

- `services/api/src/sadify_api/agent/mcp_github.py`
  FastMCP stdio server exposing `create_github_issues`.

- `services/api/src/sadify_api/agent/github_mcp.py`
  ADK-side MCP client/toolset factory and thin caller wrapper used by deterministic approval execution.

- `tests/api/test_live_drive_services.py`
  Behavior-preserving resolver tests.

- `tests/api/test_dev_tasks.py`
  Source-grounded task extraction tests.

- `tests/api/test_github_mcp_server.py`
  MCP server tests with mocked GitHub API.

- `tests/api/test_agent_github_approval.py`
  Approval gate and deterministic execution tests for GitHub issue writes.

### Modified Files

- `services/api/pyproject.toml`
  Add `fastmcp` dependency during Task 2 only.

- `Dockerfile`
  Add `fastmcp` to backend deployment dependency install list during Task 2 only.

- `services/api/src/sadify_api/config.py`
  Add optional GitHub/MCP config fields.

- `services/api/src/sadify_api/schemas.py`
  Add `DevTask`, `DevTaskExtractionResponse`, and optional result payload fields only if useful for typed responses.

- `services/api/src/sadify_api/services/gemini_structured.py`
  Add Gemini-backed structured extraction model, mirroring `GeminiSadReviewModel` style.

- `services/api/src/sadify_api/agent/tools.py`
  Add `extract_dev_tasks` FunctionTool and `create_github_issues` write wrapper.

- `services/api/src/sadify_api/agent/finalize.py`
  Add GitHub action ordering and deterministic approved execution.

- `services/api/src/sadify_api/agent/instruction.py`
  Add one narrow instruction that dev tasks must be traceable and GitHub writes require approval.

- `services/api/src/sadify_api/routes/sad.py`
  Use shared live Drive resolver, preserving current HTTP error mapping.

- `services/api/src/sadify_api/routes/agent.py`
  Pass GitHub/MCP dependencies/config into `AgentDeps`.

- `apps/web/src/components/agent/AgentTimeline.tsx`
  Render GitHub issue proposed action and completed issue links.

- `apps/web/src/components/agent/agent.module.css`
  Minimal styling for GitHub issue list/action row.

- `tests/test_tc034_agent_timeline_ui.py`
  Static UI tests for GitHub action labels and issue links.

---

## Task 0: Share Live Drive/Secret Resolver

**Purpose:** Remove Q7 duplication before MCP work. Behavior-preserving only.

**Files:**
- Create: `services/api/src/sadify_api/services/live_drive.py`
- Modify: `services/api/src/sadify_api/agent/tools.py`
- Modify: `services/api/src/sadify_api/routes/sad.py`
- Test: `tests/api/test_live_drive_services.py`

- [ ] **Step 0.1: Write failing resolver tests**

Add tests covering injected dependencies, lazy construction, and disabled live mode:

```python
def test_resolve_live_drive_services_returns_injected_pair():
    drive_client = object()
    secret_store = object()
    resolved = resolve_live_drive_services(
        config=ApiConfig(environment="test", drive_live_enabled=True),
        drive_client=drive_client,
        secret_store=secret_store,
    )
    assert resolved == (drive_client, secret_store)


def test_resolve_live_drive_services_rejects_disabled_live_mode():
    with pytest.raises(LiveDriveServicesDisabledError):
        resolve_live_drive_services(
            config=ApiConfig(environment="test", drive_live_enabled=False),
            drive_client=None,
            secret_store=None,
        )
```

- [ ] **Step 0.2: Run targeted test to verify failure**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/api/test_live_drive_services.py -q
```

Expected: fails because `sadify_api.services.live_drive` does not exist.

- [ ] **Step 0.3: Implement shared helper**

Create:

```python
class LiveDriveServicesDisabledError(Exception):
    pass


def resolve_live_drive_services(
    *,
    config: ApiConfig,
    drive_client: DriveClient | None,
    secret_store: SecretStore | None,
) -> tuple[DriveClient, SecretStore]:
    if drive_client is not None and secret_store is not None:
        return drive_client, secret_store
    if not config.drive_live_enabled:
        raise LiveDriveServicesDisabledError("Live Drive services are disabled.")
    resolved_secret_store = secret_store or get_secret_store(
        project_id=config.google_cloud_project,
        oauth_client_secret_name=config.google_oauth_client_secret_name,
    )
    resolved_drive_client = drive_client or DriveClient(
        client_id=config.google_oauth_client_id,
        client_secret=resolved_secret_store.get_oauth_client_secret(),
    )
    return resolved_drive_client, resolved_secret_store
```

- [ ] **Step 0.4: Replace duplicate helpers**

Use this helper in:

- `agent/tools.py::_resolve_live_wiki_services`
- `routes/sad.py::_resolve_live_services`

Preserve existing outward errors:

- agent wiki path still raises `WikiFlowError(503, "WIKI_LIVE_MODE_DISABLED", "...")`
- route save path still raises `SAD_SAVE_LIVE_MODE_DISABLED`
- route wiki path still raises `WIKI_LIVE_MODE_DISABLED`

- [ ] **Step 0.5: Verify**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/api/test_live_drive_services.py tests/api/test_agent_tools.py tests/api/test_sad_save.py tests/api/test_wiki_update.py -q
..\..\.venv\Scripts\python.exe -m pytest -q
```

Expected: full suite remains green, count grows only by new tests.

- [ ] **Step 0.6: Stop for user review**

Report changed files and suite count. Commit only after user approval:

```powershell
git add services/api/src/sadify_api/services/live_drive.py services/api/src/sadify_api/agent/tools.py services/api/src/sadify_api/routes/sad.py tests/api/test_live_drive_services.py
git commit -m "refactor(agent): share live Drive/Secret resolver"
```

---

## Task 1: Source-Grounded `extract_dev_tasks`

**Purpose:** Convert an approved SAD preview into developer tasks, with every task traceable to SAD/source refs.

**Files:**
- Create: `services/api/src/sadify_api/services/dev_tasks.py`
- Modify: `services/api/src/sadify_api/schemas.py`
- Modify: `services/api/src/sadify_api/services/gemini_structured.py`
- Modify: `services/api/src/sadify_api/agent/tools.py`
- Modify: `services/api/src/sadify_api/agent/instruction.py`
- Test: `tests/api/test_dev_tasks.py`
- Test: `tests/api/test_agent_tools.py`

- [ ] **Step 1.1: Add failing schema/validation tests**

Test the hard invariant:

```python
def test_validate_dev_tasks_rejects_task_without_source_refs():
    preview = SadPreviewResponse(
        title="Pet grooming SAD",
        temporary_notice="Draft",
        it_readiness=_ready_summary(),
        sections=[
            SadPreviewSection(
                title="Appointment workflow",
                body="Reception staff schedule appointments.",
                source_references=["SRC-1"],
            )
        ],
        assumptions=[],
        open_questions=[],
        source_references=["SRC-1"],
        change_tracking=_change_tracking(),
    )
    response = DevTaskExtractionResponse(
        tasks=[
            DevTask(
                priority="high",
                title="Build appointment scheduling",
                description="Create appointment scheduling workflow.",
                source_references=[],
            )
        ]
    )

    with pytest.raises(DevTaskGroundingError):
        validate_dev_tasks(response.tasks, preview)
```

Also add:

```python
def test_validate_dev_tasks_keeps_tasks_with_known_source_refs():
    tasks = validate_dev_tasks(response.tasks, preview)
    assert tasks[0].source_references == ["SRC-1"]
```

- [ ] **Step 1.2: Run tests to verify failure**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/api/test_dev_tasks.py -q
```

Expected: fails because `DevTask` and `validate_dev_tasks` do not exist.

- [ ] **Step 1.3: Add schemas**

In `schemas.py`:

```python
class DevTask(ApiModel):
    priority: Literal["high", "medium", "low"]
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    source_references: list[str] = Field(min_length=1)


class DevTaskExtractionResponse(ApiModel):
    tasks: list[DevTask] = Field(default_factory=list)
```

- [ ] **Step 1.4: Add deterministic validation**

In `services/dev_tasks.py`:

```python
class DevTaskGroundingError(Exception):
    pass


def validate_dev_tasks(
    tasks: list[DevTask],
    preview: SadPreviewResponse,
) -> list[DevTask]:
    allowed = set(preview.source_references)
    for section in preview.sections:
        allowed.update(section.source_references)
    grounded: list[DevTask] = []
    for task in tasks:
        refs = [ref for ref in task.source_references if ref in allowed]
        if not refs:
            raise DevTaskGroundingError(
                f"Developer task has no valid source references: {task.title}"
            )
        grounded.append(task.model_copy(update={"source_references": refs}))
    return grounded
```

- [ ] **Step 1.5: Add Gemini extraction model**

Mirror the `GeminiSadReviewModel` pattern in `gemini_structured.py`:

```python
class DevTaskExtractionModel(Protocol):
    def extract_dev_tasks(
        self,
        context: str,
        *,
        model: str | None = None,
    ) -> DevTaskExtractionResponse:
        ...
```

Add `GeminiDevTaskExtractionModel` using structured JSON response schema `DevTaskExtractionResponse`.

Prompt requirements, string-tested:

```text
Create developer implementation tasks from the SAD only.
Each task must include at least one source_references value copied from the SAD section or preview source references.
Do not invent tasks that are not supported by the SAD.
If a useful task cannot be grounded to a source reference, omit it.
```

- [ ] **Step 1.6: Add service function**

In `services/dev_tasks.py`:

```python
def extract_dev_tasks(
    *,
    preview: SadPreviewResponse,
    model: DevTaskExtractionModel,
    selected_model: str | None = None,
) -> list[DevTask]:
    response = model.extract_dev_tasks(
        _dev_task_context(preview),
        model=selected_model,
    )
    return validate_dev_tasks(response.tasks, preview)
```

- [ ] **Step 1.7: Add agent FunctionTool**

Extend `AgentDeps` with optional `dev_task_model`. Extend `AgentToolFunctions`:

```python
extract_dev_tasks: Callable[[str], ToolPayload]
```

Implementation shape:

```python
def extract_dev_tasks_tool(preview_id: str) -> ToolPayload:
    record = deps.sad_preview_repository.get_preview(preview_id)
    if record is None:
        return {"status": "error", "code": "PREVIEW_NOT_FOUND"}
    if deps.dev_task_model is None:
        return {"status": "skipped", "reason": "Developer task model unavailable."}
    tasks = extract_dev_tasks(
        preview=record.preview,
        model=deps.dev_task_model,
        selected_model=deps.selected_model,
    )
    return {"status": "ready", "preview_id": preview_id, "tasks": [t.model_dump() for t in tasks]}
```

Add as read-only FunctionTool in `build_agent_tools(deps)`.

- [ ] **Step 1.8: Verify**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/api/test_dev_tasks.py tests/api/test_agent_tools.py -q
..\..\.venv\Scripts\python.exe -m pytest -q
```

- [ ] **Step 1.9: Stop for user review**

Report changed files and suite count. Commit after approval:

```powershell
git add services/api/src/sadify_api/services/dev_tasks.py services/api/src/sadify_api/schemas.py services/api/src/sadify_api/services/gemini_structured.py services/api/src/sadify_api/agent/tools.py services/api/src/sadify_api/agent/instruction.py tests/api/test_dev_tasks.py tests/api/test_agent_tools.py
git commit -m "feat(agent): extract traceable developer tasks"
```

---

## Task 2: FastMCP GitHub Server

**Purpose:** Build the external MCP tool. No agent integration yet.

**User input required before live smoke:** GitHub test repo and PAT. Unit tests must mock GitHub and run without a token.

**Files:**
- Create: `services/api/src/sadify_api/agent/mcp_github.py`
- Modify: `services/api/pyproject.toml`
- Modify: `Dockerfile`
- Test: `tests/api/test_github_mcp_server.py`

- [ ] **Step 2.1: Add dependency tests/import check**

Add a test:

```python
def test_fastmcp_import_available():
    import fastmcp
    assert fastmcp is not None
```

- [ ] **Step 2.2: Add `fastmcp` dependency**

Add to `services/api/pyproject.toml` dependencies:

```toml
"fastmcp>=2.0,<3",
```

Add matching install line to root `Dockerfile`.

- [ ] **Step 2.3: Write server unit test with mocked GitHub API**

Test expected issue payload:

```python
def test_create_github_issues_posts_traceable_issue_payload(monkeypatch):
    posted = []

    def fake_post(url, *, headers, json, timeout):
        posted.append({"url": url, "headers": headers, "json": json})
        return FakeResponse(201, {"html_url": "https://github.com/acme/app/issues/1", "number": 1})

    monkeypatch.setattr(requests, "post", fake_post)

    result = create_github_issues(
        repo="acme/app",
        issues=[
            GitHubIssueInput(
                title="Build appointment scheduling",
                body="Description\n\nSource references: SRC-1",
                labels=["sadify", "priority-high"],
            )
        ],
        token="token",
    )

    assert result.issues[0].url.endswith("/issues/1")
    assert posted[0]["json"]["title"] == "Build appointment scheduling"
```

- [ ] **Step 2.4: Implement MCP server**

Implementation boundaries:

- `create_github_issues(repo: str, issues: list[GitHubIssueInput]) -> GitHubIssueCreateResult`
- Token source is env `SADIFY_GITHUB_TOKEN` inside the MCP server process.
- No token in logs or returned payloads.
- Return issue number/title/url for UI display.
- Raise actionable errors for missing token, invalid repo, non-201 GitHub response.

Tool description must be explicit:

```text
Create GitHub Issues from approved SADify developer tasks. This is a write tool and must only be called after SADify approval.
```

- [ ] **Step 2.5: Verify**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/api/test_github_mcp_server.py -q
..\..\.venv\Scripts\python.exe -m pytest -q
```

- [ ] **Step 2.6: Stop for user review**

Report changed files and suite count. Commit after approval:

```powershell
git add services/api/src/sadify_api/agent/mcp_github.py services/api/pyproject.toml Dockerfile tests/api/test_github_mcp_server.py
git commit -m "feat(agent): add GitHub Issues FastMCP server"
```

---

## Task 3: ADK MCP Toolset Integration

**Purpose:** Connect the ADK agent to the FastMCP server through `McpToolset`, while keeping core finalize working when GitHub is disabled.

**Files:**
- Create: `services/api/src/sadify_api/agent/github_mcp.py`
- Modify: `services/api/src/sadify_api/config.py`
- Modify: `services/api/src/sadify_api/agent/tools.py`
- Modify: `services/api/src/sadify_api/agent/finalize.py`
- Modify: `services/api/src/sadify_api/routes/agent.py`
- Test: `tests/api/test_agent_finalize.py`
- Test: `tests/api/test_agent_tools.py`

- [ ] **Step 3.1: Inspect ADK MCP API locally**

Run a read-only import probe:

```powershell
..\..\.venv\Scripts\python.exe -c "from google.adk.tools.mcp_tool.mcp_toolset import McpToolset; print(McpToolset)"
```

If the import path differs, adapt the plan to the installed ADK API before writing implementation.

- [ ] **Step 3.2: Write optionality test**

Test that GitHub disabled does not change the existing tool count/action behavior:

```python
def test_finalize_tools_work_when_github_mcp_disabled(fake_agent_deps):
    deps = replace(fake_agent_deps, github_mcp_enabled=False)
    tools = build_agent_tools(deps)
    names = {tool.name for tool in tools}
    assert "save_to_drive" in names
    assert "update_wiki" in names
```

- [ ] **Step 3.3: Write MCP toolset factory test**

Use monkeypatch/fake `McpToolset` to assert stdio command points to the in-repo server:

```python
def test_build_github_mcp_toolset_uses_stdio_server(monkeypatch):
    captured = {}
    monkeypatch.setattr(github_mcp, "McpToolset", lambda **kwargs: captured.update(kwargs) or "toolset")
    result = build_github_mcp_toolset(config=ApiConfig(environment="test", github_mcp_enabled=True))
    assert result == "toolset"
    assert "mcp_github" in str(captured)
```

- [ ] **Step 3.4: Add config fields**

In `ApiConfig`:

```python
github_mcp_enabled: bool = False
github_repo: str | None = None
github_token_secret_name: str | None = None
```

Env names:

- `SADIFY_GITHUB_MCP_ENABLED`
- `SADIFY_GITHUB_REPO`
- `SADIFY_GITHUB_TOKEN_SECRET_NAME`

- [ ] **Step 3.5: Implement MCP factory**

In `agent/github_mcp.py`:

```python
def build_github_mcp_toolset(config: ApiConfig) -> BaseTool | None:
    if not config.github_mcp_enabled:
        return None
    return McpToolset(
        connection_params=StdioServerParameters(
            command=sys.executable,
            args=["-m", "sadify_api.agent.mcp_github"],
        )
    )
```

Adapt import names to the installed ADK package from Step 3.1.

- [ ] **Step 3.6: Wire toolset into `build_finalize_agent`**

Keep existing FunctionTools first, append the MCP toolset only when enabled:

```python
tools = build_agent_tools(deps)
github_toolset = build_github_mcp_toolset(deps.config) if deps.config else None
if github_toolset is not None:
    tools.append(github_toolset)
```

- [ ] **Step 3.7: Verify**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/api/test_agent_finalize.py tests/api/test_agent_tools.py -q
..\..\.venv\Scripts\python.exe -m pytest -q
```

- [ ] **Step 3.8: Stop for user review**

Commit after approval:

```powershell
git add services/api/src/sadify_api/agent/github_mcp.py services/api/src/sadify_api/config.py services/api/src/sadify_api/agent/tools.py services/api/src/sadify_api/agent/finalize.py services/api/src/sadify_api/routes/agent.py tests/api/test_agent_finalize.py tests/api/test_agent_tools.py
git commit -m "feat(agent): wire GitHub MCP toolset into finalize agent"
```

---

## Task 4: Approval-Gated GitHub Issue Execution

**Purpose:** Extend GATE 3 to GitHub: no issues created without approval, and approved execution calls the MCP path.

**Files:**
- Modify: `services/api/src/sadify_api/agent/approval.py` if action matching needs payload keys.
- Modify: `services/api/src/sadify_api/agent/tools.py`
- Modify: `services/api/src/sadify_api/agent/finalize.py`
- Modify: `services/api/src/sadify_api/agent/instruction.py`
- Test: `tests/api/test_agent_github_approval.py`
- Test: `tests/api/test_agent_finalize.py`

- [ ] **Step 4.1: Write refusal test**

```python
def test_create_github_issues_refuses_without_approval(fake_agent_deps):
    calls = []
    deps = replace(
        fake_agent_deps,
        write_approval=None,
        github_issue_runner=lambda **kwargs: calls.append(kwargs),
    )
    tools = build_agent_tool_functions(deps)

    with pytest.raises(WriteApprovalRequiredError) as exc:
        tools.create_github_issues("SP-000001")

    assert calls == []
    assert exc.value.proposed_actions[0]["id"] == "create_github_issues"
```

- [ ] **Step 4.2: Write approved execution test**

```python
def test_run_approved_actions_executes_github_issues_with_matching_token(fake_agent_deps):
    store = ApprovalStore()
    approval_id = store.create(
        "AS-1",
        [
            {
                "id": "create_github_issues",
                "preview_id": "SP-000001",
                "repo": "acme/app",
                "issues": [{"title": "Build scheduler", "body": "Source references: SRC-1"}],
            }
        ],
    )

    result = run_approved_actions(
        replace(fake_agent_deps, github_issue_runner=fake_runner),
        analysis_session_id="AS-1",
        approval_store=store,
        approval_id=approval_id,
    )

    assert result["status"] == "completed"
    assert store.get("AS-1", approval_id) is None
```

- [ ] **Step 4.3: Add GitHub action payload**

Action shape:

```python
{
    "id": "create_github_issues",
    "label": "Create GitHub issues",
    "preview_id": preview_id,
    "repo": repo,
    "issues": [
        {
            "title": task.title,
            "body": task.description + "\n\nSource references: " + ", ".join(task.source_references),
            "labels": ["sadify", f"priority-{task.priority}"],
            "source_references": task.source_references,
        }
    ],
}
```

- [ ] **Step 4.4: Add tool function**

Extend `AgentToolFunctions`:

```python
create_github_issues: Callable[[str], ToolPayload]
```

Tool behavior:

1. Load preview by `preview_id`.
2. Extract/validate dev tasks.
3. Build proposed action.
4. Require write approval for `create_github_issues` with matching `preview_id`.
5. On approval, call the MCP runner.
6. Return created links:

```python
{
    "status": "created",
    "repo": "owner/repo",
    "issues": [{"number": 1, "title": "...", "url": "https://github.com/..."}],
}
```

- [ ] **Step 4.5: Extend deterministic executor**

In `finalize.py`:

- `_ordered_actions` order:

```python
{"save_to_drive": 0, "update_wiki": 1, "overwrite_wiki": 1, "create_github_issues": 2}
```

- `run_approved_actions` branch:

```python
elif action_id == "create_github_issues":
    preview_id = str(action.get("preview_id") or "")
    response = tool_functions.create_github_issues(preview_id)
```

- [ ] **Step 4.6: Ensure proposed actions include GitHub only when configured**

If `github_mcp_enabled` is false or repo/token config missing, do not propose GitHub issues. Existing Drive/wiki proposal remains unchanged.

- [ ] **Step 4.7: Verify**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/api/test_agent_github_approval.py tests/api/test_agent_finalize.py tests/api/test_agent_tools.py -q
..\..\.venv\Scripts\python.exe -m pytest -q
```

- [ ] **Step 4.8: Stop for user review**

Commit after approval:

```powershell
git add services/api/src/sadify_api/agent/approval.py services/api/src/sadify_api/agent/tools.py services/api/src/sadify_api/agent/finalize.py services/api/src/sadify_api/agent/instruction.py tests/api/test_agent_github_approval.py tests/api/test_agent_finalize.py
git commit -m "feat(agent): approval-gate GitHub issue creation"
```

---

## Task 5: Frontend GitHub Action and Result UI

**Purpose:** Make the GitHub action visible in the approval card and show issue links after completion.

**Files:**
- Modify: `apps/web/src/components/agent/AgentTimeline.tsx`
- Modify: `apps/web/src/components/agent/agent.module.css`
- Test: `tests/test_tc034_agent_timeline_ui.py`

- [ ] **Step 5.1: Write static UI tests**

Add assertions:

```python
def test_agent_timeline_renders_github_issue_action():
    source = AGENT_TIMELINE.read_text(encoding="utf-8")
    assert "Create GitHub issues" in source
    assert "Developer tasks -> GitHub Issues" in source
    assert "issue.url" in source or "created issue" in source.lower()
```

- [ ] **Step 5.2: Add action metadata**

In `AgentTimeline.tsx` action copy:

```ts
create_github_issues: {
  icon: GitBranch,
  title: "Create GitHub issues",
  what: "Developer tasks -> GitHub Issues in the target repository",
}
```

Use the repo from `action.repo` when present.

- [ ] **Step 5.3: Render completed issue links**

For completed result actions:

```tsx
{action.tool === "create_github_issues" && action.issues?.map((issue) => (
  <a href={issue.url} target="_blank" rel="noreferrer">
    #{issue.number} {issue.title}
  </a>
))}
```

- [ ] **Step 5.4: Verify frontend**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/test_tc034_agent_timeline_ui.py -q
cd apps/web
npx tsc --noEmit
npm run build
```

- [ ] **Step 5.5: Verify full backend unchanged**

```powershell
..\..\.venv\Scripts\python.exe -m pytest -q
```

- [ ] **Step 5.6: Stop for user review**

Commit after approval:

```powershell
git add apps/web/src/components/agent/AgentTimeline.tsx apps/web/src/components/agent/agent.module.css tests/test_tc034_agent_timeline_ui.py
git commit -m "feat(web): show GitHub issue approval results"
```

---

## Task 6: Local Live Smoke Against User Test Repo

**Purpose:** Prove the MCP path creates real GitHub Issues after approval.

**Files:** No code unless smoke finds a bug.

- [ ] **Step 6.1: Request user secrets**

Ask for:

- GitHub repo `owner/repo`
- PAT with Issues write

Do not print the PAT after receiving it.

- [ ] **Step 6.2: Start backend with env**

```powershell
cd D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api
$env:SADIFY_GITHUB_MCP_ENABLED="true"
$env:SADIFY_GITHUB_REPO="owner/repo"
$env:SADIFY_GITHUB_TOKEN="..."
$env:SADIFY_DRIVE_MODE="live"
$env:SADIFY_DRIVE_LIVE_ENABLED="true"
..\..\..\..\.venv\Scripts\python.exe -m uvicorn sadify_api.main:app --port 8000 --reload
```

- [ ] **Step 6.3: Start frontend if needed**

```powershell
cd D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web
npm run dev
```

- [ ] **Step 6.4: Browser smoke**

Use Gemini Flash or Pro, not Flash-Lite:

1. Sign in.
2. Connect Drive repo.
3. Create/select test project.
4. Enter requirement and complete Q&A.
5. Click `Finalize with agent`.
6. Confirm approval card includes:
   - Save SAD to Google Drive
   - Update project wiki
   - Create GitHub issues
7. Click `Approve & save`.
8. Confirm:
   - `/agent/approve` returns 200
   - Drive Doc saved
   - wiki updated or conflict re-approval works
   - GitHub Issues created in the test repo
   - issue links render in the timeline

- [ ] **Step 6.5: Stop for user review**

Report:

- backend suite count
- tsc/build result
- number of issues created
- issue URLs
- any Cloud/local logs relevant to MCP failures

No deploy yet.

---

## Task 7: Ship and Documentation Closure

**Purpose:** Deploy and close submission docs only after user approval.

**Files:**
- Modify local ignored docs:
  - `docs/superpowers/testing/test_cases/TC-034-sadify-analyst-agent.md`
  - `docs/superpowers/testing/test_cases/TC-035-github-issues-mcp.md` or equivalent new test case
  - `docs/superpowers/testing/test_case_index.md`
  - `docs/superpowers/development/07_decision_log.md`
  - `docs/superpowers/CURRENT.md`

- [ ] **Step 7.1: Request explicit deploy approval**

Deploy is billable/outward. Stop until user says yes.

- [ ] **Step 7.2: Deploy using TC-027 mechanics**

Backend first, then frontend, preserving Cloud Run env and CORS.

- [ ] **Step 7.3: Prod smoke**

On production, using Flash or Pro:

- Q&A -> Finalize with agent -> approval -> Drive Doc/wiki/GitHub issues.
- Not-ready path asks one clarification.
- Approval gate writes nothing before approval.
- Cloud Logging has no relevant 5xx/agent errors.

- [ ] **Step 7.4: Docs closure**

Record:

- New decision `D-101`: GitHub Issues via MCP is the Track-1 external action.
- Test evidence for MCP issue creation.
- Demo status.
- Architecture writeup status.

Do not commit docs unless user explicitly asks; docs are local/gitignored.

---

## Self-Review

- Spec coverage:
  - Real MCP path: Tasks 2 and 3.
  - Approval-gated GitHub writes: Task 4.
  - Source-grounded dev tasks: Task 1.
  - UI display: Task 5.
  - Live proof: Task 6.
  - Deploy/docs closure: Task 7.
  - Shared Drive resolver cleanup: Task 0.

- Risk controls:
  - GitHub disabled path is tested so existing finalize remains stable.
  - All GitHub network calls live inside the MCP server.
  - No PAT is stored in code.
  - No issue is created before approval.
  - If GitHub auth blocks the schedule, the approved fallback is Drive/Docs via MCP, but this plan intentionally tries GitHub first because it has stronger Track-1 demo value.

- Review stops:
  - Stop after each task.
  - Commit only after user review.
  - Deploy only after explicit user approval.
