# TC-034 SADify Analyst Agent

Date Created: 2026-06-05
Last Updated: 2026-06-05
Status: Passed for TC-034a/b/c - ADK finalize agent, approval-gated writes, streamed timeline, closed review loop, and live Flash browser smoke all passed; P5 MCP/external tool and P6 deploy remain separate pending work

## Traceability Sources

- `docs/superpowers/plans/2026-06-04-tc034-sadify-analyst-agent.md`
- `docs/superpowers/development/02_agent_behavior_contract.md`
- `docs/superpowers/testing/test_case_index.md`
- `services/api/src/sadify_api/agent/finalize.py`
- `services/api/src/sadify_api/agent/tools.py`
- `services/api/src/sadify_api/routes/agent.py`
- `tests/api/test_agent_finalize.py`
- `tests/api/test_agent_tools.py`
- `tests/test_tc034_agent_timeline_ui.py`

## Purpose

Verify that SADify has a visible ADK-powered Analyst Agent that can reason over
an analysis session, call SADify services as tools, critique its own SAD draft,
return explicit approval prompts before writes, execute approved writes
deterministically, and surface the activity as a streamed timeline.

## Inputs

- Saved requirement analysis sessions in the existing analysis repository.
- ADK `Agent`, `Runner`, `InMemorySessionService`, and `FunctionTool` wrappers.
- Gemini-backed `review_sad` self-audit output.
- In-memory approval tokens keyed by `(analysis_session_id, approval_id)`.
- `POST /agent/finalize`, `POST /agent/approve`, and
  `POST /agent/finalize/stream`.
- Frontend `AgentTimeline` overlay and `fetch()` `ReadableStream` consumer.

## Preconditions

