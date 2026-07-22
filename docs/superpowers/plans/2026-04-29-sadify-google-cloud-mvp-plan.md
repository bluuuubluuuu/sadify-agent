# SADify Google Cloud MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Date:** 2026-04-29  
**Last updated:** 2026-05-04  
**Status:** Background plan. Current decisions are refined in `docs/superpowers/development/` and `docs/superpowers/diagrams/2026-04-29-sadify-architecture.md`.  
**Project:** SADify  
**Google Cloud Project ID:** `sadify`  
**Goal:** Build a hackathon MVP that turns messy production-team requirements into clarified, connected requirement knowledge, project-level SAD documents, and Obsidian-compatible wiki notes.  
**Architecture:** One Streamlit web app and ADK-powered Python agent deployed together on Cloud Run. The app uses Vertex AI Gemini for reasoning, Firestore for canonical structured JSON, Secret Manager for secrets, Google Drive for project folders, and export tools for Google Docs/PDF/DOCX/wiki outputs.  
**Tech Stack:** Python, Streamlit, Google ADK, Vertex AI Gemini, Cloud Run, Firestore, Secret Manager, Google Docs API, Google Drive API, PDF/DOCX rendering, Markdown wiki generation.

## Traceability Sources

This background plan should be verified against:

- `docs/superpowers/development/00_development_index.md`
- `docs/superpowers/development/04_google_cloud_setup_runbook.md`
- `docs/superpowers/development/05_development_workflow.md`
- `docs/superpowers/diagrams/2026-04-29-sadify-architecture.md`
- `docs/superpowers/research/2026-05-02-track-1-resource-link-analysis.md`

The development docs are the current source of truth if this older plan conflicts with newer decisions.

## 2026-04-30 Refinement Note

The current MVP architecture has expanded from simple SAD document export to a connected requirement knowledge model:

- Firestore stores canonical structured JSON.
- SADify generates Obsidian-compatible Markdown wiki files from the canonical data.
- Wiki files are stored in Google Drive under project `wiki/` folders.
- SAD deliverables should support Google Docs, PDF, and DOCX as normal outputs.
- The main SAD is project-level; individual requirements become requirement cards/wiki notes.
- Wiki Markdown updates require rule-based verification, Gemini quality verification, and project-owner approval before promotion.

Use the newer development docs as the source of current decisions.

## 2026-05-02 Track 1 Source Alignment Note

Track 1 public resource links were reviewed in:

```text
docs/superpowers/research/2026-05-02-track-1-resource-link-analysis.md
```

Confirmed direction:

- SADify is still aligned as a Track 1 net-new agent.
- ADK, Gemini, Cloud Run, Firestore, Drive/Docs, and MCP-compatible tool boundaries remain suitable.
- Agents CLI should be checked before scaffolding.
- Agent Starter Pack is background reference only because its public repo points future development to Agents CLI.
- Agent Runtime, Agent Evaluation, Observability, RAG, and Agent Search remain future/stretch unless the final submission strategy changes.

## 2026-05-04 Implementation And Model Routing Note

Implementation has started. The current codebase now includes:

- manual ADK-compatible scaffold with `sadify_agent/agent.py`
- Streamlit shell in `src/sadify/app.py`
- diagnostics and logging helpers
- provider-neutral model route metadata in `src/sadify/models/routing.py`

The default model route remains:

```text
google / gemini-2.5-flash
```

This older plan is still background only. Use `docs/superpowers/development/00_development_index.md`, `07_decision_log.md`, and `11_model_provider_linkage.md` for current model-routing decisions.

---

## 1. Current Decisions

SADify should be positioned as an AI system analyst, not a generic SAD generator.

The winning behavior is:

```text
Messy production requirement
  -> SADify asks clarification questions
  -> SADify checks requirement completeness
  -> SADify generates structured SAD
  -> SADify exports to Google Docs
```

