# SADify Data Model And Output Schema

Date: 2026-04-30  
Last updated: 2026-06-19

## Purpose

This document defines the MVP data model, canonical structured output, wiki knowledge model, versioning rules, verification rules, and export records for SADify.

The schema should be practical enough to build the first version while leaving room for future collaboration, richer file extraction, and premium features.

## Traceability Sources

This schema document should be verified against:

- `docs/superpowers/development/01_product_scope.md`
- `docs/superpowers/development/02_agent_behavior_contract.md`
- `docs/superpowers/development/14_qna_workflow_refinement.md`
- `docs/superpowers/diagrams/2026-04-29-sadify-architecture.md`
- `docs/superpowers/development/05_development_workflow.md`
- `docs/superpowers/testing/test_case_index.md`

If the schema changes, update the architecture diagram, workflow checkpoints, and related test cases.

## Data Model Principles

SADify should use four layers:

```text
Canonical data layer: Firestore structured JSON
Human knowledge layer: Obsidian-compatible Markdown wiki
Document deliverable layer: Google Docs, PDF, DOCX
Preview layer: Markdown/HTML rendered in the app
```

The source of truth is always the canonical structured data in Firestore.

Rendered Markdown, wiki files, Google Docs, PDF, and DOCX files are generated artifacts. They must be traceable back to the canonical data and version that produced them.

## Project-Based Firestore Shape

The MVP should be project-based.

A project can contain multiple related requirements. These requirements can link to shared actors, entities, workflows, reports, decisions, and sources.

Recommended Firestore shape:

```text
projects/{project_id}
projects/{project_id}/knowledge_items/{item_id}
projects/{project_id}/relationships/{relationship_id}
projects/{project_id}/sources/{source_id}
projects/{project_id}/sad_versions/{sad_version_id}
projects/{project_id}/exports/{export_id}
projects/{project_id}/knowledge_item_versions/{version_id}
```

Future optional shape:

```text
projects/{project_id}/memory_versions/{memory_version_id}
projects/{project_id}/source_extraction_snapshots/{snapshot_id}
projects/{project_id}/collaborators/{collaborator_id}
```

## Prototype-To-MVP Data Additions

The proper web-app MVP adds guest mode, signed-in users, Drive repo grants, and change-set review on top of the existing project model.

Additional MVP collections:

```text
guest_drafts/{guest_draft_id}
guest_drafts/{guest_draft_id}/events/{event_id}

users/{firebase_uid}
users/{firebase_uid}/drive_grants/{grant_id}

projects/{project_id}/answers/{answer_id}
projects/{project_id}/change_sets/{change_set_id}
projects/{project_id}/questionnaire_state/{state_id}
```

Guest migration rule:

```text
The guest draft remains intact.
When the user signs in and approves migration, SADify creates a signed-in project copy,
links it to the original guest draft, and marks the guest draft as migrated.
```

Drive grant rule:

```text
Firestore stores grant metadata only.
Refresh tokens must be stored in a secure backend token store such as Secret Manager
or another explicitly approved store.
```

Change-set rule:

```text
Before saving to Drive, SADify shows a user-friendly change summary with paths:
- SAD/SAD-v003
- Wiki/workflows/stock-movement.md
- Sources/warehouse-stock-movement.txt

Technical IDs, schema records, and link details stay hidden unless expanded.
```

Questionnaire-state rule:

```text
The Q&A flow should track a stable questionnaire plan: canonical categories,
visible question-area status, required slots, overall readiness, active category,
answered questions, uncertainty answers, assumptions, and open questions
separately from model confidence. The UI should use this state to stay inside a
category until its required slots are covered, deferred, or marked not
applicable by quote-validated evidence.
```

Implementation note:

```text
MVP-09.1 / TC-021R added local questionnaire state on the analysis response.
MVP-09.2 / TC-021S is now refining that state so category order, slot coverage,
and question progression are stable enough for MVP acceptance.
MVP-09.4 / TC-021U added a safe SAD preview fallback so invalid Gemini preview
formatting no longer returns 502.
MVP-09.5 / TC-021V keeps the base business request clean and stops appended
transcript text from leaking into fallback SAD output.
MVP-09.6 / TC-021W made fallback SAD output business-facing in automated checks:
synthesized sections, normalized amendment language, coherent readiness, and
debug details outside the normal document view.
MVP-09.7 / TC-021X improved evidence-first workshop behavior locally.
MVP-09.8 / TC-021Y must generalize the questionnaire and SAD preview handoff:
domain-aware evidence facts, fact-bearing answer choices, clean user-facing
source references, stale-preview reset, and evidence-based SAD section
composition across tuition, workshop, and generic operational requests.
TC-028 replaces keyword/phrase readiness with AI-judged per-slot evidence that
quotes the actual request/source material. The backend validates quotes,
downgrades ungrounded verdicts, aggregates readiness over applicable required
slots, and derives confidence from the validated evidence mix. SAD synthesis
composition is the next cycle after TC-028 verification.
Durable Firestore questionnaire_state persistence is still a later checkpoint.
```

## Project Document

Path:

```text
projects/{project_id}
```

Example:

```json
{
  "project_id": "PROJ-001",
  "slug": "plantation-field-operations",
  "title": "Plantation Field Operations",
  "status": "planning",
  "owner_id": "local-user",
  "owner_name": "Project Owner",
  "created_at": "2026-04-30T00:00:00Z",
  "updated_at": "2026-04-30T00:00:00Z",
  "region": "asia-southeast1",
  "project_memory": {
    "summary": "The project captures operational requirements that need to be clarified and converted into a SAD.",
    "key_actors": [],
    "key_entities": [],
    "key_workflows": [],
    "known_gaps": [],
    "last_updated_from_sad_version_id": null,
    "last_updated_at": "2026-04-30T00:00:00Z"
  },
  "drive": {
    "root_folder_id": null,
    "sad_folder_id": null,
    "wiki_folder_id": null
  }
}
```

## Knowledge Items

Path:

```text
projects/{project_id}/knowledge_items/{item_id}
```

Use one unified graph-style collection for all wiki nodes.

MVP item types:

```text
requirement
entity
workflow
decision
actor
report
source
```

SADify should create `actor` and `report` nodes only when clearly detected. This prevents the wiki from becoming noisy.

Use both stable prefix IDs and readable slugs.

Example IDs:

```text
REQ-001
ENT-001
WF-001
DEC-001
ACT-001
REP-001
SRC-001
```

Example knowledge item:

```json
{
  "item_id": "REQ-001",
  "item_type": "requirement",
  "slug": "fertilizer-application-logging",
  "title": "Fertilizer Application Logging",
  "status": "draft",
  "summary": "Field staff need to record fertilizer application by block, date, worker, and fertilizer type.",
  "completeness_score": 72,
  "confidence_label": "medium",
  "problem_severity": "high",
  "recommendation_priority": "must_have",
  "source_ids": ["SRC-001"],
  "relationship_ids": ["REL-001", "REL-002"],
  "open_questions": [
    {
      "question_id": "Q-001",
      "label": "[OPEN QUESTION]",
      "severity": "high",
      "question": "Who verifies the fertilizer record?"
    }
  ],
  "assumptions": [
    {
      "assumption_id": "ASM-001",
      "label": "[ASSUMPTION]",
      "text": "Field supervisors are assumed to review fertilizer records."
    }
  ],
  "markdown_current": null,
  "markdown_draft": null,
  "markdown_status": "not_generated",
  "pending_change_summary": null,
  "verification_result": null,
  "drive_file": {
    "file_name": null,
    "drive_file_id": null,
    "url": null
  },
  "created_at": "2026-04-30T00:00:00Z",
  "updated_at": "2026-04-30T00:00:00Z"
}
```

## Requirement Cards

SADify should not create a full SAD per requirement in the MVP.

The main SAD is project-level. Requirement-level output should be a requirement card or wiki note.

A requirement card should include:

- ID
- title
- summary
- source traceability
- related actors
- related entities
- related workflows
- completeness score
- confidence label
- open questions
- assumptions
- acceptance criteria, if available
- linked requirements

