# TC-034 SADify Analyst Agent Finalize Flow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or superpowers:subagent-driven-development) to implement task-by-task. Steps use checkbox (`- [ ]`) syntax.
>
> **EXECUTION MODEL (hybrid by owner):** Each task has an **Owner**:
> - **Codex-implement** — Codex writes it via TDD, stops at the gate, CC reviews.
> - **CC-implement** — CC writes it directly (tasks where CC has the skill + confidence: UI/UX, MCP server, browser verification, docs/memory). **TOKEN EXCEPTION (⚠️CC→Codex):** a CC-implement task hands back to Codex ONLY if CC's token/context budget is running out at that point; otherwise CC does it. Marked per phase.
> - **CC-gate** — every `CC REVIEW GATE` is CC-only (review/approve/cross-check vs the 488 baseline).
>
> Whoever doesn't implement a task still reviews it. No phase begins until the prior gate passes.
>
> **Owner summary:** P0 Codex · P1 Codex · P2 Codex · P3 Codex · **P4 CC** (⚠️→Codex if low tokens) · **P5.1 Codex, P5.2 CC** (⚠️→Codex if low tokens) · P6 deploy=user-run, smoke=CC+user, docs/memory=CC.

**Goal:** Turn SADify from "backend + LLM workflow app" into one visible ADK-powered Analyst Agent that reasons over the requirement, calls existing services as tools, critiques its own SAD draft, and performs approval-gated actions (Drive/wiki save, GitHub issues via MCP) with an activity timeline.

**Architecture:** A real ADK `root_agent` + `Runner` lives inside `sadify_api` and orchestrates the existing backend through `FunctionTool` wrappers. The agent owns *judgment* (ready-to-draft? regenerate? safe to overwrite?); deterministic code owns *safety* (questionnaire/readiness engine, auth, allowed-tool gating, approval-before-writes, actual execution). Everything is additive behind a new `/agent` route; existing endpoints and the tuned Q&A engine are untouched.

**Tech Stack:** Python 3.13 / FastAPI / Pydantic v2 · google-adk 1.32 (Agent/Runner/Session/FunctionTool, McpToolset) · google-genai (Vertex Gemini) · FastMCP (GitHub MCP server) · Next.js 16 / React 19 (SSE timeline).

**Source of truth:** memory `tc034_agentic_design.md` (converged design) + `docs/superpowers/development/02_agent_behavior_contract.md` (behavior the agent MUST conform to). Plan is local/gitignored.

**GATE TO START:** TC-032 (model picker) + the current UI redesign must be deployed before Phase 2 begins. Phases 0–1 (deps + internal refactor) may proceed earlier since they change no behavior.

---

## File Structure (decomposition)

**Modify (backend):**
- `services/api/pyproject.toml` — add `google-adk`.
- `Dockerfile` — add `google-adk` to pip install.
- `services/api/src/sadify_api/routes/analysis.py` — route delegates to extracted `run_analysis_turn`.
- `services/api/src/sadify_api/routes/sad.py` — routes delegate to extracted `run_sad_preview` / `run_sad_save` / `run_wiki_update`.
- `services/api/src/sadify_api/main.py` — include `create_agent_router`.
- `services/api/src/sadify_api/schemas.py` — add `DevTask`, agent request/response/event schemas.

**Create (backend):**
- `services/api/src/sadify_api/services/analysis_flow.py` — `run_analysis_turn(...)` (P1).
- `services/api/src/sadify_api/services/sad_flow.py` — `run_sad_preview/run_sad_save/run_wiki_update(...)` + domain errors (P1).
- `services/api/src/sadify_api/services/dev_tasks.py` — `extract_dev_tasks(...)` (P5).
- `services/api/src/sadify_api/agent/__init__.py`
- `services/api/src/sadify_api/agent/instruction.py` — agent system instruction (conforms to behavior contract).
- `services/api/src/sadify_api/agent/tools.py` — `FunctionTool` wrappers over the flow services + `get_readiness` + `ask_clarification` + `review_sad`.
- `services/api/src/sadify_api/agent/finalize.py` — `build_finalize_agent(...)` + `run_finalize(...)` (ADK Runner/Session orchestration, reflect loop, approval gating).
- `services/api/src/sadify_api/agent/mcp_github.py` — FastMCP GitHub-issues server (stdio) + ADK McpToolset wiring (P5).
- `services/api/src/sadify_api/routes/agent.py` — `create_agent_router(...)` → `POST /agent/finalize`, `POST /agent/approve` (+ SSE stream P4).