The MVP should avoid unnecessary infrastructure. Do not use GKE, BigQuery, VMs, Cloud SQL, advanced multi-user collaboration, or a complex project-management system for the first version.

## 2. Google Cloud Services

| Service | Purpose | MVP Required | Notes | Cost Risk |
| --- | --- | --- | --- | --- |
| Vertex AI | Gemini model calls for clarification, completeness, and SAD generation | Yes | Use `gemini-2.5-flash` first | Low |
| Cloud Run | Host Streamlit app and Python ADK agent | Yes | One service for frontend and backend | Very low |
| Firestore | Store sessions, chat history, generated SAD docs, versions, completeness scores | Yes | Native mode | Very low |
| Secret Manager | Store GitHub token later, optional config secrets | Yes | Required once external tokens exist | Negligible |
| Google Docs API | Create generated SAD documents | Yes | Core export action | Free/API quota |
| Google Drive API | Place SAD exports and wiki files into project folders | Yes | Needed for `sad/` and `wiki/` folder placement | Free/API quota |
| Cloud Build | Build source for Cloud Run deployment | Yes | Used by `gcloud run deploy --source .` | Low |
| Artifact Registry | Store build images for Cloud Run | Yes | Used by Cloud Run source deploy | Low |
| GitHub API/MCP | Create developer issues from task breakdown | Later | Good demo extension after Docs export works | Low |
| Cloud SQL | Relational data store | No | Too heavy for MVP | Moderate |
| GKE/VMs | Infrastructure hosting | No | Overkill | High |

## 3. Region And Model

Use:

```text
Region: asia-southeast1
Model first choice: gemini-2.5-flash
Model later option: gemini-2.5-pro for final SAD generation only if output quality is weak
```

Reasoning:

- `asia-southeast1` is the closest practical Google Cloud region for Malaysia/APAC.
- Gemini Cloud Assist confirmed Gemini 2.5 Flash and Pro support for this plan.
- `gemini-2.5-flash` is fast and cost-conscious for hackathon iteration.

## 4. IAM And Security Decisions

Runtime service account:

```text
sadify-agent-sa@sadify.iam.gserviceaccount.com
```

Grant these roles to the runtime service account:

```text
roles/aiplatform.user
roles/datastore.user
roles/secretmanager.secretAccessor
```

Do not treat `roles/run.invoker` as a runtime permission. `roles/run.invoker` controls who can call the Cloud Run service. For a public hackathon demo using `--allow-unauthenticated`, Cloud Run public access is handled during deployment.

Google Docs/Drive access is handled by sharing a Drive folder with the service account email as Editor.

Recommended Drive folder:

```text
SADify Generated Docs
```

Recommended per-project structure:

```text
SADify Generated Docs/
  Project Name/
    sad/
    wiki/
```

## 5. Minimal Cloud Setup Plan

### Task 1: Set Billing Safety

This older task has been superseded by the confirmed May 2026 budget setup.

- [ ] Open Google Cloud Console for project `sadify`.
- [ ] Go to Billing.
- [ ] Confirm credits are attached.
- [ ] Create a budget alert named `SADify Hackathon Budget`.
- [ ] Set budget amount to `USD 25`.
- [ ] Set alerts at `50%`, `80%`, and `100%`.

Current confirmed setup:

```text
<budget-guardrail> billing-account budget with actual-spend alerts at 25%, 50%, 75%, and 90%.
Smaller project-only <prototype-budget> budget remains recommended before heavy model/deploy loops.
```

### Task 2: Enable Required APIs

Run in Cloud Shell:

```bash
gcloud config set project sadify

gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  firestore.googleapis.com \
  secretmanager.googleapis.com \
  docs.googleapis.com \
  drive.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
```

Expected result:

```text
Operation finished successfully.
```

### Task 3: Create Runtime Service Account

Run in Cloud Shell:

```bash
gcloud iam service-accounts create sadify-agent-sa \
  --display-name="SADify Agent Runtime"
```

