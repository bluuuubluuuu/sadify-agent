# SADify Current Work Brief

Date: 2026-06-19
Status: GitHub issue relaunch implemented and automated regression passed; TC-036 live recovery smoke and deployment decision pending

## TC-036 GitHub Issue Relaunch - PENDING LIVE SMOKE

Implementation is complete on `codex/mvp-monorepo-scaffold` through commit `1d3fee2`:

- immutable `github_issue_sets` persist by `(grant_id, project_id, save_id)` in memory or Firestore;
- authenticated prepare resolves an owned saved SAD and persists before approval;
- relaunch performs no model call and mints a fresh GATE 3 approval;
- MCP checks stable body markers across paginated open/closed issues and reports created/skipped totals;
- saved history shows a resume action only for prepared saves and uses the locked repository;
- project deletion removes issue sets before the project record and leaves remote GitHub issues unchanged.

Automated verification on 2026-06-19:

```text
652 passed, 4 skipped, 4 warnings in 37.48s
npx tsc --noEmit: passed
npm run build: compiled successfully
```

Release decision: pending. Memory-mode invalid/valid PAT recovery and Firestore restart/live GitHub dedup smokes require throwaway credentials and evidence. Do not deploy or mark TC-036 Passed until those checks are recorded in `testing/test_cases/TC-036-github-issue-relaunch.md`.

Accepted limitation: simultaneous clients can race between marker read and issue creation. Sequential retries are idempotent; v1 is not globally exactly-once.

## TC-034 SADify Analyst Agent - ACTIVE

Active test: `docs/superpowers/testing/test_cases/TC-034-sadify-analyst-agent.md`
Active plan: `docs/superpowers/plans/2026-06-04-tc034-sadify-analyst-agent.md`

Status on 2026-06-05:

- P0-P4 are complete, CC-reviewed, committed, and live-smoked locally with
  Gemini Flash through real Drive Doc save, wiki update, and wiki-conflict
  overwrite re-approval.
- GATE 3 passed: deterministic approval was live-verified on 2026-06-05.
  `/agent/approve` executes only approved actions, does not re-run the LLM,
  consumes the approval token on success, keeps the token on hard write error,
  and converts wiki conflict into re-approval.
- TC-034c polish shipped:
  - collaborative finalize (`e0f9fd1`): trust the existing Q&A when a draft is
    valid, fold review gaps into open questions, and avoid re-asking answered
    slots.
  - closed review -> revise loop (`0889aab`): feed review issues into the next
    regeneration, preserve the no-fabrication guard, regenerate only after a
    current-draft `regenerate` verdict, and add a deterministic draft safety-net.
  - live wiki resolution (`0889aab`): lazily resolve Drive/Secret services in
    the agent wiki path when live config is enabled.
  - single entry point and clearer UI (`798a325`, `18a6aa9`, `da153be`):
    primary `Finalize with agent`, secondary `Quick draft`, no duplicate
    PreviewPane finalize button, Drive-vs-wiki approval/result clarity, and
    sidebar history refresh after agent save.
  - wiki conflict UX (`bce7488`): return completed Drive-save actions when wiki
    conflict asks for overwrite re-approval.
- Latest reported verification: backend suite `537 passed, 4 skipped`;
  frontend `npx tsc --noEmit` and `npm run build` passed.
- P5 MCP/external-tool work has not started. Run the tool-ecosystem brainstorm
  before implementation; compare GitHub Issues via MCP against routing
  Drive/Docs through MCP, then recommend one.
- P6 deploy, demo video, and architecture writeup have not started. Do not
  deploy without explicit user approval.

## TC-032 Gemini Model Picker - PASSED

TC-032 is implemented, deployed, and production-smoked. It adds a backend-owned Gemini
catalog with three models (`gemini-2.5-flash` default, `gemini-2.5-pro`,
`gemini-2.5-flash-lite`), optional model fields on Q&A and SAD preview
requests, a dynamic picker populated from `GET /models`, localStorage
persistence, and adapter-level fallback to the backend default when a selected
model is invalid or unavailable.

