# SADify Agent Coding Instructions

Date: 2026-05-08  
Status: Active root instruction file
Last updated: 2026-07-20

## Purpose

This file is the top-level behavior guide for coding agents working on SADify, including Codex, Claude Code, or any other assistant.

It defines how to work in this repo without losing context, weakening code quality, making unsafe assumptions, or drifting away from the product plan.

SADify began as a Google for Startups AI Agents Challenge Track 1 entry. That
challenge closed on 2026-06-05. SADify is now being developed as a product, not
a submission. Hackathon framing in older docs is historical context, not a
current constraint. Judging criteria, demo-script deadlines, and
submission-readiness gates no longer drive priority.

For functional architecture and build notes, read `context.md`.

## Traceability Sources

This instruction file should be verified against:

- `context.md`
- `docs/superpowers/README.md`
- `docs/superpowers/CURRENT.md`
- `docs/superpowers/development/00_development_index.md`
- `docs/superpowers/development/01_product_scope.md`
- `docs/superpowers/development/02_agent_behavior_contract.md`
- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `docs/superpowers/development/04_google_cloud_setup_runbook.md`
- `docs/superpowers/development/05_development_workflow.md`
- `docs/superpowers/development/07_decision_log.md`
- `docs/superpowers/development/08_new_chat_handoff.md`
- `docs/superpowers/archive/development/09_pre_development_readiness_checklist.md`
- `docs/superpowers/archive/development/10_pre_implementation_checkpoint.md`
- `docs/superpowers/development/11_model_provider_linkage.md`
- `docs/superpowers/archive/development/12_repo_rescan_alignment_checkpoint.md`
- `docs/superpowers/development/13_cloud_credit_consuming_services.md`
- `docs/superpowers/development/14_qna_workflow_refinement.md`
- `docs/superpowers/testing/mvp_web_app_test_plan.md`
- `docs/superpowers/testing/test_cases/TC-036-github-issue-relaunch.md`

If coding behavior, source priority, cloud guardrails, or documentation rules change, update this file and the decision log together.

## Required First Read

Before coding, changing docs, enabling cloud services, or choosing tools, read
the minimum current packet first:

1. `context.md`
2. `docs/superpowers/CURRENT.md`
3. The active checkpoint plan and test named in `CURRENT.md`
   - current active plan: `docs/superpowers/plans/2026-06-19-github-issue-relaunch.md`
   - current active test: `docs/superpowers/testing/test_cases/TC-036-github-issue-relaunch.md`
4. The specific source doc for the work being changed:
   - product scope: `docs/superpowers/development/01_product_scope.md`
   - agent behavior: `docs/superpowers/development/02_agent_behavior_contract.md`
   - data/schema/output: `docs/superpowers/development/03_data_model_and_output_schema.md`
   - cloud/tools/billing: `docs/superpowers/development/04_google_cloud_setup_runbook.md`
   - implementation workflow: `docs/superpowers/development/05_development_workflow.md`
   - demo behavior: `docs/superpowers/development/06_demo_script_and_acceptance_checklist.md`
   - tests: `docs/superpowers/testing/test_case_index.md`

Use `docs/superpowers/README.md`, `docs/superpowers/development/00_development_index.md`,
`docs/superpowers/development/07_decision_log.md`,
`docs/superpowers/development/05_development_workflow.md`, and
`docs/superpowers/development/08_new_chat_handoff.md` when the current brief is
stale, a broader checkpoint decision is needed, or documents conflict.

Archived readiness and rescan snapshots live under `docs/superpowers/archive/development/`; read them only when investigating historical setup decisions. If this is a fresh conversation, also read `docs/superpowers/development/08_new_chat_handoff.md`.

## Source Priority

When documents disagree, use this order:

1. `docs/superpowers/development/07_decision_log.md`
2. `docs/superpowers/development/00_development_index.md`
3. Current dated docs in `docs/superpowers/development/`
4. `docs/superpowers/research/2026-05-02-track-1-resource-link-analysis.md`
5. `docs/superpowers/plans/2026-04-29-sadify-google-cloud-mvp-plan.md`
6. Raw source clippings in `docs/`

