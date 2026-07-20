# SADify — Archived Test Cases (Consolidated)

Date consolidated: 2026-05-24
Purpose: historical record of the TC-021R through TC-021Y cascade.
All eight superseded by TC-028 + Cycles 2A/2B.

## Index

- TC-021R-mvp-category-first-qna-refinement
- TC-021S-stable-questionnaire-plan-refactor
- TC-021T-qna-ready-state-preview-handoff
- TC-021U-qna-sad-synthesis-quality
- TC-021V-sad-fallback-composition-quality
- TC-021W-user-facing-sad-draft-quality
- TC-021X-evidence-first-qna-depth-valid-preview-coherence
- TC-021Y-domain-aware-qna-sad-quality-hardening

---

## TC-021R-mvp-category-first-qna-refinement

# TC-021R MVP Category-First Q&A Refinement

Date Created: 2026-05-14
Last Updated: 2026-05-15
Status: Superseded by TC-021S

## Purpose

Verify the refined Q&A workflow where SADify works category by category, shows one overall readiness percentage, keeps answered questions visible inside the active category, and avoids confusing user-facing readiness/confidence jumps.

This is a follow-up to TC-021 after manual testing found that the current baseline proves Gemini Q&A wiring but is not yet user-friendly enough for MVP.

## Inputs

- Cross-domain clinic or operational workflow requirement.
- Optional small text/Markdown source file.
- Fake structured model for automated tests by default.
- Live Gemini only if explicitly approved for manual smoke.

## Preconditions

- TC-021 current baseline passed.
- TC-024 SAD preview baseline passed.
- `docs/superpowers/development/14_qna_workflow_refinement.md` is the behavior source for this test.

## API / Docs Preflight

This checkpoint does not require a new external API, SDK, IAM role, OAuth scope, deployment, or live cloud call.

Implementation uses the existing local FastAPI/Next.js code and fake-model structured analysis tests. No live Gemini, Firestore, Drive, Docs, Secret Manager, Cloud Run deploy, or new API enablement was needed.

## Steps

1. Submit a new business request.
2. Confirm SADify builds a relevant category plan.
3. Confirm categories that are already clear do not force questions.
4. Answer a question inside the active category.
5. Confirm the answer appears in that category's answer history.
6. Confirm SADify asks the next needed question inside the same category when more detail is still missing.
7. Confirm SADify moves to the next unclear category only after the current category is clear enough or marked `Needs later confirmation`.
8. Select `I'm not sure`.
9. Confirm SADify stays in the same category and asks an easier suggested-default follow-up.
10. Confirm normal Q&A view uses only one visible percentage: overall readiness.
11. Confirm model confidence is hidden or appears only as a non-numeric diagnostic badge in collapsed diagnostics.
12. Generate an early SAD preview and confirm assumptions/open questions remain visible.

## Expected Output

- The top-level is a question-area status line, not a surprise question menu.
- Active category stays stable while category questions are being answered.
- Answered questions and selected answers are visible under the active category.
- Question areas use word statuses instead of category percentages.
- Overall readiness is separate from AI confidence.
- `I'm not sure` creates uncertainty/open-question state and does not falsely complete the category.
- `Other / not listed` requires details.
- No broad fallback menu appears while an active category exists.
- Repeated or very similar model questions are skipped instead of re-asked.

## Real Output

Passed locally on 2026-05-15.

Backend output:

- `/analysis/requirement` now decorates every saved analysis with a local `questionnaire` state object.
- `questionnaire.draft_readiness` is separate from model confidence.
- `questionnaire.categories` carries internal category progress, active category, question counts, and status.
- `questionnaire.answers` stores answered questions under their category.
- Local fallback no longer bounces back to the broad top-level fallback menu while a category is active.
- Duplicate repeated answers do not increase internal category progress.
- Repeated or highly similar questions in the same category are replaced with the next local question.
- `I'm not sure` keeps the active category and marks the answer as uncertain.
- During normal answer continuation, overall readiness does not decrease just because Gemini returns a lower score.

Frontend output:

- Normal Q&A view shows overall readiness as the only percentage, question-area word statuses, active category, and answered questions in the active category.
- AI confidence is moved into collapsed diagnostics as a non-numeric `AI check` label.
- Answer continuation stores the previous question category marker so backend fallback can preserve category context.
- The duplicate lower readiness/current-question panels are hidden once live analysis exists so users do not see repeated status blocks.

## Differences / Issues

Known baseline issue before this test, now fixed locally:

- Current TC-021 baseline can jump between Gemini readiness and fallback readiness.
- Current UI can show confidence too prominently.
- Current fallback can return the user to a broad top-level menu after a category question.

Remaining limitations:

- Questionnaire state is still local/request-history based; durable Firestore/repo memory is a later persistence checkpoint.
- Category completion uses a conservative local rule for fallback questions: two unique useful answers can mark a fallback category ready.
- Rendered smoke used a local HTTP 200 check because Playwright was not available in the bundled runtime during this run.
- Manual live Gemini smoke was skipped deliberately to avoid extra credit/token use.

## Evidence

Evidence:

```text
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_gemini_structured.py -q
15 passed

D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\test_mvp_live_gemini_qna_ui.py -q
11 passed

D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_gemini_structured.py tests\test_mvp_live_gemini_qna_ui.py -q
26 passed

D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests -q
154 passed

D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\node_modules\.bin\tsc.cmd -p D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\tsconfig.json --noEmit
passed

npm --prefix D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web run build
Next.js compiled successfully, TypeScript passed, static pages generated, standalone prepared.

Temporary local Next standalone server:
http://127.0.0.1:3100/ returned HTTP 200. Browser smoke confirmed one `Overall readiness` percentage on the initial screen, word-only question-area statuses, expandable `Analysis diagnostics`, no framework error overlay, and no relevant console warnings/errors. The temporary server was then stopped and port 3100 confirmed closed.
```

## Decision

TC-021R passed as a local improvement, but manual testing on 2026-05-15 showed that the category plan still drifts because the app rebuilds visible categories from later Gemini turns.

Proceed next to `TC-021S` instead of `TC-025`.


---

## TC-021S-stable-questionnaire-plan-refactor

# TC-021S MVP Stable Questionnaire Plan Refactor

Date Created: 2026-05-15  
Last Updated: 2026-05-20  
Status: Passed; historical Phase 3 checkpoint

## Purpose

Verify that SADify uses one stable questionnaire plan from the first analysis onward, with slot-based category completion and backend-owned readiness.

## Linked Docs

```text
Behavior note:
  docs/superpowers/development/14_qna_workflow_refinement.md

Design spec:
  docs/superpowers/specs/2026-05-15-sadify-stable-questionnaire-plan-design.md

Implementation plan:
  docs/superpowers/plans/2026-05-15-stable-questionnaire-plan-refactor.md
```

## Required Behaviors

