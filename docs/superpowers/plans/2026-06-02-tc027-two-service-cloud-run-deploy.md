# TC-027 Two-Service Cloud Run Deploy Plan

Date: 2026-06-02
Status: Draft - awaiting billing confirmation + explicit go-ahead before execution

Test case: `docs/superpowers/testing/test_cases/TC-027-mvp-two-service-deployed-smoke.md`
Runbook: `docs/superpowers/development/04_google_cloud_setup_runbook.md`
Worktree: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`, branch `codex/mvp-monorepo-scaffold`

## Goal

Deploy the MVP as two Cloud Run services (frontend + backend) in
`asia-southeast1`, running the live stack (`SADIFY_DRIVE_MODE=live` +
`SADIFY_PERSISTENCE=firestore`) under runtime identity
`sadify-agent-sa@sadify.iam.gserviceaccount.com` (ADC, no key file), then pass
the TC-027 deployed smoke.

## Decisions (confirmed 2026-06-02)

- Build/deploy: `gcloud run deploy --source` (Cloud Build builds each service
  from a Dockerfile; no manual Artifact Registry or CI). → decision D-094.
- Scope/cost: full live (Drive live + Firestore), `min-instances=0`
  (scale-to-zero) on both services.

## Hard constraints / stop rules

- Do NOT deploy until billing is confirmed attached and a prototype budget
  (~<prototype-budget>) is in place or explicitly waived (runbook guardrail).
- Do NOT deploy until the runtime SA IAM checklist below is verified.
- No code/`lib/api.ts` shape changes; deploy uses the current build as-is.
- All 460 local tests + the A+B/D-wording browser smoke already pass — this
  plan adds only deploy artifacts + cloud config.

## Key architecture facts (drive the sequence)

- Backend: uvicorn factory `sadify_api.main:create_app --factory`; Firebase
  init is ADC-based (`auth.py:48 initialize_app(options=options)`), so the
  Cloud Run runtime SA supplies credentials — no key file.
- Frontend: Next.js 16 standalone (`output: "standalone"`,
  `start: node .next/standalone/server.js`). The `NEXT_PUBLIC_*` envs are
  **build-time baked**: `NEXT_PUBLIC_SADIFY_API_BASE_URL`,
  `NEXT_PUBLIC_FIREBASE_{API_KEY,AUTH_DOMAIN,PROJECT_ID,APP_ID}`,
  `NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID`. → the backend URL must exist before the
  frontend image is built.
- Backend CORS reads `SADIFY_ALLOWED_ORIGINS` (`config.py:50`) → must include
  the deployed frontend URL (set/updated after the frontend URL is known).
- Browser calls the backend directly with Firebase ID tokens → backend Cloud
  Run service must allow unauthenticated ingress; app-level Firebase
  verification is the real auth gate. Frontend also unauthenticated.

## Preconditions checklist (verify before any deploy)

1. Billing attached to project `sadify`; prototype budget ~<prototype-budget> set or
   waived.
2. APIs enabled: `run`, `cloudbuild`, `artifactregistry`, `secretmanager`,
   `firestore`, `aiplatform` (Vertex), `iamcredentials`.
3. Runtime SA `sadify-agent-sa` has, at minimum:
   - `roles/aiplatform.user` (Gemini via Vertex)
   - `roles/datastore.user` (Firestore Native)
   - `roles/secretmanager.secretAccessor` + `roles/secretmanager.secretVersionAdder`
     + secret create (either `roles/secretmanager.admin` or pre-create the
     per-user `sadify-drive-token-<uid>` secrets) — Drive token store writes on
     connect.
   - Token verification needs no extra IAM (public certs).
   Note: locally the backend ran as the `firebase-adminsdk-fbsvc` SA; on Cloud
   Run it is `sadify-agent-sa`, so confirm parity of the above roles.
4. OAuth Web client (`SADIFY_GOOGLE_OAUTH_CLIENT_ID`) and Firebase Auth both
   need the deployed frontend origin added (done in step 5 of the sequence,
   after the URL exists).

## Artifacts authored (in worktree) — DONE 2026-06-02

- **`Dockerfile` at the worktree ROOT (not `services/api/`)** — Python 3.13
  slim. This location is **deliberate**: the backend image must contain BOTH
  `services/api/src` (sadify_api) and the root `src/` (the `sadify` extractors
  package the API imports via `sadify.extractors.business_files`). A single
  Cloud Build context can only reach both from the worktree root, so the
  backend deploys with `--source .`, not `--source services/api`. Installs the
  `services/api/pyproject.toml` deps plus the three lazy-imported extractor libs
  (`pypdf`, `python-docx`, `openpyxl`); `streamlit`/`google-adk`/`pandas` are
  NOT on the API path and are excluded. Uses explicit `COPY services/api/src` +
  `COPY src/` (never `COPY . .`), so `.env`/stray files cannot enter the image.
  Runs `uvicorn sadify_api.main:create_app --factory --host 0.0.0.0 --port
  ${PORT:-8080}`. `PYTHONPATH=/app/services/api/src:/app/src`.
- `apps/web/Dockerfile` — Node 22 build stage runs `npm ci && npm run build`
  with the six `NEXT_PUBLIC_*` build args; runtime stage copies
  `.next/standalone` and runs `node server.js` on `$PORT`.
- `apps/web/.dockerignore` + `apps/web/.gcloudignore` — exclude `node_modules`,
  `.next`, `.env*`.
- Root `.gcloudignore` — extended to also exclude `apps/`, `tests/`,
  `sadify_agent/` so the backend (`--source .`) build context stays lean.
- Static lock test: `tests/test_tc027_deploy_artifacts.py`.

(No `services/api/.dockerignore` is needed: the backend Dockerfile uses
explicit COPY, not whole-context COPY.)

## Deploy sequence

1. **Backend** — `gcloud run deploy sadify-api --source .`
   (run from the worktree root; uses the root `Dockerfile`)
   `--region asia-southeast1 --service-account sadify-agent-sa@... `
   `--allow-unauthenticated --min-instances 0 --set-env-vars`
   `GOOGLE_CLOUD_PROJECT=sadify,FIREBASE_PROJECT_ID=sadify,`
   `SADIFY_PERSISTENCE=firestore,SADIFY_DRIVE_MODE=live,`
   `SADIFY_DRIVE_LIVE_ENABLED=1,SADIFY_GOOGLE_OAUTH_CLIENT_ID=<id>,`
   `SADIFY_ENV=prod,SADIFY_ALLOWED_ORIGINS=https://PLACEHOLDER`.
   Capture the backend URL.
