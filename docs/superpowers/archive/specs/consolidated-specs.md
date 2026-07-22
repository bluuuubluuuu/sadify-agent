# SADify — Archived Specs (Consolidated)

Date consolidated: 2026-05-24
Purpose: historical record of design specs from Phase 3 and Phase 4.
Each section below is one original spec file, preserved verbatim.

## Index

- 2026-05-15-sadify-stable-questionnaire-plan-design
- 2026-05-18-qna-ready-state-preview-handoff-design
- 2026-05-18-qna-sad-synthesis-quality-design
- 2026-05-20-evidence-first-qna-depth-valid-preview-coherence-design
- 2026-05-21-domain-aware-qna-sad-quality-hardening-design
- 2026-05-22-evidence-based-readiness-design

---

## 2026-05-15-sadify-stable-questionnaire-plan-design

# SADify Stable Questionnaire Plan Design

Date: 2026-05-15  
Last updated: 2026-05-18  
Status: Approved design; implementation in progress, manual acceptance not yet passed

## Goal

Replace the current turn-by-turn category reconstruction with one stable questionnaire plan that keeps SADify's Q&A flow coherent, slot-driven, and easy for users to trust.

## Linked Execution Docs

```text
Behavior note:
  docs/superpowers/development/14_qna_workflow_refinement.md

Implementation plan:
  docs/superpowers/plans/2026-05-15-stable-questionnaire-plan-refactor.md

Acceptance test:
  docs/superpowers/testing/test_cases/TC-021S-stable-questionnaire-plan-refactor.md
```

Current implementation note:

```text
Automated implementation is complete through the continuity guard pass:
- first-turn slot locking
- deterministic initial-fact seeding
- semantic slot validation
- same-slot repeat prevention
- planner-owned readiness and advancement

Manual browser acceptance still needs to be rerun after these fixes.
```

## Why This Is Needed

Manual testing on 2026-05-15 showed that the current MVP can:

- show fake Q&A state before analysis
- rename the same category across turns
- reorder or replace categories unexpectedly
- switch away from an unfinished category
- imply a category is `Question 1 of 2` even when it is not truly governed by two required questions
- hide whether multi-select is allowed
- expose internal conversation labels as if they were source documents

These are architecture problems, not surface styling issues.

## Approved Product Decisions

| Area | Decision |
| --- | --- |
| Category model | Fixed core categories plus reviewed AI-proposed extras |
| Initial clear categories | Hidden from the main flow; visible in collapsed `Already understood` |
| Category order | Frozen after the first questionnaire plan is created |
| Completion model | Slot-based; never `n questions answered = done` by itself |
| Active category | Locked until covered or explicitly deferred |
| Model drift | Repair retry inside the locked category, then local fallback inside the same category |
| Late extra categories | Shown under `Suggested additions`, never auto-inserted |
| Multi-select UI | Checkbox style plus `Select all that apply.` |
| Pre-analysis UI | Neutral `No analysis yet`; no fake readiness/current question |
| Saved answer visibility | Active category visible; completed categories collapsed |
| Source refs | Business sources only in normal UI |
| Enforcement | Prompt + schema + backend validation |
| Readiness | Backend-calculated from slot coverage |
| Edited answers | Reopen only affected slot/category and recompute readiness |

## Architecture

### 1. Questionnaire Plan Service

Introduce a focused backend module responsible for:

- canonical categories
- stable labels
- display order
- slot definitions
- visibility buckets
- slot coverage state
- active category advancement
- overall readiness calculation

Gemini responses may enrich the plan, but they do not own it.

### 2. Question Generation Contract

Gemini receives a constrained job:

```text
Given this locked category and open slot,
ask one plain-language question that fills that slot.
```

The request includes:

- active category ID
- active slot ID
- category label
- slot goal
- already-covered facts
- prior active-category questions
- allowed category IDs
- instruction not to rename or reorder categories

### 3. Validation Layer

Backend validation rejects:

- wrong category ID
- wrong slot ID
- label drift
- question intent that does not belong to the locked slot
- answer choices that belong to another slot family
- duplicate/redundant question
- unapproved visible extra category
- invalid source labels

Repair retry happens once. Safe local fallback is the final guardrail.

### 4. Frontend State Model

The normal UI becomes plan-driven:

- neutral empty state before analysis
- unresolved main categories only
- `Already understood`
- `Completed areas`
- optional `Suggested additions`
- active category with current slot goal
- saved answers
- explicit single- or multi-select interaction

## Canonical Core Categories

```text
goal_scope
users_roles
workflow_steps
data_records
rules_approvals
exceptions_edges
reports_summaries
access_permissions
integrations
non_functional
```

## Example Core Slots

### Goal and scope

- business goal
- in-scope outcome
- major out-of-scope boundary when relevant

### Users and roles

- primary users
- responsibilities
- access boundary when relevant

### Workflow steps

- normal sequence
- handoffs/status changes
- completion condition

### Data and records

- main records
- required fields
- reporting linkage when relevant

### Business rules and approvals

- triggering rules
- approval path
- decision authority

### Exceptions and edge cases

- common exception
- required handling
- follow-up/reconciliation

### Reports and summaries

- needed outputs
- audience
- cadence/filters when relevant

### Access and permissions

- access model
- sensitive actions
- override handling

### Integrations

- external systems
- data exchange need

### Non-functional needs

- security/privacy
- audit/history
- volume/performance constraints when relevant

## Readiness Model

Overall readiness is computed from required slots:

```text
covered required slots
/
required relevant slots
```

Then adjusted by:

- unresolved blocking slots
- `Confirm later` slots
- required category visibility

AI confidence is diagnostic only.

## Error Handling

| Failure | Behavior |
| --- | --- |
| Gemini returns wrong category | Repair retry with locked category reminder |
| Gemini repeats an answered question | Reject and retry/fallback |
| Gemini proposes new extra category mid-flow | Store as suggestion only |
| Gemini returns invalid structured output | Repair retry, then safe local fallback |
| User selects `I'm not sure` | Keep slot open or defer as `Confirm later` |
| User edits earlier answer | Reopen affected slot/category and recompute readiness |

## Frontend Behavior

Before analysis:

```text
No analysis yet
```

During analysis:

- only one overall readiness percentage
- unresolved question areas visible
- stable labels/order
- current category and current slot goal visible
- saved answers visible for active category
- completed areas collapsed
- already-understood areas collapsed
- suggested additions collapsed when present
- checkbox UI for multi-select
- diagnostics collapsed

## Testing Strategy

Required regression coverage:

1. no fake pre-analysis Q&A state
2. initial plan created once
3. labels/order stable across turns
4. active category cannot drift
5. slot-based completion
6. late extras become suggestions only
7. multi-select visual affordance
8. source refs filter conversation history
9. repeated question rejection
10. amended answer reopens only affected slot/category
11. readiness recomputes from slot coverage
12. clinic and purchase-request end-to-end flows both remain coherent
13. first-turn question follows first unresolved plan slot, not Gemini preference
14. initial business request facts seed slot coverage before the first question
15. semantically wrong cross-slot questions are rejected even when IDs are valid

## Non-Goals

- durable Firestore persistence of the full plan in this checkpoint
- user approval workflow for suggested additions
- Drive/wiki save behavior
- full domain-specific template library

## Dependency On Later Work

This refactor should complete before wiki update approval and Drive save work continue, because later project memory and document generation need a trustworthy requirement state model.


---

## 2026-05-18-qna-ready-state-preview-handoff-design

# SADify Q&A Ready State And Preview Handoff Design

Date: 2026-05-18  
Status: Approved design; implementation not started

## Goal

Make the Q&A flow feel finished, calm, and understandable when required analysis is complete, while ensuring SAD preview generation receives the saved Q&A answers that led to that readiness state.

## Problem

Manual testing on 2026-05-18 showed that the stable questionnaire flow can now reach `100%`, but the handoff into the next step is still weak:

- required and optional work are not visually separated after the required path is complete
- the normal Q&A panel still exposes too much information at once
- completed work and saved answers compete with the active question
- the SAD preview path does not explicitly include saved questionnaire answers in its generation context
- live SAD preview generation returned invalid structured output and `502 Bad Gateway`

The first four problems are UX/state-design issues. The final problem is a preview-generation reliability issue and must be debugged with evidence before any prompt adjustment is accepted.

## Approved Product Decisions

| Area | Decision |
| --- | --- |
| 100% state | Show a clear `Ready to draft` banner once all required slots are covered or deferred. |
| Optional follow-ups | Keep them in a separate collapsed `Optional refinements` section inside the same Q&A box. They are non-blocking. |
| Question areas at 100% | Hide the normal unresolved-category grid once the required path is complete. |
| Completed work | Keep completed categories available under expandable `Completed areas`. |
| Answer history | Move saved answers into expandable `Answered so far`. |
| Current understanding | Move the analysis summary into expandable `Current understanding`. |
| Diagnostics | Keep `Tracking / diagnostics` collapsed. |
| Preview context | SAD preview input must include saved questionnaire answers, not only the initial request and high-level summary. |
| Preview failure handling | Investigate invalid structured preview output before changing prompts; add tests proving answer context is preserved. |

## User Experience

### During Required Q&A

Normal view should show only:

1. overall readiness
2. active category and active slot
3. current question
4. answer choices
5. answer action row

Secondary information remains available but collapsed:

- `Current understanding`
- `Answered so far`
- `Completed areas`
- `Already understood`
- `Suggested additions`
- `Tracking / diagnostics`

### At 100% Required Readiness

The same Q&A box becomes a completion handoff:

```text
Ready to draft
All required answers are covered.

Generate SAD preview

Optional refinements
  [collapsed]

Completed areas
  [collapsed]

Current understanding
  [collapsed]

Answered so far
  [collapsed]

Tracking / diagnostics
  [collapsed]
```

The user must be able to generate the SAD immediately. Optional questions may continue only as clearly secondary improvement work.

## Frontend State Rules

### Required vs Optional

Required questionnaire completion and optional refinements are distinct states:

- `required_complete = true` when no required slots remain open
- optional refinements do not reduce or inflate required readiness
- optional questions must never look like blockers

### Visibility

| Section | Before 100% | At 100% |
| --- | --- | --- |
| Overall readiness | Visible | Visible |
| Question areas grid | Visible | Hidden |
| Current understanding | Collapsed | Collapsed |
| Answered so far | Collapsed | Collapsed |
| Completed areas | Collapsed | Collapsed |
| Optional refinements | Hidden unless available | Collapsed when available |
| Tracking / diagnostics | Collapsed | Collapsed |

## Preview Handoff Rules

The SAD preview context must include:

- business request
- uploaded source context
- current understanding summary
- required readiness state
- saved questionnaire answers grouped by category and slot
- current assumptions
- business source references

Saved answers are load-bearing because they capture user-confirmed details that may not appear in the original request text.

## Error Handling

| Situation | Expected Behavior |
| --- | --- |
| Required path incomplete | Preview generation remains blocked with clear missing basics. |
| Required path complete | Preview generation enabled immediately. |
| Optional refinements remain | Preview remains allowed; refinements are non-blocking. |
| Structured preview output invalid | Retry once, then show a plain message that preview generation failed; retain existing analysis state. |
| Saved answers absent from preview context | Test failure; this must not regress silently. |

## Testing Strategy

Required regression coverage:

1. active Q&A view hides saved answers and understanding summary behind expanders
2. at `100%`, the Q&A box shows `Ready to draft`
3. at `100%`, unresolved question-area grid is hidden
4. completed areas remain expandable
5. optional refinements render separately and remain non-blocking
6. SAD preview context contains saved questionnaire answers
7. live-preview invalid-output path remains user-readable and leaves Q&A state intact
8. no duplicate percentage labels or competing progress signals are introduced

## Non-Goals

- durable Firestore persistence of optional refinements
- final Google Docs/Drive save path
- redesign of auth, draft, source upload, or Drive repo panels
- changing the canonical required-category model settled by TC-021S

## Linkage

```text
Behavior note:
  docs/superpowers/development/14_qna_workflow_refinement.md

Previous checkpoint:
  docs/superpowers/testing/test_cases/TC-021S-stable-questionnaire-plan-refactor.md

Next implementation plan:
  docs/superpowers/plans/2026-05-18-qna-ready-state-preview-handoff.md

Next acceptance test:
  docs/superpowers/testing/test_cases/TC-021T-qna-ready-state-preview-handoff.md
```


---

## 2026-05-18-qna-sad-synthesis-quality-design

# Q&A And SAD Synthesis Quality Design

Date: 2026-05-18  
Last updated: 2026-05-20  
Status: Historical TC-021U/TC-021V/TC-021W quality spec; active follow-up is TC-021Y

## Purpose

Define the quality checkpoint that follows the successful TC-021T handoff.

The remaining problem is not whether SADify can reach a ready state or call the
preview route. The remaining problem is whether the generated SAD is trustworthy
enough to represent what the user already said and what the user later confirmed.

2026-05-19 clarification:

