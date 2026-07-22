# SADify Q&A Workflow Refinement

Date: 2026-05-14  
Last updated: 2026-05-23  
Status: Active behavior source; TC-028 evidence-based readiness is the current readiness checkpoint

## Purpose

This document is the active source of truth for the MVP Q&A workflow.

It replaces the earlier mixed model where Gemini could rebuild categories every turn, fallback used a broad top-level menu, and the UI exposed too many competing progress signals.

The goal is a guided analyst interview:

```text
stable questionnaire plan
-> one active category
-> one clear question at a time
-> slot-based completion
-> stable readiness and traceable answers
```

## Active Execution Linkage

```text
Behavior note:
  this file

Stable-plan design spec:
  docs/superpowers/specs/2026-05-15-sadify-stable-questionnaire-plan-design.md

Stable-plan implementation plan:
  docs/superpowers/plans/2026-05-15-stable-questionnaire-plan-refactor.md

Stable-plan acceptance test:
  docs/superpowers/testing/test_cases/TC-021S-stable-questionnaire-plan-refactor.md

Prior ready-state design spec:
  docs/superpowers/specs/2026-05-18-qna-ready-state-preview-handoff-design.md

Prior ready-state implementation plan:
  docs/superpowers/plans/2026-05-18-qna-ready-state-preview-handoff.md

Prior ready-state acceptance test:
  docs/superpowers/testing/test_cases/TC-021T-qna-ready-state-preview-handoff.md

Prior Q&A/SAD synthesis route-safety design spec:
  docs/superpowers/specs/2026-05-18-qna-sad-synthesis-quality-design.md

Prior Q&A/SAD synthesis route-safety implementation plan:
  docs/superpowers/plans/2026-05-19-qna-sad-synthesis-quality.md

Prior Q&A/SAD synthesis route-safety acceptance test:
  docs/superpowers/testing/test_cases/TC-021U-qna-sad-synthesis-quality.md

Prior fallback composition plan:
  docs/superpowers/plans/2026-05-19-sad-fallback-composition-quality-upgrade.md

Prior fallback composition acceptance test:
  docs/superpowers/testing/test_cases/TC-021V-sad-fallback-composition-quality.md

Prior user-facing SAD draft quality plan:
  docs/superpowers/plans/2026-05-19-user-facing-sad-draft-quality.md

Prior user-facing SAD draft quality acceptance test:
  docs/superpowers/testing/test_cases/TC-021W-user-facing-sad-draft-quality.md

Prior evidence-first Q&A and valid preview coherence design spec:
  docs/superpowers/specs/2026-05-20-evidence-first-qna-depth-valid-preview-coherence-design.md

Prior evidence-first Q&A and valid preview coherence implementation plan:
  docs/superpowers/plans/2026-05-20-evidence-first-qna-depth-valid-preview-coherence.md

Prior evidence-first Q&A and valid preview coherence acceptance test:
  docs/superpowers/testing/test_cases/TC-021X-evidence-first-qna-depth-valid-preview-coherence.md

Prior domain-aware Q&A and SAD quality hardening design spec:
  docs/superpowers/specs/2026-05-21-domain-aware-qna-sad-quality-hardening-design.md

Prior domain-aware Q&A and SAD quality hardening implementation plan:
  docs/superpowers/plans/2026-05-21-domain-aware-qna-sad-quality-hardening.md

Prior domain-aware Q&A and SAD quality hardening acceptance test:
  docs/superpowers/testing/test_cases/TC-021Y-domain-aware-qna-sad-quality-hardening.md

Current evidence-based readiness design spec:
  docs/superpowers/specs/2026-05-22-evidence-based-readiness-design.md

Current evidence-based readiness implementation plan:
  docs/superpowers/plans/2026-05-22-evidence-based-readiness.md

Current evidence-based readiness acceptance test:
  docs/superpowers/testing/test_cases/TC-028-evidence-based-readiness.md
```

Phase position:

```text
Phase 3 - Q&A workflow stabilization:
  TC-021S and TC-021T passed after TC-021R was superseded.

Phase 4 - SAD preview and SAD quality stabilization:
  TC-021U passed route safety.
  TC-021V partially passed clean request boundaries and transport-log hiding.
  TC-021W automated checks passed, but the 2026-05-20 workshop manual smoke failed progression.
  TC-021X local checks passed but manual workshop/tuition smoke still failed
  broader progression.
  TC-021Y local hardening passed, then TC-028 replaced keyword/phrase readiness
  patching with quote-validated per-slot evidence. TC-028 full verification and
  manual smoke now block MVP-10 / TC-025.
```

Current checkpoint status:

```text
MVP-09.2 / TC-021S core continuity behavior is complete.

Implemented so far:
- fixed core questionnaire categories
- slot-aware readiness model
- active-category UI
- neutral pre-analysis UI
- collapsed already-understood/completed areas
- explicit multi-select UI
- planner-owned first-turn lock from the first unresolved slot
- deterministic initial-request seeding for clearly stated facts
- slot markers preserved in answer-history round-trips
- backend semantic guards for slot intent drift
- same-slot local fallback questions tied to canonical slot contracts
- slot-aware repeated-question replacement in the normal next-question path
- same-slot duplicate answers no longer advance the questionnaire early
- model-reported `complete` categories do not override request/answer evidence
- seeded clinic continuity now has end-to-end regression coverage

Manual reruns on 2026-05-18 showed:
- the clinic flow can now progress through the locked questionnaire path to `100%`
- the ready-state handoff renders correctly
- live `/sad/preview` can return `200`
- the next unsolved problem is now synthesis quality rather than handoff transport

Manual rerun on 2026-05-19 showed:
- TC-021U safe fallback now avoids the previous `/sad/preview` `502`
- the fallback SAD still needs composition tightening because it can display
  transport history and raw Q&A answers instead of a clean SAD draft

Automated TC-021V verification and the manual smoke on 2026-05-19 proved that
clean request boundaries and Q&A transport-history hiding work. TC-021W
automated checks then improved fallback SAD draft presentation. The 2026-05-20
workshop manual smoke still failed progression because Q&A remained too broad,
preset choices were too optimistic, and the valid SAD preview still showed
contradictory low confidence with visible IT readiness. TC-021X local checks
improved the workshop path, but the 2026-05-21 tuition smoke proved the approach
is still too narrow: domain-aware question selection, fact-bearing choices,
clean source refs, stale-preview reset, and evidence-based SAD composition were
split into cycles. The current Cycle 1 blocker is TC-028 evidence-based
readiness: richer context should score higher only when it explicitly covers
more required SAD areas, sparse context should stay lower, and backend readiness
must not depend on brittle keyword tables.
```

Current acceptance gap:

```text
TC-028 evidence-based readiness:
the interview must use model-returned per-slot evidence verdicts, validate each
partial/strong quote against the actual request, uploaded source context, and
saved answers, downgrade ungrounded verdicts, and aggregate readiness over
applicable required slots. SAD synthesis quality is the next cycle after this
readiness checkpoint is verified.
```

## Traceability Sources

- `docs/superpowers/specs/2026-05-11-sadify-prototype-to-mvp-design.md`
- `docs/superpowers/development/01_product_scope.md`
- `docs/superpowers/development/02_agent_behavior_contract.md`
- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `docs/superpowers/testing/test_cases/TC-021R-mvp-category-first-qna-refinement.md`
- `docs/superpowers/testing/test_cases/TC-021S-stable-questionnaire-plan-refactor.md`
- Manual testing feedback on 2026-05-15 and 2026-05-18
- Archived earlier implementation wording remains available under `docs/superpowers/archive/`

## Problem Statement

Manual testing on 2026-05-15 found that the current Q&A implementation is still not trustworthy enough for MVP:

- the first screen shows fake readiness/question state before any analysis exists
- category labels drift between turns
- categories appear, disappear, split, or merge
- the active category can be abandoned before it is complete
- `Question 1 of 2` is misleading because completion is count-based, not requirement-based
- source labels expose internal conversation plumbing such as `Previous Answer`
- multi-select questions are not visually obvious
- overall readiness can look arbitrary because the category set itself changes
- the implementation can still accept semantically wrong questions when Gemini reports the requested category/slot IDs
- repeated questions previously reappeared because one legacy count-based helper could
  override the stable slot plan after multiple saved answers in the same category

## Core Decisions

