# SADify New Chat Handoff

Date: 2026-05-02  
Status: Active reference
Last updated: 2026-05-24

## Purpose

This document is the handoff note for starting a new chat, changing tools, or asking another AI/coding assistant to continue SADify work.

Paste or point to this file first whenever the project context may be missing.

## Traceability Sources

This handoff should be verified against:

- `docs/superpowers/README.md`
- `docs/superpowers/CURRENT.md`
- `docs/superpowers/development/00_development_index.md`
- `docs/superpowers/development/07_decision_log.md`
- `docs/superpowers/development/05_development_workflow.md`
- `docs/superpowers/development/04_google_cloud_setup_runbook.md`
- `docs/superpowers/development/11_model_provider_linkage.md`
- `docs/superpowers/development/14_qna_workflow_refinement.md`
- `docs/superpowers/testing/test_cases/TC-026-mvp-drive-docs-save.md`
- `docs/superpowers/testing/test_cases/TC-023-mvp-drive-repo-oauth.md`
- `docs/superpowers/testing/test_cases/TC-028-evidence-based-readiness.md`
- `docs/superpowers/research/2026-05-02-track-1-resource-link-analysis.md`

Archived (historical reasoning only — do not open unless tracing a
past design decision):

- `docs/superpowers/archive/plans/` and `archive/specs/`
- `docs/superpowers/archive/testing/test_cases/consolidated-test-cases.md`

If any current decision changes, update this handoff.

## One-Message Handoff Prompt

Use this prompt when opening a new chat or switching tools:

```text
You are helping me build SADify for the Google for Startups AI Agents Challenge, Track 1.

Before doing anything, read the minimum current packet in order:
1. CLAUDE.md
2. context.md
3. docs/superpowers/CURRENT.md
4. docs/superpowers/development/00_development_index.md
5. docs/superpowers/testing/test_cases/TC-026-mvp-drive-docs-save.md
6. docs/superpowers/development/04_google_cloud_setup_runbook.md

Open the decision log, Q&A behavior note, model provider linkage, and
TC-023 Drive OAuth contract only if CURRENT.md or the active test case
points there, or if a conflict needs source-of-truth resolution. The
archived TC-021R..Y cascade lives under docs/superpowers/archive/ and
should not be opened for active work.

Then summarize:
- current project status (Phase 5 — Drive/Docs save path is active)
- confirmed decisions
- pending decisions
- next safest action
- what must not be done yet (TC-025 wiki approval and TC-027 deploy
  remain blocked until TC-026 passes)

Do not assume missing details. Ask before changing scope, cloud tools, pricing, demo scenario, or implementation strategy.
```

## Project Snapshot

SADify is a Track 1 net-new AI agent.

Core promise:

```text
SADify helps non-technical production/on-site users turn messy operational problems into clarified, complete, developer-ready System Analysis and Design documents.
```

Main differentiator:

```text
Generic AI often jumps straight to a solution.
SADify first checks missing information, asks structured clarification questions,
tracks stable question-area status and overall readiness, generates a coherent
first SAD draft, then continues into deeper IT-readiness refinement before the
MVP is considered complete.
```

Current status:

