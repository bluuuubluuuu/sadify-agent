# SADify Test Case Index

Date: 2026-04-30  
Last updated: 2026-06-19

## Purpose

This index tracks SADify test cases, expected output, real output, issues, evidence, and checkpoints.

Testing should support safe development. A feature should not move to the next checkpoint until its expected behavior, real behavior, and issues are documented.

## Traceability Sources

This test index should be verified against:

- `docs/superpowers/development/05_development_workflow.md`
- `docs/superpowers/development/02_agent_behavior_contract.md`
- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `docs/superpowers/development/04_google_cloud_setup_runbook.md`
- `docs/superpowers/development/06_demo_script_and_acceptance_checklist.md`
- `docs/superpowers/development/14_qna_workflow_refinement.md`

When a workflow checkpoint changes, update this index and the matching `TC-XXX` file.

## Current Test Phase

```text
Current phase: TC-036 GitHub Issue Relaunch And Deduplication.
Active focus: implementation and automated regression passed. Throwaway memory-mode and Firestore/live GitHub recovery smokes are pending; do not deploy or mark TC-036 Passed without that evidence.
Completed before this:
  - MVP-00 through MVP-09 (scaffold + foundations).
  - TC-021S and TC-021T (Q&A workflow stabilization).
  - TC-028 evidence-based readiness (manual browser smoke passed 2026-05-24).
  - Cycle 2A (monotonic readiness, applicability stickiness,
    merged slot_evidence persistence) — shipped 2026-05-24.
  - Cycle 2B (section coverage, assumptions/open-questions,
    paraphrasing, understanding-summary preservation) — shipped 2026-05-24.
  - Anti-repetition Guard B tightened to threshold 2.
Superseded and archived: TC-021R through TC-021Y. All eight subsumed by
  TC-028 and Cycles 2A/2B. Full text preserved in
  `docs/superpowers/archive/testing/test_cases/consolidated-test-cases.md`.
Do not deploy without explicit user approval.
```

Phase grouping:

| Phase | Tests |
| --- | --- |
| Phase 0 - Planning / challenge context | TC-015 and source docs |
| Phase 1 - Streamlit prototype baseline | TC-001 through TC-014 |
| Phase 2 - Proper MVP scaffold and full-stack foundation | TC-015 through TC-024 |
| Phase 3 - Q&A workflow stabilization | TC-021S, TC-021T (TC-021R archived) |
| Phase 4 - SAD preview and SAD quality stabilization | TC-028 (TC-021U..Y archived) |
| Phase 5 - Drive + Google Docs save path | TC-026 |
| Phase 6 - Wiki update approval + two-service deploy | TC-025A, TC-025B, TC-027 |
| Post-MVP - Model selection and agentic finalize | TC-032, TC-034 (TC-033 deferred) |

## Test Case Template

Each test case should use this structure:

```markdown
# TC-XXX Test Name

Date Created:
Last Updated:
Status: Not Run | Passed | Failed | Blocked

## Purpose

What this test proves.

## Inputs

Files, text, or user actions used for the test.

## Preconditions

What must exist before running.

## Steps

1. Step one
2. Step two

## Expected Output

What should happen.

## Real Output

What actually happened when tested.

## Differences / Issues

Where real output differs from expected output.

## Evidence

- screenshots
- exported file links
- browser console logs
- network request/response details
- HTTP status codes
- app logs
- stack traces
- command output

## Decision

Pass/fail decision and next action.
```

## Test Cases