Expected service account:

```text
sadify-agent-sa@sadify.iam.gserviceaccount.com
```

### Task 4: Grant Runtime Roles

Run in Cloud Shell:

```bash
gcloud projects add-iam-policy-binding sadify \
  --member="serviceAccount:sadify-agent-sa@sadify.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding sadify \
  --member="serviceAccount:sadify-agent-sa@sadify.iam.gserviceaccount.com" \
  --role="roles/datastore.user"

gcloud projects add-iam-policy-binding sadify \
  --member="serviceAccount:sadify-agent-sa@sadify.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

Expected result:

```text
Updated IAM policy for project [sadify].
```

### Task 5: Create Firestore Database

Use Firestore Native Mode in `asia-southeast1`.

Console path:

```text
Firestore -> Create database -> Native mode -> asia-southeast1
```

CLI option:

```bash
gcloud firestore databases create \
  --database="(default)" \
  --location=asia-southeast1
```

Expected result:

```text
Firestore database created in asia-southeast1.
```

### Task 6: Prepare Google Drive Folder

- [ ] In Google Drive, create folder `SADify Generated Docs`.
- [ ] For each project, prepare `Project Name/sad/` and `Project Name/wiki/`.
- [ ] Share the folder with `sadify-agent-sa@sadify.iam.gserviceaccount.com`.
- [ ] Give the service account `Editor` access.
- [ ] Copy the folder ID from the URL and store it for app configuration.

Folder URL shape:

```text
https://drive.google.com/drive/folders/<folder-id>
```

## 6. MVP App File Structure

Create this structure when implementation begins:

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
      agent.py
      prompts.py
      models.py
      completeness.py
      firestore_store.py
      docs_export.py
  tests/
    test_completeness.py
    test_models.py
```

File responsibilities:

| File | Responsibility |
| --- | --- |
| `src/sadify/app.py` | Streamlit UI and user flow |
| `src/sadify/config.py` | Project ID, region, model, Drive folder ID |
| `src/sadify/agent.py` | ADK/Gemini agent orchestration |
| `src/sadify/prompts.py` | System instructions and SAD generation templates |
| `src/sadify/models.py` | Typed data structures for sessions, questions, SAD output |
| `src/sadify/completeness.py` | Requirement completeness scoring rules |
| `src/sadify/firestore_store.py` | Firestore session persistence |
| `src/sadify/docs_export.py` | Google Docs and Drive export |
| `tests/test_completeness.py` | Unit tests for completeness scoring |
| `tests/test_models.py` | Unit tests for structured output models |

## 7. SADify Agent Behavior

The agent must follow this sequence:

```text
1. Read messy user requirement.
2. Extract actors, process, data, rules, constraints, risks, and missing info.
3. Calculate requirement completeness.
4. If completeness is below 80%, ask 3-5 clarification questions.
5. If completeness is 80% or above, generate SAD preview.
6. Save session and SAD version to Firestore.
7. Export to Google Docs when user clicks export.
```

The agent should not immediately generate the final SAD after the first vague input. This is the product differentiator.

## 8. SAD Output Sections

The generated SAD document must include:

```text
1. Project Title
2. Problem Statement
3. Stakeholders
4. Current Workflow
5. Proposed Workflow
6. Functional Requirements
7. Non-Functional Requirements
8. User Roles
9. Business Rules
10. Edge Cases
11. Data Entities
12. DFD-style Process Description
13. Developer Task Breakdown
14. Open Questions
15. Requirement Completeness Score
```

## 9. Implementation Plan

### Task 7: Build Local Streamlit Shell

- [ ] Create project files.
- [ ] Add Streamlit app with project title, requirement text area, and submit button.
- [ ] Run locally with `streamlit run src/sadify/app.py`.
- [ ] Confirm the UI opens and accepts input.

### Task 8: Add Completeness Engine