1. Before analysis, the UI shows a neutral empty state only.
2. First analysis creates one stable category plan.
3. Core category IDs, labels, and order stay stable across turns.
4. Already-understood categories are hidden from the main flow and appear under `Already understood`.
5. Completed categories move under `Completed areas`.
6. Active category remains locked until required slots are covered or deferred.
7. Category completion depends on covered slots, not question count.
8. Gemini category drift is repaired or replaced by same-slot fallback.
9. New extra categories appear under `Suggested additions`, not directly in the live map.
10. Multi-select questions use checkbox styling plus `Select all that apply.`
11. Normal `Source refs` show business sources only.
12. Editing an earlier answer reopens only the affected slot/category.
13. Initial business-request facts seed category/slot coverage before the first question.
14. The first active question comes from the first unresolved slot in frozen plan order.
15. Semantically wrong cross-slot questions are rejected even if category/slot IDs look valid.
16. A covered slot is not re-asked unless it is explicitly reopened.

## Planned Evidence

```text
pytest tests/api/test_questionnaire_plan.py -q
pytest tests/api/test_gemini_structured.py -q
pytest tests/test_mvp_live_gemini_qna_ui.py -q
pytest tests -q
tsc --noEmit
next build
manual browser smoke:
  - no fake pre-analysis state
  - clinic flow
  - purchase-request flow
  - stable labels/order
  - slot-based category completion
  - explicit multi-select UI
```

## Manual Result On 2026-05-18

Clinic-flow testing found the checkpoint is not yet acceptable:

1. Initial clinic input produced `0%` readiness even though the text already contained users, workflow, reports, and exceptions.
2. The first active category started at `Business rules and approvals` instead of the first unresolved canonical slot.
3. After one answer, an access-permissions question appeared while the UI still labelled it as `Business rules and approvals / Approval path`.
4. Later turns repeated the same access-permissions question and reassigned it across categories.

## Interim Decision

```text
Historical interim note from before the manual rerun: TC-021S remained in
progress at this point, and MVP-10 / TC-025 stayed blocked.
```

## Automated Progress On 2026-05-18

Checkpoint 1 was added after the failed manual test:

1. first-turn routing is now backend-locked to the first unresolved slot
2. initial clinic-style requests seed obvious slot coverage before Q1
3. frontend answer history now preserves both category and slot markers

Verification:

```text
pytest tests/api/test_questionnaire_plan.py tests/api/test_gemini_structured.py tests/test_mvp_live_gemini_qna_ui.py -q
40 passed

tsc --noEmit
passed
```

## Manual Rerun Result On 2026-05-18

The clinic-flow rerun reached `100%` with the locked plan behavior intact:

1. the flow no longer bounced between unrelated categories
2. repeated-question drift did not block completion
3. analysis requests returned `HTTP 200`

New observations from that rerun were moved to the next checkpoint:

1. the `100%` screen needs a quieter ready-state handoff
2. optional refinements need separate non-blocking placement
3. SAD preview generation returned invalid structured output
4. saved questionnaire answers are not yet included explicitly in preview context

## Final Decision

```text
TC-021S passed for questionnaire continuity.
TC-021T later passed. Current execution has moved on through TC-021W automated
checks; TC-021Y is now the active blocker before MVP-10 / TC-025.
```

## Automated Progress After Checkpoint 2

Additional behaviors now covered on 2026-05-18:

1. access-override wording is rejected when mislabeled as an approval-path question
2. an already-covered user-identification question cannot be relabeled as a responsibilities question
3. failed repair attempts use a canonical same-slot fallback instead of a cross-slot replay

Verification:

```text
pytest tests/api/test_questionnaire_plan.py tests/api/test_gemini_structured.py tests/test_mvp_live_gemini_qna_ui.py -q
43 passed

tsc --noEmit
passed
```

## Automated Progress After Checkpoint 3

Additional behaviors now covered on 2026-05-18:

1. two saved answers on the same canonical slot do not advance the questionnaire early
2. the normal next-question path no longer switches category from legacy answer counts
3. repeated-question replacement stays tied to the planner's active slot
4. the easier `I'm not sure yet` follow-up path remains available

Verification:

```text
pytest tests/api/test_gemini_structured.py -q
28 passed
```

## Automated Progress After Checkpoint 4

Additional behaviors now covered on 2026-05-18:

1. model-reported `complete` categories cannot skip uncovered required slots
2. the clinic flow advances from seeded context into the next unresolved category in frozen order
3. uncertain follow-up answers defer only the affected slot
4. proposed extra categories stay suggestions only
5. stale regression expectations were aligned with the locked-target prompt and neutral pre-analysis UI

Verification:

```text
pytest tests/api/test_questionnaire_plan.py tests/api/test_gemini_structured.py tests/test_mvp_live_gemini_qna_ui.py -q
48 passed

pytest tests/api/test_source_uploads.py tests/test_mvp_workspace_shell.py -q
5 passed

tsc --noEmit
passed

next build
passed
```

Historical interim requirement before the final manual rerun:

```text
manual browser rerun of the clinic flow - completed on 2026-05-18
```


---

## TC-021T-qna-ready-state-preview-handoff

# TC-021T Q&A Ready State And Preview Handoff

Date Created: 2026-05-18  
Last Updated: 2026-05-20  
Status: Functional handoff pass complete; historical Phase 3 checkpoint

## Purpose

Verify that the completed Q&A flow becomes a clean draft handoff, optional refinements stay visibly non-blocking, and SAD preview generation receives saved questionnaire answers.

## Linked Docs

```text
Behavior note:
  docs/superpowers/development/14_qna_workflow_refinement.md

Design spec:
  docs/superpowers/specs/2026-05-18-qna-ready-state-preview-handoff-design.md
```

## Inputs

Clinic-flow request text with enough detail to complete the required questionnaire path, followed by user-selected clarification answers.

## Preconditions

1. TC-021S stable questionnaire plan behavior is available.
2. Frontend and backend can run locally.
3. Gemini preview route is configured when live preview smoke is attempted.

## Expected Output

1. Saved answers are hidden inside `Answered so far` by default.
2. Understanding summary is hidden inside `Current understanding` by default.
3. At `100%`, the Q&A box shows `Ready to draft`.
4. At `100%`, the unresolved question-area grid is hidden.
5. `Completed areas` remains expandable.
6. `Optional refinements` appears as a separate collapsed non-blocking section when available.
7. SAD preview context includes saved questionnaire answers.
8. Preview-generation failures remain readable and do not erase Q&A state.

## Planned Evidence

```text
pytest tests/api/test_sad_preview.py -q
pytest tests/test_mvp_live_gemini_qna_ui.py -q
pytest tests/api/test_gemini_structured.py tests/api/test_sad_preview.py tests/test_mvp_live_gemini_qna_ui.py -q
pytest tests -q
tsc --noEmit
npm run build
manual browser smoke:
  - 100% ready-state screen
  - collapsed completed/answered/understanding sections
  - optional refinements visibly non-blocking
  - SAD preview route behavior after the ready state
```

## Real Output

Automated implementation completed on 2026-05-18:

1. `AnalysisPanel` now keeps `Current understanding`, `Answered so far`, `Completed areas`, and diagnostics behind expandable sections.
2. `100%` readiness now renders a `Ready to draft` handoff.
3. The unresolved question-area grid is hidden in the ready state.
4. `Optional refinements` is a separate collapsed section in the same Q&A box.
5. Any post-ready question and its answer controls now live inside `Optional refinements` instead of the main flow.
6. SAD preview context now serializes saved questionnaire answers.
7. Invalid structured SAD preview retry behavior has explicit regression coverage.

