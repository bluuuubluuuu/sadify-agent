# SADify Google Cloud Setup Runbook

Date: 2026-04-30  
Last updated: 2026-05-13

## Purpose

This runbook documents the Google Cloud setup needed for the SADify prototype. It is written for a solo developer building a hackathon MVP with limited credits.

Use this document before enabling services, creating resources, deploying to Cloud Run, or adding new Google Cloud tools.

## Traceability Sources

This runbook should be verified against:

- `docs/superpowers/research/2026-05-02-track-1-resource-link-analysis.md`
- `docs/sources/ai_agents_challenge_designed_guide.pdf`
- `docs/superpowers/development/00_development_index.md`
- `docs/superpowers/development/05_development_workflow.md`
- `docs/superpowers/diagrams/2026-04-29-sadify-architecture.md`

When any Google Cloud tool, API, model, service, role, or billing decision changes, update this runbook first and then update the affected development or testing docs.

Detailed credit-consuming service tracking now lives in:

```text
docs/superpowers/development/13_cloud_credit_consuming_services.md
```

## Credit And Billing Context

Current budget context:

```text
User has an overall billing-account budget guardrail around <budget-guardrail>.
Actual-spend alerts are configured at 25%, 50%, 75%, and 90%.
```

Purpose:

```text
Prototype and hackathon development only.
```

Billing principle:

```text
Use only what is needed for the MVP.
Track every billable service.
Prefer local development until the app is demo-ready.
Clean up resources after testing.
```

Enabling an API usually does not cost money by itself. Cost usually comes from usage or resources, such as model calls, Cloud Run requests, build minutes, stored images, database reads/writes, and stored secrets.

Current caution:

```text
The <budget-guardrail> budget is an overall guardrail, not an early prototype-warning budget.
Before automated model-heavy loops, repeated deployments, or large file-processing runs, create a smaller project-only budget around <prototype-budget> or get explicit user approval.
```

Billing observation on 2026-05-12:

```text
User reported small Cloud Run-related billing entries: small amounts on two dates.
Because the current date is 2026-05-12, recheck the exact "20/5" date in billing before treating it as historical usage.
Recent MVP-01 through MVP-04 work was local-only and did not deploy, call Gemini, or intentionally consume Google Cloud resources.
Before any next deployment or model-heavy test, review Cloud Run revisions/min instances, Artifact Registry storage, Cloud Build, logging, and whether the existing prototype service should be paused or deleted.
```

## Project Information

Current project information:

| Field | Value |
| --- | --- |
| Project name | SADify |
| Project ID | `sadify` |
| Project number | `594758969655` |
| Region | `asia-southeast1` |
| Runtime service account | `sadify-agent-sa@sadify.iam.gserviceaccount.com` |
| Current budget guardrail | Around `<budget-guardrail>` with actual-spend alerts at 25%, 50%, 75%, and 90% |
| Recommended prototype budget | Around `<prototype-budget>` before heavy model/deploy loops |

If the project ID, project number, region, or service account changes, update this runbook immediately.

## Required Services

Enable only the services needed for the MVP.

| API | Purpose |
| --- | --- |
| `aiplatform.googleapis.com` | Vertex AI Gemini calls |
| `run.googleapis.com` | Cloud Run deployment |
| `firestore.googleapis.com` | Firestore database |
| `secretmanager.googleapis.com` | Secret storage |
| `docs.googleapis.com` | Google Docs export |
| `drive.googleapis.com` | Google Drive folder/file placement |
| `cloudbuild.googleapis.com` | Source deployment build |
| `artifactregistry.googleapis.com` | Container image storage for Cloud Run |
| `iam.googleapis.com` | Service account and IAM management |

## Prototype-To-MVP Setup Change

The current deployed prototype used a Streamlit app and planned Drive access through a service-account-shared folder. The MVP web app direction supersedes that export path.

New MVP direction:

