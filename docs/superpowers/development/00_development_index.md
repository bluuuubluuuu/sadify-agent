# SADify Development Index

Date: 2026-04-30  
Last updated: 2026-05-24

## Purpose

This is the starting point for SADify development. It keeps the project direction, current status, and next steps clear for solo development and for explaining the build in a demo video.

## Traceability Sources

This index should be verified against:

- `docs/superpowers/README.md`
- `docs/superpowers/research/2026-05-02-track-1-resource-link-analysis.md`
- `docs/sources/ai_agents_challenge_designed_guide.pdf`
- `docs/Google for Startups AI Agents Challenge.md`
- `docs/Google Cloud Hackathon (Req -_ SAD agent).md`

When another document becomes the current source of truth, add it to `Current Reference Docs` below.

## Current Status

```text
Prototype baseline:
  Complete, including deployed Cloud Run smoke.

Active MVP workspace:
  D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
  branch: codex/mvp-monorepo-scaffold

Passed MVP gates:
  MVP-00 through MVP-09, Phase 3 stabilization, Phase 4 SAD synthesis.

Active checkpoint:
  Phase 5 / TC-026 Drive + Google Docs save path

Current status:
  Phase 4 complete. TC-028 evidence-based readiness, Cycle 2A
  (monotonic readiness + applicability stickiness + merged
  slot_evidence persistence), and Cycle 2B (section coverage,
  assumptions/open-questions population, paraphrasing, understanding
  summary preservation) all shipped and verified by manual browser
  smoke on 2026-05-24. Anti-repetition Guard B tightened to threshold
  2 — no question is ever asked a third time. The SAD preview now
  surfaces all cleared categories with paraphrased prose and a
  preserved understanding summary.

Active focus:
  TC-026 Drive / Google Docs save path — turn the in-memory SAD
  preview into a real saved artifact in the user's connected Drive
  folder. Live OAuth, Secret Manager, Drive write, Docs write.

Blocked until TC-026 passes:
  TC-025 wiki update approval
  TC-027 two-service Cloud Run deploy
```

## Phase-Based Navigation

| Phase | Scope | Status | Open when |
| --- | --- | --- | --- |
| Phase 0 | Original planning and challenge context | Complete; retained for traceability | Explaining Track 1 fit or revisiting product direction |
| Phase 1 | Streamlit prototype baseline | Complete through basic Cloud Run smoke | Checking prototype behavior or older checkpoint evidence |
| Phase 2 | Proper MVP scaffold and full-stack foundation | MVP-00 through MVP-09 passed | Understanding Next.js/FastAPI/Auth/Gemini/source/Drive/SAD preview foundation |
| Phase 3 | Q&A workflow stabilization | Complete (TC-021S, TC-021T passed; TC-021R..Y superseded by TC-028 — archived) | Reading carry-forward / ratchet / provenance history |
| Phase 4 | SAD preview and SAD quality stabilization | Complete (TC-028 + Cycles 2A/2B passed 2026-05-24) | Understanding the readiness model, Guards A/B, SAD synthesis prompt |
| Phase 5 | Drive + Google Docs save path | Active (TC-026 is the current focus) | Current work |
| Phase 6 | Wiki update approval + two-service deploy | Not started (TC-025 + TC-027 blocked on TC-026) | After Phase 5 lands |

For current work, the reader should not start from every historical plan. Start with the short list below, then open older docs only when a linked decision or evidence trail is needed.

Recent verified milestones:

- TC-019 live Firebase Google sign-in passed on 2026-05-13.
- TC-020 local fake-store guest draft migration passed on 2026-05-13.
- TC-021 live Gemini structured Q&A passed on 2026-05-13.
- TC-022 source upload traceability passed on 2026-05-13.
- TC-023 local Drive repo OAuth contract passed on 2026-05-14.
- TC-024 local SAD preview and IT readiness passed on 2026-05-14.
- TC-021R improved the Q&A flow locally, then was superseded by TC-021S after manual continuity testing exposed deeper drift.
- TC-028 evidence-based readiness manual smoke passed on 2026-05-24, after the prior TC-021R..Y cascade had been folded into a single evidence-driven model.
- Cycle 2A (monotonic readiness, sticky applicability, merged slot_evidence persistence) shipped on 2026-05-24.
- Cycle 2B (section coverage, assumptions/open-questions, paraphrasing, understanding-summary preservation) shipped on 2026-05-24. Manual browser smoke on laundry + event-rental PDFs both reached 100% readiness with monotonic score, clean buckets, full 10-section SAD output, no question repetition.

