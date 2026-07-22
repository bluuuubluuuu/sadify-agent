# TC-020 MVP Guest Draft Migration

Date Created: 2026-05-11
Last Updated: 2026-05-13
Status: Passed

## Purpose

Verify guest draft persistence and safer signed-in migration copy. This checkpoint uses the local backend fake store first; Firestore cloud persistence remains a later integration after the local contract is stable.

## Inputs

- Guest draft ID
- Guest requirement input
- Signed-in Firebase user

## Preconditions

TC-019 passed.

## Steps

1. Start as guest and create a draft.
2. Save the guest draft to the backend fake store.
3. Sign in.
4. Confirm SADify asks whether to continue the guest draft.
5. Approve migration.
6. Confirm a signed-in project copy is created and the guest draft remains linked.

## Expected Output

Guest draft remains intact, signed-in project copy exists, and migration metadata links both records. The UI should show that the guest draft is kept for audit.

## Real Output

Implemented in MVP worktree `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`.

- Added backend guest draft schemas, in-memory repository, and `/drafts/guest` API route.
- Added safe migration copy route `/drafts/guest/{guest_draft_id}/migrate`.
- Migration requires a verified Firebase bearer token.
- Migration creates a signed-in project copy and updates the original guest draft to `migrated` with `migrated_to_project_id`.
- Guest draft content remains available for audit; migration is copy-based, not destructive.
- Added frontend `DraftPanel` with `Start guest draft` and `Copy to signed-in project` controls.
- Browser smoke on temporary local ports verified the guest draft create flow rendered and called the backend.

## Differences / Issues

This checkpoint did not write to real Firestore cloud. It proves the local safer migration contract and API/UI wiring first. Real Firestore client persistence and cloud smoke remain future work before deployed MVP.

Production `npm run build` was not run in this checkpoint because the user's own standalone frontend server was running on port `3000` and holding `.next\standalone`. TypeScript validation and dev-server browser smoke were run instead.

## Evidence

API/docs preflight checked official docs before implementation:

```text
https://firebase.google.com/docs/firestore/manage-data/add-data
https://firebase.google.com/docs/firestore/query-data/get-data
https://cloud.google.com/firestore/docs/samples/firestore-data-set-doc-upsert
https://cloud.google.com/firestore/docs/samples/firestore-data-get-as-map
https://cloud.google.com/python/docs/reference/firestore/latest
https://firebase.google.com/docs/admin/setup
```

Red tests:

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_guest_drafts.py -q
ModuleNotFoundError: No module named 'sadify_api.services.guest_drafts'
```

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\test_mvp_guest_draft_ui.py -q
2 failed: DraftPanel.tsx missing
```

Focused green tests:

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_guest_drafts.py -q
4 passed in 1.17s
```

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\test_mvp_guest_draft_ui.py -q
2 passed in 0.15s
```

Selected regressions:

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_guest_drafts.py tests\api\test_auth_session.py tests\api\test_health_contract.py -q
11 passed in 1.53s
```

Full Python regression:

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe -q
109 passed in 9.64s
```

Frontend TypeScript:

```text
npx tsc --noEmit
exit 0
```

Temporary local smoke servers:

```text
Backend: http://127.0.0.1:8001/health -> 200
Frontend: http://127.0.0.1:3001/ -> 200
```

Browser smoke:

```text
Page title: SADify
DraftPanel visible: true
Copy to signed-in project button visible: true
Clicked Start guest draft
Guest draft ID visible: true
Active status visible: true
Guest draft kept for audit visible: true
Console errors/warnings: 0
```

## Decision

Passed for the local MVP-05 fake-store slice. Next checkpoint is MVP-06 / TC-021 live Gemini structured Q&A after user approval. Firestore cloud persistence remains explicitly deferred.
