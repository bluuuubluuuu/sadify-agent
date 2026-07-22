# TC-021 MVP Live Gemini Q&A

Date Created: 2026-05-11
Last Updated: 2026-05-20
Status: Passed; historical baseline for later TC-021R/S/T/U/V/W refinements

## Purpose

Verify live Gemini structured analysis, next-question generation, choices, answer interpretation, and saved Q&A state.

## API / Docs Preflight

Checked on 2026-05-13 before implementation:

- Vertex AI Gemini quickstart: `https://cloud.google.com/vertex-ai/generative-ai/docs/start/quickstart`
- Vertex AI structured output: `https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output`

Relevant current requirements:

- Python SDK path: `google-genai`
- Vertex env/config: `GOOGLE_GENAI_USE_VERTEXAI=True`, `GOOGLE_CLOUD_PROJECT=sadify`, `GOOGLE_CLOUD_LOCATION=global`
- Model: `gemini-2.5-flash`
- IAM: caller needs Vertex AI User / `aiplatform.endpoints.predict`
- Structured output: use `response_mime_type=application/json` and `response_schema`
- Schema should stay small because complex structured-output schemas can cause Vertex `400` errors

## Inputs

- Generic test requirement: clinic team follow-up call tracking
- Gemini model route `google / gemini-2.5-flash`
- Strict response schema for:
  - understanding summary
  - readiness score and confidence
  - questionnaire categories
  - one next question
  - answer choices
  - assumptions
  - source references

## Preconditions

TC-017 and TC-020 passed.

## Steps

1. Submit a requirement through the MVP backend.
2. Call Gemini for structured analysis.
3. Validate the JSON response against schema.
4. Render one plain-language question with choices, amend option, and why-this-matters.
5. Save Q&A state.
6. Select a choice or type an amendment and continue to the next Gemini question.

## Expected Output

Gemini produces schema-valid analysis and one simple prioritized question. Invalid model output is rejected or repaired before rendering/saving.

## Real Output

Automated/local wiring was implemented and passed:

- Backend schemas, parser, Vertex-compatible schema helper, route, lazy Gemini adapter, retry-on-invalid-output, and local Q&A state repository were added.
- Frontend `AnalysisPanel` was added and wired to `/analysis/requirement`.
- The UI can show the generated question, choices, amend field, readiness, and tracking status after a valid backend response.
- Post-MVP-09 stabilization on 2026-05-14 wired answer choice selection, amendment text, and `Continue with answer` so the previous question/answer is sent back into `/analysis/requirement` and the next Gemini question refreshes.
- Follow-up stabilization on 2026-05-14 preserves the selected answer for SAD preview if Gemini returns invalid structured JSON while preparing the next question.
- Follow-up stabilization on 2026-05-14 made the answer action more obvious: the selected answer is shown beside a primary `Save answer and ask next question` button, with `Sending answer...` while the request is in flight.
- Backend follow-up stabilization on 2026-05-14 now saves a conservative local fallback question if Gemini still returns invalid structured Q&A after the repair retry, preventing repeated `HTTP 502` dead ends for the same business context.
- Fallback follow-up on 2026-05-14 was corrected after manual testing: fallback no longer increases readiness just because more fallback answers were clicked, and it now asks a targeted fallback question based on the selected focus such as business rules, data/reports, workflow exceptions, or users/roles.
- Q&A logic stabilization on 2026-05-14 added explicit `selection_mode` support. Top-level clarification choices stay single-select, while category-specific questions can be single-select or multi-select when more than one answer may be true.
- Answered fallback top-level categories are now returned as disabled choices with an `Answered locally` status label, so users can see what changed without re-answering the same broad category.
- `I'm not sure` is now treated as a flagged uncertainty answer. The backend keeps readiness low and asks an easier suggested-default follow-up with yes/no/other-style choices instead of pretending the category is complete.
- The frontend now lets users deselect a choice by clicking it again, disables answered categories, makes the active answer state visible, and blocks continuation until a valid answer exists.
- Amendment text is now gated: users choose an answer first, optional details can be added after that, and `Other / not listed` requires details before continuing.
- Frontend fallback messaging now labels backend fallback honestly instead of saying the question was refreshed from Gemini.
- Starting a fresh analysis resets the local answer history so old answers do not leak into a new business request.
- The lower tracking card now displays choices as read-only status unless an answer handler is deliberately supplied, avoiding dead clickable buttons.
- Invalid model JSON is retried once and refused if still invalid.

Live Gemini smoke passed after granting `roles/aiplatform.user` to:

```text
firebase-adminsdk-fbsvc@sadify.iam.gserviceaccount.com
```

The backend returned:

```text
HTTP 200
analysis_id: AN-000001
saved: True
readiness.score: 30
readiness.confidence: Medium
next_question: When tracking patient follow-up calls, what specific information is most important for the clinic team to record for each call?
choices: 5
```

## Differences / Issues

- The Q&A state save is currently the MVP local backend repository, matching the MVP-05 fake-store boundary. Real Firestore cloud persistence remains deferred.
- No Cloud Run deployment or deployed smoke was performed for this checkpoint.
- One successful local live Gemini request was made after IAM was fixed; exact billing impact is not available from the command output.
- Manual answer continuation calls `/analysis/requirement` again and will consume one Gemini call per submitted answer when the real backend is configured.
- If Gemini returns invalid structured output, the backend now uses a low-confidence local fallback question after the repair retry. This keeps the prototype usable, but the fallback question is less tailored than a valid Gemini response.
- Fallback readiness stays at low confidence and `35%`; a higher readiness score should come from validated Gemini analysis or SAD preview, not repeated fallback clicks.
- Fallback category status is still local/backend-state behavior. Durable recall after reopening the same project repo is deferred until the Firestore/project-memory checkpoint.
- The fallback can only infer answered categories from the current submitted Q&A history. It does not yet perform full repository/wiki memory reconciliation.
- Manual Q&A testing on 2026-05-14 found that the current baseline is still confusing for users because the visible percentage can mean Gemini readiness in one response and fallback readiness in another response.
- Confidence is currently too prominent for the normal user flow. It should move to collapsed diagnostics or become a small non-numeric badge.
- The fallback top-level menu can appear after a category-specific question, which makes the user feel that the previous answer did not count.
- The target fix is documented in `docs/superpowers/development/14_qna_workflow_refinement.md` and was implemented locally in TC-021R: category-first Q&A, per-category progress, answered question history inside the active category, and no broad fallback menu while an active category exists.

## Evidence

Automated evidence:

```text
pytest tests/api/test_gemini_structured.py -q
6 passed
```

```text
pytest tests/test_mvp_live_gemini_qna_ui.py -q
3 passed
```

Post-MVP-09 stabilization evidence on 2026-05-14:

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe -c D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\pyproject.toml D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\test_mvp_live_gemini_qna_ui.py -q
4 passed in 0.04s
```

Q&A logic stabilization evidence on 2026-05-14:

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe -c D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\pyproject.toml D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\test_mvp_live_gemini_qna_ui.py -q
8 passed in 0.05s
```

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe -c D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\pyproject.toml D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_gemini_structured.py D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\test_mvp_live_gemini_qna_ui.py -q
20 passed in 1.45s
```

```text
D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\node_modules\.bin\tsc.cmd -p D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\tsconfig.json --noEmit
exit 0
```

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe -c D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\pyproject.toml D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests -q
148 passed in 8.26s
```

```text
npm --prefix D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web run build
Compiled successfully
```

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe -c D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\pyproject.toml D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_gemini_structured.py D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\test_mvp_live_gemini_qna_ui.py -q
15 passed in 1.33s
```

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe -c D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\pyproject.toml D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests -q
143 passed in 8.49s
```

```text
npm --prefix D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web run build
Compiled successfully
```

```text
D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\node_modules\.bin\tsc.cmd -p D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\tsconfig.json --noEmit
exit 0
```

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe -c D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\pyproject.toml D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests -q
138 passed in 13.25s
```

```text
npm --prefix D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web run build
Compiled successfully
```

```text
pytest tests/api/test_gemini_structured.py tests/test_mvp_live_gemini_qna_ui.py tests/api/test_guest_drafts.py tests/api/test_auth_session.py tests/api/test_health_contract.py -q
19 passed
```

```text
pytest tests -q
117 passed
```

```text
npx tsc --noEmit
exit 0
```

```text
npm run build
Compiled successfully
```

Live smoke evidence:

```text
GOOGLE_CLOUD_PROJECT=sadify
GOOGLE_CLOUD_LOCATION=global
GOOGLE_GENAI_USE_VERTEXAI=True
SADIFY_MODEL=gemini-2.5-flash

POST /analysis/requirement
HTTP 200
analysis_id: AN-000001
saved: True
schema validated by RequirementAnalysisResponse
```

## Decision

Passed for MVP-06 and revalidated during post-MVP-09 stabilization.

Historical baseline remains useful for proving Gemini structured Q&A and answer
continuation. Later refinements have superseded the original next-step wording:
TC-021R was superseded, TC-021S and TC-021T passed, TC-021U passed route safety,
and TC-021V partially passed. TC-021W automated checks passed, but manual
progression failed. The current active blocker before MVP-10 / TC-025 is TC-021Y
evidence-first Q&A depth and valid preview coherence.
