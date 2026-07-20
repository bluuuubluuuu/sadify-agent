# TC-016 MVP Monorepo Scaffold

Date Created: 2026-05-11
Last Updated: 2026-05-11
Status: Passed

## Purpose

Verify that the repo can host the MVP Next.js frontend and FastAPI backend without breaking the existing Python prototype baseline.

## Inputs

- Proposed `apps/web/`
- Proposed `services/api/`
- Existing `src/sadify/`
- Existing `sadify_agent/`

## Preconditions

TC-015 passed.

## Steps

1. Run API/docs preflight.
2. Create an isolated worktree for MVP-01.
3. Create the failing scaffold test.
4. Verify the test fails before scaffold files exist.
5. Create the monorepo scaffold.
6. Keep existing Python tests runnable.
7. Run scaffold-specific tests.
8. Run the full existing Python suite.

## Expected Output

The frontend and backend folders exist, dependency setup is documented, and existing Python tests still pass.

## Real Output

Passed. MVP-01 created the initial monorepo scaffold in an isolated worktree on branch `codex/mvp-monorepo-scaffold`.

Created scaffold paths:

```text
apps/web/package.json
apps/web/next.config.ts
apps/web/tsconfig.json
apps/web/src/app/layout.tsx
apps/web/src/app/page.tsx
apps/web/src/app/globals.css
services/api/pyproject.toml
services/api/src/sadify_api/__init__.py
services/api/src/sadify_api/main.py
tests/test_mvp_scaffold.py
```

The Next.js scaffold is minimal and not dependency-installed yet. The FastAPI scaffold defines a minimal `create_app()` and `/health` path, but the formal FastAPI contract test is reserved for MVP-02 / TC-017.

## Differences / Issues

No blocking scaffold issue found.

Notes:

- `node --version` worked locally and returned `v20.19.5`.
- `npm --version` required escalated execution because sandboxed npm attempted to access `C:\Users\User`; with approval it returned `10.8.2`.
- `uvicorn` was not found on PATH before dependency installation. This is expected because MVP-01 does not install FastAPI runtime dependencies. MVP-02 will install/verify FastAPI, Uvicorn, and TestClient dependencies.
- Frontend `npm install` and `npm run build` were not run in MVP-01 to avoid network/dependency installation before the scaffold checkpoint. They belong to MVP-03 unless explicitly pulled earlier.

## Evidence

API/docs preflight:

```text
External API/docs fetch required: yes, because the checkpoint creates Next.js and FastAPI scaffold files.
Cloud/billing/OAuth/IAM/deployment required: no.
Dependency install required: no for MVP-01.
```

Official docs checked:

```text
Next.js installation and create-next-app:
https://nextjs.org/docs/app/getting-started/installation
https://nextjs.org/docs/app/api-reference/cli/create-next-app

FastAPI first steps, testing, and bigger applications:
https://fastapi.tiangolo.com/tutorial/first-steps/
https://fastapi.tiangolo.com/tutorial/testing/
https://fastapi.tiangolo.com/tutorial/bigger-applications/
```

Worktree:

```text
git worktree add .worktrees\mvp-monorepo-scaffold -b codex/mvp-monorepo-scaffold
HEAD is now at b7cc44f chore: ignore local tool worktrees
Preparing worktree (new branch 'codex/mvp-monorepo-scaffold')
```

Baseline verification before scaffold:

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe -q
```

Result:

```text
91 passed in 8.73s
```

Red test verification:

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\test_mvp_scaffold.py -q
```

Result:

```text
1 failed
Missing:
apps\web\package.json
apps\web\src\app\page.tsx
services\api\pyproject.toml
services\api\src\sadify_api\main.py
```

Green scaffold test:

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\test_mvp_scaffold.py -q
```

Result:

```text
1 passed in 0.03s
```

Full Python regression:

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe -q
```

Result:

```text
92 passed in 6.56s
```

## Decision

Passed. Stop and return summary before MVP-02.