TC-021U was still a useful quality file. It fixed the first quality layer:
preview context assembly, readiness wording, diagnostic filtering, and fallback
transport safety. The later manual video smoke exposed the next quality layer:
the saved fallback preview no longer fails with `502`, but its content can still
read like a raw diagnostic/Q&A dump instead of a clean Layer 1 SAD draft.

Therefore this spec now covers both:

```text
TC-021U:
  Make the route and synthesis handoff safe.

TC-021V:
  Make the fallback SAD request boundary and transport-history cleanup safe.

TC-021W:
  Make the normal user-facing SAD preview read like a professional Layer 1 SAD
  draft, not a fallback/debug report.

TC-021X:
  Make Q&A evidence-first and apply valid preview coherence rules before MVP-10.
```

## Linked References

```text
Behavior note:
  docs/superpowers/development/14_qna_workflow_refinement.md

Product scope:
  docs/superpowers/development/01_product_scope.md

Agent behavior:
  docs/superpowers/development/02_agent_behavior_contract.md

Data model:
  docs/superpowers/development/03_data_model_and_output_schema.md

Decision log:
  docs/superpowers/development/07_decision_log.md

Prior handoff checkpoint:
  docs/superpowers/testing/test_cases/TC-021T-qna-ready-state-preview-handoff.md

TC-021U plan/test:
  docs/superpowers/plans/2026-05-19-qna-sad-synthesis-quality.md
  docs/superpowers/testing/test_cases/TC-021U-qna-sad-synthesis-quality.md

TC-021V plan/test:
  docs/superpowers/plans/2026-05-19-sad-fallback-composition-quality-upgrade.md
  docs/superpowers/testing/test_cases/TC-021V-sad-fallback-composition-quality.md

TC-021W plan/test:
  docs/superpowers/plans/2026-05-19-user-facing-sad-draft-quality.md
  docs/superpowers/testing/test_cases/TC-021W-user-facing-sad-draft-quality.md

TC-021X plan/test:
  docs/superpowers/plans/2026-05-20-evidence-first-qna-depth-valid-preview-coherence.md
  docs/superpowers/testing/test_cases/TC-021X-evidence-first-qna-depth-valid-preview-coherence.md

TC-021Y active follow-up:
  docs/superpowers/plans/2026-05-21-domain-aware-qna-sad-quality-hardening.md
  docs/superpowers/testing/test_cases/TC-021Y-domain-aware-qna-sad-quality-hardening.md
```

## Current Verified State

The following behavior is already proven:

1. The stable questionnaire plan can reach `Ready for draft - 100%`.
2. The ready-state handoff renders correctly.
3. Saved questionnaire answers are included in the SAD preview context.
4. Live `/sad/preview` can return `HTTP 200`.
5. If Gemini returns invalid structured preview JSON after one repair retry,
   the backend can save a safe local temporary preview instead of returning
   `502`.

The following behavior was originally not acceptable and has been improved:

1. Q&A can report `100%` while the generated SAD preview reports a much lower IT
   readiness score without explaining the layer difference clearly enough.
2. The preview can under-credit facts already present in the original request.
3. Generic fallback wording can bleed into a domain-specific SAD.
4. Internal retry/fallback diagnostics can appear as business-facing assumptions.
5. The ready state can still expose leftover active-category language after the
   required draft-ready path is complete.

The following TC-021V problems are now improved:

1. The fallback SAD uses the accumulated `Previous question / Previous answer /
   Previous readiness` transport log as part of the displayed business request.
2. The fallback `Current Understanding` section can show internal fallback
   behavior instead of business understanding.
3. Optional follow-up questions can remain visible as core open questions even
   after Layer 1 readiness reaches `100%`.

The following behavior was not acceptable after the 2026-05-19 TC-021V manual
video rerun and was addressed by TC-021W automated checks:

1. The preview presents itself as a safe fallback/debug document instead of a
   professional SAD draft.
2. Q&A can show `Ready for draft - 100%` while the preview's main visible status
   says `35% Low confidence`.
3. Overview, Users, and Workflow sections repeat the original request instead
   of synthesizing it.
4. Saved answers are still rendered too shallowly instead of becoming workflow,
   data, rules, access, security, and audit requirements.
5. User amendment wording is preserved literally instead of being normalized into
   formal requirement language.
6. Source refs and diagnostic details are too noisy in the normal preview.

## Design Goal

Make Layer 1 produce a coherent first SAD draft that:

- preserves the original business request
- incorporates confirmed questionnaire answers
- distinguishes unresolved items from already-confirmed facts
- keeps diagnostics out of business-facing content
- stays logically consistent with backend-owned readiness state
- never displays Q&A transport logs as the business request
- renders fallback output as structured SAD content, not raw answer history

Layer 2 IT-readiness refinement remains part of the MVP, but it is a later pass
on the same project after the first coherent draft exists.

## Recommended Approach

Use a backend-owned merged-facts layer plus tighter synthesis rules.

This is preferred over:

1. **Prompt-only tuning**
   - Faster to try, but still leaves the model to reconcile contradictory inputs.
2. **Full knowledge-graph-first redesign**
   - Stronger long term, but too large for the current checkpoint and not needed
     before the first coherent draft.

The selected approach keeps the current questionnaire architecture, adds one
authoritative synthesis input, and narrows what the preview model is allowed to
invent or expose.

## Readiness Model

SADify keeps two layers:

```text
Layer 1: Draft readiness
  Enough confirmed information to generate a coherent first SAD draft.

Layer 2: IT readiness
  Deeper implementation detail for a stronger SAD revision later in the MVP.
```

User-facing rule:

- the Q&A screen shows Layer 1 only during the first draft flow
- the temporary SAD preview may show Layer 2, but it must be clearly labeled as
  a separate later-depth assessment, not as a contradiction of Layer 1

## Proposed Architecture

```text
original request
uploaded source facts
confirmed questionnaire answers
explicit unresolved slots
        |
        v
confirmed facts builder
        |
        v
merged synthesis context
        |
        v
SAD preview generation
```

### 1. Confirmed Facts Builder

Create a backend synthesis object that separates:

- `confirmed_facts`
- `confirmed_answers`
- `unresolved_items`
- `assumptions_for_user`
- `diagnostics_internal`

Rules:

- original request facts are first-class evidence
- original request facts must be extracted from the clean base request, not from
  appended Q&A transport history
- later user-confirmed answers refine or override prior ambiguity
- fallback diagnostics never enter `assumptions_for_user`
- unresolved items must be explicit rather than inferred from stale model
  categories
- answer amendments are first-class confirmed facts and must be interpreted into
  the relevant SAD section

### 1A. Clean Request Boundary

The frontend and backend currently use one overloaded string for both:

- the user's business request
- the transport history sent back to the model as `Previous question`,
  `Previous answer`, and `Previous readiness`

That is acceptable for a quick model prompt, but not acceptable for SAD output.

The SAD preview path must receive or derive:

```text
clean_business_request = text before first "Previous question:"
confirmed_answers = analysis.questionnaire.answers
transport_history = internal diagnostic/model context only
```

The clean request is the only value that may appear in the SAD section labelled
as the business request.

### 2. Preview Context Builder

The preview prompt should receive the merged synthesis object as the main truth,
instead of a loose mix of:

- request text
- legacy analysis categories
- questionnaire answers
- fallback assumptions

Legacy analysis data can remain available for diagnostics, but it should not be
the primary semantic driver of the generated SAD.

### 2A. Structured Fallback SAD Builder

If Gemini preview generation fails schema validation, the local fallback must be
more than a safe echo. It must synthesize the confirmed facts into a useful
Layer 1 SAD outline:

```text
Overview and scope
Users and roles
Workflow
Data and records
Business rules and approvals
Exceptions and edge cases
Reports and summaries
Access and permissions
Integrations
Security and privacy
Audit and history
Assumptions
Open questions
Source traceability
```

The fallback should not use a lower-quality output format than the model path.
It can be simpler, but it must remain structured and developer-readable.

### 3. Preview Prompt Rules

The SAD synthesis prompt must:

- preserve confirmed business facts
- use questionnaire answers only as confirmed refinements
- ask open questions only for unresolved items
- avoid inventing approval paths, workflows, or constraints not supported by
  the merged facts
- exclude internal retry/fallback language from assumptions
- keep Layer 1 and Layer 2 language distinct

### 4. Ready-State UI Rule

When draft readiness reaches `100%`:

- hide active required-category language
- show `Ready to draft`
- keep only optional refinements as a non-blocking section
- do not imply there is still a required category in progress

## Quality Acceptance Criteria

The checkpoint passes only when all are true:

1. A clinic test request produces a first SAD draft that includes:
   - registration
   - queue handling
   - consultation
   - medicine collection
   - payment
   - manager daily summary
   - unpaid / uncollected handling
2. The generated SAD does not mark already-confirmed facts as missing.
3. Business-facing assumptions do not contain retry/fallback diagnostics.
4. Approval-path wording appears only when the project evidence actually
   supports it.
5. Open questions are limited to genuinely unresolved items.
6. Draft readiness and the preview narrative are semantically coherent.
7. The `100%` handoff no longer shows a required active category.
8. The first draft remains useful before the later IT-readiness pass begins.
9. The `Confirmed Business Request` section never contains `Previous question`,
   `Previous answer`, or `Previous readiness`.
10. User amendments are interpreted into the correct SAD areas.
11. The fallback preview contains structured SAD sections, not only raw Q&A
    bullets.
12. At `100%` Layer 1 readiness, optional refinement prompts do not appear as
    blocking open questions.

## Proposed Tests

### Backend tests

1. Build merged facts from request + answers + unresolved items.
2. Keep fallback diagnostics outside business-facing assumptions.
3. Prevent stale legacy category state from overriding confirmed facts.
4. Ensure preview context serializes:
   - confirmed request facts
   - confirmed answers
   - unresolved items
   - no internal diagnostics
5. Strip Q&A transport history from displayed business request.
6. Convert questionnaire answers and amendments into domain-specific SAD
   sections.
7. Verify local fallback preview returns structured sections when model preview
   validation fails twice.

### Prompt / synthesis tests

1. Clinic fixture returns no generic manager-approval language unless approved by
   evidence.
2. Clinic fixture keeps manager daily summary and exception handling in the
   generated preview.
3. Preview open questions match unresolved items, not already-known areas.

### UI tests

1. `Ready to draft` view hides required active-category language.
2. Optional refinements remain collapsed and clearly non-blocking.
3. Any Layer 2 readiness display is labeled separately from Layer 1.

### Manual acceptance

Run the clinic scenario end to end and verify:

1. the questionnaire reaches draft-ready
2. the first SAD draft reflects the whole merged requirement
3. no internal fallback wording leaks into user-facing sections
4. Layer 2 wording is understandable rather than contradictory
5. the generated SAD reads as a complete first draft, not a diagnostic dump
6. the encryption and full audit-history amendments appear under security and
   audit requirements

## Non-Goals

This checkpoint does not yet:

- implement durable Firestore questionnaire memory
- implement wiki approval/update flow
- complete the later IT-readiness questionnaire pass
- redesign the whole knowledge graph
- tune final PDF/DOCX/Google Docs output

## Documentation Impact

If approved, this design should lead to:

1. a completed acceptance test case `TC-021U` for safe synthesis handoff and
   fallback transport.
2. a follow-up acceptance test case `TC-021V` for fallback SAD composition
   boundary cleanup.
3. a follow-up acceptance test case `TC-021W` for user-facing SAD draft quality.
4. a follow-up acceptance test case `TC-021X` for evidence-first Q&A depth and
   valid preview coherence.
5. implementation plans for `MVP-09.5`, `MVP-09.6`, and `MVP-09.7`.
6. updates to:
   - development index
   - development workflow
   - Q&A workflow note
   - MVP test plan
   - handoff doc
   - test case index

## Open Questions

None blocking for planning. The current product decision is already clear:

- Layer 1 first
- Layer 2 still inside MVP
- SAD composition quality checkpoint before wiki work


---

## 2026-05-20-evidence-first-qna-depth-valid-preview-coherence-design

# Evidence-First Q&A Depth And Valid Preview Coherence Design

Date: 2026-05-20
Status: historical design for Phase 4 / TC-021X; active follow-up is TC-021Y

## Problem

TC-021W improved fallback SAD preview composition and local presentation checks, but the 2026-05-20 workshop manual smoke still failed the progression bar for user-facing quality.

Observed result:

- Q&A reached `Ready for draft - 100%`.
- SAD preview generated successfully.
- The preview still showed `60% Low confidence`.
- `Later IT readiness` was visible in the main preview.
- SAD sections were coherent but templated and general.
- Repeated `Source refs: Business Request` lines dominated the pasted output.
- Q&A relied on broad preset questions and answers that did not prove detailed workflow understanding.

## Goal

Make the current SADify Q&A workflow evidence-first so the system captures and reuses concrete business facts before claiming draft readiness or generating the preview.

## Non-Goals

- Do not start MVP-10 / TC-025.
- Do not add live Gemini/cloud requirements for local implementation.
- Do not redesign the whole product information model.
- Do not add durable external persistence beyond the existing MVP state model unless the implementation proves it is required.