| ID | Test Area | Status | Last Run | Linked Doc | Notes |
| --- | --- | --- | --- | --- | --- |
| TC-001 | Requirement Input | Passed | 2026-05-05 | `test_cases/TC-001-requirement-input.md` | Local deterministic text input and first-response pattern; browser-found render scoping bug fixed |
| TC-002 | Business File Extraction | Passed | 2026-05-05 | `test_cases/TC-002-business-file-extraction.md` | MD/TXT, PDF, DOCX, XLSX, CSV extraction plus Streamlit upload preview |
| TC-003 | Canonical JSON Schema | Passed | 2026-05-06 | `test_cases/TC-003-canonical-json-schema.md` | Six MVP canonical records validate required fields, stable IDs, types, statuses, score bounds, and useful error messages |
| TC-004 | Completeness + Confidence | Passed | 2026-05-06 | `test_cases/TC-004-completeness-confidence.md` | Local deterministic evidence checklist, short-input caps, visible score evidence, no live model call |
| TC-005 | Relationship Linking | Passed | 2026-05-06 | `test_cases/TC-005-relationship-linking.md` | Local deterministic requirement graph builder creates canonical requirement/entity/workflow/actor/report/decision/source links with evidence source IDs |
| TC-006 | Wiki Markdown Generation | Passed | 2026-05-07 | `test_cases/TC-006-wiki-markdown-generation.md` | Local deterministic wiki renderer creates frontmatter, wiki links, folder paths, questions, assumptions, and broken-link errors |
| TC-007 | Wiki Verification + Approval | Passed | 2026-05-07 | `test_cases/TC-007-wiki-verification-approval.md` | Local rule checks, pending owner review state, approval/rejection transitions; Gemini quality placeholder recorded as not_run |
| TC-008 | SAD Generation | Passed | 2026-05-07 | `test_cases/TC-008-sad-generation.md` | Local project-level SAD version creates structured sections, Markdown preview, open questions, assumptions, traceability, and developer tasks |
| TC-009 | Export Generation | Passed | 2026-05-08 | `test_cases/TC-009-export-generation.md` | Local Google-Doc-import HTML, PDF, DOCX, and wiki Markdown artifacts plus canonical export records; real Drive upload deferred |
| TC-010 | Firestore Persistence | Passed | 2026-05-06 | `test_cases/TC-010-firestore-persistence.md` | Local-first repository path mapping, validation-before-save, round trips, missing reads, and wrapped/logged errors; real cloud smoke not run |
| TC-011 | Runtime Diagnostics | Passed | 2026-05-04 | `test_cases/TC-011-runtime-diagnostics.md` | Local diagnostics foundation passed; browser/network checks remain for later external-call checkpoints |
| TC-012 | Cloud Run Smoke Test | Passed | 2026-05-11 | `test_cases/TC-012-cloud-run-smoke-test.md` | Basic deployed prototype smoke passed: health endpoint 200 ok and deterministic requirement analysis renders; live Gemini, Firestore, Drive/Docs export, and log-admin checks deferred to improvement backlog |
| TC-013 | Model Provider Routing | Passed | 2026-05-04 | `test_cases/TC-013-model-provider-routing.md` | Google/Gemini default route plus configurable final-SAD and fallback route metadata |
| TC-014 | Local End-To-End Test | Passed | 2026-05-11 | `test_cases/TC-014-local-end-to-end.md` | Local deterministic MVP path from intake through analysis, graph, wiki approval, SAD, export, diagnostics, and repository persistence |
| TC-015 | Prototype-To-MVP Design Alignment | Passed | 2026-05-11 | `test_cases/TC-015-prototype-to-mvp-design-alignment.md` | Design, decision, workflow, index, and test docs align; no code/cloud/API changes made |
| TC-016 | MVP Monorepo Scaffold | Passed | 2026-05-11 | `test_cases/TC-016-mvp-monorepo-scaffold.md` | Initial Next.js frontend and FastAPI backend scaffold added in MVP worktree; Python baseline passed with 92 tests |
| TC-017 | MVP FastAPI Health And Contract | Passed | 2026-05-12 | `test_cases/TC-017-mvp-fastapi-health-contract.md` | Typed FastAPI `/health`, redacted config diagnostics, root pytest import path, and 95-test regression passed |
| TC-018 | MVP Workspace Shell | Passed | 2026-05-12 | `test_cases/TC-018-mvp-workspace-shell.md` | Mocked Next.js workspace shell, guided Q&A, readiness, change tracking, standalone browser smoke, and 97-test regression passed |
| TC-019 | MVP Firebase Auth Session | Passed | 2026-05-13 | `test_cases/TC-019-mvp-firebase-auth-session.md` | Local auth/session foundation revalidated; live Firebase Google sign-in passed with `/auth/session` returning 200 OK and UI showing signed-in persistent session |
| TC-020 | MVP Guest Draft Migration | Passed | 2026-05-13 | `test_cases/TC-020-mvp-guest-draft-migration.md` | Local fake-store guest draft creation and safer signed-in copy contract passed; real Firestore cloud persistence deferred |
| TC-021 | MVP Live Gemini Q&A | Passed; refined by TC-021R | 2026-05-15 | `test_cases/TC-021-mvp-live-gemini-qna.md` | Backend/frontend structured Q&A wiring, live Gemini schema-valid smoke, and answer continuation passed; category/progress UX refinement completed in TC-021R |
| TC-021R | MVP Category-First Q&A Refinement | Archived (superseded by TC-028) | 2026-05-15 | `archive/testing/test_cases/consolidated-test-cases.md` | Historical only; readiness model replaced by evidence-based scoring |
| TC-021S | MVP Stable Questionnaire Plan Refactor | Archived (superseded by TC-028) | 2026-05-18 | `archive/testing/test_cases/consolidated-test-cases.md` | Historical only; carry-forward + ratchet now in production code |
| TC-021T | Q&A Ready State And Preview Handoff | Archived (superseded by TC-028) | 2026-05-18 | `archive/testing/test_cases/consolidated-test-cases.md` | Historical only; ready-state handoff stable in current codebase |
| TC-021U | Q&A And SAD Synthesis Quality | Archived (superseded by Cycle 2B) | 2026-05-19 | `archive/testing/test_cases/consolidated-test-cases.md` | Historical only; SAD synthesis composition reset in Cycle 2B |
| TC-021V | SAD Fallback Composition Quality | Archived (superseded by Cycle 2B) | 2026-05-19 | `archive/testing/test_cases/consolidated-test-cases.md` | Historical only |
| TC-021W | User-Facing SAD Draft Quality | Archived (superseded by Cycle 2B) | 2026-05-20 | `archive/testing/test_cases/consolidated-test-cases.md` | Historical only |
| TC-021X | Evidence-First Q&A Depth And Valid Preview Coherence | Archived (superseded by TC-028 + Cycle 2B) | 2026-05-21 | `archive/testing/test_cases/consolidated-test-cases.md` | Historical only |
| TC-021Y | Domain-Aware Q&A And SAD Quality Hardening | Archived (superseded by TC-028 + Cycle 2B) | 2026-05-21 | `archive/testing/test_cases/consolidated-test-cases.md` | Historical only |
| TC-022 | MVP Source Upload Traceability | Passed | 2026-05-13 | `test_cases/TC-022-mvp-source-upload-traceability.md` | Local multipart upload, source extraction state, source IDs, traceability units, unsupported-file errors, and source refs into analysis request passed; real Firestore/Drive persistence deferred |
| TC-023 | MVP Drive Repo OAuth | Passed | 2026-05-14 | `test_cases/TC-023-mvp-drive-repo-oauth.md` | Local backend-mediated Drive repo grant contract, `drive.file` scope intent, config-aware OAuth-code UI, planned repo folders, and disconnect passed; live token exchange, Secret Manager storage, Drive writes, and Picker remain deferred |
| TC-024 | MVP SAD Preview And IT Readiness | Passed | 2026-05-14 | `test_cases/TC-024-mvp-sad-preview-it-readiness.md` | Local structured SAD preview schema, blocking-basics gate, IT readiness checklist, assumptions/open questions, source refs, change tracking, preview UI, and manual live local preview smoke passed; Drive/Docs save deferred |
| TC-025A | MVP Wiki Snapshot | Passed | 2026-05-27 | `test_cases/TC-025A-mvp-wiki-snapshot.md` | Live `POST /sad/wiki/preview` + `/sad/wiki/update` write a single `Wiki/Wiki.md` Markdown snapshot into `SADify Projects/Wiki/`. Hash-based conflict detection, `WikiStateRepository`, 9 stable error codes. Behind double env gate. |
| TC-025B | MVP Encyclopedia Wiki | Passed | 2026-05-28 | `test_cases/TC-025B-mvp-encyclopedia-wiki.md` | Eight-file Obsidian-style wiki (`Wiki.md` index + seven category notes) with `[[wiki links]]`, YAML frontmatter, title-normalization routing of SAD sections, per-file hash tracking, bulk conflict approval, and backup of managed files to `_SADify/wiki-backups/<timestamp>/`. Replaced TC-025A composer. 387 local-mode regression, live Case 13 smoke passed. |
| TC-026D | MVP Project Isolation | Passed | 2026-05-28 | `test_cases/TC-026D-mvp-project-isolation.md` | Per-project Drive subfolder isolation (`SADify Projects/<Project>/SAD/`, `/Wiki/`, `/_SADify/`). Active project tracked on `DriveRepoRecord`. Per-project SV-/SA-/SM- counters (SP- stays global). `ProjectPanel` with dropdown + New project + Refresh. `CreateProjectDialog` auto-opens on `PROJECT_REQUIRED` 409. 428 local-mode regression green; live Cases 15-19 smoke passed. |
| TC-026E | MVP Project Save History | Passed | 2026-05-29 | `test_cases/TC-026E-mvp-project-history.md` | Per-project save list via `GET /projects/{project_id}/saves`. `ProjectHistoryPanel` renders the list, survives page refresh (auth-restore re-fetches status then saves), auto-refreshes after each save, isolates per project. In-memory; Firestore post-MVP. 446 local-mode regression; live Case 20 smoke passed. |
| TC-029 | Analysis-State Reset Fix | Passed | 2026-05-29 | `test_cases/TC-029-analysis-session-reset.md` | Explicit `analysis_session_id` keys carry-forward per frontend session; regenerated on new-source-upload / project-switch. Fixes cross-source content bleed (catering source no longer produces a grooming SAD), 100%-no-questions on saturated state, and "I'm not sure" acceptance. Additive schema; 457 local-mode tests; live smoke passed. |
| TC-030 | Firestore Persistence | Passed | 2026-05-30 | `test_cases/TC-030-mvp-firestore-persistence.md` | Project/SAD-save/wiki-state/Drive-grant persist to Firestore Native Mode behind `SADIFY_PERSISTENCE=firestore` (default `memory`). Survives backend cold restart; analysis/Q&A stays in-memory by design. Two P0 transaction bugs (read-after-write ordering; un-begun manual transactions) fixed via `run_in_transaction` + `firestore.transactional`. 471 local-mode tests + 4 live round-trips (real Firestore) + live restart-survival smoke passed. Commits 969cad8, 21616c7, c2166cd. Deploy prerequisite cleared. |
| TC-026 | MVP Drive Docs Save | Passed for local/fake save path | 2026-05-25 | `test_cases/TC-026-mvp-drive-docs-save.md` | Local/fake `POST /sad/save` contract passed with stable save records, fake Google Doc URL/path, `_SADify` manifest/change-log artifacts, source references, idempotent repeat save, frontend save action, and no live Drive/Docs/OAuth/Secret Manager calls. |
| TC-026B | MVP Live Drive/Docs Save | Passed | 2026-05-25 | `test_cases/TC-026B-mvp-live-drive-docs.md` | Live OAuth code exchange, real `SADify Projects` Drive folder, real Markdown-to-Doc upload, refresh token in Secret Manager, disconnect deletes per-user secret. Behind double env gate `SADIFY_DRIVE_MODE=live` + `SADIFY_DRIVE_LIVE_ENABLED=1`. Local-mode regression stays green by default. |
| TC-027 | MVP Two-Service Deployed Smoke | Passed | 2026-06-03 | `test_cases/TC-027-mvp-two-service-deployed-smoke.md` | Both Cloud Run services live in asia-southeast1 (scale-to-zero, sadify-agent-sa ADC). 7-case browser smoke all pass, zero 5xx: guest Q&A→sign-in→Drive connect→SAD preview→save Google Doc→wiki→Firestore-persisted history. 3 missing backend deps fixed (58aa315); 2 console fixes (Firebase authorized domain, OAuth JS origin). Final MVP checkpoint cleared. |
| TC-028 | Evidence-Based Readiness | Passed (manual browser smoke 2026-05-24) | 2026-05-24 | `test_cases/TC-028-evidence-based-readiness.md` | Quote-validated per-slot evidence + deterministic aggregation + derived confidence + `not_applicable` handling. Extended by Cycle 2A (monotonic score, applicability stickiness, merged slot_evidence persistence) and Cycle 2B (SAD section coverage, assumptions/open-questions, paraphrasing, understanding-summary preservation). Anti-repetition Guard B (threshold 2) ensures no question is asked a third time. |
| TC-031 | Readiness Confidence Semantics | Passed (verification + A/B/C/C2/D/D2/E automated 2026-06-02); Test-F logging held | 2026-06-02 | `test_cases/TC-031-readiness-confidence-semantics.md` | Verifies score (completeness %) and confidence (evidence-grounding) are independent, so 90%+/"Ready for draft" with Low confidence is expected, not a bug. Oscillation traced to `downgrade_count` (this-turn raw quote validation) vs strong/none ratio (merged carry-forward). A/B/C in `test_slot_evidence.py:117-130`; C2/D2 added there; D added in `test_evidence_readiness_scenarios.py`; E in `test_mvp_workspace_shell.py`. Full suite 460 passed. Test-F backend logging held for approval. Pairs with A+B confidence-binding fix + D-wording (D-093). |
| TC-032 | Gemini Model Picker | Passed | 2026-06-04 | `test_cases/TC-032-gemini-model-picker.md` | Backend-owned 3-model Gemini catalog (Flash default, Pro, Flash-Lite), model-aware Pro generation config, optional per-request model threading, localStorage-backed dynamic picker, and unavailable selected-model fallback to backend default. Full suite 488 passed / 4 skipped; deployed to Cloud Run revisions `sadify-api-00005-pc2` + `sadify-web-00002-vzw`; live Flash/Pro Q&A + SAD preview API smoke passed; deployed browser picker selected Pro and completed one visible Q&A turn. |
| TC-033 | Layer 2 Technical Design | Planned | Not run | `test_cases/TC-033-layer2-technical-design.md` | Planned technical model and diagrams slice; follows TC-032. |
| TC-034 | SADify Analyst Agent | Passed for TC-034a/b/c; P5 MCP pending | 2026-06-05 | `test_cases/TC-034-sadify-analyst-agent.md` | ADK Finalize agent with reason -> act -> reflect loop, deterministic approval-gated Drive/wiki writes, streamed AgentTimeline, closed review -> revise loop, and single visible agent entry point. Latest suite `537 passed / 4 skipped`, tsc/build green. Live Flash browser smoke passed end-to-end with real Drive Doc save, wiki update, and wiki-conflict overwrite re-approval. P5 MCP/external-tool, P6 deploy, demo video, and architecture writeup not started. |
| TC-036 | GitHub Issue Relaunch And Deduplication | Pending live smoke | 2026-06-19 | `test_cases/TC-036-github-issue-relaunch.md` | Durable immutable issue sets, authenticated saved-SAD prepare/relaunch, fresh GATE 3 approval, body-marker dedup, history resume action, and delete cascade are implemented. Automated result: `652 passed / 4 skipped`, tsc/build green. Throwaway memory/live GitHub and Firestore recovery evidence is still required. |

