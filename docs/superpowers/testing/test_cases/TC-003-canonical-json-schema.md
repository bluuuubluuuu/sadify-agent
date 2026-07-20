# TC-003 Canonical JSON Schema

Date Created: 2026-04-30
Last Updated: 2026-05-06
Status: Passed

## Purpose

Verify that canonical JSON structures validate before storage, rendering, or export.

## Traceability Sources

- `docs/superpowers/development/05_development_workflow.md` - Checkpoint 5
- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `docs/superpowers/testing/test_case_index.md`

## Inputs

Sample project, knowledge item, relationship, source, SAD version, and export records.

## Preconditions

Schema models and validators exist.

## Steps

1. Validate valid sample records.
2. Validate intentionally invalid records.
3. Review validation messages.

## Expected Output

- valid records pass
- invalid records fail
- error messages identify missing or invalid fields

## Real Output

- `ProjectRecord` validates the project document, project memory, Drive folder references, timestamp fields, and `PROJ-` project IDs.
- `SourceRecord` validates source metadata, file type, extraction status, file size, and `SRC-` source/source-item IDs.
- `KnowledgeItemRecord` validates MVP knowledge item types, matching item ID prefixes, source IDs, relationship IDs, open questions, assumptions, markdown status, and completeness score bounds.
- `RelationshipRecord` validates relationship IDs, supported relationship types, source/target knowledge item links, evidence source IDs, and confidence labels.
- `SadVersionRecord` validates SAD version IDs, version numbers, completeness score bounds, source requirement IDs, source knowledge item IDs, structured sections, rendered markdown, and verification result payloads.
- `ExportRecord` validates export IDs, export types, source SAD version IDs, knowledge-item version IDs, export status, and export metadata.
- Invalid records fail with Pydantic validation errors.
- `validation_error_messages()` returns plain field-level messages suitable for later diagnostics or UI display.

## Differences / Issues

- This checkpoint validates canonical records locally only.
- Firestore persistence is not included yet and remains Checkpoint 6.
- `KnowledgeItemVersionRecord` is not included in this slice. It is noted as a later version-history/wiki slice after the six TC-003 MVP records are stable.

## Evidence

```text
Command: .\.venv\Scripts\pytest.exe tests\test_canonical_schemas.py
Result: 6 passed in 0.48s
```

```text
Command: .\.venv\Scripts\pytest.exe
Result: 47 passed in 7.78s
```

## Decision

Passed for Checkpoint 5 canonical JSON schema validation.

Continue to Checkpoint 6: Firestore persistence.