Important backend fix: commit `ae97f8e` restored Pro after the Task-4 prune by
making generation config model-aware. Pro keeps thinking enabled with a larger
output ceiling; Flash and Flash-Lite preserve the original
`thinking_config={"thinking_budget": 0}` behavior. Do not revert this fix or
touch backend model files while continuing TC-032/TC-033.

Local verification on 2026-06-04:

```text
..\..\.venv\Scripts\python.exe -m pytest -q
488 passed, 4 skipped

npx tsc --noEmit
passed

npm run build
passed
```

Production deployment on 2026-06-04 followed the TC-027 path. Current live
revisions:

- `sadify-api` -> `sadify-api-00005-pc2`
- `sadify-web` -> `sadify-web-00002-vzw`

Production smoke evidence:

- `GET /models` returned Flash default plus Pro and Flash-Lite.
- Live Flash and Pro API calls each returned Q&A analysis + SAD preview.
- Browser smoke selected `Gemini 2.5 Pro` in the deployed picker and completed
  one visible Q&A turn.
- Cloud Logging showed no recent `sadify-api` errors after the deploy/smoke.

Layer 2 technical model and diagrams are now TC-033. Its local docs were renamed
to `docs/superpowers/specs/2026-06-03-tc033-sadify-layer2-technical-model-design.md`
and `docs/superpowers/plans/2026-06-03-tc033-sadify-layer2-technical-model.md`.

## TC-027 Deploy — DONE (D-095)

Both services live in `asia-southeast1`, scale-to-zero, runtime SA
`sadify-agent-sa` (ADC):
- Backend `sadify-api` → `https://sadify-api-594758969655.asia-southeast1.run.app`
- Frontend `sadify-web` → `https://sadify-web-594758969655.asia-southeast1.run.app`

7-case browser smoke all pass, zero 5xx: guest Q&A → Google sign-in → Drive
connect → SAD preview (amendments incorporated) → save Google Doc (SV-000001) →
8-file wiki → Firestore-persisted history survived refresh.

Deploy artifacts: root `Dockerfile` (backend, `--source .` so it includes both
`services/api/src` + `src/`), `apps/web/Dockerfile` + `apps/web/cloudbuild.yaml`
(frontend, bakes `NEXT_PUBLIC_*`). Three backend deps fixed mid-deploy
(python-multipart, firebase-admin, google-genai; commit 58aa315). Two required
post-deploy console steps: Firebase Authorized domains + OAuth JS origins for
the run.app frontend.

Optional follow-up (deferred, not required): prettier URL `sadify.web.app` via
Firebase Hosting; minor SAD per-section source-attribution polish.

Plan: `docs/superpowers/plans/2026-06-02-tc027-two-service-cloud-run-deploy.md`.

## Read First

Open these for the next development session:

1. `CLAUDE.md`
2. `context.md`
3. `docs/superpowers/CURRENT.md`
4. `docs/superpowers/development/00_development_index.md`
5. `docs/superpowers/testing/test_cases/TC-026-mvp-drive-docs-save.md`
6. `docs/superpowers/development/04_google_cloud_setup_runbook.md`

Open only when needed:

- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `docs/superpowers/development/07_decision_log.md`
- `docs/superpowers/testing/test_case_index.md`
- `docs/superpowers/development/08_new_chat_handoff.md`

## Current Status

Code worktree:

`D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`

Current phase:

TC-034 SADify Analyst Agent. TC-034a/b/c are passed through the local/live
Gemini Flash browser smoke, including real Drive Doc save, wiki update, and
wiki-conflict overwrite re-approval. Next focus is P5 MCP/external tool
planning and the shared live Drive-service resolver cleanup. P6 deploy is not
started.

Completed baseline:

- Streamlit prototype baseline complete.
- MVP scaffold (MVP-00 through MVP-09) passed.
- TC-019 live Firebase sign-in passed locally on 2026-05-13.
- TC-021 live Gemini Q&A passed locally on 2026-05-13.
- TC-022 source upload traceability passed locally on 2026-05-13.
- TC-023 Drive repo OAuth contract passed locally on 2026-05-14
  (live OAuth exchange + token storage still deferred).
