# TC-024 MVP SAD Preview And IT Readiness

Date Created: 2026-05-11
Last Updated: 2026-05-20
Status: Passed; historical MVP-09 gate

## Purpose

Verify SAD preview generation after blocking basics, IT-readiness checklist, assumptions, source traceability, and change tracking summary.

## Inputs

- Requirement with problem, goal, users/roles, and workflow
- Gemini structured SAD preview response
- Existing canonical SAD concepts

## Preconditions

TC-021 passed.

## API / Docs Preflight

Official docs checked before coding:

- Gemini API structured outputs: `https://ai.google.dev/gemini-api/docs/structured-output`
- Vertex AI structured output: `https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output`

Preflight decision:

- MVP-09 should use Gemini structured JSON for the production route, with app-side Pydantic validation before any preview state is accepted.
- Keep the SAD preview schema modest and ordered because Vertex structured output supports only a schema subset and complex schemas can be rejected.
- Do not save any Drive/Docs files in this checkpoint.
- To avoid extra cloud credit usage, verification should use fake structured model tests and local frontend smoke. A live Gemini preview click can be tested later with explicit approval.

## Steps

1. Complete blocking basics.
2. Generate a temporary SAD preview.
3. Validate SAD JSON schema.
4. Show readiness label, score, confidence, assumptions, open questions, and source references.
5. Show one-line change tracking summary with expandable paths.

## Expected Output

SAD preview is useful without pretending to be final, and all assumptions/open questions are visible before save.

## Real Output

MVP worktree `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold` now has:

- Backend `/sad/preview` route.
- Pydantic SAD preview schema with:
  - temporary preview notice
  - structured SAD sections
  - IT readiness label, score, confidence, and checklist
  - assumptions
  - open questions
  - source references
  - change tracking summary and planned paths
- Local `SadPreviewRepository` with stable `SP-` preview IDs.
- Blocking-basics gate for `problem`, `goal`, `users_roles`, and `workflow`; missing basics return `HTTP 409` and do not call the model.
- Gemini production adapter for structured SAD preview generation, using the same Vertex AI / `gemini-2.5-flash` config path.
- Repair-once behavior if Gemini returns schema-invalid JSON.
- Frontend `SadPreviewPanel` after the Q&A panel.
- Workspace state updates showing one-line change tracking and expandable status after a preview is generated.
- Preview UI labels stay user-facing: `Temporary preview`, `IT readiness`, `Assumptions`, `Open questions`, `Source refs`, and `Tracking status`.
- Manual live local smoke on 2026-05-14 reached `/auth/session`, `/analysis/requirement`, and `/sad/preview` with `HTTP 200`, generated temporary preview `SP-000001`, and showed IT readiness/open questions in the UI.
- Post-MVP-09 stabilization wired answer choice/amendment continuation before preview generation so users can answer one question and refresh the next question instead of being stuck at the first Q&A prompt.

## Differences / Issues

- Initial verification used fake structured model tests; a later manual local live SAD preview smoke was run with explicit user action.
- No Drive, Docs, Firestore cloud, Secret Manager, or Cloud Run deployment happened.
- Manual clicking `Generate SAD preview` or `Continue with answer` against the real backend will call Gemini and consume model tokens.
- The preview is backend-local state only; it is not yet saved to Google Docs or the wiki.
- Deployed two-service smoke remains deferred until the deployment checkpoint.

## Evidence

- Red test first: focused pytest initially failed because `SadPreviewResponse` and `SadPreviewPanel.tsx` did not exist.
- Focused tests after implementation: `8 passed in 1.19s`.
- Full Python regression after stabilization: `138 passed in 13.25s`.
- TypeScript check: `node ...\typescript\bin\tsc -p ...\apps\web\tsconfig.json --noEmit` exited `0`.
- Production build: `npm --prefix ...\apps\web run build` completed successfully.
- Local rendered smoke on `http://127.0.0.1:3012/` returned `HTTP 200` and confirmed HTML contained `SAD preview`, `Generate SAD preview`, `Temporary preview`, `IT readiness`, and `Tracking status`.
- Temporary smoke server on port `3012` was stopped after validation.
- Manual live local smoke evidence from user terminal/UI on 2026-05-14:

```text
POST /auth/session HTTP/1.1 200 OK
POST /analysis/requirement HTTP/1.1 200 OK
POST /sad/preview HTTP/1.1 200 OK
Temporary preview SP-000001 saved in backend state.
```

## Decision

Passed for the local MVP-09 gate. At the time, the next expected gate was
MVP-10 / TC-025. Current execution has since inserted the Phase 3 and Phase 4
quality gates: TC-021S and TC-021T passed, TC-021U passed route safety, TC-021V
partially passed, TC-021W automated checks passed, and TC-021X evidence-first
Q&A depth passed local checks but failed broader manual progression. TC-021Y is
now the active blocker before wiki work resumes.