**Create (frontend, P4):**
- `apps/web/src/lib/hooks/useAgentFinalize.ts` — SSE consumer.
- `apps/web/src/components/agent/AgentTimeline.tsx` + `agent.module.css` — activity timeline.
- `apps/web/src/components/WorkspaceV2.tsx` — "Finalize with agent" action (additive).

**Tests:** mirror under `tests/api/` (backend) and `tests/test_mvp_*` (frontend static). Baseline to never regress: **488 passed, 4 skipped** via `..\..\.venv\Scripts\python.exe -m pytest -q` from the worktree.

---

## Phase 0 — Dependencies & spec prereqs (no behavior change)

**Skill:** none special. **Deploy point:** none.

### Task 0.1: Add google-adk to backend deps + image

**Files:** Modify `services/api/pyproject.toml`, `Dockerfile`.

- [ ] **Step 1:** Add `"google-adk>=1.32.0,<2"` to the `dependencies` array in `services/api/pyproject.toml`.
- [ ] **Step 2:** In `Dockerfile`, add `"google-adk>=1.32.0,<2" \` to the `pip install` block and update the comment that currently says google-adk is "NOT needed on the API path".
- [ ] **Step 3:** Verify import in the venv:

Run: `..\..\.venv\Scripts\python.exe -c "import google.adk; from google.adk.agents import Agent; print('adk ok')"`
Expected: `adk ok`

- [ ] **Step 4:** Full suite unchanged.

Run: `..\..\.venv\Scripts\python.exe -m pytest -q`
Expected: `488 passed, 4 skipped`

- [ ] **Step 5:** Commit `chore(agent): add google-adk to backend deps for TC-034`.

> **CC REVIEW GATE 0:** google-adk present in both pyproject + Dockerfile; import works; suite still 488/4; no other deps disturbed. Confirm version resolves with existing google-genai (no conflict).

---

## Phase 1 — Behavior-preserving service extraction (RISKY — isolated)

**Goal:** lift route-handler orchestration into HTTP-agnostic, importable use-case functions so the agent can call them. **Zero behavior change** — the 488-test suite is the guard. Each route becomes a thin delegator that maps domain errors → HTTP.

**Skill:** `feature-dev:code-explorer` (map the seams) + `superpowers:test-driven-development`. **Deploy point:** optional silent deploy (no user change) — defer to P6.

**Principle for every extraction:** the service function raises **domain errors** (not `HTTPException`); the route catches them and maps to the *exact same* status/code/detail it returns today. Verify by keeping existing route tests green.

### Task 1.1: Extract `run_sad_preview`

**Files:** Create `services/api/src/sadify_api/services/sad_flow.py`; Modify `routes/sad.py` (the `generate_preview` handler).

Target signature (HTTP-agnostic):
```python
class SadPreviewBlockedError(Exception):
    def __init__(self, missing_basics: list[str]) -> None:
        self.missing_basics = missing_basics

class SadPreviewModelError(Exception):
    """Raised when Gemini fails non-validation (maps to 502)."""

def run_sad_preview(
    *,
    request: SadPreviewRequest,
    model: SadPreviewModel,
    repository: SadPreviewRepository,
) -> SadPreviewRecord:
    """Full preview use-case: clean → blocking-basics gate → build context →
    repair/fallback loop → save. Raises SadPreviewBlockedError (→409) or
    SadPreviewModelError (→502). Returns the saved record (incl. safe fallback)."""
