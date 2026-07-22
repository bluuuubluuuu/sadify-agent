# SADify Cloud Credit Consuming Services

Date: 2026-05-13  
Status: Active cost-watch reference
Last updated: 2026-05-15

## Purpose

This document lists the Google Cloud and Google platform services that can consume credits or create billable usage for SADify.

Use it before:

- running live Gemini tests
- deploying or redeploying Cloud Run
- writing to Firestore
- storing secrets or OAuth tokens
- saving files to Drive/Docs
- enabling any new Google Cloud service

This is not a pricing quote. Official prices can change, and billing may show local currency through Google Cloud SKUs. Always verify the Billing page before heavy testing.

## Traceability Sources

- `docs/superpowers/development/04_google_cloud_setup_runbook.md`
- `docs/superpowers/development/00_development_index.md`
- `docs/superpowers/testing/test_cases/TC-021-mvp-live-gemini-qna.md`
- Google Cloud Vertex AI pricing: `https://cloud.google.com/vertex-ai/generative-ai/pricing`
- Google Cloud Run pricing: `https://cloud.google.com/run`
- Firestore pricing: `https://cloud.google.com/firestore/pricing`
- Secret Manager pricing: `https://cloud.google.com/secret-manager/pricing`
- Cloud Build pricing: `https://cloud.google.com/build/pricing`
- Artifact Registry pricing: `https://cloud.google.com/artifact-registry/pricing`
- Google Cloud Observability pricing: `https://cloud.google.com/products/observability/pricing`
- Identity Platform pricing: `https://cloud.google.com/identity-platform/pricing`
- Firebase pricing: `https://firebase.google.com/pricing`

## Current Billing Guardrails

| Guardrail | Current State |
| --- | --- |
| Billing account | Attached to project `sadify` |
| Broad budget | Around <budget-guardrail> billing-account budget with actual-spend alerts |
| Recommended smaller budget | <prototype-budget> project-only budget before heavy model/deploy loops |
| Current execution rule | One checkpoint at a time; ask before cloud-heavy or repeated live tests |

## Current Services That Can Consume Credits

| Service | Current SADify Use | What Consumes Credits | Current Risk | How To Reduce Or Stop |
| --- | --- | --- | --- | --- |
| Vertex AI Gemini | Active for MVP-06 live Q&A through `gemini-2.5-flash` | Successful model calls, input/output tokens, multimodal inputs later | Low for single tests, higher for repeated loops or large files | Use short test prompts, avoid loops, keep Flash first, stop live smoke when not needed |
| Cloud Run | Existing Streamlit prototype service; MVP later uses frontend/backend services | Requests, CPU, memory, instance time, possible idle cost if min instances are set | Low but already observed small charges | Keep min instances at 0, delete paused demo services, avoid repeated deploys |
| Cloud Build | Used when deploying from source to Cloud Run | Build minutes during deploys | Low but grows with repeated deploys | Build locally first, deploy only after checkpoint passes |
| Artifact Registry | Stores Cloud Run container images | Image storage, some data transfer, vulnerability scanning if enabled | Low but persistent | Delete old images/repositories; avoid enabling paid scanning unless needed |
| Firestore | Database exists; current MVP still uses local fake-store for some flows | Document reads, writes, deletes, storage, network bandwidth | Low now; increases once real cloud persistence is wired | Keep cloud smoke small, clean test records, avoid polling loops |
| Secret Manager | Planned for OAuth/secrets; current roles exist | Active secret versions and secret access operations | Low but persistent once tokens are stored | Delete unused secrets/old versions; avoid per-test secret creation loops |
| Cloud Logging / Observability | Cloud Run and Google services emit logs automatically | Stored logs beyond free allotment, long retention, custom metrics/traces | Low now; can grow with noisy logs or repeated deploy failures | Reduce noisy logs, keep default retention, avoid large payload logging |
| Firebase Auth / Identity Platform | Local Google sign-in verified for MVP-04 | Monthly active users beyond free tier; phone/SMS/MFA messages | Low for current Google sign-in tests | Avoid phone auth/SMS in prototype; keep test accounts limited |

## Enabled Or Planned Services That Usually Do Not Directly Spend Credits By Themselves

