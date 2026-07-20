# SADify MVP Web App Test Plan

Date: 2026-05-11
Last updated: 2026-05-25
Status: Active execution guide

## Purpose

This document maps the prototype-to-MVP checkpoints to test cases, gates, expected evidence, and pass criteria.

The MVP uses two readiness layers:

```text
1. Draft-ready: coherent first SAD draft.
2. IT-ready: deeper implementation refinement on the same project before final MVP completion.
```

## Current Execution State

Current stop point:

```text
Current phase: Phase 5 - Drive + Google Docs save path.
MVP-00 through MVP-09: Passed.
Phase 3 Q&A stabilization: Complete.
Phase 4 SAD preview and SAD quality stabilization: Complete. TC-028, Cycle 2A,
Cycle 2B, and anti-repetition Guard B passed manual browser smoke on 2026-05-24.
Active checkpoint: TC-026 MVP Drive Docs Save.
Blocked: TC-025 wiki update approval and TC-027 two-service deploy until TC-026 passes.
```

Phase map:

| Phase | Scope | Status |
| --- | --- | --- |
| Phase 0 | Original planning / challenge context | Complete; historical docs retained |
| Phase 1 | Streamlit prototype baseline | Complete through basic Cloud Run smoke |
| Phase 2 | Proper MVP scaffold and full-stack foundation | MVP-00 through MVP-09 passed |
| Phase 3 | Q&A workflow stabilization | TC-021S and TC-021T passed |
| Phase 4 | SAD preview and SAD quality stabilization | Complete; TC-028 + Cycles 2A/2B passed |
| Phase 5 | Drive + Google Docs save path | Active; TC-026 is current |
| Phase 6 | Wiki update approval + two-service deployment and final smoke | Not started; blocked until TC-026 passes |

MVP-05 passed as a local fake-store slice: guest draft creation, safe signed-in project copy contract, and DraftPanel/API wiring are verified. Real Firestore cloud persistence remains deferred until the Firestore client integration checkpoint.

MVP-06 backend/frontend wiring and live Gemini smoke passed after granting Vertex AI User to `firebase-adminsdk-fbsvc@sadify.iam.gserviceaccount.com`. The backend reached Vertex AI with project `sadify`, location `global`, model `gemini-2.5-flash`, returned `HTTP 200`, validated the structured JSON, and saved local Q&A state.

MVP-07 source upload traceability passed locally on 2026-05-13. `/sources/upload` accepts multipart source files, reuses the local extractor, stores local source records with `SRC-` IDs, returns traceability units and unsupported-file errors, and passes source context/source IDs into analysis. Full Python regression, TypeScript, production build, local API smoke, and rendered browser smoke passed. Real Firestore/Drive source persistence and deployed smoke remain deferred.

MVP-08 Drive repo OAuth passed locally on 2026-05-14. `/drive/repo/connect`, `/drive/repo/disconnect`, and `/drive/repo/status` are signed-in-only; the local repo grant contract records `DG-` IDs, owner, `drive.file` scope intent, planned project repo folders, and save-blocking disconnect state. The frontend has a config-aware Google Identity Services authorization-code panel and shows `Configuration needed` until `NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID` is supplied. No live OAuth exchange, Secret Manager token storage, Drive folder write, Google Doc creation, or deployed smoke happened in this checkpoint.

MVP-09 SAD preview and IT readiness passed locally on 2026-05-14. `/sad/preview` validates a structured SAD preview schema, blocks preview generation until core basics are answered, returns IT readiness, assumptions, open questions, source references, and change tracking, and saves temporary local `SP-` preview state. The frontend adds a compact temporary preview panel and workspace tracking update. A later manual live local smoke generated `SP-000001` with `/auth/session`, `/analysis/requirement`, and `/sad/preview` returning `HTTP 200`. Drive/Docs save, Firestore cloud write, Secret Manager write, Cloud Run deploy, and deployed smoke remain deferred.

Post-MVP-09 stabilization on 2026-05-14 fixed the first Q&A answer loop: selecting a choice or typing an amendment now enables `Continue with answer`, records the previous question/answer in the next analysis request, refreshes the next Gemini question, and updates tracking status. Automated checks passed with focused Q&A UI tests, full Python regression, TypeScript, and production build. Manual continuation against the real backend will consume one Gemini call per submitted answer.