Do not silently choose between conflicting docs. State the conflict, use the priority order, and update the affected docs if the user approves the change.

## Current Project Status

The MVP is built, tested, and deployed. All six original phases are closed:
five completed, one (Phase 4) superseded rather than passed.
Current work is the post-hackathon product restructure (Approach B, agreed
2026-07-20): repo hygiene first, then the two unbuilt MVP exports, then a
first-run path for a user who is not the author.

Phase map:

```text
Phase 0 - Original planning / challenge context: complete; historical source material retained.
Phase 1 - Streamlit prototype baseline: complete through Cloud Run smoke.
Phase 2 - Proper MVP scaffold and full-stack foundation: MVP-00 through MVP-09 passed.
Phase 3 - Q&A workflow stabilization: TC-021R superseded; TC-021S and TC-021T passed.
Phase 4 - SAD preview and SAD quality stabilization: superseded. The TC-021 R-Y
          cascade is consolidated into docs/superpowers/archive/. TC-021Y never
          recorded a manual-smoke pass; the keyword/phrase readiness approach it
          was hardening was replaced by TC-028 evidence-based readiness, which
          passed on 2026-05-24 (decision log, 2026-05-23).
Phase 5 - Wiki/Drive/Docs save path: complete. TC-025A snapshot, TC-025B
          encyclopedia wiki, TC-026 local save, TC-026B live Drive/Docs,
          TC-026D project isolation, TC-026E save history all passed.
Phase 6 - Deployment: complete. TC-027 two-service Cloud Run deploy passed on
          2026-06-03 with a 7-case production smoke.
Phase 7 - Post-MVP hardening: TC-029 analysis reset, TC-030 Firestore
          persistence, TC-031 readiness semantics, D-092 UI redesign,
          TC-032 model picker, TC-034 ADK analyst agent, TC-036 GitHub issue
          relaunch. All implemented; TC-036 live smoke is still pending.
Phase 8 - Product restructure (ACTIVE, from 2026-07-20): see below.
```

Current stop point:

```text
Worktree: D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
Branch:   codex/mvp-monorepo-scaffold  (14 commits ahead of main)
Last commit: 2026-06-19.

Verified state at that commit:
  652 passed, 4 skipped (pytest)
  npx tsc --noEmit passed
  npm run build passed

Deployed state (STALE - predates the last 14 commits):
  sadify-api  -> sadify-api-00005-pc2   (2026-06-04)
  sadify-web  -> sadify-web-00002-vzw   (2026-06-04)
  Region asia-southeast1, runtime SA sadify-agent-sa, scale-to-zero.

Known open items:
  TC-036 live recovery smoke not run (needs throwaway GitHub PAT).
  PDF export not built. DOCX export not built. Both are stated MVP
    success criteria in 01_product_scope.md.
  No CI. Every deploy is a manual gcloud run deploy.
  Dangling stash on main; 5 untracked test-source files in tests/.
```

Phase 8 order of work (agreed 2026-07-20):

```text
8.1  Repo hygiene: correct the stale docs, merge the worktree branch into
     main, retire hackathon-era gates, deploy the 14 unshipped commits,
     add CI over the existing 652 tests + tsc + build.
8.2  Close the MVP promise: PDF export, DOCX export.
8.3  First-run path so a user who is not the author can reach a SAD.
```

Deliberately NOT in scope for Phase 8, and why:

```text
Async invite flow (developer invites the requester to answer). Likely the
  right long-term shape - the person who wants the SAD is not currently the
  person who does the work - but it rests on an untested premise. Validate
  with a real user before building.
Cross-project wiki memory. The strongest compounding asset in the product;
  today the wiki is per-project so nothing accumulates. Deferred with the
  same reasoning.
```

Current repo content (root):

```text
CLAUDE.md
context.md
README.md
Dockerfile          (backend image, built with --source .)
Procfile            (Streamlit-era; verify before reuse)
pyproject.toml
requirements.txt
requirements-dev.txt
apps/               (Next.js frontend)
services/api/       (FastAPI backend)
services/mcp/       (standalone stdio MCP server)
sadify_agent/       (ADK-compatible root_agent path)
src/sadify/         (prototype-era agent core)
docs/
tests/
```

