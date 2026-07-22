# TC-027 MVP Two-Service Deployed Smoke

Date Created: 2026-05-11
Last Updated: 2026-07-22
Status: Passed (2026-06-03); redeployed 2026-07-22 (revisions sadify-api-00010-m9c / sadify-web-00005-499)

## Redeploy 2026-07-22 (Phase 8.1)

After merging main to current (18 commits ahead of the 2026-06-04 revisions)
and adding CI, both services were redeployed from Google Cloud Shell. Same
service names, same URLs, new revisions:

- `sadify-api` -> `sadify-api-00010-m9c` (was `sadify-api-00005-pc2`)
- `sadify-web` -> `sadify-web-00005-499` (was `sadify-web-00002-vzw`)

CI green on main before deploy (658 passed, tsc clean, next build ok). Smoke:

- `GET /health` -> `{"status":"ok","service":"sadify-api",...}`
- Live guest Q&A returned a real Gemini turn.
- `gemini_token_usage` lines present in Cloud Logging (~4,000 Flash tokens per
  real Q&A turn) - confirms the new token metering shipped.
- Zero 5xx in Cloud Logging after deploy.
- Rate-limit smoke: pending clean confirmation (per-instance limiter; a burst
  from one client may distribute across Cloud Run instances).

## Purpose

Verify the deployed MVP across frontend Cloud Run, backend Cloud Run, auth, Gemini, Firestore, Drive, and Docs.

## Inputs

- Deployed frontend service URL
- Deployed backend service URL
- Test Google account
- Test Drive project repo
- Test requirement and source file

## Preconditions

TC-016 through TC-026 passed locally and in browser.

## Steps

1. Open deployed frontend.
2. Create guest draft.
3. Run live Gemini Q&A.
4. Sign in and migrate the guest draft.
5. Connect or create Drive project repo.
6. Generate SAD preview.
7. Review and approve changes.
8. Save SAD Google Doc, wiki Markdown, and sources.
9. Confirm Firestore and Drive links.
10. Check hidden diagnostics for critical errors.

## Expected Output

The deployed two-service MVP completes the core product path with no critical runtime errors.

## Real Output

Passed 2026-06-03. Two Cloud Run services deployed in `asia-southeast1`,
scale-to-zero, runtime SA `sadify-agent-sa` (ADC):
- Backend `sadify-api` → `https://sadify-api-594758969655.asia-southeast1.run.app`
  (revision sadify-api-00003-gcl).
- Frontend `sadify-web` → `https://sadify-web-594758969655.asia-southeast1.run.app`
  (revision sadify-web-00001-grf).

Seven-case browser smoke (pet grooming, source PDF SRC-000001), all pass,
zero 5xx across the run:
1. Guest Q&A — `/analysis/requirement 200`, source=gemini (frontend→backend
   wiring + live Gemini via Vertex ADC).
2. Google sign-in — `/auth/session 200` (firebase-admin token verify).
3. Connect Drive — `/drive/repo/connect 200` (live OAuth + Secret Manager
   token store).
4. SAD preview — `/sad/preview 200`; both user amendments incorporated;
   100%/"Ready for draft"/"High evidence".
5. Save to Drive — `/sad/save 200`; SV-000001,
   `SAD/SAD-SP-000001-SV-000001.google_doc`; real Google Doc opened.
6. Update wiki — `/sad/wiki/update 200`; 8-file encyclopedia written.
7. Firestore persistence — after hard refresh, `/projects/PR-000001/saves 200`
   returned SV-000001 (was "No saves yet" pre-save), clearing the in-memory
   deploy blocker.

## Differences / Issues

- Build surfaced three runtime deps missing from `services/api/pyproject.toml`
  (present in local .venv): `python-multipart`, `firebase-admin`,
  `google-genai`. Fixed in the backend Dockerfile + manifest + static test
  (commit 58aa315); took 3 backend deploy iterations to green.
- Two manual console steps were required after the frontend URL existed and
  were the cause of mid-smoke failures until corrected:
  - `auth/unauthorized-domain` on sign-in → added the run.app domain to
    Firebase Auth → Authorized domains.
  - `Error 400: origin_mismatch` on Drive connect → added the run.app origin
    to the "SADify Web" OAuth client → Authorized JavaScript origins.
- Cloud Run default URL keeps the `<projectNumber>.<region>.run.app` form;
  a prettier `sadify.web.app` via Firebase Hosting is an optional, deferred
  polish (not required).
- Minor SAD-quality notes (non-blocking): coarse per-section source
  attribution (all SRC-000001), one source-inferred Reports section, triggers
  slightly conflated into the rules section.

## Evidence

Cloud Logging (`gcloud logging read`, service sadify-api): 200s for
`/analysis/requirement`, `/auth/session`, `/drive/repo/connect`,
`/sad/preview`, `/sad/save`, `/sad/wiki/preview`, `/sad/wiki/update`,
`/projects/PR-000001/saves`; no severity>=ERROR / status>=500 in the run.
Pre-frontend backend checks: `/health 200` (environment=prod), CORS allow-
origin echoed for the predicted frontend URL, txt + pdf multipart uploads
extracted. Browser UI screenshots/transcripts pasted during the smoke.

## Decision

PASS. The two-service MVP is deployed and completes the full product path
(guest Q&A → sign-in → Drive connect → SAD preview → save Google Doc →
wiki → persisted history) in production with no critical runtime errors.
Final MVP checkpoint cleared.
