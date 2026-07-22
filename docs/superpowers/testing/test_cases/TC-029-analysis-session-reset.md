# TC-029 Analysis-State Reset (Deterministic Per-Session)

Date Created: 2026-05-29
Last Updated: 2026-05-29
Status: Passed (deterministic per-session reset verified live)

## Purpose

Stop analysis carry-forward from leaking across unrelated sources or
projects. Previously the backend inferred which prior analysis to carry
forward from by matching the base requirement text (the user's typed
business request). A generic word like "Analyze" collided across
completely different sources, so a new source inherited a prior saturated
analysis and produced a contaminated SAD (e.g. a catering source produced
a pet-grooming SAD).

## Root Cause

`RequirementAnalysisRepository.latest_for_request` keyed the session on
`_base_requirement_text(requirement_text)` — the text before the first
`"Previous question:"` marker — matched case-sensitively. For the
signed-in flow (no `guest_draft_id`), the session key was just the typed
business request. Two analyses with the same typed text collided; once an
analysis saturated to 100% with all canonical slots locked, later
analyses inherited the locked state via carry-forward and never freshly
analysed the new source. Capitalisation/whitespace differences made the
collision intermittent and unpredictable.

This unified three observed symptoms into one defect:
1. "I'm not sure" accepted as a final answer.
2. 100% readiness with no questions on a complete source.
3. Cross-source content bleed (catering source -> pet-grooming SAD).

## Fix

Explicit client-owned `analysis_session_id`:

- Frontend (`WorkspaceShell`) generates a stable `analysisSessionId`
  (`crypto.randomUUID()`) at mount and regenerates it ONLY when
  `sourceReferences.join(",")` or `driveRepo?.active_project_id` changes
  — the two real reset boundaries (new/changed source upload, project
  switch).
- `AnalysisPanel` forwards the id on both `startAnalysis` and
  `continueWithAnswer`.
- `api.ts` sends `analysis_session_id` in the analyze request.
- Backend `RequirementAnalysisRequest` / `RequirementAnalysisRecord`
  gain `analysis_session_id` (additive). `save_analysis` stores it.
- `latest_for_request` priority becomes: (1) explicit
  `analysis_session_id` via new `latest_for_session`, (2) existing
  `guest_draft_id`, (3) existing base-text fallback. When a session id
  is present but no record matches, it returns `None` (fresh analysis)
  and does NOT fall through to text matching — so a new session can
  never match an old analysis by typed text.

Within one analysis (answering questions), neither sources nor active
project change, so the session id stays stable and slot-evidence
carry-forward (Cycle 2A/2B) still works. A new source upload or project
switch regenerates the id, guaranteeing a fresh analysis.

## Scope

In scope:
- `analysis_session_id` on request + record schemas (additive only).
- `latest_for_session` + session-first priority in `latest_for_request`.
- Pass-through in `routes/analysis.py` (both success and fallback save).
- Frontend session-id ownership, regeneration triggers, and forwarding.

Out of scope:
- Explicit "Start over" reset button (auto-reset on source/project
  change covers the failure).
- Any change to questionnaire / slot-evidence / carry-forward logic
  (only WHICH prior record is selected changed).
- Firestore persistence (separate slice TC-030).

## Preconditions

- TC-026E passed (HEAD 8f1a302).

## Steps (manual smoke)

1. Restart backend fresh (clears in-memory state). Connect Drive.
2. Upload pet-grooming PDF, type "Analyze", run to 100%
   (saturated grooming baseline).
3. Upload catering file (changes sourceReferences -> frontend
   regenerates session id).
4. Type "Analyze" again, Start analysis.

## Expected Output

- New analysis starts low (not 100%) and asks a question.
- Fresh analysis chain (`prior=None` on first turn of the new session).
- Generated SAD is about the new source (catering), not the prior one.
- All existing tests stay green (requests without `analysis_session_id`
  hit the unchanged legacy path).

## Real Output

Implementation commit: `670b5b9 fix(analysis): deterministic per-session
reset via explicit analysis_session_id`.

Automated verification on 2026-05-29:
- Full Python regression with `SADIFY_DRIVE_MODE=local`: **457 passed**
  (was 446; +11: 7 repository/session-key tests, 1 route test, 3
  frontend static tests).
- TypeScript `npx -y tsc --noEmit`: clean.
- Zero existing tests modified — backward compatible.

Live manual smoke on 2026-05-29:

```text
Grooming baseline: pet-grooming PDF, typed "Analyze" -> 100%, grooming SAD.
Upload catering file (SRC-000004) -> session id regenerated.
Typed "Analyze" (same word) -> Start analysis.

Result:
  New chain AN-000011, readiness 71%, asked "What is the primary
  business goal..." (fresh session, NOT inherited grooming state).
  Q&A climbed AN-000011 -> AN-000021 to 100%.
  Generated SP-000002: a genuine CATERING SAD (sales/kitchen/delivery
  staff, event orders, menu packages, guest count, dietary restrictions,
  weekly owner summary). Zero pet-grooming bleed.
```

## Differences / Issues

- Behavior note (intentional, not a defect): uploading a new source
  mid-analysis regenerates the session id and starts a fresh analysis on
  the next turn. Adding a source mid-flow is a material change, so this
  is correct.
- The regenerate effect fires once on mount (deps initialise), replacing
  the initial UUID with a fresh one. Harmless.

## Evidence

- Commit `670b5b9`; 457 local-mode tests; TS clean.
- Live smoke: catering source produced a catering SAD with fresh Q&A,
  proving no carry-forward from the prior grooming analysis.
- Backward compatibility: 446 prior tests unchanged and still green.

## Decision

Passed. Analysis carry-forward is now keyed by an explicit, frontend-
owned session id that resets deterministically on new-source-upload and
project-switch. Cross-source/project contamination is eliminated; the
"100% with no questions" and "I'm not sure accepted" symptoms no longer
arise from leaked saturated state. The fix is additive and backward
compatible. Next: TC-030 Firestore persistence (so projects/saves/wiki
state survive Cloud Run cold starts and multiple instances), then
TC-027 deploy.