```text
Documentation and planning are ready.
Implementation has started.
Cloud setup is ready for careful cloud-connected development.
Manual ADK-compatible scaffold is selected.
Local Python environment is ready.
Checkpoint 1 local scaffold is complete.
Checkpoint 2 diagnostics/logging foundation is complete.
Model provider routing foundation is complete.
Checkpoint 3 requirement text input and deterministic first-response UI is complete.
Checkpoint 4 business file extraction is complete for MD, TXT, PDF, DOCX, XLSX, and CSV.
Checkpoint 5 canonical JSON schema validation is complete for the six MVP records in TC-003.
Checkpoint 6 local-first Firestore persistence repository is complete for the six canonical record types. Real Firestore cloud smoke test has not been run yet.
Checkpoint 7 local completeness + confidence scoring is complete with transparent scoring evidence and short-input caps. No live model call was used for this checkpoint.
Checkpoint 8 local relationship linking / knowledge graph is complete for canonical requirement, actor, entity, workflow, report, decision, and source links. No live model call was used for this checkpoint.
Checkpoint 9 local wiki Markdown generation is complete for YAML frontmatter, wiki links, folder paths, open questions, assumptions, and broken-link errors. No live model call or Drive write was used for this checkpoint.
Checkpoint 10 local wiki verification and owner approval state transitions are complete for rule checks, pending review metadata, approval, and rejection. Gemini quality verification is recorded as `not_run` for this local-first slice.
Checkpoint 11 local project-level SAD generation is complete for canonical SAD versions, structured sections, Markdown preview, source traceability, open questions, assumptions, and developer tasks. SAD quality verification is recorded as `not_run` for this local-first slice.
Checkpoint 12 local export generation is complete for Google-Doc-import HTML, PDF, DOCX, wiki Markdown artifacts, and canonical export records. Real Drive/Docs upload is deferred.
Checkpoint 13 local end-to-end workflow is complete for deterministic analysis, graph, wiki approval, SAD generation, export package preparation, diagnostics, and repository persistence. Real cloud writes and live model calls remain deferred.
Checkpoint 14 Cloud Run deployment is complete for the Streamlit service.
Checkpoint 15 basic Cloud Run smoke is complete for the deployed deterministic prototype: health endpoint returned 200 ok and Playwright verified the warehouse requirement path renders understanding, readiness 100%, confidence High, and current mode deterministic.
Live Gemini calls, Firestore cloud writes, Drive/Docs upload, and Cloud Run log-admin checks are improvement backlog items after the basic prototype baseline.
The prototype-to-MVP plan has started in the isolated worktree `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold` on branch `codex/mvp-monorepo-scaffold`.
MVP-00 through MVP-09 passed: doc alignment, monorepo scaffold, FastAPI health/typed contract, mocked Next.js workspace shell, Firebase Auth/session, local guest draft migration, live Gemini structured Q&A, local source upload traceability, local Drive repo OAuth contract, and local SAD preview/IT readiness.
TC-019 live Firebase Google sign-in passed locally on 2026-05-13: backend `/auth/session` returned `200 OK`, and the UI showed the signed-in persistent session message.
TC-020 local fake-store guest draft migration passed on 2026-05-13: guest draft creation, copy-based signed-in project migration contract, and DraftPanel smoke are verified. Real Firestore cloud persistence is deferred.
MVP-06 live Gemini structured Q&A passed on 2026-05-13 after Vertex AI User was granted to firebase-adminsdk-fbsvc@sadify.iam.gserviceaccount.com: schema parser, Vertex-compatible schema helper, analysis route, retry/refuse validation, local Q&A state repository, AnalysisPanel, full Python tests, TypeScript, production build, and one live `/analysis/requirement` smoke passed.
MVP-07 local source upload traceability passed on 2026-05-13: FastAPI multipart upload, local source extraction/storage, `SRC-` IDs, traceability units, unsupported-file errors, source context/source IDs into analysis, SourceUploadPanel, full Python tests, TypeScript, production build, local API smoke, and rendered browser smoke passed. Real Firestore/Drive source persistence remains deferred.
MVP-08 local Drive repo OAuth contract passed on 2026-05-14: signed-in-only backend `/drive/repo/connect`, `/drive/repo/disconnect`, and `/drive/repo/status`, local `DG-` grant records, planned Drive repo folders (`Sources`, `SAD`, `Wiki`, `_SADify`), `drive.file` scope intent, config-aware Google Identity Services authorization-code UI, full Python tests, TypeScript, production build, and rendered browser smoke passed. Live OAuth exchange, Secret Manager token storage, real Drive writes, and Picker remain deferred.
MVP-09 local SAD preview and IT readiness passed on 2026-05-14: backend `/sad/preview`, temporary `SP-` preview state, structured SAD preview schema, blocking-basics gate, IT readiness checklist, assumptions, open questions, source refs, change tracking, SadPreviewPanel UI, full Python tests, TypeScript, production build, local rendered smoke, and later manual live local preview smoke passed. Drive/Docs save remains deferred.
Post-MVP-09 stabilization on 2026-05-14 fixed Q&A answer continuation: selecting a choice or typing an amendment enables Continue with answer, includes the previous question/answer in the next analysis request, refreshes the next Gemini question, and updates tracking status. Manual answer continuation uses one Gemini call per submitted answer.
Manual Q&A testing after stabilization found that turn-by-turn Gemini category reconstruction still causes label drift, category drift, and unstable workflow behavior. The approved replacement is the stable questionnaire-plan refactor in `development/14_qna_workflow_refinement.md`.
MVP-09.2 / TC-021S questionnaire continuity passed its manual rerun on 2026-05-18 and reached `100%`.
MVP-09.3 through MVP-09.8 captured the Q&A/SAD quality stabilization trail.
Those intermediate TC-021R..Y files are archived for historical reasoning.
TC-028 then replaced keyword/phrase readiness with quote-validated per-slot
evidence, deterministic aggregation, derived confidence, and not-applicable slot
handling. Cycle 2A fixed monotonic readiness and merged slot_evidence
persistence. Cycle 2B fixed SAD section coverage, assumptions/open-question
candidates, paraphrasing, and fallback understanding-summary preservation.
Anti-repetition Guard B now exits a slot on the second repeated answer. Manual
browser smoke on 2026-05-24 with laundry and event-rental PDFs reached 100%
readiness with monotonic scores, clean buckets, full 10-section SAD output, and
no repeated questions.
```

