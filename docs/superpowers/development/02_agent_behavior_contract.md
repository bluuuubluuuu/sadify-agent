# SADify Agent Behavior Contract

Date: 2026-04-30  
Last updated: 2026-06-19

## Purpose

This document defines how SADify must behave when interpreting requirements, asking clarification questions, scoring completeness/confidence, generating SAD output, and handling source files.

This contract should guide prompts, code logic, tests, UI layout, and demo behavior.

## Traceability Sources

This behavior contract should be verified against:

- `docs/superpowers/development/01_product_scope.md`
- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `docs/superpowers/development/05_development_workflow.md`
- `docs/superpowers/development/14_qna_workflow_refinement.md`
- `docs/superpowers/testing/test_case_index.md`
- `docs/superpowers/research/2026-05-02-track-1-resource-link-analysis.md`

If agent behavior changes, update matching schemas, workflow checkpoints, and tests.

## Core Behavior Principle

SADify is an AI system analyst, not a generic chatbot.

It must not jump straight from messy input to final SAD output. It should first analyze the requirement, show what it understands, identify missing information, score completeness and confidence, then ask clarification questions.

The user may still choose to generate a draft early, but that draft must clearly mark assumptions, unresolved issues, and open questions.

## First Response Pattern

For the MVP, SADify should use a consistent first-response structure every time a user submits a new requirement.

The standard first response must include:

1. What SADify understands
2. Readiness level
3. Confidence level
4. What the business still needs to confirm
5. Practical clarification questions
6. Option to generate a draft with assumptions

This fixed pattern keeps the MVP predictable, testable, and easy to explain in a demo video.

Future or premium versions may support adaptive response arrangement. For example, SADify may analyze file readiness, identify which source is most complete, and restructure the response order based on priority. That behavior is not required for the MVP.

## MVP Web App Q&A Update

The proper web-app MVP changes the user experience from a report-like first response into a guided analyst workflow.

Confirmed MVP Q&A behavior:

```text
1. Ask one simple question at a time.
2. Always provide answer choices.
3. Provide an amend/free-text option after an answer is selected.
4. Show a short "why this matters" explanation.
5. Show question-area status so the user understands what SADify is learning.
6. Let the backend choose the active category and slot; let Gemini phrase the next question inside that locked target.
7. Keep technical SAD/wiki/process details hidden unless the user opens details.
```

The user should not need to understand SAD methodology, wiki structure, Firestore, Drive, schema validation, or versioning. SADify handles that as a black-box analyst workflow and shows only the business-relevant category, current question, answer history, draft readiness, and change summary by default.

### Category-First Q&A Rule

Manual testing on 2026-05-14 showed that mixing a fallback top-level menu with category questions is confusing.

The target MVP workflow is category-first:

```text
initial request/files
  -> identify relevant categories
  -> mark already-clear categories as ready
  -> choose the first unclear category
  -> ask questions inside that category until it is clear enough
  -> move to the next unclear category
```

The top-level is the stable question-area status line or navigator. It is not a separate question flow.

Completed categories should not be re-asked. They may appear as `Ready`, read-only, or inside a collapsed `Already understood` section.

When Gemini fails to return a valid structured question, fallback should continue inside the active category whenever possible. It should not bounce the user back to a broad menu unless there is no active category.

Implementation note:

```text
The approved replacement behavior is documented in `14_qna_workflow_refinement.md`.
Normal Q&A should show overall readiness, question-area word statuses,
active-category answers, and collapsed non-numeric AI diagnostics.
```

### Question And Answer Rules

Top-level category selection is single-select.

Category-specific questions may be multi-select only when more than one answer can naturally be true, such as users/roles or data/report details.

`I'm not sure` is a valid answer. SADify must:

- flag it as uncertainty
- keep the user in the same category
- ask an easier suggested-default follow-up
- avoid marking the category as fully ready unless the user approves an assumption or later confirms the detail

`Other / not listed` requires amendment details before continuing.

Domain-aware refinement rule:

```text
If the request already states a clear goal, scope, roles, workflow, records,
reports, or constraints, SADify should not ask a generic question for that same
fact. It should ask the highest-value missing business rule, exception,
permission, notification, threshold, status, or audit detail instead.
```

Broad answer rule:

```text
Broad preset labels are useful UI shortcuts, but they are not enough by
themselves to create precise SAD requirements. Unless an answer carries specific
business detail or an amendment adds it, the SAD should treat the area as a
draft assumption or open question rather than confirmed implementation logic.
```

## User-Facing Language Rule

The requester-facing UI should use business language first.

Use labels such as:

- What SADify understands
- Readiness
- What we still need to know
- Questions to confirm with the business

Avoid showing analyst or developer jargon in the first-response UI unless the user is looking at a SAD/developer artifact. Internal categories can still use terms like actors, workflow, data fields, approval rules, permissions, exceptions, and non-functional constraints so the generated SAD remains structured.

## Requirement Interpretation Pipeline

SADify does not train a custom model in the MVP.

Requirement interpretation should come from:

- the configured model route, with Google/Gemini as the default
- SADify system instructions
- a structured completeness checklist
- uploaded or pasted source context
- saved project/session history
- source traceability
- tool actions exposed through a clean tool layer, preferably MCP-compatible where practical

The MVP interpretation pipeline:

```text
User text or business file
  -> extract readable content
  -> normalize into requirement context
  -> analyze through the configured model route
  -> check against completeness checklist
  -> link related requirements, entities, workflows, decisions, and sources
  -> identify missing information
  -> ask clarification questions
  -> generate structured SAD draft
  -> generate connected Markdown wiki files
```

## Supported Input Types

SADify should support normal business files in the MVP.

MVP input support:

- typed or pasted text
- Markdown notes
- TXT files
- PDF files
- DOCX files
- XLSX files
- CSV files

Image input is the first priority potential development after the normal business-file MVP. It may be free with limits or part of a paid tier later. The exact limit should be decided after the core MVP works.

Future complex input support:

- images and site photos
- scanned multi-page documents
- handwritten notes
- audio or voice input
- video input
- Google Drive folder import
- email or chat thread import

## Source Handling And Traceability

SADify should treat files as both requirement context and traceable source material.

When possible, generated requirements, assumptions, gaps, and recommendations should reference their source.

MVP traceability level:

- file-level traceability
- section or page-level traceability where available
- sheet or column-level traceability for spreadsheets where available

Potential future traceability:

- exact line reference
- exact cell reference
- exact row reference
- precise page or paragraph reference

Example:

```text
FR-03: The system shall track fertilizer application by block and date.
Source: uploaded_fertilizer_log.xlsx, Sheet: April Records, Columns: Block, Date, Fertilizer Type
```

## Completeness Level

Completeness means:

```text
How much required information is present?
```

Completeness should use a hybrid approach:

- deterministic checklist for stable scoring
- Gemini explanation for nuance and user-friendly reasoning

The checklist should inspect whether these categories are present:

- actors
- workflow trigger
- current workflow
- proposed workflow
- required data fields
- approval rules
- reports
- exceptions
- permissions
- non-functional constraints
- business rules
- integration needs, if relevant

Readiness can be backed by the completeness score, but the UI should use the friendlier requester-facing label:

```text
Readiness: 65%
Level: Partial
```

For the guided Q&A UI, visible percentages should be used carefully:

- question-area status: shown as words such as `Needs answer`, `In progress`, `Ready`, or `Confirm later`
- overall readiness: one user-facing percentage derived from required slot coverage and blockers
- model confidence: not shown as a large percentage

MVP readiness has two layers:

```text
Draft readiness:
  Is there enough confirmed context to create a coherent first SAD draft?

IT readiness:
  Is there enough implementation detail for stronger IT planning and a more
  build-ready SAD revision?
```

SADify should complete the draft-ready layer first, generate the first useful
SAD draft, then continue with deeper IT-readiness questions on the same project.
Layer 2 is part of the MVP, but it should not block the user from seeing the
first useful draft.

Suggested levels:

| Score Range | Level | Meaning |
| --- | --- | --- |
| 0-39% | Low | Too much important context is missing |
| 40-69% | Partial | Enough to discuss, not enough for a reliable final SAD |
| 70-84% | Good | Mostly usable, but some gaps remain |
| 85-100% | Strong | Enough for a confident SAD draft |

## Confidence Level

Confidence means:

```text
How reliable is SADify's interpretation?
```

Confidence should use a hybrid approach:

- source quality
- ambiguity level
- completeness score
- consistency between files and user answers
- Gemini self-check