2. **Frontend** — two steps, because `NEXT_PUBLIC_*` are build-time baked and
   `--source` cannot pass `--build-arg`:
   a. Build+push the image via Cloud Build:
      `gcloud builds submit apps/web --config apps/web/cloudbuild.yaml
      --substitutions _NEXT_PUBLIC_SADIFY_API_BASE_URL=<backend URL>,
      _NEXT_PUBLIC_FIREBASE_API_KEY=<key>,_NEXT_PUBLIC_FIREBASE_APP_ID=<appId>`
      (project_id/auth_domain/oauth-client default in the config). The
      `cloud-run-source-deploy` Artifact Registry repo is auto-created by step 1.
   b. Deploy the pushed image:
      `gcloud run deploy sadify-web --image
      asia-southeast1-docker.pkg.dev/sadify/cloud-run-source-deploy/sadify-web:latest
      --region asia-southeast1 --allow-unauthenticated --min-instances 0`.
   Capture the frontend URL.
3. **Backend CORS update** — `gcloud run services update sadify-api`
   `--region asia-southeast1 --update-env-vars SADIFY_ALLOWED_ORIGINS=<frontend URL>`
   (new revision).
4. **Console origin updates** — add `<frontend URL>` to the OAuth Web client
   Authorized JavaScript origins and to Firebase Auth Authorized domains.
5. **Smoke (TC-027 steps 1-10)** — guest draft → live Gemini Q&A → sign in →
   migrate → connect/create Drive repo → SAD preview → approve → save Doc +
   wiki + sources → confirm Firestore + Drive links → check hidden diagnostics.
   Record expected/real/evidence/decision in the TC-027 file.

## Cost guardrails

- `min-instances=0` both services → no idle compute cost; pay per request +
  Cloud Build minutes + Artifact Registry image storage.
- After the smoke, review revisions, AR images, Cloud Build history; delete the
  old Streamlit prototype service if still running.
- Stop if any unexpected billing spike appears mid-deploy.

## Rollback

- Each service keeps prior revisions; `gcloud run services update-traffic
  --to-revisions` reverts instantly. Deleting both services + AR images removes
  standing cost. No data migration risk (Firestore already live and tested).

## Preflight result (read-only, 2026-06-02)

- Billing: `billingEnabled: true` on project `sadify`. User reports spend a small amount
  against the <budget-guardrail> credit (expiring in ~25 days) → budget gate satisfied.
- APIs enabled: `run`, `cloudbuild`, `artifactregistry`, `secretmanager`,
  `firestore`, `aiplatform`, `iamcredentials` — all present.
- `sadify-agent-sa` roles: `aiplatform.user`, `datastore.user`,
  `secretmanager.admin`, `secretmanager.secretAccessor`. `secretmanager.admin`
  covers create + version-add + access, so the Drive token store works.
  → IAM gate satisfied; no grants needed.

## Open items to resolve at execution time

- ~~`src/sadify` reachable in the backend image~~ — RESOLVED: root Dockerfile
  copies `src/` into the context; locked by `test_tc027_deploy_artifacts.py`.
- Decide `SADIFY_ENV` value for prod (`prod` vs leaving `test`). Plan uses
  `prod`.
- Confirm whether to predict the frontend URL (deterministic Cloud Run URL) to
  avoid the two-step CORS update, or keep the explicit step 3.

## Tooling note

- `gcloud run deploy --source` builds the images in **Google Cloud Build** —
  **local Docker is NOT required**. The Dockerfiles are only source artifacts.
- Deploy needs the **gcloud CLI**. It is not on the user's Windows PATH, so
  either install Google Cloud SDK or run the deploy from **Cloud Shell**
  (gcloud preinstalled). Cloud Shell is the lower-friction path.

## Approval gate

Preconditions (billing + IAM + APIs) are now GREEN. The plan is still not
executed until explicit user go-ahead. Authoring Dockerfiles is safe and local;
the first `gcloud run deploy` is the first billable, hard-to-reverse action.