The project SAD should combine related requirement cards into a coherent system-level document.

## Questionnaire State

The guided Q&A flow needs its own state so overall readiness and visible question-area statuses do not depend on whichever Gemini response was returned most recently.

Path:

```text
projects/{project_id}/questionnaire_state/{state_id}
```

MVP fields should include:

```json
{
  "state_id": "QSTATE-001",
  "project_id": "PROJ-001",
  "active_category_id": "workflow",
  "draft_readiness": {
    "label": "Early draft",
    "score": 25
  },
  "categories": [
    {
      "category_id": "workflow",
      "label": "Workflow steps",
      "status": "in_progress",
      "display_order": 3,
      "visibility": "main",
      "slots": [
        {
          "slot_id": "normal_flow",
          "label": "Normal flow captured",
          "required": true,
          "status": "covered",
          "evidence_strength": "strong",
          "applicable": true
        },
        {
          "slot_id": "exception_path",
          "label": "Important exception path captured",
          "required": true,
          "status": "open",
          "evidence_strength": "none",
          "applicable": true
        }
      ],
      "is_relevant": true,
      "is_visible": true
    }
  ],
  "current_question_id": "Q-003",
  "updated_at": "2026-05-14T00:00:00Z"
}
```

Normal Q&A UI should show category `status` as words and reserve the percentage display for overall `draft_readiness.score`. SAD preview may show a separate IT readiness percentage after the user generates a preview.

MVP readiness model:

```text
draft_readiness:
  Enough confirmed facts for a coherent first SAD draft.

it_readiness:
  Deeper implementation-readiness assessment for a stronger SAD revision.
```

Layer 1 should be completed first so the user can obtain a useful draft early.
Layer 2 remains part of the MVP and should be stored against the same project
rather than as a disconnected second document flow.

Category status values:

```text
needed
in_progress
ready
needs_later_confirmation
```

Category visibility values:

```text
main
already_understood
completed
suggested
not_applicable
```

Slot evidence values:

```text
evidence_strength: none | partial | strong
applicable: true | false
```

Model-returned `SlotEvidence` records:

```json
{
  "category_id": "workflow_steps",
  "slot_id": "normal_flow",
  "applicability": "applicable",
  "strength": "strong",
  "evidence_quote": "Staff submit a request when a machine has an issue.",
  "rationale": "The normal intake step is stated directly in the request."
}
```

Validation rule:

```text
Partial or strong verdicts must cite an evidence_quote found in the typed
business request, uploaded source context, or saved Q&A answers. If the quote is
missing or not found, the backend downgrades the verdict one level before
readiness is calculated. not_applicable verdicts are excluded from the required
slot denominator and appear in the UI under Not relevant to this project.
```

Question records should include:

```json
{
  "question_id": "Q-003",
  "category_id": "workflow",
  "slot_id": "exception_path",
  "text": "What happens if the patient leaves before payment?",
  "selection_mode": "single",
  "choices": [],
  "status": "active",
  "source_references": ["Business Request"]
}
```

Answer records should include:

```json
{
  "answer_id": "ANS-003",
  "question_id": "Q-003",
  "category_id": "workflow",
  "slot_id": "exception_path",
  "selected_choice_ids": ["keep_bill_open"],
  "amendment_text": "",
  "is_uncertain": false,
  "creates_assumption": false,
  "keeps_open_question": false,
  "source": "user",
  "created_at": "2026-05-14T00:00:00Z"
}
```

`I'm not sure` should set `is_uncertain` and either create a marked assumption or keep an open question after the suggested-default follow-up.

Clean SAD handoff rule:

```text
The base requirement text is canonical user input and must remain clean.

Allowed:
  requirement_text = original business request
  questionnaire.answers = structured confirmed answers
  internal_prompt_history = Previous question / Previous answer / Previous readiness

Not allowed:
  rendering Previous question / Previous answer / Previous readiness as part of
  the business request or SAD body
```

The SAD preview, fallback preview, wiki update, and final document generation
must consume the clean request plus structured answers. Appended prompt history
is only internal model context and is never a source-of-truth document field.

