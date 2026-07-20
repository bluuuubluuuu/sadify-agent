# SADify Development Workflow

Date: 2026-04-30  
Last updated: 2026-05-21

## Purpose

This document defines the safe development workflow for SADify. It focuses on building the MVP with clear checkpoints, expected outputs, real outputs, diagnostics, and test case documentation.

SADify should be developed as an engineered prototype, not a loose hack. Functional features should be protected with tests and evidence. UI polish can be improved later with frontend/design guidance.

## Traceability Sources

This workflow should be verified against:

- `docs/superpowers/development/00_development_index.md`
- `docs/superpowers/development/01_product_scope.md`
- `docs/superpowers/development/02_agent_behavior_contract.md`
- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `docs/superpowers/development/04_google_cloud_setup_runbook.md`
- `docs/superpowers/testing/test_case_index.md`
- `docs/superpowers/research/2026-05-02-track-1-resource-link-analysis.md`

When a checkpoint changes, update the matching test case and any affected source document.

## Development Mode

Use a hybrid workflow:

```text
Build by user flow.
Track app layers touched at each checkpoint.
Gate functional features with tests and evidence.
Keep UI polish flexible until core behavior is stable.
```

Functional gates are strict for:

- business file extraction
- canonical JSON schema
- Firestore persistence
- completeness and confidence scoring
- relationship linking
- wiki Markdown generation
- wiki verification and owner approval
- project-level SAD generation
- Google Docs/PDF/DOCX/wiki export
- diagnostics and HTTP behavior

UI polish is flexible early. It can be improved after core behavior works.

## Required Documentation Per Functional Checkpoint

Before a functional checkpoint is considered complete:

1. Update the matching test case doc.
2. Record expected output.
3. Record real output.
4. Record differences or issues.
5. Attach evidence where possible.
6. Mark the checkpoint as Passed, Failed, or Blocked.

Evidence can include:

- screenshots
- exported file links
- browser console logs
- network request/response details
- HTTP status codes
- app logs
- stack traces
- command output

## Cloud Rule

Cloud setup can happen early.

Cloud Run deployment must wait until local checkpoints pass.

Deployment rule:

```text
Do not deploy to Cloud Run until local end-to-end behavior works.
```

For the hackathon demo, Cloud Run can be public with:

```text
--allow-unauthenticated
```

## Checkpoint Overview

The table below records the completed Streamlit prototype checkpoint path. It remains useful as the baseline and regression suite.

| Checkpoint | Name | Matching Test Case | Gate Strictness |
| --- | --- | --- | --- |
| 0 | Read docs and confirm scope | - | Strict |
| 1 | Local project scaffold | - | Strict |
| 2 | Runtime diagnostics/logging foundation | TC-011 | Strict |
| 2A | Model provider routing foundation | TC-013 | Strict |
| 3 | Requirement text input | TC-001 | Strict |
| 4 | Business file extraction | TC-002 | Strict |
| 5 | Canonical JSON schema validation | TC-003 | Strict |
| 6 | Firestore persistence | TC-010 | Strict |
| 7 | Completeness + confidence scoring | TC-004 | Strict |
| 8 | Relationship linking / knowledge graph | TC-005 | Strict |
| 9 | Wiki Markdown generation | TC-006 | Strict |
| 10 | Wiki verification + owner approval | TC-007 | Strict |
| 11 | Project-level SAD generation | TC-008 | Strict |
| 12 | Google Docs/PDF/DOCX/wiki export | TC-009 | Strict |
| 13 | Local end-to-end test | TC-014, covering TC-001 to TC-011 | Strict |
| 14 | Cloud Run deployment | - | Strict |
| 15 | Cloud Run smoke test | TC-012 | Strict |

## Prototype-To-MVP Checkpoint Track

The MVP checkpoint track starts after the basic deployed prototype baseline. It supersedes the Streamlit-only implementation path for new MVP work.

Phase-based reading map:

| Phase | Workflow meaning | Current status |
| --- | --- | --- |
| Phase 0 | Planning, challenge fit, architecture decision trail | Complete; historical docs retained |
| Phase 1 | Streamlit prototype checkpoints 1-15 | Complete through basic deployed Cloud Run smoke |
| Phase 2 | Proper MVP scaffold, auth, Gemini Q&A, source upload, Drive contract, SAD preview foundation | MVP-00 through MVP-09 passed |
| Phase 3 | Stable Q&A and ready-state handoff | TC-021S and TC-021T passed; TC-021R superseded |
| Phase 4 | SAD preview quality and valid preview coherence | Active; TC-021Y is the current gate |
| Phase 5 | Wiki update approval and Drive/Docs save path | Not started; blocked until TC-021Y passes |
| Phase 6 | Two-service deployment and final smoke | Not started for the proper MVP |