### 1. Stable Questionnaire Plan

The backend creates one questionnaire plan from the first valid analysis of a draft/project.

That plan owns:

- canonical category IDs
- stable user-facing labels
- frozen visible order
- required slots per category
- already-understood categories
- suggested extra categories
- active category
- slot status
- answer history

The plan is not rebuilt from scratch on every Gemini turn.

### 2. Fixed Core Categories Plus Reviewed Extras

The MVP uses these fixed core categories:

```text
1. Goal and scope
2. Users and roles
3. Workflow steps
4. Data and records
5. Business rules and approvals
6. Exceptions and edge cases
7. Reports and summaries
8. Access and permissions
9. Integrations
10. Non-functional needs
```

Gemini may suggest project-specific extra categories, but:

- extras are not auto-added into the live questionnaire
- late extras appear under `Suggested additions`
- the backend validates whether the suggestion is truly distinct from existing core categories
- the user-visible main questionnaire remains stable

### 3. Category Visibility

Normal Q&A view shows only unresolved visible categories.

Categories already clear from the first request or uploaded files are hidden from the main flow and appear under a collapsed `Already understood` section.

Completed categories move to a collapsed `Completed areas` section after they are finished.

### 4. Frozen Order

Once the questionnaire plan is created, visible category order is frozen for the life of the current project/draft plan.

Gemini may suggest the next best phrasing inside the active category, but it does not reorder the visible questionnaire map.

### 5. Slot-Based Completion

A category is complete when its required slots are covered, not after an arbitrary number of questions.

Examples:

```text
Users and roles
- primary users identified
- core responsibilities clarified
- access boundary or exception clarified when relevant

Workflow steps
- normal flow captured
- handoffs/status changes captured
- important exception path captured

Data and records
- main records identified
- critical fields identified
- reporting linkage or retention clarified when relevant
```

Some categories may need one question. Others may need several. If the initial request already covers a slot, SADify should not ask it again.

### 6. Active Category Lock

SADify stays inside the active category until:

- all required slots are covered, or
- unresolved slots are explicitly marked `Confirm later`

If Gemini proposes a question from a different category before that:

1. backend rejects the drift
2. Gemini gets one repair retry constrained to the same active category and target slot
3. if still invalid, SADify asks a safe local fallback question for that same slot

The system must not switch categories early just because Gemini changed its mind.

### 7. Prompt Plus Backend Enforcement

Prompt-only guidance is insufficient.

The Q&A contract must use:

- strict system instructions
- structured schema fields for `active_category_id`, `target_slot_id`, and `proposed_extra_categories`
- backend validation for:
  - canonical category IDs
  - canonical labels
  - slot ownership
  - question intent belonging to the target slot
  - choice family belonging to the target slot
  - duplicate/redundant questions
  - unapproved extra categories
  - active-category drift

Gemini helps analyze and phrase questions. The backend owns workflow truth.

### 8. Readiness

Overall readiness is backend-calculated from stable required slots and
quote-validated evidence. It is not a Gemini-decided score and it is not a
keyword or phrase table.

The Gemini analysis response may return a `slot_evidence` verdict for each
canonical required slot:

```text
category_id
slot_id
applicability: applicable | not_applicable
strength: none | partial | strong
evidence_quote
rationale
```

The backend validates every `partial` or `strong` verdict by checking that its
`evidence_quote` appears in the actual business material:

- typed business request
- uploaded source context
- saved Q&A answers

If the quote is empty or not found, the backend downgrades the verdict one
level. `none` and `not_applicable` verdicts do not need quotes.

Readiness is then aggregated deterministically over applicable required slots:

- `strong` / covered contributes full weight
- `partial` contributes half weight
- `none` remains open
- `not_applicable` slots are excluded from the denominator

Confidence is also derived by the backend from the validated verdict mix and
downgrade count:

- high confidence requires mostly strong applicable evidence and no downgrades
- low confidence applies when many applicable slots have no evidence or several
  verdicts were downgraded
- everything else is medium confidence

A draft-ready score alone is not enough for SAD preview if an applicable
required slot remains open. The preview gate also requires questionnaire
categories to be ready or explicitly marked for later confirmation.

Normal Q&A shows one percentage only:

```text
Overall readiness
```