## Target Model

### 1. Source Facts

The business request and uploaded sources should be parsed into confirmed facts before the first question is selected.

Confirmed facts should include:

- category;
- slot or facet;
- normalized value;
- source reference;
- confidence or evidence note.

### 2. Facet Coverage

Category completion must be based on meaningful facets, not only one broad answer per category.

Workshop example facets:

- Workflow: trigger, submission, assignment, diagnosis, parts use, approval, repair update, completion, open-state handling.
- Data: machine, request, issue, technician, diagnosis notes, parts used, part cost, status, completion time, open reason, audit event.
- Rules: expensive-part approval, approving role, completion prerequisites, mandatory open reason.
- Exceptions: parts unavailable, overdue job, duplicate or wrong request if not already known.
- Reports: open requests, completed repairs, repeated issues, parts cost, overdue jobs, weekly cadence, report audience.
- Access: staff own requests, supervisor assignment, technician repair updates, manager approvals and reports.
- Integrations: no external systems in first version when stated.
- Non-functional: secure login, role restrictions, audit user and timestamp.

### 3. Question Selection

Questions should ask for the most important missing facet, not repeat facts already present in the request.

For the rich workshop request, the next question should not ask a broad normal-flow question if the request already states submission, assignment, technician work, approval, exception, reporting, access, integration, and audit facts.

Good follow-up examples:

- "What value or rule makes a part expensive enough to require manager approval?"
- "When should a maintenance job be considered overdue?"
- "Which status values should a request move through from submission to closure?"
- "Should technicians be able to edit diagnosis and parts details after completion?"

### 4. Answer Choices

Preset choices may still exist, but they should be contextual and fact-bearing.

Avoid choices that only say:

- "Capture or update records"
- "Review or approve work"
- "Prepare or fulfil the next step"

Prefer choices that preserve details:

- "Supervisor assigns a technician after request submission"
- "Manager approval is required before expensive parts are used"
- "Technician records diagnosis, parts used, status, and completion time"

### 5. SAD Synthesis Context

The SAD generator should receive:

- clean business request text;
- confirmed source facts;
- structured answer facts;
- remaining known gaps;
- presentation rules for user-facing preview.

It should not rely mainly on generic answer labels.

### 6. Preview Presentation

Valid Gemini previews and fallback previews must share the same user-facing presentation guardrails:

- business-facing draft first;
- IT readiness collapsed or secondary;
- no contradictory low-confidence banner when Q&A says ready;
- no raw transport logs;
- no repeated source reference clutter;
- no generic cross-domain leakage.

## Acceptance Criteria

TC-021X local checks passed, but manual workshop/tuition smoke still showed
broader quality gaps. TC-021Y now owns the active acceptance gate.

Historical TC-021X acceptance criteria were:

- rich workshop facts are credited across rules, exceptions, access, integrations, and non-functional needs;
- the first next question targets a genuinely missing detail;
- readiness does not reach `100%` from broad category labels alone;
- SAD preview includes concrete workshop entities, workflow, rules, reports, access, integrations, and audit requirements;
- valid preview UI does not surface `60% Low confidence` plus `Later IT readiness` as the main result after Q&A readiness says draft-ready;
- source references are present but not repeated under every section in a way that hurts readability.

## Traceability

Primary follow-up test:

- `docs/superpowers/testing/test_cases/TC-021X-evidence-first-qna-depth-valid-preview-coherence.md`

Implementation plan:

- `docs/superpowers/plans/2026-05-20-evidence-first-qna-depth-valid-preview-coherence.md`

Active follow-up:

- `docs/superpowers/specs/2026-05-21-domain-aware-qna-sad-quality-hardening-design.md`
- `docs/superpowers/plans/2026-05-21-domain-aware-qna-sad-quality-hardening.md`
- `docs/superpowers/testing/test_cases/TC-021Y-domain-aware-qna-sad-quality-hardening.md`

Prior evidence:

- `docs/superpowers/testing/test_cases/TC-021W-user-facing-sad-draft-quality.md`


---

## 2026-05-21-domain-aware-qna-sad-quality-hardening-design

# Domain-Aware Q&A And SAD Quality Hardening Design

Date: 2026-05-21
Status: active design for Phase 4 / TC-021Y

## Purpose

TC-021X improved the workshop path, but the manual tuition-centre smoke on
2026-05-21 showed the quality problem is broader than one domain. SADify still
leans on broad preset questions, domain-specific hardcoded composers, and
fallback wording that can leak into the user-facing SAD.

This design defines the next refinement: make Q&A and SAD preview quality driven
by extracted business evidence for any operational workflow, not by one-off
workshop or clinic branches.

## Triggering Evidence

Workshop smoke, 2026-05-20:

- rich workshop request reached `Ready for draft - 100%`;
- SAD preview became more domain-aware after TC-021X local implementation;
- remaining issues included generic approval text, clinic wording such as
  `incomplete visits`, tracking path leakage, and too much template feel.

Tuition-centre smoke, 2026-05-21:

- video: `C:\Users\User\AppData\Local\Packages\Microsoft.ScreenSketch_8wekyb3d8bbwe\TempState\Recordings\20260521-0245-19.3155261.mp4`
- Q&A began at `In progress - 42%` and asked a generic business-goal question
  even though the request already stated a clear tracking scope.
- after answering broad preset questions, Q&A reached `Ready for draft - 100%`.
- the SAD preview was domain-aware enough to mention enrolment, schedules,
  attendance, fees, parent updates, and weekly summaries.
- the visible SAD still said it was generated using a fallback mechanism.
- source refs exposed internal slot IDs such as `goal_scope.business_goal`.
- approval wording was invented/generic for a tuition scenario.
- exception handling used generic `mark incomplete and keep open` wording that
  does not fit all tuition cases.

## Problem

The current implementation can pass narrow automated checks while still feeling
template-driven in manual use because:

1. initial fact seeding is deterministic but shallow and domain-specific;
2. fallback questions are mostly broad category prompts, with only one workshop
   contextual refinement;
3. broad preset labels can enter the SAD as confirmed business facts;
4. fallback/diagnostic labels and internal slot IDs can appear in normal output;
5. deterministic SAD composition has hardcoded clinic/workshop branches instead
   of a general evidence-to-section pipeline;
6. old preview state can remain visible after a new business request until a new
   preview is generated.

## Goal

Make the current SADify flow behave like a practical system analyst:

```text
business request
-> extract concrete domain facts
-> identify missing high-risk facets
-> ask one domain-aware question
-> store answer facts with meaning
-> produce a clean Layer 1 SAD draft
-> keep diagnostics and deeper IT review secondary
```