## Runtime Diagnostics Coverage

`TC-011` should cover:

- browser console errors
- network requests
- failed API calls
- file upload behavior
- response timing
- extraction logs
- Gemini request/response logs with sensitive data redacted
- Firestore read/write logs
- export logs
- verification logs
- exception stack traces
- schema validation failures
- broken wiki links
- Google Drive/Docs export failures
- HTTP status codes
- timeout handling
- retry behavior
- user-friendly error messages

## Architecture Foundation Coverage

`TC-013` covers the model-routing foundation that sits between diagnostics and requirement text input:

- `google / gemini-2.5-flash` remains the default route
- requirement-analysis and final-SAD routes can be configured separately
- optional fallback route can be configured
- provider readiness is visible without leaking secrets
- live non-Google adapter calls remain future

## Local MVP Coverage

`TC-014` covers the local end-to-end checkpoint across earlier local capabilities:

- requirement analysis uses the same deterministic service as the Streamlit wrapper
- relationship graph, wiki Markdown, wiki verification, SAD generation, and export generation compose successfully
- owner approval promotes generated wiki drafts for the local workflow proof
- canonical records persist through the Firestore repository abstraction with a fake local client
- diagnostics record successful local stages
- Streamlit starts headlessly and returns `200 ok` on the local health endpoint

## Prototype-To-MVP Coverage

`TC-015` through `TC-027` cover the new MVP web-app track described in:

```text
docs/superpowers/specs/2026-05-11-sadify-prototype-to-mvp-design.md
docs/superpowers/development/05_development_workflow.md
docs/superpowers/testing/mvp_web_app_test_plan.md
```

Each new MVP feature must update its matching test case before the next checkpoint starts. Cloud-connected features require deployed smoke evidence, not only local tests.