Manual live smoke completed on 2026-05-18:

1. The clinic-flow Q&A reached `Ready for draft - 100%`.
2. The ready-state handoff rendered with collapsed secondary sections.
3. `/sad/preview` returned `HTTP 200`.
4. Temporary preview `SP-000001` was saved successfully.
5. The generated preview reused some saved questionnaire answers together with the original clinic request.

## Differences / Issues

1. The technical preview handoff now works, but the generated SAD quality is not yet acceptable for progression.
2. The Q&A surface reported `100%` readiness while the generated SAD preview reported `35% / Low confidence`, creating a contradiction the user cannot trust.
3. The preview body reused clinic facts, but its readiness checklist still said users/roles, workflow, data fields, and business rules were missing even when the original request already supplied much of that information.
4. Generic fallback/approval language bled into the clinic SAD, producing weakly grounded content such as approval-path wording that was not clearly implied by the clinic request.
5. Internal diagnostics such as fallback-use notes appeared as business-facing SAD assumptions.
6. The ready screen still showed an `Active category` after required readiness reached `100%`.

## Evidence

```text
pytest tests\test_mvp_live_gemini_qna_ui.py -q
13 passed

pytest tests\api\test_sad_preview.py -q
9 passed

pytest tests\api\test_gemini_structured.py tests\api\test_sad_preview.py tests\test_mvp_live_gemini_qna_ui.py -q
54 passed

pytest tests -q
179 passed

tsc --noEmit
passed

npm --prefix apps\web run build
passed

Browser smoke:
http://localhost:3000/ loaded
title: SADify
neutral pre-analysis screen present
console warnings/errors: none

Manual live smoke:
POST /analysis/requirement -> repeated HTTP 200 responses through the clinic flow
POST /sad/preview -> HTTP 200
temporary preview id -> SP-000001
```

## Decision

```text
TC-021T passed as the ready-state / preview-handoff integration slice.
Do not start MVP-10 yet. TC-021U passed route safety, TC-021V partially passed
composition cleanup, TC-021W automated checks passed, and TC-021X improved the
workshop path locally. TC-021Y is now the active follow-up before wiki work.
```


---

## TC-021U-qna-sad-synthesis-quality

# TC-021U Q&A And SAD Synthesis Quality

Date Created: 2026-05-19  
Last Updated: 2026-05-20  
Status: Passed for transport/synthesis guard; historical Phase 4 guardrail

## Purpose

Verify that the first draft SAD preview uses one coherent merged view of:

- the original business request
- uploaded source context
- confirmed questionnaire answers
- genuinely unresolved items

This checkpoint follows TC-021T. TC-021T proved the ready-state handoff and live
preview transport. TC-021U verifies the quality of the handoff content.

## Linked Docs

```text
Behavior note:
  docs/superpowers/development/14_qna_workflow_refinement.md

Design spec:
  docs/superpowers/specs/2026-05-18-qna-sad-synthesis-quality-design.md

Implementation plan:
  docs/superpowers/plans/2026-05-19-qna-sad-synthesis-quality.md

Follow-up composition plan:
  docs/superpowers/plans/2026-05-19-sad-fallback-composition-quality-upgrade.md

Follow-up composition acceptance test:
  docs/superpowers/testing/test_cases/TC-021V-sad-fallback-composition-quality.md

Prior checkpoint:
  docs/superpowers/testing/test_cases/TC-021T-qna-ready-state-preview-handoff.md
```

## Input Fixture

```text
Small clinic wants to track patient registration, queue status, doctor consultation, medicine collection, and payment in one simple system. Reception staff register patients and update queue status. Doctors record consultation notes. Pharmacy staff prepare medicine. Cashier records payment. Manager needs a daily summary of patients served, waiting time, and unpaid bills. Some patients may skip payment or leave before collecting medicine.
```

## Expected Output

1. SAD preview context includes confirmed facts from the original request.
2. SAD preview context includes saved questionnaire answers.
3. SAD preview context separates unresolved items from internal diagnostics.
4. Business-facing assumptions do not contain fallback/retry wording.
5. Preview generation does not mark already-confirmed clinic facts as missing.
6. If the preview shows IT readiness, it is clearly a deeper Layer 2 assessment, not a contradiction of Layer 1 draft readiness.
7. At `100%` draft readiness, the Q&A UI hides required active-category wording.
8. Optional refinements remain collapsed and non-blocking.
9. If Gemini returns invalid structured SAD preview JSON after retry, the
   backend saves a safe local temporary preview instead of returning `502`.

## Planned Evidence

```text
pytest tests/api/test_sad_synthesis.py -q
pytest tests/api/test_sad_preview.py -q
pytest tests/test_mvp_live_gemini_qna_ui.py -q
pytest tests/test_mvp_sad_preview_it_readiness_ui.py -q
pytest tests -q
node ...\typescript\bin\tsc -p apps\web\tsconfig.json --noEmit
npm --prefix apps\web run build
manual browser smoke after implementation:
  - clinic fixture reaches Ready to draft
  - SAD preview includes clinic flow facts
  - no fallback diagnostics in assumptions
  - Layer 2 readiness wording is not confusing
```

## Real Output

Automated verification on 2026-05-19:

```text
pytest tests\api\test_sad_synthesis.py tests\api\test_sad_preview.py tests\api\test_gemini_structured.py tests\test_mvp_live_gemini_qna_ui.py tests\test_mvp_sad_preview_it_readiness_ui.py -q
-> 48 passed

pytest tests -q
-> 184 passed

node apps\web\node_modules\typescript\bin\tsc -p apps\web\tsconfig.json --noEmit
-> passed

npm --prefix apps\web run build
-> passed
```

Implemented behavior:

- SAD preview context now has explicit sections for confirmed request facts,
  confirmed questionnaire answers, unresolved items, business-facing
  assumptions, source references, source context, and internal diagnostics.
- Fallback/retry/Gemini validation wording is separated from business-facing
  assumptions before preview generation.
- SAD preview prompt now treats confirmed request facts as authoritative and
  keeps Layer 1 draft readiness separate from deeper Layer 2 IT readiness.
- At `100%` draft readiness, required active-category wording is hidden.
- SAD preview UI labels IT readiness as `Later IT readiness` and describes it
  as a deeper implementation check.
- SAD preview route now falls back to a deterministic local temporary SAD when
  Gemini returns invalid structured preview output after normal + repair
  attempts. The fallback preserves request facts, saved Q&A answers, source
  references, safe assumptions, open follow-up items, and a tracking path of
  `_SADify/local-fallback`.

Manual live video smoke on 2026-05-19:

```text
video:
  C:\Users\User\AppData\Local\Packages\Microsoft.ScreenSketch_8wekyb3d8bbwe\TempState\Recordings\20260519-0838-06.8933020.mp4

observed:
  - Q&A calls returned HTTP 200.
  - Q&A reached Ready for draft - 100%.
  - /sad/preview returned HTTP 200 and saved SP-000001.
  - The safe fallback prevented the previous 502 dead end.
```

## Differences / Issues

- An earlier manual live browser smoke on 2026-05-19 exposed repeated
  `/sad/preview` `502` responses after successful Q&A calls. Root cause:
  Gemini preview output failed backend schema validation after the existing
  repair retry. The safe local fallback resolved this route failure.