## Non-Goals

- Do not start MVP-10 / TC-025.
- Do not run live Gemini/cloud calls for implementation.
- Do not build a full ontology, RAG layer, or durable Firestore questionnaire
  persistence.
- Do not create a separate domain template pack product.
- Do not remove historical TC-021U/V/W/X evidence.

## Design Principles

### 1. General Evidence Model

Create a small backend evidence layer that extracts facts into stable buckets:

- business goal and first-version scope;
- actors/roles and responsibilities;
- workflow trigger, normal steps, handoffs, completion condition;
- records/entities and important fields;
- rules, approvals, thresholds, and decision authority;
- exceptions and required handling;
- reports, metrics, audience, cadence, and filters;
- access model and restricted actions;
- integrations or explicit no-integration scope;
- non-functional controls such as security, privacy, audit, timestamp, and data
  protection.

Each fact should keep:

- normalized text;
- category ID;
- slot or facet ID;
- source label such as `Business Request`;
- evidence phrase or short reason.

Internal source labels such as `goal_scope.business_goal` are not user-facing
source references.

### 2. Domain Hints Without Hardcoding The Whole SAD

The extractor may infer a light domain profile from nouns and roles:

- tuition centre: student, class, teacher, parent, fee, attendance;
- workshop maintenance: machine, request, technician, part, repair;
- clinic: patient, queue, doctor, pharmacy, cashier;
- generic operations: request/case/task, staff, manager, status, report.

Domain profile should help choose question wording and examples. It must not be
the only way to compose a SAD section. The SAD composer should work from facts
even when the domain is new.

### 3. Missing-Facet Question Ladder

Question selection should prefer the highest-value missing facet, not the first
generic open slot.

For a tuition request that already states enrolment, schedules, attendance,
fees, parent updates, and reports, better first questions are:

- "When should parents be notified about an absence?"
- "When should an unpaid fee become a follow-up item?"
- "What makes a class full?"
- "Who can edit attendance or payment records after they are saved?"

For a rich workshop request, better refinement questions remain:

- expensive-part threshold;
- overdue definition;
- status lifecycle;
- edit-after-completion rule;
- weekly report grouping.

Generic goal questions should be used only when the request truly lacks a clear
purpose or scope.

### 4. Fact-Bearing Choices

Choices should preserve business detail. Avoid using broad labels as final facts.

Bad:

```text
Review or approve work
Capture or update records
Mark incomplete and keep open
```

Better:

```text
Parents are notified after any unexcused absence.
Unpaid fees become follow-up items after the due date.
Class is full when enrolled students reach the configured capacity.
Teachers can correct attendance only with an audit note.
```

### 5. SAD Preview Output Contract

The normal SAD preview must:

- never mention fallback mechanism, repair retry, schema validation, or local
  composer in the document body;
- never show internal slot IDs as source refs;
- never invent an approval path or rule from a generic answer;
- use confirmed request facts before generic defaults;
- convert broad answers into assumptions or open questions when they are not
  specific enough;
- keep IT readiness and tracking details collapsed;
- clear stale preview content when a new analysis/request starts.

### 6. Section Composition

The composer should build sections from the evidence model:

- Confirmed Business Request: concise scope summary from request facts;
- Executive Summary: one paragraph with actors, workflow, and business value;
- Scope: first-version inclusions and explicit exclusions;
- Users and Responsibilities: role-to-action mapping;
- Workflow: ordered steps and handoffs;
- Data and Records: entities, fields, statuses, money/notes/reasons;
- Business Rules and Approvals: only confirmed rules and open rule questions;
- Exceptions and Follow-Up: exception -> required handling pairs;
- Reports and Summaries: metrics, audience, cadence;
- Access and Permissions: role restrictions and sensitive actions;
- Security and Privacy: confirmed controls;
- Audit and History: events, actor, timestamp, changed data;
- Integrations: confirmed systems or explicit no-external-system scope.

## Acceptance Criteria

TC-021Y passes only when local tests and manual smoke prove:

1. tuition, workshop, and one generic operations request produce domain-aware
   first or next questions.
2. a request with clear scope does not ask a generic business-goal question first.
3. readiness cannot reach `100%` only because every category received one broad
   preset answer.
4. broad preset answers are not rendered as precise business requirements unless
   amended with specific detail.
5. generated SAD preview contains no visible `fallback mechanism`,
   `_SADify/local-fallback`, `Previous question`, or internal slot IDs.
6. tuition SAD sections mention student enrolment, class assignment, schedules,
   attendance, progress notes, parent absence/unpaid-fee updates, weekly manager
   summaries, class capacity, security, and audit only when supported by facts or
   marked as open questions.
7. workshop SAD rules use maintenance language, not clinic wording such as
   `incomplete visits`.
8. old preview content is cleared when a new analysis/request begins.
9. source references remain accessible but business-facing.

## Documentation Impact

This design creates the new active Phase 4 gate:

- `docs/superpowers/testing/test_cases/TC-021Y-domain-aware-qna-sad-quality-hardening.md`
- `docs/superpowers/plans/2026-05-21-domain-aware-qna-sad-quality-hardening.md`

TC-021X becomes a local implementation pass with manual progression failure
evidence. It remains historical traceability, not the active blocker.


---


---

## 2026-05-22-evidence-based-readiness-design

# Evidence-Based Readiness Design

Date: 2026-05-22
Last updated: 2026-05-22
Status: Approved design; ready for implementation planning
Owner track: Phase 4 - SAD preview and SAD quality stabilization

## Purpose

Replace SADify's rigid, keyword-driven Q&A readiness with an evidence-based
readiness model. The model judges how well each requirement area is supported by
real material (business request, uploaded files, saved answers), and the backend
aggregates that judgement into a readiness score deterministically.

This is the first of two sequenced cycles. SAD synthesis quality is the second
cycle and is intentionally out of scope here. The evidence model defined in this
spec is shaped so the later SAD synthesis cycle can reuse it without redesign.

## Traceability Sources

This spec should be verified against:

- `CLAUDE.md`
- `context.md`
- `docs/superpowers/development/07_decision_log.md`
- `docs/superpowers/development/14_qna_workflow_refinement.md`
- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `docs/superpowers/development/05_development_workflow.md`
- `docs/superpowers/testing/test_case_index.md`

If readiness behavior, the questionnaire data model, or the AI/backend boundary
changes, update this spec and the affected source docs together.

## Problem Statement

The current Q&A readiness is rigid and not evidence-based:

- Readiness is `covered_required_slots / total_required_slots * 100`
  (`questionnaire_plan.py` `recalculate_readiness`). With ~19 fixed required
  slots, the score can only land on fixed `N/19` steps.