```

- [ ] **Step 1:** Write a failing test `tests/api/test_sad_flow.py::test_run_sad_preview_saves_record` that calls `run_sad_preview(...)` directly with a fake model returning `VALID_PREVIEW` and asserts a saved record with the parsed preview. Add `test_run_sad_preview_blocked_raises` (missing basics → `SadPreviewBlockedError`).
- [ ] **Step 2:** Run → FAIL (module missing). `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_sad_flow.py -q`
- [ ] **Step 3:** Move the body of `generate_preview` (the clean/missing-basics/context/repair-fallback/save logic, currently `routes/sad.py:106-186`) into `run_sad_preview`, raising the domain errors instead of `HTTPException`. Keep `_call_sad_preview_model` behavior identical (selected-model passthrough).
- [ ] **Step 4:** Rewrite the route `generate_preview` to: `try: record = run_sad_preview(...)` / `except SadPreviewBlockedError as e: raise HTTPException(409, {...e.missing_basics})` / `except SadPreviewModelError: raise HTTPException(502, "Gemini SAD preview failed.")`, returning the same `SadPreviewApiResponse`.
- [ ] **Step 5:** Run new tests → PASS, then the existing preview route tests → unchanged. `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_sad_preview.py tests/api/test_sad_flow.py -q`
- [ ] **Step 6:** Commit `refactor(sad): extract run_sad_preview use-case (no behavior change)`.

### Task 1.2: Extract `run_sad_save`

**Files:** `services/api/src/sadify_api/services/sad_flow.py`; Modify `routes/sad.py` (`save_preview`).

Target: `run_sad_save(*, user, request, deps...) -> SadSaveRecord` raising domain errors mirroring the existing `_sad_save_error` codes (`SAD_SAVE_AUTH_REQUIRED`, `SAD_SAVE_REPO_REQUIRED`, `PROJECT_REQUIRED`, `SAD_SAVE_PREVIEW_NOT_FOUND`, `SAD_SAVE_TOKEN_MISSING/INVALID`, `SAD_SAVE_DRIVE_UPLOAD_FAILED`, …). The route maps each to the existing status+code.

- [ ] **Step 1:** Failing test `test_run_sad_save_*` (success + one representative error, e.g. repo-required) with fake repos/drive in local mode.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Extract `save_preview` body (`routes/sad.py:189-352`) into `run_sad_save`; raise domain errors carrying `(status, code, message)` so the route mapping is mechanical.
- [ ] **Step 4:** Route delegates + maps.
- [ ] **Step 5:** Run `tests/api/test_sad_save*.py` + new tests → green.
- [ ] **Step 6:** Commit `refactor(sad): extract run_sad_save use-case`.

### Task 1.3: Extract `run_wiki_update`

**Files:** `services/api/src/sadify_api/services/sad_flow.py`; Modify `routes/sad.py` (`preview_wiki_update` + `update_wiki`).

Target: `run_wiki_update(*, user, request, deps...) -> WikiUpdateResult` and `run_wiki_preview(...) -> WikiPreviewResult`, raising domain errors mirroring `_wiki_error` codes (incl. `WIKI_CONFLICT` with `changed_files`).

- [ ] **Step 1:** Failing test for `run_wiki_update` success + `WIKI_CONFLICT` path (changed file, no force).
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Extract both wiki handler bodies; preserve backup/snapshot ordering and conflict enforcement exactly.
- [ ] **Step 4:** Routes delegate + map.
- [ ] **Step 5:** Run `tests/api/test_*wiki*.py` + new → green.
- [ ] **Step 6:** Commit `refactor(sad): extract run_wiki_update/preview use-cases`.

### Task 1.4: Extract `run_analysis_turn`

**Files:** Create `services/api/src/sadify_api/services/analysis_flow.py`; Modify `routes/analysis.py` (`analyze_requirement`).

Target: `run_analysis_turn(*, request, model, repository) -> RequirementAnalysisRecord`. This wraps the existing module-level helpers (already importable in `analysis.py`: `_locked_target_for_request`, `_with_questionnaire_state`, `_fallback_requirement_analysis`, etc.) plus the repair loop + save. **Do not change** any of those helpers — only relocate the *handler body*. Leave the helpers where they are or move them alongside; the Q&A engine logic is frozen.

- [ ] **Step 1:** Failing test `test_run_analysis_turn_*` (gemini path saves record; fallback path saves fallback) with a fake analysis model.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Move `analyze_requirement` body (`routes/analysis.py:91-186`) into `run_analysis_turn`; the route calls it and returns `RequirementAnalysisApiResponse`. `_log_turn` stays.
- [ ] **Step 4:** Run `tests/api/test_gemini_structured.py` + analysis/questionnaire tests + new → green.
- [ ] **Step 5:** Commit `refactor(analysis): extract run_analysis_turn use-case`.

> **GUARD SEMANTICS (read first):** GATE 1 means **zero regressions in pre-existing tests** — NOT a frozen total. Each task *adds* direct-call tests, so the count grows monotonically: **488 → 490 (after 1.1) → +N (1.2) → +N (1.3) → +N (1.4)**. A run with only additions and **0 failures** is the proof. Never edit/delete a test to hit a number; if a pre-existing test fails, that's a real regression — stop and report. CC tracks the running count per task.
>
> **CC REVIEW GATE 1 (the critical gate):** For each extraction — (a) every pre-existing test still passes with **0 failures** (count grows by the task's new tests — the proof of behavior preservation); (b) diff is pure relocation + error-type swap, no logic change in the Q&A/readiness/evidence helpers; (c) route still returns identical status/code/detail for every error path (spot-check the mappings); (d) new direct-call tests exercise the service functions. CC reads each diff specifically for accidental behavior drift. Do not proceed to Phase 2 until this gate passes.

---

## Phase 2 — ADK agent scaffold + tools (no UI)

**GATE:** TC-032 + UI redesign deployed. **Skill:** `feature-dev:code-architect` + `claude-code-guide` (ADK questions). **Deploy point:** none yet.

**Agent design (conforms to `02_agent_behavior_contract.md`):** goal-and-guardrails instruction, NOT a script. The agent chooses tool order; Python only enforces safety. Tools are thin wrappers over Phase-1 flow services.

### Task 2.1: Agent instruction + tool wrappers

**Files:** Create `agent/instruction.py`, `agent/tools.py`.

`agent/instruction.py` — system instruction stating: you are SADify's analyst finalizer; clarify-first (never present low-confidence as final); judge readiness before drafting; if not ready, ask ONE clarification via the tool, don't fabricate; mark assumptions/open questions; never overwrite a changed wiki or write to Drive/GitHub without explicit approval; keep dev tasks traceable. (Mirror the MUST-NOT list from the contract.)

`agent/tools.py` — ADK `FunctionTool`s (each calls a Phase-1 service or existing engine; pure, typed, docstringed so the model knows when to use them):
```python
get_readiness(analysis_id) -> {score, confidence, gaps, label}     # from saved analysis
ask_clarification(analysis_session_id) -> {question, why, choices}  # existing engine via run_analysis_turn; LLM only phrases the framing
generate_sad(analysis_id) -> {preview_id, sections, assumptions, open_questions}  # run_sad_preview
# (write tools added in P3 with approval gating)
```

- [ ] **Step 1:** Failing test `tests/api/test_agent_tools.py` asserting each tool returns the documented shape against fake deps.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement the wrappers (sync fns; they call the flow services with injected deps via a small dataclass `AgentDeps`).
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(agent): agent instruction + read/generate tool wrappers`.

