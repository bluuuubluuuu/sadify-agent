# SADify Project Context

Date: 2026-05-08  
Status: Active root context file
Last updated: 2026-06-19

## Purpose

This file gives coding agents a compact functional map of SADify: what the app does, how it is structured, how data moves, and where to find deeper details.

For behavior and quality rules, read `CLAUDE.md`.

## Traceability Sources

This context file should be verified against:

- `CLAUDE.md`
- `docs/superpowers/README.md`
- `docs/superpowers/CURRENT.md`
- `docs/superpowers/development/00_development_index.md`
- `docs/superpowers/development/01_product_scope.md`
- `docs/superpowers/development/02_agent_behavior_contract.md`
- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `docs/superpowers/development/04_google_cloud_setup_runbook.md`
- `docs/superpowers/development/05_development_workflow.md`
- `docs/superpowers/development/07_decision_log.md`
- `docs/superpowers/archive/development/09_pre_development_readiness_checklist.md`
- `docs/superpowers/archive/development/10_pre_implementation_checkpoint.md`
- `docs/superpowers/development/11_model_provider_linkage.md`
- `docs/superpowers/archive/development/12_repo_rescan_alignment_checkpoint.md`
- `docs/superpowers/development/13_cloud_credit_consuming_services.md`
- `docs/superpowers/development/14_qna_workflow_refinement.md`
- `docs/superpowers/testing/mvp_web_app_test_plan.md`
- `docs/superpowers/testing/test_cases/TC-026-mvp-drive-docs-save.md`
- `docs/superpowers/testing/test_cases/TC-028-evidence-based-readiness.md`
- `docs/superpowers/diagrams/2026-04-29-sadify-architecture.md`

If architecture, dataflow, feature scope, or target code structure changes, update this file and the detailed source docs together.

## Current State

SADify has a completed Streamlit functional prototype baseline and an in-progress proper MVP web app track.

Phase status:

```text
Phase 0 - Original planning / challenge context: complete; retained for traceability.
Phase 1 - Streamlit prototype baseline: complete through basic Cloud Run smoke.
Phase 2 - Proper MVP scaffold and full-stack foundation: MVP-00 through MVP-09 passed.
Phase 3 - Q&A workflow stabilization: TC-021S and TC-021T passed after TC-021R was superseded.
Phase 4 - SAD preview and SAD quality stabilization: complete. TC-028 evidence-based readiness, Cycle 2A readiness stabilization, Cycle 2B SAD synthesis, and no-repeat Q&A guard are verified.
Phase 5 - Drive + Google Docs save path: active. TC-026 is the next checkpoint.
Phase 6 - Wiki update approval and two-service deployment/final smoke: not started; blocked until TC-026 passes.
```

Prototype baseline:

```text
Streamlit deterministic prototype checkpoints 1 through 15 are complete, including Cloud Run deployment and basic Cloud Run smoke.
Live Gemini, Firestore cloud writes, Drive/Docs upload, and Cloud Run log-admin checks remain improvement backlog for the prototype baseline.
```

MVP web app track:

```text
Worktree: D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
Branch: codex/mvp-monorepo-scaffold
MVP-00 through MVP-09 passed.
TC-019 live Firebase Google sign-in and backend ID-token verification passed locally on 2026-05-13.
TC-020 local fake-store guest draft migration passed on 2026-05-13; real Firestore cloud persistence remains deferred.
TC-021 live Gemini structured Q&A passed locally on 2026-05-13 after Vertex AI User was granted to firebase-adminsdk-fbsvc@sadify.iam.gserviceaccount.com.
TC-022 local source upload traceability passed on 2026-05-13; real Firestore/Drive source persistence remains deferred.
TC-023 local Drive repo OAuth contract passed on 2026-05-14; live OAuth exchange, Secret Manager token storage, Drive writes, and Picker remain deferred.
TC-024 local SAD preview and IT readiness passed on 2026-05-14; manual live local preview smoke also passed; Drive/Docs save remains deferred.
Post-MVP-09 stabilization on 2026-05-14 fixed Q&A answer choice/amend continuation. Manual continuation uses one Gemini call per submitted answer.
MVP-09.2 through MVP-09.8 captured the Q&A/SAD quality stabilization trail and are now archived as historical evidence.
TC-028 evidence-based readiness replaces keyword and phrase tables with model-returned per-slot evidence verdicts, backend quote validation, deterministic aggregation, derived confidence, and not-applicable slot handling.
Cycle 2A fixed monotonic readiness, applicability stickiness, and merged slot_evidence persistence. Cycle 2B fixed SAD section coverage, assumptions/open-questions candidates, paraphrasing, and fallback understanding-summary preservation.
Manual browser smoke on 2026-05-24 with laundry and event-rental PDFs reached 100% readiness with monotonic score, clean buckets, full 10-section SAD output, and no repeated questions.
Current active checkpoint: TC-026 Drive + Google Docs save path. Do not start TC-025 wiki update approval or TC-027 two-service deploy until TC-026 passes.
```

