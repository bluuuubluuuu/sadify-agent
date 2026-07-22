# TC-031 Readiness Confidence Semantics

Date Created: 2026-06-02
Last Updated: 2026-06-02
Status: Passed (behavior verified by code inspection + automated unit/integration tests A/B/C/C2/D/D2/E); Test-F logging proposed (held)

## Traceability Sources

- `docs/superpowers/development/02_agent_behavior_contract.md`
- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `docs/superpowers/testing/test_cases/TC-028-evidence-based-readiness.md`
- Decision log D-089 (AI-judged, quote-validated per-slot evidence), D-092 (UI redesign), D-093 (confidence semantics)

## Purpose

Prove that the readiness **score** (completeness %) and the readiness
**confidence** badge are computed from independent inputs, so a draft that
shows 90%+ / "Ready for draft" can correctly still show **Low** confidence.
This documents the mechanism as **expected behavior, not a bug**, and pins the
exact code path so future smokes are not re-diagnosed from scratch.

## Inputs

- Manual browser smoke: project "Catering event", source
  `catering-corporate-events-context.txt`, Q&A answered through readiness.
- Backend turn log (below).
- Read-only code inspection of the score/confidence path.

## Preconditions

- Backend running with live Gemini Q&A (`SADIFY_PERSISTENCE` and Drive mode
  irrelevant to this test).
- Frontend on the new shell with the A+B readiness-binding fix applied
  (`WorkspaceV2.tsx` reads `questionnaire.draft_readiness.confidence`).

## Mechanism Under Test (file:line, worktree `mvp-monorepo-scaffold`)

Score and label — `services/api/src/sadify_api/services/questionnaire_plan.py`:
- `recalculate_readiness` (324-359): fixed denominator over all required slots;
  `score = round(100 * Σ _slot_weight / n_required)`.
- `_slot_weight` (362-374): `not_applicable → 1.0`, `strong → 1.0`,
  `partial → 0.5`, `none`/`confirm_later → 0.0`.
- `_readiness_label` (488-494): `≥90 "Ready for draft"`, `≥70 "Mostly ready"`,
  `≥40 "In progress"`.

Confidence — `services/api/src/sadify_api/services/slot_evidence.py::derive_confidence`
(120-141):
- denominator = applicable verdicts only (`not_applicable` EXCLUDED), 131-132.
- `total == 0 → Low` (133-134).
- `downgrade_count ≥ 2` OR `none > total/2 → Low` (137-138).
- `strong/total ≥ 0.7` AND `downgrade_count == 0 → High` (139-140).
- else `Medium` (141).

Wiring — `services/api/src/sadify_api/routes/analysis.py`:
- merged monotonic carry-forward verdicts (312-314; `merge_evidence`
  `slot_evidence.py:63-117`).
- `derive_confidence(verdicts=MERGED, downgrade_count=len(evidence_diagnostics
  THIS turn))` (331-333).
- `draft_readiness = {label, score (plan), confidence: derived}` (354-358).
- `questionnaire.diagnostics` carries `"AI confidence: …"`,
  `"Derived confidence: …"`, and per-slot downgrade lines (359-364, 391).

Frontend — `apps/web/src/components/WorkspaceV2.tsx` (179-182): binds
`questionnaire?.draft_readiness.{label,confidence} ?? readiness.{…}`; raw Gemini
confidence used only when `questionnaire` is null. Badge rendered in
`apps/web/src/components/chat/ReadinessPane.tsx:45`.

SAD preview confidence is a SEPARATE Layer-2 concept —
`services/api/src/sadify_api/services/sad_preview.py::_draft_ready_it_readiness`
(376-398): `confidence = "High" if draft-ready else analysis.readiness.confidence`.
Not the Q&A derived confidence.

## Expected Output

- Score is monotonic across turns; confidence is recomputed each turn from the
  current verdict mix + this-turn `downgrade_count`.
- A 90%+ score with Low confidence is valid and reachable ONLY via
  `downgrade_count ≥ 2` or `none > half` of applicable verdicts.
- A partial-heavy plan at 90%+ yields **Medium**, not Low.
- Frontend confidence comes from `draft_readiness.confidence` (derived), never
  raw Gemini confidence when `questionnaire` exists.

## Real Output

Backend turn log (catering smoke):

```text
AN-000001 score=68 errors=-
AN-000002 score=84 errors=-
AN-000003 score=87 errors=-           # High at 87 (strong-ratio high, score held by partials)
AN-000004 score=89 errors=repair=False:QuestionnaireDriftError
AN-000005 score=92 errors=-
AN-000006 score=95 errors=repair=False:QuestionnaireDriftError
AN-000007 score=97 errors=-
AN-000008 score=100 source=fallback errors=repair=False+repair=True:QuestionnaireDriftError
```

Observed badge sequence: 68 Low, 84 Low, 87 High, 89 Low, 92 Low, 95 Low,
97 High, 100 High.