- The later manual video smoke proved the fallback route works, but exposed a
  new content-quality issue: the fallback SAD can still show `Previous question`,
  `Previous answer`, and `Previous readiness` logs in the displayed business
  request, and can render saved answers as raw Q&A bullets instead of structured
  SAD sections.
- Production build initially failed inside the sandbox with `EPERM` while npm
  inspected `C:\Users\User`; rerunning the same build outside the sandbox
  passed.

## Decision

```text
TC-021U passes for its intended guardrail: route stability, synthesis context,
diagnostic filtering, ready-state cleanup, and safe local fallback instead of
502. TC-021V later partially passed composition cleanup, TC-021W passed
automated user-facing draft checks, and TC-021X improved the workshop path
locally. Do not proceed to MVP-10 / TC-025 yet; TC-021Y domain-aware Q&A and
SAD quality hardening is now the active blocker.
```


---

## TC-021V-sad-fallback-composition-quality

# TC-021V SAD Fallback Composition Quality

Date Created: 2026-05-19  
Last Updated: 2026-05-21  
Status: Partial pass; TC-021W automated checks passed, TC-021X local checks passed, and TC-021Y follow-up is active

## Purpose

Verify that SADify's fallback SAD preview is not just transport-safe, but also
useful as a first structured SAD draft when Gemini structured preview output is
invalid.

This follows TC-021U. TC-021U proved the backend no longer returns `502` after
invalid Gemini preview output. TC-021V verifies that the saved fallback preview
is clean, structured, and uses confirmed answers correctly.

## Linked Docs

```text
Behavior note:
  docs/superpowers/development/14_qna_workflow_refinement.md

Design spec:
  docs/superpowers/specs/2026-05-18-qna-sad-synthesis-quality-design.md

Implementation plan:
  docs/superpowers/plans/2026-05-19-sad-fallback-composition-quality-upgrade.md

Prior checkpoint:
  docs/superpowers/testing/test_cases/TC-021U-qna-sad-synthesis-quality.md
```

## Triggering Evidence

Manual video smoke on 2026-05-19 exposed the original fallback composition
problem:

```text
video:
  C:\Users\User\AppData\Local\Packages\Microsoft.ScreenSketch_8wekyb3d8bbwe\TempState\Recordings\20260519-0838-06.8933020.mp4

observed:
  - Q&A reached Ready for draft - 100%
  - /sad/preview returned a saved SP preview
  - fallback preview avoided 502
  - Confirmed Business Request included Previous question / Previous answer logs
  - confirmed answers appeared as raw bullets rather than synthesized SAD content
  - encryption and audit amendments were preserved but not interpreted into SAD sections
```

Manual video smoke on 2026-05-19 after the TC-021V automated fix:

```text
video:
  C:\Users\User\AppData\Local\Packages\Microsoft.ScreenSketch_8wekyb3d8bbwe\TempState\Recordings\20260519-1313-20.7210124.mp4

passed:
  - Q&A reached Ready for draft - 100%
  - /sad/preview returned HTTP 200 and saved SP-000001
  - Confirmed Business Request stayed clean
  - Previous question / Previous answer / Previous readiness logs no longer leaked
  - saved Q&A answers and amendments were present in the preview

failed:
  - preview still presented itself as a fallback/debug document
  - the visible SAD showed Safe Temporary SAD Preview, 35% Low confidence,
    AI preview formatting, and Later IT readiness too prominently
  - Overview, Users, and Workflow repeated the original request instead of
    synthesizing it into a professional Layer 1 SAD draft
  - saved answers were still shown as shallow bullets rather than interpreted
    requirements, workflow steps, records, rules, and controls
  - user amendment wording such as "dun downgrade" was preserved literally
    instead of normalized into professional requirement language
  - Source refs repeated after nearly every section and made the document noisy
  - empty or low-value sections such as Assumptions, Source refs, and Tracking
    status still appeared in the main result
  - the 100% Q&A state conflicted with the SAD preview's 35% Low confidence label
```

## Input Fixture

```text
Small clinic wants to track patient registration, queue status, doctor consultation, medicine collection, and payment in one simple system. Reception staff register patients and update queue status. Doctors record consultation notes. Pharmacy staff prepare medicine. Cashier records payment. Manager needs a daily summary of patients served, waiting time, and unpaid bills. Some patients may skip payment or leave before collecting medicine.
```

## Confirmed Answers To Preserve

```text
Data and records:
  Names or identifiers
  Dates and statuses
  Responsible staff or owner
  Amounts, notes, or reasons

Business rules:
  A record cannot be completed until key steps are done

Approvals:
  It goes through multiple approval levels

Exceptions:
  Mark incomplete and keep open

Access:
  Role-based access

Sensitive actions:
  Approve or reject work
  Delete or overwrite records
  Export or share information
  Change system settings

Integrations:
  No external systems in the first version

Security/privacy:
  Secure login
  Restrict sensitive data by role
  Keep personal or confidential data protected
  Amendment: keep all sensitive data encrypted with optimized choice, dun downgrade

Audit/history:
  Edits and corrections
  Approvals and decisions
  Status changes
  Exports or downloads
  Amendment: any actions towards the system and the data all must be recorded
```

## Expected Output

1. `/sad/preview` returns `HTTP 200`.
2. `Confirmed Business Request` contains only the clean clinic request.
3. No user-facing SAD section contains:
   - `Previous question`
   - `Previous answer`
   - `Previous readiness`
4. Fallback preview includes structured sections:
   - Overview and scope
   - Users and roles
   - Workflow
   - Data and records
   - Business rules and approvals
   - Exceptions and edge cases
   - Reports and summaries
   - Access and permissions
   - Integrations
   - Security and privacy
   - Audit and history
5. Security/privacy section includes the encryption amendment.
6. Audit/history section includes the full audit amendment.
7. Open questions contain only true remaining gaps or optional refinement notes.
8. The generated fallback reads as a first SAD draft, not a diagnostic dump.

## Planned Evidence

```text
pytest tests/api/test_sad_synthesis.py -q
pytest tests/api/test_sad_preview.py -q
pytest tests/test_mvp_live_gemini_qna_ui.py -q
pytest tests -q
node ...\typescript\bin\tsc -p apps\web\tsconfig.json --noEmit
npm --prefix apps\web run build
manual MP4 smoke after implementation
```

## Real Output

Automated verification on 2026-05-19:

```text
pytest tests\api\test_sad_synthesis.py::test_clean_business_request_strips_qna_transport_history -q
-> 1 passed

pytest tests\test_mvp_live_gemini_qna_ui.py::test_live_gemini_qna_ui_preserves_clean_requirement_for_preview -q
-> 1 passed

pytest tests\api\test_sad_preview.py::test_safe_fallback_preview_renders_structured_sad_sections tests\api\test_sad_preview.py::test_safe_fallback_preview_does_not_show_internal_understanding tests\api\test_sad_preview.py::test_safe_fallback_preview_does_not_promote_optional_question_as_core_gap_when_ready -q
-> 3 passed

pytest tests\api\test_sad_synthesis.py -q
-> 3 passed

pytest tests\api\test_sad_preview.py -q
-> 14 passed

pytest tests\test_mvp_live_gemini_qna_ui.py -q
-> 14 passed

pytest tests -q
-> 189 passed

node apps\web\node_modules\typescript\bin\tsc -p apps\web\tsconfig.json --noEmit
-> passed

npm --prefix apps\web run build
-> passed after sandbox escalation; initial sandbox run failed with Windows EPERM while lstat C:\Users\User
```

