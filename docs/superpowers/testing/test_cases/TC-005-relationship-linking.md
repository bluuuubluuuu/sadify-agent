# TC-005 Relationship Linking

Date Created: 2026-04-30
Last Updated: 2026-05-06
Status: Passed

## Purpose

Verify that SADify can create understandable links between requirements, entities, workflows, actors, reports, decisions, and sources.

## Traceability Sources

- `docs/superpowers/development/05_development_workflow.md` - Checkpoint 8
- `docs/superpowers/development/03_data_model_and_output_schema.md` - knowledge item and relationship model
- `docs/superpowers/diagrams/2026-04-29-sadify-architecture.md` - wiki knowledge layer
- `docs/superpowers/testing/test_case_index.md`

## Inputs

Requirement context describing stock movement, actors, location/stock entities, workflow steps, dashboards/exports, role-based access, audit history, and attached source IDs.

## Preconditions

Knowledge item and relationship schemas exist. Checkpoint 7 local completeness/confidence scoring is available for requirement-item metadata.

## Steps

1. Build a local deterministic requirement graph from clear requirement text.
2. Validate generated knowledge items with canonical `KnowledgeItemRecord`.
3. Validate generated relationships with canonical `RelationshipRecord`.
4. Check duplicate/noisy actor nodes are minimized.
5. Check vague input creates only the requirement item.
6. Review relationship labels, explanations, confidence, and evidence source IDs.

## Expected Output

- relationships are created as dedicated canonical records
- relationship labels are understandable
- detected requirement, actor, entity, workflow, report, decision, and source nodes use stable canonical IDs
- duplicate/noisy nodes are minimized
- source evidence is preserved through `evidence_source_ids`
- vague input does not create misleading graph nodes

## Real Output

Passed with a local deterministic graph builder:

- `REQ-001` requirement item is created.
- clear actor nodes are created for operators, supervisors, managers, and workers when present.
- repeated people terms such as `Supervisors` and `supervisor` are deduplicated.
- entity nodes are created for clear stock/location signals.
- workflow, report, decision, and source nodes are linked through canonical relationship types.
- source IDs such as `SRC-001` and `SRC-002` are preserved on relationships.
- vague input such as `Need an app.` creates only the requirement item and no relationships.

## Differences / Issues

No blocking differences. This checkpoint is intentionally local and deterministic; live model-assisted relationship extraction, Firestore writes, and UI graph visualization remain later slices.

## Evidence

- `.\.venv\Scripts\pytest.exe tests\test_relationship_linking.py` -> 4 passed.
- `.\.venv\Scripts\pytest.exe tests\test_relationship_linking.py tests\test_canonical_schemas.py` -> 10 passed.
- `.\.venv\Scripts\pytest.exe` -> 66 passed.

## Decision

Passed. Continue to Checkpoint 9: wiki Markdown generation from canonical knowledge items and relationship records.
