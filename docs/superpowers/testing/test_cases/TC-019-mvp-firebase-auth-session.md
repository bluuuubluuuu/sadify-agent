# TC-019 MVP Firebase Auth Session

Date Created: 2026-05-11
Last Updated: 2026-05-13
Status: Passed

## Purpose

Verify persistent Google sign-in through Firebase Auth / Google Identity Platform and backend identity verification.

## Inputs

- Firebase Auth / Google Identity Platform configuration
- Frontend sign-in flow
- Backend token verification endpoint

## Preconditions

TC-017 and TC-018 passed.

## API / Docs Preflight

Checked official docs before coding:

- `https://firebase.google.com/docs/auth/web/start`
- `https://firebase.google.com/docs/auth/web/google-signin`
- `https://firebase.google.com/docs/auth/web/auth-state-persistence`
- `https://firebase.google.com/docs/auth/admin/verify-id-tokens`
- `https://firebase.google.com/docs/admin/setup`
- `https://fastapi.tiangolo.com/tutorial/cors/`

Rechecked official docs on 2026-05-13 before attempting live verification:

- `https://firebase.google.com/docs/web/learn-more`
- `https://firebase.google.com/docs/auth/web/start`
- `https://firebase.google.com/docs/auth/web/google-signin`
- `https://firebase.google.com/docs/auth/web/auth-state-persistence`
- `https://firebase.google.com/docs/auth/admin/verify-id-tokens`
- `https://firebase.google.com/docs/admin/setup`

External cloud/API calls required for local contract: no.
Live Google sign-in required for full pass: yes. On 2026-05-13, Firebase web config and local backend Firebase Admin credentials were added outside git and live local sign-in verification passed.

Dependencies added:

- Frontend: `firebase 12.13.0`
- Backend: `firebase-admin 7.4.0`

## Steps

1. Add failing backend auth session contract tests.
2. Add failing frontend auth scaffold tests.
3. Implement Firebase config guard, local persistence setup, Google sign-in client flow, backend session verification route, and auth CORS preflight.
4. Verify missing and invalid tokens are rejected without echoing token values.
5. Build frontend and smoke-test current no-config UI state.
6. Defer live Google sign-in until Firebase web config is present.

## Expected Output

Local contract: guest mode remains available, Google sign-in is visible but blocked until config exists, backend verifies bearer tokens through Firebase Admin verifier, and token values are not echoed.

Full live output: user session remains live after refresh and backend verifies real Firebase ID token.

## Real Output

Implemented in MVP worktree `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`.

- Frontend session panel renders guest mode, `Continue as guest`, `Sign in with Google`, and `Firebase config needed`.
- Firebase Web SDK setup uses `browserLocalPersistence`, `onAuthStateChanged`, `GoogleAuthProvider`, and `signInWithPopup`.
- Backend exposes `/auth/session` and `/auth/me`.
- Backend uses injectable verifier for tests and Firebase Admin verifier for real tokens.
- Backend CORS allows `Authorization` from `http://localhost:3000`.
- Revalidated on 2026-05-13: local auth tests, full Python regression, frontend production build, and no-config HTTP smoke still pass.
- Live verification on 2026-05-13: Google sign-in returned to SADify, UI showed the correct signed-in session message, and backend `/auth/session` returned `200 OK`.

## Differences / Issues

Local live verification depends on ignored local files/env vars:

```text
Frontend Firebase web config: apps\web\.env.local
Backend Firebase Admin credential: GOOGLE_APPLICATION_CREDENTIALS pointing to a local service-account JSON under D:\GoogleCloudHack\.secrets\
```

Do not commit or paste the Firebase Admin JSON.

`npm audit --audit-level=moderate` still reports the same moderate PostCSS advisory through Next.js. The suggested `npm audit fix --force` would install a breaking/downgrade path, so it was not applied.

## Evidence

Red test evidence:

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_auth_session.py -q
ModuleNotFoundError: No module named 'sadify_api.services'
```

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\test_mvp_auth_session_scaffold.py -q
2 failed: AuthPanel/firebase auth files missing
```

CORS red test evidence:

```text
FAILED test_auth_session_allows_frontend_cors_preflight
assert 405 == 200
```

Green evidence:

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api -q
7 passed in 1.12s
```

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe -q
103 passed in 10.13s
```

```text
npm run build
Compiled successfully
prepare:standalone completed
```

Browser smoke evidence:

```text
URL: http://localhost:3000/
Title: SADify
Guest mode visible
Continue as guest visible/clickable
Sign in with Google visible/disabled
Firebase config needed visible
Console errors: 0
Console warnings: 0
Desktop and 390x844 mobile viewport checked
```

2026-05-13 preflight and revalidation evidence:

```text
Official Firebase docs rechecked for web config, web auth start, Google sign-in, auth persistence, Admin ID token verification, and Admin SDK setup.
Firebase web config object requires valid apiKey, projectId, and appId; authDomain is also needed for Auth.
Google sign-in requires Google provider enabled in Firebase Auth.
Local persistence is valid for staying signed in until explicit sign-out.
Backend should receive the client ID token and verify it with Firebase Admin SDK.
```

Environment presence check, values redacted:

```text
D:\GoogleCloudHack\.env: GOOGLE_CLOUD_PROJECT present; Firebase web keys, FIREBASE_PROJECT_ID, and GOOGLE_APPLICATION_CREDENTIALS missing.
D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\.env: missing-file.
D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\.env.local: missing-file.
```

After Firebase setup, values still redacted:

```text
D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\.env.local exists.
NEXT_PUBLIC_FIREBASE_API_KEY=present
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=present
NEXT_PUBLIC_FIREBASE_PROJECT_ID=present
NEXT_PUBLIC_FIREBASE_APP_ID=present
NEXT_PUBLIC_SADIFY_API_BASE_URL=present
Firebase Admin JSON exists locally, type=service_account, project_id=sadify, private_key=present.
```

Focused TC-019 local regression:

```text
$env:PYTHONPATH="services/api/src;src;."
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_auth_session.py tests\test_mvp_auth_session_scaffold.py -q
6 passed in 1.44s
```

Full Python regression:

```text
$env:PYTHONPATH="services/api/src;src;."
D:\GoogleCloudHack\.venv\Scripts\pytest.exe -q
103 passed in 12.48s
```

Frontend build:

```text
npm run build
Compiled successfully
prepare:standalone completed
```

No-config local HTTP smoke against the built Next standalone server:

```text
GET http://127.0.0.1:3000/
status=200
contains_SADify=True
contains_Guest_mode=True
contains_Firebase_config_needed=True
```

Live local Firebase sign-in verification:

```text
Backend started with:
FIREBASE_PROJECT_ID=sadify
GOOGLE_CLOUD_PROJECT=sadify
GOOGLE_APPLICATION_CREDENTIALS=D:\GoogleCloudHack\.secrets\sadify-firebase-adminsdk-fbsvc-ac7a32c920.json

Backend evidence:
OPTIONS /auth/session HTTP/1.1" 200 OK
POST /auth/session HTTP/1.1" 200 OK
POST /auth/session HTTP/1.1" 200 OK

UI evidence:
Session panel showed the correct signed-in message:
"Signed in. Your session will stay live on this browser."
```

## Decision

Passed. TC-019 now verifies Firebase Google sign-in, local browser session persistence after returning to SADify, frontend session messaging, CORS preflight, and backend Firebase ID-token verification through `/auth/session`.