Phase snapshot:

```text
Phase 0 - Original planning / challenge context: complete and retained.
Phase 1 - Streamlit prototype baseline: complete through basic Cloud Run smoke.
Phase 2 - Proper MVP scaffold and full-stack foundation: MVP-00 through MVP-09 passed.
Phase 3 - Q&A workflow stabilization: TC-021S and TC-021T passed; TC-021R superseded.
Phase 4 - SAD preview and SAD quality stabilization: complete; TC-028 + Cycles 2A/2B passed.
Phase 5 - Drive + Google Docs save path: active; TC-026 is current.
Phase 6 - Wiki update approval + two-service deployment/final smoke: not started; TC-025 and TC-027 are blocked until TC-026 passes.
```

## Current Technical Direction

| Area | Current Direction |
| --- | --- |
| App UI | Prototype: Streamlit. MVP target: Next.js/React |
| Backend | MVP target: Python FastAPI |
| Agent framework | Google ADK |
| Default model platform | Vertex AI Gemini |
| Default model | `gemini-2.5-flash` |
| Model routing | Requirement analysis, final SAD, and optional fallback route metadata |
| Provider bases | Google, OpenAI, Anthropic, OpenAI-compatible endpoint, Ollama, Hugging Face |
| Deployment | Prototype: one Cloud Run service. MVP target: two Cloud Run services; current MVP work is local only |
| Canonical storage | Firestore Native Mode |
| Human knowledge layer | Obsidian-compatible Markdown wiki |
| First MVP outputs | SAD Google Doc, wiki Markdown, raw/source files |
| Later outputs | PDF and DOCX after core Drive/Docs save path is stable |
| Tool boundary | Clean Python tools, MCP-compatible later |
| Region | `asia-southeast1` |
| Credit safety | <budget-guardrail> billing-account budget with actual-spend alerts at 25%, 50%, 75%, and 90%; smaller project-only budget still recommended before heavy model/deploy loops. User reported small Cloud Run billing entries; verify exact dates/cost source before more deployments |
| Scaffold path | Manual ADK-compatible scaffold with `root_agent` |
| Local environment | Python 3.13.2, `.venv`, `pip`, `google-adk` 1.32.0, Streamlit 1.57.0, pytest 9.0.3 |

## Confirmed Do This

- Build locally first.
- Use manual ADK-compatible scaffold for MVP development.
- Keep ADK-compatible agent core separate from Streamlit UI while sharing the same underlying services where behavior overlaps.
- Use Firestore as canonical structured JSON store.
- Generate wiki Markdown from canonical data.
- Require wiki verification and owner approval before overwrite.
- Keep Cloud Run as MVP deployment path, now with separate frontend and backend services for the proper MVP.
- Keep Agent Runtime / Agent Engine as stretch unless deliberately reopened.
- Keep Google/Gemini as the default model route for Track 1.
- Keep non-Google provider adapters as future until the requirement-analysis flow can test them meaningfully.
- Use screenshots for Google Cloud Console verification.
- Keep test docs updated with expected output, real output, issues, evidence, and decision.
- Keep `.env` local and ignored; commit only `.env.example`.