- TC-024 local SAD preview + IT readiness passed on 2026-05-14.
- TC-028 evidence-based readiness manual smoke passed on 2026-05-24.
- Cycle 2A (monotonic readiness, sticky applicability, merged
  slot_evidence persistence) shipped and verified on 2026-05-24.
- Cycle 2B (section coverage, assumptions/open-questions population,
  per-section source refs, paraphrasing, understanding-summary
  preservation across fallback) shipped and verified on 2026-05-24.
- Anti-repetition Guard B tightened to threshold 2 (no question is
  ever asked a third time).
- TC-026 local/fake SAD save path passed on 2026-05-25. It saves an
  existing `SP-` preview into a local project-repo artifact record with
  fake Google Doc URL/path, `_SADify` manifest/change-log artifacts,
  source references, stable error codes, and idempotent repeat saves.
- TC-026B live Drive/Docs save passed on 2026-05-25. Real OAuth
  authorization-code exchange, real `SADify Projects` Drive folder
  create-or-find, real Markdown-to-Doc upload, refresh token persisted
  in Secret Manager (`sadify-drive-token-<uid>`), and per-user secret
  deleted on disconnect. Behind the double env gate
  `SADIFY_DRIVE_MODE=live` + `SADIFY_DRIVE_LIVE_ENABLED=1`; local mode
  remains the default so the local regression and TC-026 manual smoke
  stay offline.
- TC-025A wiki snapshot passed on 2026-05-27. Live `POST /sad/wiki/preview`
  + `POST /sad/wiki/update` wrote a single `Wiki/Wiki.md` Markdown
  snapshot into the connected `SADify Projects/Wiki` subfolder.
  Hash-based conflict detection with explicit overwrite confirmation,
  in-memory `WikiStateRepository`, and 9 stable error codes. Composer
  superseded by TC-025B.
- TC-025B encyclopedia wiki passed on 2026-05-28. Multi-file Obsidian-
  style knowledge graph per `context.md` lines 439-468. Eight files per
  update (`Wiki.md` index + seven categorized notes), title-normalization
  routing of SAD sections to category files, `[[wiki links]]`, YAML
  frontmatter, per-file hash tracking, bulk conflict approval, and
  backup of managed files to `_SADify/wiki-backups/<timestamp>/` before
  overwrite. 387 local-mode regression green; live Case 13 smoke
  passed.
- TC-026D project isolation passed on 2026-05-28. Per-project Drive
  subfolders (`SADify Projects/<Project>/SAD/`, `/Wiki/`, `/_SADify/`).
  Active project tracked on `DriveRepoRecord`. Per-project counters
  for SV-/SA-/SM- (SP- stays global). `ProjectPanel` dropdown +
  New project + Refresh. `CreateProjectDialog` auto-opens on
  `PROJECT_REQUIRED` 409. 428 local-mode regression green; live
  Cases 15-19 smoke passed.
- TC-026E project save history passed on 2026-05-29. `GET
  /projects/{project_id}/saves` + `ProjectHistoryPanel`. History
  survives page refresh (auth-restore re-fetches `/drive/repo/status`
  then the saves), auto-refreshes after each save, isolates per
  project. In-memory only (Firestore persistence post-MVP). 446
  local-mode regression green; live Case 20 smoke passed.
- TC-029 analysis-state reset passed on 2026-05-29. Explicit
  `analysis_session_id` keys carry-forward per frontend session,
  regenerated on new-source-upload / project-switch. Fixes cross-source
  content bleed. 457 local-mode tests; live smoke passed.
- TC-030 Firestore persistence passed on 2026-05-30. Project/SAD-save/
  wiki-state/Drive-grant repositories persist to Firestore Native Mode
  behind `SADIFY_PERSISTENCE=firestore` (default `memory`); analysis/Q&A
  stays in-memory. Two P0 transaction bugs (read-after-write ordering;
  un-begun manual transactions) found in review and fixed via
  `run_in_transaction` + the official `firestore.transactional`
  decorator. 471 local-mode tests + 4 live round-trips (real Firestore)
  + live restart-survival smoke passed. The deploy blocker (in-memory
  state loss) is cleared. Commits 969cad8, 21616c7, c2166cd.