### Task 2.2: Finalize agent + Runner + route (non-streaming)

**Files:** Create `agent/finalize.py`, `routes/agent.py`; Modify `main.py`, `schemas.py`.

`agent/finalize.py`:
```python
def build_finalize_agent(deps: AgentDeps, model: str) -> Agent: ...   # ADK Agent w/ FunctionTools, resolved model
def run_finalize(deps, *, analysis_session_id, model, approval=None) -> FinalizeResult: ...
    # uses ADK Runner + InMemorySessionService (request-scoped — DECIDED: fine for
    # TC-034 demo, no Agent Engine persistence). Returns {status, events[], result}
    # status in {"asked_clarification","awaiting_approval","completed"}
    # NOTE (Codex): build a tiny Runner.run(...) proof test with fake tools first.
```
`schemas.py`: add `AgentFinalizeRequest{analysis_session_id, model?}`, `AgentEvent{type, tool, summary, reasoning?}`, `AgentFinalizeResponse{status, events[], result?}`.
`routes/agent.py`: `POST /agent/finalize` → `run_finalize(...)`, returns `AgentFinalizeResponse`. Agent runs on `resolve_gemini_model(request.model, config)`.

- [ ] **Step 1:** Failing tests `tests/api/test_agent_finalize.py` for the three branches using **fake tools** (inject a fake agent/runner or stub the model): ready→generates draft→`completed` (writes deferred to P3); not-ready→`asked_clarification`; (conflict branch deferred to P3).
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `build_finalize_agent` + `run_finalize` (ADK Runner/Session), the route, and wire `create_agent_router` into `create_app` (additive include).
- [ ] **Step 4:** Run new tests → PASS; full suite → green.
- [ ] **Step 5:** Manual local check: start backend, `POST /agent/finalize` against a real draft-ready analysis session; confirm it returns events + a generated preview. (CC narrates; user runs.)
- [ ] **Step 6:** Commit `feat(agent): finalize agent + Runner + POST /agent/finalize (non-streaming)`.

