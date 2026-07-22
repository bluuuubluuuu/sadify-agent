# SADify Superpowers Reference

Created: 2026-04-29  
Last updated: 2026-05-25

This folder stores durable planning references for SADify so the project direction is not lost across chats or build sessions.

## Open First

For the current Phase 5 development path, use the minimum-token packet:

1. `../../CLAUDE.md`
2. `../../context.md`
3. `CURRENT.md`
4. `development/00_development_index.md`
5. `testing/test_cases/TC-026-mvp-drive-docs-save.md`
6. `development/04_google_cloud_setup_runbook.md`

Open `development/00_development_index.md`, `development/07_decision_log.md`,
`development/05_development_workflow.md`,
`development/14_qna_workflow_refinement.md`, `testing/test_cases/TC-023-mvp-drive-repo-oauth.md`,
and test indexes only when the brief or plan points there, or when a conflict
needs source-of-truth resolution.

## Phase Map

| Phase | Focus | Current status | Main docs |
| --- | --- | --- | --- |
| Phase 0 | Original planning / challenge context | Complete; historical source material retained | `research/`, source clippings, `plans/2026-04-29-sadify-google-cloud-mvp-plan.md` |
| Phase 1 | Streamlit prototype baseline | Complete through basic Cloud Run smoke | `development/05_development_workflow.md`, `testing/test_case_index.md` |
| Phase 2 | Proper MVP scaffold and full-stack foundation | MVP-00 through MVP-09 passed | `testing/mvp_web_app_test_plan.md`, TC-015 through TC-024 |
| Phase 3 | Q&A workflow stabilization | TC-021S and TC-021T passed; TC-021R superseded | `development/14_qna_workflow_refinement.md`, TC-021S, TC-021T |
| Phase 4 | SAD preview and SAD quality stabilization | Complete. TC-028 + Cycles 2A/2B passed manual browser smoke on 2026-05-24 | TC-028 and archived TC-021R..Y history |
| Phase 5 | Drive + Google Docs save path | Active; TC-026 is current | TC-026, TC-023, cloud setup runbook |
| Phase 6 | Wiki update approval + two-service deployment/final smoke | Not started; TC-025 and TC-027 are blocked until TC-026 passes | TC-025, TC-027 |

## Current Reference Set

- [2026-05-02 Root Coding Instructions](../../CLAUDE.md)
- [2026-05-02 Root Project Context](../../context.md)
- [2026-05-24 Current Work Brief](CURRENT.md)
- [2026-04-30 SADify Development Index](development/00_development_index.md)
- [2026-04-30 SADify Product Scope](development/01_product_scope.md)
- [2026-04-30 SADify Agent Behavior Contract](development/02_agent_behavior_contract.md)
- [2026-04-30 SADify Data Model And Output Schema](development/03_data_model_and_output_schema.md)
- [2026-04-30 SADify Google Cloud Setup Runbook](development/04_google_cloud_setup_runbook.md)
- [2026-04-30 SADify Development Workflow](development/05_development_workflow.md)
- [2026-05-02 SADify Demo Script And Acceptance Checklist](development/06_demo_script_and_acceptance_checklist.md)
- [2026-05-02 SADify Decision Log](development/07_decision_log.md)
- [2026-05-02 SADify New Chat Handoff](development/08_new_chat_handoff.md)
- [2026-05-04 SADify Model Provider Linkage](development/11_model_provider_linkage.md)
- [2026-05-13 SADify Cloud Credit Consuming Services](development/13_cloud_credit_consuming_services.md)
- [2026-05-14 SADify Q&A Workflow Refinement](development/14_qna_workflow_refinement.md)
- [2026-05-24 TC-028 Evidence-Based Readiness](testing/test_cases/TC-028-evidence-based-readiness.md)
- [2026-05-11 TC-026 MVP Drive Docs Save](testing/test_cases/TC-026-mvp-drive-docs-save.md)
- [2026-05-02 Track 1 Resource Link Analysis](research/2026-05-02-track-1-resource-link-analysis.md)
- [2026-04-30 SADify Test Case Index](testing/test_case_index.md)
- [2026-04-29 SADify Google Cloud MVP Plan](plans/2026-04-29-sadify-google-cloud-mvp-plan.md)
- [2026-04-29 SADify Architecture Diagram](diagrams/2026-04-29-sadify-architecture.md)

