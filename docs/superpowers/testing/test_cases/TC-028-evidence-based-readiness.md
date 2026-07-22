# TC-028 Evidence-Based Readiness

Date Created: 2026-05-23
Last Updated: 2026-05-25
Status: Passed; manual browser smoke completed 2026-05-24

## Purpose

Validate that SADify draft readiness is based on quote-validated per-slot
evidence instead of hardcoded domain or phrase lists.

This test case became the Phase 4 foundation. Cycle 2A and Cycle 2B later
extended it with monotonic readiness, no-repeat Q&A behavior, and stronger SAD
synthesis.

## Inputs

Scenario 1 - vague text-only request:

```text
A shop wants a system to track things.
```

Scenario 2 - rich text-only request:

```text
Rich multi-paragraph operational request where most required SAD areas have
strong evidence and the remaining areas have partial evidence.
```

Scenario 3 - file-only upload smoke:

```text
Upload a business workflow PDF/DOCX/TXT and type a minimal prompt such as:
Please analyse the uploaded workflow and ask the next important question.
```

Scenario 4 - broad answers:

```text
Request plus broad vague answers that only partially answer required slots.
```

Scenario 5 - not-applicable category:

```text
Everything required is covered and integrations are explicitly not needed for
the first version.
```

## Preconditions

- Worktree: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`
- Local Python environment: `D:\GoogleCloudHack\.venv`
- No live Gemini or cloud calls are required for automated TC-028 checks.
- Tests must use `FakeRequirementAnalysisModel` or equivalent fake model output.
- TC-025 and TC-027 remain blocked until TC-026 Drive + Google Docs save passes.

## Steps

1. Run the automated scenario table:

```powershell
$env:PYTHONPATH="D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src;D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\src;D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold"
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_evidence_readiness_scenarios.py -q
```

2. Run full local verification from Task 10:

```powershell
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests -q
node apps\web\node_modules\typescript\bin\tsc -p apps\web\tsconfig.json --noEmit
npm --prefix apps\web run build
```

3. Manual smoke with a file-only or mostly-file context:
   - upload a workflow file;
   - wait until source traceability shows a source reference;
   - type a minimal request such as `Please analyse the uploaded workflow`;
   - start analysis;
   - confirm readiness follows source evidence, not the minimal typed text;
   - continue until draft-ready if appropriate;
   - confirm preview generation is not blocked by missing typed-text basics when
     uploaded source evidence covers the required basics.

## Expected Output

- Sparse requests score low unless actual evidence covers required slots.
- Rich requests score higher only when more required SAD areas have explicit
  evidence.
- Broad partial answers do not reach `100%`.
- `not_applicable` required slots do not reduce the score denominator.
- Partial/strong model verdicts without a quote found in the actual material are
  downgraded before readiness is calculated.
- Confidence is derived from validated evidence and downgrade count.
- The UI can display `not_applicable` areas under `Not relevant to this project`.
- SAD preview draft gate requires readiness plus no applicable required slot at
  no evidence.

## Real Output

Automated scenario table on 2026-05-23:

```text
tests/api/test_evidence_readiness_scenarios.py -q
4 passed
```

Full local verification on 2026-05-23:

```text
Full Python regression:
  D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests -q
  234 passed in 21.24s

Frontend TypeScript:
  node D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\node_modules\typescript\bin\tsc -p D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\tsconfig.json --noEmit
  passed

Next.js production build:
  npm --prefix D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web run build
  passed outside sandbox after sandbox blocked Node from lstat C:\Users\User
```

Manual file-only/browser smoke:

```text
Pending user browser smoke.
```

## Differences / Issues

- Scenario 3 is intentionally manual because it uses a real uploaded file and
  browser flow.
- TC-028 does not judge final SAD prose quality; that is the next cycle.

## Evidence

- Code commits:
  - `6c4507c feat: add SlotEvidence schema and plan slot evidence fields`
  - `4fb35ed feat: request per-slot evidence verdicts from the analysis model`
  - `72f85c2 feat: add slot evidence validation and confidence derivation`
  - `f4c4106 feat: build questionnaire plan and readiness from slot evidence`
  - `d6a820a feat: drive questionnaire readiness from validated slot evidence`
  - `93d2bb1 fix: require complete evidence before SAD preview draft gate`
  - `379e8b2 feat: show not-relevant questionnaire areas in the web UI`
  - `74f1103 test: add evidence readiness acceptance scenarios`
  - `29e3264 chore: evidence-based readiness verification pass`
- Design spec:
  `docs/superpowers/archive/specs/consolidated-specs.md`
- Implementation plan:
  `docs/superpowers/archive/plans/consolidated-plans.md`

## Decision

Passed. Automated TC-028 checks, Cycle 2A, Cycle 2B, and manual browser smoke
with laundry and event-rental PDFs completed. Phase 4 is closed; continue with
TC-026 Drive + Google Docs save path.