Current MVP worktree content:

```text
.worktrees/mvp-monorepo-scaffold/
  apps/web/
  services/api/
  tests/
```

Private local files such as `.env` and `.venv/` must stay ignored by git.

Before resuming work, recheck the worktree status and the matching test case. Do
not run model-heavy loops until cost risk is explicitly accepted.

Note on the model baseline below: the "prototype frontend: Streamlit" line is
historical. Streamlit is the Phase 1 prototype, superseded by the Next.js app in
`apps/web`. Do not build new UI in Streamlit.

## Project Baseline

SADify is an AI system analyst that turns messy operational requirements into
developer-ready System Analysis and Design documents. It was built as a Track 1
net-new agent for the Google for Startups AI Agents Challenge; it is now a
product under continued development.

Core promise:

```text
SADify helps non-technical production/on-site users turn messy operational problems into clarified, complete, developer-ready System Analysis and Design documents.
```

Main differentiator:

```text
SADify must clarify, score completeness/confidence, expose gaps, and preserve source traceability before generating final-looking output.
```

## Non-Negotiable Product Rules

- Keep SADify cross-domain. Agriculture/plantation may inspire a demo later, but do not lock the product to that domain.
- Support normal business files in the MVP: typed text, Markdown, TXT, PDF, DOCX, XLSX, and CSV.
- Keep user-facing copy business-first. The app should say things like "what we still need to know" and "questions to confirm with the business", while technical categories such as actors, workflow, data fields, approvals, permissions, and constraints remain internal structure for SAD generation.
- Treat image support, voice input, advanced diagrams, multi-user collaboration, and full project management as future or premium potential unless the decision log changes.
- Keep basic trust features available: clarification questions, missing info, completeness/confidence, version history, basic exports, and source traceability.
- Do not make core trustworthy behavior premium-only.
- GitHub Issues export is stretch only after core exports work.

## Coding Behavior Rules

- Read existing docs and code before editing.
- Prefer the repo's existing architecture and naming once implementation exists.
- Keep edits scoped to the requested task and related source docs.
- Ask before changing scope, cloud services, pricing, demo scenario, or implementation strategy.
- Do not make assumptions when the answer is missing and risky. Ask the user or mark the item as pending.
- If a reasonable default is documented, follow it and mention the source.
- Do not overbuild. Build checkpoint by checkpoint from `05_development_workflow.md`.
- Keep the agent core separate from the Streamlit UI.
- Keep tool actions clean and MCP-compatible where practical.
- Do not hide important logic inside UI-only code if it needs to be tested through the agent core.
- Do not add unrelated refactors while implementing a checkpoint.
- Do not commit real secrets, keys, tokens, credentials, or Drive folder IDs.
- Create `.env.example` with placeholders only when scaffolding begins.

## Quality Bar

Functional features are not complete until their matching test case is updated with:

- expected output
- real output
- differences or issues
- evidence
- pass/fail/block decision

Evidence can include screenshots, command output, browser console logs, HTTP status codes, app logs, stack traces, exported file links, and network response details.

Diagnostics must be built early. Runtime errors, HTTP failures, file extraction failures, Gemini failures, Firestore failures, export failures, and schema validation failures must be visible in development logs and explained plainly to the user.

## Cloud And Billing Guardrails

The user has an overall billing-account budget guardrail around <budget-guardrail> for prototype work.

Before cloud-heavy work:

- confirm billing is attached
- prefer creating a smaller project-only prototype budget around <prototype-budget>
- treat the current <budget-guardrail> budget as a broad guardrail, not an early warning for mistakes
- enable only required APIs
- create only documented resources
- record any new cloud tool in `docs/superpowers/development/04_google_cloud_setup_runbook.md`

Do not use these for the MVP unless the decision log is reopened:

```text
GKE
Compute Engine VM
BigQuery
Cloud SQL
Dataflow
Pub/Sub
Load Balancer
GPU resources
Cloud Composer
Dataproc
Memorystore
```

Both Cloud Run services are already deployed and in production. Deployment is no
longer gated on a checkpoint; it is gated on green CI (tests + tsc + build).
Deploying a change that has not passed those three is still forbidden.

## Google Platform Baseline

Current MVP choices:

- prototype frontend: Streamlit
- MVP frontend: Next.js/React
- MVP backend: Python FastAPI
- agent framework: Google ADK
- default model platform: Vertex AI Gemini
- default model: `gemini-2.5-flash`
- model routing: provider-neutral route layer for requirement analysis, final SAD generation, and optional fallback
- runtime: prototype uses one Cloud Run service; MVP target uses two Cloud Run services, frontend and backend
- auth: Firebase Auth / Google Identity Platform; local live sign-in verified in TC-019
- canonical storage: Firestore Native Mode, backend-only for MVP
- secrets: Secret Manager
- exports: Google Docs API, Google Drive API, wiki Markdown, source files; PDF/DOCX return after core Drive/Docs path is stable
- region: `asia-southeast1`
- runtime service account: `sadify-agent-sa@sadify.iam.gserviceaccount.com`

Manual ADK-compatible scaffolding is selected. Keep the ADK-compatible `root_agent` path separate from Streamlit.

The model router may record Google, OpenAI, Anthropic, OpenAI-compatible, Ollama, and Hugging Face provider configuration, but Google/Gemini remains the default Track 1 route. Do not add live non-Google adapter calls before the requirement-analysis workflow exists and can test them against real SADify behavior.

Agent Starter Pack is background reference only. Agent Runtime / Agent Engine, Agent Evaluation, Observability, RAG/Search, Grounding, and A2A are stretch or future unless deliberately reopened.

## Documentation Update Rules

When changing product scope, update:

- `docs/superpowers/development/01_product_scope.md`
- `docs/superpowers/development/07_decision_log.md`
- related tests

When changing agent behavior, update:

- `docs/superpowers/development/02_agent_behavior_contract.md`
- schemas, workflow checkpoints, and tests

When changing data structures, exports, wiki behavior, or versioning, update:

- `docs/superpowers/development/03_data_model_and_output_schema.md`
- architecture diagram
- workflow checkpoints
- related tests

When changing cloud tools, APIs, models, IAM, billing, or deployment, update:

- `docs/superpowers/development/04_google_cloud_setup_runbook.md`
- decision log
- readiness checklist if needed
- `docs/superpowers/development/11_model_provider_linkage.md` if model routing, provider selection, or provider adapter behavior changes

When changing checkpoint order or completion rules, update:

- `docs/superpowers/development/05_development_workflow.md`
- `docs/superpowers/testing/test_case_index.md`
- matching `TC-XXX` files

Every durable planning or testing document must include date and traceability sources.

## Conversation And Question Rules

- If the user asks for planning or docs, ask clarifying questions only when the answer cannot be safely discovered from local docs.
- If the user asks for implementation, do the work after reading the relevant docs.
- If a decision is pending, do not silently decide it unless the user has already provided a preference.
- If blocked by missing cloud console state, ask for a screenshot or a short confirmation.
- If a public source may have changed, verify it before using it as a current fact.
- Keep progress updates short and specific.
- Explain tradeoffs in simple words when the user asks.

## Stop Conditions

Stop and resolve before continuing if:

- billing safety is unclear before cloud-heavy work
- scaffold path is not decided before local scaffold
- a new Google Cloud service is recommended but not added to the runbook
- canonical JSON schema becomes unclear
- source traceability is missing
- wiki overwrite protection is missing
- Firestore state model changes without schema update
- test case docs are not updated for completed checkpoints
- cloud deployment is attempted before local MVP passes

## Root File Responsibilities

Use this file for agent behavior, repo discipline, and quality rules.

Use `context.md` for architecture, dataflow, feature map, target code structure, and development checkpoints.

Do not turn either file into the full specification. Detailed decisions stay in `docs/superpowers/`.