Follow-up Q&A logic stabilization on 2026-05-14 tightened the questionnaire behavior before MVP-10. Top-level fallback categories are single-select and become disabled with `Answered locally` after a specific follow-up is answered. Category-specific questions can be multi-select only when more than one answer may be true. `I'm not sure` is flagged as uncertainty and routes to easier suggested-default yes/no/other-style follow-up choices. Amendment text is disabled until an answer is selected, and `Other / not listed` requires details. This stabilization used local/fake model verification only; no new live Gemini call was run.

Manual Q&A testing after that stabilization found the larger workflow issue documented in `docs/superpowers/development/14_qna_workflow_refinement.md`: the UI mixed user progress, model readiness, and fallback readiness. Confidence was displayed too prominently, and fallback could return the user to a broad top-level menu after a category question. This was resolved by MVP-09.1 / TC-021R before moving to MVP-10.

MVP-09.1 / TC-021R improved the earlier Q&A flow locally, but manual testing on 2026-05-15 showed the deeper architecture is still unstable because categories are still rebuilt from later Gemini turns. The approved replacement is MVP-09.2 / TC-021S: one stable questionnaire plan, slot-based completion, frozen order/labels, backend-owned readiness, reviewed extra categories, and neutral pre-analysis UI.

Partial MVP-09.2 implementation was added, but manual clinic-flow testing on
2026-05-18 failed acceptance:

```text
1. initial business-request facts were under-credited
2. first-turn category routing could still follow Gemini instead of plan order
3. cross-slot semantic drift could pass when IDs looked valid
4. answered questions could repeat later
```

Those continuity gaps were re-tested successfully on 2026-05-18; the manual
clinic flow reached `100%`. The later TC-021U through TC-021Y trail is now
archived as historical quality-debug evidence. TC-028 and Cycles 2A/2B are the
current completed Phase 4 evidence.

TC-028 and its follow-up cycles now close the Phase 4 quality gate:
readiness is evidence-based, score progression is monotonic, fallback turns
preserve merged slot evidence, the second repeated answer exits a slot, and SAD
preview synthesis surfaces every cleared category with paraphrased prose. Manual
browser smoke on 2026-05-24 against laundry and event-rental PDFs reached 100%
readiness with no repeated questions and full 10-section SAD output.

## Gate Rule

Every feature follows:

```text
plan packet gather + alignment cross-check
-> API/doc preflight
-> implementation
-> unit tests
-> local integration tests
-> browser smoke
-> deployed smoke for cloud features
-> update matching TC doc with expected output, real output, evidence, issues, and decision
-> checkpoint summary to user
-> wait for approval before next checkpoint
```

## Plan Packet Alignment

Before implementation begins, collect and compare:

```text
1. active behavior/product note
2. approved design spec
3. implementation plan
4. matching acceptance test case
5. linked schema/data-model docs
6. linked decision-log entries
7. current relevant code and tests
8. current git/worktree status
```

Confirm:

```text
- behavior note, spec, plan, and acceptance test describe the same target
- docs match the current checkpoint status
- the code does not already contradict the assumed starting point
- any external API or cloud dependency is identified before coding
```

If the packet does not align, fix the docs or stop for user clarification before
executing the plan.

## API/Docs Preflight

Every feature then follows:

```text
API/doc preflight
-> unit tests
-> local integration tests
-> browser smoke
-> deployed smoke for cloud features
-> update matching TC doc with expected output, real output, evidence, issues, and decision
-> checkpoint summary to user
-> wait for approval before next checkpoint
```

Before each checkpoint starts, identify whether it touches any external API, SDK, or cloud/browser integration.

If yes, check current official docs first and record:

```text
1. API or SDK name
2. Official doc URL checked
3. Required scopes, permissions, roles, env vars, redirect URLs, or credentials
4. Whether the checkpoint requires network access, cloud billing, deployment, OAuth consent, or user approval
5. Any open setup risk before coding
```

Mandatory preflight areas:

```text
Firebase Auth / Google Identity Platform
Firebase Admin SDK ID token verification
Gemini structured output
Firestore client/API
Google Drive API and Drive Picker
Google Docs API
Secret Manager IAM and token storage
Cloud Run deployment
Next.js and FastAPI build/runtime behavior
```

Do not proceed on memory alone for these areas.

## Evidence Gate

Every feature follows:

```text
unit tests
-> local integration tests
-> browser smoke
-> deployed smoke for cloud features
-> update matching TC doc with expected output, real output, evidence, issues, and decision
```

## Checkpoint Stop Rule

After one checkpoint completes, stop and return a summary to the user:

```text
1. What changed
2. Tests and evidence
3. Potential issues, limitations, or risks
4. What the next checkpoint is
5. What approval or setup is needed before continuing
```

Do not start the next checkpoint until the user approves.

## Checkpoint Test Matrix

| Checkpoint | Test Case | Feature | Local Tests | Browser Smoke | Deployed Smoke |
| --- | --- | --- | --- | --- | --- |
| MVP-00 | TC-015 | Design alignment | Doc search | No | No |
| MVP-01 | TC-016 | Monorepo scaffold | `tests/test_mvp_scaffold.py` | No | No |
| MVP-02 | TC-017 | FastAPI health/contract | `tests/api/test_health_contract.py` | No | No |
| MVP-03 | TC-018 | Workspace shell | frontend build | Yes | No |
| MVP-04 | TC-019 | Firebase Auth session | mocked token tests | Yes | Local live sign-in passed; deployed smoke later |
| MVP-05 | TC-020 | Guest draft migration | fake repo + local smoke | Yes | Local only; real Firestore/deployed smoke later |
| MVP-06 | TC-021 | Live Gemini Q&A | schema parser + fake model tests + answer-loop UI test | Yes | Local live smoke passed; deployed smoke later |
| MVP-07 | TC-022 | Source upload traceability | extraction + API tests | Yes | Local only; deployed smoke later |
| MVP-08 | TC-023 | Drive repo OAuth | mocked grant tests | Yes | Local only; live OAuth/deployed smoke later |
| MVP-09 | TC-024 | SAD preview/readiness | schema + renderer tests | Yes | Local live preview smoke passed; deployed smoke later |
| MVP-09.1 | TC-021R | Category-first Q&A refinement | backend/frontend Q&A state tests passed | Local HTTP 200 smoke | Superseded by TC-021S after manual continuity testing |
| MVP-09.2 | TC-021S | Stable questionnaire plan refactor | plan continuity tests, slot tests, UI flow tests | Manual clinic rerun reached `100%` on 2026-05-18 | Passed |
| MVP-09.3 | TC-021T | Q&A ready state and SAD preview handoff | Q&A UI tests + SAD preview context tests | Live local smoke passed on 2026-05-18 | Functional pass; quality follow-up required before MVP-10 |
| MVP-09.4 | TC-021U | Q&A + SAD synthesis quality | merged-facts, diagnostic filtering, prompt guard, ready-state UI, safe SAD fallback, full regression | manual video smoke confirmed fallback HTTP 200 but content still raw | Passed for route/synthesis guard; TC-021V required |
| MVP-09.5 | TC-021V | SAD fallback composition quality | clean request boundary, structured fallback SAD sections, amendment preservation, optional-gap filtering, full regression | manual video smoke showed partial pass and remaining quality failure | Partial pass |
| MVP-09.6 | TC-021W | User-facing SAD draft quality | professional title, synthesized sections, normalized amendments, coherent readiness, collapsed diagnostics, full regression | workshop manual smoke failed progression | Automated checks pass; followed by TC-021X and TC-021Y |
| MVP-09.7 | TC-021X | Evidence-first Q&A depth and valid preview coherence | fact extraction, facet readiness, contextual next question, structured answers, valid preview UI guardrails | local tests passed; manual progression failed | Followed by TC-021Y |
| MVP-09.8 | TC-021Y | Domain-aware Q&A and SAD quality hardening | archived historical checks | Superseded by TC-028 + Cycles 2A/2B | Archived |
| MVP-09.9 | TC-028 | Evidence-based readiness and SAD quality stabilization | quote-validated slot evidence, monotonic readiness, no-repeat guard, full SAD section coverage | Manual laundry and event-rental PDF smoke passed on 2026-05-24 | Passed |
| MVP-10 | TC-026 | Drive + Google Docs save | fake Drive/Docs tests first; live OAuth/Drive/Docs only after explicit approval | Active | Planned |
| MVP-11 | TC-025 | Wiki update approval | path/link/backup tests | Blocked until TC-026 passes | Planned |
| MVP-12 | TC-027 | Full deployed MVP | selected regression suite | Blocked until TC-026 passes | Planned |