> **CC REVIEW GATE 2:** real ADK `Agent`+`Runner`+`FunctionTool` used (not a hand-rolled state machine); branch tests pass with fake tools; existing endpoints untouched; agent runs on the selected model; full suite green. CC confirms the LLM owns tool sequencing (no orchestration `if`s in the route).

---

## Phase 3 — Self-reflection + approval gating (MINIMUM DEMOABLE BAR)

**Skill:** `feature-dev:code-architect` + TDD. **Deploy point:** ✅ **DEPLOY + DEMO HERE** (user-approved; prod smoke incl. Pro).

### Task 3.1: `review_sad` self-critique tool + reflect loop

**Files:** Modify `agent/tools.py`, `agent/finalize.py`.

`review_sad(preview_id) -> {verdict, issues[]}` where `verdict ∈ {proceed, tighten, regenerate, ask}` — a **Gemini self-audit** (advisory) flagging missing sections, weak/ungrounded claims, vague FRs. DECIDED: this is an LLM self-critique producing *structured issues* — **sentence-level deterministic claim-to-source is NOT required here** (that hard, deterministic traceability invariant is reserved for dev tasks in P5.1). The agent decides what to do with the verdict; `run_finalize` enforces a **regenerate cap of 2**, after which it proceeds with the best draft + surfaces remaining issues as open questions.

