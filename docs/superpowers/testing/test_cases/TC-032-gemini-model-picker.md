# TC-032 Gemini Model Picker

Date Created: 2026-06-03
Last Updated: 2026-06-04
Status: Passed

## Purpose

Verify that SADify exposes a backend-owned Gemini model catalog, lets the
frontend choose a model globally, sends the selected model through Q&A and SAD
preview calls, and falls back to the backend default when a requested model is
invalid or unavailable.

## Inputs

- Backend catalog IDs from `GEMINI_MODEL_CATALOG`.
- Frontend `ModelPicker` selection persisted in `localStorage`.
- Fake backend model adapters that capture the selected model.
- Fake Gemini client that raises `NotFound` for an allowlisted selected model
  and succeeds for the default model.
- Live allowlist probe against project `sadify`, Vertex AI, location `global`.

## Preconditions

- Worktree: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`
- Branch: `codex/mvp-monorepo-scaffold`
- MVP production deployment already passed as TC-027.
- No deploy without explicit user approval.

## Steps

1. Call `GET /models`.
2. Submit `/analysis/requirement` without a model and with `gemini-2.5-pro`.
3. Submit `/sad/preview` without a model and with `gemini-2.5-pro`.
4. Simulate unavailable `gemini-2.5-flash-lite` and confirm retry to
   `gemini-2.5-flash`.
5. Probe all shipped model IDs live against Vertex AI for project `sadify`.
6. Verify frontend static wiring for `listModels`, `ModelPicker`,
   `localStorage`, `useQnA`, `useSadSave`, and `WorkspaceV2`.
7. Run full Python regression.
8. Run frontend typecheck and build.

## Expected Output

- `/models` returns the shipped Gemini catalog and backend default.
- Missing or invalid model IDs resolve to backend default.
- A configured but unavailable selected model retries backend default and does
  not fail the request when default succeeds.
- The shipped catalog contains only model IDs that work for project `sadify` in
  Vertex AI location `global`.
- Frontend persists selected model and sends it on future Q&A/SAD preview calls.
- Existing MVP behavior remains unchanged when no model is selected.

## Real Output

Implementation completed and deployed from branch `codex/mvp-monorepo-scaffold`.

Backend:

- `GET /models` returns the backend-owned Gemini catalog:
  `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.5-flash-lite`.
- Missing or invalid model IDs fall back to backend default
  `gemini-2.5-flash`.
- Allowlisted-but-unavailable selected IDs retry the backend default in the
  Gemini adapter.
- `gemini-2.5-pro` uses model-aware generation config: Pro keeps thinking
  enabled with `max_output_tokens=24000`; Flash/Flash-Lite preserve the
  previous `thinking_config={"thinking_budget": 0}` and `max_output_tokens=8000`.

Frontend:

- Picker is populated dynamically from `GET /models`; no Pro option is
  hardcoded in frontend option data.
- Initial picker state is empty/loading until `/models` resolves, preventing a
  hardcoded frontend model from being sent before the backend default is known.
- A valid stored `localStorage` selection wins; otherwise the response
  `default` wins.
- Selected model is sent on both analysis and SAD preview requests.
- Catalog hints render per model, including Pro's `slower, higher quality`.

Verification:

```text
..\..\.venv\Scripts\python.exe -m pytest -q
488 passed, 4 skipped

npx tsc --noEmit
passed

npm run build
passed
```

Live model probe evidence:

```text
gemini-2.5-flash       OK      OK
gemini-2.5-flash-lite  OK      OK
gemini-2.5-pro         initially rejected thinking_budget=0 with 400 INVALID_ARGUMENT
gemini-2.5-pro         live JSON verified after ae97f8e model-aware generation config
```

Production deployment evidence (2026-06-04):

```text
Pre-deploy / CC live baseline:
sadify-api  sadify-api-00003-gcl  created 2026-06-02T11:35:39Z
sadify-web  sadify-web-00001-grf  created 2026-06-02T11:54:38Z

Deploy commands followed the TC-027 path:
1. gcloud run deploy sadify-api --source .
   -> sadify-api-00004-x2b serving 100%