## Do Not Do Yet

- Do not deploy to Cloud Run before local MVP passes.
- Do not enable extra Google Cloud services without updating the runbook.
- Do not print the real Drive folder ID or any secrets into docs or chat unless explicitly needed.
- Do not run automated model-heavy loops or repeated deployments without a smaller project-only prototype budget or explicit user approval.
- Do not add live OpenAI, Anthropic, Hugging Face, Ollama, or OpenAI-compatible calls before the Gemini MVP workflow exists and provider secrets/cost are deliberately accepted.
- Do not use GKE, VMs, BigQuery, Cloud SQL, Dataflow, Pub/Sub, GPUs, or other heavy services for MVP.
- Do not lock the product to agriculture/plantation only.
- Do not add RAG/Vertex AI Search before local file/wiki memory proves insufficient.
- Do not make core trust features premium-only.
- Do not present low-confidence SAD output as final truth.
- Do not overwrite verified wiki notes without rule check, Gemini quality check, and human approval.

## Immediate Pending Questions

Resolved before local scaffold:

```text
Devpost project path: done
Git repo initialized in D:\GoogleCloudHack
Docs/planning folders are ignored by git
Manual ADK-compatible scaffold selected
Python local environment ready
Required APIs enabled
Service account created and IAM roles granted
Firestore Native Mode created in asia-southeast1
Drive root folder created, shared with service account as Editor, and folder ID saved in local .env
```

Still pending before or during the next MVP steps:

1. Execute TC-026 Drive + Google Docs save path local-first before any wiki approval or deployment work.
2. Should the user create a smaller project-only budget around <prototype-budget> before heavy model/deploy loops?
3. What exact backend OAuth client secret/token exchange and least-privilege Secret Manager roles should be used for real user-owned Drive/Docs grant storage?
4. What exact demo scenario should be used for the first deployed vertical slice?

## New Chat First Action

The first action in a new chat should be:

```text
Read `CLAUDE.md`, `context.md`, `docs/superpowers/CURRENT.md`,
`docs/superpowers/testing/test_cases/TC-026-mvp-drive-docs-save.md`, and
`docs/superpowers/development/04_google_cloud_setup_runbook.md`, then confirm
the next action.
```

If the user wants to resume development, the next safest sequence is:

```text
1. Open D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold.
2. Recheck git status.
3. Gather the full active execution packet before coding:
   - `testing/test_cases/TC-026-mvp-drive-docs-save.md`
   - `testing/test_cases/TC-023-mvp-drive-repo-oauth.md`
   - `development/04_google_cloud_setup_runbook.md`
   - `development/03_data_model_and_output_schema.md`
   - `development/07_decision_log.md`
   - relevant current code and tests
4. Cross-check behavior note, spec, plan, test case, and code before editing.
5. If anything disagrees, align the docs or ask the user before implementation.
6. Execute TC-026 local/fake-store first.
7. Ask before live OAuth, Drive, Docs, Secret Manager, or deployment work.
8. Continue to TC-025 and TC-027 only after TC-026 passes.
9. Continue one checkpoint at a time, with API/docs preflight and checkpoint summary before moving on.
```

Manual local commands for user access:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
set "PYTHONPATH=services\api\src;src;."
D:\GoogleCloudHack\.venv\Scripts\uvicorn.exe sadify_api.main:app --host 0.0.0.0 --port 8000
```

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web
npm run build
npm run start
```

## Source Priority

When documents disagree, use this order:

1. `07_decision_log.md`
2. `00_development_index.md`
3. Current dated development docs
4. `2026-05-02-track-1-resource-link-analysis.md`
5. Older `2026-04-29` background plan
6. Raw brainstorming/source clippings

## User Collaboration Preference

Important working style:

- Ask before creating each new major doc or changing scope.
- Make decisions explicit.
- Keep dates in documents.
- Track sources and cross-links.
- Prefer safe, documented development over rushing.
- Keep billing and cleanup visible because credits are limited.
- Document expected output, real output, issues, evidence, and checkpoint status for tests.