Implemented behavior:

- backend `clean_business_request()` strips Q&A transport history before SAD
  synthesis and preview storage
- frontend keeps a clean requirement text for SAD preview while still sending
  Q&A history only to the next analysis call
- local safe fallback preview now renders structured SAD sections instead of a
  raw `Confirmed Q&A Answers` dump
- fallback preview filters internal Gemini/fallback summary text from the
  visible overview
- at `100%` draft readiness, optional next questions are not promoted as core
  unresolved gaps
- encryption and full audit-history amendments are preserved in the proper
  Security/Privacy and Audit/History sections

## Decision

```text
TC-021V is a partial pass. It fixed the clean-request boundary and stopped Q&A
transport-history leakage, but the manual smoke still failed the user-facing SAD
quality bar.

Do not proceed to MVP-10 / TC-025. TC-021X made Q&A more evidence-first for
the workshop path, but manual workshop/tuition smoke still failed broader
quality progression. Continue with TC-021Y to harden domain-aware Q&A and SAD
output quality.
```


---

## TC-021W-user-facing-sad-draft-quality

# TC-021W User-Facing SAD Draft Quality

Date Created: 2026-05-19  
Last Updated: 2026-05-21  
Status: Automated pass; manual workshop smoke failed progression; TC-021X local checks passed and TC-021Y is active

## Purpose

Verify that SADify's generated SAD preview reads like a clean Layer 1 System
Analysis Document for a business user, even when Gemini's structured preview
format fails and the local fallback composer is used.

TC-021V fixed transport leakage and clean request boundaries. TC-021W owns the
next quality layer: remove debug framing, synthesize answers into professional
SAD sections, normalize user amendments, and keep readiness messaging coherent.

## Linked Docs

```text
Behavior note:
  docs/superpowers/development/14_qna_workflow_refinement.md

Design spec:
  docs/superpowers/specs/2026-05-18-qna-sad-synthesis-quality-design.md

Implementation plan:
  docs/superpowers/plans/2026-05-19-user-facing-sad-draft-quality.md

Prior checkpoint:
  docs/superpowers/testing/test_cases/TC-021V-sad-fallback-composition-quality.md

Follow-up checkpoint:
  docs/superpowers/testing/test_cases/TC-021X-evidence-first-qna-depth-valid-preview-coherence.md
```

## Triggering Evidence

Manual video smoke on 2026-05-19:

```text
video:
  C:\Users\User\AppData\Local\Packages\Microsoft.ScreenSketch_8wekyb3d8bbwe\TempState\Recordings\20260519-1313-20.7210124.mp4

observed:
  - Q&A reached Ready for draft - 100%
  - temporary SAD preview was saved as SP-000001
  - the preview no longer leaked Previous question / Previous answer logs
  - the SAD still looked like a fallback/debug document
  - the SAD showed 35% Low confidence after Q&A had reached 100%
  - content repeated the original request instead of synthesizing a document
  - Q&A answers and amendments were present but shallowly rendered
```

## Input Fixture

```text
Small clinic wants to track patient registration, queue status, doctor consultation, medicine collection, and payment in one simple system. Reception staff register patients and update queue status. Doctors record consultation notes. Pharmacy staff prepare medicine. Cashier records payment. Manager needs a daily summary of patients served, waiting time, and unpaid bills. Some patients may skip payment or leave before collecting medicine.
```

## Confirmed Answers To Preserve And Interpret

```text
Data and records:
  Names or identifiers
  Dates and statuses
  Responsible staff or owner
  Amounts, notes, or reasons

Business rules:
  A record cannot be completed until key steps are done

Approvals:
  It goes through multiple approval levels

Exceptions:
  Mark incomplete and keep open

Access:
  Role-based access

Sensitive actions:
  Delete or overwrite records
  Change system settings

Integrations:
  No external systems in the first version

Security/privacy:
  Secure login
  Restrict sensitive data by role
  Keep personal or confidential data protected
  Amendment: keep all sensitive data encrypted with optimized choice, dun downgrade

Audit/history:
  Edits and corrections
  Approvals and decisions
  Status changes
  Amendment: any actions towards the system and the data all must be recorded
```

## Expected Output

1. `/sad/preview` returns `HTTP 200`.
2. User-facing preview title is business-facing, for example:
   `Clinic Patient Flow Management SAD Draft`.
3. Normal preview does not show:
   - `Safe Temporary SAD Preview`
   - `AI preview formatting`
   - `Generated safe local preview`
   - `_SADify/local-fallback`
   - `35% Low confidence` as the main visible status
   - raw `Previous question`, `Previous answer`, or `Previous readiness`
4. The first visible readiness message stays coherent with Q&A:
   `Draft-ready` or equivalent, with Layer 2/IT readiness collapsed or clearly
   labelled as later implementation review.
5. Sections are synthesized, not repeated request text:
   - Executive summary
   - Scope
   - Users and responsibilities
   - Workflow
   - Data and records
   - Business rules and approvals
   - Exceptions and follow-up
   - Reports and summaries
   - Access and permissions
   - Security and privacy
   - Audit and history
   - Integrations
6. Workflow section describes ordered steps from registration through payment,
   with exception paths for skipped payment and uncollected medicine.
7. Data section turns selected fields into readable record requirements.
8. Security amendment is normalized into professional language, for example:
   sensitive data must remain encrypted and security controls must not be
   weakened.
9. Audit amendment is normalized into professional language, for example:
   all user actions that affect system data must be recorded.
10. Source refs are not repeated after every section in the main flow; they are
    shown once or under a collapsed traceability section.
11. Empty sections are hidden or replaced with useful text.
12. Open questions contain only true optional refinements or Layer 2 follow-up,
    not already answered required items.

## Planned Evidence

```text
pytest tests/api/test_sad_preview.py -q
pytest tests/test_mvp_sad_preview_it_readiness_ui.py -q
pytest tests -q
node ...\typescript\bin\tsc -p apps\web\tsconfig.json --noEmit
npm --prefix apps\web run build
manual MP4 smoke after implementation
```

## Real Output

Automated TC-021W implementation completed on 2026-05-20.

Backend fallback composer output:

```text
title:
  Clinic Patient Flow Management SAD Draft

temporary notice:
  Draft preview generated from the confirmed business request and saved Q&A
  answers. Review before saving as a formal SAD.

normal readiness:
  Ready for draft / 100% / High

sections:
  Confirmed Business Request
  Executive Summary
  Scope
  Users and Responsibilities
  Workflow
  Data and Records
  Business Rules and Approvals
  Exceptions and Follow-Up
  Reports and Summaries
  Access and Permissions
  Security and Privacy
  Audit and History
  Integrations
```

Confirmed automated behavior:

```text
- fallback preview title is business-facing
- visible backend preview text no longer includes Safe Temporary SAD Preview,
  AI preview formatting, Generated safe local preview, or _SADify/local-fallback
- workflow is synthesized into ordered clinic steps from registration through
  payment, with skipped-payment / uncollected-medicine follow-up
- data fields are normalized into readable record requirements
- security amendment is normalized to sensitive data must remain encrypted and
  security controls must not be weakened
- audit amendment is normalized to all user actions that affect system data must
  be recorded
- frontend fallback preview branch shows Draft-ready / Layer 1 preview
- frontend keeps fallback diagnostics, source refs, and tracking status behind
  collapsed details in the normal view
```

## Differences / Issues

```text
Manual workshop smoke on 2026-05-20 proved the automated fallback presentation
improvement is not enough for progression. The app reached Q&A `Ready for draft
- 100%`, generated a domain-specific maintenance SAD preview, but still showed
`60% Low confidence` and visible `Later IT readiness`. The Q&A also remained too
general because broad preset questions and answer labels did not capture enough
detailed workflow evidence.

TC-021W should stay as automated pass plus manual progression failure evidence.
TC-021X later improved the workshop path locally, but broader workshop/tuition
manual smoke still failed. MVP-10 / TC-025 should not start. Continue with
TC-021Y.
```

## Evidence

```text
Focused backend red check before implementation:
  D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_sad_preview.py -q
  result: 3 failed, 14 passed
  expected failures:
    test_safe_fallback_preview_uses_business_facing_title_and_notice
    test_safe_fallback_preview_synthesizes_sections_instead_of_repeating_request
    test_safe_fallback_preview_normalizes_user_amendments

Focused backend after implementation:
  D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_sad_preview.py -q
  result: 17 passed in 1.16s

Focused frontend red check before implementation:
  D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\test_mvp_sad_preview_it_readiness_ui.py -q
  result: 1 failed, 2 passed
  expected failure:
    test_sad_preview_ui_hides_fallback_diagnostics_from_normal_view

Focused frontend after implementation:
  D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\test_mvp_sad_preview_it_readiness_ui.py -q
  result: 3 passed in 0.06s

Full regression:
  D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests -q
  result: 193 passed in 8.23s

TypeScript:
  node D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\node_modules\typescript\bin\tsc -p D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\tsconfig.json --noEmit
  result: exit 0

Next.js production build:
  npm --prefix D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web run build
  result: exit 0, compiled successfully

Manual workshop smoke after automated implementation:
  video:
    C:\Users\User\AppData\Local\Packages\Microsoft.ScreenSketch_8wekyb3d8bbwe\TempState\Recordings\20260520-0241-51.6027462.mp4
  extracted final frame:
    D:\GoogleCloudHack\video_inspector_output\sadify_tc021w_20260520_0241\frame_00-09-01.jpg
  observed:
    Q&A reached Ready for draft - 100%
    temporary preview SP-000001 was saved
    title was Maintenance Request Tracking System - SAD Preview
    preview showed 60% Low confidence
    Later IT readiness was visible in the main preview
    source refs repeated under multiple sections
    SAD was coherent but still too general/template-like
```

## Decision

```text
TC-021W automated checks pass, but manual workshop smoke failed progression.
TC-021X later improved the workshop path locally, but manual workshop/tuition
smoke still failed broader domain-aware progression. The next active blocker is
TC-021Y domain-aware Q&A and SAD quality hardening. Do not start wiki update
approval until TC-021Y passes.
```


---

## TC-021X-evidence-first-qna-depth-valid-preview-coherence

# TC-021X - Evidence-First Q&A Depth And Valid Preview Coherence

Status: local implementation passed; manual workshop/tuition smoke failed broader progression; followed by TC-021Y
Phase: 4 - SAD preview and SAD quality stabilization
Date created: 2026-05-20

## Purpose

Validate that SADify no longer treats broad preset Q&A coverage as enough for a user-facing SAD draft, and that valid preview output follows the same user-facing quality rules as fallback preview output.

## Follow-Up Blocker

MVP-10 / TC-025 wiki update approval must not start until TC-021Y passes.

## Test Input

Use this business request for local and manual validation:

```text
A small equipment workshop wants to track maintenance requests for company machines. Staff submit a request when a machine has an issue. The workshop supervisor assigns a technician, and the technician records diagnosis notes, parts used, repair status, and completion time. Expensive parts require manager approval before use. If parts are unavailable or a job is overdue, the request stays open with a reason. The operations manager needs a weekly summary of open requests, completed repairs, repeated machine issues, parts cost, and overdue jobs. Staff can create and view their own requests, supervisors assign jobs, technicians update repair details, and managers approve expensive parts and view reports. No external systems are needed in the first version. The system must use secure login, restrict actions by role, and record every change with user and timestamp.
```

## Current Failing Evidence

Manual smoke from 2026-05-20:

- Video: `C:\Users\User\AppData\Local\Packages\Microsoft.ScreenSketch_8wekyb3d8bbwe\TempState\Recordings\20260520-0241-51.6027462.mp4`
- Extracted final frame: `D:\GoogleCloudHack\video_inspector_output\sadify_tc021w_20260520_0241\frame_00-09-01.jpg`
- Q&A reached `Ready for draft - 100%`.
- SAD preview generated as `SP-000001`.
- Preview title was domain-specific: `Maintenance Request Tracking System - SAD Preview`.
- Preview still showed `60% Low confidence`.
- `Later IT readiness` was visible in the main preview.
- Content was coherent but too general/template-like.
- Source refs repeated under multiple sections.

This is a TC-021W partial result, not a pass for progression.

## Expected Q&A Behavior

For the rich workshop input, the system should:

- seed known facts from the request across workflow, data, rules, exceptions, reports, access, integrations, and non-functional needs;
- avoid asking a broad normal-flow or generic responsibility question if those facts are already present;
- ask a precise missing-facet question, such as approval threshold, overdue definition, status values, edit rules after completion, or report grouping;
- offer contextual choices that preserve workshop details;
- avoid marking the analysis `100%` ready based only on generic labels.

## Expected SAD Preview Behavior

The SAD preview should:

- stay business-facing in the main body;
- include workshop-specific entities and records;
- describe the workflow in concrete steps;
- include the expensive-parts approval rule;
- include open-reason handling for unavailable parts and overdue jobs;
- include weekly report contents and audience;
- include role-based permissions;
- include no-external-system first-version scope;
- include secure login, role restrictions, and audit trail with user and timestamp;
- keep IT readiness collapsed or secondary;
- not show a contradictory `60% Low confidence` state after Q&A says ready for draft;
- show source refs without repeating them under every section.

## Local Test Expectations

Add or update local tests so they fail before implementation and pass after:

- rich workshop initial fact extraction covers the stated rules, exceptions, access, integrations, and non-functional requirements;
- next-question selection skips already-known broad facets and asks a missing detailed facet;
- readiness calculation requires meaningful facet coverage;
- valid preview presentation applies the same user-facing guardrails as fallback preview presentation;
- generated or synthesized SAD content includes the concrete workshop facts above.

## Local Implementation Result

Implemented on 2026-05-20:

- rich workshop initial facts are credited across rules, exceptions, access, integrations, and non-functional needs;
- broad preset responsibility labels no longer complete the responsibility slot by themselves;
- when the rich workshop request already covers the normal workflow, the next local fallback question targets the missing expensive-parts approval rule;
- valid preview UI uses the same Layer 1 / later implementation review presentation pattern as fallback previews;
- section-level source refs are no longer repeated in the main preview list;
- deterministic fallback SAD composition now synthesizes the workshop maintenance request into workshop-specific SAD sections.

