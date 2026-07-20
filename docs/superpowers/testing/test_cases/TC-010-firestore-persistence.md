# TC-010 Firestore Persistence

Date Created: 2026-04-30
Last Updated: 2026-05-06
Status: Passed

## Purpose

Verify that validated canonical data can be saved to and read from Firestore.

## Traceability Sources

- `docs/superpowers/development/05_development_workflow.md` - Checkpoint 6
- `docs/superpowers/development/04_google_cloud_setup_runbook.md` - Firestore setup
- `docs/superpowers/development/03_data_model_and_output_schema.md` - Firestore model
- `docs/superpowers/testing/test_case_index.md`

## Inputs

Validated project, knowledge item, relationship, source, SAD version, and export records.

## Preconditions

Firestore database exists in Google Cloud, and the local persistence service layer exists.

This checkpoint was run in local-first mode with an in-memory Firestore-shaped fake client. No real Firestore cloud smoke write was run in this checkpoint.

## Steps

1. Save project document.
2. Save subcollection records.
3. Read records back.
4. Compare saved and loaded data.

## Expected Output

- records save successfully
- records read successfully
- loaded data matches expected schema
- errors are logged and shown clearly

## Real Output

- `FirestoreRepository` can save and read `ProjectRecord` at `projects/{project_id}`.
- `FirestoreRepository` can save and read `SourceRecord` at `projects/{project_id}/sources/{source_id}`.
- `FirestoreRepository` can save and read `KnowledgeItemRecord` at `projects/{project_id}/knowledge_items/{item_id}`.
- `FirestoreRepository` can save and read `RelationshipRecord` at `projects/{project_id}/relationships/{relationship_id}`.
- `FirestoreRepository` can save and read `SadVersionRecord` at `projects/{project_id}/sad_versions/{sad_version_id}`.
- `FirestoreRepository` can save and read `ExportRecord` at `projects/{project_id}/exports/{export_id}`.
- Save methods accept either Pydantic model instances or dictionaries and validate before writing.
- Invalid canonical data fails before the fake client storage is mutated.
- Invalid project document paths fail before subcollection writes.
- Missing documents return `None`.
- Client write/read failures are logged through `sadify.firestore` and raised as `FirestorePersistenceError` with plain action-specific messages.

## Differences / Issues

- This checkpoint proves local repository behavior and Firestore path mapping without a real cloud write.
- A real Firestore smoke test remains optional and should be run only after explicit approval because it uses cloud resources.
- No Streamlit UI change is included yet.

## Evidence

```text
Command: .\.venv\Scripts\pytest.exe tests\test_firestore_persistence.py
Result: 9 passed in 0.45s
```

```text
Command: .\.venv\Scripts\pytest.exe
Result: 56 passed in 7.46s
```

## Decision

Passed for Checkpoint 6 local-first Firestore persistence.

Before relying on production Firestore, run one explicit cloud smoke test against project `sadify` and clean up the test record.

Continue to Checkpoint 7: completeness + confidence scoring.