Question areas use word statuses:

```text
Needs answer
In progress
Ready
Confirm later
```

If an earlier answer changes, SADify reopens only the affected slot/category and
recomputes readiness from validated evidence. Readiness may then decrease for a
real reason.

### 9. Multi-Select

Multi-select questions must be unmistakable:

- checkbox-style choices
- helper text: `Select all that apply.`
- clicking again deselects
- amendment text applies to the whole selected set
- `Other / not listed` requires details

### 10. Source Labels

Normal `Source refs` show business sources only:

- uploaded files
- pasted source labels
- business request

Conversation history such as previous answers belongs in answer history or diagnostics, not in business source refs.

## User Flow

```text
Before analysis
  -> show neutral "No analysis yet"
  -> no fake readiness
  -> no fake categories
  -> no fake current question

First analysis
  -> create stable questionnaire plan
  -> classify already-understood categories
  -> choose first unresolved category
  -> choose first required open slot
  -> ask one easy question for that slot

Answer submitted
  -> save answer to slot/category
  -> recalculate slot coverage
  -> if active category still has open required slots, ask next question there
  -> else move category to Ready or Confirm later
  -> then advance to next unresolved category in frozen order

Late discovery
  -> if AI finds a distinct new area, place it in Suggested additions
  -> do not mutate the live map automatically

Required path complete
  -> show Ready to draft
  -> allow SAD preview immediately
  -> hide the unresolved category grid
  -> keep completed areas expandable
  -> keep optional refinements separate and non-blocking
```

## Normal UI Arrangement

```text
Overall readiness
In progress - 55%

Question areas
Users and roles - In progress
Workflow steps - Needs answer
Data and records - Needs answer

Already understood
[collapsed]

Completed areas
[collapsed]

Active category
Users and roles
Working on: access boundary

Saved answers
- Which staff use the system? Reception, doctor, pharmacy, cashier

Current question
What should happen when staff need access outside their normal role?

[ ] Require manager approval
[ ] Allow temporary access with audit log
[ ] Block access outside the role
[ ] Other / not listed

Select all that apply.
```

Debug information stays collapsed under `Tracking / diagnostics`.

## Completion Handoff

When required readiness reaches `100%`, the normal Q&A box becomes a draft
handoff rather than another ordinary question screen.

Visible by default:

```text
Ready to draft
Overall readiness
Generate SAD preview
```

Collapsed by default:

```text
Optional refinements
Completed areas
Current understanding
Answered so far
Tracking / diagnostics
```

The standard question-area grid should be hidden at `100%`. Optional refinements
may still be offered, but they must be visibly non-blocking and must not make the
required path look unfinished.

Saved answers and the understanding summary are still available to the user, but
they should not compete with the active task in the normal view.

## Status Rules

| Status | Meaning |
| --- | --- |
| Needs answer | At least one required slot is uncovered. |
| In progress | At least one useful slot is covered and at least one required slot remains open. |
| Ready | Required slots are covered enough for MVP SAD drafting. |
| Confirm later | A required slot remains unresolved because the user explicitly deferred it. |

## Prompt Contract

The Gemini Q&A prompt must receive:

- frozen plan summary
- active category ID and label
- active slot ID and plain-language slot goal
- completed slot facts
- allowed visible category IDs
- forbidden categories for the current turn
- prior questions in the active category
- explicit instruction not to rename categories or add visible categories

The model response must return:

- next question text
- why it matters
- choices
- selection mode
- target category ID
- target slot ID
- optional proposed extra categories
- assumptions
- business source references

The backend rejects responses that do not match the active category and target slot.
It must also reject responses whose wording or answer choices belong to another
slot even if Gemini reports the requested IDs correctly.

## SAD Preview Handoff Rule

The SAD preview context must include saved questionnaire answers in addition to
the business request, current understanding, assumptions, and business source
references. Those answers are user-confirmed requirement facts and cannot be
silently dropped when generating the preview.

The business request passed into SAD preview must stay clean. Q&A transport
history such as `Previous question`, `Previous answer`, and `Previous readiness`
may be used internally for model continuity, but it must not be stored or
rendered as the business request.

## SAD Synthesis Quality Rule

The SAD generator must not treat fallback diagnostics or model-side temporary
readiness as business truth.

