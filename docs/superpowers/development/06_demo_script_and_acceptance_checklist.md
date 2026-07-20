# SADify Demo Script And Acceptance Checklist

Date: 2026-05-02  
Last updated: 2026-05-04

## Purpose

This document defines how to prepare the SADify demo without locking the final demo domain too early.

The demo should be problem-first, practical, and evidence-backed. It should show why SADify exists, how it behaves differently from a generic chatbot, and what must work before recording.

## Traceability Sources

This demo checklist should be verified against:

- `docs/Google for Startups AI Agents Challenge.md`
- `docs/superpowers/research/2026-05-02-track-1-resource-link-analysis.md`
- `docs/superpowers/development/01_product_scope.md`
- `docs/superpowers/development/02_agent_behavior_contract.md`
- `docs/superpowers/development/05_development_workflow.md`
- `docs/superpowers/testing/test_case_index.md`

If the demo case, judging emphasis, or acceptance gate changes, update product scope and relevant tests.

## Demo Position

SADify should be presented as an AI system analyst for production and on-site operations teams.

The demo should explain:

```text
Production/on-site teams know the real operational problem.
IT/development teams need structured requirements.
SADify bridges the gap by clarifying, scoring, structuring, linking, and exporting the requirement knowledge.
```

Technical framing for the prototype:

```text
The demo should default to Google/Gemini for Track 1 alignment. The model-routing foundation can be mentioned as architecture readiness, but the video should not distract from the core clarification-first workflow.
```

Short comparison line:

> Generic AI often jumps straight to solutions. SADify clarifies missing requirement areas first, then generates developer-ready output.

## Demo Scenario Status

The final demo scenario is intentionally undecided for now.

Do not lock the project to warehouse, plantation, manufacturing, HR operations, maintenance, or any other single domain yet.

The chosen scenario should prove the method, not narrow the product.

## Scenario Selection Checklist

A good demo scenario should have:

- real operational pain
- non-technical user input
- at least 2-3 user roles
- missing approval or exception details
- important data fields
- reports or management visibility
- clear business rules
- enough complexity to show related requirements
- enough source material to show traceability
- enough structure to generate wiki links
- not too complex for a 3-5 minute demo

Avoid demo scenarios that are:

- too simple
- too technical from the start
- too broad to explain quickly
- dependent on many integrations
- hard to understand without domain knowledge

## Main Wow Sequence

The demo should show these moments in this order:

```text
1. Clarification + question-area status
2. Connected wiki knowledge
3. Google Docs/PDF/DOCX export
```

This sequence shows the difference between SADify and a generic document generator.

## Flexible Demo Timeline

Target length:

```text
3-5 minutes
```

The timing below is a guide, not a strict rule.

### 0:00 - 0:40 Problem

Explain the real communication gap:

- operations people know the real problem
- IT people need structured requirements
- unclear requirements cause wrong assumptions, rework, and delays

Sample wording:

> In many teams, production or on-site staff understand the real issue, but they describe it in daily operational language. Developers need actors, workflows, data fields, approvals, exceptions, and constraints. SADify helps translate that messy operational knowledge into structured system analysis.

### 0:40 - 1:10 What SADify Is

Explain SADify in one or two sentences:

> SADify is an AI system analyst that turns messy operational input into clarified, complete, developer-ready System Analysis and Design output.

Mention the key behavior:

- it does not immediately generate a final SAD
- it checks question-area status and overall readiness
- it asks clarification questions
- it builds connected requirement knowledge

### 1:10 - 2:40 Live Product Flow

Show:

1. user enters messy requirement or uploads business files
2. SADify summarizes what it understands
3. SADify shows question-area status and overall readiness
4. SADify lists missing information
5. SADify asks clarification questions
6. user answers or chooses draft with assumptions

Important demo point:

```text
SADify should visibly show missing information instead of hiding assumptions.
```

### 2:40 - 3:30 Connected Knowledge Layer

Show:

- generated knowledge items
- linked requirements, actors, entities, workflows, reports, decisions, and sources
- Obsidian-compatible Markdown wiki files
- optional graph view if available

Explain:

> SADify does not only generate a document. It builds a connected requirement knowledge base, so teams can see how requirements, data, workflows, and sources relate to each other.

### 3:30 - 4:20 SAD Output And Exports

Show:

- project-level SAD preview
- assumptions and open questions
- source traceability
- developer task breakdown
- Google Docs export
- PDF export
- DOCX export
- wiki Markdown export folder

Important demo point:

```text
The SAD is generated from canonical structured data, not from a random one-off chat response.
```