- Frontend UI redesign (D-092) shipped on 2026-06-02. The stacked
  debug-panel frontend is replaced by a guided adaptive 3-pane chat
  workspace (Sidebar | Chat | Preview) driven by a derived `stage`.
  Prior request/transport/fallback logic was extracted verbatim into
  hooks (Q&A carry-forward string byte-identical); old panels removed;
  CSS Modules + central design tokens + inline Phosphor SVG icons (no
  new dependency). Codex follow-up added a persistent wiki-updated
  indicator, a per-project Drive repo link, and scrollbar polish.
  `apps/web` and the Python static UI tests only; backend untouched.
  `tsc --noEmit` clean, static UI tests green, `next build` OK.
  Commits 05fb247..56f647d, de7209f.
- Readiness binding fix (D-092a) shipped on 2026-06-02 (commit 87d059d).
  Coverage list + readiness label/confidence now read the stable
  `questionnaire.*` state, falling back to raw only when `questionnaire`
  is null. Fixes per-turn coverage flicker/disappearance and the
  92-100% + "Fallback question ready"/Low mismatch. Frontend-only.
- TC-031 readiness confidence semantics verified on 2026-06-02 (read-only).
  Score (completeness %) and confidence (evidence-grounding) are
  independent by design (D-093): 90%+/"Ready for draft" with Low
  confidence is expected, not a bug. A/B/C already covered in
  `test_slot_evidence.py`; C2/D/D2 automated (commit 78e7183, full suite
  460 passed); Test-F logging held.
- A+B + D-wording manual browser smoke PASSED on 2026-06-02 (catering
  event, 7-turn live Gemini run). A: `locked=` ratchet strictly monotonic
  across all turns (no coverage regression). B: the real fallback turn
  AN-000007 rendered 100%/"Ready for draft"/"High evidence" — NOT
  "Fallback question ready/Low" — confirming the raw-binding regression is
  fixed. D-wording: badge reads "{level} evidence" with tooltip; SAD
  preview collapsible reads "Implementation review (separate from draft
  readiness)". Commits 87d059d + 12898cb smoke-validated.

## Phase 4 Stop Point

```text
Worktree: D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
Branch:   codex/mvp-monorepo-scaffold

Final-state verification on 2026-05-24:
- Score strictly monotonic across 8-turn live runs (laundry + event
  rental PDFs).
- No question repetition: every turn advances to a new slot.
- Provenance buckets correctly separate source-derived vs Q&A-derived
  categories.
- SAD output surfaces all cleared categories (10 sections).
- Understanding-summary panel preserves the real summary across
  fallback turns instead of leaking the diagnostic narrative.
- 276 Python tests pass; TypeScript clean.
```

## Phase 5 Stop Point

```text
Worktree: D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
Branch:   codex/mvp-monorepo-scaffold

TC-026 local/fake save verification on 2026-05-25:
- Backend save tests: 8 passed.
- Focused final regression: 46 passed.
- Full final Python regression: 290 passed (after the abf2860 regen-reset
  regression test landed).
- Frontend TypeScript: passed outside sandbox after sandbox blocked Node
  from lstat C:\Users\User.
- Local save-flow smoke passed:
  save_id=SV-000001
  doc_path=SAD/SAD-SP-000001-SV-000001.google_doc
  source_ids=SRC-000001
  disconnect_code=SAD_SAVE_REPO_DISCONNECTED
- Manual browser smoke through all six cases passed on 2026-05-25:
  Case 3 -> 409 SAD_SAVE_REPO_REQUIRED
  Case 4 -> 200 SV-000001 / LOCAL-GDOC-000001
  Case 5 -> 200 idempotent (same SV-000001)
  Case 6 -> 409 SAD_SAVE_REPO_DISCONNECTED
  Case 7 -> 200 SV-000002 / LOCAL-GDOC-000002 (new grant DG-000002)
  Case 8 -> 200 SV-000003 / LOCAL-GDOC-000003 (new preview SP-000002,
            saved card cleared on regenerate)
- No live Drive, Docs, OAuth exchange, Secret Manager write, dependency
  install, Cloud API enablement, wiki approval, or deployment occurred.
```