Before generating a SAD preview, SADify should prepare one merged confirmed-facts
view from:

1. original business request
2. uploaded source facts
3. user-confirmed questionnaire answers
4. explicit unresolved items

The generated SAD should:

- preserve facts already stated in the original request
- incorporate later confirmed answers as refinements or overrides
- keep open questions limited to genuinely unresolved items
- avoid generic fallback language that is not grounded in the project
- keep internal retry/fallback diagnostics out of business-facing assumptions
- stay consistent with backend-owned readiness

If the model preview fails schema validation and the local fallback is used, the
fallback must still compose domain sections from confirmed facts. It must not
show raw answer logs as the final SAD body.

## Data Model Direction

Questionnaire plan:

```json
{
  "plan_id": "QPLAN-001",
  "active_category_id": "users_roles",
  "categories": [
    {
      "id": "users_roles",
      "label": "Users and roles",
      "display_order": 2,
      "visibility": "main",
      "status": "in_progress",
      "slots": [
        {
          "id": "primary_users",
          "label": "Primary users identified",
          "required": true,
          "status": "covered"
        },
        {
          "id": "access_boundary",
          "label": "Access boundary clarified",
          "required": true,
          "status": "open"
        }
      ]
    }
  ],
  "suggested_additions": [],
  "overall_readiness": {
    "label": "In progress",
    "score": 55
  }
}
```

Question:

```json
{
  "question_id": "Q-004",
  "category_id": "users_roles",
  "slot_id": "access_boundary",
  "selection_mode": "multiple",
  "text": "What should happen when staff need access outside their normal role?",
  "choices": []
}
```

Answer:

```json
{
  "answer_id": "ANS-004",
  "category_id": "users_roles",
  "slot_id": "access_boundary",
  "selected_choice_ids": ["manager_approval"],
  "amendment_text": "",
  "is_uncertain": false,
  "source": "user"
}
```

## Acceptance Criteria

The refactor is acceptable only when:

1. Before analysis, no fake Q&A/readiness/category data is shown.
2. The first real analysis creates one stable plan.
3. Category labels and order remain stable across all later turns.
4. Already-understood categories are hidden from the main flow and available under `Already understood`.
5. Completed categories move to `Completed areas`.
6. Active category stays locked until required slots are covered or deferred.
7. `Question n of m` is replaced by truthful slot wording unless the exact remaining count is truly known.
8. Gemini category drift is rejected and repaired before fallback is used.
9. New project-specific categories are suggested, not auto-inserted.
10. Overall readiness is backend-calculated from quote-validated slot evidence.
11. Multi-select questions visibly use checkboxes and `Select all that apply.`
12. Normal `Source refs` show business sources only.
13. Repeated or semantically duplicate questions are skipped.
14. Editing an earlier answer reopens only the affected slot/category and recomputes readiness.
15. The first active category is chosen from the first unresolved slot in frozen plan order, not from Gemini preference.
16. Initial business request facts seed already-covered slots before the first question is asked.
17. A cross-slot question such as an access-override question labelled as an approval-path question is rejected before it is saved or shown.

## Implementation Priority

The earlier TC-021R work is superseded. TC-021S and TC-021T have passed, and the
current execution is in Phase 4 SAD preview quality stabilization. Continue in
this order:

```text
MVP-09.2 / TC-021S: Stable Questionnaire Plan Refactor - passed
MVP-09.3 / TC-021T: Q&A ready state and SAD preview handoff - passed
MVP-09.4 / TC-021U: Q&A + SAD synthesis route-safety quality - passed
MVP-09.5 / TC-021V: SAD fallback composition quality - partial pass
MVP-09.6 / TC-021W: User-facing SAD draft quality - automated pass, manual progression failed
MVP-09.7 / TC-021X: Evidence-first Q&A depth and valid preview coherence - local pass, manual progression failed
MVP-09.8 / TC-021Y: Domain-aware Q&A and SAD quality hardening - local pass; superseded for readiness by TC-028
TC-028: Evidence-based readiness - implementation tasks complete; full verification/manual smoke pending
Next cycle: SAD synthesis quality - do not start until TC-028 is verified
MVP-10 / TC-025: Wiki update approval - blocked until TC-028 passes
```