Current MVP execution state:

```text
MVP-00 through MVP-09 have passed.
TC-019 live Firebase Google sign-in and backend ID-token verification passed locally on 2026-05-13.
TC-020 local fake-store guest draft creation and safer signed-in copy contract passed on 2026-05-13.
TC-021 live Gemini structured Q&A passed on 2026-05-13 after Vertex AI User was granted to firebase-adminsdk-fbsvc@sadify.iam.gserviceaccount.com.
TC-022 local source upload traceability passed on 2026-05-13 with multipart upload, extracted source records, traceability units, source context into analysis, TypeScript/build checks, local API smoke, and rendered browser smoke. Real Firestore/Drive source persistence is deferred.
TC-023 local Drive repo OAuth contract passed on 2026-05-14 with signed-in-only repo grant routes, Google Identity Services authorization-code UI, `drive.file` scope intent, planned folder structure, and disconnect save blocking. Live OAuth exchange, Secret Manager token storage, Drive writes, and Picker remain deferred.
TC-024 local SAD preview and IT readiness passed on 2026-05-14 with structured preview schema, blocking-basics gate, IT readiness checklist, assumptions/open questions, source refs, change tracking, temporary preview UI, full tests, TypeScript, production build, local rendered smoke, and later manual live local preview smoke. Drive/Docs save remains deferred.
Post-MVP-09 stabilization fixed the Q&A answer loop on 2026-05-14: users can select a choice or type an amendment, click Continue with answer, refresh the next Gemini question, and see tracking status update. Manual continuation uses one live Gemini request per submitted answer.
Manual Q&A testing then found that the UI still mixed model-led category reconstruction, readiness, fallback state, and confidence in a confusing way. The approved replacement was the stable questionnaire-plan refactor documented in `14_qna_workflow_refinement.md`.
MVP-09.2 automated implementation completed through Checkpoint 4, and the manual clinic-flow rerun on 2026-05-18 reached `100%` with stable progression.
MVP-09.3 / TC-021T passed functionally on 2026-05-18: the `100%` handoff rendered, saved questionnaire answers entered the preview context, and live `/sad/preview` returned `HTTP 200`.
TC-021U now passes for the route-safety layer: the preview context keeps
diagnostics separated, the ready-state UI is cleaner, and invalid Gemini
structured preview output saves a safe local fallback instead of returning
`502`. TC-021V partially passes: the fallback SAD keeps the business request
clean and no longer leaks raw Q&A transport history. TC-021W automated checks
pass for fallback/user-facing presentation, but the 2026-05-20 workshop manual
smoke failed progression because Q&A remained too broad and the valid preview
still showed contradictory low confidence plus visible IT readiness. TC-021X
then passed local checks and improved the workshop path, but the 2026-05-21
tuition-centre manual smoke showed the fix is still too narrow: Q&A can ask a
generic goal question when scope is already clear, broad preset answers can
drive the flow to `100%`, and SAD output can still expose fallback wording,
internal slot IDs, and invented generic rules. The active checkpoint is now
TC-021Y domain-aware Q&A and SAD quality hardening. MVP-10 / TC-025 remains
blocked until TC-021Y passes.
```

Source spec:

```text
docs/superpowers/specs/2026-05-11-sadify-prototype-to-mvp-design.md
```

Implementation and testing references:

```text
docs/superpowers/testing/mvp_web_app_test_plan.md
docs/superpowers/development/14_qna_workflow_refinement.md
```

Checkpoint rule:

```text
Feature work cannot proceed to the next checkpoint until the matching test doc records expected output, real output, evidence, issues, and decision.
Cloud-touching features also require deployed Cloud Run smoke evidence.
```

Checkpoint operating rule:

```text
Before starting any checkpoint:
1. Gather the complete checkpoint packet before touching code:
   - active behavior/product note
   - approved design spec
   - implementation plan
   - matching test case
   - linked data-model/schema docs
   - linked decision-log entries
   - current relevant code files and current test files
   - current git/worktree status
2. Cross-check the packet:
   - behavior note vs design spec
   - design spec vs implementation plan
   - implementation plan vs test case
   - docs vs current code behavior
   - docs vs current checkpoint status
3. If any document is stale, contradictory, or missing a required link, fix the documentation first or ask the user before implementation begins.
4. Identify whether the checkpoint touches external APIs, SDKs, auth, cloud services, or browser integrations.
5. If yes, fetch or re-check the current official documentation before coding.
6. Record the API docs checked, required scopes, credentials, env vars, cost/deployment implications, and unresolved setup questions in the checkpoint notes.
7. Do not rely on old memory for OAuth, Firebase/Auth, Gemini, Firestore, Drive, Docs, Secret Manager, Cloud Run, or framework setup.

After completing one checkpoint:
1. Stop.
2. Return a checkpoint summary to the user.
3. Include changes made, tests/evidence, potential issues or limitations, and the next phase.
4. Wait for user approval before starting the next checkpoint.
```

### Plan Execution Preflight

Before executing any implementation plan, prepare one short preflight note with:

```text
1. plan being executed
2. linked behavior note, design spec, acceptance test, and decision entries
3. files/modules expected to change
4. current code behavior relevant to the plan
5. open contradictions or stale docs found during cross-check
6. external API/docs preflight result, if any
7. explicit go/no-go decision
```

Do not execute the plan until the linked docs and current code agree on the
intended behavior, or the mismatch is documented and approved for correction.

| MVP Checkpoint | Name | Matching Test Case | Required Gate |
| --- | --- | --- | --- |
| MVP-00 | Prototype-to-MVP design and doc alignment | TC-015 | Docs review |
| MVP-01 | Monorepo scaffold for Next.js frontend and FastAPI backend | TC-016 | Unit/local |
| MVP-02 | FastAPI health, config, diagnostics, and typed API contract | TC-017 | Unit/local/API |
| MVP-03 | Next.js project workspace shell with mocked data | TC-018 | Unit/local/browser |
| MVP-04 | Firebase Auth persistent session and backend token verification | TC-019 | Unit/local/browser/deployed |
| MVP-05 | Guest Firestore draft and safer sign-in migration copy | TC-020 | Unit/local/integration/deployed |
| MVP-06 | Live Gemini structured analysis and one-question Q&A state | TC-021 | Unit/local/browser/deployed |
| MVP-07 | Source upload, extraction, and traceability in the web app | TC-022 | Unit/local/browser/deployed |
| MVP-08 | Drive repo connect/create, OAuth grant store, and disconnect | TC-023 | Unit/local/browser/deployed |
| MVP-09 | SAD preview, IT-readiness check, and change tracking summary | TC-024 | Unit/local/browser/deployed |
| MVP-09.1 | Category-first Q&A workflow refinement | TC-021R | Superseded |
| MVP-09.2 | Stable questionnaire plan refactor | TC-021S | Unit/local/browser/manual acceptance |
| MVP-09.3 | Q&A ready state and SAD preview handoff | TC-021T | Unit/local/browser/manual acceptance |
| MVP-09.4 | Q&A + SAD synthesis quality | TC-021U | Unit/local/manual acceptance |
| MVP-09.5 | SAD fallback composition quality | TC-021V | Unit/local/browser/manual acceptance |
| MVP-09.6 | User-facing SAD draft quality | TC-021W | Unit/local/browser/manual acceptance |
| MVP-09.7 | Evidence-first Q&A depth and valid preview coherence | TC-021X | Local pass; manual progression failed |
| MVP-09.8 | Domain-aware Q&A and SAD quality hardening | TC-021Y | Unit/local/browser/manual acceptance |
| MVP-10 | Wiki update plan, approval, taxonomy checks, and backups | TC-025 | Unit/local/browser/deployed |
| MVP-11 | Save SAD Google Doc, wiki Markdown, sources, and `_SADify` metadata | TC-026 | Unit/local/browser/deployed |
| MVP-12 | Full two-service deployed MVP smoke | TC-027 | Deployed end-to-end |

The first implementation milestone is MVP-01 through MVP-06 as a thin full-stack slice:

```text
Next.js -> FastAPI -> guest Firestore draft -> live Gemini structured analysis -> first Q&A state saved
```

## Active Work Linkage

```text
Behavior note:
  14_qna_workflow_refinement.md

Design spec:
  ../specs/2026-05-21-domain-aware-qna-sad-quality-hardening-design.md

Implementation plan:
  ../plans/2026-05-21-domain-aware-qna-sad-quality-hardening.md

Acceptance test:
  ../testing/test_cases/TC-021Y-domain-aware-qna-sad-quality-hardening.md
```