## Source Context

- `docs/Google for Startups AI Agents Challenge.md`
- `docs/Google Cloud Hackathon (Req -_ SAD agent).md`
- `docs/sources/ai_agents_challenge_designed_guide.pdf`
- `docs/superpowers/research/2026-05-02-track-1-resource-link-analysis.md`

## Traceability Rule

Every current planning, development, architecture, and testing document should include a `Traceability Sources` section or be listed as a source context document here.

When a decision changes, update the source document first, then update any linked docs that depend on it.

## Current Direction

SADify is a Track 1 net-new AI agent for the Google for Startups AI Agents Challenge.

The prototype and MVP should use Google Cloud only where it helps the prototype and demo:

- Gemini on Vertex AI as the default reasoning and generation route
- Provider-neutral model routing for requirement analysis, final SAD generation, and optional fallback
- Google ADK for agent structure
- Manual ADK-compatible scaffold selected for the MVP
- Agent Starter Pack as background reference only
- Cloud Run for demo deployment when ready; prototype uses one service, proper MVP targets two services
- Next.js/React frontend and FastAPI backend for the proper MVP
- Firebase Auth / Google Identity Platform for persistent sign-in
- Firestore for canonical structured JSON, accessed through the backend for MVP
- Secret Manager for secrets
- User-owned Google Drive project repo selected/created through OAuth
- Google Docs SAD, wiki Markdown, and source files as the first MVP save path
- PDF and DOCX after the core Drive/Docs save path is stable
- Obsidian-compatible Markdown wiki files as the connected requirement knowledge layer
- MCP-compatible tool actions where practical

The most current development references are the minimum-token packet in `CURRENT.md`. The older 2026-04-29 plan remains useful background, but the development docs and architecture diagram are the source of current decisions. Completed or superseded implementation plans are consolidated under `docs/superpowers/archive/` and should be treated as historical traceability only.

Current implementation state:

- Streamlit prototype checkpoints 1 through 15 are complete, including basic deployed Cloud Run smoke.
- Prototype live Gemini calls, Firestore cloud writes, Drive/Docs upload, and Cloud Run log-admin checks remain backlog after the baseline.
- Proper MVP worktree: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`.
- Proper MVP branch: `codex/mvp-monorepo-scaffold`.
- MVP-00 through MVP-09 passed.
- TC-019 live Firebase Google sign-in and backend ID-token verification passed locally on 2026-05-13.
- TC-020 local fake-store guest draft migration passed on 2026-05-13; real Firestore cloud persistence remains deferred.
- TC-021 live Gemini structured Q&A passed locally on 2026-05-13 after Vertex AI User was granted to the Firebase Admin SDK service account.
- TC-022 local source upload traceability passed on 2026-05-13; real Firestore/Drive source persistence remains deferred.
- TC-023 local Drive repo OAuth contract passed on 2026-05-14; live OAuth exchange, Secret Manager token storage, Drive writes, and Picker remain deferred.
- TC-024 local SAD preview and IT readiness passed on 2026-05-14; Drive/Docs save remains deferred.
- TC-028, Cycle 2A, Cycle 2B, and the no-repeat Guard B fix completed Phase 4 on 2026-05-24. Manual laundry and event-rental PDF smokes reached 100% readiness with monotonic score, clean provenance buckets, full 10-section SAD output, source refs, and no repeated questions.
- Phase 5 is active: TC-026 Drive + Google Docs save path. TC-025 wiki update approval and TC-027 two-service deploy are blocked until TC-026 passes.

## Active Execution Chain

For the current Drive/Docs save path, use this sequence:

```text
Acceptance test:
  testing/test_cases/TC-026-mvp-drive-docs-save.md

Related contract:
  testing/test_cases/TC-023-mvp-drive-repo-oauth.md

Cloud setup:
  development/04_google_cloud_setup_runbook.md
```

Historical readiness and rescan snapshots remain available, but they are not
part of the active reading path:

```text
archive/development/consolidated-development.md
```