- Each slot is binary (`open` / `covered`). Evidence quality is never weighed.
- Coverage is decided by a ~240-line keyword table
  (`routes/analysis.py` `_initial_facts_from_request`, lines ~825-1067) and a
  hardcoded broad-label reject dict (`_answer_has_enough_evidence`,
  lines ~1070-1156). Every new domain or phrasing needs new hardcoded rules.
- Per-category progress uses literal constants `100/50/25/35/0`
  (`_category_progress`, `_category_progress_status`).
- The Gemini analysis call already returns a `readiness.score`, but the
  questionnaire path discards it and uses only the slot-coverage arithmetic.

Result: every time a user initiates a context with text or a file, SADify
returns a coarse, preset-feeling percentage that does not reflect what the
request actually contains.

## Confirmed Design Decisions

Settled during brainstorming on 2026-05-22:

1. **Scope:** readiness first; SAD synthesis is a separate later cycle. The
   evidence model is designed to be reusable by that later cycle.
2. **Structure:** hybrid. The 10 fixed core categories and their frozen order
   stay as a stable backbone. The AI may mark areas as not-applicable per
   project. Per-area readiness is AI-judged on an evidence scale, not keyword
   matching.
3. **Model calls:** the evidence judgement is folded into the existing analysis
   call. No extra Gemini call, no extra cost.
4. **Acceptance:** a fixed scenario table with expected readiness bands, asserted
   automatically, plus the user's manual sign-off.
5. **Evidence aggregation:** Approach A - per-slot evidence verdicts with cited
   quotes, validated and aggregated by the backend.

## Architecture And Boundary

The AI judges evidence. The backend owns truth.

```text
business request + uploaded files + saved answers
  -> existing Gemini analysis call (schema extended with slot_evidence)
  -> backend quote validation and downgrade
  -> backend builds the questionnaire plan from validated evidence
  -> backend aggregates readiness score and derives confidence
  -> stable plan, frozen category order, draft-ready gate
```

Unchanged backbone:

- The 10 canonical categories (`CANONICAL_CATEGORY_IDS`) and their slot
  blueprints (`_CATEGORY_BLUEPRINTS`).
- Frozen visible category order (decision log #2 and #4).
- The stable questionnaire plan and one-active-category Q&A flow.

Changed:

- Decision log #8 is amended. It currently states readiness is fully
  backend-calculated and not Gemini-decided. The amended rule: the backend
  aggregates readiness deterministically, but the per-slot evidence inputs are
  AI-judged and quote-validated. The AI never returns a final score.

## The Evidence Model

### New AI output: `slot_evidence`

The analysis response schema (`gemini_structured.py`
`requirement_analysis_schema`) gains a `slot_evidence` array. For every required
slot of every core category the model returns one verdict:

```text
{
  "category_id": "<canonical category id>",
  "slot_id": "<canonical slot id>",
  "applicability": "applicable" | "not_applicable",
  "strength": "none" | "partial" | "strong",
  "evidence_quote": "<verbatim span copied from the supplied material>",
  "rationale": "<one short sentence>"
}
```

Rules given to the model:

- Judge every required slot listed in the prompt. Optional slots may also be
  judged but do not affect required readiness.
- `applicability = not_applicable` means the area genuinely does not fit this
  project (for example, integrations for a tool with no external systems).
- `strength` rates how well the supplied material supports the slot:
  - `strong` - the material clearly and specifically states it;
  - `partial` - the material hints at it or states it only vaguely;
  - `none` - the material does not cover it.
- `evidence_quote` must be copied verbatim from the supplied material for any
  `partial` or `strong` verdict. It may be empty for `none` or `not_applicable`.

The prompt embeds the canonical category/slot list (id and plain-language label)
so the model judges a known, fixed set.

### Pydantic model: `SlotEvidence`

New model in `schemas.py`:

```text
SlotEvidence(ApiModel):
  category_id: str
  slot_id: str
  applicability: Literal["applicable", "not_applicable"]
  strength: Literal["none", "partial", "strong"]
  evidence_quote: str = ""
  rationale: str = ""
```

`RequirementAnalysisResponse` gains:

```text
slot_evidence: list[SlotEvidence] = Field(default_factory=list)
```

Because `ApiModel` uses `extra="forbid"`, the field must be added to both the
Gemini response schema and the Pydantic model, and to the schema `required` and
`propertyOrdering` lists.

### Questionnaire plan changes

`QuestionnairePlanSlot` gains two fields:

```text
evidence_strength: Literal["none", "partial", "strong"] = "none"
applicable: bool = True
```

`status` is still present and still drives the Q&A flow, but it is now derived:

- user explicitly deferred the slot -> `confirm_later`;
- `evidence_strength == "strong"` -> `covered`;
- otherwise (`partial` or `none`) -> `open`, so partial slots still get a
  question.

`applicable == false` slots are skipped by next-question selection and excluded
from the readiness denominator.

`QuestionnairePlanCategory.visibility` and
`QuestionnaireProgressCategory.visibility` gain a `not_applicable` value. A
category whose required slots are all `not_applicable` is shown in a collapsed
"Not relevant to this project" section, mirroring the existing
`already_understood` and `completed` groups.

## Data Flow

### Context initiate (text and/or uploaded file, no answers)

1. `analyze_requirement` builds the model text from request and source context
   (existing `_build_model_requirement_text`).
2. The Gemini analysis call returns `next_question` and `slot_evidence` for all
   required slots.
3. The backend validates quotes, builds the plan from evidence, computes
   readiness and confidence.
4. Readiness reflects what the request or file actually contains. No preset
   percentage.

### Answer submit

1. The existing transport appends the previous question/answer to the model
   text.
2. The analysis call re-judges `slot_evidence` with the answers now part of the
   supplied material. A genuine answer produces a `strong` verdict that quotes
   the answer text. A vague or broad answer produces `partial` or `none`, so
   readiness does not jump falsely. This replaces `_answer_has_enough_evidence`.
3. The backend rebuilds the plan from the latest verdicts.

### Recompute and answer edits

The backend always rebuilds the plan from the current verdicts every turn, so
editing an earlier answer naturally re-judges affected slots and readiness can
move down for a real reason. No special edit handling is required.

## Scoring And Confidence

### Readiness aggregation

In `recalculate_readiness`:

```text
applicable_required = required slots where applicable == true
weight(slot):
  status == confirm_later (user-deferred) -> 1.0
  evidence_strength == strong             -> 1.0
  evidence_strength == partial            -> 0.5
  evidence_strength == none               -> 0.0
score = round(100 * sum(weight) / max(1, count(applicable_required)))
```

`not_applicable` slots are excluded from both numerator and denominator. The
score moves in half-slot steps over a project-specific denominator, so the fixed
`N/19` quantization is gone.

### Draft-ready gate

The questionnaire is draft-ready when:

- `score >= 90`, and
- no applicable required slot is still at `evidence_strength == none`.

The second condition stops a high percentage from masking one completely empty
critical slot. This replaces the separate keyword-based
`missing_blocking_basics` gate for the questionnaire-driven path.

### Confidence (derived, not asserted)

The backend derives confidence from the verdict mix instead of trusting a free
AI field:

- `High` - at least 70 percent of applicable required slots are `strong`, and no
  verdict was downgraded by quote validation;
- `Low` - more than 50 percent of applicable required slots are `none`, or two
  or more verdicts were downgraded;
- `Medium` - otherwise.

The AI's existing `readiness` object stays in the schema unchanged (no schema
break), but `questionnaire.draft_readiness` - the value the UI shows - becomes
fully evidence-derived for both score and confidence. This removes the current
contradiction where readiness can show 100 percent with Low confidence.