User-facing SAD draft rule:

```text
The normal SAD preview must not expose fallback/debug implementation details as
document content. If local fallback composition is used, the saved preview still
needs a professional SAD title, synthesized sections, normalized user amendment
language, and coherent draft-readiness wording. Diagnostics such as local
fallback path, repair failure, and raw model-formatting issues belong in
collapsed tracking details only.
```

Domain-aware evidence rule:

```text
Questionnaire answers and source references must not use internal slot IDs as
user-facing source labels. Internal slot IDs can guide plan coverage, but SAD
preview, wiki update, and final document generation should consume clean
business facts and business source labels.
```

## Relationships

Path:

```text
projects/{project_id}/relationships/{relationship_id}
```

Relationships should be stored as dedicated documents because the wiki graph is central to SADify.

Use understandable naming conventions.

Example:

```json
{
  "relationship_id": "REL-001",
  "source_item_id": "REQ-001",
  "source_item_title": "Fertilizer Application Logging",
  "target_item_id": "ENT-002",
  "target_item_title": "Field Block",
  "relationship_type": "uses_entity",
  "relationship_label": "Requirement uses entity",
  "explanation": "Fertilizer application records are captured by field block.",
  "confidence_label": "high",
  "evidence_source_ids": ["SRC-001"],
  "created_at": "2026-04-30T00:00:00Z",
  "updated_at": "2026-04-30T00:00:00Z"
}
```

Suggested relationship types:

```text
relates_to
depends_on
conflicts_with
uses_entity
performed_by_actor
produces_report
uses_workflow
supported_by_source
records_decision
```

## Sources

Sources are stored in two places:

```text
projects/{project_id}/sources/{source_id}
projects/{project_id}/knowledge_items/{source_item_id}
```

The `sources` collection stores file metadata and extraction state.

The `source` knowledge item exists so source files appear in the wiki graph.

Example source metadata:

```json
{
  "source_id": "SRC-001",
  "source_item_id": "SRC-001",
  "source_type": "xlsx",
  "original_file_name": "fertilizer_log_april.xlsx",
  "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "file_size_bytes": 204800,
  "drive_file_id": null,
  "extraction_status": "extracted",
  "extracted_text_preview": "Sheet April Records contains Block, Date, Fertilizer Type...",
  "extraction_summary": "The spreadsheet records fertilizer applications by field block and date.",
  "traceability_units": [
    {
      "unit_type": "sheet",
      "unit_name": "April Records",
      "columns": ["Block", "Date", "Fertilizer Type", "Worker"]
    }
  ],
  "created_at": "2026-04-30T00:00:00Z",
  "updated_at": "2026-04-30T00:00:00Z"
}
```

Future improvement:

```text
source_extraction_snapshots
```

These snapshots can store how raw source content became extracted requirement knowledge, then compacted project memory, then final SAD output. This can make the agent smarter and more auditable later.

## SAD Versions

Path:

```text
projects/{project_id}/sad_versions/{sad_version_id}
```

SAD versions are project-level in the MVP.

Each SAD version should store both structured sections and rendered Markdown.

Principle:

```text
Structured JSON is the source of truth.
Rendered Markdown is a human-readable generated cache.
Google Docs/PDF/DOCX exports are generated artifacts.
Wiki Markdown files are generated linked notes.
```

Example:

```json
{
  "sad_version_id": "SAD-001",
  "version_number": 1,
  "status": "draft",
  "created_at": "2026-04-30T00:00:00Z",
  "created_by": "local-user",
  "completeness_score": 78,
  "confidence_label": "medium",
  "source_requirement_ids": ["REQ-001", "REQ-002"],
  "source_knowledge_item_ids": ["REQ-001", "REQ-002", "ENT-001", "ACT-001"],
  "structured_sections": {
    "summary": {},
    "critical_gaps": [],
    "functional_requirements": [],
    "non_functional_requirements": [],
    "business_rules": [],
    "edge_cases": [],
    "data_entities": [],
    "workflows": [],
    "developer_tasks": [],
    "assumptions": [],
    "open_questions": [],
    "source_traceability": []
  },
  "rendered_markdown": "# System Analysis and Design\n\n...",
  "verification_result": {
    "schema_validation": {
      "status": "passed",
      "issues": []
    },
    "sad_quality_check": {
      "status": "passed",
      "issues": []
    }
  }
}
```

