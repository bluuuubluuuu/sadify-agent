# TC-017 MVP FastAPI Health And Contract

Date Created: 2026-05-11
Last Updated: 2026-05-12
Status: Passed

## Purpose

Verify the FastAPI backend health, config diagnostics, error shape, and typed response contract foundation.

## Inputs

- FastAPI backend service
- Health endpoint
- Diagnostics endpoint or hidden-dev diagnostics route

## Preconditions

TC-016 passed.

## API / Docs Preflight

Checked official FastAPI docs before coding:

- `https://fastapi.tiangolo.com/tutorial/first-steps/`
- `https://fastapi.tiangolo.com/tutorial/testing/`
- `https://fastapi.tiangolo.com/tutorial/bigger-applications/`

External API/cloud access required: no.
Dependency install required: no. Existing `.venv` already had `fastapi 0.136.1`, `uvicorn 0.46.0`, and `httpx 0.28.1`.

## Steps

1. Add a failing FastAPI `TestClient` contract test for `/health`.
2. Verify the test fails because `/health` only returns `{"status": "ok"}`.
3. Add typed config, response schemas, health route, and redacted diagnostics route.
4. Verify config diagnostics exposes only non-secret runtime details.
5. Verify diagnostics can be disabled.
6. Run focused API tests and full Python regression.

## Expected Output

Backend returns healthy status, typed JSON responses, and redacted diagnostics without exposing secrets.

## Real Output

Implemented in MVP worktree `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`.

- `/health` returns `status`, `service`, and `environment`.
- `/diagnostics/config` returns redacted config diagnostics when enabled.
- `/diagnostics/config` is not registered when diagnostics are disabled.
- Root pytest config includes `services/api/src`, so normal repo-level pytest can import `sadify_api`.

## Differences / Issues

Standalone browser/server smoke was not run in this checkpoint; FastAPI behavior was validated through `TestClient`.

## Evidence

Red test evidence:

```text
tests\api\test_health_contract.py::test_health_returns_backend_contract
AssertionError: assert {'status': 'ok'} == {'status': 'ok', 'service': 'sadify-api', 'environment': 'test'}
1 failed in 1.43s
```

Green focused contract evidence:

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_health_contract.py -q
...                                                                      [100%]
3 passed in 1.19s
```

API suite evidence:

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api -q
...                                                                      [100%]
3 passed in 0.98s
```

Full regression evidence:

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe -q
........................................................................ [ 75%]
.......................                                                  [100%]
95 passed in 8.07s
```

## Decision

Passed. Proceed to MVP-03 only after user approval.