- [ ] Implement deterministic checks for:
  - actors
  - workflow trigger
  - required data
  - approval flow
  - reporting needs
  - edge cases
  - user permissions
  - non-functional constraints
- [ ] Return score from `0` to `100`.
- [ ] Return missing categories as short labels.
- [ ] Add unit tests.

### Task 9: Add Gemini/ADK Agent

- [ ] Configure Vertex AI with:

```text
Project: sadify
Location: asia-southeast1
Model: gemini-2.5-flash
```

- [ ] Add system instruction:

```text
You are SADify, an AI system analyst. Your job is to convert messy production-team requirements into validated, structured System Analysis and Design output. You must clarify missing information before generating final SAD output.
```

- [ ] Build functions for:
  - analyzing messy requirement
  - generating clarification questions
  - generating SAD document
  - generating developer task breakdown

### Task 10: Add Firestore Persistence

- [ ] Store each requirement session in collection `sessions`.
- [ ] Use document fields:

```text
created_at
updated_at
raw_requirement
clarification_answers
completeness_score
missing_categories
sad_markdown
exported_doc_url
```

- [ ] Show previous generated documents in the app after the main MVP flow works.

### Task 11: Add Standard SAD And Wiki Exports

- [ ] Use Google Docs API to create a document.
- [ ] Use Google Drive API to move it into the shared folder `SADify Generated Docs`.
- [ ] Generate PDF and DOCX outputs from the same structured SAD version.
- [ ] Generate Obsidian-compatible Markdown wiki files from canonical knowledge items.
- [ ] Return SAD export links and wiki folder link in the Streamlit UI.
- [ ] Store detailed export records in Firestore.

### Task 12: Deploy To Cloud Run

Run from project root after the local app works:

```bash
gcloud run deploy sadify-app \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --service-account sadify-agent-sa@sadify.iam.gserviceaccount.com
```

Expected result:

```text
Service [sadify-app] revision deployed.
Service URL: https://sadify-app-...a.run.app
```

## 10. Demo Plan

Use this demo scenario:

```text
Our warehouse team keeps losing track of stock movement. Items are moved between locations but sometimes operators forget to update the record. Supervisors only notice mistakes during monthly checking. We need a system to fix this.
```

Demo steps:

```text
1. Paste messy requirement into SADify.
2. Show completeness score below 80%.
3. Show missing categories: approval flow, data fields, notification rules, reports, edge cases.
4. SADify asks clarification questions.
5. User answers naturally.
6. SADify generates structured SAD.
7. SADify exports to Google Docs.
8. Show Google Doc URL.
```

Pitch line:

```text
Unlike generic AI tools that jump straight to a solution, SADify behaves like a system analyst: it validates requirement completeness before producing developer-ready system specifications.
```

## 11. Later Extensions

Add only after standard SAD exports and wiki generation work:

```text
1. GitHub Issues export from developer task breakdown.
2. Company/domain templates for warehouse, production, HR, maintenance, and procurement.
3. Version comparison between SAD drafts and wiki notes.
4. Collaborator approval workflow beyond the project owner.
5. Image input.
```

## 12. Known Risks

| Risk | Mitigation |
| --- | --- |
| Gemini output becomes too generic | Use strict prompts, structured output, and completeness checks |
| Google Docs/Drive service account folder access fails | Share Drive folder directly with service account as Editor |
| Cloud Run deployment complexity slows demo | Build locally first, deploy only after core flow works |
| Costs increase during testing | Use budget alert and `gemini-2.5-flash` by default |
| MVP becomes too broad | Do standard exports and wiki generation first, GitHub Issues later |

## 13. Immediate Next Step

Start with cloud safety and local MVP:

```text
1. Set budget alert.
2. Enable required APIs.
3. Create service account and Firestore.
4. Create Drive folder with `sad/` and `wiki/` structure and share with service account.
5. Build local Streamlit + Gemini MVP.
```