Execution rule for the active checkpoint:

```text
If docs, code, or tests disagree during the active checkpoint:
1. behavior note defines the product rule
2. design spec defines the architecture
3. implementation plan defines the work sequence
4. test case defines acceptance
5. update all four when the approved behavior changes
```

## Checkpoint 0: Read Docs And Confirm Scope

App layers touched:

```text
documentation only
```

Expected output:

- current development docs are read
- source of current decisions is understood
- older 2026-04-29 plan is treated as background
- no coding begins before scope is clear
- Google AI Agents Challenge guide implications are understood
- ADK/Agent Platform compatibility is preserved

Required references:

- `docs/superpowers/development/00_development_index.md`
- `docs/superpowers/development/01_product_scope.md`
- `docs/superpowers/development/02_agent_behavior_contract.md`
- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `docs/superpowers/development/04_google_cloud_setup_runbook.md`
- `docs/superpowers/diagrams/2026-04-29-sadify-architecture.md`
- `docs/superpowers/research/2026-05-02-track-1-resource-link-analysis.md`
- `C:\Users\User\Downloads\ai_agents_challenge_designed_guide.pdf`

Pre-coding platform alignment checks:

- check Google ADK docs for current Python project structure
- check Agents CLI before scaffolding because it is the newer guide-linked lifecycle helper
- treat Agent Starter Pack as background reference unless Agents CLI is unsuitable
- keep the agent core separate from the Streamlit UI
- expose tool actions cleanly so they can become MCP-compatible
- keep Cloud Run as MVP runtime and Agent Runtime as stretch/future
- record any new platform service in `04_google_cloud_setup_runbook.md`

Scaffold decision to record before coding:

```text
Option A: Use Agents CLI scaffold, then adapt for SADify.
Option B: Build manually, but follow ADK-compatible layout and root_agent naming.
```

Do not begin coding until the selected option is documented in the checkpoint notes.

Checkpoint passes when:

```text
The next implementation step is clear and matches the current docs.
```

## Checkpoint 1: Local Project Scaffold

App layers touched:

```text
project structure
dependency management
basic app shell
```

Expected output:

- Python project is created
- dependency file exists
- source folder exists
- test folder exists
- Streamlit app can start locally
- no cloud deployment is attempted

Suggested structure:

```text
sadify/
  pyproject.toml
  README.md
  .gitignore
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
      renderers/
  tests/
```

ADK compatibility requirement:

```text
The agent core must be runnable outside Streamlit.
```

Expected ADK-compatible shape:

```text
sadify_agent/
  __init__.py
  agent.py
  requirements.txt
```

Expected ADK naming:

```text
root_agent
```

The Streamlit UI and ADK-compatible agent should share application services instead of duplicating business logic. The current first slice keeps `root_agent` as the ADK entrypoint and uses local services, including the C13 local workflow service, as the reusable behavior layer for future ADK tools, Cloud Run deployment, and possible Agent Runtime migration later.

Checkpoint passes when:

```text
The local app starts and shows a basic SADify page.
```

## Checkpoint 2: Runtime Diagnostics And Logging Foundation

Matching test:

```text
TC-011-runtime-diagnostics.md
```

App layers touched:

```text
logging
error handling
HTTP response handling
debug output
```

Expected output:

- app logs important actions
- errors are shown to the user in plain language
- stack traces are available in dev logs
- external calls have status and timing logs
- sensitive data is not printed in logs
- failed operations include actionable messages

Checkpoint passes when:

```text
Diagnostics are available before file extraction, model calls, exports, or Firestore writes are built.
```

## Checkpoint 2A: Model Provider Routing Foundation

Matching test:

```text
TC-013-model-provider-routing.md
```

App layers touched:

```text
configuration
model routing metadata
provider readiness diagnostics
Streamlit runtime sidebar
```

Expected output:

- Google/Gemini remains the default model route.
- requirement analysis and final SAD generation can point to separate provider/model pairs.
- an optional fallback route can be configured.
- supported provider bases are listed without committing secrets.
- provider readiness can be displayed without leaking API keys or Drive folder IDs.
- live non-Google provider calls are not required yet.

Checkpoint passes when:

```text
The app can report model routes and provider readiness while keeping `google / gemini-2.5-flash` as the default route.
```

## Checkpoint 3: Requirement Text Input

Matching test:

```text
TC-001-requirement-input.md
```