Active focus:

TC-034 submission-readiness planning. P5 MCP/external-tool work is the firm
Track-1 gap; do the tool-ecosystem brainstorm and approval plan before writing
MCP code. Carry the cleanup to extract the shared live Drive-service resolver
between `agent/tools.py` and `routes/sad.py`. Do not start P6 deploy without
explicit user approval.

Must not start without explicit approval:

- TC-034 P5 MCP implementation.
- TC-034 P6 deploy.

## What Just Shipped

### Q&A Workflow

- Carry-forward merge across turns (no per-turn flicker).
- One-way category ratchet (no revert, no pop-up).
- Provenance buckets: "Already understood" = source-derived,
  "Completed areas" = Q&A-derived; frozen once set.
- Guard A: substantive user answers become evidence even if Gemini's
  judgement misses them.
- Guard B: second answer for the same slot ends the loop; preserves
  evidence strength.

### Readiness (Cycle 2A)

- Fixed denominator over all canonical required slots.
- `not_applicable` counts as resolved.
- Applicability sticky-monotonic in both directions.
- Merged slot_evidence persisted into the saved response so carry-forward
  survives fallback turns.

### SAD Synthesis (Cycle 2B)

- Context lists every cleared category, partial-evidence slots, and deferred
  slots as candidate blocks.
- Prompt requires one section per cleared category, populates Assumptions from
  partial slots, Open Questions from deferred slots.
- Prompt forbids verbatim answer pasting.
- `understanding_summary` preserved across fallback turns.

### Local SAD Save (TC-026)

- Backend `POST /sad/save` with Firebase-auth guard.
- Stable save error codes for missing auth, no active repo, disconnected repo,
  missing preview ID, and unknown preview ID.
- Local `SadSaveRepository` with idempotency key
  `(user_id, repo_id, preview_id, preview_revision)`.
- Fake Google Doc artifact, `_SADify` manifest/change-log artifacts, and source
  reference artifacts.
- Frontend Save to project repo action after a preview exists.
- Workspace tracking update after save.

## Latest Commits

```text
da153be feat(web): clearer Drive-vs-wiki approval/result UI + save-history refresh
bce7488 fix(agent): surface completed save on wiki conflict for UI refresh
18a6aa9 feat(web): single agent entry point (Finalize hero + Quick draft)
0889aab feat(agent): closed revise loop, draft safety-net, live-wiki fix
798a325 feat(web): make "Finalize with agent" the hero action in the ready footer
e0f9fd1 fix(agent): trust Q&A and finalize instead of re-asking (collaborative)
31d256d feat(web): agent activity timeline (Finalize with agent)
d1285d2 feat(agent): SSE event stream for /agent/finalize
686e3de fix(agent): make approved writes deterministic
639d043 feat(agent): approval-gated Drive/wiki writes + /agent/approve
e44951c feat(web): add dynamic Gemini model picker
ae97f8e fix(models): restore gemini-2.5-pro with model-aware generation config
15f5946 feat(models): fail over unavailable Gemini selections
9813e51 feat(models): thread optional model through analysis and preview
c1f88f6 feat(models): add Gemini model catalog endpoint
de7209f feat(ui): persistent wiki-updated indicator, per-project repo link, scrollbar polish
56f647d feat(ui): flip / onto new shell; remove old panels; migrate static UI tests
15e2428 fix(ui): lock 3-pane to viewport; scroll each pane independently
5a0d0cf feat(ui): preview/save/wiki - PreviewPane hero, WikiDialog, useSadSave (logic preserved)
4b19d7c feat(ui): stage model + adaptive 3-pane responsive AppShell
05fb247 feat(ui): design tokens, Plus Jakarta Sans, phosphor icons, loading primitives
c2166cd test(persistence): live firestore smoke for save/wiki/drive-grant round-trips
21616c7 fix(persistence): begin firestore transactions via transactional decorator
969cad8 feat(persistence): firestore-backed repositories behind SADIFY_PERSISTENCE
670b5b9 fix(analysis): deterministic per-session reset via explicit analysis_session_id
8f1a302 feat(history): per-project save history endpoint and UI panel
928d7f7 feat(projects): per-project Drive isolation with active project switching
23107b3 feat(wiki): encyclopedia knowledge graph with per-file conflict and backup
8e19296 fix(wiki): write Wiki.md into Wiki/ subfolder instead of project root
0b1ad4b feat(wiki): live wiki update with conflict-aware approval
95d1eda chore(drive): clean up TC-026B env var naming and OAuth scope relaxation
ee87b18 feat(drive): live drive/docs save behind SADIFY_DRIVE_MODE=live
abf2860 feat(web): add local dev connect + reset save state on preview regen
9f4900b feat(web): add local SAD save action
e917a36 feat(sad): add local SAD save contract
c928b83 feat(sad): cycle 2b - surface every cleared category, populate assumptions/open-questions, preserve summary
4a3f288 fix(qna): zero-tolerance anti-repetition - second answer ends the loop
8333f21 fix(readiness): persist merged slot_evidence so carry-forward survives fallback turns
f4faabb fix(readiness): score is now monotonic - never drops between turns (Cycle 2A)
ca5933e fix(qna): break the same-slot question loop via answer-based coverage
b195bcf fix(questionnaire): tag category provenance so bucket labels stop flipping
6cf04ff fix: one-way category ratchet - no revert, no pop-up
```