```text
Next.js frontend on Cloud Run
FastAPI backend on Cloud Run
Firebase Auth / Google Identity Platform for persistent Google sign-in
Backend-only Firestore access
User-owned Google Drive project repo through OAuth
Backend-mediated Drive/Docs OAuth grant storage
Disconnect Google Drive control
```

Do not enable or reconfigure new auth/OAuth services until the matching implementation plan is approved.

TC-023 local OAuth planning note, 2026-05-14:

```text
SADify should use the Google Identity Services authorization code model for persistent backend Drive/Docs access.
The first repo-connection scope intent is https://www.googleapis.com/auth/drive.file.
Live token exchange, refresh-token storage, Drive Picker, and real Drive/Docs writes are deferred until the matching save/setup checkpoint.
```

Before implementation, verify and document the exact current Google setup for:

```text
1. Firebase Auth / Google Identity Platform APIs and console setup.
2. OAuth consent screen and redirect URLs for local and Cloud Run environments.
3. Minimal Drive/Docs scopes for folder selection, project repo creation, Google Docs creation, and Markdown/source uploads.
4. Least-privilege Secret Manager roles needed for the backend token store.
5. Whether the backend should store refresh tokens in Secret Manager or another explicitly approved secure store.
```

Current known issue:

```text
The existing runtime service account has Secret Manager Secret Accessor for reading secrets.
That may not be sufficient for creating/updating/deleting per-user OAuth token secrets.
Do not change IAM until the least-privilege role is verified.
```

Current MVP auth setup status:

```text
TC-019 local Firebase Auth/session verification passed on 2026-05-13.
Required local frontend/backend config includes Firebase web values such as NEXT_PUBLIC_FIREBASE_API_KEY, NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN, NEXT_PUBLIC_FIREBASE_PROJECT_ID, NEXT_PUBLIC_FIREBASE_APP_ID, backend FIREBASE_PROJECT_ID / GOOGLE_CLOUD_PROJECT alignment, and a local Firebase Admin credential outside git.
Deployed Cloud Run auth config, redirect/domain setup, and service identity credential behavior remain later deployment work.
```

## Hackathon Guide Platform Mapping

The AI Agents Challenge guide emphasizes building with Google Cloud agent tools, especially ADK, Gemini, MCP/tool integrations, Agent Runtime, Sessions/Memory, Evaluation, and Observability.

For SADify, use the platform in layers:

| Google Platform Component | SADify Decision | Why |
| --- | --- | --- |
| Google Cloud Billing | Required now | Protect the prototype budget with billing alerts; current confirmed guardrail is around <budget-guardrail>, with a smaller project-only budget still recommended before heavy loops |
| APIs & Services | Required now | Enable only the services listed in this runbook |
| IAM & Admin | Required now | Create and permission `sadify-agent-sa` |
| Vertex AI Gemini | Required for MVP | Default reasoning, clarification, completeness, verification, and generation route |
| Google ADK | Required for MVP | Agent framework; keeps SADify aligned with the challenge guide |
| Agents CLI | Check before coding | Preferred guide-linked helper for scaffolding, evaluating, deploying, and operating ADK agents |
| Agent Starter Pack | Background only | Older template source; useful for patterns, but public repo now points future development to Agents CLI |
| MCP / Tool integrations | Required concept for MVP | Export and file actions should be modeled as tools where practical |
| Cloud Run | Required later | Prototype/demo hosting after local checkpoints pass |
| Firestore | Required for MVP | Canonical structured JSON, versions, relationships, project memory |
| Secret Manager | Required for MVP | Safe storage for secrets/tokens when external integrations need them |
| Google Drive API | Required for MVP | Stores `sad/` and `wiki/` project folders and exported files |
| Google Docs API | Required for MVP | Creates Google Docs SAD deliverables |
| Cloud Build | Required later | Builds source for Cloud Run deployment |
| Artifact Registry | Required later | Stores Cloud Run container images |
| Agent Runtime / Agent Engine | Optional/stretch | Future managed runtime, sessions, memory, and observability path |
| Agent Evaluation / Simulation | Optional/stretch | Future reliability layer for test scenarios and edge cases |
| Agent Observability | Optional/stretch | Future tracing/debugging layer for agent reasoning and tool calls |
| Agent Search / RAG | Future | Possible grounding upgrade if uploaded files/wiki memory are not enough |
| A2A Protocol | Future/Track 3 style | Not needed for Track 1 MVP, but useful if SADify becomes marketplace/enterprise-ready |