Prototype root structure:

```text
README.md
pyproject.toml
requirements.txt
requirements-dev.txt
.env.example
sadify_agent/
src/sadify/
tests/
```

Private local files:

```text
.env
.venv/
```

These must stay ignored by git.

MVP worktree structure:

```text
.worktrees/mvp-monorepo-scaffold/
  apps/web/
  services/api/
  tests/
```

Historical readiness snapshots are archived at:

```text
docs/superpowers/archive/development/consolidated-development.md
```

Before changing cloud usage, also check `docs/superpowers/development/13_cloud_credit_consuming_services.md`.

## Primary References

Use these for detailed source of truth:

| Area | Reference |
| --- | --- |
| Current minimum handoff | `docs/superpowers/CURRENT.md` |
| Start here for full index | `docs/superpowers/development/00_development_index.md` |
| Decisions | `docs/superpowers/development/07_decision_log.md` |
| Product scope | `docs/superpowers/development/01_product_scope.md` |
| Agent behavior | `docs/superpowers/development/02_agent_behavior_contract.md` |
| Data model/schema | `docs/superpowers/development/03_data_model_and_output_schema.md` |
| Google Cloud setup | `docs/superpowers/development/04_google_cloud_setup_runbook.md` |
| Development workflow | `docs/superpowers/development/05_development_workflow.md` |
| Demo/acceptance | `docs/superpowers/development/06_demo_script_and_acceptance_checklist.md` |
| New chat handoff | `docs/superpowers/development/08_new_chat_handoff.md` |
| Historical pre-implementation checkpoint | `docs/superpowers/archive/development/10_pre_implementation_checkpoint.md` |
| Model provider linkage | `docs/superpowers/development/11_model_provider_linkage.md` |
| Current Q&A workflow | `docs/superpowers/development/14_qna_workflow_refinement.md` |
| Current active test | `docs/superpowers/testing/test_cases/TC-026-mvp-drive-docs-save.md` |
| Completed readiness test | `docs/superpowers/testing/test_cases/TC-028-evidence-based-readiness.md` |
| Cloud credit watch | `docs/superpowers/development/13_cloud_credit_consuming_services.md` |
| Test index | `docs/superpowers/testing/test_case_index.md` |
| Architecture diagram | `docs/superpowers/diagrams/2026-04-29-sadify-architecture.md` |
| Track 1 source analysis | `docs/superpowers/research/2026-05-02-track-1-resource-link-analysis.md` |

## Functional Goal

SADify converts messy operational requirements into clarified, structured, developer-ready System Analysis and Design output.

MVP flow:

```text
messy text or business files
  -> extract readable requirement context
  -> normalize sources
  -> analyze with SADify agent
  -> show what SADify understands
  -> show readiness and confidence
  -> list what the business still needs to confirm
  -> save canonical project knowledge
  -> link requirements, entities, workflows, decisions, actors, reports, and sources
  -> generate project-level SAD
  -> generate Obsidian-compatible wiki Markdown
  -> export Google Docs, PDF, and DOCX
```

## MVP User-Facing Features

Build only the core MVP first:

- requirement text input
- business file upload and extraction for MD, TXT, PDF, DOCX, XLSX, CSV
- standard first response: what SADify understands, readiness, confidence, what the business still needs to confirm, practical clarification questions, draft option
- completeness and confidence display
- critical gaps and open questions
- project-level SAD generation
- requirement-level cards/wiki notes
- connected wiki Markdown generation
- wiki verification and owner approval before overwrite
- Google Docs, PDF, DOCX, and wiki Markdown export
- saved project/session history
- SAD version history
- runtime diagnostics and clear errors

Not MVP:

- multi-user collaboration
- full project management system
- advanced diagram editor
- voice input
- image input
- Jira integration
- mobile app
- RAG/Search infrastructure
- Agent Runtime deployment

## Target Architecture

Runtime:

```text
Prototype:
Browser
  -> Streamlit UI
  -> application services
  -> ADK-compatible SADify agent core
  -> model router
  -> default Google Gemini route
  -> canonical JSON
  -> Firestore
  -> renderers and export tools
  -> Google Drive / Google Docs / PDF / DOCX / wiki Markdown

MVP target:
Browser
  -> Next.js/React frontend
  -> FastAPI backend
  -> Firebase Auth / Google Identity Platform
  -> backend-only Firestore access
  -> Gemini structured JSON reasoning
  -> user-owned Drive/Docs project repo through OAuth
  -> Google Docs SAD, wiki Markdown, and source files
```

The agent core must be runnable without Streamlit. Streamlit should call services; services should call the ADK-compatible agent and tool layer.

Tool boundaries should be clean enough to become MCP-compatible later. The MVP can use normal Python functions/classes first.

The model router currently supports separate route metadata for requirement analysis, final SAD generation, and optional fallback. The default route remains `google / gemini-2.5-flash`. Non-Google provider calls are not live yet.

User-facing copy should stay business-first. Technical categories can remain in services and schemas, but the Streamlit UI should avoid analyst jargon such as actors, non-functional constraints, and workflow states unless the user is viewing a developer/SAD artifact.

## Target Local Code Shape

The exact scaffold depends on the Agents CLI decision, but the local project should preserve this separation:

```text
sadify/
  pyproject.toml
  README.md
  .gitignore
  .env.example
  src/
    sadify/
      __init__.py
      app.py
      config.py
      logging_config.py
      diagnostics.py
      extractors/
      schemas/
      services/
      models/
      agents/
      tools/
      renderers/
      exporters/
  tests/
```

Expected ADK-compatible shape:

```text
sadify_agent/
  __init__.py
  agent.py
  requirements.txt
```

Expected ADK export name:

```text
root_agent
```

If Agents CLI generates a different structure, keep the same responsibilities and update this file plus the development workflow.

## Main Internal Layers

| Layer | Responsibility |
| --- | --- |
| `app.py` | Streamlit UI only: intake, upload, preview, approvals, export buttons |
| `config.py` | Environment/config loading with safe defaults and no secrets in source |
| `logging_config.py` | Structured development logging |
| `diagnostics.py` | Error display, timing/status capture, debug summaries |
| `extractors/` | MD/TXT/PDF/DOCX/XLSX/CSV extraction into normalized source context |
| `schemas/` | Canonical Pydantic/data schemas and validation |
| `services/` | Orchestration: projects, sessions, Firestore repository, versioning, exports |
| `models/` | Provider-neutral model route metadata and readiness checks |
| `agents/` | SADify analyst instructions, ADK adapter, Gemini calls |
| `tools/` | Extract, save, link, render, verify, export actions |
| `renderers/` | SAD Markdown/HTML, wiki Markdown, PDF/DOCX source rendering |
| `exporters/` | Google Docs/Drive, PDF, DOCX, wiki file output |
| `tests/` | Unit/integration tests matching documented checkpoints |

## Canonical Data Model

Firestore is the canonical source of truth.

Recommended Firestore shape:

```text
projects/{project_id}
projects/{project_id}/knowledge_items/{item_id}
projects/{project_id}/relationships/{relationship_id}
projects/{project_id}/sources/{source_id}
projects/{project_id}/sad_versions/{sad_version_id}
projects/{project_id}/exports/{export_id}
projects/{project_id}/knowledge_item_versions/{version_id}
```

Future optional collections:

```text
projects/{project_id}/memory_versions/{memory_version_id}
projects/{project_id}/source_extraction_snapshots/{snapshot_id}
projects/{project_id}/collaborators/{collaborator_id}
```

MVP knowledge item types:

```text
requirement
entity
workflow
decision
actor
report
source
```

Use stable IDs and readable slugs:

```text
REQ-001
ENT-001
WF-001
DEC-001
ACT-001
REP-001
SRC-001
```

The project-level SAD combines related requirement cards. Do not generate one full SAD per requirement.

## Source Handling

Source files are both input context and traceability evidence.

MVP traceability should capture:

- file-level source
- section/page where available
- sheet/column info for spreadsheets where available
- extraction status and errors
- source IDs referenced by generated requirements, questions, assumptions, relationships, SAD sections, and exports

Future traceability can add exact line, row, cell, paragraph, or page references.

## Agent First Response Contract

For each new requirement, SADify should return this predictable structure:

1. short understanding summary
2. completeness level and score
3. confidence level and reason
4. missing information table
5. clarification questions
6. option to generate a draft with assumptions

Use the labels from `02_agent_behavior_contract.md`:

```text
[CRITICAL], [HIGH], [MEDIUM], [LOW]
[MUST-HAVE], [SHOULD-HAVE], [NICE-TO-HAVE], [FUTURE]
[ASSUMPTION], [OPEN QUESTION], [SOURCE], [CONFIDENCE]
```

Do not present low-confidence output as final truth.

## Completeness And Confidence

Completeness means how much required information is present.

Checklist categories:

```text
actors
workflow trigger
current workflow
proposed workflow
required data fields
approval rules
reports
exceptions
permissions
non-functional constraints
business rules
integration needs
```

Suggested completeness levels:

```text
0-39% Low
40-69% Partial
70-84% Good
85-100% Strong
```

Confidence means how reliable SADify's interpretation is. It should consider source quality, ambiguity, completeness, consistency, and Gemini self-check.

## SAD Output Sections

Project-level SAD drafts should include:

1. project title
2. requirement summary
3. completeness and confidence summary
4. critical gaps and open questions
5. problem statement
6. stakeholders
7. current workflow
8. proposed workflow
9. functional requirements
10. non-functional requirements
11. user roles and permissions
12. business rules
13. edge cases and exception handling
14. data entities
15. integration needs
16. DFD-style process description
17. developer task breakdown
18. assumptions
19. source traceability

## Wiki Knowledge Layer

Wiki Markdown is generated from canonical knowledge items.

Drive structure:

```text
SADify Generated Docs/
  Project Name/
    sad/
      SAD-v1.google_doc
      SAD-v1.pdf
      SAD-v1.docx
    wiki/
      requirements/
      entities/
      workflows/
      decisions/
      actors/
      reports/
      sources/
```

Wiki notes should include YAML frontmatter, readable headings, open questions, sources, and `[[wiki links]]`.

Obsidian is optional. SADify only needs to create compatible Markdown files that Obsidian can open later.

## Wiki Verification Flow

Never overwrite verified wiki notes directly.

MVP flow:

```text
1. Generate markdown_draft from canonical JSON.
2. Run rule-based structural checks.
3. Run Gemini quality check.
4. Show pending change summary to project owner.
5. Project owner approves or rejects.
6. Promote markdown_draft to markdown_current only after checks and approval pass.
```

Allowed statuses:

```text
not_generated
draft
rule_failed
quality_failed
pending_human_approval
verified
rejected
```

## Export Behavior

Normal MVP exports:

- Google Docs
- PDF
- DOCX
- Obsidian-compatible wiki Markdown

Each export should create an export record with:

- export ID
- export type
- source SAD version ID or knowledge item version IDs
- file name
- Drive file ID or URL
- created timestamp
- status
- error message if failed

## Google Cloud Runtime Context

Current project:

```text
Project name: SADify
Project ID: sadify
Project number: 594758969655
Region: asia-southeast1
Runtime service account: sadify-agent-sa@sadify.iam.gserviceaccount.com
Budget guardrail: <budget-guardrail> billing-account budget with 25%, 50%, 75%, and 90% actual-spend alerts
Prototype budget recommendation: create a smaller project-only <prototype-budget> budget before heavy model/deploy loops
```

Required APIs:

```text
aiplatform.googleapis.com
run.googleapis.com
firestore.googleapis.com
secretmanager.googleapis.com
docs.googleapis.com
drive.googleapis.com
cloudbuild.googleapis.com
artifactregistry.googleapis.com
iam.googleapis.com
```

Required APIs have been enabled in project `sadify`.

Likely local environment variables:

```text
GOOGLE_CLOUD_PROJECT=sadify
GOOGLE_CLOUD_LOCATION=asia-southeast1
GOOGLE_GENAI_USE_VERTEXAI=True
SADIFY_MODEL_PROVIDER=google
SADIFY_MODEL=gemini-2.5-flash
SADIFY_FINAL_SAD_PROVIDER=google
SADIFY_FINAL_SAD_MODEL=gemini-2.5-flash
SADIFY_FALLBACK_PROVIDER=
SADIFY_FALLBACK_MODEL=
SADIFY_DRIVE_ROOT_FOLDER_ID=<folder-id>
```