## Project Summary

SADify is a Track 1 net-new AI agent for the Google for Startups AI Agents Challenge.

SADify helps production or on-site teams describe messy business requirements in natural language. It asks clarification questions, checks requirement completeness, and generates a structured System Analysis and Design document for IT teams.

The core value is not simply generating a SAD document. The core value is making the agent behave like a system analyst: clarify first, validate completeness, then produce developer-ready output.

## MVP Flow

```text
Messy production requirement or business files
  -> SADify extracts requirement context
  -> SADify asks clarification questions
  -> SADify tracks question-area status and overall draft readiness
  -> SADify generates a coherent first SAD draft
  -> SADify continues into deeper IT-readiness refinement
  -> SADify builds connected requirement knowledge
  -> SADify generates stronger SAD revisions
  -> SADify exports SAD documents and wiki Markdown files
```

## Current Technical Direction

| Area | Decision |
| --- | --- |
| Frontend | Prototype: Streamlit. MVP target: Next.js/React workspace UI |
| Agent framework | Google ADK |
| Default model platform | Vertex AI Gemini |
| Default model | `gemini-2.5-flash` |
| Model routing | Provider-neutral backend interfaces. Gemini active first; model switching is future priority 1 |
| Supported provider bases | Google, OpenAI, Anthropic, OpenAI-compatible endpoint, Ollama, Hugging Face |
| Backend | MVP target: Python FastAPI backend reusing current Python services where practical |
| Auth | MVP target: Firebase Auth / Google Identity Platform |
| Deployment | Prototype: one Cloud Run service. MVP target: two Cloud Run services, frontend and backend |
| Agent platform compatibility | ADK-compatible agent core, Agent Runtime as stretch |
| Scaffold/eval helper | Manual ADK-compatible scaffold selected; revisit Agents CLI later only if useful |
| Legacy template reference | Agent Starter Pack is background only |
| Storage | Firestore Native Mode, accessed through backend only |
| Secrets | Secret Manager |
| Canonical data | Structured JSON in Firestore |
| Human knowledge layer | Obsidian-compatible Markdown wiki |
| First MVP exports | Google Docs SAD, wiki Markdown files, raw/source files |
| Later normal exports | PDF and DOCX after Drive/Docs wiring is stable |
| File placement | User-owned Google Drive project repo selected or created through OAuth |
| Region | `asia-southeast1` |

## Current Reference Docs

Read these first for normal work:

1. `CLAUDE.md`
2. `context.md`
3. `docs/superpowers/CURRENT.md`
4. `docs/superpowers/development/00_development_index.md`
5. `docs/superpowers/testing/test_cases/TC-026-mvp-drive-docs-save.md`
6. `docs/superpowers/development/04_google_cloud_setup_runbook.md`

Open these for broader context, conflict resolution, or cross-checking:

1. `docs/superpowers/testing/test_cases/TC-023-mvp-drive-repo-oauth.md`
2. `docs/superpowers/development/07_decision_log.md`
3. `docs/superpowers/development/05_development_workflow.md`
4. `docs/superpowers/development/08_new_chat_handoff.md`
5. `docs/superpowers/development/14_qna_workflow_refinement.md`
6. `docs/superpowers/testing/test_case_index.md`
7. `docs/superpowers/testing/mvp_web_app_test_plan.md`

Use these only when the task touches their topic:

- `docs/superpowers/development/04_google_cloud_setup_runbook.md`
- `docs/superpowers/development/11_model_provider_linkage.md`
- `docs/superpowers/development/13_cloud_credit_consuming_services.md`
- `docs/superpowers/testing/mvp_web_app_test_plan.md`
- `docs/superpowers/diagrams/2026-04-29-sadify-architecture.md`
- `docs/superpowers/specs/2026-05-11-sadify-prototype-to-mvp-design.md`
- `docs/superpowers/research/2026-05-02-track-1-resource-link-analysis.md`
- `docs/Google for Startups AI Agents Challenge.md`
- `docs/Google Cloud Hackathon (Req -_ SAD agent).md`

The 2026-04-29 Google Cloud MVP plan is useful background, but the dated
development docs above are the current source of decisions. Historical readiness
and repository snapshots are available in `docs/superpowers/archive/development/`.
Completed or superseded implementation plans/specs are consolidated under
`docs/superpowers/archive/` and should be treated as historical evidence only.
The active execution reference is the TC-026 acceptance test plus the Drive/OAuth
contract from TC-023.

## Development Doc Map

This table separates active development references from archived snapshots so the
normal reading path stays short.

| Order | Document | Purpose | Status |
| --- | --- | --- | --- |
| 00 | `00_development_index.md` | Start-here map, current status, next step | Created |
| 01 | `01_product_scope.md` | MVP scope, users, success criteria, not-MVP list | Created |
| 02 | `02_agent_behavior_contract.md` | Exact SADify behavior rules and completeness gate | Created |
| 03 | `03_data_model_and_output_schema.md` | Firestore model and generated SAD schema | Created |
| 04 | `04_google_cloud_setup_runbook.md` | Console/CLI setup for APIs, IAM, Firestore, Drive, deploy | Created |
| 05 | `05_development_workflow.md` | Local coding order and verification checklist | Created |
| 06 | `06_demo_script_and_acceptance_checklist.md` | Demo flow, acceptance criteria, recording checklist | Created |
| 07 | `07_decision_log.md` | Why major architecture/product choices were made | Created |
| 08 | `08_new_chat_handoff.md` | Portable handoff prompt and project snapshot for new chats/tools | Created |
| 09-10,12 | `../archive/development/consolidated-development.md` | Historical readiness and repo-rescan snapshots | Archived |
| 11 | `11_model_provider_linkage.md` | Flexible model-provider route decision and adapter plan | Created |
| 13 | `13_cloud_credit_consuming_services.md` | Dedicated list of services that can consume cloud credits and how to control them | Created |
| 14 | `14_qna_workflow_refinement.md` | Active Q&A behavior note for the stable questionnaire refactor | Active |

## Active Work Linkage

```text
Active checkpoint:
  Phase 5 / TC-026 Drive + Google Docs save path

Acceptance test:
  docs/superpowers/testing/test_cases/TC-026-mvp-drive-docs-save.md

Related Drive/OAuth contract:
  docs/superpowers/testing/test_cases/TC-023-mvp-drive-repo-oauth.md

Cloud setup:
  docs/superpowers/development/04_google_cloud_setup_runbook.md

Current status:
  Phase 4 is complete. TC-028, Cycle 2A, Cycle 2B, and the no-repeat Guard B
  fix passed manual browser smoke on 2026-05-24 with laundry and event-rental
  PDFs. The next work is to convert the temporary SAD preview into a saved
  user-owned Google Drive/Docs artifact.

Next action:
  Align TC-026 with the current phase ordering, then implement the save path
  local-first. Do not perform live OAuth, Drive, Docs, Secret Manager, or deploy
  operations without explicit user approval.
```

## Before Executing Any Plan

Use this rule for every future plan, not only the current Q&A work:

```text
1. Open the behavior note, design spec, implementation plan, acceptance test,
   linked schema/data-model docs, linked decision entries, current code, and
   current tests.
2. Confirm the plan/spec/test chain agrees with the current project status.
3. Check the current git/worktree state before editing.
4. If the work touches external APIs or cloud services, re-check current official
   docs before coding.
5. Record any contradiction, stale wording, missing link, setup gap, or open risk.
6. Align the docs first, then begin implementation only when the packet is coherent.
```