## Phase 1 Required Evidence

MVP-01 evidence:

```text
pytest tests/test_mvp_scaffold.py -q
```

MVP-02 evidence:

```text
pytest tests/api/test_health_contract.py -q
local GET /health response
```

MVP-03 evidence:

```text
npm run build
browser screenshot of workspace shell
```

MVP-04 evidence:

```text
pytest tests/api -q
pytest -q
npm run build
browser smoke of guest mode and disabled Google sign-in when config is missing
live Google sign-in smoke after Firebase web config is provided
```

MVP-05 evidence:

```text
pytest tests/api/test_guest_drafts.py -q
guest draft API response body
```

MVP-06 evidence:

```text
pytest tests/api/test_gemini_structured.py -q
pytest tests/test_mvp_live_gemini_qna_ui.py -q
pytest tests/api/test_gemini_structured.py tests/test_mvp_live_gemini_qna_ui.py -q
pytest tests -q
npx tsc --noEmit
npm run build
one live Gemini schema-valid response after IAM is fixed
browser screenshot of generated question after live smoke passes
choice/amend continuation refreshes the next question
fallback top-level categories disable after answered; uncertainty routes to easier follow-up
```

MVP-07 evidence:

```text
pytest tests/api/test_source_uploads.py tests/test_mvp_source_upload_traceability_ui.py -q
pytest tests -q
node ...\typescript\bin\tsc -p apps\web\tsconfig.json --noEmit
npm --prefix apps\web run build
local POST /sources/upload multipart response with SRC source ID and traceability units
browser smoke of SourceUploadPanel and no-file upload validation message
```

MVP-08 evidence:

```text
pytest tests/api/test_drive_repo.py tests/test_mvp_drive_repo_oauth_ui.py -q
pytest tests -q
node ...\typescript\bin\tsc -p apps\web\tsconfig.json --noEmit
npm --prefix apps\web run build
browser smoke of DriveRepoPanel showing Project repo, Connect Google Drive, Disconnect Google Drive, and Configuration needed
```

MVP-09 evidence:

```text
pytest tests/api/test_sad_preview.py tests/test_mvp_sad_preview_it_readiness_ui.py -q
pytest tests -q
node ...\typescript\bin\tsc -p apps\web\tsconfig.json --noEmit
npm --prefix apps\web run build
local rendered smoke of SadPreviewPanel showing SAD preview, Generate SAD preview, Temporary preview, IT readiness, and Tracking status
manual live local POST /sad/preview 200 with temporary preview ID when explicitly approved
```

MVP-09.1 / TC-021R evidence:

```text
pytest tests\api\test_gemini_structured.py -q -> 13 passed
pytest tests\test_mvp_live_gemini_qna_ui.py -q -> 10 passed
pytest tests\api\test_gemini_structured.py tests\test_mvp_live_gemini_qna_ui.py -q -> 23 passed
pytest tests -q -> 151 passed
tsc --noEmit -> passed
npm --prefix apps\web run build -> passed
temporary local Next standalone HTTP smoke on http://127.0.0.1:3100/ -> 200, then server stopped
```

MVP-09.3 / TC-021T evidence:

```text
pytest tests\test_mvp_live_gemini_qna_ui.py -q -> 13 passed
pytest tests\api\test_sad_preview.py -q -> 9 passed
pytest tests\api\test_gemini_structured.py tests\api\test_sad_preview.py tests\test_mvp_live_gemini_qna_ui.py -q -> 54 passed
pytest tests -q -> 179 passed
tsc --noEmit -> passed
npm --prefix apps\web run build -> passed
temporary local frontend browser smoke on http://localhost:3000/ -> page loaded, no console errors, then server stopped
manual live SAD preview smoke -> passed on 2026-05-18 with `HTTP 200`
quality review -> failed progression because SAD output conflicted with Q&A readiness and leaked fallback/internal content
```