## Latest Verification

Most recent run on 2026-06-05:

```text
TC-034 backend regression: 537 passed, 4 skipped
Frontend TypeScript: npx tsc --noEmit passed
Frontend production build: npm run build passed
GATE 3 live re-probe: /finalize -> awaiting_approval and
/approve -> save_to_drive + update_wiki with no regeneration; bogus token
refused with zero writes.
TC-034c live Flash browser smoke: Finalize with agent -> approval card ->
Approve & save -> real Drive Doc write + wiki update; wiki conflict returned
overwrite re-approval and overwrite approval updated the wiki.
```

Earlier run on 2026-05-25:

```text
Full Python regression: 290 passed
Focused save/preview/drive/UI regression: 46 passed
Frontend TypeScript: passed outside sandbox
Local save-flow smoke: passed; repeat save returned the same save ID,
                       source references were linked, disconnected repo
                       returned SAD_SAVE_REPO_DISCONNECTED.
Manual browser smoke:  6/6 cases passed (Cases 3-8); see TC-026 Evidence
                       block for the full POST sequence. No googleapis.com,
                       oauth2.googleapis.com, or Secret Manager traffic.
```

## TC-034 Submission Next Checklist

Before starting P5 MCP/external-tool implementation:

1. Run the tool-ecosystem brainstorm: compare GitHub Issues via MCP against
   routing Drive/Docs save through MCP, weighing demo value against risk.
2. Recommend one path for approval. Current bias: GitHub Issues via MCP has
   stronger Track-1/demo value; Drive/Docs via MCP is lower risk but weaker
   because SADify already saves to Drive/Docs.
3. Keep GATE 3 intact: no Drive/wiki/GitHub write without approval.
4. Carry the Q7 cleanup: extract shared live Drive-service resolution from
   `agent/tools.py` and `routes/sad.py` before or alongside P5.
5. After approved MCP work passes locally, request explicit deploy approval.
   Production deploy and smoke remain separate.

## Next-Development Rescan (Phase 5/6 prep)

### Path A: TC-026B live Drive/Docs save

Backend extension points (modify in place — do not duplicate):

- `services/api/src/sadify_api/services/drive_repo.py`
  `connect_repo()` currently stores `token_store="local_metadata_only"`. Add
  a real authorization-code exchange and persist refresh-token reference into
  Secret Manager. Keep the existing `DriveRepoRecord` shape; add fields only
  if needed for token version metadata.