Diagnosis (PASS): confidence tracks per-turn quote validity, not completeness.
The oscillation is driven by a coupling quirk — `downgrade_count` is computed
from THIS turn's raw Gemini quote validation (`analysis.py:304,417`), while the
`strong/none` ratio is computed from the MERGED carry-forward verdicts
(`analysis.py:312-314`). A turn that re-cites bad quotes for already-strong
slots keeps the score (monotonic merge) but spikes `downgrade_count` → Low for
that turn only. Fallback turns produce empty new verdicts/diagnostics →
`downgrade_count=0` → tend High (explains AN-000008 = 100 High).

## Differences / Issues

- Not a defect: score and confidence are intentionally independent.
- UX wording issue: the badge "Low confidence" next to "Ready for draft" reads
  as contradictory. Recommend reframing confidence as *evidence-grounding
  quality* (see D-093), not blocking.
- Observability gap: `_log_turn` (`analysis.py:172-213`) logs
  `id/source/prior/active/score/locked/errors` only — no `confidence` or
  `downgrade_count`; its `errors` field is drift-repair retries, NOT quote
  downgrades. The values exist in the API response (`questionnaire.diagnostics`)
  but not in the tail log. See Test F.

## Test Cases

| # | Test | Construction | Expected | State |
| --- | --- | --- | --- | --- |
| A | downgrade overrides high strong-ratio | ≥70% applicable `strong`, `derive_confidence(v, downgrade_count=2)` | `"Low"` | EXISTS — `tests/api/test_slot_evidence.py:128-130` (passed) |
| B | clean strong majority | ≥70% applicable `strong`, `downgrade_count=0` | `"High"` | EXISTS — `test_slot_evidence.py:117-119` (passed) |
| C | none-heavy | `none > total/2` | `"Low"` | EXISTS — `test_slot_evidence.py:122-125` (passed) |
| C2 | partial-heavy ≠ Low | mostly `partial`, 0 strong, `downgrade=0`, `none ≤ half` | `"Medium"` | DONE — `test_slot_evidence.py::test_derive_confidence_medium_when_partial_heavy_no_downgrades` (passed) |
| D | Ready + Low coexist (integration) | 19 strong canonical verdicts, 2 citing quotes absent from material → route `/analysis/requirement` | `score ≥ 90` (95), `label == "Ready for draft"`, `confidence == "Low"`, ≥2 "downgraded" diagnostics | DONE — `test_evidence_readiness_scenarios.py::test_scenario_ready_for_draft_can_coexist_with_low_confidence` (passed) |
| D2 | oscillation | same verdict mix (constant score basis), `downgrade_count` 2 then 0 | `Low` then `High` — confidence volatility independent of monotonic score | DONE — `test_slot_evidence.py::test_derive_confidence_oscillates_with_downgrade_count_on_same_verdicts` (passed) |
| E | frontend binding | `WorkspaceV2.tsx` static assert: passes `questionnaire?.draft_readiness.confidence`, raw only when questionnaire null | assertion holds | DONE — `tests/test_mvp_workspace_shell.py::test_readiness_pane_binds_stable_questionnaire_state_not_raw` |
| F | log diagnostics (proposal) | extend `_log_turn` with `conf=%s downgrades=%d` threaded from `_with_questionnaire_state` | one-line, non-invasive, no schema/UI change | PROPOSED |

## Evidence

- Code inspection: `slot_evidence.py:120-141`, `questionnaire_plan.py:324-374,488-494`,
  `analysis.py:172-213,304-364`, `sad_preview.py:376-398`,
  `WorkspaceV2.tsx:179-182`, `ReadinessPane.tsx:45`.
- Existing automated coverage: `tests/api/test_slot_evidence.py:117-130`.
- Added automated: C2/D2 (`test_slot_evidence.py`), D (`test_evidence_readiness_scenarios.py`),
  commit 78e7183; full suite 460 passed, 4 skipped.
- Backend turn log (above) + observed badge sequence.
- Manual browser smoke 2026-06-02 (catering, 7-turn live run): score
  monotonic 71→76→92→92→95→97→100; `locked=` ratchet strictly monotonic
  (no coverage regression); badge tracked "Low evidence" → "High evidence"
  at 100%. The real fallback turn AN-000007 (double QuestionnaireDriftError)
  rendered 100%/"Ready for draft"/"High evidence", confirming Low confidence
  at high % is grounding-driven and the fallback raw-binding is masked.

## Decision

PASS — current behavior is verified and intentional. Score = completeness,
confidence = evidence-grounding quality; they are independent and a 90%+ draft
can legitimately show Low confidence.

Recommended follow-ups (separate, not blocking):
1. Keep the mechanism.
2. UI wording: reframe the confidence badge as evidence quality (pairs with the
   queued D-wording pass).
3. Implement Test F logging for smoke observability. (HELD — backend log line
   needs explicit approval before adding.)
4. ~~Add automated C2/D/D2~~ — DONE 2026-06-02; full suite 460 passed, 4 skipped.
5. Defer any change to the this-turn-vs-merged `downgrade_count` coupling — that
   is a benchmarking decision, not a smoke fix.