For the current active checkpoint, the packet is:

```text
acceptance    -> TC-026-mvp-drive-docs-save.md
drive contract -> TC-023-mvp-drive-repo-oauth.md
cloud runbook -> 04_google_cloud_setup_runbook.md
schema note   -> 03_data_model_and_output_schema.md
decision log  -> 07_decision_log.md
```

## Immediate Next Step

Pre-development readiness has been checked:

```text
docs/superpowers/archive/development/consolidated-development.md
```

Completed setup:

```text
1. Confirmed project `sadify`.
2. Enabled required APIs.
3. Created runtime service account.
4. Granted required IAM roles.
5. Created Firestore Native Mode database in `asia-southeast1`.
6. Created Google Drive export folder.
7. Shared the Drive folder with the service account as Editor.
8. Saved Drive folder ID in local `.env`.
9. Confirmed local `.venv` with ADK, Streamlit, pytest, and extraction dependencies.
10. Selected manual ADK-compatible scaffold.
```

Completed implementation checkpoints:

```text
1. Streamlit shell.
2. Runtime diagnostics/logging foundation.
3. ADK-compatible `root_agent`.
4. Provider-neutral model routing foundation with Gemini default.
5. Requirement text input and deterministic first-response UI.
6. Business-first UI language foundation for requester-facing analysis.
7. Business file extraction for MD, TXT, PDF, DOCX, XLSX, and CSV.
8. Canonical JSON schema validation for the six MVP records in TC-003.
9. Local-first Firestore persistence repository for the six canonical record types.
10. Local completeness + confidence scoring with visible scoring evidence and short-input caps.
11. Local deterministic relationship linking / knowledge graph records for requirements, actors, entities, workflows, reports, decisions, and sources.
12. Local deterministic wiki Markdown renderer with YAML frontmatter, wiki links, folder paths, questions, assumptions, and broken-link protection.
13. Local deterministic wiki verification and owner approval state transitions.
14. Local deterministic project-level SAD generation with structured sections, Markdown preview, source traceability, open questions, assumptions, and developer tasks.
15. Local export generation for Google-Doc-import HTML, PDF, DOCX, wiki Markdown artifacts, and canonical export records.
16. Local end-to-end workflow from requirement analysis through graph, wiki approval, SAD, export package, diagnostics, and repository persistence.
17. Local test suite passing. Latest alignment review on 2026-05-11: 89 tests passed and Streamlit health returned 200 ok.
18. Cloud Run deployment complete for the Streamlit service.
19. Basic deployed Cloud Run smoke passed: health endpoint returned 200 ok and Playwright verified deterministic warehouse requirement analysis on the deployed URL.
20. MVP-00 prototype-to-MVP design alignment passed.
21. MVP-01 monorepo scaffold passed in `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`.
22. MVP-02 FastAPI health/config/typed API contract passed.
23. MVP-03 Next.js mocked workspace shell passed with local browser smoke.
24. MVP-04 Firebase Auth/session passed locally. TC-019 live Google sign-in and backend Firebase ID-token verification returned `/auth/session` 200 OK on 2026-05-13.
25. MVP-05 guest draft migration passed locally with backend fake-store draft creation, safe signed-in project copy contract, DraftPanel UI, and browser smoke. Real Firestore cloud persistence is deferred.
26. MVP-06 structured Q&A passed with backend schema/parser/route/Gemini adapter, retry/refuse validation, frontend AnalysisPanel, TypeScript, production build, and one live Gemini schema-valid smoke through `/analysis/requirement`.
27. MVP-07 source upload traceability passed with FastAPI multipart upload, local source extraction/storage, traceability units, unsupported-file errors, source context/reference handoff into analysis, SourceUploadPanel, full tests, TypeScript, production build, local API smoke, and browser smoke.
28. MVP-08 Drive repo OAuth contract passed locally with signed-in-only backend repo grant routes, planned project repo folder structure, `drive.file` scope intent, config-aware Google Identity Services authorization-code UI, disconnect save blocking, full tests, TypeScript, production build, and browser smoke.
29. MVP-09 SAD preview and IT readiness passed locally with `/sad/preview`, temporary `SP-` preview state, blocking-basics gate, structured SAD preview schema, IT readiness checklist, assumptions, open questions, source refs, change tracking, SadPreviewPanel UI, full tests, TypeScript, production build, local rendered smoke, and later manual live local preview smoke.
30. Post-MVP-09 stabilization fixed the Q&A answer loop: choice selection or amendment text now sends the previous question/answer back into `/analysis/requirement`, refreshes the next Gemini question, updates tracking status, and avoids dead clickable buttons in the read-only tracking card.
31. Follow-up Q&A logic stabilization fixed fallback questionnaire flow: top-level fallback categories are single-select and disabled after answered, category follow-ups can be multi-select when useful, `I'm not sure` routes to easier suggested-default follow-ups, `Other / not listed` requires details, and repeated fallback clicks no longer inflate readiness.
32. Manual Q&A testing then exposed a larger UX/design issue: user-facing percentages mix Gemini readiness and fallback readiness, confidence appears like a status score, and fallback can bounce the user from a category-specific question back to a top-level menu. `14_qna_workflow_refinement.md` now defines the target category-first Q&A flow.
33. MVP-09.1 / TC-021R improved the Q&A flow locally, but manual testing showed category drift still remains.
34. MVP-09.2 / TC-021S stable questionnaire plan refactor passed the manual clinic rerun on 2026-05-18.
35. MVP-09.3 / TC-021T passed functionally on 2026-05-18: ready-state UI rendered and live `/sad/preview` returned `200`.
36. The same live clinic smoke exposed a new quality blocker before MVP-10: generated SAD output still conflicted with Q&A readiness and did not yet merge source requirements plus confirmed answers into one trustworthy analysis.
37. TC-021U then fixed the route-safety part of that blocker: invalid Gemini
structured preview output now saves a safe local fallback preview instead of
returning `502`.
38. Manual video smoke on 2026-05-19 proved fallback transport works but exposed
the next SAD-quality blocker: fallback preview content still needed clean request
boundaries and structured answer-to-section synthesis.
39. TC-021W automated checks passed those fallback presentation guardrails, but
the 2026-05-20 workshop manual smoke failed progression because Q&A questions
and preset answers remained too broad, and the valid preview still showed
`60% Low confidence` plus visible IT readiness after Q&A reached `100%`.
```

Current stop point:

```text
1. Phase 4 is complete.
2. Continue with TC-026 Drive + Google Docs save path.
3. Keep the first TC-026 implementation local/fake-store until the save contract is stable.
4. Do not start TC-025 wiki update approval or TC-027 deployment until TC-026 passes.
5. Do not perform live Drive/Docs/Secret Manager writes without explicit user approval.
```

## Demo Explanation Anchor

Use this sentence when explaining the project:

> SADify is an AI system analyst that helps non-technical production teams turn real operational problems into clarified, complete, developer-ready System Analysis and Design documents.

Use this sentence when explaining the difference from generic AI:

> Generic AI often jumps straight to a solution. SADify first checks what information is missing, asks structured clarification questions, and only generates the SAD once the requirement is complete enough.

## Open Questions

- Will the live requirement-analysis implementation call pure ADK immediately, or use a thin model-router adapter that stays ADK-compatible?
- TC-023 preflight selected Google Identity Services authorization code flow and `drive.file` as the first Drive scope intent; Docs scope and least-privilege Secret Manager token-store roles still need verification before real Drive/Docs save.
- What exact first demo scenario should be used for the vertical slice?
- Should the user create a smaller project-only <prototype-budget> prototype budget before heavy model/deploy loops?
- Has any new Google Cloud service/tool been added to the runbook before use?
- Should PDF/DOCX return immediately after the first SAD Google Doc + wiki + sources save path, or wait until the core MVP is fully deployed?
- What exact OAuth client secret/token exchange and secure token-store implementation should be used before real Drive/Docs writes?