MVP-09.4 / TC-021U evidence:

```text
pytest tests\api\test_sad_preview.py tests\api\test_sad_synthesis.py tests\api\test_gemini_structured.py tests\test_mvp_sad_preview_it_readiness_ui.py -q -> 48 passed
pytest tests -q -> 184 passed
tsc --noEmit -> passed
npm --prefix apps\web run build -> passed after sandbox escalation
manual live Gemini/browser smoke on 2026-05-19 -> Q&A calls returned HTTP 200, but /sad/preview returned 502 twice
safe fallback fix -> implemented and automated
manual video smoke on 2026-05-19 -> /sad/preview returned HTTP 200 and saved SP preview, but fallback SAD content still exposed raw Q&A transport/history
```

MVP-09.5 / TC-021V evidence:

```text
pytest tests\api\test_sad_synthesis.py -q -> 3 passed
pytest tests\api\test_sad_preview.py -q -> 14 passed
pytest tests\test_mvp_live_gemini_qna_ui.py -q -> 14 passed
pytest tests -q -> 189 passed
tsc --noEmit -> passed
npm --prefix apps\web run build -> passed after sandbox escalation
manual video smoke on 2026-05-19 -> partial pass. Clean business request and
transport-log hiding passed, but user-facing quality failed because the preview
still showed fallback/debug framing, 35% Low confidence after Q&A 100%, repeated
request text, shallow answer bullets, literal amendment wording, repeated source
refs, and empty/noisy details.
```

MVP-09.6 / TC-021W evidence:

```text
pytest tests\api\test_sad_preview.py -q -> 17 passed
pytest tests\test_mvp_sad_preview_it_readiness_ui.py -q -> 3 passed
pytest tests -q -> 193 passed
tsc --noEmit -> passed
npm --prefix apps\web run build -> passed
manual video smoke -> pending; expected professional Layer 1 SAD draft with no normal-view debug framing
```

## Official Planning Notes

Use narrow permissions where possible:

- Firebase web auth persistence defaults to local browser persistence, which matches the "do not always log in" requirement.
- Backend should verify Firebase ID tokens with Firebase Admin SDK before trusting a signed-in user.
- Gemini supports structured outputs with JSON Schema for `gemini-2.5-flash`; still validate business rules in application code.
- Docs `documents.create` can use `https://www.googleapis.com/auth/drive.file`, which is narrower than full Drive.
- Secret Manager `secretAccessor` only reads secret payloads; adding or managing token versions needs additional least-privilege role verification.

## Manual Test Rules

For each browser smoke:

```text
1. Use a cross-domain generic requirement.
2. Do not hardcode the warehouse scenario.
3. Confirm question language is simple.
4. Confirm answer choices are shown.
5. Confirm amend/free-text option is shown.
6. Confirm overall readiness is the only normal Q&A percentage.
7. Confirm question areas use word statuses instead of percentages.
8. Confirm AI confidence is hidden or only shown in collapsed diagnostics.
9. Confirm technical details are hidden unless expanded.
10. Confirm no secrets, access tokens, Drive folder IDs, or raw credentials appear in UI/log output.
```

## Deployed Smoke Rules

For cloud features:

```text
1. Deploy only after local tests and browser smoke pass.
2. Use short test input to control Gemini cost.
3. Use a test Google account and test Drive folder.
4. Record Cloud Run service URLs.
5. Record health endpoint response.
6. Record browser screenshot.
7. Record Drive/Docs links only if they are safe test links.
8. Record failures with logs redacted.
```

## Stop Conditions

Stop and fix before moving on if:

- Schema validation fails.
- Firebase session does not persist.
- Backend accepts unauthenticated signed-in-only actions.
- Guest draft cannot be migrated safely.
- Gemini output writes directly to Firestore/Drive without validation.
- Drive OAuth scope is broader than planned without explicit approval.
- User-facing UI becomes report-like or technical instead of simple Q&A.
- Normal Q&A view shows more than one percentage or mixes overall readiness, model confidence, fallback state, and category details.
- The user is bounced back to a broad top-level menu before the active category is clear enough.
