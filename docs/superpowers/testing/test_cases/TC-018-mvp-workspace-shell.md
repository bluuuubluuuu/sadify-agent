# TC-018 MVP Workspace Shell

Date Created: 2026-05-11
Last Updated: 2026-05-12
Status: Passed

## Purpose

Verify the Next.js project workspace shell with user-friendly guided Q&A, readiness, category progress, change tracking, and expandable project status.

## Inputs

- Mocked backend project state
- Mocked question state
- Mocked change tracking state

## Preconditions

TC-017 passed.

## API / Docs Preflight

Checked official Next.js docs before coding:

- `https://nextjs.org/docs/app/getting-started/project-structure`
- `https://nextjs.org/docs/app/api-reference/file-conventions/page`
- `https://nextjs.org/docs/app/api-reference/config/typescript`
- `https://nextjs.org/docs/app/guides/testing/playwright`

External Google/Gemini/Drive APIs required: no.
Dependency install required: yes. `npm install` created `package-lock.json` and installed Next.js/React dependencies locally.

## Steps

1. Add failing workspace shell structure test.
2. Implement mocked workspace state and workspace UI components.
3. Build the Next.js app.
4. Start the standalone production server.
5. Open the workspace in a browser.
6. Confirm the current question, choices, amend field, readiness, category progress, tracking summary, and expandable status render.
7. Confirm browser console has no errors after interactions.

## Expected Output

The workspace focuses on the current question and necessary status only; technical details remain hidden by default in an expandable tracking section.

## Real Output

Implemented in MVP worktree `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`.

- Home route renders a mocked project workspace shell.
- Current question shows plain-language choices and an amend field.
- Readiness panel shows score, confidence, and questionnaire sections.
- Change tracking is visible, with detailed status hidden inside an expandable section.
- Standalone build output copies static assets so `node .next/standalone/server.js` can serve the UI without missing chunks.

## Differences / Issues

Known issue: `npm audit --audit-level=moderate` reports a moderate PostCSS advisory through Next.js. The suggested `npm audit fix --force` would install a breaking/downgrade path, so it was not applied in this checkpoint.

In-app Browser plugin path failed because no Codex IAB backend was discoverable. Regular Playwright CLI was used as fallback.

## Evidence

Red test evidence:

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\test_mvp_workspace_shell.py -q
FAILED tests/test_mvp_workspace_shell.py::test_workspace_shell_files_exist
FAILED tests/test_mvp_workspace_shell.py::test_workspace_shell_renders_qna_readiness_and_tracking
2 failed in 0.32s
```

Green focused test evidence:

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\test_mvp_workspace_shell.py -q
2 passed in 0.06s
```

Full Python regression evidence:

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe -q
97 passed in 15.71s
```

Frontend build evidence:

```text
npm run build
Compiled successfully
Route (app): /, /_not-found, /icon.svg
prepare:standalone completed
```

Browser smoke evidence:

```text
URL: http://localhost:3000/
Title: SADify
Console errors: 0
Console warnings: 0
Interaction: expanded Tracking status and filled Amend answer.
Responsive check: desktop and 390x844 mobile viewport.
```

## Decision

Passed. Proceed to MVP-04 only after user approval.