| Service/API | SADify Use | Credit Note |
| --- | --- | --- |
| IAM API | Service accounts and role grants | Role changes do not normally create compute/model/storage usage |
| Drive API | User-owned project repo, wiki files, source files | API calls mostly hit quota; Drive storage is in the user/Workspace account, not normal GCP compute credits |
| Docs API | SAD Google Doc creation | API calls mostly hit quota; generated Docs live in Drive and may count against Drive/Workspace storage |
| Firebase console/project config | Auth setup and web app config | Config itself does not drive compute charges; Auth usage can |

## Services To Avoid Unless Explicitly Approved

Do not add these for the current MVP without updating the plan and this document:

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
Vertex AI Search / RAG Engine
Cloud Storage as product storage
Phone Authentication / SMS MFA
```

## Check Before Each Checkpoint

Ask these before starting a checkpoint:

1. Does this checkpoint call Gemini or another live model?
2. Does it deploy or rebuild Cloud Run?
3. Does it write to Firestore, Secret Manager, Drive, or Docs?
4. Does it upload large files or process repeated test loops?
5. Does it enable a new API or create a new persistent resource?
6. Is the test input small and generic enough for a cheap smoke test?
7. Is there a cleanup step after the test?

## Manual Billing Checks

Use Google Cloud Console:

```text
Billing -> Reports
Billing -> Cost table
Billing -> Budgets & alerts
Cloud Run -> sadify services -> Revisions -> Min instances
Artifact Registry -> Repositories -> image count and size
Firestore -> Data -> test collections
Secret Manager -> active secrets and versions
Logging -> Logs Storage -> _Default bucket retention and volume
```

## Current Notes

- TC-021 made one successful live Gemini call on 2026-05-13 after IAM was fixed.
- The earlier failed Gemini call returned `403`; official Vertex AI pricing says failed `4xx/5xx` generative requests are not charged for input/output tokens.
- User previously observed small Cloud Run-related billing entries. Recheck Billing Reports before the next deployment.
- TC-022 / MVP-07 source upload traceability stayed local. It did not deploy, write Drive/Firestore, or make a new live Gemini call.
- MVP-08 / TC-023 Drive repo OAuth stayed local on 2026-05-14. It did not deploy, store secrets, exchange OAuth tokens, write to Secret Manager, write to Drive, or call Gemini.
- MVP-09 / TC-024 SAD preview and IT readiness stayed local/fake-model for verification on 2026-05-14. It did not deploy, write Drive/Firestore/Secret Manager, or make a live Gemini call. Manual `Generate SAD preview` against the real backend will call Gemini and consume model tokens.
- A later manual local live preview smoke on 2026-05-14 did call Gemini through `/analysis/requirement` and `/sad/preview` and returned `HTTP 200`. Keep further live preview/answer tests short.
- Post-MVP-09 Q&A answer continuation does not add a new service, but each manual `Continue with answer` against the real backend calls Gemini once.
- If a live answer continuation receives invalid structured Gemini output, the UI fallback keeps the answer locally for preview without making an extra automatic Gemini call.
- If Gemini returns invalid structured Q&A after the repair retry, the backend now saves a local fallback question without making more model calls. This avoids repeated paid retry loops from the app itself.
- Fallback questions are deterministic and local. They do not call Gemini, and fallback readiness should not increase from repeated fallback clicks.
- The 2026-05-14 Q&A logic stabilization for selection modes, disabled answered categories, `I'm not sure`, and amendment rules used fake-model/local tests only. No live Gemini, Firestore, Drive, Docs, Secret Manager, Cloud Run deploy, or new API enablement was run for that update.
- The 2026-05-14 Q&A workflow refinement documentation pass was docs-only. It did not run backend/frontend servers, live Gemini, Firestore, Drive, Docs, Secret Manager, Cloud Run deploy, or new API enablement.
- The 2026-05-15 MVP-09.1 / TC-021R category-first Q&A refinement implementation used local fake-model tests, TypeScript, production build, and a temporary localhost HTTP smoke only. It did not run live Gemini, Firestore, Drive, Docs, Secret Manager, Cloud Run deploy, or new API enablement.
- The 2026-05-15 follow-up Q&A UI simplification and repeated-question guard used local fake-model tests only. It did not run live Gemini, Firestore, Drive, Docs, Secret Manager, Cloud Run deploy, or new API enablement.
- Future live Drive/Docs checkpoints can create Google API traffic, Drive files, Docs files, and persistent Secret Manager token storage. Recheck OAuth setup and cost/cleanup notes before running those live saves.