Confidence may be shown in generated SAD output or diagnostics as:

```text
Confidence: Medium
Reason: The workflow is clear, but approval rules and exception handling are not confirmed.
```

In the requester-facing Q&A panel, confidence should not be a large numeric display. Normal users care more about what is ready and what to answer next. Use a small non-numeric badge only if needed:

```text
AI check: needs review
AI check: usable
AI check: strong
```

Suggested confidence labels:

| Label | Meaning |
| --- | --- |
| Low | SADify may be misunderstanding the requirement or missing important context |
| Medium | SADify understands the main idea, but several details need confirmation |
| High | SADify has enough clear, consistent context to generate a reliable SAD draft |

## Problem And Recommendation Labels

SADify must separate problem severity from recommendation priority.

Problem severity is risk-based.

Recommendation priority is planning-based.

### Problem Severity Labels

Use these labels internally for missing information, unclear requirements, contradictions, and risks. In the first-response UI, show the unbracketed business priority labels `Critical`, `High`, `Medium`, and `Low`.

| Label | Meaning |
| --- | --- |
| [CRITICAL] | Cannot design safely or correctly without resolving this |
| [HIGH] | Likely to affect workflow, data model, permissions, or delivery |
| [MEDIUM] | Improves accuracy and planning, but may not block the first draft |
| [LOW] | Useful detail, but minor for initial understanding |

### Recommendation Priority Labels

Use these labels for suggested system features, design decisions, or next actions:

| Label | Meaning |
| --- | --- |
| [MUST-HAVE] | Needed for MVP correctness or business usefulness |
| [SHOULD-HAVE] | Important, but can be phased after core flow |
| [NICE-TO-HAVE] | Useful improvement if time allows |
| [FUTURE] | Later-stage, premium, or non-MVP idea |

### Trust Labels

Use these labels to keep generated output transparent:

| Label | Meaning |
| --- | --- |
| [ASSUMPTION] | SADify inferred this because the user did not confirm it |
| [OPEN QUESTION] | The user should answer this before finalizing |
| [SOURCE] | Shows where the item came from |
| [CONFIDENCE] | Explains reliability of the interpretation |

## Visual Arrangement Rules

SADify output should be easy to scan and track.

The MVP should use a mixed format:

- short explanations where context is needed
- tables for tracking gaps, requirements, tasks, entities, and recommendations
- consistent bracket labels for severity, priority, assumptions, sources, and confidence
- clear section headings
- important items near the top, not buried at the bottom
- question-area status lines for the questionnaire
- answered-question history inside the active category
- model confidence hidden in diagnostics unless explicitly needed

Example requester-facing missing information table:

```markdown
| Area | Priority | What is unclear | Why this matters | What to answer next |
| --- | --- | --- | --- | --- |
| Checking and approval | High | It is not clear who checks, approves, rejects, or changes records | The system needs clear controls for important decisions and changes | Say who can check, approve, reject, correct, or override the record |
| Details to capture | High | We do not yet know what details staff need to enter, scan, or select | Forms, records, and reports depend on these details | List details such as item, quantity, status, date, location, reason, or remarks |
```

Example recommendation table:

```markdown
| Priority | Recommendation | Reason | Phase |
| --- | --- | --- | --- |
| [MUST-HAVE] | Add audit trail | Needed for accountability | MVP |
| [SHOULD-HAVE] | Add weekly summary report | Helps management visibility | Phase 2 |
```

## Draft Generation Rules

SADify should recommend clarifying missing information before generating the final SAD.

However, the user may choose to generate a draft even when completeness or confidence is low.

If the user generates early, SADify must:

- allow a draft
- clearly mark assumptions
- list open questions
- label missing information by problem severity
- label suggested features by recommendation priority
- state that the output is a draft, not a finalized SAD
- keep unresolved risks visible near the top

SADify must not present low-confidence output as final truth.

After a draft-ready SAD is created, SADify should be able to continue into an
IT-readiness pass that asks only the deeper unresolved implementation questions
needed to strengthen the next SAD revision.

## Canonical Output Format

SADify should keep one canonical structured representation internally, preferably JSON.

This canonical internal structure is the source of truth for:

- Markdown or HTML preview
- Google Docs export
- PDF export
- DOCX export
- Obsidian-compatible Markdown wiki files
- future templates
- future developer ticket export