- Worktree: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`
- Branch: `codex/mvp-monorepo-scaffold`
- TC-032 Gemini model picker is deployed and production-smoked.
- Current plan: `docs/superpowers/plans/2026-06-04-tc034-sadify-analyst-agent.md`
- No Cloud Run deploy without explicit user approval.

## Steps

1. Run the backend agent tests for ADK tool wrapping, finalize behavior,
   self-review, approval gating, deterministic approve execution, and streaming.
2. Run the frontend static UI tests for the streamed timeline and approval UI.
3. Run the full Python suite.
4. Run frontend typecheck and build.
5. Manually browser-smoke the timeline, approval prompt, real Drive/wiki write,
   and wiki-conflict overwrite re-approval.

## Expected Output

- The finalize flow is a real ADK agent loop, not a hand-written state machine.
- The agent can inspect readiness, generate a SAD draft, self-review it,
  regenerate within the cap, or ask one clarification.
- No Drive/wiki write executes without a valid matching approval token.
- `/agent/approve` executes only the approved actions and does not re-run the LLM.
- The stream endpoint returns ordered NDJSON events ending in a terminal status.
- The frontend renders reasoning, tool steps, and an approval prompt through
  `fetch()` + `ReadableStream`, not `EventSource`.
- Existing manual Q&A/SAD save/wiki flows remain additive and untouched.

## Real Output

### TC-034a - Real ADK Agent Loop (P2/P3.1)

#### Expected Output

The finalize agent runs through ADK `Agent` + `Runner` + `FunctionTool`. The
model owns tool sequencing. `review_sad` self-critiques the generated draft,
can request regeneration, and the regenerate loop is capped at two extra
attempts by code-level boundaries.

#### Real Output

Implemented in commits:

- `d16f6c6 feat(agent): agent instruction + read/generate tool wrappers`
- `d2c2287 feat(agent): add finalize runner and route`
- `d29f43d feat(agent): review_sad self-reflection with regenerate cap`

CC live probe with real Gemini observed:

```text
get_readiness -> generate_sad -> review_sad(regenerate) -> generate_sad -> review_sad -> ask_clarification
```

#### Differences / Issues

None recorded for TC-034a.

#### Evidence

- `tests/api/test_agent_finalize.py`
- `tests/api/test_agent_tools.py`
- CC live probe: real Gemini executed the reason -> act -> reflect -> re-act
  loop and produced analyst-grade self-audit issues before asking a
  clarification.

#### Decision

PASS. The core loop is ADK-driven and includes self-reflection with a capped
regeneration path.

### TC-034b - Approval Gate / GATE 3 (P3.2 + Determinism Fix)

#### Expected Output

No Drive/wiki write fires without a matching, preview-scoped, single-use
approval token. `/approve` executes only the approved actions deterministically
and never re-runs the LLM. The token is consumed on success, kept on hard write
failure, and wiki conflict returns a new overwrite approval.

#### Real Output

Implemented in commits:

- `639d043 feat(agent): approval-gated Drive/wiki writes + /agent/approve`
- `686e3de fix(agent): make approved writes deterministic`

The determinism fix changed `/agent/approve` to call approved tool functions
directly with the peeked approval token, rather than re-entering the ADK loop.
Ready `/agent/finalize` results now return `awaiting_approval` with
`save_to_drive` and `update_wiki` proposed actions.

#### Differences / Issues

The first live GATE 3 run found a reliability issue: `/approve` re-ran the
agent, regenerated a new preview, and burned the approval token without saving
the approved preview. The safety invariant still held because no unauthorized
write fired. Commit `686e3de` fixed the reliability issue by making approved
write execution deterministic.

#### Evidence

- Tests cover deterministic approve without an LLM run.
- Tests cover missing token refusal.
- Tests cover mismatched preview refusal.
- Tests cover hard write failure leaving the token retryable.
- Tests cover wiki conflict consuming the original token and issuing a new
  overwrite approval.
- CC live re-probe confirmed `/finalize -> awaiting_approval` and
  `/approve -> save_to_drive + update_wiki` with no regeneration.
- CC live re-probe confirmed bogus approval token refused with zero writes.

#### Decision

PASS. GATE 3 safety and approve determinism are both verified.

### TC-034c - Activity Timeline, Closed Review Loop, and Live Browser Smoke

#### Expected Output

`POST /agent/finalize/stream` yields NDJSON events with derived reasoning for
each step and a terminal status. The frontend consumes the POST stream via
`fetch()` + `ReadableStream`, renders reasoning -> tool steps -> approval
prompt in `AgentTimeline`, and leaves the manual flow intact.

#### Real Output

Implemented in commits:

- `d1285d2 feat(agent): SSE event stream for /agent/finalize`
- `31d256d feat(web): agent activity timeline (Finalize with agent)`
- `e0f9fd1 fix(agent): trust Q&A and finalize instead of re-asking (collaborative)`
- `798a325 feat(web): make "Finalize with agent" the hero action in the ready footer`
- `0889aab feat(agent): closed revise loop, draft safety-net, live-wiki fix`
- `18a6aa9 feat(web): single agent entry point (Finalize hero + Quick draft)`
- `bce7488 fix(agent): surface completed save on wiki conflict for UI refresh`
- `da153be feat(web): clearer Drive-vs-wiki approval/result UI + save-history refresh`

Backend stream tests assert ordered tool events with reasoning and a terminal
status. Frontend static tests assert `streamAgentFinalize`, `approveAgentActions`,
`ReadableStream` parsing, no `EventSource`, `AgentTimeline` reasoning display,
approval prompt rendering, and unchanged manual save wiring.

The later TC-034c polish made the browser-visible agent flow demoable:

- A valid draft now wins over stray `ask_clarification` tool calls, so answered
  Q&A facts remain trusted and review gaps fold into the SAD's open questions.
- `review_sad` feedback is threaded into the next regeneration with a
  no-fabrication instruction, and regeneration is allowed only after a current
  draft's `regenerate` verdict.
- A deterministic draft safety-net prevents phantom approval when a weaker model
  stops after readiness checking.
- Live wiki updates resolve Drive/Secret dependencies lazily in the agent path,
  matching the existing SAD route behavior.
- The frontend has a single primary `Finalize with agent` entry point, a
  secondary `Quick draft` manual path, clearer Drive-vs-wiki approval/result
  copy, and save-history refresh after agent saves.

#### Differences / Issues

None recorded for TC-034c. The prior localhost approval-card and live-wiki
issues were resolved by the committed TC-034c fixes above.

Remaining submission work is outside TC-034c: P5 MCP/external tool, P6 deploy,
demo video, and architecture writeup are not done.

#### Evidence

- Backend commit: `d1285d2`
- Frontend commit: `31d256d`
- Follow-up commits: `e0f9fd1`, `798a325`, `0889aab`, `18a6aa9`, `bce7488`,
  `da153be`
- Backend tests: `tests/api/test_agent_finalize.py`
- Frontend static UI test: `tests/test_tc034_agent_timeline_ui.py`
- CC-reported whole-suite evidence:

```text
..\..\.venv\Scripts\python.exe -m pytest -q
537 passed, 4 skipped
```

- CC-reported frontend verification:

```text
npx tsc --noEmit
passed