### 4:20 - 5:00 Close

Close with business value:

- clearer requirements
- fewer assumptions
- faster IT understanding
- reusable requirement knowledge
- safer development handoff

Sample closing:

> SADify helps teams move from vague operational problems to clarified, traceable, developer-ready specifications. The goal is not just to generate a document, but to create a reliable requirement knowledge base that both operations and IT can trust.

## Acceptance Checklist

Do not record the final demo until the checklist below is satisfied or any remaining gaps are intentionally documented.

## Product Readiness

- [ ] A user can enter messy requirement text.
- [ ] A user can upload supported business files if file upload is included in the demo.
- [ ] SADify shows an understanding summary.
- [ ] SADify shows question-area status.
- [ ] SADify shows draft readiness.
- [ ] Model confidence is hidden or kept in diagnostics, not displayed as the main progress score.
- [ ] SADify shows missing information.
- [ ] SADify asks clarification questions.
- [ ] SADify allows draft generation with visible assumptions.

## Agent Behavior Readiness

- [ ] SADify follows the standard first-response pattern.
- [ ] Low-confidence output is not presented as final truth.
- [ ] Assumptions are clearly labelled.
- [ ] Open questions are visible near the top.
- [ ] Problem severity labels are used consistently.
- [ ] Recommendation priority labels are used consistently.
- [ ] Same input through ADK-compatible path and app path produces consistent behavior.
- [ ] Model route shown in the app uses Google/Gemini unless a deliberate provider test is being recorded.

## Data And Wiki Readiness

- [ ] Canonical JSON validates.
- [ ] Knowledge items are created.
- [ ] Relationships are created with understandable labels.
- [ ] Source traceability is preserved.
- [ ] Wiki Markdown files are generated.
- [ ] Wiki notes use YAML frontmatter.
- [ ] Wiki notes use `[[wiki links]]`.
- [ ] Wiki files are grouped by item type.
- [ ] Wiki verification prevents unsafe overwrite.
- [ ] Project owner approval works for wiki promotion.

## Export Readiness

- [ ] Google Docs export works.
- [ ] PDF export works.
- [ ] DOCX export works.
- [ ] Wiki Markdown export works.
- [ ] Export records are saved.
- [ ] Export links open successfully.
- [ ] Failed exports show understandable errors.

## Google Cloud Readiness

- [ ] Correct project is selected: `sadify`.
- [ ] Billing budget guardrail exists.
- [ ] Smaller project-only prototype budget exists or heavy model/deploy testing is explicitly approved.
- [ ] Required APIs are enabled.
- [ ] Avoid-list services are not used.
- [ ] Service account exists: `sadify-agent-sa@sadify.iam.gserviceaccount.com`.
- [ ] IAM roles are not broader than necessary.
- [ ] Firestore is available.
- [ ] Drive folder is shared with the service account.
- [ ] Cloud Run is deployed only after local checkpoints pass.

## Cost And Billing Readiness

- [ ] Current billing/budget context is understood.
- [ ] No unnecessary services are running.
- [ ] Cloud Run service can be deleted after demo if needed.
- [ ] Artifact Registry images can be cleaned up.
- [ ] Test files in Drive can be removed.
- [ ] Cost tracking table in the runbook is up to date.

## Demo Recording Readiness

- [ ] Demo scenario is chosen and understandable.
- [ ] Demo input is prepared.
- [ ] Expected output is prepared.
- [ ] Real output has been tested.
- [ ] Critical errors are resolved.
- [ ] Logs show no critical runtime errors.
- [ ] Browser console has no unexpected errors.
- [ ] Network/API failures are handled cleanly.
- [ ] Demo flow can complete within 3-5 minutes.

## Evidence Required Before Recording

Collect evidence before recording:

- working local app screenshot
- generated SAD preview
- exported Google Doc link
- exported PDF file
- exported DOCX file
- generated wiki Markdown folder
- Firestore record screenshot or export
- logs showing no critical errors
- budget alert screenshot
- Cloud Run URL if deployed
- Cloud Run logs if deployed

## Internal Criteria Coverage Check

The demo should naturally show:

- technical implementation
- business case
- innovation and creativity
- clear presentation

Do not make the video feel like a scoring checklist. The story should remain human and problem-first.

## Stop Conditions

Do not record the final demo if:

- SADify hides assumptions
- question-area status or overall readiness is missing
- wiki generation is broken
- exports are not traceable to versions
- Google Cloud billing status is unclear
- runtime errors appear during the main flow
- the chosen scenario is too vague to show value