## Knowledge Item Versions

Path:

```text
projects/{project_id}/knowledge_item_versions/{version_id}
```

The MVP should keep version history for:

- SAD documents
- knowledge items

Example:

```json
{
  "version_id": "KIV-001",
  "item_id": "REQ-001",
  "item_type": "requirement",
  "version_number": 1,
  "change_type": "created",
  "change_summary": "Initial requirement card generated from uploaded spreadsheet.",
  "snapshot": {
    "title": "Fertilizer Application Logging",
    "summary": "Field staff need to record fertilizer application by block, date, worker, and fertilizer type.",
    "completeness_score": 72,
    "confidence_label": "medium"
  },
  "markdown_current": "# Fertilizer Application Logging\n\n...",
  "created_at": "2026-04-30T00:00:00Z",
  "created_by": "local-user"
}
```

## Wiki Markdown Storage And Verification

Wiki Markdown notes are generated from canonical knowledge items.

They must not overwrite the latest verified note without verification and approval.

MVP fields on each knowledge item:

```json
{
  "markdown_current": "latest verified Markdown note",
  "markdown_draft": "new generated Markdown note waiting for verification",
  "markdown_status": "pending_human_approval",
  "pending_change_summary": "Updated related entities and added two open questions.",
  "verification_result": {
    "rule_based": {
      "status": "passed",
      "issues": []
    },
    "gemini_quality": {
      "status": "passed",
      "issues": []
    },
    "human_review": {
      "status": "pending",
      "reviewer_role": "owner",
      "reviewed_by": null,
      "reviewed_at": null
    }
  }
}
```

Allowed `markdown_status` values:

```text
not_generated
draft
rule_failed
quality_failed
pending_human_approval
verified
rejected
```

MVP verification flow:

```text
1. Generate markdown_draft from canonical JSON.
2. Run rule-based structural checks.
3. Run Gemini quality check.
4. Show pending change to project owner.
5. Project owner approves or rejects.
6. Promote markdown_draft to markdown_current only after required checks and approval pass.
```

MVP human approval:

```text
project owner only
```

Future approval scaling:

```text
collaborators
production reviewer
IT reviewer
manager or scope approver
```

## Verification By Artifact Type

| Artifact Type | MVP Verification | Purpose |
| --- | --- | --- |
| Canonical JSON | Strict schema validation and required field checks | Protect source of truth |
| Wiki Markdown | Rule-based check + Gemini quality check + project owner approval | Prevent broken graph links and unsafe overwrites |
| SAD document draft | Structured section validation, visible assumptions, visible open questions | Keep SAD usable and transparent |
| Google Docs/PDF/DOCX export | Confirm file generated, correct version linked, URL saved | Track final deliverables |
| Project memory | Generated from latest canonical data and linked to source version | Keep compact agent context reliable |
| Source extraction | Basic extraction status and source metadata saved | Ensure input is traceable |

## Wiki File Structure In Google Drive

Generated wiki Markdown files should be grouped by item type.

Recommended Drive structure:

```text
Google Drive/
  SADify Generated Docs/
    Project Name/
      sad/
        SAD-v1.google_doc
        SAD-v1.pdf
        SAD-v1.docx
      wiki/
        requirements/
          REQ-001-fertilizer-application-logging.md
        entities/
          ENT-001-worker.md
          ENT-002-field-block.md
        workflows/
          WF-001-fertilizer-recording.md
        decisions/
          DEC-001-offline-mode-needed.md
        actors/
          ACT-001-field-supervisor.md
        reports/
          REP-001-daily-fertilizer-usage-report.md
        sources/
          SRC-001-uploaded-sop.md
```

Obsidian itself is optional. SADify only needs to generate Obsidian-compatible Markdown files with YAML frontmatter and `[[wiki links]]`.