- `services/api/src/sadify_api/services/sad_save.py`
  `save_preview()` currently emits a `LOCAL-GDOC-` ID. Add a Drive/Docs
  client call path that writes a real Doc into the connected folder and
  returns the real `file_id` + `url`. Preserve the existing local-fake path
  behind a feature flag or env switch so tests stay offline.
- `services/api/src/sadify_api/routes/sad.py`
  No change needed to the route — schemas and idempotency stay the same.

Frontend extension points:

- `apps/web/src/lib/googleOAuth.ts` already has the GIS authorization-code
  helper. Enabling `NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID` switches the live
  "Connect Google Drive" button on and auto-hides the local-dev button.
- `apps/web/src/components/DriveRepoPanel.tsx` needs a folder picker when
  Drive Picker is wired (not in repo yet).

Cloud prerequisites (must land in `04_google_cloud_setup_runbook.md` before
any live call):

- Drive API + Docs API enablement in project `sadify`.
- OAuth consent screen + Web client ID with the SADify frontend origin.
- Secret Manager role split: Admin (one-time create), Version Adder (token
  rotation), Accessor (runtime read).
- Service-account access pattern for Drive scopes (likely
  `https://www.googleapis.com/auth/drive.file` only — already declared in
  `DRIVE_FILE_SCOPE`).

Schemas already in place:
- `DriveRepoRecord.token_store` field exists.
- `DriveRepoRecord.saves_blocked` flag works end-to-end.
- `SadSaveArtifact.file_id` / `url` types accept real Google IDs.

Open questions to resolve before writing the TC-026B plan:
- Folder selection UX: Drive Picker vs free-form folder ID input.
- Doc body composition: native Docs `batchUpdate` from SAD sections vs
  rendered Markdown blob attached as Doc.
- Token rotation cadence and Secret Manager naming convention.

### Path B: TC-027 two-service Cloud Run deploy of current local-save build

Status: not started. No Dockerfile, no cloudbuild config, no .cloud-run
manifests anywhere in the repo or worktree as of 2026-05-25.

What exists:
- `Procfile` at repo root (Streamlit-era, likely outdated for two-service).
- `pyproject.toml` for backend and worktree.
- `apps/web/package.json` (Next.js build).

What needs to be authored before TC-027 plan:
- Two Dockerfiles: one for `services/api` (uvicorn + sadify_api), one for
  `apps/web` (Next.js production build).
- Cloud Run service definitions for both, in region `asia-southeast1`.
- Service-account binding: existing `sadify-agent-sa@sadify.iam.gserviceaccount.com`
  for backend; frontend runs unauthenticated.
- Build/push pipeline (Cloud Build trigger or local `gcloud run deploy`).
- Frontend env wiring for backend base URL via Cloud Run service URL.

Deploy can ship the current local-fake save path or wait until TC-026B is
live. Either is acceptable; TC-026B-first is cleaner because deploying the
local-fake path creates a public URL that doesn't actually persist anything
durable.

### Path C: TC-025 wiki update approval

Smaller scope, but the current TC-025 spec assumes a real Drive write target
exists. Without TC-026B, TC-025 would have to operate against the local-fake
save record. Recommend deferring TC-025 until after TC-026B.

### Recommended next slice

1. TC-026B live Drive/Docs/OAuth/Secret Manager.
2. TC-025 wiki update approval (now has a real save target).
3. TC-027 two-service Cloud Run deploy.

User approval + billing confirmation required before step 1.

## Stop Rule

Do not enable Drive / Docs API or write to a real Drive folder until the user
has confirmed billing and granted explicit go-ahead. Local contract +
fake-store verification passed; live write remains separate.

## Outstanding Polish (Non-Blocking)

- Per-section SRC inline rendering in `SadPreviewPanel.tsx` (data is present in
  the response; UI just does not render section-level refs inline).

## Archive Notes

Superseded TC-021 cascade (R through Y) was consolidated into
`docs/superpowers/archive/testing/test_cases/consolidated-test-cases.md`.

Older Phase 4 plans and specs already live under
`docs/superpowers/archive/plans/consolidated-plans.md` and
`docs/superpowers/archive/specs/consolidated-specs.md`.
