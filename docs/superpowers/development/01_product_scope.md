# SADify Product Scope

Date: 2026-04-30  
Last updated: 2026-05-18

## Purpose

This document defines what SADify is, what the MVP should include, what it should avoid, and how the product can grow later without weakening the core user value.

## Traceability Sources

This scope should be verified against:

- `docs/Google for Startups AI Agents Challenge.md`
- `docs/Google Cloud Hackathon (Req -_ SAD agent).md`
- `docs/superpowers/research/2026-05-02-track-1-resource-link-analysis.md`
- `docs/superpowers/development/00_development_index.md`
- `docs/superpowers/development/02_agent_behavior_contract.md`
- `docs/superpowers/development/14_qna_workflow_refinement.md`
- `docs/superpowers/development/06_demo_script_and_acceptance_checklist.md`

If product scope changes, update the development index, agent behavior contract, demo checklist, and test case index.

## Product Definition

SADify is an AI system analyst for production and on-site operations teams.

It helps users describe messy business or operational requirements in natural language, then turns those inputs into clarified, structured, developer-ready System Analysis and Design output.

SADify should not behave like a generic chatbot that immediately jumps to a solution. It should guide the user through requirement clarification, show what information is missing, track question-area status and overall readiness, and then generate a SAD draft that IT teams can use.

## Product Scope

SADify is designed as a generic core for production and operations requirement translation.

The product should not be locked to one domain such as warehouse, manufacturing, agriculture, plantation, HR operations, or maintenance. Those domains can become examples, templates, or future specializations.

The current MVP should prove that the method works:

```text
messy operational problem
  -> clarification
  -> draft-ready clarification and SAD draft
  -> deeper IT-readiness refinement
  -> stronger structured SAD revision
  -> exportable document
```

## Demo Case Position

The demo case is intentionally undecided for now.

The project may later use an agriculture or plantation-inspired scenario because that is close to the current project inspiration. However, the documentation should not lock SADify to a specific demo domain yet.

The demo scenario should be chosen later based on which case best shows:

- real operational pain
- non-technical user input
- missing requirement details
- business rules
- edge cases
- useful developer-ready output

## Target Users

The primary users are production and on-site operations staff.

These users understand real field or operational problems, but they may not naturally describe those problems in IT-friendly terms such as workflows, actors, data entities, approval rules, edge cases, system constraints, and non-functional requirements.

Examples of target users:

- operations staff
- production supervisors
- on-site team leads
- field coordinators
- department users requesting internal systems
- non-technical business users who need IT support

## Output Receivers

The main receiver is the IT or development team.

SADify output should help developers quickly understand:

- what problem to solve
- who is involved
- what workflow exists today
- what the proposed workflow should be
- what data is needed
- what business rules apply
- what edge cases must be handled
- what tasks can be built

Business management is a secondary receiver.

The SAD output should also be readable enough for managers to review scope, approve direction, and understand why a system is needed.

## MVP Scope

The MVP should include:

- natural language requirement input
- normal business-file input support
- clarification questions
- missing information list
- requirement completeness level
- internal confidence diagnostics
- structured SAD draft generation
- functional requirements
- non-functional requirements
- business rules
- edge cases
- data entity suggestions
- developer task breakdown
- saved project/session history
- SAD version history
- connected requirement knowledge base
- Obsidian-compatible Markdown wiki export
- Google Docs export
- PDF export
- DOCX export
- one lightweight cross-domain completeness checklist
- two explicit readiness layers:
  - draft readiness for a coherent first SAD draft
  - IT readiness for a more implementation-ready revision

The lightweight completeness checklist should cover general requirement categories:

```text
Actors
Workflow
Data fields
Approval rules
Reports
Exceptions
Permissions
Non-functional constraints
```

## Input Scope

SADify should support normal business files in the MVP because production and operations users often keep requirements, SOPs, records, and issue notes in common office formats.

MVP input support:

- typed or pasted text
- Markdown notes
- TXT files
- PDF files
- DOCX files
- XLSX files
- CSV files

Image input should be treated as the first priority potential development after the business-file MVP.

Image support may become free with limits or part of a paid tier depending on future product decisions. The exact limit should be decided later. Possible limits include:

- number of images per project
- number of files per project
- file size
- monthly upload volume