## Evidence

Run from `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`:

```text
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_sad_preview.py tests\api\test_sad_synthesis.py tests\api\test_gemini_structured.py tests\test_mvp_sad_preview_it_readiness_ui.py -q
result: 60 passed in 2.57s

D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests -q
result: 197 passed in 12.20s

node D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\node_modules\typescript\bin\tsc -p D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\tsconfig.json --noEmit
result: exit 0

npm --prefix apps\web run build
result: compiled successfully
```

Note: root `npx tsc --noEmit` resolved the wrong npm package (`tsc@2.0.4`) and failed before TypeScript ran. The repo's installed compiler command above passed.

## Manual Smoke Result After Local Implementation

Workshop manual smoke after the local TC-021X changes showed improvement but
still exposed polish issues:

- workshop SAD became domain-specific;
- `Business Rules and Approvals` still used generic approval wording in some
  cases;
- workshop rules could still mention `incomplete visits`, which is clinic
  leakage;
- internal `_SADify/local-fallback` tracking path could still appear in tracking
  details.

Tuition manual smoke on 2026-05-21 showed TC-021X is too narrow:

- video: `C:\Users\User\AppData\Local\Packages\Microsoft.ScreenSketch_8wekyb3d8bbwe\TempState\Recordings\20260521-0245-19.3155261.mp4`
- Q&A asked a generic business-goal question although the tuition request already
  stated the first-version scope.
- Q&A reached `Ready for draft - 100%` through broad preset answers.
- SAD preview mentioned tuition concepts but still exposed fallback mechanism
  wording, internal source refs, and generic/invented approval logic.

## Historical Manual Smoke Script

1. Start the API and web app in the MVP worktree.
2. Open SADify and sign in or continue with the existing session.
3. Paste the workshop request from this test.
4. Start analysis.
5. Record the first question and answer choices.
6. Continue until the app says ready for draft.
7. Generate SAD preview.
8. Confirm the preview meets the expected behavior above.

## Decision

TC-021X remains valuable local implementation evidence, but it is not the final
Phase 4 pass. Continue with:

```text
docs/superpowers/testing/test_cases/TC-021Y-domain-aware-qna-sad-quality-hardening.md
```


---

## TC-021Y-domain-aware-qna-sad-quality-hardening

# TC-021Y - Domain-Aware Q&A And SAD Quality Hardening

Date Created: 2026-05-21
Last Updated: 2026-05-21
Status: Local implementation passed; browser/manual smoke pending before MVP-10

## Purpose

Validate that SADify asks domain-aware, missing-facet questions and generates a
clean Layer 1 SAD draft across more than one operational domain.

This follows TC-021X. TC-021X improved the workshop path locally, but manual
workshop and tuition-centre smoke tests still showed generic Q&A and template
leakage in user-facing SAD output.

## Blocked Until This Passes

MVP-10 / TC-025 wiki update approval must not start until TC-021Y passes.

## Linked Docs

```text
Behavior note:
  docs/superpowers/development/14_qna_workflow_refinement.md

Design spec:
  docs/superpowers/specs/2026-05-21-domain-aware-qna-sad-quality-hardening-design.md

Implementation plan:
  docs/superpowers/plans/2026-05-21-domain-aware-qna-sad-quality-hardening.md

Prior checkpoint:
  docs/superpowers/testing/test_cases/TC-021X-evidence-first-qna-depth-valid-preview-coherence.md
```

## Triggering Evidence

Workshop smoke, 2026-05-20:

```text
video:
  C:\Users\User\AppData\Local\Packages\Microsoft.ScreenSketch_8wekyb3d8bbwe\TempState\Recordings\20260520-0241-51.6027462.mp4

observed:
  Q&A reached Ready for draft - 100%.
  SAD preview became more domain-specific after local TC-021X work.
  Remaining output still had generic approval wording, clinic wording leakage,
  tracking path leakage, and template feel.
```

Tuition smoke, 2026-05-21:

```text
video:
  C:\Users\User\AppData\Local\Packages\Microsoft.ScreenSketch_8wekyb3d8bbwe\TempState\Recordings\20260521-0245-19.3155261.mp4

observed:
  Initial Q&A asked a generic business-goal question even though scope was clear.
  Q&A reached Ready for draft - 100% after broad preset answers.
  SAD preview mentioned tuition-centre concepts, but visible output still said
  fallback mechanism, exposed internal slot source refs, invented generic
  approval wording, and used generic exception handling.
```

Event-rental uploaded-source smoke, 2026-05-21:

```text
observed:
  After the PDF was actually uploaded, Q&A used SRC-000001 and asked a
  source-aware owner-approval question. After answering enough questions, the UI
  showed Ready for draft - 100%, but Generate SAD preview returned:
  "Answer the blocking basics before generating a SAD preview."

  The optional/refinement question also leaked clinic wording:
  "Role access decides who can view, edit, approve, and report on clinic
  information" with reception/doctor/pharmacy/cashier choices.
```

## Test Inputs

### Tuition Centre

```text
A small tuition centre wants a simple system to track student enrolment, class schedules, attendance, fee payments, and parent updates. Admin staff register students and assign them to classes. Teachers mark attendance and add short progress notes. Parents should receive updates when students are absent or fees are unpaid. The centre manager needs a weekly summary of enrolled students, attendance issues, unpaid fees, and classes that are full.
```

### Equipment Workshop

```text
A small equipment workshop wants to track maintenance requests for company machines. Staff submit a request when a machine has an issue. The workshop supervisor assigns a technician, and the technician records diagnosis notes, parts used, repair status, and completion time. Expensive parts require manager approval before use. If parts are unavailable or a job is overdue, the request stays open with a reason. The operations manager needs a weekly summary of open requests, completed repairs, repeated machine issues, parts cost, and overdue jobs. Staff can create and view their own requests, supervisors assign jobs, technicians update repair details, and managers approve expensive parts and view reports. No external systems are needed in the first version. The system must use secure login, restrict actions by role, and record every change with user and timestamp.
```

### Generic Operations

```text
A small service team wants to track customer requests, staff assignment, status updates, unresolved reasons, and weekly manager summaries in one simple system.
```

### Uploaded Event Rental Source

Use `D:\GoogleCloudHack\.tmp\sadify_upload_test_sources\event-rental-workflow.pdf`
with this typed request:

```text
Please analyse the uploaded event rental workflow and ask the next important question.
```

## Expected Q&A Behavior

For the tuition request:

- seed goal and first-version scope from the request;
- do not ask a generic "main goal" question first;
- ask a missing detailed rule such as parent notification timing, unpaid-fee
  follow-up, class capacity, attendance correction, or access boundaries;
- offer fact-bearing choices that mention tuition concepts.

For the workshop request:

- preserve the TC-021X evidence-first workshop behavior;
- ask a missing detail such as expensive-part threshold, overdue definition,
  status lifecycle, edit-after-completion, or report grouping;
- never use clinic wording in maintenance output.

For the generic request:

- ask clear operational questions without pretending domain details are known;
- still avoid generic answers becoming over-specific SAD rules.