App layers touched:

```text
Streamlit UI
input validation
first response layout
```

Expected output:

- user can enter requirement text
- empty input is rejected with a clear message
- valid input is accepted
- app shows the deterministic local standard first-response pattern:
  - understanding summary
  - completeness
  - confidence
  - missing information
  - clarification questions
  - draft option

Checkpoint passes when:

```text
Text input can drive the deterministic first-response UI without live model integration yet.
```

## Checkpoint 4: Business File Extraction

Matching test:

```text
TC-002-business-file-extraction.md
```

App layers touched:

```text
file upload
extractors
source metadata
diagnostics
```

Expected output:

- MD/TXT text is extracted
- selectable PDF text is extracted
- DOCX paragraphs are extracted
- XLSX/CSV rows and headers are summarized
- source metadata is captured
- extraction errors are shown clearly
- unsupported files are rejected clearly

MVP file types:

```text
MD
TXT
PDF
DOCX
XLSX
CSV
```

Checkpoint passes when:

```text
Each MVP file type can produce normalized requirement context or a documented error.
```

## Checkpoint 5: Canonical JSON Schema Validation

Matching test:

```text
TC-003-canonical-json-schema.md
```

App layers touched:

```text
schemas
validation
canonical data model
```

Expected output:

- project schema validates
- knowledge item schema validates
- relationship schema validates
- source schema validates
- SAD version schema validates
- export record schema validates
- invalid records fail with useful validation errors

Checkpoint passes when:

```text
Canonical JSON is validated before being saved or rendered.
```

## Checkpoint 6: Firestore Persistence

Matching test:

```text
TC-010-firestore-persistence.md
```

App layers touched:

```text
Firestore service
project persistence
knowledge item persistence
relationship persistence
version persistence
export records
```

Expected output:

- project document can be created
- knowledge items can be saved and read
- relationships can be saved and read
- sources can be saved and read
- SAD versions can be saved and read
- export records can be saved and read
- Firestore errors are logged and shown clearly

Checkpoint passes when:

```text
Validated canonical JSON can round-trip through Firestore.
```

## Checkpoint 7: Completeness + Confidence Scoring

Matching test:

```text
TC-004-completeness-confidence.md
```

App layers touched:

```text
completeness engine
confidence scoring
UI labels
model-route handoff metadata
```

Expected output:

- deterministic checklist produces a transparent score
- confidence score is explained from visible evidence
- completeness level is shown
- confidence label is shown
- missing categories are listed
- low-confidence output is not presented as final truth
- live Gemini/model-router nuance is not required for this checkpoint and should remain a later slice unless explicitly approved

Checkpoint passes when:

```text
The app can explain what is known, what is missing, and how reliable the interpretation is without a live model call.
```

## Checkpoint 8: Relationship Linking / Knowledge Graph

Matching test:

```text
TC-005-relationship-linking.md
```

App layers touched:

```text
relationship builder
canonical JSON
source traceability
```

Expected output:

- requirements can link to entities
- requirements can link to actors
- requirements can link to workflows
- requirements can link to reports
- requirements can link to sources
- relationships include labels, explanations, confidence, and evidence source IDs
- duplicate/noisy nodes are minimized
- first slice is local and deterministic unless a live model call is explicitly approved

Checkpoint passes when:

```text
The app can create understandable relationship records for the wiki graph.
```

## Checkpoint 9: Wiki Markdown Generation

Matching test:

```text
TC-006-wiki-markdown-generation.md
```

App layers touched:

```text
wiki renderer
Markdown generation
YAML frontmatter
Drive path planning
```

Expected output:

- requirement notes generate
- entity notes generate
- workflow notes generate
- decision notes generate
- actor notes generate when clearly detected
- report notes generate when clearly detected
- source notes generate
- YAML frontmatter includes required fields
- `[[wiki links]]` are generated
- files are grouped by item type

Checkpoint passes when:

```text
Canonical knowledge items can render into Obsidian-compatible Markdown drafts.
```

## Checkpoint 10: Wiki Verification + Owner Approval

Matching test:

```text
TC-007-wiki-verification-approval.md
```

App layers touched:

```text
rule-based verifier
Gemini quality verifier placeholder
approval UI
versioning
```

Expected output:

- generated wiki note becomes `markdown_draft`
- rule-based checks run
- Gemini quality status is recorded; live Gemini quality check remains a later slice unless explicitly approved
- failed checks prevent promotion
- pending change summary is shown
- project owner can approve or reject
- approved draft becomes `markdown_current`