Current MVP stance:

```text
Build locally with ADK-compatible structure.
Use Vertex AI Gemini as the default model route.
Keep provider-neutral routing metadata for future model comparison and fallback.
Use Firestore/Drive/Docs as tools and storage.
Deploy to Cloud Run only after local checkpoints pass.
Keep Agent Runtime, Evaluation, Observability, RAG, and A2A as future/stretch paths.
```

## Model Provider Routing Context

SADify now has a provider-neutral routing foundation in code. This does not change the Google Cloud MVP runtime or required Google Cloud services.

Default route:

```text
Provider: google
Model: gemini-2.5-flash
```

Route variables:

```text
SADIFY_MODEL_PROVIDER=google
SADIFY_MODEL=gemini-2.5-flash
SADIFY_FINAL_SAD_PROVIDER=google
SADIFY_FINAL_SAD_MODEL=gemini-2.5-flash
SADIFY_FALLBACK_PROVIDER=
SADIFY_FALLBACK_MODEL=
```

Provider bases recorded for future adapters:

```text
google
openai
anthropic
openai_compatible
ollama
huggingface
```

Cost and setup rule:

```text
Do not add live non-Google model calls until the requirement-analysis flow exists, provider secrets are deliberately configured, and cost risk is accepted.
```

## Track 1 Source Alignment Notes

Latest source tracker:

```text
docs/superpowers/research/2026-05-02-track-1-resource-link-analysis.md
```

Key alignment decisions:

- SADify is still a valid Track 1 net-new agent.
- Public guide links support ADK, Gemini, MCP/tool integrations, and Cloud Run as suitable for the MVP.
- Agents CLI was checked during readiness; manual ADK-compatible scaffolding was selected for the MVP because local `agents-cli` and local `gcloud` were not installed and the manual path is easier to debug.
- Treat Agent Starter Pack as reference only because it now points future development to Agents CLI.
- Keep Agent Runtime / Agent Engine as stretch unless a later submission decision requires managed runtime features.
- Keep RAG Engine, Vertex AI Search, and Grounding with Google Search as future only for the MVP.
- Keep SADify budget planning conservative. The current confirmed guardrail is an overall <budget-guardrail> billing-account budget; a smaller project-only prototype budget is still recommended before heavier testing.

## Screenshot Validation Checklist

When checking Google Cloud Console screenshots, validate:

- active project is `sadify`
- billing credit is visible or attached
- billing budget guardrail exists
- smaller project-only prototype budget exists if heavy testing is about to begin
- enabled APIs match the required API list
- no avoid-list services are being used accidentally
- service account is `sadify-agent-sa@sadify.iam.gserviceaccount.com`
- IAM roles are not broader than necessary
- Firestore is in `asia-southeast1`
- Drive folder is shared with the service account as Editor
- Cloud Run is not deployed until local MVP checkpoints pass
- any new tool/service is added to the Tool And Version Tracking table before use

## Setup Order

Use this order:

```text
1. Confirm billing credits.
2. Create budget alert.
3. Enable APIs.
4. Create service account.
5. Grant IAM roles.
6. Create Firestore database.
7. Prototype-only: create Google Drive folder structure.
8. Prototype-only: share Drive folder with service account.
9. MVP web app: replace the prototype Drive folder path with user-owned Drive repo selection through OAuth after the matching implementation plan is approved.
10. Build locally first.
11. Deploy to Cloud Run only when MVP is ready.
```

## Step 1: Confirm Billing Credits

Console path:

```text
Google Cloud Console -> Billing -> Credits
```

Confirm:

```text
Billing account is attached to project `sadify`.
Overall <budget-guardrail> budget guardrail exists with actual-spend alerts.
```

If billing is not attached, do not deploy or run model-heavy tests.

## Step 2: Create Budget Alert

Use a cautious prototype budget before heavy model/deploy loops.

Budget:

```text
Recommended: <prototype-budget> project-only budget
Current confirmed: <budget-guardrail> billing-account budget
```

Alerts:

```text
Current confirmed: 25%, 50%, 75%, 90% on actual spend
Recommended for smaller project-only budget: 25%, 50%, 75%, 90%
```

Console path:

```text
Google Cloud Console -> Billing -> Budgets & alerts -> Create budget
```

Suggested name:

```text
SADify Prototype Budget
```

Use this budget to catch mistakes early. Increase it later only if there is a clear reason.

## Step 3: Enable Required APIs

Primary method: Cloud Shell.

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
  artifactregistry.googleapis.com \
  iam.googleapis.com
```

Expected result:

```text
Operation finished successfully.
```

Console fallback:

```text
Google Cloud Console -> APIs & Services -> Library
Search each API name -> Enable
```

## Step 4: Create Runtime Service Account

Primary method: Cloud Shell.

```bash
gcloud iam service-accounts create sadify-agent-sa \
  --display-name="SADify Agent Runtime"
```

Expected service account:

```text
sadify-agent-sa@sadify.iam.gserviceaccount.com
```

Console fallback:

```text
Google Cloud Console -> IAM & Admin -> Service Accounts -> Create service account
```

## Step 5: Grant IAM Roles

Grant only the permissions needed by the runtime service account.

Primary method: Cloud Shell.

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

Console fallback:

```text
Google Cloud Console -> IAM & Admin -> IAM -> Grant access
Principal: sadify-agent-sa@sadify.iam.gserviceaccount.com
Roles:
- Vertex AI User
- Cloud Datastore User
- Secret Manager Secret Accessor
```

Local MVP note:

```text
TC-021 local Gemini smoke currently uses the Firebase Admin SDK credential:
firebase-adminsdk-fbsvc@sadify.iam.gserviceaccount.com

If that credential is used to call Vertex AI locally, it also needs Vertex AI User
or another service account with roles/aiplatform.user must be used for
GOOGLE_APPLICATION_CREDENTIALS.
```

Do not treat `roles/run.invoker` as a runtime permission. It controls who can call the Cloud Run service. For the public hackathon demo, use Cloud Run public access only when deploying the demo.

## Step 6: Create Firestore Database

Use Firestore Native Mode.

Location:

```text
asia-southeast1
```

Console path:

```text
Google Cloud Console -> Firestore -> Create database -> Native mode -> asia-southeast1
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

## Step 7: Create Google Drive Folder Structure

Prototype note:

```text
This service-account shared-folder path was valid for the Streamlit prototype.
The proper MVP uses user-owned Drive project repos through OAuth instead.
Keep this section for prototype history and fallback debugging, not as the MVP export path.
```

Create this root folder in Google Drive:

```text
SADify Generated Docs
```

For each project, SADify should create or use:

```text
SADify Generated Docs/
  Project Name/
    sad/
    wiki/
```

The `sad/` folder stores:

```text
Google Docs
PDF
DOCX
```

The `wiki/` folder stores Obsidian-compatible Markdown files:

```text
requirements/
entities/
workflows/
decisions/
actors/
reports/
sources/
```

## Step 8: Share Drive Folder With Service Account

Prototype note:

```text
This step is superseded for the proper MVP by user-owned Drive/Docs OAuth.
Do not build new MVP export behavior around the service-account shared-folder model unless the decision is reopened.
```

In Google Drive:

```text
Right-click SADify Generated Docs -> Share
```

Add:

```text
sadify-agent-sa@sadify.iam.gserviceaccount.com
```

Permission:

```text
Editor
```

Google Docs/Drive access is handled by Drive folder sharing, not by project IAM roles.

Copy and store the root folder ID.

Folder URL shape:

```text
https://drive.google.com/drive/folders/<folder-id>
```

## Step 9: Local Development First

Build locally before deploying.

Local build target:

```text
Streamlit UI
ADK/Gemini agent
file extraction for normal business files
canonical JSON
Firestore save
wiki Markdown generation
Google Docs/PDF/DOCX export
```

Do not deploy to Cloud Run until the MVP flow works locally.

## Step 10: Cloud Run Demo Deployment

Deploy only when the app is demo-ready.

For hackathon demo, use public access:

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

After deployment, test:

```text
1. App loads.
2. User can enter requirement or upload supported files.
3. Gemini response works.
4. Firestore save works.
5. Wiki Markdown generation works.
6. Google Docs/PDF/DOCX export works.
7. Drive links are returned.
```

## Cost Tracking Table

The dedicated current ledger is:

```text
docs/superpowers/development/13_cloud_credit_consuming_services.md
```

Keep this summary table aligned with that file.

| Service | Why Used | Cost Trigger | Cost Risk | How To Stop Cost |
| --- | --- | --- | --- | --- |
| Vertex AI | Gemini calls for interpretation, completeness, SAD generation | Tokens/model calls | Low to moderate if heavily tested | Stop test loops, reduce calls, use Flash first |
| Cloud Run | App and agent hosting | Requests, CPU, memory | Low if scales to zero | Delete service or stop deploying |
| Cloud Build | Builds source for Cloud Run | Build minutes | Low but can grow with repeated deploys | Stop repeated deployments |
| Artifact Registry | Stores container images | Image storage | Low but persistent | Delete old images/repository |
| Firestore | Stores project data, versions, wiki metadata | Reads, writes, storage | Low for prototype | Delete test data/database if no longer needed |
| Secret Manager | Stores secrets/tokens | Active secrets/versions | Negligible but persistent | Delete unused secrets/versions |
| Google Docs API | Creates SAD documents | API quota usage | Usually low/free quota | Stop exports |
| Google Drive API | Folder/file placement and wiki files | API quota usage/storage in Drive | Usually low/free quota | Stop exports/remove generated files |

## Services To Avoid For Prototype

Do not use these unless the plan is explicitly updated with a reason:

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

Reason:

```text
They are unnecessary for the current prototype and may increase cost or complexity.
```

## Cleanup And Shutdown Checklist

Use this when testing is finished or if costs need to be stopped quickly.

### Cloud Run

```bash
gcloud run services delete sadify-app \
  --region asia-southeast1
```

### Artifact Registry

Console path:

```text
Artifact Registry -> Repositories -> Delete unused images or repository
```

### Firestore Test Data

Console path:

```text
Firestore -> Data -> Delete test projects/collections
```

Be careful with Firestore deletion. Export any useful prototype data before deleting.

### Secret Manager

Console path:

```text
Secret Manager -> Delete unused secrets or old secret versions
```

### Google Drive Files

Delete generated test folders/files from:

```text
SADify Generated Docs
```

Remove service account access if the prototype is no longer active.

### Disable APIs

Only disable APIs when you are sure the project is paused or finished.

Console path:

```text
APIs & Services -> Enabled APIs & services -> Select API -> Disable
```

## Tool And Version Tracking

Whenever a new cloud service, tool, library, model, or integration is recommended or added, update this runbook.

Track:

```text
tool/service name
purpose
version/model if applicable
why it is needed
cost risk
how to disable/remove it
whether it is MVP or future
```

Current tool/version assumptions:

| Tool/Service | Current Choice | Purpose | Status |
| --- | --- | --- | --- |
| Vertex AI Gemini | `gemini-2.5-flash` first | Default reasoning and generation route | MVP |
| Model provider router | Local SADify route metadata | Separate requirement-analysis, final-SAD, and fallback model choices | MVP foundation |
| OpenAI / Anthropic / Hugging Face / Ollama / OpenAI-compatible providers | Config placeholders only | Future provider adapters after real analysis flow exists | Future |
| Google ADK | Python ADK | Agent framework | MVP |
| Agents CLI | Check current version before scaffold | Scaffold, eval, deploy helper | Pre-coding check |
| Agent Starter Pack | Reference only | Older templates/patterns | Background |
| Streamlit | Current stable version when installed | Fast MVP UI | MVP |
| Cloud Run | Managed service | Demo hosting | MVP when demo-ready |
| Firestore | Native Mode | Project state and canonical JSON | MVP |
| Google Drive API | Current API | Folder placement and wiki files | MVP |
| Google Docs API | Current API | SAD export | MVP |

If any tool changes, update this table and the avoid list if needed.

## TC-026B Live Drive/Docs Setup (Completed 2026-05-25)

Cloud preparation for the live Drive/Docs save slice. Everything below has
been verified in the GCP console for project `sadify`.

### APIs enabled

- Google Drive API
- Google Docs API
- Secret Manager API
- (Already on from earlier work: Firebase, Identity Toolkit, Vertex AI)

### OAuth consent screen

- App name: `SADify`
- User type: External
- Publishing status: In Production (100-user lifetime cap; unverified-app
  warning is expected and acceptable for the hackathon prototype)
- Authorized domain: `sadify.firebaseapp.com`
- Developer contact: `<owner-email>`
- Scopes added:
  - `https://www.googleapis.com/auth/drive.file` (non-sensitive, per-file)
  - `https://www.googleapis.com/auth/documents` (sensitive)
- Not submitted for verification — no justification text or demo video
  provided. Sufficient for unverified-app warning + 100-user cap.

### OAuth Web Client (new, separate from Firebase Auth client)

- Name: `SADify Web (TC-026B)`
- Application type: Web application
- Client ID: `594758969655-0md22e7bs1hvjjg1ihpokvvtpuarq6pp.apps.googleusercontent.com`
- Client secret: stored in
  `D:\GoogleCloudHack\.secrets\sadify-drive-oauth-client.txt` (local-only,
  `.secrets/` is gitignored) AND mirrored into Secret Manager (see below).
- Authorized JavaScript origins: `http://localhost:3000`
- Authorized redirect URIs: `http://localhost:3000`
- Do NOT modify the older `Web client (auto created by Google Service)` —
  that one is used by Firebase Authentication for TC-019 sign-in.

### Secret Manager — OAuth client secret

- Secret name: `sadify-drive-oauth-client-secret`
- Resource: `projects/594758969655/secrets/sadify-drive-oauth-client-secret`
- Replication policy: Automatic
- Encryption: Google-managed key
- Version 1 holds the OAuth client secret (GOCSPX-...).
- Permissions on this secret:
  - `sadify-agent-sa@sadify.iam.gserviceaccount.com` → Secret Manager Secret
    Accessor (runtime SA; production reads)
  - `firebase-adminsdk-fbsvc@sadify.iam.gserviceaccount.com` → Secret Manager
    Secret Accessor (local dev reads via GOOGLE_APPLICATION_CREDENTIALS)

### Secret Manager — per-user refresh tokens (created at runtime)

- Secret name pattern: `sadify-drive-token-<firebase-uid>`
- Created by the backend on first live Drive connect.
- New version added on each refresh.
- Project-level Secret Manager Admin role granted to both
  `sadify-agent-sa` and `firebase-adminsdk-fbsvc` so the backend can:
  - Create new per-user secrets on first connect
  - Add new versions on token refresh
  - Read existing versions at save time

### Environment variables (to be added to .env.example in the TC-026B plan)

Backend (FastAPI):

```text
SADIFY_DRIVE_MODE=local                 # set to "live" to enable real Drive
SADIFY_GOOGLE_OAUTH_CLIENT_ID=594758969655-0md22e7bs1hvjjg1ihpokvvtpuarq6pp.apps.googleusercontent.com
SADIFY_GOOGLE_OAUTH_CLIENT_SECRET_NAME=sadify-drive-oauth-client-secret
SADIFY_DRIVE_FOLDER_NAME=SADify Projects
```