Future complex input support may include:

- scanned multi-page documents
- handwritten notes
- audio or voice input
- video input
- Google Drive folder import
- email or chat thread import

## Completeness And Confidence Behavior

The MVP should be guided but flexible.

SADify should show the user:

- what information has been captured
- what important information is missing
- clarification questions to improve the requirement
- question-area word statuses for relevant requirement areas
- overall draft readiness in user-friendly language

SADify should recommend clarifying missing information before generating the final SAD.

However, the user should still be allowed to generate a draft SAD if they choose. In that case, the output should clearly mark assumptions, risks, and open questions.

This avoids blocking the user during a demo while still showing SADify's main differentiator.

MVP readiness uses two layers:

```text
Layer 1: Draft-ready
  Enough confirmed information to generate a coherent first SAD draft.

Layer 2: IT-ready
  Deeper implementation detail after the draft exists, so the revised SAD is
  more suitable for real IT planning.
```

Layer 1 should be implemented first so the product can deliver value early.
Layer 2 is still part of the MVP and must be completed before the MVP is treated
as finished.

AI confidence is useful internally, but it should not be a primary user-facing number in the Q&A panel. If shown, it belongs in a collapsed diagnostic view or as a small non-numeric badge.

The questionnaire should work category by category. SADify should stay inside the active category until the current category's required slots are covered or explicitly deferred, then move to the next unclear category in frozen plan order. The top-level display should be a stable question-area status line, not a surprise question menu.

## MVP Success Criteria

The MVP is successful when a user can:

1. Enter a messy production or operations requirement.
2. See missing information, question-area status, and overall readiness.
3. Answer clarification questions.
4. Generate a coherent draft-ready SAD.
5. Continue into deeper IT-readiness refinement on the same project.
6. Generate a stronger SAD revision after the IT-readiness pass.
7. See developer-readable sections and task breakdown.
8. Export the generated SAD to normal business formats: Google Docs, PDF, and DOCX.
9. Generate connected Markdown wiki files that can be opened later in Obsidian to view requirement relationships.

GitHub Issues export is not required for MVP success.

## Potential Stretch Scope

If time is sufficient, SADify can optionally create GitHub Issues from the developer task breakdown.

This would make the demo feel more agentic because SADify would not only generate documentation, but also start the development workflow.

This is a stretch feature because it adds authentication, API setup, and demo risk. Standard SAD exports and wiki generation should work first.

## Not MVP

The MVP should exclude:

- multi-user collaboration
- complex login or authentication
- full project management system
- many domain-specific templates
- advanced diagram editor
- Jira integration
- voice input
- mobile app

These features are excluded because they are useful, but not necessary to prove the core SADify workflow. Adding them too early would distract from the main product risk: whether SADify can consistently clarify and structure requirements better than a generic chatbot.

## Future Product Direction

Core usefulness should remain available in the base product.

Features that make SADify trustworthy for developers should not be treated as artificial premium locks. This includes:

- saved project history
- SAD version history
- basic export
- completeness score
- missing information list
- clarification questions

Paid features should be based on scale, collaboration, customization, automation, and enterprise needs.

Potential future paid or premium features:

| Future Feature | Why It Can Be Premium |
| --- | --- |
| More projects or storage | Users pay when usage grows |
| Longer retention | Useful for teams with many past requirements |
| Multi-user collaboration | Teams need comments, review, and shared workspaces |
| Approval workflow | Useful for business sign-off and IT review |
| Full project management layer | Can manage tasks after SAD generation |
| Advanced diagram editor | Valuable for DFD, ERD, and workflow refinement |
| Voice input | Helpful for field or on-site users |
| Advanced domain templates | Paid industry packs for plantation, manufacturing, warehouse, maintenance, HR operations, and procurement |
| GitHub or Jira integrations | Useful for teams that want development workflow automation |
| Organization workspace | Useful for companies with multiple departments |
| Enterprise controls | SSO, audit logs, admin controls, custom standards, and compliance needs |

## Product Principle

SADify should earn trust by helping users produce clearer requirements, not by hiding essential development value behind payment.

The MVP should focus on one clear promise:

> SADify helps non-technical operations users turn real field problems into clarified, complete, developer-ready SAD documents.