Checkpoint passes when:

```text
Wiki notes cannot overwrite verified notes without checks and owner approval.
```

## Checkpoint 11: Project-Level SAD Generation

Matching test:

```text
TC-008-sad-generation.md
```

App layers touched:

```text
local SAD generation service
future Gemini refinement route
SAD renderer
canonical SAD version
Markdown preview
```

Expected output:

- project-level SAD is generated
- requirements are included as sections/modules
- assumptions are visible
- open questions are visible
- source traceability is included
- completeness and confidence summary is included
- rendered Markdown preview is created from structured sections
- first slice is local and deterministic unless a live model call is explicitly approved

Checkpoint passes when:

```text
The generated SAD is readable to humans and traceable to canonical JSON.
```

## Checkpoint 12: Google Docs/PDF/DOCX/Wiki Export

Matching test:

```text
TC-009-export-generation.md
```

App layers touched:

```text
local export generation service
future Google Docs API connector
future Google Drive API connector
PDF renderer
DOCX renderer
wiki file export
export records
```

Expected output:

- Google Docs export works
- PDF export works
- DOCX export works
- wiki Markdown files are saved in Drive
- exports are placed in correct `sad/` and `wiki/` folders
- export records are saved
- export failures are logged and shown clearly
- first slice may prepare local artifacts and export records before real Drive upload

Checkpoint passes when:

```text
Each required export type produces a local artifact or a documented error.
```

## Checkpoint 13: Local End-To-End Test

Matching tests:

```text
TC-014, with coverage across TC-001 through TC-011
```

App layers touched:

```text
full local MVP
```

Expected output:

- user enters text or uploads business files
- requirement context is extracted
- question-area status and overall readiness are shown
- model confidence is hidden or limited to diagnostics
- relationships are generated
- wiki notes are generated and verified
- project owner approval works
- project-level SAD is generated
- exports work
- Firestore state is consistent
- diagnostics are available
- ADK-compatible agent path can be tested separately from Streamlit
- Streamlit output and ADK test output are consistent for the same input

Checkpoint passes when:

```text
The MVP works locally without unresolved critical functional issues.
```

Current status:

```text
Passed on 2026-05-08.
Local workflow service added in commit 77adef3.
Verification: 89 passed in 9.05s.
Streamlit health smoke: 200 ok on localhost:8502.
Fresh alignment review on 2026-05-11: 89 passed in 12.49s, Streamlit health 200 ok.
```

ADK compatibility check:

```text
1. Run the agent core without Streamlit.
2. Submit the same requirement through the ADK path and Streamlit path.
3. Compare summary, completeness, confidence, missing info, and generated structure.
4. Fix wrapper/service drift if outputs differ for reasons unrelated to UI formatting.
```

## Checkpoint 14: Cloud Run Deployment

App layers touched:

```text
Cloud Run
Cloud Build
Artifact Registry
runtime service account
```

Expected output:

- local MVP has already passed
- app deploys to Cloud Run
- service uses `sadify-agent-sa`
- public demo access is enabled only when needed
- deployment URL is recorded
- budget alert is already active

Deployment command:

```bash
gcloud run deploy sadify-app \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --service-account sadify-agent-sa@sadify.iam.gserviceaccount.com
```

Checkpoint passes when:

```text
Cloud Run deployment succeeds and the service URL loads.
```

## Checkpoint 15: Cloud Run Smoke Test

Matching test:

```text
TC-012-cloud-run-smoke-test.md
```

App layers touched:

```text
deployed app
Vertex AI
Firestore
Drive/Docs export
runtime diagnostics
```

Expected output:

- deployed app loads
- basic requirement input works
- Gemini call works
- Firestore read/write works
- at least one export works
- logs show no critical runtime errors
- public demo URL is usable

Checkpoint passes when:

```text
The deployed app can complete the demo-critical path.
```

## Stop Conditions

Stop and fix before proceeding if:

- canonical JSON fails validation
- wiki verification cannot prevent unsafe overwrite
- exports cannot be traced to source versions
- Firestore state becomes inconsistent
- errors are hidden from the user
- logs expose sensitive content
- cost/billing behavior is unclear

## UI Guidance

Core UI can be simple during functional development.

After functional checkpoints pass, use frontend/design guidance to improve:

- layout clarity
- labels and badges
- tables
- upload experience
- export result display
- pending approval view
- demo polish