## Wiki Markdown Note Shape

Example:

```markdown
---
id: REQ-001
type: requirement
slug: fertilizer-application-logging
status: draft
completeness: 72
confidence: medium
sources:
  - SRC-001
related:
  - REQ-002
shared_entities:
  - ENT-001
  - ENT-002
---

# Fertilizer Application Logging

## Summary
Field staff need to record fertilizer application by block, date, worker, and fertilizer type.

## Related Notes
- [[REQ-002-worker-attendance]]
- [[ENT-001-worker]]
- [[ENT-002-field-block]]
- [[WF-001-fertilizer-recording]]

## Open Questions
- [HIGH] Who verifies the fertilizer record?
- [MEDIUM] Is offline entry required in the field?

## Sources
- [[SRC-001-uploaded-sop]]
```

## Export Records

Path:

```text
projects/{project_id}/exports/{export_id}
```

Track detailed export records.

Example:

```json
{
  "export_id": "EXP-001",
  "export_type": "google_doc",
  "source_sad_version_id": "SAD-001",
  "source_knowledge_item_version_ids": ["KIV-001", "KIV-002"],
  "file_name": "SAD-v1-plantation-field-operations",
  "drive_file_id": "drive-file-id",
  "url": "https://docs.google.com/document/d/...",
  "created_at": "2026-04-30T00:00:00Z",
  "created_by": "local-user",
  "status": "success",
  "error_message": null
}
```

Use `source_sad_version_id` for SAD document exports.

Use `source_knowledge_item_version_ids` for wiki Markdown exports or any export that depends on connected knowledge-item notes.

Checkpoint 12 local-first export preparation can create successful local artifacts before Drive upload exists. In that state:

```text
status: success
drive_file_id: null
url: null
```

Drive IDs and URLs are filled only after the later Google Drive/Docs connector uploads or converts the artifact.

Allowed export types:

```text
google_doc
pdf
docx
wiki_markdown
```

## Project Memory

Current project memory should live inside the project document for MVP.

Future memory versions can live here:

```text
projects/{project_id}/memory_versions/{memory_version_id}
```

Example project memory:

```json
{
  "summary": "Plantation operations requirements are being clarified for field work tracking.",
  "key_actors": ["Field Supervisor", "Worker", "Manager"],
  "key_entities": ["Field Block", "Task", "Attendance"],
  "key_workflows": ["Fertilizer Recording Workflow"],
  "known_gaps": ["Approval flow unclear", "Offline support not confirmed"],
  "last_updated_from_sad_version_id": "SAD-003",
  "last_updated_at": "2026-04-30T00:00:00Z"
}
```

Project memory lets the agent load compacted project context quickly instead of reading every file or version every time.

## GitHub Issue Sets

Prepared GitHub issue sets are stored in the `github_issue_sets` collection. The ownership key is `(grant_id, project_id, save_id)`; `preview_id` is metadata and is not an authorization key.

```json
{
  "grant_id": "DG-000001",
  "project_id": "PR-000001",
  "save_id": "SV-000001",
  "preview_id": "SP-000001",
  "owner_uid": "firebase-uid-001",
  "repo": "octocat/sadify-demo",
  "status": "prepared",
  "issues": [
    {
      "marker": "<!-- sadify-github-issue:PR-000001:SV-000001:0 -->",
      "title": "Implement approval workflow",
      "body": "Source-grounded implementation details and marker.",
      "labels": ["sadify"]
    }
  ],
  "created_at": "2026-06-19T00:00:00Z",
  "updated_at": "2026-06-19T00:00:00Z"
}
```

`create_if_absent` preserves the first set and its repository. Relaunch uses that exact stored set. Project history exposes only `has_github_issue_set`; issue bodies are not copied into history responses. Project deletion removes issue sets before deleting the project record, while remote GitHub issues remain untouched.

## Future Extensions

Future schema improvements:

- source extraction snapshots
- exact line/cell/page traceability
- image source nodes
- audio/video transcript nodes
- collaborator roles
- team approval workflow
- memory version history
- billing or plan-limit records
- download/export usage statistics