npm run build
passed
```

Manual browser smoke evidence:

| Evidence Item | Status | Notes |
| --- | --- | --- |
| Localhost timeline transcript | PASSED 2026-06-05 | Browser transcript showed `SADify agent`, streamed readiness reasoning, draft generation, self-review, and approval pause. |
| Approval prompt visible in browser | PASSED 2026-06-05 | `Finalize with agent` reached `awaiting_approval` and rendered the approval card with Drive/wiki actions. |
| Real Drive Doc write | PASSED 2026-06-05 | Live Flash smoke completed `Approve & save` and wrote a real SAD Google Doc through the agent approval path. |
| Real wiki update | PASSED 2026-06-05 | Live Flash smoke updated the project wiki through the agent approval path with live Drive/wiki dependencies enabled. |
| Wiki conflict -> overwrite re-approval | PASSED 2026-06-05 | Conflict flow surfaced the already-completed Drive save and returned an overwrite re-approval; the overwrite approval updated the wiki. |
| Sidebar history refresh | PASSED 2026-06-05 | Agent save refreshes the sidebar/project history after `da153be`. |

#### Decision

PASS. TC-034c is browser-smoked and live-verified locally with Gemini Flash,
including real Drive Doc write, wiki update, and wiki-conflict overwrite
re-approval. Do not claim demo video or architecture writeup completion; those
remain submission tasks.

## Differences / Issues

- P5 MCP/tool-ecosystem work has not started and is gated on the user's tool
  brainstorm.
- P6 deploy has not started.
- Demo video and architecture writeup have not started.

## Evidence

- `d16f6c6 feat(agent): agent instruction + read/generate tool wrappers`
- `d2c2287 feat(agent): add finalize runner and route`
- `d29f43d feat(agent): review_sad self-reflection with regenerate cap`
- `639d043 feat(agent): approval-gated Drive/wiki writes + /agent/approve`
- `686e3de fix(agent): make approved writes deterministic`
- `d1285d2 feat(agent): SSE event stream for /agent/finalize`
- `31d256d feat(web): agent activity timeline (Finalize with agent)`
- `e0f9fd1 fix(agent): trust Q&A and finalize instead of re-asking (collaborative)`
- `798a325 feat(web): make "Finalize with agent" the hero action in the ready footer`
- `0889aab feat(agent): closed revise loop, draft safety-net, live-wiki fix`
- `18a6aa9 feat(web): single agent entry point (Finalize hero + Quick draft)`
- `bce7488 fix(agent): surface completed save on wiki conflict for UI refresh`
- `da153be feat(web): clearer Drive-vs-wiki approval/result UI + save-history refresh`
- `tests/api/test_agent_finalize.py`
- `tests/api/test_agent_tools.py`
- `tests/test_tc034_agent_timeline_ui.py`
- CC-reported backend suite: `537 passed, 4 skipped`
- CC-reported frontend checks: `npx tsc --noEmit` passed; `npm run build`
  passed.

## Decision

TC-034a/b/c passed as of 2026-06-05: P0-P4 are complete, CC-reviewed, and
browser-smoked with Gemini Flash through real Drive Doc save, wiki update, and
wiki-conflict overwrite re-approval. P5 MCP/external tool, P6 deploy, demo
video, and architecture writeup remain pending submission work.