Frontend (Next.js):

```text
NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID=594758969655-0md22e7bs1hvjjg1ihpokvvtpuarq6pp.apps.googleusercontent.com
```

Setting `NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID` auto-hides the local-dev
connect button added in commit `abf2860` and re-enables the live
"Connect Google Drive" button gated by `isGoogleOAuthConfigured()`.

### Cost notes

- Drive API and Docs API: free tier covers a hackathon demo by orders of
  magnitude. No quota concerns.
- Secret Manager: free tier covers 6 active secret versions and 10k access
  operations per month. A handful of test users with refresh tokens stays
  well under.
- No new Compute/GKE/BigQuery/etc. needed for TC-026B.

### Disable/rollback steps if needed

1. Frontend: unset `NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID` to re-hide live UI.
2. Backend: set `SADIFY_DRIVE_MODE=local` to fall back to fake Doc IDs.
3. To revoke all user grants in bulk: delete all `sadify-drive-token-*`
   secrets in Secret Manager.
4. To fully roll back: delete the `SADify Web (TC-026B)` OAuth client and
   the `sadify-drive-oauth-client-secret` secret. Do not delete the older
   Firebase Auth client.

## TC-030 Firestore Persistence (Completed 2026-05-30)

Firestore Native Mode is now the live backend store for the repositories that
must survive Cloud Run cold starts, multiple instances, and redeploys. Gated
behind `SADIFY_PERSISTENCE=firestore` (default `memory`).

### Database (already provisioned, re-verified)

- `(default)` database, **Native mode**, Standard edition, `asia-southeast1`
  (Singapore), created 2 May 2026. No new database created for TC-030.

### IAM — Cloud Datastore User (`roles/datastore.user`)

- `sadify-agent-sa@sadify.iam.gserviceaccount.com` (Cloud Run runtime) —
  already held from earlier setup.
- `firebase-adminsdk-fbsvc@sadify.iam.gserviceaccount.com` (local dev via
  `GOOGLE_APPLICATION_CREDENTIALS`) — **granted 2026-05-30** so the local live
  smoke and `SADIFY_PERSISTENCE=firestore` dev runs can read/write Firestore.

```bash
gcloud projects add-iam-policy-binding sadify \
  --member="serviceAccount:firebase-adminsdk-fbsvc@sadify.iam.gserviceaccount.com" \
  --role="roles/datastore.user"
```

### Collections written by the app

```text
drive_repos, projects, project_name_index, sad_saves,
sad_save_idempotency, wiki_state, counters
```

`counters/*` are persistent transactional sequence docs (PR-/SV-/SA-/SM-/DG-/
fake-doc/local-folder). Do NOT delete or reset them — that can cause future ID
reuse. The `RequirementAnalysisRepository` and source uploads remain in-memory
by design (ephemeral working session).

### Environment variables

Backend (FastAPI):

```text
SADIFY_PERSISTENCE=memory     # default; set "firestore" in deployed/live-persist runs
SADIFY_FIRESTORE_LIVE=        # leave empty; set 1 only for the opt-in live Firestore smoke
GOOGLE_CLOUD_PROJECT=sadify   # used to construct the Firestore client
```

The deployed Cloud Run backend (TC-027) will run `SADIFY_PERSISTENCE=firestore`
with the `sadify-agent-sa` runtime identity (no key file; ADC).

### Dependency

- `google-cloud-firestore` (2.27.0) — only new dependency. Transactions use the
  official `firestore.transactional` decorator (manual un-begun transactions
  fail against real Firestore).

### Cost notes

- Firestore reads/writes for a hackathon prototype stay well within the free
  tier. No quota concerns.

### Disable/rollback steps if needed

1. Backend: set `SADIFY_PERSISTENCE=memory` (or unset) to fall back to
   in-memory repositories. No Firestore traffic.
2. To clear test data: delete docs in the collections above via Firestore ->
   Data. Leave `counters/*` unless you accept ID reuse.