Normal user-facing export behavior should include:

- Markdown or HTML preview
- Google Docs export
- PDF export
- DOCX export
- connected Markdown wiki export

These basic export formats should not be treated as premium-only behavior.

Plan differences may be based on:

- input file size
- number of input files
- total source context size
- output document size
- number of exports
- number of saved versions
- retention period
- template count
- collaboration and organization features

Pricing should scale with processing, storage, export workload, customization, and collaboration. It should not block basic usefulness.

## Standard SAD Output Sections

When generating a SAD draft, SADify should include:

1. Project title
2. Requirement summary
3. Completeness and confidence summary
4. Critical gaps and open questions
5. Problem statement
6. Stakeholders
7. Current workflow
8. Proposed workflow
9. Functional requirements
10. Non-functional requirements
11. User roles and permissions
12. Business rules
13. Edge cases and exception handling
14. Data entities
15. Integration needs
16. DFD-style process description
17. Developer task breakdown
18. Assumptions
19. Source traceability

The exact display can evolve, but the MVP should keep these sections predictable.

User-facing quality rule:

```text
If SADify uses a local fallback composer because the AI returned invalid
structured SAD preview formatting, the visible SAD must still read like a normal
business document. The main preview must not expose fallback/debug labels,
repair failures, raw Q&A transcript history, contradictory readiness scores, or
informal amendment wording. Diagnostics may exist, but only behind collapsed
tracking details.
```

Source reference quality rule:

```text
Normal SAD output may show business sources such as Business Request or uploaded
source IDs. It must not show internal questionnaire slot IDs such as
goal_scope.business_goal as user-facing source references.
```

## Model Routing Behavior

SADify now has model route metadata for:

```text
requirement_analysis
final_sad
fallback
```

Default behavior:

```text
requirement_analysis: google / gemini-2.5-flash
final_sad: google / gemini-2.5-flash
fallback: not configured
```

This does not change the first-response behavior contract. The agent must still clarify first, expose question-area status and overall readiness, keep confidence available as diagnostics, show missing information, and mark assumptions before producing final-looking output.

Live non-Google adapters are future until the requirement-analysis flow exists and can test them against real SADify behavior.

## Must Not Do

SADify must not:

- hide assumptions
- present low-confidence output as final truth
- invent business rules without marking them as assumptions
- skip missing critical information silently
- bury important open questions at the bottom
- generate developer tasks that are not traceable to requirements
- treat vague input as complete just because it sounds plausible
- confuse problem severity with recommendation priority
- overfit the product to one demo domain
- claim it trained or learned a custom model when it only used prompts/context
- lock basic trustworthy behavior behind payment
- bury export, wiki generation, or verification behavior inside UI-only code that cannot be tested through the agent core

## Durable GitHub Issue Relaunch

GitHub issue preparation is an authenticated, saved-SAD operation. The agent must resolve the caller's active Drive grant, project, and owned `save_id` before preparing or approving an issue set.

- The prepared issue set is immutable and locks the original GitHub repository.
- Preparing persists the set before returning an approval.
- Relaunch reads the stored set, performs no model or task-extraction call, and mints a fresh in-memory GATE 3 approval.
- Relaunch never bypasses approval, even when the set was approved previously.
- A PAT is held only in frontend memory and is sent only for approval execution; it is never persisted in the issue set or approval result.
- A failed GitHub write preserves the current approval so the user can correct the PAT or retry.
- Sequential retries compare stable body markers across open and closed GitHub issues. Existing markers are skipped and reported, not recreated.
- An all-skipped result is successful completion, not an error.
- Concurrent marker checks are not exactly-once; the accepted v1 limitation is documented in TC-036.

## MVP Acceptance Criteria

The behavior contract is satisfied when SADify can:

1. Accept messy text or business-file context.
2. Summarize what it understands.
3. Show question-area status and overall readiness.
4. Keep model confidence available as diagnostics instead of a main user-facing score.
5. List missing information with problem severity labels.
6. Ask clarification questions.
7. Allow early draft generation only with visible assumptions and open questions.
8. Generate a structured SAD draft with consistent sections.
9. Preserve source traceability where available.
10. Generate linked wiki Markdown files from the canonical structure.
11. Render output in a clear mixed format using consistent labels and tables.
