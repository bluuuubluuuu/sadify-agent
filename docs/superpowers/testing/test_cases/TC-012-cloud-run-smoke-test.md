# TC-012 Cloud Run Smoke Test

Date Created: 2026-04-30
Last Updated: 2026-05-11
Status: Passed

## Purpose

Verify that the deployed Cloud Run app can complete the basic prototype path.

For the 2026-05-11 baseline, the basic prototype path is intentionally
cost-safe and deterministic:

```text
deployed app loads
-> user submits a business requirement
-> SADify renders understanding, readiness, confidence, gaps, and questions
```

Live Gemini, Firestore cloud writes, Google Drive/Docs upload, and Cloud Run log
administration are deferred to the first improvement slice. They are not marked
as passed by this test.

## Traceability Sources

- `docs/superpowers/development/05_development_workflow.md` - Checkpoint 15
- `docs/superpowers/development/04_google_cloud_setup_runbook.md` - Cloud Run deployment and cost controls
- `docs/superpowers/development/06_demo_script_and_acceptance_checklist.md` - demo acceptance gate
- `docs/superpowers/testing/test_case_index.md`

## Inputs

Small demo requirement text and one simple supported business file if available.

## Preconditions

Local MVP has passed, Cloud Run deployment exists, budget alert is active.

## Steps

1. Open the Cloud Run service URL.
2. Verify the Streamlit health endpoint.
3. Submit demo warehouse stock movement requirement.
4. Confirm deployed runtime metadata is visible.
5. Confirm deterministic requirement analysis renders.
6. Capture browser evidence.
7. Record deferred live-cloud integration checks.

## Expected Output

- deployed app loads
- health endpoint returns `200 ok`
- deployed runtime shows project `sadify`
- deployed runtime shows environment `cloud`
- deployed runtime shows service account configured
- basic deterministic requirement flow works
- readiness, confidence, and current mode render without a page crash

## Real Output

Passed for the basic deployed prototype.

Command evidence:

```text
Command: Invoke-WebRequest -Uri "https://sadify-app-ohzgmdegca-as.a.run.app/_stcore/health" -UseBasicParsing
Result: StatusCode 200, Content ok
```

Playwright browser evidence:

- URL loaded: `https://sadify-app-ohzgmdegca-as.a.run.app`
- Page title: `SADify`
- Runtime sidebar showed `Project: sadify`.
- Runtime sidebar showed `Environment: cloud`.
- Runtime sidebar showed `Provider: google`.
- Runtime sidebar showed `Model: gemini-2.5-flash`.
- Runtime sidebar showed `Service account: configured`.
- Runtime sidebar showed `Drive folder: missing`.
- A warehouse stock movement requirement was submitted.
- The app rendered `What SADify understands`.
- Readiness displayed `100%`.
- Confidence displayed `High`.
- Current mode displayed `deterministic`.

User-provided browser screenshot showed the same deployed behavior.

Not run yet:

- live Gemini call
- Firestore cloud save/read
- Google Drive or Google Docs export
- Cloud Run log review

## Differences / Issues

- The deployed runtime reports `Drive folder: missing`, so Drive/Docs export cannot be treated as ready.
- The current Streamlit app only exposes deterministic requirement analysis. It does not expose a live Gemini action, a real Firestore save/read action, or a real Drive/Docs upload action.
- Local Google Cloud administration is not available on this machine: `gcloud` is not installed and ADC is not configured. Therefore Cloud Run logs were not reviewed from this environment.
- These issues are accepted as improvement backlog items, not blockers for the basic prototype baseline.

## Evidence

- Health endpoint command returned `200 ok`.
- Playwright snapshot after submit showed `What SADify understands`, `Readiness 100%`, `Confidence High`, and `Current mode deterministic`.
- Screenshot artifact: `output/playwright/c15-cloud-run-deterministic-smoke.png`
- User-provided browser screenshot in the current Codex thread, dated 2026-05-11.

## Decision

Passed as the basic deployed prototype smoke.

Baseline result:

```text
Deployed app loads and deterministic requirement analysis renders.
```

Improvement backlog:

```text
1. Configure SADIFY_DRIVE_ROOT_FOLDER_ID on the Cloud Run service through a safe runtime config path.
2. Add or expose a live Gemini smoke path.
3. Add or expose a Firestore cloud save/read smoke path.
4. Add or expose at least one Drive/Docs export smoke path.
5. Install/authenticate Google Cloud CLI or ADC locally, or run log review from Cloud Shell.
```