- [ ] **Step 1:** Failing tests: weak draft → `regenerate` once → `proceed`; cap honored (no infinite loop); `ask` verdict → `asked_clarification`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement the tool + the capped reflect loop in `run_finalize`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(agent): review_sad self-reflection with regenerate cap`.

### Task 3.2: Approval-gated write tools

**Files:** Modify `agent/tools.py`, `agent/finalize.py`, `routes/agent.py`, `schemas.py`.

Write tools (`save_to_drive`, `update_wiki`) refuse to execute unless `run_finalize` is invoked with a valid `approval` token for that step. **Approval-token storage (DECIDED):** an in-memory store keyed by `(analysis_session_id, approval_id)` holding the pending proposed actions; cleared on use. In-memory is sufficient (approve follows within seconds) — no Firestore needed. Flow: first call returns `status="awaiting_approval"` with the proposed actions + the drafted preview + a generated `approval_id`; `POST /agent/approve {analysis_session_id, approval_id}` re-enters `run_finalize` with approval and executes the writes via `run_sad_save`/`run_wiki_update`. Wiki conflict (`WIKI_CONFLICT`) surfaces as an explicit re-approval ("overwrite changed wiki?"). Enforce the gate in CODE + TESTS (a write tool called without a matching approval token must raise), not only via the agent instruction.

- [ ] **Step 1:** Failing tests: write tool refuses without approval; `/agent/approve` executes save+wiki; conflict → re-approval required.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement approval token + `/agent/approve`; wire write tools through the Phase-1 save/wiki flows.
- [ ] **Step 4:** Run → PASS; full suite green.
- [ ] **Step 5:** Commit `feat(agent): approval-gated Drive/wiki writes + /agent/approve`.

> **CC REVIEW GATE 3 (demoable bar):** full reason→act→reflect→act loop works; **no write executes without an approval token** (CC verifies by test + code read); regenerate cap enforced; conflict re-approval works; full suite green; agent obeys the behavior contract (clarify-first, marked assumptions). **Then: deploy to prod (user approval required — billable) and run prod smoke incl. selecting Pro; check Cloud Logging.** This is the shippable Track-1 milestone.

---

## Phase 4 — SSE activity timeline + Next.js consumer (CUTTABLE)

**Owner: CC-implement** (⚠️→Codex only if CC low on tokens). **Skill:** `ui-ux-pro-max` + `frontend-design` + `document-skills:webapp-testing`. **Deploy point:** with P6.

### Task 4.1: Stream agent events (SSE)

**Files:** Modify `routes/agent.py`, `agent/finalize.py`.

Add `POST /agent/finalize/stream` returning a **streamed response body** (NDJSON, or SSE-formatted text parsed manually); emit one event per tool-call AND per agent reasoning step (`AgentEvent{type, tool, summary, reasoning}`). Non-streaming endpoint stays for tests/fallback. **DECIDED (not EventSource):** the frontend consumes this via `fetch()` + `ReadableStream`, NOT `EventSource` — EventSource is GET-only and cannot send the Firebase `Authorization` header. `POST` + fetch-streaming keeps the existing auth pattern and avoids tokens in URLs.

- [ ] **Step 1:** Backend test asserts the stream yields ordered events ending in a terminal status.
- [ ] Steps 2–4: implement, run, commit `feat(agent): SSE event stream for /agent/finalize`.

### Task 4.2: Timeline UI

**Files:** Create `apps/web/src/lib/hooks/useAgentFinalize.ts`, `components/agent/AgentTimeline.tsx` + `agent.module.css`; Modify `WorkspaceV2.tsx` (add "Finalize with agent" action, additive — the existing manual flow stays).

- [ ] **Step 1:** Static UI test (string assertions) like the existing `test_mvp_*` pattern: hook consumes the POST fetch stream (ReadableStream reader, NOT EventSource); timeline renders events incl. reasoning; "Finalize with agent" wired.
- [ ] Steps 2–4: implement; `npx tsc --noEmit` clean; `npm run build` ok; commit `feat(web): agent activity timeline (Finalize with agent)`.
- [ ] **Step 5:** Browser verify (webapp-testing or user paste): live timeline shows reasoning → tool calls → approval prompt.

> **CC REVIEW GATE 4:** timeline shows *reasoning*, not just tool names; manual flow untouched; tsc + build green; full suite green. If time-boxed out, this phase is CUT and the agent still works via the non-streaming result.

---

## Phase 5 — MCP external action (STRETCH / CUTTABLE)

**Owner: P5.1 Codex-implement · P5.2 CC-implement** (⚠️→Codex only if CC low on tokens). **Skill:** `document-skills:mcp-builder` (CC, for the FastMCP server). **Deploy point:** with P6.

### Task 5.1: `extract_dev_tasks` capability  *(Codex)*

**Files:** Create `services/api/src/sadify_api/services/dev_tasks.py`; Modify `schemas.py` (add `DevTask{priority, title, description, source_refs[]}`).

`extract_dev_tasks(preview, analysis, sources) -> list[DevTask]` — structured, **traceable** tasks (each carries `source_refs`; honor the MUST-NOT "no untraceable dev tasks"). Gemini structured call + deterministic validation that every task has a source_ref.

- [ ] Steps 1–5 (TDD): test traceability invariant; implement; commit `feat(agent): extract_dev_tasks (traceable)`.

### Task 5.2: FastMCP GitHub server + ADK McpToolset  *(CC — ⚠️→Codex if low tokens)*

**Files:** Create `agent/mcp_github.py`; Modify `agent/tools.py`, `agent/finalize.py`.

Self-written **FastMCP** (Python, package `fastmcp`) server exposing `create_github_issues(repo, tasks, token)`; run as a **stdio subprocess** wired via ADK `McpToolset`. **DECIDED:** add `fastmcp` to deps **in this phase** (not P0 — P5 is cuttable; only bloat the deploy image if P5 ships). The `create_github_issues` agent tool is **approval-gated** (outbound write) and records issue links into project history/wiki. **GitHub auth UX (PENDING user decision at P5, recommendation):** user supplies a PAT (`repo` scope) stored in Secret Manager like the Drive secret; issues go to a user-named repo. Live creation is the strongest demo; Docs-via-MCP fallback is acceptable if PAT collection is too fiddly. **Fallback:** if the GitHub MCP path proves too heavy, wrap the existing Drive/Docs save as the MCP action instead (still satisfies "≥1 MCP external tool"; doc explicitly accepts Google-Docs-via-MCP).

- [ ] **Step 1:** MCP server unit test with a mocked GitHub API (no real network); test the issues payload shape.
- [ ] **Step 2:** Agent tool test: refuses without approval; on approval, calls the MCP tool; core finalize still works with GitHub disabled.
- [ ] Steps 3–5: implement; commit `feat(agent): GitHub issues via FastMCP (approval-gated, optional)`.

> **CC REVIEW GATE 5:** agent creates GitHub issues through MCP, approval-gated; **core finalize works without GitHub connected** (CC verifies the optionality); dev tasks traceable; full suite green. CUT to the Google-Docs-via-MCP fallback if blocked.

---

## Phase 6 — Deploy + prod smoke + docs closure

**Skill:** `document-skills:webapp-testing`. **Deploy point:** ✅ full stack.

### Task 6.1: Deploy

- [ ] Backend: `gcloud run deploy sadify-api --source .` (image now includes google-adk from P0; PYTHONPATH unchanged). STOP for user approval — billable.
- [ ] Frontend: `gcloud builds submit apps/web --config apps/web/cloudbuild.yaml --substitutions=...` → `gcloud run deploy sadify-web --image .../sadify-web:latest`.

### Task 6.2: Prod smoke (CC narrates one case at a time; user runs browser)

- [ ] Agentic finalize end-to-end on prod with **Pro selected**: interview → readiness gate → draft → self-review (observe a regenerate or a clean proceed) → approval → Drive Doc + wiki saved → (if P5) GitHub issues created. Watch Cloud Logging for 5xx/agent errors.
- [ ] Not-ready path: agent asks a clarification instead of drafting.
- [ ] Approval gate: confirm nothing wrote before approval.

### Task 6.3: Docs closure (the four together — per the doc-workflow rule)

- [ ] `docs/superpowers/testing/test_cases/TC-034-*.md` — expected/real/diff/evidence/pass-fail.
- [ ] `CURRENT.md`, `07_decision_log.md` (new D-### for the agent), `test_case_index.md` — updated together.

> **CC REVIEW GATE 6 (final):** prod smoke green (zero 5xx), agent demonstrably reasons/acts/reflects/asks-approval on prod incl. Pro; all four docs updated; memory `project_phase_status.md` + `tc034_agentic_design.md` marked done. TC-034 closed.

---

## Cut-line summary (deadline safety)
- **Must ship (Track-1 satisfying):** P0 → P3 (real ADK agent that reasons → acts → reflects → asks approval → saves SAD/wiki) + P6 deploy.
- **Enhancements (cut in order if time runs short):** P5 (MCP GitHub → fallback to Docs-via-MCP) is cuttable last; P4 (timeline polish) is cuttable first but high demo value.
- **Never compromise:** GATE 1 (MVP behavior preserved) and GATE 3 (no write without approval).

## Self-review notes (coverage check)
- Framework (ADK): P2/P3. Reason-act-reflect: P3. MCP: P5 (+fallback). Approval-gated writes: P3. Activity timeline: P4. extract_dev_tasks/traceability: P5. Behavior-contract conformance: instruction in P2 + traceability invariant in P5. Q&A engine preserved: P1 freezes helpers, `ask_clarification` reuses engine. Non-breaking: additive `/agent` only; routes delegate. Deploy gate + cost (Pro latency, multi-call loop): noted in P3/P6.