Use `.env.example` for placeholders only. Never store real secrets in repo files.

## Development Checkpoints

Follow this order from `05_development_workflow.md`:

| Checkpoint | Name | Test |
| --- | --- | --- |
| 0 | Read docs and confirm scope | - |
| 1 | Local project scaffold | - |
| 2 | Runtime diagnostics/logging foundation | TC-011 |
| 2A | Model provider routing foundation | TC-013 |
| 3 | Requirement text input | TC-001 |
| 4 | Business file extraction | TC-002 |
| 5 | Canonical JSON schema validation | TC-003 |
| 6 | Firestore persistence | TC-010 |
| 7 | Completeness + confidence scoring | TC-004 |
| 8 | Relationship linking / knowledge graph | TC-005 |
| 9 | Wiki Markdown generation | TC-006 |
| 10 | Wiki verification + owner approval | TC-007 |
| 11 | Project-level SAD generation | TC-008 |
| 12 | Google Docs/PDF/DOCX/wiki export | TC-009 |
| 13 | Local end-to-end test | TC-001 to TC-011 |
| 14 | Cloud Run deployment | - |
| 15 | Cloud Run smoke test | TC-012 |

Do not skip diagnostics. Do not deploy before local end-to-end behavior works.

## Completed Before Current Next Checkpoint

Resolved before local scaffold and early implementation:

- Devpost project path restored or recreated.
- Git repo initialized in `D:\GoogleCloudHack`.
- Planning docs and temporary source materials are ignored by git.
- Manual ADK-compatible scaffold selected.
- Local Python environment confirmed: Python 3.13.2, `.venv`, `pip`, `google-adk` 1.32.0, Streamlit 1.57.0, pytest 9.0.3.
- Required APIs enabled.
- Runtime service account created.
- Required IAM roles granted.
- Firestore Native Mode database created in `asia-southeast1`.
- Google Drive root folder created and shared with the service account as Editor.
- Google Drive root folder ID saved in local `.env`, not in docs or git.
- Streamlit shell created.
- ADK-compatible `root_agent` created.
- Runtime diagnostics and logging foundation created.
- Provider-neutral model route metadata created.
- Requirement text input and deterministic first-response UI created.
- Business file extraction created.
- Canonical JSON schema validation created.
- Local-first Firestore persistence repository created.
- Local completeness/confidence scoring created.
- Local relationship linking / knowledge graph records created.
- Local wiki Markdown generation created.
- Local wiki verification and owner approval state transitions created.
- Local project-level SAD generation created.
- Local export generation created.
- Local tests pass.

Still pending:

- live requirement-analysis adapter shape: pure ADK call path vs thin model-router adapter kept ADK-compatible
- exact first demo scenario
- optional smaller project-only prototype budget before heavy model/deploy loops

Use `docs/superpowers/archive/development/09_pre_development_readiness_checklist.md`
only as historical go/no-go evidence. For current work, use
`docs/superpowers/development/05_development_workflow.md` and the active
checkpoint test case.

## Useful Demo Anchor

Use this simple explanation:

```text
SADify is an AI system analyst that helps non-technical production teams turn real operational problems into clarified, complete, developer-ready System Analysis and Design documents.
```

Difference from generic AI:

```text
Generic AI often jumps straight to a solution. SADify first checks what information is missing, asks structured clarification questions, and only generates the SAD once the requirement is complete enough.
```

## GitHub Issue Relaunch Status

The MVP worktree now persists immutable prepared GitHub issue sets by `(grant_id, project_id, save_id)`. Authenticated relaunch from saved SAD history mints a fresh GATE 3 approval without rerunning developer-task extraction. Stable markers embedded in issue bodies make sequential retries idempotent across open and closed GitHub issues; created and skipped totals are shown to the user. Prepared sets retain their original repository even if the project is later relinked.

Automated verification on 2026-06-19 passed with `652 passed, 4 skipped`, clean TypeScript, and a successful Next production build. TC-036 remains pending until throwaway memory-mode and Firestore/live GitHub recovery smokes produce real evidence. No deployment was performed.