## Validation And Error Handling

### Quote validation (anti-hallucination guard)

For every verdict with `strength` of `partial` or `strong`:

1. The backend builds the combined material: clean business request plus source
   context plus every saved answer text.
2. It normalizes both the quote and the material (lowercase, collapse
   whitespace).
3. If `evidence_quote` is empty or is not a substring of the normalized
   material, the verdict is downgraded one notch (`strong` -> `partial` ->
   `none`) and a diagnostic is recorded.

This is the truth guard, analogous to the existing `QuestionnaireDriftError`
category check. The AI cannot inflate readiness with invented evidence.

Additional validation:

- Verdicts referencing unknown category or slot IDs are dropped.
- Required slots with no verdict default to `strength = none`,
  `applicability = applicable`.

### AI call failure

The analysis call already retries once and then falls back to the local
`_fallback_requirement_analysis` path. With the keyword tables removed, the
fallback emits empty `slot_evidence`. All slots become `none`, so readiness is
Low and confidence is Low, with an honest diagnostic such as
"analysis incomplete, retrying". The fallback still produces a next question
through existing fallback-question logic. This is honest degradation rather than
a keyword guess.

## What Gets Deleted Or Replaced

Deleted from `routes/analysis.py`:

- `_initial_facts_from_request` - the ~240-line keyword table.
- `_answer_has_enough_evidence` - the hardcoded broad-label reject dict.
- `_category_progress` and `_category_progress_status` - the literal
  `100/50/25/35/0` progress constants.

Callers of `_initial_facts_from_request` (`_with_questionnaire_state`,
`_questionnaire_plan`, `_locked_target_for_request`) are updated to consume
validated `slot_evidence` instead.

## New And Changed Files

- `services/api/src/sadify_api/services/gemini_structured.py` - add
  `slot_evidence` to `requirement_analysis_schema`; update `_analysis_prompt`
  with the evidence instructions and the embedded canonical slot list; raise
  `max_output_tokens` for the analysis call from 1800 to about 3000 to fit the
  new array.
- `services/api/src/sadify_api/schemas.py` - add `SlotEvidence`; add
  `slot_evidence` to `RequirementAnalysisResponse`; add `evidence_strength` and
  `applicable` to `QuestionnairePlanSlot`; add `not_applicable` to the two
  `visibility` literals.
- `services/api/src/sadify_api/services/questionnaire_plan.py` - build the plan
  from evidence; new weighted aggregation in `recalculate_readiness`; derived
  slot `status`; `not_applicable` category visibility.
- `services/api/src/sadify_api/services/slot_evidence.py` - new focused service:
  quote validation and downgrade, confidence derivation, and the
  plan-from-evidence glue. Keeps this logic out of the already large
  `routes/analysis.py` (1874 lines).
- `services/api/src/sadify_api/routes/analysis.py` - delete the three keyword
  functions; consume `slot_evidence`.
- `apps/web` - extend the `QuestionnairePlanSlot` and readiness TypeScript types;
  render the collapsed "Not relevant to this project" section. Minor; the UI
  already renders categories and statuses.
- `tests/api/test_slot_evidence.py` - new tests for validation, downgrade,
  aggregation, confidence, and the scenario table.
- Existing affected tests in `tests/api/test_gemini_structured.py` and
  `tests/api/test_questionnaire_plan.py` - updated for the new model.

## Testing

### Scenario table

Five fixed requests, each asserted automatically against an expected readiness
band and key slot expectations, then confirmed by manual sign-off:

| # | Scenario | Expected |
| --- | --- | --- |
| 1 | One-line vague request | readiness Low (~10-30%), most slots `none`, confidence Low |
| 2 | Rich multi-paragraph workshop request | readiness Medium-High, several slots `strong`, some still `partial`/`none`, confidence Medium |
| 3 | File-only upload with minimal typed text | readiness reflects file content - not zero, not preset |
| 4 | Good request plus broad/vague answers submitted | readiness does not reach 100; broad answers score `partial` |
| 5 | Category genuinely irrelevant (no integrations) | that category `not_applicable`, excluded from the denominator, readiness not penalized |

### Anti-hallucination test

A verdict whose `evidence_quote` does not appear in the supplied material is
downgraded, and the downgrade lowers confidence.

### Test quality rule

Tests assert evidence verdicts and readiness bands - real behavior - not keyword
presence in output strings. Keyword-presence assertions are the reason earlier
checkpoints passed locally but failed manual smoke.

## Docs To Update During Implementation

- `docs/superpowers/development/07_decision_log.md` - amend decision #8.
- `docs/superpowers/development/14_qna_workflow_refinement.md` - rewrite the
  Readiness section (#8) for the evidence model.
- `docs/superpowers/development/03_data_model_and_output_schema.md` - add
  `SlotEvidence` and the updated `QuestionnairePlanSlot`.
- `docs/superpowers/testing/test_case_index.md` and a new `TC-` test case for
  this checkpoint.
- `context.md` and `docs/superpowers/CURRENT.md` - phase notes.

## Out Of Scope

- SAD synthesis quality and the SAD preview fallback templates. That is the
  second cycle and gets its own spec, plan, and test case.
- Changing the 10 canonical categories or their order.
- Live non-Google model providers.
- Wiki, Drive, and Docs save paths.

## Implementation Handoff

Implementation will be executed by Codex. The implementation plan produced from
this spec must therefore be detailed enough to follow task-by-task without this
conversation, and it must include a standalone handover Markdown document that
summarizes context, branch, verification commands, and stop conditions for the
Codex session.

