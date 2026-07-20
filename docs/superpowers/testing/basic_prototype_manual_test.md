# SADify Basic Prototype Manual Test

Date: 2026-05-11
Status: Passed with known Drive config follow-up

## Purpose

Use this checklist to test the deployed basic SADify prototype before starting the next improvement phase.

Prototype boundary:

```text
This test verifies the deployed deterministic prototype.
It does not verify live Gemini, Firestore cloud save/read, Google Drive export, Google Docs export, or Cloud Run log review.
```

## Test URL

```text
https://sadify-app-ohzgmdegca-as.a.run.app
```

## Test 1: App Loads

Steps:

1. Open the test URL.
2. Wait for the SADify page to load.
3. Check the left sidebar.

Expected result:

- Page title shows `SADify`.
- Sidebar shows `Project: sadify`.
- Sidebar shows `Provider: google`.
- Sidebar shows `Model: gemini-2.5-flash`.
- Sidebar shows `Environment: cloud`.
- Sidebar shows `Service account: configured`.
- `Drive folder: missing` is acceptable for the basic prototype baseline.

Pass/fail:

```text
Result: Passed by user manual test on 2026-05-11.
Notes: Drive folder still shows missing; accepted as known follow-up for the basic prototype baseline.
```

## Test 2: Strong Requirement Analysis

Paste this into the business request box:

```text
Warehouse staff record stock movement when goods are received, picked, packed, and dispatched. Operators scan item codes, enter quantity, location, date, and status. Supervisors review rejected or corrected records. Managers need a daily dashboard and weekly export. The system needs role-based access and audit history.
```

Steps:

1. Click `Check what is still unclear`.
2. Review the analysis output.

Expected result:

- `What SADify understands` appears.
- Readiness shows `100%`.
- Confidence shows `High`.
- Current mode shows `deterministic`.
- `What we still need to know` says the request includes the main business details.
- A draft-preparation message appears.

Pass/fail:

```text
Result: Passed by user manual test on 2026-05-11.
Notes:
```

## Test 3: Weak Requirement Analysis

Paste this into the business request box:

```text
We need a better inventory system.
```

Steps:

1. Click `Check what is still unclear`.
2. Review readiness, confidence, gaps, and questions.

Expected result:

- Readiness is lower than the strong requirement.
- Confidence is not `High`.
- SADify lists missing details.
- SADify asks clarification questions about process, users, data, controls, reports, or operating needs.

Pass/fail:

```text
Result: Passed by user manual test on 2026-05-11.
Notes:
```

## Test 4: File Upload Context

Use this local file:

```text
tmp/manual-test/warehouse-stock-movement.txt
```

Steps:

1. Open the deployed app.
2. Upload the file under `Add business files`.
3. Optionally add short text in the request box.
4. Click `Check what is still unclear`.

Expected result:

- App accepts the `.txt` file.
- File appears under readable business files or is included in extracted context.
- Analysis still renders without an error.
- The uploaded file content helps SADify identify stock movement, users, reports, and controls.

Pass/fail:

```text
Result: Passed by user manual test on 2026-05-11.
Notes:
```

## Test 5: Refresh Stability

Steps:

1. Refresh the browser page.
2. Repeat Test 2.

Expected result:

- App reloads successfully.
- Strong requirement analysis still renders.
- No visible app crash or error page appears.

Pass/fail:

```text
Result: Passed by user manual test on 2026-05-11.
Notes:
```

## Overall Decision

Pass the basic prototype if:

- Test 1 passes.
- Test 2 passes.
- Test 3 produces useful missing-info questions.
- Test 4 does not crash.
- Test 5 passes.

Known follow-up improvements:

- Configure deployed Drive folder runtime config. Current deployed app still shows `Drive folder: missing`.
- Add live Gemini smoke.
- Add Firestore cloud save/read smoke.
- Add Drive/Docs export smoke.
- Review Cloud Run logs from Cloud Shell or authenticated Google Cloud CLI.