For uploaded event-rental or customer-order sources:

- use uploaded `source_context` as first-class evidence for Q&A and preview
  gating;
- ask about booking/order, delivery, return, payment, damage, customer updates,
  or owner/sales/warehouse/driver responsibilities;
- never show clinic roles or clinic access wording unless the source is actually
  a clinic workflow.

## Expected SAD Preview Behavior

The SAD preview should:

1. read like a normal draft, not a fallback/debug report;
2. hide fallback mechanism and local composer wording from normal output;
3. hide internal slot IDs from source refs;
4. avoid invented approval paths;
5. place vague/broad answers under assumptions or open questions;
6. clear previous preview content when a new analysis/request starts;
7. keep IT readiness and tracking secondary or collapsed.
8. allow preview generation when the newer questionnaire says draft-ready and
   uploaded source context contains the business basics.

## Local Evidence

```text
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_gemini_structured.py tests\api\test_sad_preview.py tests\api\test_sad_synthesis.py -q
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\test_mvp_sad_preview_it_readiness_ui.py -q
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests -q
node D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\node_modules\typescript\bin\tsc -p D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\tsconfig.json --noEmit
npm --prefix D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web run build
```

Result, 2026-05-21:

```text
Focused API tests:
  tests/api/test_gemini_structured.py
  tests/api/test_sad_preview.py
  tests/api/test_sad_synthesis.py
  59 passed

SAD preview UI checks:
  tests/test_mvp_sad_preview_it_readiness_ui.py
  5 passed

Full Python regression:
  tests
  201 passed

TypeScript:
  node ...\typescript\bin\tsc ... --noEmit
  passed

Next.js production build:
  npm --prefix ...\apps\web run build
  passed outside sandbox after sandbox blocked Node from lstat C:\Users\User

No-cloud local smoke:
  Tuition first question:
    Which parent, fee, attendance, or class rule should automatically trigger follow-up?
  Tuition target:
    rules_approvals / triggering_rules
  Tuition choices:
    parent absence, unpaid fee follow-up, class capacity
  Tuition SAD:
    Tuition Centre Management System SAD Draft
    leak check passed for fallback mechanism, _SADify/local-fallback,
    goal_scope.business_goal, multi-level approval, and incomplete visits
  Workshop SAD:
    Maintenance Request Tracking System SAD Draft
    no clinic wording leak
    keeps requests-stay-open-with-reason handling
```

Additional uploaded-source regression, 2026-05-21:

```text
Triggering video:
  C:\Users\User\AppData\Local\Packages\Microsoft.ScreenSketch_8wekyb3d8bbwe\TempState\Recordings\20260521-0434-01.3169206.mp4

Observed problem:
  A laundry workflow uploaded as a source still produced broad repeated
  questions such as generic business-goal / normal-flow prompts.

Root cause:
  Uploaded source_context was included in the model prompt and some initial
  evidence checks, but replacement/fallback paths did not consistently pass the
  combined typed request + uploaded source context into fallback question
  generation. When Gemini drifted or repeated, SADify replaced the question with
  generic slot wording instead of source-aware wording.

Fix:
  Combined request/source context is now used for:
    - initial evidence extraction
    - refinement target selection
    - locked-slot fallback question generation
    - drift replacement
    - repeated-question replacement
  Added a generic customer service/order refinement path, covering uploaded
  laundry-style workflows without making the system laundry-only.

Regression evidence:
  tests/api/test_gemini_structured.py::test_analysis_api_uses_uploaded_source_context_for_domain_question_replacement passed
  tests/api/test_gemini_structured.py::test_analysis_api_uploaded_source_followup_does_not_repeat_broad_question passed
  tests/api/test_gemini_structured.py passed: 39 passed
  tests/api/test_source_uploads.py passed: 3 passed
  full tests passed: 203 passed
```

Additional event-rental uploaded-source correction, 2026-05-21:

```text
Root cause:
  /sad/preview still used the older blocking-basics gate with only typed
  requirement text, not uploaded source_context or the newer questionnaire
  draft readiness.

  Legacy fallback questions also still contained clinic-specific wording in the
  generic fallback path, so optional/refinement questions could leak clinic
  roles into event-rental workflows after Gemini returned invalid output.

Fix:
  Preview blocking-basics now includes source_context evidence and bypasses the
  legacy block when questionnaire draft_readiness is draft-ready.
  Legacy fallback questions now receive combined typed request + source context
  and use event/customer-order wording for bookings, delivery, returns, payment,
  damage, and role access.
  Generic fallback SAD sections no longer say patient/visit/medicine unless the
  request is actually clinic-specific.

Regression evidence:
  tests/api/test_gemini_structured.py::test_analysis_fallback_question_uses_event_source_context_not_clinic_template passed
  tests/api/test_sad_preview.py::test_sad_preview_api_allows_draft_ready_uploaded_source_with_minimal_typed_request passed
  tests/api/test_sad_preview.py::test_safe_fallback_preview_generic_event_request_does_not_leak_clinic_terms passed
  tests/api/test_gemini_structured.py passed: 40 passed
  tests/api/test_sad_preview.py passed: 21 passed
  tests/api/test_gemini_structured.py tests/api/test_sad_preview.py tests/api/test_sad_synthesis.py tests/api/test_source_uploads.py passed: 67 passed
  tests/test_mvp_sad_preview_it_readiness_ui.py tests/test_mvp_source_upload_traceability_ui.py passed: 7 passed
  full tests passed: 206 passed
  TypeScript passed
  Next.js production build passed outside sandbox after sandbox blocked Node from lstat C:\Users\User
```

## Manual Smoke Script

1. Start the API and frontend locally.
2. Test the tuition request first.
3. Confirm the first question is domain-aware and not a generic goal question.
4. Answer enough questions to reach draft-ready.
5. Generate SAD preview.
6. Confirm no fallback/debug wording, internal slot refs, invented approvals, or
   stale previous preview content appears.
7. Repeat the workshop request and verify the maintenance SAD has no clinic
   wording leakage.
8. Upload `D:\GoogleCloudHack\.tmp\sadify_upload_test_sources\laundry-workflow.txt`
   or the matching DOCX/PDF, enter only:
   `Please analyse the uploaded laundry shop workflow and ask the next important question.`
   Confirm the next question uses source-aware order/customer/payment/delay
   wording and does not repeat broad goal or normal-flow prompts.
9. Upload `D:\GoogleCloudHack\.tmp\sadify_upload_test_sources\event-rental-workflow.pdf`,
   enter only:
   `Please analyse the uploaded event rental workflow and ask the next important question.`
   Confirm `1 source reference(s) attached`, answer enough questions to reach
   draft-ready, and generate the SAD preview.
10. Confirm the event-rental flow does not block preview after `Ready for draft -
    100%`, and no optional/refinement question or generated SAD section leaks
    clinic roles such as reception, doctors, pharmacy, cashier, patient visits,
    or medicine collection.

## Pass/Fail Rule

Pass only if local tests and browser/manual smoke both meet the expected Q&A and
SAD preview behavior. Local tests and no-cloud smoke passed on 2026-05-21. The
remaining gate is browser/manual smoke in the normal local app setup. If either
tuition or workshop still feels template-driven, TC-021Y remains partial.


---