2. gcloud builds submit apps/web --config apps/web/cloudbuild.yaml
   -> build 0c5265f8-76b9-4575-8b72-e63e459aca53 SUCCESS
3. gcloud run deploy sadify-web --image .../sadify-web:latest
   -> sadify-web-00002-vzw serving 100%
4. gcloud run services update sadify-api --update-env-vars SADIFY_ALLOWED_ORIGINS=<frontend URL>
   -> sadify-api-00005-pc2 serving 100%

Post-deploy:
sadify-api latest ready sadify-api-00005-pc2
  image digest sha256:fc8ab92d1169993d38f310ab81c83e9d4c8a208ba9ec0a334ccc400b946d6816
sadify-web latest ready sadify-web-00002-vzw
  image digest sha256:b48443318d31cf189d3902f96067105a7da2be32ef9acdd4e8c48e80521e7102
Backend URL:  https://sadify-api-594758969655.asia-southeast1.run.app
Frontend URL: https://sadify-web-594758969655.asia-southeast1.run.app
```

Production smoke (2026-06-04):

```text
GET /health -> ok
GET /models -> default gemini-2.5-flash; models gemini-2.5-flash, gemini-2.5-pro, gemini-2.5-flash-lite

POST /analysis/requirement + POST /sad/preview with gemini-2.5-flash:
analysis_id AN-000001; preview_id SP-000001; preview_sections 13; IT readiness 35

POST /analysis/requirement + POST /sad/preview with gemini-2.5-pro:
analysis_id AN-000002; preview_id SP-000002; preview title "Damaged Returns Management System"; preview_sections 6; IT readiness 65

Cloud Logging:
recent sadify-api severity>=ERROR query over the deploy/smoke window returned no rows.
Request logs on sadify-api-00005-pc2 showed HTTP 200 for /models, /analysis/requirement, and /sad/preview.

Frontend:
GET https://sadify-web-594758969655.asia-southeast1.run.app -> HTTP 200, title "SADify".

Browser UI:
Temporary Playwright smoke selected `Gemini 2.5 Pro` in the deployed picker,
started the deployed Q&A flow, submitted a visible answer, confirmed the UI
kept `Gemini 2.5 Pro` selected, and captured a screenshot during the run.
The scratch Playwright runner and screenshot were removed after evidence was
recorded.
Result: `1 passed (45.1s)`.
```

## Differences / Issues

None for TC-032. The UI browser smoke intentionally bounded itself to model
selection plus one visible Q&A turn; SAD preview model routing was verified by
the live Pro `/sad/preview` API call and covered locally by frontend request
threading tests.

## Evidence

- Backend commits:
  - `c1f88f6 feat(models): add Gemini model catalog endpoint`
  - `9813e51 feat(models): thread optional model through analysis and preview`
  - `15f5946 feat(models): fail over unavailable Gemini selections`
  - `ae97f8e fix(models): restore gemini-2.5-pro with model-aware generation config`
- Frontend commit:
  - `e44951c feat(web): add dynamic Gemini model picker`
- Chat footer UX follow-up included in the deployed web image:
  - `0a98101 feat(web): collapse answer options between turns`
- `pytest`: `488 passed, 4 skipped`
- `npx tsc --noEmit`: passed
- `npm run build`: passed
- Live Vertex probe: Flash and Flash-Lite returned OK; Pro live JSON verified
  after model-aware config.
- Cloud Build: `0c5265f8-76b9-4575-8b72-e63e459aca53` SUCCESS.
- Cloud Run revisions: `sadify-api-00005-pc2`, `sadify-web-00002-vzw`.
- Production API smoke: Flash and Pro each returned analysis + SAD preview.
- Frontend reachability: HTTP 200, title `SADify`.
- Browser smoke: deployed picker selected Pro and completed one visible Q&A
  turn.

## Decision

Passed. TC-032 is deployed and production-smoked: real Q&A succeeded, real SAD
preview succeeded through the deployed backend, the browser picker switched to
`gemini-2.5-pro`, and Cloud Logging showed no recent model-routing or
generation errors.
