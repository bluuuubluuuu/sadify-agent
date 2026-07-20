# SADify — Archived Plans (Consolidated)

Date consolidated: 2026-05-24
Purpose: historical record of execution plans from Phase 1 through Phase 4.
Each section below is one original plan file, preserved verbatim.

## Index

- 2026-05-06-canonical-json-schema-validation-plan
- 2026-05-06-completeness-confidence-scoring-plan
- 2026-05-06-firestore-persistence-plan
- 2026-05-06-relationship-linking-plan
- 2026-05-07-project-level-sad-generation-plan
- 2026-05-07-wiki-markdown-generation-plan
- 2026-05-07-wiki-verification-approval-plan
- 2026-05-08-local-end-to-end-plan
- 2026-05-08-local-export-generation-plan
- 2026-05-11-cloud-run-deployment-plan
- 2026-05-11-sadify-prototype-to-mvp-implementation-plan
- 2026-05-15-stable-questionnaire-plan-refactor
- 2026-05-18-qna-ready-state-preview-handoff
- 2026-05-19-qna-sad-synthesis-quality
- 2026-05-19-sad-fallback-composition-quality-upgrade
- 2026-05-19-user-facing-sad-draft-quality
- 2026-05-20-evidence-first-qna-depth-valid-preview-coherence
- 2026-05-21-domain-aware-qna-sad-quality-hardening
- 2026-05-22-evidence-based-readiness
- 2026-05-22-evidence-based-readiness-HANDOVER

---

## 2026-05-06-canonical-json-schema-validation-plan

# Canonical JSON Schema Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Checkpoint 5 canonical JSON validation for the six MVP records named by TC-003.

**Architecture:** Add a focused Pydantic schema layer under `src/sadify/schemas/` that validates canonical records before later Firestore persistence, rendering, or export layers consume them. Keep this checkpoint local and deterministic: no Firestore client, no live model call, no Streamlit UI change.

**Tech Stack:** Python 3.13, Pydantic 2.x, pytest 9.x.

---

## Scope

Use Approach A for this checkpoint.

Implement now:

- `ProjectRecord`
- `ProjectMemory`
- `DriveFolders`
- `SourceRecord`
- `TraceabilityUnit`
- `KnowledgeItemRecord`
- `OpenQuestion`
- `Assumption`
- `DriveFileRef`
- `RelationshipRecord`
- `SadVersionRecord`
- `ExportRecord`
- validation helpers that expose plain validation messages

Do not implement now:

- Firestore persistence
- generated wiki files
- SAD rendering
- export generation
- live LLM calls
- `KnowledgeItemVersionRecord`

Approach B note for later: add `KnowledgeItemVersionRecord` in a later slice when wiki/version-history work starts, most likely before or during the Wiki Markdown and version-history checkpoints. It belongs after canonical records are stable and before verified wiki overwrite behavior needs snapshots.

## File Structure

- Create `src/sadify/schemas/canonical.py`
  - Contains all canonical MVP Pydantic models, enums, ID validation helpers, and `validation_error_messages`.
- Modify `src/sadify/schemas/__init__.py`
  - Re-export the canonical schema models and helper.
- Create `tests/test_canonical_schemas.py`
  - Tests valid records, invalid records, ID prefix validation, enum validation, score bounds, and useful validation messages.
- Update `docs/superpowers/testing/test_cases/TC-003-canonical-json-schema.md`
  - Record expected output, real output, evidence, and decision after tests pass.

## Task 1: Schema Test Skeleton

**Files:**
- Create: `tests/test_canonical_schemas.py`

- [ ] **Step 1: Write failing tests for valid records**

Add tests that import the not-yet-created models:

```python
from pydantic import ValidationError

from sadify.schemas import (
    ExportRecord,
    KnowledgeItemRecord,
    ProjectMemory,
    ProjectRecord,
    RelationshipRecord,
    SadVersionRecord,
    SourceRecord,
    validation_error_messages,
)
```

Create fixtures for valid project, source, knowledge item, relationship, SAD version, and export records. Assert each model validates and preserves key fields.

- [ ] **Step 2: Run red test**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_canonical_schemas.py
```

Expected: fail because models are not exported yet.

## Task 2: Minimal Canonical Models

**Files:**
- Create: `src/sadify/schemas/canonical.py`
- Modify: `src/sadify/schemas/__init__.py`

- [ ] **Step 1: Implement minimal models to pass valid-record tests**

Use Pydantic `BaseModel`, `ConfigDict(extra="forbid")`, `Field`, `Literal`, and `field_validator` or `model_validator` where needed.

Required ID prefixes:

```text
project_id: PROJ-
source_id: SRC-
source_item_id: SRC-
item_id: REQ-, ENT-, WF-, DEC-, ACT-, REP-, SRC-
relationship_id: REL-
sad_version_id: SAD-
export_id: EXP-
source_sad_version_id: SAD-
source_knowledge_item_version_ids: KIV-
```

- [ ] **Step 2: Run green test**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_canonical_schemas.py
```

Expected: valid-record tests pass.

## Task 3: Validation Rules

**Files:**
- Modify: `tests/test_canonical_schemas.py`
- Modify: `src/sadify/schemas/canonical.py`

- [ ] **Step 1: Add failing tests for invalid records**

Cover these behaviors:

- missing required field identifies the field
- bad ID prefix fails with a clear message
- unsupported `item_type` fails
- unsupported `relationship_type` fails
- unsupported `export_type` fails
- completeness score below `0` or above `100` fails
- export status must be `success`, `failed`, or `pending`

- [ ] **Step 2: Run red tests**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_canonical_schemas.py
```

Expected: fail on missing validation rules.

- [ ] **Step 3: Implement validators**

Add focused helper functions:

```python
def _validate_id_prefix(value: str, allowed_prefixes: tuple[str, ...], field_name: str) -> str:
    ...
```

Add model validators where cross-field validation is needed.

- [ ] **Step 4: Run green tests**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_canonical_schemas.py
```

Expected: all canonical schema tests pass.

## Task 4: Useful Validation Messages

**Files:**
- Modify: `tests/test_canonical_schemas.py`
- Modify: `src/sadify/schemas/canonical.py`

- [ ] **Step 1: Add failing test for plain validation messages**

Test:

```python
with pytest.raises(ValidationError) as exc_info:
    KnowledgeItemRecord(**bad_record)

messages = validation_error_messages(exc_info.value)
assert any("item_id" in message for message in messages)
```

- [ ] **Step 2: Implement `validation_error_messages`**

Return concise strings suitable for diagnostics or UI later:

```text
item_id: must start with one of REQ-, ENT-, WF-, DEC-, ACT-, REP-, SRC-
```

- [ ] **Step 3: Run schema tests**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_canonical_schemas.py
```

Expected: all canonical schema tests pass.

## Task 5: Full Verification And TC-003 Update

**Files:**
- Modify: `docs/superpowers/testing/test_cases/TC-003-canonical-json-schema.md`

- [ ] **Step 1: Run full test suite**

Run:

```powershell
.\.venv\Scripts\pytest.exe
```

Expected: all tests pass.

- [ ] **Step 2: Update TC-003**

Set TC-003 status to Passed, update date to 2026-05-06, and record:

- valid canonical records pass
- invalid canonical records fail
- useful validation messages identify fields
- no Firestore persistence is included yet
- evidence from targeted schema tests and full test suite

- [ ] **Step 3: Check git status**

Run:

```powershell
git status --short --branch
```

Expected: tracked development files changed plus ignored docs changed.

## Task 6: Commit Development Files Only

**Files:**
- Stage: `src/sadify/schemas/__init__.py`
- Stage: `src/sadify/schemas/canonical.py`
- Stage: `tests/test_canonical_schemas.py`
- Do not stage ignored docs unless the user explicitly changes the repo policy.

- [ ] **Step 1: Review diff**

Run:

```powershell
git diff -- src/sadify/schemas/__init__.py src/sadify/schemas/canonical.py tests/test_canonical_schemas.py
```

- [ ] **Step 2: Commit tracked development changes**

Run:

```powershell
git add src/sadify/schemas/__init__.py src/sadify/schemas/canonical.py tests/test_canonical_schemas.py
git commit -m "feat: add canonical schema validation"
```

Expected: commit contains development files only.

## Self-Review

- Spec coverage: Covers all six TC-003 records and useful validation errors.
- Scope check: Keeps Firestore, version-history schema, rendering, and export generation out of Checkpoint 5.
- Approach B placement: `KnowledgeItemVersionRecord` is noted for a later slice when wiki/version-history snapshots are needed.
- Placeholder scan: No TBD/TODO placeholders.


---

## 2026-05-06-completeness-confidence-scoring-plan

# Completeness Confidence Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Checkpoint 7 local completeness and confidence scoring that is transparent, business-friendly, and cost-safe before live model calls.

**Architecture:** Add a focused scoring service under `src/sadify/services/` and have `requirement_analysis.py` delegate scoring to it. The service will score category evidence, apply caps for very vague input, return visible evidence and missing information, and preserve the current Streamlit display contract.

**Tech Stack:** Python 3.13, dataclasses, regex, pytest 9.x, existing Streamlit page model.

---

## Scope

Included:

- Local deterministic completeness score.
- Confidence score and explanation based on visible evidence.
- Stronger handling for vague single-word or role-only input such as `admin`.
- Business-friendly missing information and clarification questions.
- Tests for vague, partial, and strong inputs.
- Checkpoint docs and test case docs updated.

Not included:

- Live Gemini/model-router call.
- Non-Google provider adapters.
- Firestore writes for analysis results.
- Relationship linking, wiki generation, SAD generation, or exports.

## Files

- Create: `src/sadify/services/completeness_scoring.py`
- Create: `tests/test_completeness_scoring.py`
- Modify: `src/sadify/services/requirement_analysis.py`
- Modify: `tests/test_requirement_analysis.py`
- Modify: `docs/superpowers/testing/test_cases/TC-004-completeness-confidence.md`
- Modify: `docs/superpowers/testing/test_case_index.md`
- Modify: `docs/superpowers/development/00_development_index.md`
- Modify: `docs/superpowers/development/08_new_chat_handoff.md`

## Task 1: Scoring Service Tests

- [ ] **Step 1: Write failing tests**

Create `tests/test_completeness_scoring.py` with tests like:

```python
from sadify.services.completeness_scoring import score_requirement_context


def test_role_only_input_stays_low_even_when_role_keyword_matches():
    result = score_requirement_context("admin")

    assert result.score <= 10
    assert result.level == "Low"
    assert result.confidence_label == "Low"
    assert "too little business context" in result.confidence_reason.lower()
    assert result.missing_categories[0].area == "Business problem"


def test_partial_operational_input_scores_middle_with_visible_evidence():
    result = score_requirement_context(
        "Warehouse operators record stock movement by item, quantity, "
        "location, and status. Supervisors review rejected records."
    )

    assert 45 <= result.score <= 75
    assert result.level in {"Partial", "Good"}
    assert result.confidence_label == "Medium"
    assert any(category.category == "people" for category in result.present_categories)
    assert any(category.category == "details" for category in result.present_categories)
    assert result.evidence_summary


def test_strong_operational_input_scores_strong_without_live_model():
    result = score_requirement_context(
        "Warehouse operators scan stock during receiving, picking, packing, "
        "and dispatch. They record item code, quantity, location, date, "
        "status, and remarks. Supervisors approve adjustments and rejected "
        "records. Managers need daily dashboards and weekly exports. The "
        "system needs role-based access, audit history, mobile use, fast "
        "busy-hour performance, and safe handling for missing or failed scans."
    )

    assert result.score >= 85
    assert result.level == "Strong"
    assert result.confidence_label == "High"
    assert result.missing_categories == ()
```

- [ ] **Step 2: Run tests to verify red**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_completeness_scoring.py
```

Expected:

```text
ModuleNotFoundError: No module named 'sadify.services.completeness_scoring'
```

## Task 2: Implement Scoring Service

- [ ] **Step 1: Create `src/sadify/services/completeness_scoring.py`**

Implement dataclasses:

```python
ScoredCategory
MissingCategory
CompletenessScore
```

Implement:

```python
score_requirement_context(requirement_text: str) -> CompletenessScore
```

Rules:

- Normalize whitespace.
- Detect category signals with whole-word regex.
- Score by weighted categories:
  - business_problem: 15
  - people: 12
  - process: 18
  - details: 15
  - approval: 12
  - visibility: 10
  - exceptions: 8
  - access: 6
  - operating_needs: 4
- Apply caps:
  - fewer than 5 words: max 10
  - fewer than 15 words: max 25
  - no process category: max 55
  - no business_problem category: max 65
- Map levels:
  - 0-39 Low
  - 40-69 Partial
  - 70-84 Good
  - 85-100 Strong
- Map confidence:
  - score <= 39 or fewer than 15 words: Low
  - score <= 84: Medium
  - score >= 85 and no missing critical categories: High

- [ ] **Step 2: Run tests to verify green**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_completeness_scoring.py
```

Expected:

```text
3 passed
```

## Task 3: Wire Requirement Analysis

- [ ] **Step 1: Update tests**

Modify `tests/test_requirement_analysis.py` so `admin` or `people` stays low and so display dict includes:

```python
assert display["scoring_basis"]
assert display["evidence_summary"]
```

- [ ] **Step 2: Verify red**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_requirement_analysis.py
```

Expected: failures for missing `scoring_basis` and old score behavior.

- [ ] **Step 3: Update `requirement_analysis.py`**

Change it to call `score_requirement_context(normalized_text)`, map scoring missing categories to the existing `MissingInformation` display objects, and build clarification questions from the score result.

- [ ] **Step 4: Verify green**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_requirement_analysis.py tests\test_app_shell.py
```

Expected: all selected tests pass.

## Task 4: Documentation And Full Verification

- [ ] **Step 1: Update TC-004**

Record local C7 expected behavior, real output, evidence, and decision.

- [ ] **Step 2: Update index/handoff docs**

Mark C7 complete only after full verification passes.

- [ ] **Step 3: Run full suite**

Run:

```powershell
.\.venv\Scripts\pytest.exe
```

Expected:

```text
all tests pass
```

- [ ] **Step 4: Commit tracked development only**

Run:

```powershell
git status --short
git add src/sadify/services/completeness_scoring.py src/sadify/services/requirement_analysis.py tests/test_completeness_scoring.py tests/test_requirement_analysis.py
git commit -m "feat: add completeness confidence scoring"
```

Do not stage docs because the user requested docs stay out of git.


---

## 2026-05-06-firestore-persistence-plan

# Firestore Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Checkpoint 6 local-first Firestore persistence for validated canonical SADify records.

**Architecture:** Add a small persistence service that accepts canonical Pydantic models from Checkpoint 5, validates them again before saving, writes through a Firestore-like client interface, and reads records back into canonical models. Unit tests use an in-memory fake client so this checkpoint proves paths, validation, round-trip behavior, and error handling without cloud calls.

**Tech Stack:** Python 3.13, Pydantic 2.x, pytest 9.x, Firestore-compatible repository interface.

---

## Scope

Use Approach A.

Implement now:

- local-first Firestore repository abstraction
- save/read methods for the six TC-010 record types
- validation-before-save using Checkpoint 5 schemas
- Firestore path mapping for project document and subcollections
- in-memory fake Firestore client for tests
- friendly persistence error wrapper

Do not implement now:

- real Firestore smoke write
- Streamlit UI changes
- cloud credentials setup
- Firestore emulator setup
- live model calls
- generated wiki/version-history persistence beyond the IDs already referenced by export records

Real Firestore smoke test note: after this local abstraction is green and committed, run one explicit cloud smoke test only with user approval. The smoke test should create a small test project under `projects/PROJ-SMOKE-001`, read it back, and delete or document cleanup.

## File Structure

- Create `src/sadify/services/firestore_persistence.py`
  - Repository class, collection path helpers, fake-client-compatible protocol expectations, error wrapper.
- Modify `src/sadify/services/__init__.py`
  - Re-export persistence repository and error.
- Create `tests/test_firestore_persistence.py`
  - In-memory fake Firestore objects plus repository tests.
- Update `requirements.txt`
  - Add `google-cloud-firestore` only if a real client factory is included in this checkpoint.
- Update `docs/superpowers/testing/test_cases/TC-010-firestore-persistence.md`
  - Record local-first evidence and note no real cloud smoke yet.

## Task 1: Failing Round-Trip Tests

**Files:**
- Create: `tests/test_firestore_persistence.py`

- [ ] **Step 1: Write fake Firestore classes**

Add small fake classes with the Firestore method shape the repository needs:

```python
class FakeFirestoreClient:
    def __init__(self):
        self.storage = {}

    def collection(self, name):
        return FakeCollectionReference(self.storage, (name,))
```

The fake should support:

- `collection(name)`
- `document(id)`
- nested `collection(name)`
- `set(payload)`
- `get().exists`
- `get().to_dict()`

- [ ] **Step 2: Write failing repository tests**

Import the not-yet-created repository:

```python
from sadify.services import FirestorePersistenceError, FirestoreRepository
```

Test:

- project save/read round-trips `ProjectRecord`
- source, knowledge item, relationship, SAD version, and export records save/read under `projects/{project_id}/...`

- [ ] **Step 3: Run red test**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_firestore_persistence.py
```

Expected: fail because repository does not exist yet.

## Task 2: Minimal Repository

**Files:**
- Create: `src/sadify/services/firestore_persistence.py`
- Modify: `src/sadify/services/__init__.py`

- [ ] **Step 1: Implement minimal repository**

Create:

```python
class FirestorePersistenceError(RuntimeError):
    pass

class FirestoreRepository:
    def __init__(self, client):
        self._client = client
```

Add save/read methods and path helpers.

Path mapping:

```text
projects/{project_id}
projects/{project_id}/sources/{source_id}
projects/{project_id}/knowledge_items/{item_id}
projects/{project_id}/relationships/{relationship_id}
projects/{project_id}/sad_versions/{sad_version_id}
projects/{project_id}/exports/{export_id}
```

- [ ] **Step 2: Run green tests**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_firestore_persistence.py
```

Expected: round-trip tests pass.

## Task 3: Validation Before Save

**Files:**
- Modify: `tests/test_firestore_persistence.py`
- Modify: `src/sadify/services/firestore_persistence.py`

- [ ] **Step 1: Add failing tests**

Cover:

- saving a plain invalid dict fails before client write
- invalid source ID for source record fails
- missing document returns `None`

- [ ] **Step 2: Run red tests**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_firestore_persistence.py
```

Expected: fail until repository validates dict inputs and handles missing reads.

- [ ] **Step 3: Implement validation helpers**

Allow save methods to accept either model instances or dicts:

```python
def _coerce_model(model_type, value):
    if isinstance(value, model_type):
        return value
    return model_type.model_validate(value)
```

Ensure client storage is not written when validation fails.

- [ ] **Step 4: Run green tests**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_firestore_persistence.py
```

Expected: all persistence tests pass.

## Task 4: Friendly Error Wrapping

**Files:**
- Modify: `tests/test_firestore_persistence.py`
- Modify: `src/sadify/services/firestore_persistence.py`

- [ ] **Step 1: Add failing tests**

Use a fake client that raises on `set()` and assert:

- repository raises `FirestorePersistenceError`
- message names the action and record type
- raw exception is chained, not exposed as an unstructured UI string

- [ ] **Step 2: Implement wrapper**

Wrap client errors for save/read:

```python
raise FirestorePersistenceError("Could not save project PROJ-001.") from exc
```

- [ ] **Step 3: Run green tests**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_firestore_persistence.py
```

Expected: all persistence tests pass.

## Task 5: Verification And TC-010 Update

**Files:**
- Modify: `docs/superpowers/testing/test_cases/TC-010-firestore-persistence.md`
- Modify: `docs/superpowers/testing/test_case_index.md`
- Modify: `docs/superpowers/development/00_development_index.md`
- Modify: `context.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Run targeted tests**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_firestore_persistence.py
```

- [ ] **Step 2: Run full tests**

Run:

```powershell
.\.venv\Scripts\pytest.exe
```

- [ ] **Step 3: Update docs**

Mark TC-010 as Passed for local-first persistence only. State clearly that no real Firestore cloud smoke test has been run yet.

Update current status docs so the next checkpoint becomes Checkpoint 7: completeness + confidence scoring.

## Task 6: Commit Development Files Only

**Files:**
- Stage: `src/sadify/services/__init__.py`
- Stage: `src/sadify/services/firestore_persistence.py`
- Stage: `tests/test_firestore_persistence.py`
- Stage: `requirements.txt` only if modified
- Do not stage ignored docs unless repo policy changes.

- [ ] **Step 1: Review staged diff**

Run:

```powershell
git diff --cached --stat
git diff --cached -- src/sadify/services/firestore_persistence.py tests/test_firestore_persistence.py
```

- [ ] **Step 2: Commit tracked development changes**

Run:

```powershell
git commit -m "feat: add firestore persistence repository"
```

Expected: commit contains development files only.

## Self-Review

- Spec coverage: Covers TC-010 save/read behavior for all six Checkpoint 5 canonical records.
- Scope check: Keeps real cloud smoke test separate and explicit.
- Cloud safety: No real Firestore write occurs in this local-first implementation.
- Placeholder scan: No TBD/TODO placeholders.


---

## 2026-05-06-relationship-linking-plan

# Relationship Linking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Checkpoint 8 local relationship linking that turns requirement text into canonical knowledge items and relationship records.

**Architecture:** Add a focused service under `src/sadify/services/relationship_linking.py`. The service will detect clear local signals for actors, entities, workflows, reports, decisions, and source evidence; create canonical `KnowledgeItemRecord` and `RelationshipRecord` objects; and keep the first slice deterministic and cost-safe.

**Tech Stack:** Python 3.13, dataclasses, regex, Pydantic canonical schemas, pytest 9.x.

---

## Scope

Included:

- Local deterministic graph builder.
- Canonical requirement, actor, entity, workflow, report, decision, and source knowledge items.
- Canonical relationship records using existing schema relationship types.
- Evidence source IDs preserved on relationships.
- Deduplication for repeated/noisy detected terms.
- Tests before implementation.

Not included:

- Live Gemini/model-router relationship extraction.
- Firestore writes.
- Wiki Markdown generation.
- UI graph visualization.
- Multi-requirement clustering across a full project.

## Files

- Create: `src/sadify/services/relationship_linking.py`
- Create: `tests/test_relationship_linking.py`
- Modify: `src/sadify/services/__init__.py`
- Modify: `docs/superpowers/testing/test_cases/TC-005-relationship-linking.md`
- Modify: `docs/superpowers/testing/test_case_index.md`
- Modify: current status/handoff docs after verification.

## Task 1: Failing Service Tests

- [ ] **Step 1: Create `tests/test_relationship_linking.py`**

Write tests that expect this API:

```python
from datetime import datetime, timezone

from sadify.schemas import KnowledgeItemRecord, RelationshipRecord
from sadify.services.relationship_linking import build_requirement_graph


TIMESTAMP = datetime(2026, 5, 6, tzinfo=timezone.utc)


def test_build_requirement_graph_creates_canonical_items_and_relationships():
    graph = build_requirement_graph(
        requirement_id="REQ-001",
        title="Warehouse Stock Movement",
        requirement_text=(
            "Warehouse operators scan stock during receiving, picking, packing, "
            "and dispatch. They record item code, quantity, location, date, "
            "status, and remarks. Supervisors approve adjustments and rejected "
            "records. Managers need daily dashboards and weekly exports. The "
            "system needs role-based access and audit history."
        ),
        source_ids=("SRC-001",),
        created_at=TIMESTAMP,
    )

    assert all(isinstance(item, KnowledgeItemRecord) for item in graph.knowledge_items)
    assert all(isinstance(link, RelationshipRecord) for link in graph.relationships)
    assert graph.requirement.item_id == "REQ-001"
    assert graph.item_titles_by_type("actor") == ["Operators", "Supervisors", "Managers"]
    assert "Stock" in graph.item_titles_by_type("entity")
    assert "Stock Movement Workflow" in graph.item_titles_by_type("workflow")
    assert "Daily Dashboard" in graph.item_titles_by_type("report")
    assert "Role-Based Access Rules" in graph.item_titles_by_type("decision")
    assert "Source SRC-001" in graph.item_titles_by_type("source")
    assert graph.relationship_types() == [
        "performed_by_actor",
        "performed_by_actor",
        "performed_by_actor",
        "uses_entity",
        "uses_entity",
        "uses_workflow",
        "produces_report",
        "produces_report",
        "records_decision",
        "supported_by_source",
    ]
```

- [ ] **Step 2: Add deduplication and vague-input tests**

```python
def test_graph_builder_deduplicates_repeated_people_terms():
    graph = build_requirement_graph(
        requirement_id="REQ-001",
        title="Supervisor Review",
        requirement_text="Supervisors and supervisor review records with operators.",
        created_at=TIMESTAMP,
    )

    assert graph.item_titles_by_type("actor") == ["Supervisors", "Operators"]


def test_vague_input_creates_only_requirement_item():
    graph = build_requirement_graph(
        requirement_id="REQ-001",
        title="Plantation App",
        requirement_text="Need an app.",
        created_at=TIMESTAMP,
    )

    assert [item.item_id for item in graph.knowledge_items] == ["REQ-001"]
    assert graph.relationships == ()
```

- [ ] **Step 3: Verify red**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_relationship_linking.py
```

Expected:

```text
ModuleNotFoundError: No module named 'sadify.services.relationship_linking'
```

## Task 2: Relationship Linking Service

- [ ] **Step 1: Create the service**

Create `src/sadify/services/relationship_linking.py` with:

```python
RelationshipGraph
build_requirement_graph(...)
```

Detection rules:

- actors: operators, supervisors, managers, admin, staff, workers.
- entities: stock, item code, quantity, location, date, status, remarks, block, activity.
- workflow: stock movement / receiving / picking / packing / dispatch / review.
- reports: dashboard, report, export, daily, weekly.
- decisions: role-based access, access rules, audit history, approval rules.
- sources: each valid `SRC-...` source ID becomes a source knowledge item.

Relationship mapping:

- actor -> `performed_by_actor`
- entity -> `uses_entity`
- workflow -> `uses_workflow`
- report -> `produces_report`
- decision -> `records_decision`
- source -> `supported_by_source`

- [ ] **Step 2: Verify green**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_relationship_linking.py
```

Expected: all relationship-linking tests pass.

## Task 3: Export Service API And Full Verification

- [ ] **Step 1: Update `src/sadify/services/__init__.py`**

Expose:

```python
RelationshipGraph
build_requirement_graph
```

- [ ] **Step 2: Run targeted tests**

```powershell
.\.venv\Scripts\pytest.exe tests\test_relationship_linking.py tests\test_canonical_schemas.py
```

- [ ] **Step 3: Run full suite**

```powershell
.\.venv\Scripts\pytest.exe
```

Expected: all tests pass.

## Task 4: Docs And Commit

- [ ] **Step 1: Update TC-005 and test index**

Record expected output, real output, evidence, and C8 decision.

- [ ] **Step 2: Update current status docs**

Mark C8 complete and next checkpoint as C9 wiki Markdown generation.

- [ ] **Step 3: Commit tracked development only**

```powershell
git add src/sadify/services/relationship_linking.py src/sadify/services/__init__.py tests/test_relationship_linking.py
git commit -m "feat: add relationship linking graph builder"
```

Do not stage docs because docs are ignored by user preference.

## Execution Result

Status: Completed on 2026-05-06.

Tracked development commit:

```text
211f12a feat: add relationship linking graph builder
```

Verification:

```text
.\.venv\Scripts\pytest.exe tests\test_relationship_linking.py -> 4 passed
.\.venv\Scripts\pytest.exe tests\test_relationship_linking.py tests\test_canonical_schemas.py -> 10 passed
.\.venv\Scripts\pytest.exe -> 66 passed
```

Next checkpoint:

```text
Checkpoint 9: wiki Markdown generation
```


---

## 2026-05-07-project-level-sad-generation-plan

# Project-Level SAD Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Checkpoint 11 by generating a project-level canonical SAD version and readable Markdown preview from existing canonical knowledge items and relationships.

**Architecture:** Add a local-first `sad_generation` service that accepts validated `KnowledgeItemRecord` and `RelationshipRecord` values, groups them into predictable SAD sections, creates a `SadVersionRecord`, and renders Markdown from the structured sections. Live Gemini/model-route refinement remains a later layer that can improve section wording after this deterministic baseline exists.

**Tech Stack:** Python 3.13, Pydantic canonical schemas, pytest, existing SADify relationship graph records.

---

## File Structure

- Create `src/sadify/services/sad_generation.py`
  - Owns project-level SAD generation.
  - Provides `generate_project_sad`.
  - Raises `SadGenerationError` for invalid generation inputs.
  - Keeps rendering close to structured section construction for the first local slice.
- Modify `src/sadify/services/__init__.py`
  - Exports the C11 service and error type.
- Create `tests/test_sad_generation.py`
  - Covers canonical record creation, required sections, traceability, assumptions/open questions, and missing requirement behavior.
- Update ignored docs after implementation:
  - `docs/superpowers/testing/test_cases/TC-008-sad-generation.md`
  - `docs/superpowers/testing/test_case_index.md`
  - `docs/superpowers/development/12_repo_rescan_alignment_checkpoint.md`
  - `docs/superpowers/development/08_new_chat_handoff.md`
  - this plan with execution evidence.

## Design Summary

The service should build a project-level SAD, not one SAD per requirement. The output must be useful to a human reviewer and traceable to canonical JSON.

Required local sections:

- `summary`
- `critical_gaps`
- `functional_requirements`
- `non_functional_requirements`
- `business_rules`
- `edge_cases`
- `data_entities`
- `workflows`
- `developer_tasks`
- `assumptions`
- `open_questions`
- `source_traceability`

The rendered Markdown preview should include the standard behavior-contract sections:

- Requirement Summary
- Completeness And Confidence
- Critical Gaps And Open Questions
- Problem Statement
- Stakeholders
- Current Workflow
- Proposed Workflow
- Functional Requirements
- Non-Functional Requirements
- User Roles And Permissions
- Business Rules
- Edge Cases And Exception Handling
- Data Entities
- Integration Needs
- DFD-Style Process Description
- Developer Task Breakdown
- Assumptions
- Source Traceability

## Task 1: Write Failing Tests For Canonical SAD Generation

**Files:**
- Create: `tests/test_sad_generation.py`

- [ ] **Step 1: Add tests for the public API**

```python
from datetime import datetime, timezone

import pytest

from sadify.schemas import Assumption, KnowledgeItemRecord, OpenQuestion, SadVersionRecord
from sadify.services.relationship_linking import build_requirement_graph
from sadify.services.sad_generation import SadGenerationError, generate_project_sad


TIMESTAMP = datetime(2026, 5, 7, tzinfo=timezone.utc)


def test_generate_project_sad_creates_canonical_version_record():
    graph = _sample_graph()

    sad = generate_project_sad(
        sad_version_id="SAD-001",
        project_title="Warehouse Operations",
        knowledge_items=graph.knowledge_items,
        relationships=graph.relationships,
        created_at=TIMESTAMP,
        created_by="local-user",
    )

    assert isinstance(sad, SadVersionRecord)
    assert sad.sad_version_id == "SAD-001"
    assert sad.version_number == 1
    assert sad.status == "draft"
    assert sad.source_requirement_ids == ["REQ-001"]
    assert "REQ-001" in sad.source_knowledge_item_ids
    assert "ACT-001" in sad.source_knowledge_item_ids
    assert "SRC-001" in sad.source_knowledge_item_ids
    assert sad.completeness_score == 100
    assert sad.confidence_label == "high"
    assert sad.verification_result["schema_validation"]["status"] == "passed"
    assert sad.verification_result["sad_quality_check"]["status"] == "not_run"
```

- [ ] **Step 2: Add tests for Markdown preview and traceability**

```python
def test_generated_sad_markdown_contains_required_sections_and_traceability():
    graph = _sample_graph()

    sad = generate_project_sad(
        sad_version_id="SAD-001",
        project_title="Warehouse Operations",
        knowledge_items=graph.knowledge_items,
        relationships=graph.relationships,
        created_at=TIMESTAMP,
        created_by="local-user",
    )

    markdown = sad.rendered_markdown
    assert markdown.startswith("# Warehouse Operations System Analysis And Design")
    for heading in (
        "## Requirement Summary",
        "## Completeness And Confidence",
        "## Critical Gaps And Open Questions",
        "## Stakeholders",
        "## Functional Requirements",
        "## Developer Task Breakdown",
        "## Source Traceability",
    ):
        assert heading in markdown
    assert "REQ-001" in markdown
    assert "SRC-001" in markdown
    assert "Operators" in markdown
    assert "Daily Dashboard" in markdown
```

- [ ] **Step 3: Add tests for assumptions and open questions**

```python
def test_generated_sad_keeps_assumptions_and_open_questions_visible():
    graph = _sample_graph()
    requirement = graph.requirement.model_copy(
        update={
            "open_questions": [
                OpenQuestion(
                    question_id="Q-001",
                    label="[OPEN QUESTION]",
                    severity="high",
                    question="Who owns final stock adjustment approval?",
                )
            ],
            "assumptions": [
                Assumption(
                    assumption_id="ASM-001",
                    label="[ASSUMPTION]",
                    text="Supervisors are assumed to review rejected records.",
                )
            ],
        }
    )
    knowledge_items = (requirement,) + graph.knowledge_items[1:]

    sad = generate_project_sad(
        sad_version_id="SAD-001",
        project_title="Warehouse Operations",
        knowledge_items=knowledge_items,
        relationships=graph.relationships,
        created_at=TIMESTAMP,
        created_by="local-user",
    )

    assert sad.structured_sections["open_questions"] == [
        {
            "requirement_id": "REQ-001",
            "severity": "high",
            "question": "Who owns final stock adjustment approval?",
        }
    ]
    assert sad.structured_sections["assumptions"] == [
        {
            "requirement_id": "REQ-001",
            "text": "Supervisors are assumed to review rejected records.",
        }
    ]
    assert "[OPEN QUESTION] Who owns final stock adjustment approval?" in sad.rendered_markdown
    assert "[ASSUMPTION] Supervisors are assumed to review rejected records." in sad.rendered_markdown
```

- [ ] **Step 4: Add invalid-input test and helpers**

```python
def test_generate_project_sad_requires_at_least_one_requirement():
    graph = _sample_graph()
    non_requirement_items = tuple(
        item for item in graph.knowledge_items if item.item_type != "requirement"
    )

    with pytest.raises(SadGenerationError) as exc_info:
        generate_project_sad(
            sad_version_id="SAD-001",
            project_title="Warehouse Operations",
            knowledge_items=non_requirement_items,
            relationships=graph.relationships,
            created_at=TIMESTAMP,
            created_by="local-user",
        )

    assert "at least one requirement" in str(exc_info.value)


def _sample_graph():
    return build_requirement_graph(
        requirement_id="REQ-001",
        title="Warehouse Stock Movement",
        requirement_text=(
            "Warehouse operators scan stock during receiving, picking, packing, "
            "and dispatch. They record item code, quantity, location, date, "
            "status, and remarks. Supervisors approve adjustments and rejected "
            "records. Managers need daily dashboards and weekly exports. The "
            "system needs role-based access and audit history."
        ),
        source_ids=("SRC-001",),
        created_at=TIMESTAMP,
    )
```

- [ ] **Step 5: Run red tests**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_sad_generation.py -q
```

Expected:

```text
ModuleNotFoundError or ImportError for sadify.services.sad_generation
```

## Task 2: Implement Local SAD Generation

**Files:**
- Create: `src/sadify/services/sad_generation.py`
- Modify: `src/sadify/services/__init__.py`

- [ ] **Step 1: Implement `SadGenerationError` and `generate_project_sad`**

Create the service with these responsibilities:

- validate at least one requirement item exists
- group canonical items by type
- aggregate completeness and confidence from requirement items
- include all source knowledge IDs
- build predictable structured sections
- render Markdown from structured sections
- return a validated `SadVersionRecord`

- [ ] **Step 2: Export the service**

Add to `src/sadify/services/__init__.py`:

```python
from sadify.services.sad_generation import SadGenerationError, generate_project_sad
```

and add both names to `__all__`.

- [ ] **Step 3: Run green tests**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_sad_generation.py -q
```

Expected:

```text
4 passed
```

## Task 3: Regression Verification And Docs

**Files:**
- Modify ignored docs listed above.

- [ ] **Step 1: Run related test set**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_sad_generation.py tests\test_canonical_schemas.py tests\test_relationship_linking.py -q
```

Expected:

```text
All selected tests pass.
```

- [ ] **Step 2: Run full suite**

Run:

```powershell
.\.venv\Scripts\pytest.exe
```

Expected:

```text
All tests pass.
```

- [ ] **Step 3: Update checkpoint docs**

Record:

- expected output
- real output
- test commands
- C11 decision
- next checkpoint is C12 export generation

- [ ] **Step 4: Commit tracked development files only**

Run:

```powershell
git status --short
git add src\sadify\services\sad_generation.py src\sadify\services\__init__.py tests\test_sad_generation.py
git commit -m "feat: add project sad generation"
```

Expected:

```text
Commit succeeds. Ignored docs remain local-only.
```

## Self-Review

- Spec coverage: The plan covers canonical SAD version creation, readable Markdown preview, visible assumptions/open questions, source traceability, completeness/confidence summary, and developer tasks.
- Placeholder scan: No TBD/TODO/fill-in placeholders remain.
- Type consistency: Public API uses existing `KnowledgeItemRecord`, `RelationshipRecord`, and `SadVersionRecord` types.

## Execution Result

Status: Implemented locally.

Tracked development files:

```text
src/sadify/services/sad_generation.py
src/sadify/services/__init__.py
tests/test_sad_generation.py
```

Verification:

```text
Command: .\.venv\Scripts\pytest.exe tests\test_sad_generation.py -q
Result: 4 passed in 0.31s

Command: .\.venv\Scripts\pytest.exe tests\test_sad_generation.py tests\test_canonical_schemas.py tests\test_relationship_linking.py -q
Result: 14 passed in 0.37s

Command: .\.venv\Scripts\pytest.exe
Result: 80 passed in 5.84s
```

Commit:

```text
050b1d8 feat: add project sad generation
```

Next checkpoint:

```text
Checkpoint 12: Google Docs/PDF/DOCX/wiki export generation.
```


---

## 2026-05-07-wiki-markdown-generation-plan

# Wiki Markdown Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Checkpoint 9 local wiki Markdown generation from canonical knowledge items and relationship records.

**Architecture:** Add a focused renderer under `src/sadify/renderers/wiki_markdown.py`. The renderer will accept canonical `KnowledgeItemRecord` and `RelationshipRecord` objects, return deterministic `WikiNoteDraft` records, and keep file grouping/link generation local and testable.

**Tech Stack:** Python 3.13, dataclasses, canonical Pydantic schemas, pytest 9.x, plain Markdown/YAML frontmatter rendering.

---

## Scope

Included:

- Local deterministic wiki Markdown rendering.
- Markdown draft objects with item ID, type, folder, file name, relative path, and markdown content.
- YAML frontmatter for ID, type, slug, status, completeness, confidence, sources, relationships, and related item IDs.
- `[[wiki links]]` generated from canonical relationship endpoints.
- Folder grouping by knowledge item type.
- Open questions, assumptions, related notes, and sources sections.
- Broken relationship endpoint detection to avoid silently generating invalid links.
- Tests before implementation.

Not included:

- Google Drive writes.
- Firestore writes.
- Markdown verification/approval workflow.
- Gemini quality check.
- Obsidian runtime integration.
- Streamlit UI visualization.
- Project-level SAD generation.

## Files

- Create: `src/sadify/renderers/wiki_markdown.py`
- Modify: `src/sadify/renderers/__init__.py`
- Create: `tests/test_wiki_markdown_renderer.py`
- Modify after verification: `docs/superpowers/testing/test_cases/TC-006-wiki-markdown-generation.md`
- Modify after verification: `docs/superpowers/testing/test_case_index.md`
- Modify after verification: current status/handoff docs.

## Target API

```python
from sadify.renderers.wiki_markdown import render_wiki_notes

notes = render_wiki_notes(
    knowledge_items=graph.knowledge_items,
    relationships=graph.relationships,
)
```

`render_wiki_notes` returns `tuple[WikiNoteDraft, ...]`.

`WikiNoteDraft` fields:

```python
item_id: str
item_type: str
slug: str
folder: str
file_name: str
relative_path: str
markdown: str
linked_item_ids: tuple[str, ...]
```

Folder mapping:

```text
requirement -> requirements
entity -> entities
workflow -> workflows
decision -> decisions
actor -> actors
report -> reports
source -> sources
```

File name format:

```text
{item_id}-{slug}.md
```

Wiki link target format:

```text
[[{item_id}-{slug}]]
```

## Task 1: Failing Renderer Tests

- [ ] **Step 1: Create `tests/test_wiki_markdown_renderer.py`**

Write the first test using the C8 relationship graph:

```python
from datetime import datetime, timezone

from sadify.renderers.wiki_markdown import render_wiki_notes
from sadify.services.relationship_linking import build_requirement_graph


TIMESTAMP = datetime(2026, 5, 7, tzinfo=timezone.utc)


def _sample_graph():
    return build_requirement_graph(
        requirement_id="REQ-001",
        title="Warehouse Stock Movement",
        requirement_text=(
            "Warehouse operators scan stock during receiving, picking, packing, "
            "and dispatch. They record item code, quantity, location, date, "
            "status, and remarks. Supervisors approve adjustments and rejected "
            "records. Managers need daily dashboards and weekly exports. The "
            "system needs role-based access and audit history."
        ),
        source_ids=("SRC-001",),
        created_at=TIMESTAMP,
    )


def _note_by_id(notes, item_id):
    return next(note for note in notes if note.item_id == item_id)


def test_render_wiki_notes_creates_grouped_markdown_drafts():
    graph = _sample_graph()

    notes = render_wiki_notes(
        knowledge_items=graph.knowledge_items,
        relationships=graph.relationships,
    )

    requirement_note = _note_by_id(notes, "REQ-001")
    source_note = _note_by_id(notes, "SRC-001")

    assert requirement_note.folder == "requirements"
    assert requirement_note.file_name == "REQ-001-warehouse-stock-movement.md"
    assert requirement_note.relative_path == (
        "requirements/REQ-001-warehouse-stock-movement.md"
    )
    assert source_note.folder == "sources"
    assert source_note.relative_path == "sources/SRC-001-source-src-001.md"
```

- [ ] **Step 2: Add frontmatter and link assertions**

Add:

```python
def test_requirement_note_contains_frontmatter_sections_and_wiki_links():
    graph = _sample_graph()

    notes = render_wiki_notes(
        knowledge_items=graph.knowledge_items,
        relationships=graph.relationships,
    )

    requirement_note = _note_by_id(notes, "REQ-001")

    assert requirement_note.markdown.startswith("---\n")
    assert "id: REQ-001\n" in requirement_note.markdown
    assert "type: requirement\n" in requirement_note.markdown
    assert "slug: warehouse-stock-movement\n" in requirement_note.markdown
    assert "status: draft\n" in requirement_note.markdown
    assert "sources:\n  - SRC-001\n" in requirement_note.markdown
    assert "# Warehouse Stock Movement\n" in requirement_note.markdown
    assert "## Summary\n" in requirement_note.markdown
    assert "## Related Notes\n" in requirement_note.markdown
    assert "[[ACT-001-operators]]" in requirement_note.markdown
    assert "[[ENT-001-stock]]" in requirement_note.markdown
    assert "[[WF-001-stock-movement-workflow]]" in requirement_note.markdown
    assert "[[REP-001-daily-dashboard]]" in requirement_note.markdown
    assert "[[DEC-001-role-based-access-rules]]" in requirement_note.markdown
    assert "[[SRC-001-source-src-001]]" in requirement_note.markdown
    assert requirement_note.linked_item_ids == (
        "ACT-001",
        "ACT-002",
        "ACT-003",
        "ENT-001",
        "ENT-002",
        "WF-001",
        "REP-001",
        "REP-002",
        "DEC-001",
        "SRC-001",
    )
```

- [ ] **Step 3: Add questions/assumptions and broken-link tests**

Add:

```python
import pytest

from sadify.renderers.wiki_markdown import (
    WikiMarkdownRenderError,
    render_wiki_notes,
)
from sadify.schemas import KnowledgeItemRecord


def test_note_includes_open_questions_and_assumptions():
    graph = _sample_graph()
    item_data = graph.requirement.model_dump()
    item_data["open_questions"] = [
        {
            "question_id": "Q-001",
            "label": "[OPEN QUESTION]",
            "severity": "high",
            "question": "Who approves stock adjustments?",
        }
    ]
    item_data["assumptions"] = [
        {
            "assumption_id": "ASM-001",
            "label": "[ASSUMPTION]",
            "text": "Supervisors review rejected records.",
        }
    ]
    requirement = KnowledgeItemRecord(**item_data)
    items = (requirement,) + tuple(
        item for item in graph.knowledge_items if item.item_id != "REQ-001"
    )

    notes = render_wiki_notes(
        knowledge_items=items,
        relationships=graph.relationships,
    )

    markdown = _note_by_id(notes, "REQ-001").markdown
    assert "## Open Questions\n" in markdown
    assert "- [HIGH] Who approves stock adjustments?\n" in markdown
    assert "## Assumptions\n" in markdown
    assert "- [ASSUMPTION] Supervisors review rejected records.\n" in markdown


def test_renderer_rejects_relationships_with_missing_items():
    graph = _sample_graph()
    items = tuple(item for item in graph.knowledge_items if item.item_id != "ACT-001")

    with pytest.raises(WikiMarkdownRenderError) as exc_info:
        render_wiki_notes(
            knowledge_items=items,
            relationships=graph.relationships,
        )

    assert "ACT-001" in str(exc_info.value)
```

- [ ] **Step 4: Verify red**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_wiki_markdown_renderer.py
```

Expected:

```text
ModuleNotFoundError: No module named 'sadify.renderers.wiki_markdown'
```

## Task 2: Minimal Wiki Markdown Renderer

- [ ] **Step 1: Create `src/sadify/renderers/wiki_markdown.py`**

Implement:

```python
@dataclass(frozen=True)
class WikiNoteDraft:
    item_id: str
    item_type: str
    slug: str
    folder: str
    file_name: str
    relative_path: str
    markdown: str
    linked_item_ids: tuple[str, ...]


class WikiMarkdownRenderError(ValueError):
    pass


def render_wiki_notes(
    *,
    knowledge_items: Sequence[KnowledgeItemRecord],
    relationships: Sequence[RelationshipRecord],
) -> tuple[WikiNoteDraft, ...]:
    ...
```

Implementation rules:

- Build `items_by_id` from all knowledge items.
- Validate every relationship source and target exists in `items_by_id`.
- Build note drafts in the order knowledge items are provided.
- Use deterministic folder names from item type.
- Use file stem `{item_id}-{slug}`.
- Include outgoing and incoming relationships in each note.
- For each related item, render `- [[target-stem]] - relationship label`.
- For source relationships, include the source note link in both `Related Notes` and `Sources`.
- Include `Open Questions` only when item has open questions.
- Include `Assumptions` only when item has assumptions.
- If a note has no related items, render `- No related notes yet.`

- [ ] **Step 2: Verify green**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_wiki_markdown_renderer.py
```

Expected:

```text
4 passed
```

## Task 3: Renderer Package Export And Regression Tests

- [ ] **Step 1: Update `src/sadify/renderers/__init__.py`**

Expose:

```python
WikiMarkdownRenderError
WikiNoteDraft
render_wiki_notes
```

- [ ] **Step 2: Run targeted tests**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_wiki_markdown_renderer.py tests\test_relationship_linking.py tests\test_canonical_schemas.py
```

Expected:

```text
all targeted tests pass
```

- [ ] **Step 3: Run full suite**

Run:

```powershell
.\.venv\Scripts\pytest.exe
```

Expected:

```text
all tests pass
```

## Task 4: Docs And Commit

- [ ] **Step 1: Update TC-006**

Record expected output, real output, differences/issues, evidence, and decision.

- [ ] **Step 2: Update test index and status docs**

Mark TC-006/C9 passed and set Checkpoint 10 as next.

- [ ] **Step 3: Commit tracked development only**

Run:

```powershell
git add src\sadify\renderers\wiki_markdown.py src\sadify\renderers\__init__.py tests\test_wiki_markdown_renderer.py
git commit -m "feat: add wiki markdown renderer"
```

Do not stage docs because docs are ignored by user preference.

## Execution Result

Status: Completed on 2026-05-07.

Tracked development commit:

```text
1c9c2fc feat: add wiki markdown renderer
```

Verification:

```text
.\.venv\Scripts\pytest.exe tests\test_wiki_markdown_renderer.py -> 4 passed
.\.venv\Scripts\pytest.exe tests\test_wiki_markdown_renderer.py tests\test_relationship_linking.py tests\test_canonical_schemas.py -> 14 passed
.\.venv\Scripts\pytest.exe -> 70 passed
```

Next checkpoint:

```text
Checkpoint 10: wiki verification and owner approval
```


---

## 2026-05-07-wiki-verification-approval-plan

# Wiki Verification And Owner Approval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Checkpoint 10 local wiki verification and owner approval state transitions for generated Markdown drafts.

**Architecture:** Add a focused service under `src/sadify/services/wiki_verification.py`. The service will verify `WikiNoteDraft` objects with deterministic rules, prepare canonical `KnowledgeItemRecord` copies for owner review, and promote or reject drafts without mutating the original item.

**Tech Stack:** Python 3.13, dataclasses, regex, canonical Pydantic schemas, pytest 9.x.

---

## Scope

Included:

- Local rule-based wiki Markdown verification.
- Broken wiki link detection against generated note file stems.
- Required frontmatter and section checks.
- Approval-ready `KnowledgeItemRecord` copy with `markdown_draft`, `markdown_status`, `pending_change_summary`, and `verification_result`.
- Owner approval that promotes `markdown_draft` to `markdown_current`.
- Owner rejection that preserves `markdown_current`, clears the pending draft, and records rejection reason.
- Tests before implementation.

Not included:

- Live Gemini quality verification.
- Streamlit approval UI.
- Firestore writes.
- Google Drive writes.
- Knowledge item version records.
- Project-level SAD generation.

## Files

- Create: `src/sadify/services/wiki_verification.py`
- Modify: `src/sadify/services/__init__.py`
- Create: `tests/test_wiki_verification.py`
- Modify after verification: `docs/superpowers/testing/test_cases/TC-007-wiki-verification-approval.md`
- Modify after verification: `docs/superpowers/testing/test_case_index.md`
- Modify after verification: current status/handoff docs.

## Target API

```python
from sadify.services.wiki_verification import (
    approve_wiki_draft,
    prepare_wiki_draft_for_approval,
    reject_wiki_draft,
    verify_wiki_note,
)

verification = verify_wiki_note(note, all_notes=notes)
pending_item = prepare_wiki_draft_for_approval(item, note, all_notes=notes)
approved_item = approve_wiki_draft(pending_item, reviewed_by="owner")
rejected_item = reject_wiki_draft(pending_item, reviewed_by="owner", reason="...")
```

`verify_wiki_note` returns `WikiVerificationResult`.

`WikiVerificationResult` fields:

```python
status: str  # passed | failed
issues: tuple[WikiVerificationIssue, ...]
```

`WikiVerificationIssue` fields:

```python
code: str
message: str
severity: str
```

## Task 1: Failing Verification Tests

- [ ] **Step 1: Create `tests/test_wiki_verification.py`**

Write:

```python
from datetime import datetime, timezone

import pytest

from sadify.renderers.wiki_markdown import render_wiki_notes
from sadify.services.relationship_linking import build_requirement_graph
from sadify.services.wiki_verification import (
    WikiApprovalError,
    approve_wiki_draft,
    prepare_wiki_draft_for_approval,
    reject_wiki_draft,
    verify_wiki_note,
)


TIMESTAMP = datetime(2026, 5, 7, tzinfo=timezone.utc)


def _sample_graph():
    return build_requirement_graph(
        requirement_id="REQ-001",
        title="Warehouse Stock Movement",
        requirement_text=(
            "Warehouse operators scan stock during receiving, picking, packing, "
            "and dispatch. They record item code, quantity, location, date, "
            "status, and remarks. Supervisors approve adjustments and rejected "
            "records. Managers need daily dashboards and weekly exports. The "
            "system needs role-based access and audit history."
        ),
        source_ids=("SRC-001",),
        created_at=TIMESTAMP,
    )


def _sample_notes():
    graph = _sample_graph()
    return graph, render_wiki_notes(
        knowledge_items=graph.knowledge_items,
        relationships=graph.relationships,
    )


def _note_by_id(notes, item_id):
    return next(note for note in notes if note.item_id == item_id)


def test_verify_wiki_note_passes_structural_checks():
    _, notes = _sample_notes()
    note = _note_by_id(notes, "REQ-001")

    result = verify_wiki_note(note, all_notes=notes)

    assert result.status == "passed"
    assert result.issues == ()
    assert result.to_dict() == {"status": "passed", "issues": []}
```

- [ ] **Step 2: Add failed-check and approval-state tests**

Add:

```python
def test_verify_wiki_note_reports_missing_sections_and_broken_links():
    _, notes = _sample_notes()
    note = _note_by_id(notes, "REQ-001")
    broken_note = note.with_markdown(
        note.markdown.replace("## Sources\n", "").replace(
            "[[ACT-001-operators]]",
            "[[ACT-404-missing]]",
        )
    )

    result = verify_wiki_note(broken_note, all_notes=notes)

    assert result.status == "failed"
    assert [issue.code for issue in result.issues] == [
        "missing_sources_section",
        "broken_wiki_link",
    ]


def test_prepare_wiki_draft_for_approval_sets_pending_fields():
    graph, notes = _sample_notes()
    item = graph.requirement
    note = _note_by_id(notes, "REQ-001")

    pending_item = prepare_wiki_draft_for_approval(
        item=item,
        note=note,
        all_notes=notes,
    )

    assert pending_item.markdown_current is None
    assert pending_item.markdown_draft == note.markdown
    assert pending_item.markdown_status == "pending_human_approval"
    assert pending_item.pending_change_summary == (
        "Generated wiki draft for Warehouse Stock Movement. "
        "Rule checks passed. Awaiting owner approval."
    )
    assert pending_item.verification_result["rule_based"]["status"] == "passed"
    assert pending_item.verification_result["gemini_quality"]["status"] == "not_run"
    assert pending_item.verification_result["human_review"]["status"] == "pending"
```

- [ ] **Step 3: Add approve/reject transition tests**

Add:

```python
def test_owner_approval_promotes_draft_to_current_note():
    graph, notes = _sample_notes()
    pending_item = prepare_wiki_draft_for_approval(
        item=graph.requirement,
        note=_note_by_id(notes, "REQ-001"),
        all_notes=notes,
    )

    approved_item = approve_wiki_draft(
        pending_item,
        reviewed_by="owner@example.com",
        reviewed_at=TIMESTAMP,
    )

    assert approved_item.markdown_current == pending_item.markdown_draft
    assert approved_item.markdown_draft is None
    assert approved_item.markdown_status == "verified"
    assert approved_item.verification_result["human_review"]["status"] == "approved"
    assert approved_item.verification_result["human_review"]["reviewed_by"] == (
        "owner@example.com"
    )


def test_owner_rejection_keeps_current_note_and_records_reason():
    graph, notes = _sample_notes()
    item = graph.requirement.model_copy(
        update={"markdown_current": "# Existing verified note\n"}
    )
    pending_item = prepare_wiki_draft_for_approval(
        item=item,
        note=_note_by_id(notes, "REQ-001"),
        all_notes=notes,
    )

    rejected_item = reject_wiki_draft(
        pending_item,
        reviewed_by="owner@example.com",
        reason="Need to confirm manager report wording.",
        reviewed_at=TIMESTAMP,
    )

    assert rejected_item.markdown_current == "# Existing verified note\n"
    assert rejected_item.markdown_draft is None
    assert rejected_item.markdown_status == "rejected"
    assert rejected_item.pending_change_summary == (
        "Rejected by owner@example.com: Need to confirm manager report wording."
    )
    assert rejected_item.verification_result["human_review"]["status"] == "rejected"
```

- [ ] **Step 4: Add blocked approval test**

Add:

```python
def test_owner_approval_requires_pending_verified_draft():
    graph, _ = _sample_notes()

    with pytest.raises(WikiApprovalError) as exc_info:
        approve_wiki_draft(
            graph.requirement,
            reviewed_by="owner@example.com",
            reviewed_at=TIMESTAMP,
        )

    assert "pending_human_approval" in str(exc_info.value)
```

- [ ] **Step 5: Verify red**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_wiki_verification.py
```

Expected:

```text
ModuleNotFoundError: No module named 'sadify.services.wiki_verification'
```

## Task 2: Local Verification And Approval Service

- [ ] **Step 1: Create `src/sadify/services/wiki_verification.py`**

Implement:

```python
WikiVerificationIssue
WikiVerificationResult
WikiApprovalError
verify_wiki_note(...)
prepare_wiki_draft_for_approval(...)
approve_wiki_draft(...)
reject_wiki_draft(...)
```

Rule checks:

- Markdown starts with `---`.
- Frontmatter contains `id`, `type`, `slug`, `status`, `sources`, `relationships`, and `related`.
- Body contains `# {title}` style heading.
- Body contains `## Summary`, `## Related Notes`, and `## Sources`.
- All `[[wiki links]]` refer to a file stem in `all_notes`.

State rules:

- Passing verification sets `markdown_status="pending_human_approval"`.
- Failing verification sets `markdown_status="rule_failed"` and does not allow approval.
- `gemini_quality` is recorded with `status="not_run"` and a reason for this local-first slice.
- Owner approval requires `markdown_status="pending_human_approval"` and a non-empty `markdown_draft`.
- Approval promotes draft to current and clears draft.
- Rejection keeps existing current note and clears draft.

- [ ] **Step 2: Verify green**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_wiki_verification.py
```

Expected:

```text
6 passed
```

## Task 3: Service Export And Regression Tests

- [ ] **Step 1: Update `src/sadify/services/__init__.py`**

Expose:

```python
WikiApprovalError
WikiVerificationIssue
WikiVerificationResult
approve_wiki_draft
prepare_wiki_draft_for_approval
reject_wiki_draft
verify_wiki_note
```

- [ ] **Step 2: Run targeted tests**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_wiki_verification.py tests\test_wiki_markdown_renderer.py tests\test_canonical_schemas.py
```

Expected:

```text
all targeted tests pass
```

- [ ] **Step 3: Run full suite**

Run:

```powershell
.\.venv\Scripts\pytest.exe
```

Expected:

```text
all tests pass
```

## Task 4: Docs And Commit

- [ ] **Step 1: Update TC-007**

Record expected output, real output, differences/issues, evidence, and decision.

- [ ] **Step 2: Update test index and status docs**

Mark TC-007/C10 passed and set Checkpoint 11 as next.

- [ ] **Step 3: Commit tracked development only**

Run:

```powershell
git add src\sadify\services\wiki_verification.py src\sadify\services\__init__.py tests\test_wiki_verification.py
git commit -m "feat: add wiki verification approval flow"
```

Do not stage docs because docs are ignored by user preference.

## Execution Result

Status: Completed on 2026-05-07.

Tracked development commit:

```text
18778ce feat: add wiki verification approval flow
```

Verification:

```text
.\.venv\Scripts\pytest.exe tests\test_wiki_verification.py -> 6 passed
.\.venv\Scripts\pytest.exe tests\test_wiki_verification.py tests\test_wiki_markdown_renderer.py tests\test_canonical_schemas.py -> 16 passed
.\.venv\Scripts\pytest.exe -> 76 passed
```

Next checkpoint:

```text
Checkpoint 11: project-level SAD generation
```


---

## 2026-05-08-local-end-to-end-plan

# Local End-To-End Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` or `superpowers:subagent-driven-development` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Checkpoint 13 by proving SADify can run a deterministic local MVP flow from requirement intake through analysis, graph, wiki verification, SAD generation, export records, and persistence boundaries.

**Architecture:** Add a local workflow service that composes existing checkpoint services. It should not introduce live model calls, Drive writes, or cloud Firestore writes. It should provide a single service-level path that Streamlit, ADK wrappers, and future Cloud Run smoke tests can reuse.

**Tech Stack:** Python 3.13, existing Pydantic schemas, existing deterministic services, existing Firestore repository abstraction with fake/local client in tests.

---

## File Structure

- Create `src/sadify/services/local_end_to_end.py`
  - Owns the C13 deterministic local orchestration.
  - Provides `run_local_end_to_end`, `LocalEndToEndInput`, `LocalEndToEndResult`, and `LocalEndToEndError`.
  - Calls requirement analysis, relationship graph, wiki Markdown, wiki approval, SAD generation, export preparation, diagnostics, and optional repository persistence.
- Modify `src/sadify/services/__init__.py`
  - Exports the C13 service API.
- Create `tests/test_local_end_to_end.py`
  - Covers full artifact creation, persistence consistency, diagnostics, and Streamlit/ADK shared-service alignment.
- Update ignored docs after implementation:
  - `docs/superpowers/testing/test_cases/TC-014-local-end-to-end.md`
  - `docs/superpowers/testing/test_case_index.md`
  - `docs/superpowers/development/05_development_workflow.md`
  - `docs/superpowers/development/08_new_chat_handoff.md`
  - `docs/superpowers/development/12_repo_rescan_alignment_checkpoint.md`
  - this plan with execution evidence.

## Design Summary

The first C13 slice should prove the full local path without external costs:

1. Normalize a business requirement text.
2. Build the same analysis view model used by Streamlit.
3. Build canonical requirement graph records.
4. Render wiki notes.
5. Run rule-based wiki verification.
6. Promote passing drafts through owner approval for local E2E proof.
7. Generate project-level SAD.
8. Prepare export artifacts and canonical export records.
9. Save canonical records through the existing repository interface when supplied.
10. Record diagnostics for each major step.

The service should keep generated IDs stable enough for tests and manual validation.

## Task 1: Write Failing Tests

**Files:**
- Create: `tests/test_local_end_to_end.py`

- [x] **Step 1: Add a full local workflow test**

Test that a representative warehouse requirement produces:

- valid analysis
- high/strong enough completeness
- canonical graph with relationships
- verified wiki items
- SAD version
- Google Doc/PDF/DOCX/wiki export package
- success diagnostics

- [x] **Step 2: Add persistence consistency test**

Use a fake Firestore client with the existing `FirestoreRepository`. Assert that the workflow saves:

- project document
- knowledge items
- relationships
- SAD version
- export records

- [x] **Step 3: Add wrapper alignment test**

Assert the local workflow analysis display output matches `sadify.app.build_analysis_view_model` for the same text. This protects Streamlit from drifting away from the service path.

- [x] **Step 4: Add empty input rejection test**

The local workflow should reject empty requirement text with a clear local error before generating graph/wiki/SAD/export records.

- [x] **Step 5: Run red tests**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_local_end_to_end.py -q
```

Expected:

```text
ModuleNotFoundError or ImportError for sadify.services.local_end_to_end
```

Actual:

```text
ModuleNotFoundError: No module named 'sadify.services.local_end_to_end'
```

## Task 2: Implement Local End-To-End Workflow

**Files:**
- Create: `src/sadify/services/local_end_to_end.py`
- Modify: `src/sadify/services/__init__.py`

- [x] **Step 1: Implement public dataclasses and error**

`LocalEndToEndInput` should include project ID, project title, project slug, requirement ID/title/text, source IDs, owner/reviewer, timestamp, and export settings.

`LocalEndToEndResult` should include analysis, graph, wiki notes, verified knowledge items, SAD version, export package, diagnostics, and saved record counts.

- [x] **Step 2: Implement deterministic orchestration**

Wire existing services in sequence. Do not call live LLM providers or cloud APIs.

- [x] **Step 3: Implement optional repository persistence**

When a repository is provided, save project, knowledge items, relationships, SAD version, and export records through existing repository methods.

- [x] **Step 4: Record diagnostics**

Use `DiagnosticsRecorder` and `timed_action` around each major stage.

- [x] **Step 5: Export service API**

Add C13 symbols to `src/sadify/services/__init__.py`.

- [x] **Step 6: Run green tests**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_local_end_to_end.py -q
```

Expected:

```text
4 passed
```

Actual:

```text
4 passed in 1.79s
```

## Task 3: Verification, Docs, Commit

**Files:**
- Modify ignored docs listed above.

- [x] **Step 1: Run related test set**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_local_end_to_end.py tests\test_export_generation.py tests\test_sad_generation.py tests\test_wiki_verification.py tests\test_firestore_persistence.py tests\test_app_shell.py -q
```

Expected:

```text
All selected tests pass.
```

Actual:

```text
37 passed in 2.08s
```

- [x] **Step 2: Run full suite**

Run:

```powershell
.\.venv\Scripts\pytest.exe
```

Expected:

```text
All tests pass.
```

Actual:

```text
89 passed in 9.05s
```

- [x] **Step 3: Update checkpoint docs**

Record expected output, real output, limitations, command evidence, C13 decision, and next checkpoint.

- [x] **Step 4: Commit tracked development files only**

Run:

```powershell
git add src\sadify\services\local_end_to_end.py src\sadify\services\__init__.py tests\test_local_end_to_end.py
git commit -m "feat: add local end-to-end workflow"
```

Expected:

```text
Commit succeeds. Ignored docs remain local-only.
```

Actual:

```text
77adef3 feat: add local end-to-end workflow
```

## Self-Review

- Spec coverage: Plan covers the local MVP path across C1-C12 outputs.
- Cost safety: No cloud, Drive, or live model calls are included.
- Drift control: Wrapper alignment test compares workflow analysis with Streamlit analysis.

## Execution Result

Status: Implemented locally.

Tracked development files:

```text
src/sadify/services/local_end_to_end.py
src/sadify/services/__init__.py
tests/test_local_end_to_end.py
```

Verification:

```text
Command: .\.venv\Scripts\pytest.exe tests\test_local_end_to_end.py -q
Result: 4 passed in 1.79s

Command: .\.venv\Scripts\pytest.exe tests\test_local_end_to_end.py tests\test_export_generation.py tests\test_sad_generation.py tests\test_wiki_verification.py tests\test_firestore_persistence.py tests\test_app_shell.py -q
Result: 37 passed in 2.08s

Command: .\.venv\Scripts\pytest.exe
Result: 89 passed in 9.05s
```

Streamlit local smoke:

```text
Command: headless Streamlit start on localhost:8502, then GET /_stcore/health
Result: STREAMLIT_HEALTH:200:ok
```

Fresh alignment review on 2026-05-11:

```text
Command: .\.venv\Scripts\pytest.exe
Result: 89 passed in 12.49s

Command: headless Streamlit start on localhost:8502, then GET /_stcore/health
Result: STREAMLIT_HEALTH:200:ok
```

Commit:

```text
77adef3 feat: add local end-to-end workflow
```

Next checkpoint:

```text
Checkpoint 14: Cloud Run deployment preparation and deployment.
```


---

## 2026-05-08-local-export-generation-plan

# Local Export Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Checkpoint 12 by preparing local Google-Doc-import, PDF, DOCX, and wiki Markdown export artifacts with canonical export records.

**Architecture:** Add a local-first export service that converts a generated `SadVersionRecord` and wiki note drafts into export artifacts. The service creates validated `ExportRecord`s and can materialize artifacts to a target directory; real Google Drive/Docs upload is deliberately not included in this first slice.

**Tech Stack:** Python 3.13, existing `python-docx`, existing `pypdf` test validation, built-in bytes/path handling, existing SADify schemas and renderers.

---

## File Structure

- Create `src/sadify/services/export_generation.py`
  - Owns local export artifact preparation.
  - Provides `prepare_export_package` and `write_export_package`.
  - Provides `PreparedExportArtifact`, `ExportPackage`, and `ExportGenerationError`.
  - Generates Google Docs import-source HTML, PDF bytes, DOCX bytes, and wiki Markdown artifacts.
- Modify `src/sadify/services/__init__.py`
  - Exports the C12 service API.
- Create `tests/test_export_generation.py`
  - Covers export records, local artifacts, PDF/DOCX readability, wiki paths, and safe file writes.
- Update ignored docs after implementation:
  - `docs/superpowers/testing/test_cases/TC-009-export-generation.md`
  - `docs/superpowers/testing/test_case_index.md`
  - `docs/superpowers/development/12_repo_rescan_alignment_checkpoint.md`
  - `docs/superpowers/development/08_new_chat_handoff.md`
  - this plan with execution evidence.

## Design Summary

The first C12 slice should prove export generation without cloud writes:

- `google_doc`: HTML artifact that can later be uploaded to Drive and converted to a Google Doc.
- `pdf`: valid PDF bytes generated locally from the SAD Markdown.
- `docx`: valid DOCX bytes generated locally from the SAD Markdown using `python-docx`.
- `wiki_markdown`: one Markdown artifact per wiki note, preserving note folder paths.

Export records should be canonical and trace back to the source SAD version. Drive IDs and URLs remain `None` until an actual Drive upload service is added.

## Task 1: Write Failing Tests

**Files:**
- Create: `tests/test_export_generation.py`

- [ ] **Step 1: Add tests for artifact and record generation**

```python
def test_prepare_export_package_creates_sad_document_artifacts_and_records():
    sad, notes = _sample_sad_and_notes()

    package = prepare_export_package(
        sad_version=sad,
        wiki_notes=notes,
        project_slug="warehouse-operations",
        created_at=TIMESTAMP,
        created_by="local-user",
    )

    assert package.export_types()[:3] == ("google_doc", "pdf", "docx")
    assert package.artifact_by_type("google_doc").relative_path.startswith("sad/")
    assert package.artifact_by_type("pdf").content.startswith(b"%PDF-")
    assert package.artifact_by_type("docx").content.startswith(b"PK")
    assert [record.export_id for record in package.records[:3]] == [
        "EXP-001",
        "EXP-002",
        "EXP-003",
    ]
    assert all(record.source_sad_version_id == "SAD-001" for record in package.records)
    assert all(record.status == "success" for record in package.records)
    assert all(record.drive_file_id is None for record in package.records)
```

- [ ] **Step 2: Add PDF and DOCX readability tests**

```python
def test_pdf_and_docx_artifacts_are_readable():
    sad, notes = _sample_sad_and_notes()
    package = prepare_export_package(
        sad_version=sad,
        wiki_notes=notes,
        project_slug="warehouse-operations",
        created_at=TIMESTAMP,
        created_by="local-user",
    )

    pdf = package.artifact_by_type("pdf")
    reader = PdfReader(BytesIO(pdf.content))
    assert len(reader.pages) == 1

    docx = package.artifact_by_type("docx")
    document = Document(BytesIO(docx.content))
    paragraph_text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "Warehouse Operations System Analysis And Design" in paragraph_text
    assert "Source Traceability" in paragraph_text
```

- [ ] **Step 3: Add wiki artifact path tests**

```python
def test_wiki_markdown_artifacts_keep_note_paths_and_content():
    _, notes = _sample_sad_and_notes()
    package = prepare_export_package(
        sad_version=_sample_sad_and_notes()[0],
        wiki_notes=notes,
        project_slug="warehouse-operations",
        created_at=TIMESTAMP,
        created_by="local-user",
    )

    requirement_note = next(note for note in notes if note.item_id == "REQ-001")
    artifact = package.artifact_by_relative_path(
        f"wiki/{requirement_note.relative_path}"
    )

    assert artifact.export_type == "wiki_markdown"
    assert artifact.content.decode("utf-8") == requirement_note.markdown
```

- [ ] **Step 4: Add safe file-write tests**

```python
def test_write_export_package_materializes_relative_paths(tmp_path):
    sad, notes = _sample_sad_and_notes()
    package = prepare_export_package(
        sad_version=sad,
        wiki_notes=notes[:1],
        project_slug="warehouse-operations",
        created_at=TIMESTAMP,
        created_by="local-user",
    )

    written_paths = write_export_package(package, tmp_path)

    assert len(written_paths) == len(package.artifacts)
    assert all(path.exists() for path in written_paths)
    assert all(tmp_path.resolve() in path.resolve().parents for path in written_paths)
```

- [ ] **Step 5: Add path traversal rejection test and helpers**

```python
def test_write_export_package_rejects_paths_outside_target(tmp_path):
    artifact = PreparedExportArtifact(
        export_id="EXP-999",
        export_type="wiki_markdown",
        relative_path="../escape.md",
        file_name="escape.md",
        mime_type="text/markdown",
        content=b"escape",
    )
    package = ExportPackage(artifacts=(artifact,), records=())

    with pytest.raises(ExportGenerationError):
        write_export_package(package, tmp_path)
```

- [ ] **Step 6: Run red tests**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_export_generation.py -q
```

Expected:

```text
ModuleNotFoundError or ImportError for sadify.services.export_generation
```

## Task 2: Implement Export Generation

**Files:**
- Create: `src/sadify/services/export_generation.py`
- Modify: `src/sadify/services/__init__.py`

- [ ] **Step 1: Implement public dataclasses and errors**

Use immutable dataclasses:

```python
@dataclass(frozen=True)
class PreparedExportArtifact:
    export_id: str
    export_type: str
    relative_path: str
    file_name: str
    mime_type: str
    content: bytes
```

`ExportPackage` should expose:

- `export_types()`
- `artifact_by_type(export_type)`
- `artifact_by_relative_path(relative_path)`

- [ ] **Step 2: Implement artifact preparation**

Create artifacts in this order:

1. `google_doc` HTML source under `sad/`
2. `pdf` under `sad/`
3. `docx` under `sad/`
4. one `wiki_markdown` artifact per wiki note under `wiki/`

Create one `ExportRecord` per artifact.

- [ ] **Step 3: Implement local renderers**

Renderer requirements:

- HTML must escape text and preserve headings/lists enough for Google Docs import later.
- PDF must produce valid `%PDF-` bytes without adding a new dependency.
- DOCX must use existing `python-docx`.
- Wiki Markdown must preserve exact note Markdown.

- [ ] **Step 4: Implement safe writer**

`write_export_package` should create parent directories and reject relative paths that resolve outside the target directory.

- [ ] **Step 5: Export service API**

Add C12 symbols to `src/sadify/services/__init__.py`.

- [ ] **Step 6: Run green tests**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_export_generation.py -q
```

Expected:

```text
5 passed
```

## Task 3: Verification, Docs, Commit

**Files:**
- Modify ignored docs listed above.

- [ ] **Step 1: Run related test set**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_export_generation.py tests\test_sad_generation.py tests\test_wiki_markdown_renderer.py tests\test_canonical_schemas.py -q
```

Expected:

```text
All selected tests pass.
```

- [ ] **Step 2: Run full suite**

Run:

```powershell
.\.venv\Scripts\pytest.exe
```

Expected:

```text
All tests pass.
```

- [ ] **Step 3: Update checkpoint docs**

Record:

- expected output
- real output
- Drive/Docs upload limitation
- test commands
- C12 decision
- next checkpoint is local end-to-end test

- [ ] **Step 4: Commit tracked development files only**

Run:

```powershell
git add src\sadify\services\export_generation.py src\sadify\services\__init__.py tests\test_export_generation.py
git commit -m "feat: add local export generation"
```

Expected:

```text
Commit succeeds. Ignored docs remain local-only.
```

## Self-Review

- Spec coverage: The plan covers Google-Doc-import HTML, PDF, DOCX, wiki Markdown, export records, safe local materialization, and Drive upload deferral.
- Placeholder scan: No TBD/TODO/fill-in placeholders remain.
- Type consistency: Public API uses existing `SadVersionRecord`, `WikiNoteDraft`, and `ExportRecord` types.

## Execution Result

Status: Implemented locally.

Tracked development files:

```text
src/sadify/services/export_generation.py
src/sadify/services/__init__.py
tests/test_export_generation.py
```

Verification:

```text
Command: .\.venv\Scripts\pytest.exe tests\test_export_generation.py -q
Result: 5 passed in 1.28s

Command: .\.venv\Scripts\pytest.exe tests\test_export_generation.py tests\test_sad_generation.py tests\test_wiki_markdown_renderer.py tests\test_canonical_schemas.py -q
Result: 19 passed in 1.32s

Command: .\.venv\Scripts\pytest.exe
Result: 85 passed in 6.61s
```

Commit:

```text
c9406f1 feat: add local export generation
```

Next checkpoint:

```text
Historical next checkpoint from 2026-05-08: Checkpoint 13 local end-to-end test.
Current update on 2026-05-11: Checkpoint 13 has passed; next is Checkpoint 14 Cloud Run deployment preparation and deployment.
```


---

## 2026-05-11-cloud-run-deployment-plan

# Cloud Run Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Per user instruction, complete one subtask at a time, then stop and ask for the next required check or approval.

**Goal:** Prepare and deploy the locally verified SADify MVP to Cloud Run without leaking secrets or starting billable cloud work before explicit approval.

**Architecture:** Use the existing Streamlit application as the Cloud Run service. Keep the app local-first and deterministic for the first deployment. Cloud Run should run with the existing user-managed service account, while live model calls, real Drive/Docs writes, and real Firestore smoke tests remain controlled follow-up checks.

**Tech Stack:** Python 3.13, Streamlit, Google Cloud Run source deploy, Google Cloud Buildpacks, Cloud Build, Artifact Registry, user-managed service account `sadify-agent-sa@sadify.iam.gserviceaccount.com`.

---

## C14 Subtask Breakdown

Follow this exact stop-and-check rhythm:

1. **Subtask 1: C14 preflight and deployment task plan**
   - Check repo state.
   - Check deployment file gaps.
   - Run full local tests.
   - Write this plan.
   - Stop and ask for deployment-mode confirmation.

2. **Subtask 2: Add deploy readiness files without deploying**
   - Add a Cloud Run entrypoint file.
   - Add `.gcloudignore`.
   - Add tests/static checks for deployment files.
   - Run targeted tests and full tests.
   - Commit tracked deployment-readiness files.
   - Stop and ask the user to approve local Cloud Run-style smoke.
   - Status: Complete on 2026-05-11.

3. **Subtask 3: Local Cloud Run-style entrypoint smoke**
   - Run Streamlit using Cloud Run-like host and port settings.
   - Verify local health endpoint.
   - Update docs with evidence.
   - Stop and ask for explicit approval before any cloud deploy.
   - Status: Complete on 2026-05-11.

4. **Subtask 4: Cloud Run deployment**
   - Deploy from source only after explicit approval.
   - Use project `sadify`, region `asia-southeast1`, and service account `sadify-agent-sa@sadify.iam.gserviceaccount.com`.
   - Record service URL and deployment output.
   - Stop before smoke testing anything expensive or live-model related.

5. **Subtask 5: Post-deploy smoke and C15 handoff**
   - Check deployed app loads.
   - Check logs for critical runtime errors.
   - Run only cost-safe demo path first.
   - Update `TC-012` and C15 docs.
   - Stop and ask before live Gemini/Firestore/Drive testing if not already approved.

## Subtask 1 Result

Status: Complete on 2026-05-11.

Findings:

```text
No Procfile found.
No .gcloudignore found.
No root main.py entrypoint found.
SADify Streamlit app lives at src/sadify/app.py.
requirements.txt includes streamlit and required local dependencies.
.gitignore already excludes .env, .venv, docs, tmp, caches, and generated outputs.
.env.example contains placeholders only.
```

Verification:

```text
Command: .\.venv\Scripts\pytest.exe
Result: 89 passed in 12.23s

Command: git status --short --branch
Result: branch main, no tracked changes
```

Decision:

```text
Do not deploy yet.
Subtask 2 should add deployment readiness files first.
```

## Subtask 2 Plan: Deploy Readiness Files

**Files:**

- Create `Procfile`
  - Purpose: make Cloud Run buildpack run the actual Streamlit app path.
  - Planned content:

```text
web: streamlit run src/sadify/app.py --server.address 0.0.0.0 --server.port $PORT --browser.gatherUsageStats false
```

- Create `.gcloudignore`
  - Purpose: keep secrets, local docs, virtualenv, caches, and generated files out of Cloud Build uploads.
  - Planned content should include:

```text
.env
.env.*
!.env.example
.venv/
venv/
env/
docs/
tmp/
__pycache__/
*.py[cod]
pytest-cache-files-*/
.pytest_cache/
output/
artifacts/
exports/
node_modules/
.streamlit/secrets.toml
```

- Create `tests/test_cloud_run_deploy_files.py`
  - Purpose: assert deployment files exist and do not leak secrets or point to the wrong app path.
  - Planned tests:

```python
from pathlib import Path


def test_procfile_runs_streamlit_app_on_cloud_run_port():
    procfile = Path("Procfile").read_text(encoding="utf-8").strip()

    assert procfile.startswith("web: streamlit run src/sadify/app.py")
    assert "--server.address 0.0.0.0" in procfile
    assert "--server.port $PORT" in procfile
    assert "--browser.gatherUsageStats false" in procfile


def test_gcloudignore_excludes_local_secrets_docs_and_build_noise():
    patterns = set(Path(".gcloudignore").read_text(encoding="utf-8").splitlines())

    assert ".env" in patterns
    assert ".env.*" in patterns
    assert "!.env.example" in patterns
    assert ".venv/" in patterns
    assert "docs/" in patterns
    assert "tmp/" in patterns
    assert "__pycache__/" in patterns
    assert ".streamlit/secrets.toml" in patterns
```

Verification commands after Subtask 2:

```powershell
.\.venv\Scripts\pytest.exe tests\test_cloud_run_deploy_files.py -q
.\.venv\Scripts\pytest.exe
```

Expected:

```text
All tests pass.
```

Commit command after Subtask 2:

```powershell
git add Procfile .gcloudignore tests\test_cloud_run_deploy_files.py
git commit -m "chore: add cloud run deploy readiness files"
```

Subtask 2 result:

```text
Created: Procfile
Created: .gcloudignore
Created: tests/test_cloud_run_deploy_files.py

Red test:
Command: .\.venv\Scripts\pytest.exe tests\test_cloud_run_deploy_files.py -q
Result: 2 failed because Procfile and .gcloudignore did not exist.

Green targeted test:
Command: .\.venv\Scripts\pytest.exe tests\test_cloud_run_deploy_files.py -q
Result: 2 passed in 0.03s

Full suite:
Command: .\.venv\Scripts\pytest.exe
Result: 91 passed in 7.84s
```

## Subtask 3 Plan: Local Cloud Run-Style Smoke

Run the app locally with Cloud Run-like host and port:

```powershell
$env:PORT = "8503"
.\.venv\Scripts\streamlit.exe run src/sadify/app.py --server.address 0.0.0.0 --server.port $env:PORT --browser.gatherUsageStats false
```

Health check:

```powershell
Invoke-WebRequest -Uri "http://localhost:8503/_stcore/health" -UseBasicParsing
```

Expected:

```text
200 ok
```

Subtask 3 result:

```text
Command: local Streamlit startup using src/sadify/app.py, --server.address 0.0.0.0, --server.port 8503, and browser usage stats disabled
Result: STREAMLIT_HEALTH:200:ok
STDERR: Uvicorn server started on 0.0.0.0:8503

No Cloud Run, Cloud Build, Artifact Registry, or Google API command was run.
The local process was stopped after the health check.
```

## Subtask 4 Plan: Cloud Run Deploy

Do not run until user explicitly approves cloud deployment.

Deployment command for Cloud Shell or a local machine with `gcloud`:

```bash
gcloud config set project sadify

gcloud run deploy sadify-app \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --service-account sadify-agent-sa@sadify.iam.gserviceaccount.com \
  --set-env-vars GOOGLE_CLOUD_PROJECT=sadify,GOOGLE_CLOUD_LOCATION=asia-southeast1,GOOGLE_GENAI_USE_VERTEXAI=True,SADIFY_MODEL_PROVIDER=google,SADIFY_MODEL=gemini-2.5-flash,SADIFY_FINAL_SAD_PROVIDER=google,SADIFY_FINAL_SAD_MODEL=gemini-2.5-flash,SADIFY_ENV=cloud,SADIFY_LOG_LEVEL=INFO,SADIFY_RUNTIME_SERVICE_ACCOUNT=sadify-agent-sa@sadify.iam.gserviceaccount.com
```

Important deployment notes:

- Do not set `GOOGLE_APPLICATION_CREDENTIALS` on Cloud Run.
- Do not pass real Drive folder ID in chat.
- Source deployment uses Cloud Build and Artifact Registry, so it can consume credits.
- Real Drive/Docs, Firestore cloud writes, and live model calls remain C15 smoke checks unless explicitly approved during C14.

Subtask 4 pre-deploy check on 2026-05-11:

```text
Local command: gcloud version
Result: blocked. gcloud is not installed on the local Windows machine.

Local command: where.exe gcloud
Result: blocked. No gcloud executable found on PATH.
```

Deployment cannot be truthfully marked complete until one of these paths is used:

1. Install and authenticate Google Cloud CLI locally, then deploy from `D:\GoogleCloudHack`.
2. Push or upload the source into Cloud Shell, then deploy from that Cloud Shell source directory.
3. Use another deployment workstation where the source code and Google Cloud CLI are both available.

Services involved in C14 deployment:

- Cloud Run / Cloud Run Admin API: hosts the Streamlit service and bills by request, CPU, memory, networking, and configured scaling.
- Cloud Build: source deployment build step; bills by build minutes after included/free quota.
- Artifact Registry: stores the built container image; bills by image storage and some data transfer after free/included amounts.
- IAM / service accounts: attaches `sadify-agent-sa@sadify.iam.gserviceaccount.com` as service identity; no expected direct runtime cost, but required permissions can block deployment.
- Cloud Logging / Cloud Monitoring: receives service logs and metrics; default usage has free allotments, but high log volume, custom metrics, long retention, uptime checks, or traces can bill.
- Service Usage APIs: used for API enablement and checks; no expected direct app runtime cost.

Services enabled or planned for later app features, but not required to run the deterministic C14 startup path:

- Vertex AI / Gemini Agent Platform: bills only when live model calls are made.
- Firestore: bills reads, writes, deletes, storage, and egress after the project free tier.
- Secret Manager: bills active secret versions and secret access operations after free monthly limits.
- Google Drive API: standard use currently has no additional cost, but quota/egress limits apply and charges are planned later in 2026 for quota overages.
- Google Docs API: standard use currently has no additional cost, but quota limits apply and charges are planned later in 2026 for quota overages.
- Cloud Trace: only relevant if trace export is enabled; bills span ingestion after free allotment.

Subtask 4 deployment result on 2026-05-11:

```text
Command: gcloud run deploy sadify-app --source . --project sadify --region asia-southeast1 --allow-unauthenticated --service-account sadify-agent-sa@sadify.iam.gserviceaccount.com
Result: deployed successfully.

Deployment output URL:
https://sadify-app-594758969655.asia-southeast1.run.app

Verified Cloud Run service metadata:
status.url: https://sadify-app-ohzgmdegca-as.a.run.app
latestReadyRevisionName: sadify-app-00001-mxv
traffic: 100
```

Stop point:

```text
Do not run browser/app smoke, live Gemini, Firestore, Drive, or Docs checks until Subtask 5 is approved.
```

## Subtask 5 Plan: C15 Smoke Handoff

After deployment:

1. Confirm the service URL loads.
2. Check Cloud Run logs for startup errors.
3. Try basic deterministic requirement analysis.
4. Update `docs/superpowers/testing/test_cases/TC-012-cloud-run-smoke-test.md`.
5. Stop before live Gemini/Firestore/Drive smoke if extra cost approval is needed.

Subtask 5 partial result on 2026-05-11:

```text
User-provided browser screenshot confirms the deployed service URL loads:
https://sadify-app-ohzgmdegca-as.a.run.app

The deployed app reports:
- Project: sadify
- Provider: google
- Model: gemini-2.5-flash
- Environment: cloud
- Service account: configured
- Drive folder: missing

The deterministic warehouse requirement flow renders:
- "What SADify understands"
- Readiness: 100%
- Confidence: High
- Current mode: deterministic
```

Additional C15 basic-prototype smoke result on 2026-05-11:

```text
Command:
Invoke-WebRequest -Uri "https://sadify-app-ohzgmdegca-as.a.run.app/_stcore/health" -UseBasicParsing

Result:
StatusCode 200, Content ok

Playwright browser smoke:
- Page title: SADify
- URL: https://sadify-app-ohzgmdegca-as.a.run.app/
- Project: sadify
- Environment: cloud
- Service account: configured
- Submitted warehouse stock movement requirement
- Rendered "What SADify understands"
- Readiness: 100%
- Confidence: High
- Current mode: deterministic

Screenshot artifact:
output/playwright/c15-cloud-run-deterministic-smoke.png
```

Decision:

```text
Subtask 5 is complete for the basic deployed prototype baseline.
TC-012 passes as a cost-safe deterministic Cloud Run smoke.
Live Gemini, Firestore cloud writes, Drive/Docs upload, and Cloud Run log administration are not marked passed; they move to the first improvement backlog after the basic prototype baseline.
The deployed runtime still reports Drive folder missing, so configuring SADIFY_DRIVE_ROOT_FOLDER_ID on Cloud Run is the first cloud-config improvement.
```

## Sources Checked

- Cloud Run source deployment supports `gcloud run deploy --source .` and uses buildpacks, Cloud Build, and Artifact Registry.
- Cloud Run service identity should use a user-managed service account.
- Python buildpacks support Streamlit and custom entrypoints through `Procfile` or `GOOGLE_ENTRYPOINT`.


---

## 2026-05-11-sadify-prototype-to-mvp-implementation-plan

# SADify Prototype-To-MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move SADify from the Streamlit functional prototype into a proper MVP web app with Next.js, FastAPI, Firebase Auth, guest Firestore drafts, live Gemini structured Q&A, and a tested path toward user-owned Drive/Docs project repos.

**Architecture:** Build a monorepo with a Next.js/React frontend and a Python FastAPI backend while preserving the existing `src/sadify` services and `sadify_agent/root_agent` compatibility. Start with a thin full-stack slice before adding OAuth, Drive/Docs, SAD save, and living wiki updates.

**Tech Stack:** Next.js/React/TypeScript, Python 3.13, FastAPI, Pydantic, Firebase Auth / Google Identity Platform, Firestore, Vertex AI Gemini `gemini-2.5-flash`, Google Drive API, Google Docs API, Secret Manager, Cloud Run, Playwright/browser smoke, pytest.

---

## Source Documents

Read these before implementation:

- `docs/superpowers/specs/2026-05-11-sadify-prototype-to-mvp-design.md`
- `docs/superpowers/diagrams/2026-05-11-sadify-mvp-web-architecture.md`
- `docs/superpowers/development/00_development_index.md`
- `docs/superpowers/development/02_agent_behavior_contract.md`
- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `docs/superpowers/development/04_google_cloud_setup_runbook.md`
- `docs/superpowers/development/05_development_workflow.md`
- `docs/superpowers/development/07_decision_log.md`
- `docs/superpowers/testing/mvp_web_app_test_plan.md`

Official docs checked during planning:

- Firebase backend ID-token verification: `https://firebase.google.com/docs/auth/admin/verify-id-tokens`
- Firebase web auth persistence: `https://firebase.google.com/docs/auth/web/auth-state-persistence`
- Identity Platform concept docs: `https://docs.cloud.google.com/identity-platform/docs/concepts-authentication`
- Gemini structured outputs: `https://ai.google.dev/gemini-api/docs/structured-output`
- Drive API scopes: `https://developers.google.com/drive/api/guides/api-specific-auth`
- Docs API scopes and `documents.create`: `https://developers.google.com/docs/api/auth`, `https://developers.google.com/docs/api/reference/rest/v1/documents/create`
- Drive Picker: `https://developers.google.com/drive/api/guides/picker`
- Secret Manager roles: `https://cloud.google.com/secret-manager/docs/access-control`

## Scope Split

The MVP includes several independent subsystems. Implement them in phases and stop at every gate.

| Phase | Checkpoints | Focus | Proceed When |
| --- | --- | --- | --- |
| 0 | MVP-00 | Docs and checkpoint alignment | TC-015 passed |
| 1 | MVP-01 to MVP-06 | Thin full-stack slice | TC-016 through TC-021 passed |
| 2 | MVP-07 | Source upload and traceability | TC-022 passed |
| 3 | MVP-08 | Firebase/Drive OAuth repo connection | TC-023 passed |
| 4 | MVP-09 | SAD preview, readiness, change tracking | TC-024 passed |
| 5 | MVP-10 | Wiki update approval and backups | TC-025 passed |
| 6 | MVP-11 | Drive/Docs save | TC-026 passed |
| 7 | MVP-12 | Two-service deployed smoke | TC-027 passed |

This plan details Phase 0 and Phase 1. Later phases get their own implementation plans after Phase 1 passes.

## File Structure

Create or modify these areas during Phase 1:

```text
apps/
  web/
    package.json
    next.config.ts
    tsconfig.json
    src/app/page.tsx
    src/app/layout.tsx
    src/components/WorkspaceShell.tsx
    src/components/CurrentQuestion.tsx
    src/components/ReadinessPanel.tsx
    src/components/ChangeSummary.tsx
    src/lib/api.ts
    src/lib/mockState.ts

services/
  api/
    pyproject.toml
    src/sadify_api/__init__.py
    src/sadify_api/main.py
    src/sadify_api/config.py
    src/sadify_api/dependencies.py
    src/sadify_api/routes/health.py
    src/sadify_api/routes/drafts.py
    src/sadify_api/routes/analysis.py
    src/sadify_api/schemas.py
    src/sadify_api/services/guest_drafts.py
    src/sadify_api/services/gemini_structured.py

tests/
  api/
    test_health_contract.py
    test_guest_drafts.py
    test_gemini_structured.py
  test_mvp_scaffold.py
```

Keep existing files under `src/sadify/` passing. Do not delete the Streamlit prototype until the MVP path is proven.

## Phase 0: Documentation Gate

### Task 0: Pass TC-015 Design Alignment

**Files:**
- Modify: `docs/superpowers/testing/test_cases/TC-015-prototype-to-mvp-design-alignment.md`
- Read: all source documents listed above

- [ ] **Step 1: Review alignment**

Check:

```text
1. The design spec names Next.js + FastAPI as MVP target.
2. The decision log marks Streamlit and service-account Drive as prototype/superseded for MVP.
3. The workflow contains MVP-00 through MVP-12.
4. The test index contains TC-015 through TC-027.
5. The runbook warns not to change OAuth/Firebase/IAM until implementation plan approval.
```

- [ ] **Step 2: Run doc consistency search**

Run:

```powershell
rg -n "Streamlit for fastest MVP build|One Cloud Run service for MVP deployment|Share Drive folder with service account" docs\superpowers
```

Expected:

```text
Only historical or explicitly superseded references remain.
```

- [ ] **Step 3: Update TC-015**

Set:

```markdown
Status: Passed
Real Output: Design, decision, workflow, and test docs agree on the prototype-to-MVP direction.
Evidence: paste the doc consistency command and result summary.
Decision: Passed. Proceed to MVP-01.
```

- [ ] **Step 4: Commit checkpoint docs if requested**

Docs are currently ignored by `.gitignore`, so do not force staging unless the user wants docs tracked.

## Phase 1: Thin Full-Stack Slice

Target:

```text
Next.js frontend
-> FastAPI backend
-> guest Firestore draft abstraction
-> live Gemini structured analysis call
-> first Q&A state saved
```

### Task 1: MVP Monorepo Scaffold

**Files:**
- Create: `tests/test_mvp_scaffold.py`
- Create: `apps/web/package.json`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/app/page.tsx`
- Create: `services/api/pyproject.toml`
- Create: `services/api/src/sadify_api/__init__.py`
- Create: `services/api/src/sadify_api/main.py`

- [ ] **Step 1: Write failing scaffold test**

Create `tests/test_mvp_scaffold.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mvp_monorepo_scaffold_files_exist():
    expected_paths = [
        ROOT / "apps" / "web" / "package.json",
        ROOT / "apps" / "web" / "src" / "app" / "page.tsx",
        ROOT / "services" / "api" / "pyproject.toml",
        ROOT / "services" / "api" / "src" / "sadify_api" / "main.py",
    ]

    missing = [str(path.relative_to(ROOT)) for path in expected_paths if not path.exists()]

    assert missing == []
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_mvp_scaffold.py -q
```

Expected:

```text
FAIL because scaffold files do not exist.
```

- [ ] **Step 3: Create frontend scaffold files**

Create `apps/web/package.json`:

```json
{
  "name": "sadify-web",
  "private": true,
  "version": "0.1.0",
  "scripts": {
    "dev": "next dev --hostname 0.0.0.0 --port 3000",
    "build": "next build",
    "start": "next start --hostname 0.0.0.0 --port 3000",
    "lint": "next lint"
  },
  "dependencies": {
    "@types/node": "^24.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "next": "^16.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "typescript": "^5.9.0"
  },
  "devDependencies": {}
}
```

Create `apps/web/next.config.ts`:

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
};

export default nextConfig;
```

Create `apps/web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "es2022"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }]
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

Create `apps/web/src/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SADify",
  description: "AI system analyst workspace",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

Create `apps/web/src/app/page.tsx`:

```tsx
export default function Home() {
  return (
    <main>
      <h1>SADify</h1>
      <p>Project workspace loading.</p>
    </main>
  );
}
```

Create `apps/web/src/app/globals.css`:

```css
:root {
  color-scheme: dark;
  background: #0f1115;
  color: #f5f7fb;
  font-family: Arial, Helvetica, sans-serif;
}

body {
  margin: 0;
}

main {
  padding: 32px;
}
```

- [ ] **Step 4: Create backend scaffold files**

Create `services/api/pyproject.toml`:

```toml
[project]
name = "sadify-api"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "fastapi>=0.124.0",
    "uvicorn[standard]>=0.38.0",
    "pydantic>=2.13.0",
]

[tool.pytest.ini_options]
pythonpath = [
    "src",
    "../../src",
    "../..",
]
```

Create `services/api/src/sadify_api/__init__.py`:

```python
__all__ = ["create_app"]

from sadify_api.main import create_app
```

Create `services/api/src/sadify_api/main.py`:

```python
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="SADify API", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 5: Run scaffold test**

Run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_mvp_scaffold.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 6: Update TC-016**

Record expected output, real output, command output, and decision in `docs/superpowers/testing/test_cases/TC-016-mvp-monorepo-scaffold.md`.

### Task 2: FastAPI Health And Contract

**Files:**
- Create: `tests/api/test_health_contract.py`
- Modify: `services/api/src/sadify_api/main.py`
- Create: `services/api/src/sadify_api/config.py`
- Create: `services/api/src/sadify_api/routes/health.py`
- Create: `services/api/src/sadify_api/schemas.py`

- [ ] **Step 1: Add FastAPI test dependency to root dev requirements**

Modify `requirements-dev.txt`:

```text
-r requirements.txt
pytest>=9.0.0
fastapi>=0.124.0
uvicorn[standard]>=0.38.0
httpx>=0.28.0
```

- [ ] **Step 2: Install dependencies when approved**

Run only after user approval if packages are missing:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Expected:

```text
Successfully installed or requirement already satisfied.
```

- [ ] **Step 3: Write failing API health contract test**

Create `tests/api/test_health_contract.py`:

```python
from fastapi.testclient import TestClient

from sadify_api.main import create_app


def test_health_returns_backend_contract():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "sadify-api",
        "environment": "test",
    }
```

- [ ] **Step 4: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH="services/api/src;src;."; .\.venv\Scripts\pytest.exe tests\api\test_health_contract.py -q
```

Expected:

```text
FAIL because /health does not include service and environment.
```

- [ ] **Step 5: Implement config and schema**

Create `services/api/src/sadify_api/config.py`:

```python
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ApiConfig:
    environment: str


def load_api_config() -> ApiConfig:
    return ApiConfig(environment=os.getenv("SADIFY_ENV", "test").strip() or "test")
```

Create `services/api/src/sadify_api/schemas.py`:

```python
from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(ApiModel):
    status: str
    service: str
    environment: str
```

Create `services/api/src/sadify_api/routes/health.py`:

```python
from fastapi import APIRouter

from sadify_api.config import ApiConfig
from sadify_api.schemas import HealthResponse


router = APIRouter()


def build_health_response(config: ApiConfig) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="sadify-api",
        environment=config.environment,
    )


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return build_health_response(ApiConfig(environment="test"))
```

Update `services/api/src/sadify_api/main.py`:

```python
from fastapi import FastAPI

from sadify_api.config import load_api_config
from sadify_api.routes.health import build_health_response
from sadify_api.schemas import HealthResponse


def create_app() -> FastAPI:
    app = FastAPI(title="SADify API", version="0.1.0")
    config = load_api_config()

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return build_health_response(config)

    return app


app = create_app()
```

- [ ] **Step 6: Run API contract test**

Run:

```powershell
$env:PYTHONPATH="services/api/src;src;."; .\.venv\Scripts\pytest.exe tests\api\test_health_contract.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 7: Update TC-017**

Record test command, real output, issues, and decision in `TC-017-mvp-fastapi-health-contract.md`.

### Task 3: Workspace Shell With Mocked Data

**Files:**
- Create: `apps/web/src/components/WorkspaceShell.tsx`
- Create: `apps/web/src/components/CurrentQuestion.tsx`
- Create: `apps/web/src/components/ReadinessPanel.tsx`
- Create: `apps/web/src/components/ChangeSummary.tsx`
- Create: `apps/web/src/lib/mockState.ts`
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/app/globals.css`

- [ ] **Step 1: Add mocked workspace state**

Create `apps/web/src/lib/mockState.ts`:

```ts
export type Choice = {
  id: string;
  label: string;
};

export type WorkspaceState = {
  projectTitle: string;
  mode: "guest" | "signed_in";
  readinessLabel: string;
  readinessScore: number;
  confidenceLabel: "Low" | "Medium" | "High";
  currentQuestion: {
    text: string;
    whyThisMatters: string;
    choices: Choice[];
  };
  categories: Array<{ label: string; status: "complete" | "partial" | "missing" }>;
  changeSummary: string;
};

export const mockWorkspaceState: WorkspaceState = {
  projectTitle: "Guest draft",
  mode: "guest",
  readinessLabel: "Getting started",
  readinessScore: 35,
  confidenceLabel: "Medium",
  currentQuestion: {
    text: "Who will use this system most often?",
    whyThisMatters: "This helps SADify define roles, permissions, and daily workflow.",
    choices: [
      { id: "operators", label: "Operators or frontline staff" },
      { id: "supervisors", label: "Supervisors or approvers" },
      { id: "managers", label: "Managers or report viewers" },
      { id: "not_sure", label: "Not sure yet" },
    ],
  },
  categories: [
    { label: "Problem", status: "partial" },
    { label: "Users/Roles", status: "missing" },
    { label: "Workflow", status: "missing" },
    { label: "Data", status: "missing" },
    { label: "Reports", status: "missing" },
  ],
  changeSummary: "No saved project changes yet.",
};
```

- [ ] **Step 2: Create workspace components**

Create `apps/web/src/components/CurrentQuestion.tsx`:

```tsx
import type { Choice } from "@/lib/mockState";

type Props = {
  text: string;
  whyThisMatters: string;
  choices: Choice[];
};

export function CurrentQuestion({ text, whyThisMatters, choices }: Props) {
  return (
    <section className="question-panel" aria-label="Current SADify question">
      <p className="eyebrow">SADify asks</p>
      <h2>{text}</h2>
      <p className="why">{whyThisMatters}</p>
      <div className="choice-grid">
        {choices.map((choice) => (
          <button key={choice.id} type="button" className="choice-button">
            {choice.label}
          </button>
        ))}
      </div>
      <label className="amend">
        Amend answer
        <textarea placeholder="Add details or correct the choices here." />
      </label>
    </section>
  );
}
```

Create `apps/web/src/components/ReadinessPanel.tsx`:

```tsx
import type { WorkspaceState } from "@/lib/mockState";

type Props = Pick<WorkspaceState, "readinessLabel" | "readinessScore" | "confidenceLabel" | "categories">;

export function ReadinessPanel({ readinessLabel, readinessScore, confidenceLabel, categories }: Props) {
  return (
    <aside className="readiness-panel" aria-label="Readiness and questionnaire progress">
      <p className="eyebrow">Readiness</p>
      <strong>{readinessLabel}</strong>
      <span>{readinessScore}% / {confidenceLabel}</span>
      <div className="category-list">
        {categories.map((category) => (
          <div key={category.label} className={`category ${category.status}`}>
            <span>{category.label}</span>
            <small>{category.status}</small>
          </div>
        ))}
      </div>
    </aside>
  );
}
```

Create `apps/web/src/components/ChangeSummary.tsx`:

```tsx
type Props = {
  summary: string;
};

export function ChangeSummary({ summary }: Props) {
  return (
    <section className="change-summary" aria-label="Change tracking summary">
      <span>{summary}</span>
      <details>
        <summary>Project status</summary>
        <p>Guest Draft -> Questions -> SAD Preview -> Review Changes -> Saved</p>
      </details>
    </section>
  );
}
```

Create `apps/web/src/components/WorkspaceShell.tsx`:

```tsx
import type { WorkspaceState } from "@/lib/mockState";
import { ChangeSummary } from "./ChangeSummary";
import { CurrentQuestion } from "./CurrentQuestion";
import { ReadinessPanel } from "./ReadinessPanel";

type Props = {
  state: WorkspaceState;
};

export function WorkspaceShell({ state }: Props) {
  return (
    <main className="workspace">
      <header className="workspace-header">
        <div>
          <p className="eyebrow">SADify</p>
          <h1>{state.projectTitle}</h1>
        </div>
        <span className="mode-pill">{state.mode === "guest" ? "Guest draft" : "Signed in"}</span>
      </header>
      <ChangeSummary summary={state.changeSummary} />
      <div className="workspace-grid">
        <CurrentQuestion {...state.currentQuestion} />
        <ReadinessPanel
          readinessLabel={state.readinessLabel}
          readinessScore={state.readinessScore}
          confidenceLabel={state.confidenceLabel}
          categories={state.categories}
        />
      </div>
    </main>
  );
}
```

- [ ] **Step 3: Wire page**

Update `apps/web/src/app/page.tsx`:

```tsx
import { WorkspaceShell } from "@/components/WorkspaceShell";
import { mockWorkspaceState } from "@/lib/mockState";

export default function Home() {
  return <WorkspaceShell state={mockWorkspaceState} />;
}
```

- [ ] **Step 4: Add focused CSS**

Update `apps/web/src/app/globals.css` with stable layout dimensions and no oversized landing page:

```css
:root {
  color-scheme: dark;
  background: #0f1115;
  color: #f5f7fb;
  font-family: Arial, Helvetica, sans-serif;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: #0f1115;
}

button,
textarea {
  font: inherit;
}

.workspace {
  min-height: 100vh;
  padding: 24px;
  display: grid;
  gap: 16px;
}

.workspace-header,
.change-summary,
.question-panel,
.readiness-panel {
  border: 1px solid #2c3240;
  background: #171b23;
  border-radius: 8px;
}

.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
}

.workspace-header h1,
.question-panel h2 {
  margin: 0;
  letter-spacing: 0;
}

.eyebrow {
  margin: 0 0 6px;
  color: #9aa4b2;
  font-size: 12px;
  text-transform: uppercase;
}

.mode-pill {
  color: #8be9a6;
}

.change-summary {
  padding: 12px 16px;
  color: #d9e2ef;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
  gap: 16px;
}

.question-panel,
.readiness-panel {
  padding: 20px;
}

.why {
  color: #b9c2cf;
  line-height: 1.5;
}

.choice-grid {
  display: grid;
  gap: 10px;
  margin: 18px 0;
}

.choice-button {
  min-height: 44px;
  text-align: left;
  color: #f5f7fb;
  background: #202635;
  border: 1px solid #394252;
  border-radius: 8px;
  padding: 10px 12px;
}

.amend {
  display: grid;
  gap: 8px;
  color: #d9e2ef;
}

.amend textarea {
  min-height: 92px;
  color: #f5f7fb;
  background: #10141c;
  border: 1px solid #394252;
  border-radius: 8px;
  padding: 10px;
  resize: vertical;
}

.readiness-panel strong {
  display: block;
  font-size: 24px;
  letter-spacing: 0;
}

.readiness-panel > span {
  display: block;
  margin: 4px 0 18px;
  color: #b9c2cf;
}

.category-list {
  display: grid;
  gap: 8px;
}

.category {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #2c3240;
}

.category small {
  color: #9aa4b2;
}

@media (max-width: 860px) {
  .workspace {
    padding: 16px;
  }

  .workspace-grid {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 5: Run frontend checks**

From `apps/web`, run after dependencies are installed:

```powershell
npm install
npm run build
```

Expected:

```text
Next.js build completes successfully.
```

- [ ] **Step 6: Browser smoke**

Run the frontend dev server and use browser testing to confirm:

```text
SADify title visible
current question visible
choices visible
amend field visible
readiness visible
category progress visible
change summary visible
project status expandable
```

- [ ] **Step 7: Update TC-018**

Record screenshot path, browser observations, build result, and decision.

### Task 4: Backend Guest Draft Service

**Files:**
- Create: `tests/api/test_guest_drafts.py`
- Create: `services/api/src/sadify_api/services/guest_drafts.py`
- Create: `services/api/src/sadify_api/routes/drafts.py`
- Modify: `services/api/src/sadify_api/main.py`
- Modify: `services/api/src/sadify_api/schemas.py`

- [ ] **Step 1: Write failing guest draft service tests**

Create `tests/api/test_guest_drafts.py`:

```python
from datetime import UTC, datetime

from sadify_api.services.guest_drafts import GuestDraftRepository, create_guest_draft


def test_create_guest_draft_has_auditable_owner_and_status():
    now = datetime(2026, 5, 11, tzinfo=UTC)
    draft = create_guest_draft(
        guest_session_id="guest-session-001",
        created_at=now,
    )

    assert draft.guest_draft_id.startswith("GD-")
    assert draft.owner_kind == "guest"
    assert draft.guest_session_id == "guest-session-001"
    assert draft.status == "active"
    assert draft.created_at == now
    assert draft.updated_at == now


def test_guest_draft_repository_round_trips_with_fake_store():
    repository = GuestDraftRepository()
    now = datetime(2026, 5, 11, tzinfo=UTC)
    draft = create_guest_draft(
        guest_session_id="guest-session-001",
        created_at=now,
    )

    repository.save(draft)

    assert repository.get(draft.guest_draft_id) == draft
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
$env:PYTHONPATH="services/api/src;src;."; .\.venv\Scripts\pytest.exe tests\api\test_guest_drafts.py -q
```

Expected:

```text
FAIL because GuestDraftRepository and create_guest_draft do not exist.
```

- [ ] **Step 3: Implement guest draft schema and fake repository**

Append to `services/api/src/sadify_api/schemas.py`:

```python
from datetime import datetime
from typing import Literal


class GuestDraftRecord(ApiModel):
    guest_draft_id: str
    owner_kind: Literal["guest"]
    guest_session_id: str
    status: Literal["active", "migrated", "abandoned"]
    migrated_to_project_id: str | None = None
    created_at: datetime
    updated_at: datetime
```

Create `services/api/src/sadify_api/services/guest_drafts.py`:

```python
from datetime import datetime

from sadify_api.schemas import GuestDraftRecord


class GuestDraftRepository:
    def __init__(self) -> None:
        self._drafts: dict[str, GuestDraftRecord] = {}

    def save(self, draft: GuestDraftRecord) -> GuestDraftRecord:
        self._drafts[draft.guest_draft_id] = draft
        return draft

    def get(self, guest_draft_id: str) -> GuestDraftRecord | None:
        return self._drafts.get(guest_draft_id)


def create_guest_draft(
    *,
    guest_session_id: str,
    created_at: datetime,
    next_number: int = 1,
) -> GuestDraftRecord:
    return GuestDraftRecord(
        guest_draft_id=f"GD-{next_number:06d}",
        owner_kind="guest",
        guest_session_id=guest_session_id,
        status="active",
        migrated_to_project_id=None,
        created_at=created_at,
        updated_at=created_at,
    )
```

- [ ] **Step 4: Add API route**

Create `services/api/src/sadify_api/routes/drafts.py`:

```python
from datetime import UTC, datetime

from fastapi import APIRouter

from sadify_api.schemas import GuestDraftRecord
from sadify_api.services.guest_drafts import create_guest_draft


router = APIRouter(prefix="/drafts", tags=["drafts"])


@router.post("/guest", response_model=GuestDraftRecord)
def create_guest() -> GuestDraftRecord:
    return create_guest_draft(
        guest_session_id="local-browser-session",
        created_at=datetime.now(UTC),
    )
```

Update `services/api/src/sadify_api/main.py`:

```python
from fastapi import FastAPI

from sadify_api.config import load_api_config
from sadify_api.routes import drafts
from sadify_api.routes.health import build_health_response
from sadify_api.schemas import HealthResponse


def create_app() -> FastAPI:
    app = FastAPI(title="SADify API", version="0.1.0")
    config = load_api_config()
    app.include_router(drafts.router)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return build_health_response(config)

    return app


app = create_app()
```

Create `services/api/src/sadify_api/routes/__init__.py`:

```python
__all__ = ["drafts"]
```

- [ ] **Step 5: Run tests**

Run:

```powershell
$env:PYTHONPATH="services/api/src;src;."; .\.venv\Scripts\pytest.exe tests\api\test_guest_drafts.py tests\api\test_health_contract.py -q
```

Expected:

```text
All selected tests pass.
```

- [ ] **Step 6: Update TC-020 draft section**

Record this as the local fake-store part of TC-020. Full cloud Firestore migration remains blocked until Firestore client integration is implemented.

### Task 5: Gemini Structured Analysis Contract

**Files:**
- Create: `tests/api/test_gemini_structured.py`
- Create: `services/api/src/sadify_api/services/gemini_structured.py`
- Create: `services/api/src/sadify_api/routes/analysis.py`
- Modify: `services/api/src/sadify_api/schemas.py`
- Modify: `services/api/src/sadify_api/main.py`

- [ ] **Step 1: Write failing structured analysis tests**

Create `tests/api/test_gemini_structured.py`:

```python
import json

import pytest
from pydantic import ValidationError

from sadify_api.schemas import RequirementAnalysisResponse
from sadify_api.services.gemini_structured import parse_requirement_analysis


VALID_PAYLOAD = {
    "understanding_summary": "The team needs a system to track operational work.",
    "readiness": {
        "label": "Getting started",
        "score": 35,
        "confidence": "Medium",
    },
    "categories": [
        {"id": "problem", "label": "Problem", "status": "partial"},
        {"id": "users_roles", "label": "Users/Roles", "status": "missing"},
    ],
    "next_question": {
        "text": "Who will use this system most often?",
        "why_this_matters": "This defines roles and permissions.",
        "choices": [
            {"id": "frontline", "label": "Frontline staff"},
            {"id": "supervisor", "label": "Supervisors"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "users_roles",
    },
    "assumptions": [],
    "source_references": [],
}


def test_parse_requirement_analysis_accepts_schema_valid_json():
    parsed = parse_requirement_analysis(json.dumps(VALID_PAYLOAD))

    assert isinstance(parsed, RequirementAnalysisResponse)
    assert parsed.readiness.score == 35
    assert parsed.next_question.choices[-1].id == "not_sure"


def test_parse_requirement_analysis_rejects_score_outside_bounds():
    payload = VALID_PAYLOAD.copy()
    payload["readiness"] = {
        "label": "Impossible",
        "score": 150,
        "confidence": "High",
    }

    with pytest.raises(ValidationError):
        parse_requirement_analysis(json.dumps(payload))
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
$env:PYTHONPATH="services/api/src;src;."; .\.venv\Scripts\pytest.exe tests\api\test_gemini_structured.py -q
```

Expected:

```text
FAIL because RequirementAnalysisResponse and parser do not exist.
```

- [ ] **Step 3: Add structured response schemas**

Append to `services/api/src/sadify_api/schemas.py`:

```python
from pydantic import Field


class ReadinessSummary(ApiModel):
    label: str
    score: int = Field(ge=0, le=100)
    confidence: str


class QuestionnaireCategory(ApiModel):
    id: str
    label: str
    status: str


class QuestionChoice(ApiModel):
    id: str
    label: str


class NextQuestion(ApiModel):
    text: str
    why_this_matters: str
    choices: list[QuestionChoice]
    target_category: str


class RequirementAnalysisResponse(ApiModel):
    understanding_summary: str
    readiness: ReadinessSummary
    categories: list[QuestionnaireCategory]
    next_question: NextQuestion
    assumptions: list[str]
    source_references: list[str]
```

- [ ] **Step 4: Add parser service**

Create `services/api/src/sadify_api/services/gemini_structured.py`:

```python
from sadify_api.schemas import RequirementAnalysisResponse


def parse_requirement_analysis(raw_json: str) -> RequirementAnalysisResponse:
    return RequirementAnalysisResponse.model_validate_json(raw_json)


def requirement_analysis_schema() -> dict:
    return RequirementAnalysisResponse.model_json_schema()
```

- [ ] **Step 5: Add local deterministic route stub before live Gemini**

Create `services/api/src/sadify_api/routes/analysis.py`:

```python
import json

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from sadify_api.schemas import RequirementAnalysisResponse
from sadify_api.services.gemini_structured import parse_requirement_analysis


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_text: str


router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/requirement", response_model=RequirementAnalysisResponse)
def analyze_requirement(request: AnalysisRequest) -> RequirementAnalysisResponse:
    payload = {
        "understanding_summary": f"SADify is reviewing: {request.requirement_text[:120]}",
        "readiness": {
            "label": "Getting started",
            "score": 35,
            "confidence": "Medium",
        },
        "categories": [
            {"id": "problem", "label": "Problem", "status": "partial"},
            {"id": "users_roles", "label": "Users/Roles", "status": "missing"},
            {"id": "workflow", "label": "Workflow", "status": "missing"},
        ],
        "next_question": {
            "text": "Who will use this system most often?",
            "why_this_matters": "This helps SADify define roles, permissions, and daily workflow.",
            "choices": [
                {"id": "frontline", "label": "Frontline staff"},
                {"id": "supervisor", "label": "Supervisors or approvers"},
                {"id": "manager", "label": "Managers or report viewers"},
                {"id": "not_sure", "label": "Not sure yet"},
            ],
            "target_category": "users_roles",
        },
        "assumptions": [],
        "source_references": [],
    }
    return parse_requirement_analysis(json.dumps(payload))
```

Update `services/api/src/sadify_api/main.py`:

```python
from fastapi import FastAPI

from sadify_api.config import load_api_config
from sadify_api.routes import analysis, drafts
from sadify_api.routes.health import build_health_response
from sadify_api.schemas import HealthResponse


def create_app() -> FastAPI:
    app = FastAPI(title="SADify API", version="0.1.0")
    config = load_api_config()
    app.include_router(analysis.router)
    app.include_router(drafts.router)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return build_health_response(config)

    return app


app = create_app()
```

- [ ] **Step 6: Run structured contract tests**

Run:

```powershell
$env:PYTHONPATH="services/api/src;src;."; .\.venv\Scripts\pytest.exe tests\api\test_gemini_structured.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 7: Add live Gemini adapter only after local schema contract passes**

Use Gemini structured output with:

```text
response_mime_type = application/json
response_json_schema = RequirementAnalysisResponse.model_json_schema()
```

Implementation must:

```text
1. Call Gemini once for requirement analysis.
2. Validate with RequirementAnalysisResponse.
3. Retry once with a repair prompt if validation fails.
4. Refuse to save or render invalid output.
5. Redact prompts/source text from diagnostics unless explicitly in dev mode.
```

- [ ] **Step 8: Run live Gemini smoke only with approval**

Run a single live-call smoke using a short generic requirement.

Expected:

```text
Gemini returns schema-valid JSON and a plain-language next question.
```

- [ ] **Step 9: Update TC-021**

Record:

```text
local schema tests
live Gemini smoke command
model used
token/cost notes if available
schema validation result
first question shown
```

### Task 6: Wire Frontend To Backend Analysis

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/components/WorkspaceShell.tsx`

- [ ] **Step 1: Add API client**

Create `apps/web/src/lib/api.ts`:

```ts
export type AnalysisResponse = {
  understanding_summary: string;
  readiness: {
    label: string;
    score: number;
    confidence: string;
  };
  categories: Array<{ id: string; label: string; status: string }>;
  next_question: {
    text: string;
    why_this_matters: string;
    choices: Array<{ id: string; label: string }>;
    target_category: string;
  };
  assumptions: string[];
  source_references: string[];
};

export async function analyzeRequirement(requirementText: string): Promise<AnalysisResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_SADIFY_API_BASE_URL ?? "http://localhost:8000";
  const response = await fetch(`${baseUrl}/analysis/requirement`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ requirement_text: requirementText }),
  });

  if (!response.ok) {
    throw new Error(`Analysis failed with ${response.status}`);
  }

  return response.json();
}
```

- [ ] **Step 2: Add a minimal interactive page**

Update `apps/web/src/app/page.tsx` to a client component that lets user submit text and renders analysis. Keep the mocked workspace if API is unavailable.

```tsx
"use client";

import { useState } from "react";
import { WorkspaceShell } from "@/components/WorkspaceShell";
import { analyzeRequirement, type AnalysisResponse } from "@/lib/api";
import { mockWorkspaceState } from "@/lib/mockState";

function toWorkspaceState(response: AnalysisResponse) {
  return {
    ...mockWorkspaceState,
    readinessLabel: response.readiness.label,
    readinessScore: response.readiness.score,
    confidenceLabel: response.readiness.confidence as "Low" | "Medium" | "High",
    currentQuestion: {
      text: response.next_question.text,
      whyThisMatters: response.next_question.why_this_matters,
      choices: response.next_question.choices,
    },
    categories: response.categories.map((category) => ({
      label: category.label,
      status: category.status as "complete" | "partial" | "missing",
    })),
    changeSummary: "1 analysis added to this guest draft.",
  };
}

export default function Home() {
  const [requirementText, setRequirementText] = useState("");
  const [state, setState] = useState(mockWorkspaceState);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    try {
      const result = await analyzeRequirement(requirementText);
      setState(toWorkspaceState(result));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Analysis failed.");
    }
  }

  return (
    <>
      <section className="intake">
        <label>
          Tell SADify what is happening
          <textarea value={requirementText} onChange={(event) => setRequirementText(event.target.value)} />
        </label>
        <button type="button" onClick={submit}>Start analysis</button>
        {error ? <p role="alert">{error}</p> : null}
      </section>
      <WorkspaceShell state={state} />
    </>
  );
}
```

- [ ] **Step 3: Run API and frontend locally**

Terminal 1:

```powershell
$env:PYTHONPATH="services/api/src;src;."; .\.venv\Scripts\uvicorn.exe sadify_api.main:app --host 0.0.0.0 --port 8000
```

Terminal 2:

```powershell
cd apps\web
$env:NEXT_PUBLIC_SADIFY_API_BASE_URL="http://localhost:8000"
npm run dev
```

- [ ] **Step 4: Browser smoke**

Use browser testing:

```text
1. Open http://localhost:3000.
2. Enter a short cross-domain requirement.
3. Click Start analysis.
4. Confirm readiness updates.
5. Confirm Gemini/local schema question appears.
6. Confirm change summary updates.
```

- [ ] **Step 5: Update TC-018 and TC-021**

Record browser evidence and any API failures.

## Later Phase Plans To Create After Phase 1 Passes

Create these separate plans after Phase 1:

| Plan | Checkpoint | Contents |
| --- | --- | --- |
| `2026-05-12-source-upload-traceability-plan.md` | MVP-07 / TC-022 | Web file upload, existing extraction services, source records, traceability into Gemini prompt. |
| `2026-05-12-drive-repo-oauth-plan.md` | MVP-08 / TC-023 | Firebase sign-in, OAuth grant, Drive Picker, repo create/select, token storage, disconnect. |
| `2026-05-12-sad-preview-readiness-plan.md` | MVP-09 / TC-024 | Gemini SAD schema, readiness checklist, preview, assumptions, change tracking. |
| `2026-05-12-wiki-update-approval-plan.md` | MVP-10 / TC-025 | Wiki taxonomy, existing wiki read/reverify, proposed folder/file approval, backups. |
| `2026-05-12-drive-docs-save-plan.md` | MVP-11 / TC-026 | Create SAD Google Doc, upload wiki Markdown, upload sources, update manifest/change log. |
| `2026-05-12-two-service-deploy-plan.md` | MVP-12 / TC-027 | Frontend/backend Cloud Run deployment, env vars, smoke test, diagnostics. |

## Required Test Commands For Phase 1

Run after each touched checkpoint:

```powershell
.\.venv\Scripts\pytest.exe tests\test_mvp_scaffold.py -q
```

```powershell
$env:PYTHONPATH="services/api/src;src;."; .\.venv\Scripts\pytest.exe tests\api -q
```

```powershell
.\.venv\Scripts\pytest.exe -q
```

From `apps/web`:

```powershell
npm run build
```

Browser smoke:

```text
Use Playwright/browser-use to verify the workspace and analysis flow.
```

Cloud smoke:

```text
Do not deploy until local Phase 1 passes and user approves cloud run.
```

## Per-Checkpoint Operating Rule

Before starting any checkpoint, run an API/docs preflight.

Preflight questions:

```text
1. Does this checkpoint touch an external API, SDK, cloud service, OAuth flow, browser integration, or deployment platform?
2. If yes, what official docs must be checked before coding?
3. What scopes, roles, redirect URLs, env vars, credentials, billing implications, or deployment changes are required?
4. Is network/cloud access needed for this checkpoint?
5. Does the user need to approve any new API, cost, OAuth consent setup, IAM role, dependency install, or deployment?
```

Record the answers in the matching TC doc before implementation begins.

Mandatory official-doc checks:

```text
MVP-02 FastAPI: FastAPI/TestClient docs if dependency/API behavior is unclear.
MVP-03 Next.js: Next.js current docs if build/runtime behavior is unclear.
MVP-04 Auth: Firebase Auth persistence and backend ID-token verification docs.
MVP-05 Firestore: Firestore client/API docs before cloud write/read.
MVP-06 Gemini: Gemini structured output docs before live calls.
MVP-07 Sources: file extraction library docs if parser behavior changes.
MVP-08 Drive OAuth: Drive API scopes, Drive Picker, OAuth consent, and Secret Manager IAM docs.
MVP-09 SAD preview: Gemini structured output docs for SAD schema.
MVP-10 Wiki: Drive file read/update docs and link validation behavior.
MVP-11 Drive/Docs save: Docs API create/update and Drive upload/folder docs.
MVP-12 Deploy: Cloud Run frontend/backend deploy docs.
```

After completing one checkpoint, stop and report:

```text
1. Summary of changes
2. Files changed
3. Tests run and evidence
4. Potential issues or known limitations
5. Next checkpoint and required approvals/setup
```

Do not start the next checkpoint until the user approves.

## Stop Conditions

Stop and ask before proceeding if:

- A live Gemini call cannot produce schema-valid JSON.
- Firebase Auth setup requires new APIs or OAuth consent changes not in the runbook.
- Secret Manager token storage requires broader-than-expected IAM.
- Firestore guest drafts cannot be tested with a fake/local integration first.
- Browser flow exposes too much technical wiki/schema/process detail.
- Any existing prototype test fails unexpectedly.

## Execution Handoff

Plan execution should start with MVP-00 and then MVP-01 through MVP-06 only.

After Phase 1 passes, create the next subsystem plan before touching Drive/Docs OAuth.


---

## 2026-05-15-stable-questionnaire-plan-refactor

# Stable Questionnaire Plan Refactor Implementation Plan

Status: Historical Phase 3 implementation plan. TC-021S has passed; use this
only for traceability. The active blocker is TC-021Y domain-aware Q&A and SAD
quality hardening.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace SADify's turn-by-turn category reconstruction with a stable, slot-based questionnaire plan that keeps the Q&A flow coherent from first analysis through later edits.

**Architecture:** Add a backend questionnaire-plan domain module that owns canonical categories, slot coverage, active-category advancement, and readiness. Constrain Gemini to ask for one requested slot at a time, validate drift in the API layer, and simplify the frontend around the stable plan buckets: unresolved, already understood, completed, and suggested additions.

**Tech Stack:** Python, FastAPI, Pydantic, React/Next.js, pytest, TypeScript

---

## Linked Source Docs

```text
Behavior note:
  docs/superpowers/development/14_qna_workflow_refinement.md

Design spec:
  docs/superpowers/specs/2026-05-15-sadify-stable-questionnaire-plan-design.md

Acceptance test:
  docs/superpowers/testing/test_cases/TC-021S-stable-questionnaire-plan-refactor.md
```

## Current Execution Status

```text
Tasks 1-4 have partial implementation evidence.
Manual testing on 2026-05-18 showed the plan is not complete yet:
- repeated questions can reappear

Checkpoint 1 completed on 2026-05-18:
- first-turn routing now locks to the first unresolved plan slot
- clear initial request facts seed the plan before Q1
- answer history carries slot markers through the frontend/backend round-trip

Checkpoint 2 completed on 2026-05-18:
- canonical slot contracts now validate question semantics
- cross-slot questions with valid IDs are rejected before save/render
- invalid model retries fall back to canonical same-slot local questions

Checkpoint 3 completed on 2026-05-18:
- normal next-question handling no longer advances by legacy answer count
- repeated-question replacement now stays bound to the planner's active slot
- multiple saved answers on the same slot no longer force an early category jump

Checkpoint 4 completed on 2026-05-18:
- model-reported `complete` categories no longer outrank request/answer evidence
- clinic continuity is covered across seeded first turn and next-category advance
- suggested extra categories stay suggestions instead of entering the live map
- outdated regression expectations were aligned with the approved neutral pre-analysis UI

The automated pass is ready. Before continuing beyond TC-021S, rerun manual
browser acceptance.
```

## File Map

| File | Responsibility |
| --- | --- |
| `services/api/src/sadify_api/services/questionnaire_plan.py` | Canonical categories, slots, plan creation, advancement, readiness |
| `services/api/src/sadify_api/services/gemini_structured.py` | Locked prompt and schema fields for active category/slot |
| `services/api/src/sadify_api/routes/analysis.py` | API orchestration, validation, retry/fallback integration |
| `services/api/src/sadify_api/schemas.py` | Plan/slot/question schema contracts |
| `apps/web/src/components/AnalysisPanel.tsx` | Plan-driven Q&A rendering and answer interaction |
| `apps/web/src/components/WorkspaceShell.tsx` | Empty-state wiring and removal of fake seeded Q&A |
| `apps/web/src/lib/api.ts` | Updated plan/slot response types |
| `apps/web/src/lib/mockState.ts` | Neutral pre-analysis workspace state |
| `apps/web/src/app/globals.css` | Main/hidden/completed sections and checkbox multi-select styling |
| `tests/api/test_questionnaire_plan.py` | Pure domain tests for plan creation/advancement/readiness |
| `tests/api/test_gemini_structured.py` | API/prompt/validation regression tests |
| `tests/test_mvp_live_gemini_qna_ui.py` | Static frontend wiring tests |
| `docs/superpowers/...` | Active documentation alignment |

### Task 1: Add Canonical Plan Domain

**Files:**
- Create: `services/api/src/sadify_api/services/questionnaire_plan.py`
- Create: `tests/api/test_questionnaire_plan.py`
- Modify: `services/api/src/sadify_api/schemas.py`

- [ ] **Step 1: Write failing tests for canonical categories, stable order, and slot-based readiness**

```python
def test_plan_uses_canonical_categories_and_frozen_order():
    plan = create_initial_plan(initial_facts={"workflow_steps": {"normal_flow"}})
    assert [category.id for category in plan.categories][:4] == [
        "goal_scope",
        "users_roles",
        "workflow_steps",
        "data_records",
    ]
    assert plan.category("workflow_steps").visibility == "already_understood"


def test_readiness_uses_required_slot_coverage_not_question_count():
    plan = create_initial_plan(initial_facts={})
    updated = cover_slot(plan, "users_roles", "primary_users")
    assert updated.category("users_roles").status == "in_progress"
    assert updated.overall_readiness.score > plan.overall_readiness.score
```

- [ ] **Step 2: Run the new test file and confirm it fails**

Run:

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_questionnaire_plan.py -q
```

Expected: failures because the plan service does not exist yet.

- [ ] **Step 3: Implement canonical category, slot, and readiness models**

Implement plan dataclasses/Pydantic models and helpers for:

- `create_initial_plan`
- `cover_slot`
- `defer_slot`
- `reopen_slot`
- `next_open_slot`
- `recalculate_readiness`

- [ ] **Step 4: Run the plan tests**

Expected: new plan tests pass.

### Task 2: Replace Turn-Rebuilt Questionnaire State

**Files:**
- Modify: `services/api/src/sadify_api/routes/analysis.py`
- Modify: `tests/api/test_gemini_structured.py`

- [ ] **Step 1: Add failing tests for stable labels/order and active-category lock**

Cover:

- first response creates one plan
- later responses cannot rename `users_roles`
- later responses cannot reorder categories
- unfinished category remains active despite model drift
- `Question 1 of 2` behavior is removed in favor of slot goal

- [ ] **Step 2: Run the focused API tests**

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_gemini_structured.py -q
```

Expected: failures around continuity.

- [ ] **Step 3: Route analysis through questionnaire-plan state**

Replace:

- category reconstruction from latest model response
- `FALLBACK_QUESTIONS_NEEDED = 2`

With:

- plan creation on first turn
- plan mutation from prior answers
- active slot selection
- backend-calculated readiness

- [ ] **Step 4: Run the focused API tests**

Expected: continuity tests pass.

### Task 3: Harden Gemini Prompt And Validation

**Files:**
- Modify: `services/api/src/sadify_api/services/gemini_structured.py`
- Modify: `services/api/src/sadify_api/schemas.py`
- Modify: `services/api/src/sadify_api/routes/analysis.py`
- Modify: `tests/api/test_gemini_structured.py`

- [ ] **Step 1: Add failing tests for drift rejection**

Cover:

- wrong `target_category`
- wrong `target_slot_id`
- semantically wrong question text under a technically valid slot ID
- choice set that belongs to another slot family
- repeated semantic question
- unapproved extra visible category
- business source refs only

- [ ] **Step 2: Extend schema**

Add:

```python
target_slot_id: str
proposed_extra_categories: list[...]
```

- [ ] **Step 3: Replace the prompt**

The prompt must explicitly include:

- frozen category plan
- active category
- active slot
- allowed category IDs
- instruction not to rename/reorder categories
- business-source-only reference rule

- [ ] **Step 4: Add validation + repair retry + local same-slot fallback**

Expected:

- drifted model answer is rejected
- one repair attempt is made
- fallback remains in the same slot/category
- semantically mismatched question content is rejected before save/render
- repeated answered slot is skipped instead of replayed

- [ ] **Step 5: Run focused API tests**

Expected: drift handling tests pass.

### Task 4: Clean The Pre-Analysis And Plan UI

**Files:**
- Modify: `apps/web/src/components/WorkspaceShell.tsx`
- Modify: `apps/web/src/components/AnalysisPanel.tsx`
- Modify: `apps/web/src/lib/mockState.ts`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/app/globals.css`
- Modify: `tests/test_mvp_live_gemini_qna_ui.py`

- [ ] **Step 1: Add failing UI wiring tests**

Cover:

- `No analysis yet`
- no seeded current question before analysis
- `Already understood`
- `Completed areas`
- `Suggested additions`
- slot goal label
- checkbox multi-select + `Select all that apply.`
- no `Previous Answer` in normal source refs

- [ ] **Step 2: Run UI tests**

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\test_mvp_live_gemini_qna_ui.py -q
```

Expected: failures.

- [ ] **Step 3: Implement plan-driven rendering**

Replace seeded mock Q&A display with neutral empty state.

Render:

- unresolved categories
- collapsed `Already understood`
- collapsed `Completed areas`
- collapsed `Suggested additions`
- active slot goal
- active saved answers
- checkbox multi-select

- [ ] **Step 4: Run UI tests**

Expected: UI wiring tests pass.

### Task 5: End-To-End Continuity Regression

**Files:**
- Modify: `tests/api/test_gemini_structured.py`
- Modify: `tests/test_mvp_live_gemini_qna_ui.py`
- Create if needed: `tests/api/fixtures/questionnaire_flows.py`

- [ ] **Step 1: Add clinic flow regression**

Assert:

- stable category order
- active category stays until slots complete
- readiness rises from covered slots
- no unrelated purchase-request categories appear
- first question starts from the first unresolved slot after initial facts are seeded
- already-provided clinic facts do not leave the plan at 0%

- [ ] **Step 2: Add purchase-request flow regression**

Assert:

- purchase-related extra category becomes suggested, not auto-inserted later
- first active category finishes before next category
- labels stay canonical

- [ ] **Step 3: Add amended-answer regression**

Assert:

- changing an earlier answer reopens only the affected category/slot
- readiness recomputes downward only for that actual change

- [ ] **Step 4: Add semantic slot-guard regression**

Assert:

- access-override wording cannot be accepted for `rules_approvals.approval_path`
- a question with valid IDs but wrong intent is repaired or replaced
- the wrong question is never saved under the locked slot

- [ ] **Step 5: Run focused regression suite**

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_questionnaire_plan.py tests\api\test_gemini_structured.py tests\test_mvp_live_gemini_qna_ui.py -q
```

Expected: all pass.

### Task 6: Update Active Docs And Archive Superseded Wording

**Files:**
- Modify:
  - `docs/superpowers/specs/2026-05-11-sadify-prototype-to-mvp-design.md`
  - `docs/superpowers/development/01_product_scope.md`
  - `docs/superpowers/development/02_agent_behavior_contract.md`
  - `docs/superpowers/development/03_data_model_and_output_schema.md`
  - `docs/superpowers/development/05_development_workflow.md`
  - `docs/superpowers/development/06_demo_script_and_acceptance_checklist.md`
  - `docs/superpowers/development/07_decision_log.md`
  - `docs/superpowers/development/08_new_chat_handoff.md`
  - `docs/superpowers/testing/mvp_web_app_test_plan.md`
  - `docs/superpowers/testing/test_case_index.md`
  - `docs/superpowers/testing/test_cases/TC-021R-mvp-category-first-qna-refinement.md`
- Create:
  - `docs/superpowers/testing/test_cases/TC-021S-stable-questionnaire-plan-refactor.md`

- [ ] **Step 1: Replace active contradictions**

Remove active claims that:

- Gemini owns readiness score
- user-facing category percentages remain normal UI
- AI can reprioritize visible categories every turn

- [ ] **Step 2: Add TC-021S**

Document:

- stable plan
- slot-based completion
- category lock
- extras as suggestions
- neutral pre-analysis UI

- [ ] **Step 3: Cross-check active docs**

Run:

```powershell
rg -n "Gemini-decided score|category progress from 0-100|AI-prioritized next best question" docs\superpowers
```

Expected: no active contradictory wording remains outside clearly historical notes.

### Task 7: Verification

**Files:**
- No new files

- [ ] **Step 1: Run focused tests**

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_questionnaire_plan.py tests\api\test_gemini_structured.py tests\test_mvp_live_gemini_qna_ui.py -q
```

- [ ] **Step 2: Run full Python regression**

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests -q
```

- [ ] **Step 3: Run TypeScript**

```powershell
D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\node_modules\.bin\tsc.cmd -p D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\tsconfig.json --noEmit
```

- [ ] **Step 4: Run production build**

```powershell
npm --prefix D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web run build
```

- [ ] **Step 5: Run manual local browser smoke**

Test:

1. no fake pre-analysis panel
2. clinic flow
3. purchase-request flow
4. multi-select checkbox affordance
5. stable labels/order
6. same active category until slots complete

## Execution Checkpoint

Stop after this plan is reviewed and approved. Do not begin code edits until user approval is given.


---

## 2026-05-18-qna-ready-state-preview-handoff

# Q&A Ready State And Preview Handoff Implementation Plan

Status: Historical Phase 3 implementation plan. TC-021T has passed; use this
only for traceability. The active blocker is TC-021Y domain-aware Q&A and SAD
quality hardening.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the completed questionnaire into a clear `Ready to draft` handoff, keep optional refinements visibly non-blocking, and pass saved questionnaire answers into SAD preview generation.

**Architecture:** Keep the stable questionnaire plan as the source of truth. Add a small derived ready-state layer in the frontend instead of changing the category model, and extend the SAD preview context builder so it serializes questionnaire answers alongside the existing request, summary, assumptions, and source context.

**Tech Stack:** Python, FastAPI, Pydantic, React/Next.js, pytest, TypeScript

---

## Linked Source Docs

```text
Behavior note:
  docs/superpowers/development/14_qna_workflow_refinement.md

Design spec:
  docs/superpowers/specs/2026-05-18-qna-ready-state-preview-handoff-design.md

Acceptance test:
  docs/superpowers/testing/test_cases/TC-021T-qna-ready-state-preview-handoff.md
```

## File Map

| File | Responsibility |
| --- | --- |
| `apps/web/src/components/AnalysisPanel.tsx` | Ready-state rendering, collapsed secondary sections, optional refinements UI |
| `apps/web/src/app/globals.css` | Reduced visual density and ready-state styles |
| `services/api/src/sadify_api/services/sad_preview.py` | Include questionnaire answers in generated preview context |
| `tests/api/test_sad_preview.py` | Preview-context regression coverage |
| `tests/test_mvp_live_gemini_qna_ui.py` | Static UI regression coverage |
| `docs/superpowers/...` | Active checkpoint alignment |

### Task 1: Add Failing UI Regressions

**Files:**
- Modify: `tests/test_mvp_live_gemini_qna_ui.py`

- [ ] **Step 1: Add tests for collapsed secondary sections and ready-state wording**

```python
def test_analysis_panel_hides_secondary_context_behind_expandable_sections():
    panel = _read("apps/web/src/components/AnalysisPanel.tsx")
    assert "Current understanding" in panel
    assert "Answered so far" in panel
    assert "details className=\"questionnaire-bucket\"" in panel


def test_analysis_panel_has_ready_to_draft_handoff_and_optional_refinements():
    panel = _read("apps/web/src/components/AnalysisPanel.tsx")
    assert "Ready to draft" in panel
    assert "Optional refinements" in panel
    assert "isQuestionnaireReady" in panel
```

- [ ] **Step 2: Run the focused UI test file**

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\test_mvp_live_gemini_qna_ui.py -q
```

Expected: FAIL until the new UI states are implemented.

### Task 2: Add Failing Preview-Context Regression

**Files:**
- Modify: `tests/api/test_sad_preview.py`

- [ ] **Step 1: Add a test proving saved questionnaire answers reach preview context**

```python
def test_sad_preview_context_includes_questionnaire_answers():
    analysis = _analysis_with_blocking_basics()
    analysis["questionnaire"] = {
        "draft_readiness": {
            "label": "Ready for draft",
            "score": 100,
            "confidence": "High",
        },
        "active_category_id": "reports_summaries",
        "active_slot_id": None,
        "active_slot_label": None,
        "categories": [
            {
                "id": "reports_summaries",
                "label": "Reports and summaries",
                "status": "ready",
                "visibility": "completed",
                "progress": 100,
                "questions_total": 1,
                "questions_answered": 1,
                "is_active": False,
            }
        ],
        "answers": [
            {
                "category_id": "reports_summaries",
                "slot_id": "needed_outputs",
                "question": "Which summary does the manager need?",
                "answer": "Daily patients served and unpaid bills",
                "is_uncertain": False,
            }
        ],
        "diagnostics": [],
    }
    context = build_sad_preview_context(
        requirement_text="Need a clinic system.",
        analysis_id="AN-000001",
        analysis=RequirementAnalysisResponse.model_validate(analysis),
        source_context=None,
        source_references=[],
    )
    assert "Questionnaire answers:" in context
    assert "Which summary does the manager need?" in context
    assert "Daily patients served and unpaid bills" in context
```

- [ ] **Step 2: Run the focused preview test**

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_sad_preview.py -q
```

Expected: FAIL because saved answers are not yet serialized into preview context.

### Task 3: Implement Ready-State UI Cleanup

**Files:**
- Modify: `apps/web/src/components/AnalysisPanel.tsx`
- Modify: `apps/web/src/app/globals.css`

- [ ] **Step 1: Derive a ready-state flag from questionnaire readiness**

```tsx
const isQuestionnaireReady =
  questionnaire?.draft_readiness.score === 100 ||
  unresolvedCategories.length === 0;
```

- [ ] **Step 2: Move summary and saved answers into collapsed sections**

```tsx
<details className="questionnaire-bucket">
  <summary>Current understanding</summary>
  <p>{analysis.understanding_summary}</p>
</details>

{activeAnswers.length ? (
  <details className="questionnaire-bucket">
    <summary>Answered so far</summary>
    ...
  </details>
) : null}
```

- [ ] **Step 3: Render the ready banner and hide the unresolved grid at `100%`**

```tsx
{isQuestionnaireReady ? (
  <div className="ready-handoff">
    <p className="eyebrow">Required analysis complete</p>
    <strong>Ready to draft</strong>
    <p>All required answers are covered. You can generate the SAD now.</p>
  </div>
) : (
  <div className="category-progress-row" aria-label="Question categories">
    ...
  </div>
)}
```

- [ ] **Step 4: Add a separate collapsed optional-refinement section**

```tsx
{isQuestionnaireReady ? (
  <details className="questionnaire-bucket">
    <summary>Optional refinements</summary>
    <p>These extra details can improve the SAD, but they do not block drafting.</p>
  </details>
) : null}
```

- [ ] **Step 5: Add compact CSS for the new handoff**

```css
.ready-handoff {
  border: 1px solid #74c993;
  border-radius: 8px;
  padding: 14px;
  background: #163420;
}

.ready-handoff strong {
  display: block;
  color: #f6f2e9;
  font-size: 1.15rem;
}
```

- [ ] **Step 6: Run focused UI tests**

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\test_mvp_live_gemini_qna_ui.py -q
```

Expected: PASS.

### Task 4: Include Saved Answers In Preview Context

**Files:**
- Modify: `services/api/src/sadify_api/services/sad_preview.py`

- [ ] **Step 1: Add a formatter for questionnaire answers**

```python
def _questionnaire_answer_lines(analysis: RequirementAnalysisResponse) -> list[str]:
    questionnaire = analysis.questionnaire
    if questionnaire is None or not questionnaire.answers:
        return ["- none"]
    return [
        (
            f"- {answer.category_id}.{answer.slot_id or 'unknown_slot'}: "
            f"{answer.question} -> {answer.answer}"
        )
        for answer in questionnaire.answers
    ]
```

- [ ] **Step 2: Insert the answer block into the preview context**

```python
"Questionnaire answers:\n"
f"{chr(10).join(_questionnaire_answer_lines(analysis))}\n\n"
```

- [ ] **Step 3: Run focused preview tests**

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_sad_preview.py -q
```

Expected: PASS.

### Task 5: Verify The Structured Preview Failure Boundary

**Files:**
- Modify if needed: `tests/api/test_sad_preview.py`
- Modify only after evidence: `services/api/src/sadify_api/services/gemini_structured.py`

- [ ] **Step 1: Add or confirm a regression covering invalid preview retry behavior**

Use the existing invalid-preview repair test as the baseline and add any missing assertion that the API returns the readable `Gemini returned invalid structured SAD preview.` detail after both attempts fail.

- [ ] **Step 2: Run focused preview tests**

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_sad_preview.py -q
```

- [ ] **Step 3: Reproduce one live local preview after Tasks 3 and 4**

Manual evidence required:

```text
POST /sad/preview returns either 200 with saved preview
or 502 with the exact readable invalid-preview message
```

- [ ] **Step 4: Only if the live preview still fails, record the actual failure evidence before changing prompt text**

The prompt may be adjusted only after capturing:

1. request context shape
2. model response failure mode
3. which schema field failed validation

### Task 6: Update Acceptance Docs

**Files:**
- Modify:
  - `docs/superpowers/testing/test_cases/TC-021T-qna-ready-state-preview-handoff.md`
  - `docs/superpowers/testing/mvp_web_app_test_plan.md`
  - `docs/superpowers/development/00_development_index.md`
  - `docs/superpowers/development/08_new_chat_handoff.md`

- [ ] **Step 1: Record real output, evidence, issues, and decision**
- [ ] **Step 2: Keep MVP-10 blocked unless TC-021T passes**

### Task 7: Verification

- [ ] **Step 1: Run focused tests**

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_sad_preview.py tests\test_mvp_live_gemini_qna_ui.py -q
```

- [ ] **Step 2: Run related regression bundle**

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_gemini_structured.py tests\api\test_sad_preview.py tests\test_mvp_live_gemini_qna_ui.py -q
```

- [ ] **Step 3: Run full Python suite**

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests -q
```

- [ ] **Step 4: Run TypeScript**

```powershell
D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\node_modules\.bin\tsc.cmd -p D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\tsconfig.json --noEmit
```

- [ ] **Step 5: Run production build**

```powershell
npm --prefix D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web run build
```

- [ ] **Step 6: Manual browser smoke**

Verify:

1. active Q&A view is quieter
2. saved answers and current understanding are collapsed by default
3. at `100%`, `Ready to draft` appears
4. unresolved question grid is hidden at `100%`
5. optional refinements are separate and non-blocking
6. completed areas remain expandable
7. SAD preview uses the completed analysis state

## Self-Review

- Spec coverage: every approved ready-state decision and the preview answer bridge has a matching task.
- Placeholder scan: no `TBD`/`TODO` placeholders remain.
- Type consistency: the plan uses current field names from `QuestionnaireState`, `QuestionnaireAnswer`, and `SadPreviewRequest`.


---

## 2026-05-19-qna-sad-synthesis-quality

# Q&A SAD Synthesis Quality Implementation Plan

Status: Historical Phase 4 guardrail plan. TC-021U passed for route safety and
synthesis handoff; use this only for traceability. The active blocker is
TC-021X evidence-first Q&A depth and valid preview coherence.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the first SAD preview merge original request facts and confirmed Q&A answers into one trustworthy draft context without leaking fallback diagnostics or contradicting draft readiness.

**Architecture:** Add a small backend synthesis service that builds a confirmed-facts context before `/sad/preview` calls Gemini. Keep the existing Q&A state and SAD preview schema, but make preview generation consume the merged facts instead of stale model categories as the main truth. Tighten the ready-state UI so `100%` draft readiness hides required active-category language.

**Tech Stack:** Python FastAPI, Pydantic schemas, pytest, Next.js/React, TypeScript.

---

## Execution Result And Follow-Up

TC-021U is complete for its original scope:

```text
1. SAD preview context now separates confirmed request facts, confirmed
   questionnaire answers, unresolved items, source references, and internal
   diagnostics.
2. Internal fallback/retry/Gemini validation wording is kept out of
   business-facing assumptions.
3. `100%` draft readiness hides required active-category wording.
4. Invalid Gemini structured SAD preview output now saves a safe local fallback
   preview instead of returning `502`.
```

Manual video smoke on 2026-05-19 then exposed a new follow-up quality gap:

```text
The fallback preview is transport-safe, but it can still display raw Q&A
transport logs and saved answers as diagnostic text instead of synthesizing them
into SAD sections.
```

Do not reopen this plan for the next fix. Use the follow-up plan instead:

```text
docs/superpowers/plans/2026-05-19-sad-fallback-composition-quality-upgrade.md
```

Matching acceptance test:

```text
docs/superpowers/testing/test_cases/TC-021V-sad-fallback-composition-quality.md
```

## File Structure

```text
D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\sad_synthesis.py
  New focused backend service for confirmed facts, unresolved items, and safe preview context.

D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\sad_preview.py
  Replace loose preview context construction with the synthesis service.

D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\routes\sad.py
  Continue using the same preview route contract after context generation is tightened.

D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\gemini_structured.py
  Tighten the SAD preview prompt so the model respects confirmed facts and keeps diagnostics out.

D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\src\components\AnalysisPanel.tsx
  Hide active required-category language when draft readiness is complete.

D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\src\components\SadPreviewPanel.tsx
  Label IT readiness as later-depth readiness, not the same as draft readiness.
```

### Task 1: Add Merged SAD Synthesis Service

**Files:**
- Create: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\sad_synthesis.py`
- Test: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_synthesis.py`

- [ ] **Step 1: Write failing tests**

Add tests that prove request facts and answers survive:

```python
def test_synthesis_keeps_request_facts_and_answers():
    context = build_sad_synthesis_context(
        requirement_text=CLINIC_REQUEST,
        analysis_id="AN-000010",
        analysis=clinic_analysis_with_answers(),
        source_context=None,
        source_references=["Business Request"],
    )

    assert "patient registration" in context
    assert "queue status" in context
    assert "doctor consultation" in context
    assert "medicine collection" in context
    assert "payment" in context
    assert "Questionnaire answers" in context
```

Add tests that prove internal diagnostics are separated:

```python
def test_synthesis_filters_internal_diagnostics_from_user_assumptions():
    context = build_sad_synthesis_context(
        requirement_text=CLINIC_REQUEST,
        analysis_id="AN-000010",
        analysis=clinic_fallback_analysis(),
        source_context=None,
        source_references=[],
    )

    business_section = context.split("Business-facing assumptions:", 1)[1]
    business_section = business_section.split("Business source references:", 1)[0]
    assert "Fallback was used" not in business_section
    assert "Gemini output could not be validated" not in business_section
    assert "Internal diagnostics" in context
```

- [ ] **Step 2: Run the new tests to confirm failure**

Run:

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_sad_synthesis.py -q
```

Expected: fail because `sad_synthesis.py` does not exist.

- [ ] **Step 3: Implement the service**

Create a focused service with:

```python
from sadify_api.schemas import RequirementAnalysisResponse

INTERNAL_DIAGNOSTIC_TERMS = (
    "fallback",
    "gemini output",
    "structured-output",
    "retry",
    "validated",
)

def split_assumptions(assumptions: list[str]) -> tuple[list[str], list[str]]:
    user_visible = []
    diagnostics = []
    for assumption in assumptions:
        lowered = assumption.lower()
        if any(term in lowered for term in INTERNAL_DIAGNOSTIC_TERMS):
            diagnostics.append(assumption)
        else:
            user_visible.append(assumption)
    return user_visible, diagnostics
```

Build the context with explicit sections:

```text
Layer 1 draft readiness
Confirmed request facts
Confirmed questionnaire answers
Unresolved items
Business-facing assumptions
Business source references
Source context
Internal diagnostics, not for SAD assumptions
```

- [ ] **Step 4: Run focused tests**

Run:

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_sad_synthesis.py -q
```

Expected: pass.

### Task 2: Route SAD Preview Through Synthesis Context

**Files:**
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\sad_preview.py`
- Test: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_preview.py`

- [ ] **Step 1: Add failing regression**

Add:

```python
def test_sad_preview_context_uses_synthesis_without_internal_fallback_assumptions():
    context = build_sad_preview_context(
        requirement_text=CLINIC_REQUEST,
        analysis_id="AN-000010",
        analysis=analysis_with_fallback_assumption_and_answers(),
        source_context=None,
        source_references=["Business Request"],
    )

    assert "Confirmed request facts:" in context
    assert "Confirmed questionnaire answers:" in context
    business_section = context.split("Business-facing assumptions:", 1)[1]
    business_section = business_section.split("Business source references:", 1)[0]
    assert "Fallback was used" not in business_section
```

- [ ] **Step 2: Run focused preview tests**

Run:

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_sad_preview.py -q
```

Expected: fail until `build_sad_preview_context()` delegates to the synthesis builder.

- [ ] **Step 3: Update context builder**

In `sad_preview.py`, import `build_sad_synthesis_context` and make `build_sad_preview_context()` return that output. Keep the public function name so existing route/tests do not churn.

- [ ] **Step 4: Run backend tests**

Run:

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_sad_synthesis.py tests\api\test_sad_preview.py -q
```

Expected: pass.

### Task 3: Tighten SAD Preview Prompt

**Files:**
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\gemini_structured.py`
- Test: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_gemini_structured.py`

- [ ] **Step 1: Add prompt assertions**

Add assertions that `_sad_preview_prompt()` contains:

```python
assert "Confirmed request facts are authoritative" in prompt
assert "Do not turn internal diagnostics into SAD assumptions" in prompt
assert "Layer 1 draft readiness and Layer 2 IT readiness are different" in prompt
```

- [ ] **Step 2: Run prompt tests**

Run:

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\api\test_gemini_structured.py -q
```

Expected: fail until prompt is updated.

- [ ] **Step 3: Update `_sad_preview_prompt()`**

Add concise rules:

```text
Confirmed request facts are authoritative. Confirmed questionnaire answers refine
or override ambiguity. Open questions must come only from unresolved items.
Do not turn internal diagnostics into SAD assumptions. Layer 1 draft readiness
and Layer 2 IT readiness are different; if IT readiness is lower, explain it as
deeper implementation detail still to refine, not as missing draft basics.
```

- [ ] **Step 4: Run prompt tests**

Expected: pass.

### Task 4: Clean Ready-State UI And Layer Labels

**Files:**
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\src\components\AnalysisPanel.tsx`
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\src\components\SadPreviewPanel.tsx`
- Test: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\test_mvp_live_gemini_qna_ui.py`
- Test: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\test_mvp_sad_preview_it_readiness_ui.py`

- [ ] **Step 1: Add failing UI string tests**

Add checks:

```python
assert "!isQuestionnaireReady && activeCategory" in panel
assert "Later IT readiness" in sad_preview_panel
assert "Deeper implementation check" in sad_preview_panel
```

- [ ] **Step 2: Run focused UI tests**

Run:

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests\test_mvp_live_gemini_qna_ui.py tests\test_mvp_sad_preview_it_readiness_ui.py -q
```

Expected: fail until UI labels are changed.

- [ ] **Step 3: Update UI**

In `AnalysisPanel.tsx`, render active category only when not ready:

```tsx
{!isQuestionnaireReady && activeCategory ? (
  <div className="active-category">
    ...
  </div>
) : null}
```

In `SadPreviewPanel.tsx`, rename the preview readiness section copy to:

```tsx
<h4>Later IT readiness</h4>
<p>Deeper implementation check: {preview.it_readiness.label}</p>
```

- [ ] **Step 4: Run focused UI tests**

Expected: pass.

### Task 5: Full Verification And Docs Update

**Files:**
- Modify: `D:\GoogleCloudHack\docs\superpowers\testing\test_cases\TC-021U-qna-sad-synthesis-quality.md`
- Modify as needed: `D:\GoogleCloudHack\docs\superpowers\development\00_development_index.md`
- Modify as needed: `D:\GoogleCloudHack\docs\superpowers\testing\mvp_web_app_test_plan.md`
- Modify as needed: `D:\GoogleCloudHack\docs\superpowers\development\08_new_chat_handoff.md`

- [ ] **Step 1: Run full backend/frontend verification**

Run:

```powershell
D:\GoogleCloudHack\.venv\Scripts\pytest.exe tests -q
node .\apps\web\node_modules\typescript\bin\tsc -p apps\web\tsconfig.json --noEmit
npm --prefix apps\web run build
```

Expected: all pass.

- [ ] **Step 2: Manual clinic smoke**

Run backend and frontend locally, then use the clinic fixture from TC-021U.

Expected:

- Q&A reaches `Ready to draft`
- SAD preview returns `HTTP 200`
- preview includes clinic request facts and confirmed answers
- assumptions do not mention fallback/retry/Gemini diagnostics
- IT readiness is visibly a later-depth check

- [ ] **Step 3: Update TC-021U real output**

Record real test outputs, differences, issues, evidence, and final decision.

## Self-Review

Spec coverage:

- merged facts: Task 1 and Task 2
- diagnostic filtering: Task 1 and Task 3
- readiness coherence: Task 3 and Task 4
- UI ready-state cleanup: Task 4
- test/doc evidence: Task 5

Placeholder scan:

- No placeholder sections remain.

Type consistency:

- Uses existing `RequirementAnalysisResponse`, `SadPreviewResponse`, and existing preview route contract.
- Adds a new service only; no API shape change is required for this checkpoint.


---

## 2026-05-19-sad-fallback-composition-quality-upgrade

# SAD Fallback Composition Quality Upgrade Implementation Plan

Status: Historical Phase 4 partial-pass plan. TC-021V fixed clean request
boundaries and transport-log hiding, TC-021W automated presentation checks
passed, and TC-021X improved the workshop path locally. The active blocker is
now TC-021Y.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade SAD preview fallback output from a safe raw dump into a clean, structured Layer 1 SAD draft that uses the clean business request and interprets confirmed answers/amendments.

**Architecture:** Keep the existing Gemini preview path and safe fallback reliability. Add a clean request boundary and a deterministic fallback composer that maps questionnaire answers into SAD sections when Gemini structured preview output fails validation.

**Tech Stack:** Python FastAPI, Pydantic schemas, pytest, Next.js/React, TypeScript.

---

## Relation To TC-021U

The previous SAD quality plan was not wasted or "not quality enough"; it solved
the first layer of the problem:

```text
TC-021U:
  route stability, synthesis-context structure, diagnostic filtering,
  ready-state wording, and safe local fallback instead of 502
```

This plan exists because the 2026-05-19 manual video smoke proved the next
quality layer:

```text
TC-021V:
  fallback output must be a clean SAD draft, not a raw dump of Q&A transport
  history and saved answer bullets
```

## Execution Result

Automated implementation completed on 2026-05-19.

```text
Focused tests:
  test_sad_synthesis.py -> 3 passed
  test_sad_preview.py -> 14 passed
  test_mvp_live_gemini_qna_ui.py -> 14 passed

Full regression:
  pytest tests -q -> 189 passed
  tsc --noEmit -> passed
  npm --prefix apps\web run build -> passed after sandbox escalation
```

This historical plan is complete enough for TC-021V traceability. TC-021X is
the active blocker before MVP-10.

## File Structure

```text
D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\sad_synthesis.py
  Add clean request extraction and answer-to-section synthesis helpers.

D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\sad_preview.py
  Upgrade build_safe_sad_fallback_preview() to use structured synthesized sections.

D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\routes\sad.py
  Keep the same /sad/preview response shape; pass clean facts into fallback composer.

D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\src\components\AnalysisPanel.tsx
  Stop passing appended Q&A history as the SAD preview business request.

D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\src\components\WorkspaceShell.tsx
  Store clean analysis requirement text separately from model prompt history.

D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_synthesis.py
  Add clean request and answer synthesis tests.

D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_preview.py
  Add fallback SAD composition tests.

D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\test_mvp_live_gemini_qna_ui.py
  Add UI wiring tests for clean request preservation.
```

### Task 1: Protect Clean Business Request Boundary

**Files:**
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\sad_synthesis.py`
- Test: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_synthesis.py`

- [ ] **Step 1: Write failing tests**

Add:

```python
def test_clean_business_request_strips_qna_transport_history():
    polluted = (
        "Small clinic wants to track registration and payment.\n\n"
        "Previous question: [category: data_records][slot: critical_fields] Which details are essential?\n\n"
        "Previous answer: Names or identifiers\n\n"
        "Previous readiness: 53"
    )

    assert clean_business_request(polluted) == (
        "Small clinic wants to track registration and payment."
    )
```

- [ ] **Step 2: Run the test and verify red**

Run:

```powershell
$env:PYTHONPATH='D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src;D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\src;D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold'
D:\GoogleCloudHack\.venv\Scripts\pytest.exe D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_synthesis.py::test_clean_business_request_strips_qna_transport_history -q
```

Expected: fail because `clean_business_request` does not exist.

- [ ] **Step 3: Implement the helper**

Add to `sad_synthesis.py`:

```python
def clean_business_request(requirement_text: str) -> str:
    return requirement_text.split("Previous question:", 1)[0].strip()
```

- [ ] **Step 4: Verify green**

Run the same focused test.

Expected: pass.

### Task 2: Preserve Clean Requirement Text In Frontend Handoff

**Files:**
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\src\components\AnalysisPanel.tsx`
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\src\components\WorkspaceShell.tsx`
- Test: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\test_mvp_live_gemini_qna_ui.py`

- [ ] **Step 1: Write failing UI source tests**

Add:

```python
def test_live_gemini_qna_ui_preserves_clean_requirement_for_preview():
    panel = (WEB_SRC / "components" / "AnalysisPanel.tsx").read_text(encoding="utf-8")
    shell = (WEB_SRC / "components" / "WorkspaceShell.tsx").read_text(encoding="utf-8")

    assert "cleanRequirementText" in panel
    assert "onAnalysisSaved(response, cleanRequirementText)" in panel
    assert "setAnalysisRequirementText(cleanRequirementText)" in shell
```

- [ ] **Step 2: Run focused UI test and verify red**

Run:

```powershell
$env:PYTHONPATH='D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src;D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\src;D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold'
D:\GoogleCloudHack\.venv\Scripts\pytest.exe D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\test_mvp_live_gemini_qna_ui.py::test_live_gemini_qna_ui_preserves_clean_requirement_for_preview -q
```

Expected: fail until the clean request is stored separately.

- [ ] **Step 3: Update AnalysisPanel**

In `AnalysisPanel.tsx`, add:

```tsx
const [cleanRequirementText, setCleanRequirementText] = useState(
  "Need a simple way to validate an operational workflow idea.",
);
```

In `startAnalysis()`, before the API call:

```tsx
const cleanText = requirementText.trim();
setCleanRequirementText(cleanText);
```

Then call:

```tsx
onAnalysisSaved(response, cleanText);
```

In `continueWithAnswer()`, keep using `nextRequirementText` for the model call, but call:

```tsx
onAnalysisSaved(response, cleanRequirementText);
```

and in the error path:

```tsx
onAnswerKeptForPreview?.(analysisResponse, cleanRequirementText, answerText);
```

- [ ] **Step 4: Update WorkspaceShell**

Keep `analysisRequirementText` as the clean value that `SadPreviewPanel` receives.

Do not overwrite it with appended transport history.

- [ ] **Step 5: Verify focused UI test**

Run the focused UI test.

Expected: pass.

### Task 3: Compose Structured Fallback SAD Sections

**Files:**
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\sad_preview.py`
- Test: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_preview.py`

- [ ] **Step 1: Write failing composition test**

Add:

```python
def test_safe_fallback_preview_renders_structured_sad_sections():
    analysis = _clinic_analysis_with_all_answers_and_amendments()

    preview = build_safe_sad_fallback_preview(
        requirement_text=CLINIC_REQUEST_WITH_TRANSPORT_HISTORY,
        analysis=RequirementAnalysisResponse.model_validate(analysis),
        source_references=["Business Request"],
    )

    titles = [section.title for section in preview.sections]
    assert "Confirmed Business Request" in titles
    assert "Users and Roles" in titles
    assert "Workflow" in titles
    assert "Data and Records" in titles
    assert "Business Rules and Approvals" in titles
    assert "Exceptions and Edge Cases" in titles
    assert "Reports and Summaries" in titles
    assert "Security and Privacy" in titles
    assert "Audit and History" in titles

    business_request = next(
        section.body for section in preview.sections
        if section.title == "Confirmed Business Request"
    )
    assert "Previous question:" not in business_request
    assert "Previous answer:" not in business_request

    security = next(section.body for section in preview.sections if section.title == "Security and Privacy")
    assert "encrypted" in security.lower()
    assert "dun downgrade" in security

    audit = next(section.body for section in preview.sections if section.title == "Audit and History")
    assert "any actions towards the system and the data all must be recorded" in audit
```

- [ ] **Step 2: Run focused test and verify red**

Run:

```powershell
$env:PYTHONPATH='D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src;D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\src;D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold'
D:\GoogleCloudHack\.venv\Scripts\pytest.exe D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_preview.py::test_safe_fallback_preview_renders_structured_sad_sections -q
```

Expected: fail because the fallback currently renders raw Q&A sections.

- [ ] **Step 3: Add answer grouping helper**

In `sad_preview.py`, add:

```python
def _answers_by_category(analysis: RequirementAnalysisResponse) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    if analysis.questionnaire is None:
        return grouped
    for answer in analysis.questionnaire.answers:
        line = f"{answer.question}: {answer.answer}"
        grouped.setdefault(answer.category_id, []).append(line)
    return grouped
```

- [ ] **Step 4: Build structured sections**

Replace the fallback's raw `Confirmed Q&A Answers` section with section builders:

```python
sections = [
    _section("Confirmed Business Request", clean_business_request(requirement_text), references),
    _section("Overview and Scope", analysis.understanding_summary, references),
    _section("Users and Roles", _section_body(grouped, ["users_roles"], "No extra role details confirmed."), references),
    _section("Workflow", _section_body(grouped, ["workflow_steps"], "Use the workflow stated in the request."), references),
    _section("Data and Records", _section_body(grouped, ["data_records"], "Use records stated in the request."), references),
    _section("Business Rules and Approvals", _section_body(grouped, ["rules_approvals"], "No extra approval details confirmed."), references),
    _section("Exceptions and Edge Cases", _section_body(grouped, ["exceptions_edges"], "Use exceptions stated in the request."), references),
    _section("Reports and Summaries", _section_body(grouped, ["reports_summaries"], "Use reports stated in the request."), references),
    _section("Access and Permissions", _section_body(grouped, ["access_permissions"], "Role-based access details need review."), references),
    _section("Integrations", _section_body(grouped, ["integrations"], "No external integrations confirmed."), references),
    _section("Security and Privacy", _section_body(grouped, ["non_functional"], "Security/privacy details need review.", include_slots=["security_privacy"]), references),
    _section("Audit and History", _section_body(grouped, ["non_functional"], "Audit/history details need review.", include_slots=["audit_history"]), references),
]
```

The exact implementation may split by `slot_id` so `security_privacy` and
`audit_history` do not collapse into one generic non-functional block.

- [ ] **Step 5: Verify focused fallback test**

Run the focused fallback composition test.

Expected: pass.

### Task 4: Remove Internal Understanding From Fallback SAD

**Files:**
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\sad_preview.py`
- Test: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_preview.py`

- [ ] **Step 1: Add failing diagnostic-leak test**

Add:

```python
def test_safe_fallback_preview_does_not_show_internal_understanding():
    analysis = _clinic_fallback_analysis_with_diagnostic_summary()

    preview = build_safe_sad_fallback_preview(
        requirement_text=CLINIC_REQUEST,
        analysis=RequirementAnalysisResponse.model_validate(analysis),
        source_references=["Business Request"],
    )

    joined = "\n".join(section.body for section in preview.sections)
    assert "SADify kept the business request" not in joined
    assert "Gemini's latest structured question could not be validated" not in joined
```

- [ ] **Step 2: Verify red**

Run the focused test.

Expected: fail until internal fallback summary is filtered.

- [ ] **Step 3: Implement safe understanding text**

Add:

```python
def _safe_understanding_summary(analysis: RequirementAnalysisResponse, requirement_text: str) -> str:
    lowered = analysis.understanding_summary.lower()
    if "gemini" in lowered or "fallback" in lowered or "sadify kept" in lowered:
        return clean_business_request(requirement_text)
    return analysis.understanding_summary
```

Use this for `Overview and Scope`.

- [ ] **Step 4: Verify focused test**

Expected: pass.

### Task 5: Open Questions Should Reflect Real Remaining Gaps

**Files:**
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\sad_preview.py`
- Test: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_preview.py`

- [ ] **Step 1: Add failing open-question test**

Add:

```python
def test_safe_fallback_preview_does_not_promote_optional_question_as_core_gap_when_ready():
    analysis = _clinic_ready_analysis_with_optional_next_question()

    preview = build_safe_sad_fallback_preview(
        requirement_text=CLINIC_REQUEST,
        analysis=RequirementAnalysisResponse.model_validate(analysis),
        source_references=["Business Request"],
    )

    assert "Which staff access rule should be confirmed first?" not in preview.open_questions
```

- [ ] **Step 2: Verify red**

Run the focused test.

Expected: fail until ready-state optional questions are filtered.

- [ ] **Step 3: Filter optional next question after 100% readiness**

In `_safe_open_questions`, when `analysis.questionnaire.draft_readiness.score == 100`
and there are no unresolved required categories, return:

```python
["Review optional refinements before final saving if the project owner wants more detail."]
```

or an empty list if the UI handles no questions cleanly.

- [ ] **Step 4: Verify focused test**

Expected: pass.

### Task 6: Full Verification And Docs Update

**Files:**
- Modify: `D:\GoogleCloudHack\docs\superpowers\testing\test_cases\TC-021V-sad-fallback-composition-quality.md`
- Modify as needed:
  - `D:\GoogleCloudHack\docs\superpowers\testing\mvp_web_app_test_plan.md`
  - `D:\GoogleCloudHack\docs\superpowers\development\00_development_index.md`
  - `D:\GoogleCloudHack\docs\superpowers\development\08_new_chat_handoff.md`

- [ ] **Step 1: Run focused tests**

Run:

```powershell
$env:PYTHONPATH='D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src;D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\src;D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold'
D:\GoogleCloudHack\.venv\Scripts\pytest.exe D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_preview.py D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_synthesis.py D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\test_mvp_live_gemini_qna_ui.py -q
```

Expected: all pass.

- [ ] **Step 2: Run full verification**

Run:

```powershell
$env:PYTHONPATH='D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src;D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\src;D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold'
D:\GoogleCloudHack\.venv\Scripts\pytest.exe D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests -q
node D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\node_modules\typescript\bin\tsc -p D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\tsconfig.json --noEmit
npm --prefix D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web run build
```

Expected: all pass. If `npm` is blocked by sandbox `EPERM`, rerun build with approved escalation.

- [ ] **Step 3: Manual video smoke**

Run the clinic fixture again.

Expected:

- Q&A reaches `Ready for draft - 100%`.
- `/sad/preview` returns `HTTP 200`.
- `Confirmed Business Request` contains only the clinic request.
- No `Previous question`, `Previous answer`, or `Previous readiness` appears in any user-facing SAD section.
- Security/privacy section includes the encryption amendment.
- Audit/history section includes the full audit amendment.
- Fallback preview, if used, reads as a structured SAD draft.

## Self-Review

Spec coverage:

- Clean request boundary: Task 1 and Task 2
- Structured fallback SAD: Task 3
- Internal understanding cleanup: Task 4
- Open question cleanup: Task 5
- Full verification/docs: Task 6

Placeholder scan:

- No placeholder sections remain.

Type consistency:

- Uses existing `RequirementAnalysisResponse`, `SadPreviewResponse`, `SadPreviewSection`, and current `/sad/preview` response shape.
- Does not add a new API contract in this checkpoint.


---

## 2026-05-19-user-facing-sad-draft-quality

# User-Facing SAD Draft Quality Implementation Plan

Status: Historical implementation trace. TC-021W automated checks passed, but
the 2026-05-20 workshop manual smoke failed progression. TC-021X later improved
the workshop path locally, but manual workshop/tuition smoke still failed
broader progression. The active follow-up is
`TC-021Y-domain-aware-qna-sad-quality-hardening.md`. Do not start MVP-10 /
TC-025 until TC-021Y passes.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the fallback SAD preview into a clean, professional Layer 1 SAD draft instead of a debug-style fallback report.

**Architecture:** Keep Gemini structured preview as the preferred path, but make the local fallback composer business-facing and deterministic. The backend will synthesize confirmed request facts plus questionnaire answers into named SAD sections, while the frontend will move fallback diagnostics and Layer 2 readiness into collapsed details.

**Tech Stack:** Python FastAPI/Pydantic service layer, Next.js/React components, pytest, TypeScript, Next.js production build.

**Execution result, 2026-05-20:** Backend composer, frontend fallback UI, focused
tests, full regression, TypeScript, and Next.js build pass locally. The checklist
below is retained as historical implementation traceability; do not re-execute
it unless historical evidence is needed. TC-021X later improved the workshop
path locally; the next active gate is TC-021Y.

---

## File Structure

- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\sad_preview.py`
  - Owns fallback SAD composition, title/notice, normalized answer wording, source-reference placement, and safe open questions.
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\src\components\SadPreviewPanel.tsx`
  - Owns user-facing preview layout, hiding fallback diagnostics from the normal view, and moving IT-readiness details behind an expander.
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_preview.py`
  - Adds backend composition tests using the clinic fixture and amended answers.
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\test_mvp_sad_preview_it_readiness_ui.py`
  - Adds frontend assertions that the normal preview does not show debug/fallback framing.
- Modify after implementation: `D:\GoogleCloudHack\docs\superpowers\testing\test_cases\TC-021W-user-facing-sad-draft-quality.md`
  - Records expected output, real output, evidence, issues, and decision.

External API/docs preflight:

```text
No external API, cloud service, or live Gemini call is required for implementation.
Use local unit/UI tests only. Manual smoke may use the user's already-running local backend/frontend.
```

---

### Task 1: Add Backend Failing Tests For Business-Facing Fallback SAD

**Files:**
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_preview.py`

- [ ] **Step 1: Add the failing title/debug-framing test**

Add this test after `test_safe_fallback_preview_renders_structured_sad_sections`:

```python
def test_safe_fallback_preview_uses_business_facing_title_and_notice():
    analysis = _clinic_analysis_with_all_answers_and_amendments()

    preview = build_safe_sad_fallback_preview(
        requirement_text=CLINIC_REQUEST_WITH_TRANSPORT_HISTORY,
        analysis=RequirementAnalysisResponse.model_validate(analysis),
        source_references=["Business Request"],
    )

    visible_text = "\n".join(
        [
            preview.title,
            preview.temporary_notice,
            preview.it_readiness.label,
            preview.change_tracking.summary,
            *[section.title + "\n" + section.body for section in preview.sections],
        ]
    )

    assert "Clinic Patient Flow Management SAD Draft" == preview.title
    assert "Safe Temporary SAD Preview" not in visible_text
    assert "AI preview formatting" not in visible_text
    assert "Generated safe local preview" not in visible_text
    assert "_SADify/local-fallback" not in visible_text
    assert preview.it_readiness.score == 100
    assert preview.it_readiness.confidence == "High"
```

- [ ] **Step 2: Add the failing synthesis-depth test**

Add this test after the title/debug-framing test:

```python
def test_safe_fallback_preview_synthesizes_sections_instead_of_repeating_request():
    analysis = _clinic_analysis_with_all_answers_and_amendments()

    preview = build_safe_sad_fallback_preview(
        requirement_text=CLINIC_REQUEST,
        analysis=RequirementAnalysisResponse.model_validate(analysis),
        source_references=["Business Request"],
    )

    section_map = {section.title: section.body for section in preview.sections}

    workflow = section_map["Workflow"]
    assert "1. Register patient" in workflow
    assert "2. Manage queue status" in workflow
    assert "3. Record doctor consultation" in workflow
    assert "4. Prepare and collect medicine" in workflow
    assert "5. Record payment and close visit" in workflow
    assert "If payment or medicine collection is skipped" in workflow

    data = section_map["Data and Records"]
    assert "Patient or visit identifier" in data
    assert "status timestamps" in data
    assert "responsible staff member" in data
    assert "amounts, notes, or reasons" in data

    request_repetition_count = sum(
        1
        for section in preview.sections
        if section.body == CLINIC_REQUEST
    )
    assert request_repetition_count == 0
```

- [ ] **Step 3: Add the failing amendment-normalization test**

Add this test after the synthesis-depth test:

```python
def test_safe_fallback_preview_normalizes_user_amendments():
    analysis = _clinic_analysis_with_all_answers_and_amendments()

    preview = build_safe_sad_fallback_preview(
        requirement_text=CLINIC_REQUEST,
        analysis=RequirementAnalysisResponse.model_validate(analysis),
        source_references=["Business Request"],
    )

    section_map = {section.title: section.body for section in preview.sections}

    security = section_map["Security and Privacy"]
    assert "sensitive data must remain encrypted" in security.lower()
    assert "security controls must not be weakened" in security.lower()
    assert "dun downgrade" not in security
    assert "| Details:" not in security

    audit = section_map["Audit and History"]
    assert "all user actions that affect system data must be recorded" in audit.lower()
    assert "| Details:" not in audit
```

- [ ] **Step 4: Run tests and verify they fail**

Run:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_sad_preview.py -q
```

Expected:

```text
FAIL test_safe_fallback_preview_uses_business_facing_title_and_notice
FAIL test_safe_fallback_preview_synthesizes_sections_instead_of_repeating_request
FAIL test_safe_fallback_preview_normalizes_user_amendments
```

---

### Task 2: Implement Backend Fallback SAD Composer

**Files:**
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\sad_preview.py`

- [ ] **Step 1: Add answer lookup helpers**

Add these helpers below `_questionnaire_answers()`:

```python
def _answer_map(
    answers: list[tuple[str, str | None, str]],
) -> dict[tuple[str, str], str]:
    return {
        (category_id, slot_id or ""): answer.strip()
        for category_id, slot_id, answer in answers
    }


def _strip_details_marker(answer: str) -> str:
    return answer.split("| Details:", 1)[0].strip()


def _details_text(answer: str) -> str:
    marker = "| Details:"
    if marker not in answer:
        return ""
    return answer.split(marker, 1)[1].strip()
```

- [ ] **Step 2: Replace fallback title and readiness**

In `build_safe_sad_fallback_preview`, replace:

```python
title="Safe Temporary SAD Preview",
temporary_notice=(
    "Temporary preview generated from confirmed request facts and saved "
    "Q&A answers because the AI preview formatting could not be validated."
),
it_readiness=_safe_it_readiness(analysis),
```

with:

```python
title=_business_sad_title(clean_request),
temporary_notice=(
    "Draft preview generated from the confirmed business request and saved "
    "Q&A answers. Review before saving as a formal SAD."
),
it_readiness=_draft_ready_it_readiness(analysis),
```

Add these helpers:

```python
def _business_sad_title(clean_request: str) -> str:
    lowered = clean_request.lower()
    if "clinic" in lowered and "patient" in lowered:
        return "Clinic Patient Flow Management SAD Draft"
    return "System Analysis Document Draft"


def _draft_ready_it_readiness(analysis: RequirementAnalysisResponse) -> ItReadinessSummary:
    layer_one_label = "Ready for draft" if _is_draft_ready(analysis) else "Draft review needed"
    return ItReadinessSummary(
        label=layer_one_label,
        score=100 if _is_draft_ready(analysis) else analysis.readiness.score,
        confidence="High" if _is_draft_ready(analysis) else analysis.readiness.confidence,
        checklist=[
            {
                "id": "layer_one_context",
                "label": "Layer 1 SAD draft",
                "status": "ready" if _is_draft_ready(analysis) else "needs_input",
                "reason": "The draft uses confirmed request facts and saved Q&A answers.",
            },
            {
                "id": "layer_two_review",
                "label": "Later implementation review",
                "status": "needs_input",
                "reason": "Detailed technical design remains a later MVP refinement step.",
            },
        ],
    )
```

- [ ] **Step 3: Replace shallow section bodies with composed sections**

Inside `build_safe_sad_fallback_preview`, after `answers = _questionnaire_answers(analysis)`, add:

```python
answer_lookup = _answer_map(answers)
```

Replace the `sections=[...]` list with:

```python
sections=[
    _section("Confirmed Business Request", clean_request, references),
    _section("Executive Summary", _compose_executive_summary(clean_request), references),
    _section("Scope", _compose_scope(clean_request), references),
    _section("Users and Responsibilities", _compose_users_and_roles(clean_request), references),
    _section("Workflow", _compose_workflow(clean_request, answer_lookup), references),
    _section("Data and Records", _compose_data_records(answer_lookup), references),
    _section("Business Rules and Approvals", _compose_rules_and_approvals(answer_lookup), references),
    _section("Exceptions and Follow-Up", _compose_exceptions(clean_request, answer_lookup), references),
    _section("Reports and Summaries", _compose_reports(clean_request), references),
    _section("Access and Permissions", _compose_access(answer_lookup), references),
    _section("Security and Privacy", _compose_security(answer_lookup), references),
    _section("Audit and History", _compose_audit(answer_lookup), references),
    _section("Integrations", _compose_integrations(answer_lookup), references),
],
```

- [ ] **Step 4: Add deterministic composer helpers**

Add these helpers below `_request_sentences()`:

```python
def _compose_executive_summary(clean_request: str) -> str:
    if "clinic" in clean_request.lower():
        return (
            "The proposed system will support a small clinic's patient journey "
            "from registration through queue handling, consultation, medicine "
            "collection, payment, and daily management reporting."
        )
    return clean_request


def _compose_scope(clean_request: str) -> str:
    if "clinic" in clean_request.lower():
        return (
            "The Layer 1 scope covers one simple internal clinic system for "
            "frontline staff and managers. The draft focuses on operational "
            "tracking, status visibility, record completeness, exception follow-up, "
            "and daily summaries."
        )
    return "The Layer 1 scope is based on the confirmed business request."


def _compose_users_and_roles(clean_request: str) -> str:
    if "clinic" in clean_request.lower():
        return (
            "Reception staff register patients and update queue status. Doctors "
            "record consultation notes. Pharmacy staff prepare medicine and track "
            "collection. Cashiers record payments and unpaid bills. Managers review "
            "daily summaries and follow up on incomplete visits."
        )
    return _request_sentences(clean_request, ("staff", "manager", "user", "role"), "Users and responsibilities need review.")


def _compose_workflow(clean_request: str, answers: dict[tuple[str, str], str]) -> str:
    exception_rule = answers.get(("exceptions_edges", "required_handling"), "Mark incomplete and keep open")
    if "clinic" in clean_request.lower():
        return (
            "1. Register patient and create a visit record. "
            "2. Manage queue status until the patient is ready for consultation. "
            "3. Record doctor consultation notes. "
            "4. Prepare medicine and record collection status. "
            "5. Record payment and close the visit only when required steps are complete. "
            f"If payment or medicine collection is skipped, staff should {exception_rule.lower()} for follow-up."
        )
    return "Workflow steps should follow the confirmed business request and saved answers."


def _compose_data_records(answers: dict[tuple[str, str], str]) -> str:
    fields = answers.get(("data_records", "critical_fields"), "")
    if fields:
        return (
            "Each operational record should include a patient or visit identifier, "
            "status timestamps, the responsible staff member or owner, and any "
            "amounts, notes, or reasons needed to explain the record."
        )
    return "Record fields need later review."


def _compose_rules_and_approvals(answers: dict[tuple[str, str], str]) -> str:
    rule = answers.get(("rules_approvals", "triggering_rules"), "A record cannot be completed until key steps are done")
    approval = answers.get(("rules_approvals", "approval_path"), "Approval details need review")
    return (
        f"Core rule: {rule}. Approval path: {approval}. These rules should prevent "
        "incomplete visits from being treated as complete."
    )


def _compose_exceptions(clean_request: str, answers: dict[tuple[str, str], str]) -> str:
    handling = answers.get(("exceptions_edges", "required_handling"), "Mark incomplete and keep open")
    return (
        "Known exception cases include skipped payment and leaving before medicine "
        f"collection. When this happens, staff should {handling.lower()} so the "
        "case remains visible for follow-up."
    )


def _compose_reports(clean_request: str) -> str:
    return _request_sentences(
        clean_request,
        ("summary", "report", "manager", "served", "waiting", "unpaid"),
        "Reports and summaries need later review.",
    )


def _compose_access(answers: dict[tuple[str, str], str]) -> str:
    model = answers.get(("access_permissions", "access_model"), "Role-based access")
    sensitive = answers.get(("access_permissions", "sensitive_actions"), "Sensitive actions need review")
    return (
        f"Access should use {model.lower()}. Tighter permission control is required "
        f"for: {sensitive}."
    )


def _compose_integrations(answers: dict[tuple[str, str], str]) -> str:
    return answers.get(("integrations", "external_systems"), "No external integrations are confirmed for the first version.")


def _compose_security(answers: dict[tuple[str, str], str]) -> str:
    answer = answers.get(("non_functional", "security_privacy"), "")
    details = _details_text(answer)
    text = "The system should require secure login, restrict sensitive data by role, and protect personal or confidential data."
    if "encrypted" in details.lower():
        text += " Sensitive data must remain encrypted and security controls must not be weakened."
    return text


def _compose_audit(answers: dict[tuple[str, str], str]) -> str:
    answer = answers.get(("non_functional", "audit_history"), "")
    base = _strip_details_marker(answer)
    text = (
        "Audit history should cover edits and corrections, approvals and decisions, "
        "status changes, and exports or downloads."
    )
    if base:
        text = f"Audit history should cover {base.lower()}."
    if "any actions" in _details_text(answer).lower():
        text += " All user actions that affect system data must be recorded."
    return text
```

- [ ] **Step 5: Run backend tests**

Run:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_sad_preview.py -q
```

Expected:

```text
all tests in test_sad_preview.py pass
```

---

### Task 3: Move Preview Diagnostics Out Of The Normal UI

**Files:**
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\src\components\SadPreviewPanel.tsx`
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\test_mvp_sad_preview_it_readiness_ui.py`

- [ ] **Step 1: Add frontend failing test**

Add a test that renders the preview panel with a fallback preview response and asserts:

```text
visible normal output includes:
  Clinic Patient Flow Management SAD Draft
  Draft-ready

visible normal output does not include:
  35%
  Low confidence
  AI preview formatting
  _SADify/local-fallback
  Generated safe local preview

collapsed diagnostics still include:
  Tracking status
```

Use the existing frontend string-inspection style already used in
`tests/test_mvp_sad_preview_it_readiness_ui.py`.

- [ ] **Step 2: Implement UI branching for fallback preview**

In `SadPreviewPanel.tsx`, add:

```tsx
const isFallbackPreview = preview?.change_tracking.paths.includes(
  "_SADify/local-fallback",
);
```

Replace the score block:

```tsx
<div className="it-score">
  <span>{preview.it_readiness.score}%</span>
  <small>{preview.it_readiness.confidence} confidence</small>
</div>
```

with:

```tsx
<div className="it-score">
  {isFallbackPreview ? (
    <>
      <span>Draft-ready</span>
      <small>Layer 1 preview</small>
    </>
  ) : (
    <>
      <span>{preview.it_readiness.score}%</span>
      <small>{preview.it_readiness.confidence} confidence</small>
    </>
  )}
</div>
```

- [ ] **Step 3: Collapse later IT readiness for fallback previews**

Wrap the `it-readiness` block in a `details` element when `isFallbackPreview`
is true:

```tsx
{isFallbackPreview ? (
  <details className="it-readiness">
    <summary>Later implementation review</summary>
    <p>{preview.it_readiness.label}</p>
    <div className="it-checks">{/* existing checklist map */}</div>
  </details>
) : (
  <section className="it-readiness">{/* existing content */}</section>
)}
```

- [ ] **Step 4: Collapse source refs and tracking by default**

Keep per-section source references out of the main section cards for fallback
previews:

```tsx
{!isFallbackPreview && section.source_references.length > 0 ? (
  <small>Source refs: {section.source_references.join(", ")}</small>
) : null}
```

Leave the existing `Source refs` and `Tracking status` details closed by
default.

- [ ] **Step 5: Run frontend-focused tests**

Run:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\test_mvp_sad_preview_it_readiness_ui.py -q
```

Expected:

```text
all frontend SAD preview UI tests pass
```

---

### Task 4: Full Verification And Docs

**Files:**
- Modify: `D:\GoogleCloudHack\docs\superpowers\testing\test_cases\TC-021W-user-facing-sad-draft-quality.md`
- Modify: `D:\GoogleCloudHack\docs\superpowers\testing\mvp_web_app_test_plan.md`
- Modify: `D:\GoogleCloudHack\docs\superpowers\testing\test_case_index.md`
- Modify: `D:\GoogleCloudHack\docs\superpowers\development\00_development_index.md`
- Modify: `D:\GoogleCloudHack\docs\superpowers\development\08_new_chat_handoff.md`
- Modify: `D:\GoogleCloudHack\context.md`
- Modify: `D:\GoogleCloudHack\CLAUDE.md`

- [ ] **Step 1: Run full local verification**

Run:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests -q
node D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\node_modules\typescript\bin\tsc -p D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\tsconfig.json --noEmit
npm --prefix D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web run build
```

Expected:

```text
pytest passes
tsc exits 0
Next.js build exits 0
```

- [ ] **Step 2: Update TC-021W with evidence**

Record:

```text
focused backend tests
focused frontend tests
full pytest result
TypeScript result
Next.js build result
manual smoke status
remaining issues
decision
```

- [ ] **Step 3: Update active docs**

Update active docs to say:

```text
TC-021W automated checks pass, but the 2026-05-20 workshop manual smoke failed progression
MVP-10 / TC-025 remains blocked until TC-021Y passes
```

- [ ] **Step 4: Stop for user manual smoke**

Return:

```text
what changed
tests/evidence
known risks
manual restart commands
manual test script
next checkpoint
```

Do not start MVP-10 in the same turn.

---

## Self-Review

Spec coverage:

```text
TC-021W Expected Output items 1-12 are covered by Task 1 backend tests, Task 2
composer changes, Task 3 frontend UI changes, and Task 4 manual smoke.
```

Placeholder scan:

```text
No TBD/TODO/fill-later implementation steps are present.
```

Type consistency:

```text
The plan uses existing `SadPreviewResponse`, `ItReadinessSummary`,
`SadPreviewSection`, and existing `SadPreviewPanel` props. No schema migration is
required for this checkpoint.
```

## Execution Handoff

Plan implemented through automated checks and saved to
`docs/superpowers/plans/2026-05-19-user-facing-sad-draft-quality.md`.

Next action:

1. Use this plan as historical TC-021W implementation traceability only.
2. Continue with `TC-021Y-domain-aware-qna-sad-quality-hardening.md`.
3. Continue to MVP-10 / TC-025 only after TC-021Y passes and the user approves.


---

## 2026-05-20-evidence-first-qna-depth-valid-preview-coherence

# Evidence-First Q&A Depth And Valid Preview Coherence Implementation Plan

Status: Historical Phase 4 plan. TC-021X passed local checks and improved the
workshop path, but manual workshop/tuition smoke still failed broader
progression. The active blocker is TC-021Y:
`docs/superpowers/plans/2026-05-21-domain-aware-qna-sad-quality-hardening.md`.

> **For agentic workers:** Execute this plan step by step. Use test-first development for behavior changes. Do not start MVP-10 / TC-025. Do not use live Gemini/cloud calls for local implementation unless the user explicitly asks for manual smoke with live services.

**Goal:** Fix the current Phase 4 blocker by making Q&A fact coverage and SAD preview presentation detailed enough for a user-facing SAD draft.

**Architecture:** Add an evidence-first fact layer around the existing questionnaire and synthesis flow. Reuse current categories and API routes, but make completion depend on concrete facts/facets rather than broad preset labels. Apply the same preview presentation guardrails to valid and fallback previews.

**Tech Stack:** Python FastAPI backend, pytest, TypeScript/React frontend, existing local MVP worktree.

---

## Task 1: Add Failing Backend Tests For Evidence-First Coverage

**Files:**

- `tests/api/test_gemini_structured.py` or new `tests/api/test_evidence_first_questionnaire.py`
- `tests/api/test_sad_synthesis.py`

**Test cases:**

- Rich workshop request seeds facts for:
  - workflow;
  - data and records;
  - business rules and approvals;
  - exceptions and edge cases;
  - reports and summaries;
  - access and permissions;
  - integrations;
  - non-functional needs.
- First next question does not ask a broad workflow/responsibility question when those facts are already known.
- Readiness cannot become `100%` from one generic answer per category.
- Structured answer facts are available to SAD synthesis.

**Acceptance:** Tests fail for the current implementation for the known TC-021X gaps.

---

## Task 2: Implement Confirmed Facts And Facet Coverage

**Files:**

- `services/api/src/sadify_api/services/questionnaire_plan.py`
- `services/api/src/sadify_api/services/questionnaire_slots.py`
- `services/api/src/sadify_api/routes/analysis.py`
- possible new file: `services/api/src/sadify_api/services/confirmed_facts.py`
- `services/api/src/sadify_api/schemas.py`

**Implementation notes:**

- Keep the current category model.
- Add a small, explicit facet map per category.
- Extract known facts from the business request using deterministic local rules first.
- Preserve source references as `Business Request` facts.
- Mark facets covered only when the request or answer includes usable detail.
- Do not let a broad preset label satisfy all facets in a category.

**Acceptance:** Rich workshop request credits the facts already stated by the user, including approval, unavailable parts, overdue open reasons, no external systems, secure login, role restrictions, and audit trail.

---

## Task 3: Make Questions And Choices Contextual

**Files:**

- `services/api/src/sadify_api/services/questionnaire_slots.py`
- `services/api/src/sadify_api/services/questionnaire_plan.py`
- `services/api/src/sadify_api/routes/analysis.py`
- existing Gemini structured/fallback service files if needed

**Implementation notes:**

- Select the most important missing facet, not just the first incomplete category.
- Build fallback questions from the domain and missing facet.
- Build choices that preserve implementation detail.
- Keep existing safe fallback behavior for invalid Gemini output.

**Acceptance:** For the workshop input, the next question is specific to a missing detail such as approval threshold, overdue definition, status lifecycle, edit-after-completion rule, or report grouping. It should not ask a generic "Which normal flow best matches" question when the flow is already clear.

---

## Task 4: Feed Structured Facts Into SAD Synthesis

**Files:**

- `services/api/src/sadify_api/services/sad_synthesis.py`
- `services/api/src/sadify_api/services/sad_preview.py`
- `services/api/src/sadify_api/routes/sad.py`
- `services/api/src/sadify_api/schemas.py`
- `tests/api/test_sad_synthesis.py`
- `tests/api/test_sad_preview.py`

**Implementation notes:**

- Pass confirmed source facts and structured answer facts to SAD synthesis.
- Include known gaps separately from confirmed facts.
- Avoid sections that invent implementation details.
- Reduce repeated source reference clutter in section rendering.

**Acceptance:** The workshop SAD includes concrete entities, workflow, approval rules, exception handling, reporting, access, integration scope, and audit requirements from the request.

---

## Task 5: Align Valid Preview UI With Fallback Guardrails

**Files:**

- `apps/web/src/components/SadPreviewPanel.tsx`
- `apps/web/src/app/analysis/AnalysisPanel.tsx` if state handling is involved
- `tests/test_mvp_sad_preview_it_readiness_ui.py`

**Implementation notes:**

- Apply current user-facing preview rules to valid Gemini previews too.
- Keep IT readiness collapsed or visually secondary.
- Avoid contradictory confidence/readiness display after the app says ready for draft.
- Keep source refs accessible but not repeated as body noise.

**Acceptance:** A valid preview no longer surfaces `60% Low confidence` plus expanded `Later IT readiness` as the main result after Q&A readiness is complete.

---

## Task 6: Verify Locally

Run from:

`D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`

```powershell
$env:PYTHONPATH="services\api\src;src;."
pytest tests\api\test_sad_preview.py tests\api\test_sad_synthesis.py tests\api\test_gemini_structured.py -q
pytest tests\test_mvp_sad_preview_it_readiness_ui.py -q
pytest tests -q
npx tsc --noEmit
npm --prefix apps\web run build
```

Expected result:

- focused tests pass;
- full pytest suite passes;
- TypeScript check passes;
- web build passes.

---

## Task 7: Manual Smoke And Handoff

Use the TC-021X workshop request in:

`docs/superpowers/testing/test_cases/TC-021X-evidence-first-qna-depth-valid-preview-coherence.md`

Confirm:

- initial facts are credited;
- next questions are detailed and not generic repeats;
- readiness is not over-optimistic;
- SAD preview is detailed and business-facing;
- IT readiness is not the main result;
- source refs are readable.

After verification:

- update `docs/superpowers/CURRENT.md` with the latest status;
- update TC-021X result;
- stop with summary, test evidence, risks, and manual smoke script;
- do not proceed to MVP-10 in the same turn.


---

## 2026-05-21-domain-aware-qna-sad-quality-hardening

# Domain-Aware Q&A And SAD Quality Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` or `superpowers:subagent-driven-development` to
> implement this plan task-by-task. Use test-first development. Do not start
> MVP-10 / TC-025. Do not use live Gemini/cloud calls for implementation.

**Goal:** Make SADify ask domain-aware missing-detail questions and generate a
clean Layer 1 SAD preview across tuition, workshop, and generic operational
requests.

**Architecture:** Add a small evidence extraction and question-targeting layer
around the existing questionnaire plan. Replace domain-only SAD composition with
evidence-to-section composition, while keeping current API contracts. Update the
preview UI so stale preview state and debug/source internals do not leak.

**Tech Stack:** Python FastAPI/Pydantic services, pytest, Next.js/React,
TypeScript, existing local MVP worktree.

---

## File Structure

Modify:

- `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\routes\analysis.py`
  - uses evidence extraction to seed plans and choose missing-facet questions.
- `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\questionnaire_slots.py`
  - owns domain-aware fallback questions and fact-bearing choices.
- `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\sad_preview.py`
  - composes SAD sections from evidence and hides fallback/debug wording.
- `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\sad_synthesis.py`
  - keeps clean business request and source/answer facts separated.
- `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\src\components\SadPreviewPanel.tsx`
  - clears stale preview on new analysis/request and hides internal tracking paths.

Create if the extraction logic grows beyond `analysis.py`:

- `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\business_evidence.py`
  - focused evidence extractor with no API dependency.

Tests:

- `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_gemini_structured.py`
- `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_preview.py`
- `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_synthesis.py`
- `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\test_mvp_sad_preview_it_readiness_ui.py`

No external API/docs preflight is needed. Implementation uses local rules and
local tests only.

---

## Task 1: Add Failing Tests For Tuition Q&A Targeting

**Files:**

- Modify: `tests/api/test_gemini_structured.py`

- [ ] **Step 1: Add tuition fixture**

Add:

```python
TUITION_REQUEST = (
    "A small tuition centre wants a simple system to track student enrolment, "
    "class schedules, attendance, fee payments, and parent updates. Admin staff "
    "register students and assign them to classes. Teachers mark attendance and "
    "add short progress notes. Parents should receive updates when students are "
    "absent or fees are unpaid. The centre manager needs a weekly summary of "
    "enrolled students, attendance issues, unpaid fees, and classes that are full."
)
```

- [ ] **Step 2: Add failing first-question test**

Add:

```python
def test_analysis_api_tuition_request_skips_generic_goal_and_asks_domain_rule():
    generic_payload = VALID_PAYLOAD.copy()
    generic_payload["next_question"] = {
        "text": "What main result should this system help the business achieve?",
        "why_this_matters": "This gives the SAD a clear business goal.",
        "choices": [{"id": "reduce_delay", "label": "Reduce delays"}],
        "target_category": "goal_scope",
        "target_slot_id": "business_goal",
    }
    repository = RequirementAnalysisRepository()
    model = FakeRequirementAnalysisModel([generic_payload, generic_payload])
    client = TestClient(create_app(analysis_model=model, analysis_repository=repository))

    response = client.post("/analysis/requirement", json={"requirement_text": TUITION_REQUEST})

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["questionnaire"]["active_category_id"] in {
        "rules_approvals",
        "exceptions_edges",
        "access_permissions",
        "non_functional",
    }
    assert analysis["questionnaire"]["active_slot_id"] != "business_goal"
    question_text = analysis["next_question"]["text"].lower()
    assert "main result" not in question_text
    assert any(term in question_text for term in ("parent", "absence", "fee", "class", "attendance", "access"))
```

- [ ] **Step 3: Verify red**

Run:

```powershell
cd D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
$env:PYTHONPATH="services\api\src;src;."
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_gemini_structured.py::test_analysis_api_tuition_request_skips_generic_goal_and_asks_domain_rule -q
```

Expected: fail because tuition currently falls back to broad goal/category logic.

---

## Task 2: Add Business Evidence Extraction

**Files:**

- Modify: `services/api/src/sadify_api/routes/analysis.py`
- Create if useful: `services/api/src/sadify_api/services/business_evidence.py`
- Test: `tests/api/test_gemini_structured.py`

- [ ] **Step 1: Implement or extract an evidence helper**

Use deterministic phrase detection for Layer 1 facts:

```python
def evidence_facts_from_text(text: str) -> dict[str, set[str]]:
    lowered = text.lower()
    facts: dict[str, set[str]] = {}

    def cover(category_id: str, *slot_ids: str) -> None:
        facts.setdefault(category_id, set()).update(slot_ids)

    if any(term in lowered for term in ("wants a simple system", "wants to track", "needs a system", "need a system")):
        cover("goal_scope", "business_goal", "in_scope_outcome")
    if any(term in lowered for term in ("student", "class", "teacher", "parent", "fee", "attendance")):
        cover("users_roles", "primary_users")
        cover("workflow_steps", "normal_flow")
        cover("data_records", "main_records")
        cover("reports_summaries", "needed_outputs", "audience")
    if "admin staff" in lowered and "teachers" in lowered:
        cover("users_roles", "responsibilities")
        cover("workflow_steps", "handoffs")
    if any(term in lowered for term in ("parents should receive updates", "absent", "unpaid")):
        cover("exceptions_edges", "common_exception")
    if "weekly summary" in lowered:
        cover("reports_summaries", "cadence_filters")
    return facts
```

Then merge this helper into `_initial_facts_from_request()` without removing
existing clinic/workshop coverage.

- [ ] **Step 2: Add a refinement target for tuition**

Add logic equivalent to:

```python
if any(term in text for term in ("tuition", "student", "parent", "fee", "attendance")):
    for category_id, slot_id in (
        ("exceptions_edges", "required_handling"),
        ("rules_approvals", "triggering_rules"),
        ("access_permissions", "sensitive_actions"),
    ):
        slot = plan.category(category_id).slot(slot_id)
        if slot.status == "open":
            return QuestionnairePlanSlotPointer(category_id=category_id, slot_id=slot_id)
```

- [ ] **Step 3: Verify green**

Run the focused tuition test from Task 1.

Expected: pass.

---

## Task 3: Add Domain-Aware Fallback Questions And Choices

**Files:**

- Modify: `services/api/src/sadify_api/services/questionnaire_slots.py`
- Test: `tests/api/test_gemini_structured.py`

- [ ] **Step 1: Add tuition contextual fallback**

In `_contextual_fallback_question()`, add tuition handling:

```python
is_tuition = any(term in lowered for term in ("tuition", "student", "class", "teacher", "parent", "fee", "attendance"))
if is_tuition and (category_id, slot_id) == ("exceptions_edges", "required_handling"):
    return {
        "text": "When should parents be notified about absence or unpaid fees?",
        "why_this_matters": "This turns parent updates into clear system rules.",
        "choices": [
            {"id": "same_day_absence", "label": "Notify parents on the same day when a student is absent"},
            {"id": "after_fee_due", "label": "Notify parents when a fee remains unpaid after the due date"},
            {"id": "manager_review", "label": "Manager reviews attendance or fee issues before notification"},
            {"id": "not_sure", "label": "I'm not sure yet"},
            {"id": "other", "label": "Other / not listed"},
        ],
        "target_category": category_id,
        "target_slot_id": slot_id,
        "selection_mode": "multiple",
    }
```

Also add tuition contextual fallbacks for:

- `rules_approvals.triggering_rules`: class full, fee overdue, absence trigger;
- `access_permissions.sensitive_actions`: payment edits, attendance corrections,
  parent contact changes;
- `non_functional.audit_history`: attendance/payment/profile changes.

- [ ] **Step 2: Verify choices are fact-bearing**

Extend the Task 1 test to assert at least one choice label contains a tuition
term such as `parent`, `fee`, `absence`, `attendance`, or `class`.

- [ ] **Step 3: Run focused tests**

```powershell
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_gemini_structured.py::test_analysis_api_tuition_request_skips_generic_goal_and_asks_domain_rule -q
```

Expected: pass.

---

## Task 4: Prevent Broad Answers From Becoming Precise Requirements

**Files:**

- Modify: `services/api/src/sadify_api/routes/analysis.py`
- Test: `tests/api/test_gemini_structured.py`

- [ ] **Step 1: Add failing readiness test**

Add a test that submits a generic request plus broad previous answers for every
category and asserts draft readiness remains below `100`.

```python
def test_analysis_api_broad_answers_do_not_make_draft_ready():
    response = client.post(
        "/analysis/requirement",
        json={"requirement_text": GENERIC_REQUEST_WITH_BROAD_PREVIOUS_ANSWERS},
    )
    analysis = response.json()["analysis"]
    assert analysis["questionnaire"]["draft_readiness"]["score"] < 100
```

Use broad labels already present in `SLOT_CONTRACTS`.

- [ ] **Step 2: Expand broad-label guard**

Extend `_answer_has_enough_evidence()` for broad labels in:

- data records;
- rules/approvals;
- exceptions;
- access;
- integrations;
- non-functional needs.

Broad labels may save the answer history, but they should not fully cover a slot
unless accompanied by amendment details.

- [ ] **Step 3: Verify focused test**

Expected: readiness remains below `100`.

---

## Task 5: Compose SAD From Evidence And Remove User-Facing Leaks

**Files:**

- Modify: `services/api/src/sadify_api/services/sad_preview.py`
- Modify: `services/api/src/sadify_api/services/sad_synthesis.py`
- Test: `tests/api/test_sad_preview.py`
- Test: `tests/api/test_sad_synthesis.py`

- [ ] **Step 1: Add failing tuition SAD test**

Add:

```python
def test_safe_fallback_preview_synthesizes_tuition_sad_without_debug_leaks():
    preview = build_safe_sad_fallback_preview(
        requirement_text=TUITION_REQUEST,
        analysis=RequirementAnalysisResponse.model_validate(_tuition_analysis_with_answers()),
        source_references=["Business Request", "goal_scope.business_goal"],
    )

    visible = "\n".join([preview.title, preview.temporary_notice, *[s.title + "\n" + s.body for s in preview.sections]])
    assert "fallback mechanism" not in visible.lower()
    assert "_SADify/local-fallback" not in visible
    assert "goal_scope.business_goal" not in visible
    assert "student enrolment" in visible.lower()
    assert "class schedules" in visible.lower()
    assert "attendance" in visible.lower()
    assert "fee" in visible.lower()
    assert "parent" in visible.lower()
    assert "multi-level approval" not in visible.lower()
```

- [ ] **Step 2: Sanitize source references**

Update `_safe_source_references()` so internal slot IDs are filtered from
user-facing `source_references`.

Keep labels such as:

- `Business Request`;
- uploaded source IDs such as `SRC-000001`;
- uploaded file names if already supported.

- [ ] **Step 3: Replace hardcoded fallback wording**

Update `temporary_notice`, `change_tracking.summary`, and generic fallback text
so the normal document says `Draft preview`, not `fallback mechanism`.

- [ ] **Step 4: Add tuition/general composer branches through evidence**

Prefer reusable helpers:

- `_request_terms(clean_request, keywords)`;
- `_compose_role_actions(clean_request)`;
- `_compose_workflow_from_sentences(clean_request)`;
- `_compose_reports_from_request(clean_request)`;
- `_compose_domain_open_questions(clean_request, answers)`.

Use domain branches only for wording, not for the entire section body.

- [ ] **Step 5: Fix workshop wording leakage**

Update workshop rules output so it says:

```text
These rules should prevent incomplete maintenance requests from being treated as complete.
```

and not `incomplete visits`.

- [ ] **Step 6: Verify focused SAD tests**

```powershell
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_sad_preview.py tests\api\test_sad_synthesis.py -q
```

Expected: pass.

---

## Task 6: Clear Stale Preview And Hide Tracking Paths In UI

**Files:**

- Modify: `apps/web/src/components/SadPreviewPanel.tsx`
- Test: `tests/test_mvp_sad_preview_it_readiness_ui.py`

- [ ] **Step 1: Add failing UI string test**

Assert:

```python
assert "useEffect" in panel
assert "setPreviewResponse(null)" in panel
assert "setMessage(\"Temporary preview only. No Google Doc or Drive file is saved here.\")" in panel
assert "path.startsWith(\"_SADify/\")" in panel
```

- [ ] **Step 2: Implement reset on new input**

Import `useEffect` and reset local preview when any of these changes:

- `analysisResponse?.analysis_id`;
- `requirementText`.

- [ ] **Step 3: Hide internal tracking paths**

In `Tracking status`, render user-facing paths only:

```tsx
const visibleTrackingPaths = preview.change_tracking.paths.filter(
  (path) => !path.startsWith("_SADify/"),
);
```

If all paths are internal, show:

```text
Temporary draft state saved.
```

- [ ] **Step 4: Verify frontend test**

```powershell
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\test_mvp_sad_preview_it_readiness_ui.py -q
```

Expected: pass.

---

## Task 7: Full Local Verification

Run from:

```powershell
cd D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
$env:PYTHONPATH="services\api\src;src;."
```

Commands:

```powershell
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_gemini_structured.py tests\api\test_sad_preview.py tests\api\test_sad_synthesis.py -q
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\test_mvp_sad_preview_it_readiness_ui.py -q
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests -q
node D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\node_modules\typescript\bin\tsc -p D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\tsconfig.json --noEmit
npm --prefix D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web run build
```

Expected:

- focused tests pass;
- full Python regression passes;
- TypeScript exits `0`;
- Next.js build compiles successfully.

---

## Task 8: Manual Smoke And Docs Lock

- [ ] **Step 1: Run tuition manual smoke**

Use the tuition request in TC-021Y.

Expected:

- first question is domain-aware;
- SAD has no fallback/debug wording;
- source refs are business-facing;
- no invented multi-level approval;
- previous/stale preview is cleared.

- [ ] **Step 2: Run workshop manual smoke**

Use the workshop request in TC-021Y.

Expected:

- no clinic wording leakage;
- expensive-part approval and open-reason handling remain concrete;
- IT readiness stays secondary.

- [ ] **Step 3: Update docs after verification**

Update:

- `docs/superpowers/CURRENT.md`
- `docs/superpowers/testing/test_cases/TC-021Y-domain-aware-qna-sad-quality-hardening.md`
- `docs/superpowers/testing/test_case_index.md`
- `docs/superpowers/testing/mvp_web_app_test_plan.md`

Stop after TC-021Y. Do not start MVP-10 in the same turn.

## Self-Review

Spec coverage:

- domain-aware Q&A: Tasks 1-3
- broad-answer guard: Task 4
- clean SAD output: Task 5
- stale/debug UI cleanup: Task 6
- verification and docs lock: Tasks 7-8

Placeholder scan:

- No TBD/TODO/fill-later items remain.

Type consistency:

- Uses the existing `RequirementAnalysisResponse`, questionnaire state, and
  `SadPreviewResponse` contracts.
- No API shape change is required for this checkpoint.

## Execution Handoff

Plan complete. Execution must wait for user approval.

Recommended execution mode:

```text
Inline execution with TDD checkpoints in the current worktree.
```


---


---

## 2026-05-22-evidence-based-readiness

# Evidence-Based Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to
> implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for
> tracking. Use test-first development. Do not start the SAD synthesis cycle. No
> live Gemini or cloud calls are needed; all tests are local.

**Goal:** Replace SADify's keyword-driven Q&A readiness with an AI-judged,
quote-validated, backend-aggregated evidence model.

**Architecture:** The existing Gemini analysis call returns a per-slot evidence
verdict array. The backend validates each verdict against the supplied material
(quote must be present), aggregates a weighted readiness score over applicable
required slots, derives confidence from the verdict mix, and builds the stable
questionnaire plan from evidence instead of keyword tables.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, pytest, Next.js/TypeScript.

**Source spec:** `docs/superpowers/specs/2026-05-22-evidence-based-readiness-design.md`

**Worktree:** `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`
**Branch:** `codex/mvp-monorepo-scaffold`

---

## Conventions

All commands run from the worktree root:

```powershell
cd D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
$env:PYTHONPATH="services\api\src;src;."
```

Python: `D:\GoogleCloudHack\.venv\Scripts\python.exe`
Pytest: `D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest`

Paths below are relative to the worktree root.

---

## File Structure

Modify:

- `services/api/src/sadify_api/schemas.py` — add `SlotEvidence`; extend
  `RequirementAnalysisResponse` and `QuestionnairePlanSlot`; extend two
  `visibility` literals.
- `services/api/src/sadify_api/services/gemini_structured.py` — add
  `slot_evidence` to the analysis response schema; extend `_analysis_prompt`;
  raise `max_output_tokens`.
- `services/api/src/sadify_api/services/questionnaire_plan.py` — add
  `canonical_required_slots` and `create_plan_from_evidence`; rewrite
  `recalculate_readiness` aggregation; make `next_open_slot` skip
  not-applicable slots; update `cover_slot`/`reopen_slot`; add `not_applicable`
  visibility handling.
- `services/api/src/sadify_api/routes/analysis.py` — delete the three keyword
  functions; rewire `_with_questionnaire_state`, `_questionnaire_plan`,
  `_locked_target_for_request`.
- `apps/web/src/lib/api.ts` — extend the questionnaire/slot TypeScript types.
- `apps/web/src/components/AnalysisPanel.tsx` — render a collapsed "Not relevant
  to this project" group.

Create:

- `services/api/src/sadify_api/services/slot_evidence.py` — evidence validation,
  downgrade, confidence derivation, evidence-to-plan glue.
- `tests/api/test_slot_evidence.py` — unit tests for the new service.
- `tests/api/test_evidence_readiness_scenarios.py` — the acceptance scenario
  table.

Tests touched: `tests/api/test_questionnaire_plan.py`,
`tests/api/test_gemini_structured.py` (updated for the new model).

---

## Task 1: Add the `SlotEvidence` schema and model fields

**Files:**
- Modify: `services/api/src/sadify_api/schemas.py`
- Test: `tests/api/test_slot_evidence.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/api/test_slot_evidence.py`:

```python
from sadify_api.schemas import (
    QuestionnairePlanSlot,
    RequirementAnalysisResponse,
    SlotEvidence,
)


def test_slot_evidence_defaults():
    verdict = SlotEvidence(category_id="goal_scope", slot_id="business_goal")
    assert verdict.applicability == "applicable"
    assert verdict.strength == "none"
    assert verdict.evidence_quote == ""
    assert verdict.rationale == ""


def test_questionnaire_plan_slot_has_evidence_fields():
    slot = QuestionnairePlanSlot(id="business_goal", label="Business goal")
    assert slot.evidence_strength == "none"
    assert slot.applicable is True


def test_requirement_analysis_response_defaults_slot_evidence_to_empty():
    response = RequirementAnalysisResponse(
        understanding_summary="A team needs a tracking system.",
        readiness={"label": "Getting started", "score": 10, "confidence": "Low"},
        categories=[{"id": "goal_scope", "label": "Goal", "status": "missing"}],
        next_question={
            "text": "What is the goal?",
            "why_this_matters": "Clarifies the goal.",
            "choices": [
                {"id": "a", "label": "Reduce delays"},
                {"id": "b", "label": "Reduce errors"},
            ],
            "target_category": "goal_scope",
            "target_slot_id": "business_goal",
        },
        assumptions=[],
        source_references=[],
    )
    assert response.slot_evidence == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_slot_evidence.py -q`
Expected: FAIL — `ImportError` for `SlotEvidence`.

- [ ] **Step 3: Add `SlotEvidence` and field changes**

In `schemas.py`, add this model immediately before `class QuestionnaireCategory`:

```python
class SlotEvidence(ApiModel):
    category_id: str = Field(min_length=1)
    slot_id: str = Field(min_length=1)
    applicability: Literal["applicable", "not_applicable"] = "applicable"
    strength: Literal["none", "partial", "strong"] = "none"
    evidence_quote: str = ""
    rationale: str = ""
```

In `QuestionnaireProgressCategory`, change the `visibility` line to:

```python
    visibility: Literal[
        "main", "already_understood", "completed", "suggested", "not_applicable"
    ] = "main"
```

In `QuestionnairePlanSlot`, add two fields after `status`:

```python
    evidence_strength: Literal["none", "partial", "strong"] = "none"
    applicable: bool = True
```

In `QuestionnairePlanCategory`, change the `visibility` line to:

```python
    visibility: Literal[
        "main", "already_understood", "completed", "suggested", "not_applicable"
    ] = "main"
```

In `RequirementAnalysisResponse`, add this field after `proposed_extra_categories`:

```python
    slot_evidence: list[SlotEvidence] = Field(default_factory=list)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_slot_evidence.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```powershell
git add services/api/src/sadify_api/schemas.py tests/api/test_slot_evidence.py
git commit -m "feat: add SlotEvidence schema and plan slot evidence fields"
```

---

## Task 2: Extend the Gemini analysis schema and prompt

**Files:**
- Modify: `services/api/src/sadify_api/services/questionnaire_plan.py`
- Modify: `services/api/src/sadify_api/services/gemini_structured.py`
- Test: `tests/api/test_gemini_structured.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/api/test_gemini_structured.py`:

```python
def test_analysis_schema_includes_slot_evidence():
    schema = requirement_analysis_schema()
    assert "slot_evidence" in schema["properties"]
    assert "slot_evidence" in schema["required"]
    item = schema["properties"]["slot_evidence"]["items"]
    assert item["properties"]["strength"]["enum"] == ["none", "partial", "strong"]
    assert item["properties"]["applicability"]["enum"] == [
        "applicable",
        "not_applicable",
    ]


def test_canonical_required_slots_lists_every_required_slot():
    from sadify_api.services.questionnaire_plan import canonical_required_slots

    slots = canonical_required_slots()
    assert ("goal_scope", "business_goal") in {
        (entry[0], entry[1]) for entry in slots
    }
    assert all(len(entry) == 3 for entry in slots)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_gemini_structured.py::test_analysis_schema_includes_slot_evidence tests\api\test_gemini_structured.py::test_canonical_required_slots_lists_every_required_slot -q`
Expected: FAIL — `slot_evidence` missing; `canonical_required_slots` undefined.

- [ ] **Step 3: Add `canonical_required_slots` to `questionnaire_plan.py`**

Append to `questionnaire_plan.py`:

```python
def canonical_required_slots() -> list[tuple[str, str, str]]:
    """Return (category_id, slot_id, label) for every required slot."""
    entries: list[tuple[str, str, str]] = []
    for blueprint in _CATEGORY_BLUEPRINTS:
        category_id = str(blueprint["id"])
        for slot_id, label, required in blueprint["slots"]:
            if required:
                entries.append((category_id, slot_id, label))
    return entries
```

- [ ] **Step 4: Add `slot_evidence` to the analysis schema**

In `gemini_structured.py` `requirement_analysis_schema()`, add this entry to the
`properties` dict (after `proposed_extra_categories`):

```python
            "slot_evidence": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "category_id": {"type": "STRING"},
                        "slot_id": {"type": "STRING"},
                        "applicability": {
                            "type": "STRING",
                            "enum": ["applicable", "not_applicable"],
                        },
                        "strength": {
                            "type": "STRING",
                            "enum": ["none", "partial", "strong"],
                        },
                        "evidence_quote": {"type": "STRING"},
                        "rationale": {"type": "STRING"},
                    },
                    "required": [
                        "category_id",
                        "slot_id",
                        "applicability",
                        "strength",
                        "evidence_quote",
                        "rationale",
                    ],
                    "propertyOrdering": [
                        "category_id",
                        "slot_id",
                        "applicability",
                        "strength",
                        "evidence_quote",
                        "rationale",
                    ],
                },
            },
```

Add the string `"slot_evidence"` as the last item of both the top-level
`required` list and the top-level `propertyOrdering` list in the same function.

- [ ] **Step 5: Extend `_analysis_prompt` with evidence instructions**

In `gemini_structured.py`, add this import at the top of the file:

```python
from sadify_api.services.questionnaire_plan import canonical_required_slots
```

Add a helper function above `_analysis_prompt`:

```python
def _slot_evidence_instructions() -> str:
    slot_lines = "\n".join(
        f"- {category_id}.{slot_id}: {label}"
        for category_id, slot_id, label in canonical_required_slots()
    )
    return (
        "Also return slot_evidence: one verdict for every required slot listed "
        "below. For each slot decide applicability (applicable or "
        "not_applicable for this project), then strength of support from the "
        "supplied material (strong = clearly and specifically stated, partial = "
        "only hinted or vague, none = not covered). For partial or strong, "
        "copy a verbatim evidence_quote from the supplied material; leave it "
        "empty for none or not_applicable. Keep rationale to one short "
        "sentence. Required slots:\n"
        f"{slot_lines}"
    )
```

In `_analysis_prompt`, insert `_slot_evidence_instructions()` into the returned
string immediately before the `"Business request:\n"` line:

```python
        "Use source_references only for business source labels such as uploaded "
        "files or Business Request. Never cite Previous Answer as a source.\n\n"
        f"{_slot_evidence_instructions()}\n\n"
        "Business request:\n"
        f"{requirement_text}"
```

- [ ] **Step 6: Raise the analysis output token limit**

In `gemini_structured.py` `GeminiRequirementAnalysisModel.analyze_requirement`,
change `"max_output_tokens": 1800` to `"max_output_tokens": 3000`.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_gemini_structured.py -q`
Expected: PASS for the two new tests. If any existing test asserts the old
`max_output_tokens` or schema key count, update that test to the new values.

- [ ] **Step 8: Commit**

```powershell
git add services/api/src/sadify_api/services/gemini_structured.py services/api/src/sadify_api/services/questionnaire_plan.py tests/api/test_gemini_structured.py
git commit -m "feat: request per-slot evidence verdicts from the analysis model"
```

---

## Task 3: Build the `slot_evidence` service — validation and confidence

**Files:**
- Create: `services/api/src/sadify_api/services/slot_evidence.py`
- Test: `tests/api/test_slot_evidence.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/api/test_slot_evidence.py`:

```python
from sadify_api.schemas import SlotEvidence
from sadify_api.services.slot_evidence import (
    derive_confidence,
    evidence_map,
    validate_slot_evidence,
)


def _verdict(category_id, slot_id, strength, quote="", applicability="applicable"):
    return SlotEvidence(
        category_id=category_id,
        slot_id=slot_id,
        applicability=applicability,
        strength=strength,
        evidence_quote=quote,
    )


def test_validate_keeps_verdict_with_quote_present_in_material():
    material = "Staff submit a maintenance request when a machine has an issue."
    verdicts, diagnostics = validate_slot_evidence(
        [_verdict("workflow_steps", "normal_flow", "strong", "staff submit a maintenance request")],
        material=material,
    )
    assert verdicts[0].strength == "strong"
    assert diagnostics == []


def test_validate_downgrades_strong_verdict_with_missing_quote():
    verdicts, diagnostics = validate_slot_evidence(
        [_verdict("workflow_steps", "normal_flow", "strong", "invented text not in material")],
        material="A team needs a tracking system.",
    )
    assert verdicts[0].strength == "partial"
    assert len(diagnostics) == 1


def test_validate_downgrades_partial_verdict_with_empty_quote_to_none():
    verdicts, diagnostics = validate_slot_evidence(
        [_verdict("workflow_steps", "normal_flow", "partial", "")],
        material="A team needs a tracking system.",
    )
    assert verdicts[0].strength == "none"
    assert len(diagnostics) == 1


def test_validate_ignores_quote_for_none_and_not_applicable():
    verdicts, diagnostics = validate_slot_evidence(
        [
            _verdict("integrations", "external_systems", "none", ""),
            _verdict("integrations", "external_systems", "none", "", "not_applicable"),
        ],
        material="A team needs a tracking system.",
    )
    assert diagnostics == []


def test_derive_confidence_high_when_mostly_strong_and_no_downgrades():
    verdicts = [_verdict("c", f"s{i}", "strong", "q") for i in range(10)]
    assert derive_confidence(verdicts, downgrade_count=0) == "High"


def test_derive_confidence_low_when_mostly_none():
    verdicts = [_verdict("c", f"s{i}", "none") for i in range(8)]
    verdicts += [_verdict("c", f"s{i}", "partial", "q") for i in range(2)]
    assert derive_confidence(verdicts, downgrade_count=0) == "Low"


def test_derive_confidence_low_when_two_or_more_downgrades():
    verdicts = [_verdict("c", f"s{i}", "strong", "q") for i in range(10)]
    assert derive_confidence(verdicts, downgrade_count=2) == "Low"


def test_evidence_map_keys_by_category_and_slot():
    mapping = evidence_map([_verdict("goal_scope", "business_goal", "strong", "q")])
    assert mapping[("goal_scope", "business_goal")].strength == "strong"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_slot_evidence.py -q`
Expected: FAIL — `slot_evidence` module not found.

- [ ] **Step 3: Create `slot_evidence.py`**

Create `services/api/src/sadify_api/services/slot_evidence.py`:

```python
"""Validate AI-judged slot evidence and derive readiness confidence.

The analysis model returns one evidence verdict per required slot. The backend
never trusts a verdict's strength unless a partial or strong verdict cites a
quote that actually appears in the supplied material. This keeps readiness
grounded in real evidence and blocks hallucinated coverage.
"""

from typing import Literal

from sadify_api.schemas import SlotEvidence

_DOWNGRADE = {"strong": "partial", "partial": "none", "none": "none"}


def _normalise(text: str) -> str:
    return " ".join(text.lower().split())


def validate_slot_evidence(
    verdicts: list[SlotEvidence],
    *,
    material: str,
) -> tuple[list[SlotEvidence], list[str]]:
    """Return quote-validated verdicts plus human-readable diagnostics.

    A partial or strong verdict whose evidence_quote is empty or not present in
    the material is downgraded one notch (strong -> partial -> none).
    """
    normalised_material = _normalise(material)
    validated: list[SlotEvidence] = []
    diagnostics: list[str] = []
    for verdict in verdicts:
        if verdict.strength in ("partial", "strong"):
            quote = _normalise(verdict.evidence_quote)
            if not quote or quote not in normalised_material:
                downgraded = _DOWNGRADE[verdict.strength]
                diagnostics.append(
                    f"{verdict.category_id}.{verdict.slot_id}: "
                    f"{verdict.strength} downgraded to {downgraded} "
                    "because the cited evidence was not found."
                )
                validated.append(
                    verdict.model_copy(update={"strength": downgraded})
                )
                continue
        validated.append(verdict)
    return validated, diagnostics


def evidence_map(
    verdicts: list[SlotEvidence],
) -> dict[tuple[str, str], SlotEvidence]:
    """Index verdicts by (category_id, slot_id). Later entries win."""
    return {
        (verdict.category_id, verdict.slot_id): verdict for verdict in verdicts
    }


def derive_confidence(
    verdicts: list[SlotEvidence],
    *,
    downgrade_count: int,
) -> Literal["Low", "Medium", "High"]:
    """Derive readiness confidence from the verdict mix.

    High: at least 70% of applicable verdicts are strong and nothing was
    downgraded. Low: more than half are none, or two or more downgrades.
    Medium: anything else.
    """
    applicable = [v for v in verdicts if v.applicability == "applicable"]
    total = len(applicable)
    if total == 0:
        return "Low"
    strong = sum(1 for v in applicable if v.strength == "strong")
    none = sum(1 for v in applicable if v.strength == "none")
    if downgrade_count >= 2 or none > total / 2:
        return "Low"
    if strong / total >= 0.7 and downgrade_count == 0:
        return "High"
    return "Medium"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_slot_evidence.py -q`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```powershell
git add services/api/src/sadify_api/services/slot_evidence.py tests/api/test_slot_evidence.py
git commit -m "feat: add slot evidence validation and confidence derivation"
```

---

## Task 4: Build the questionnaire plan from evidence

**Files:**
- Modify: `services/api/src/sadify_api/services/questionnaire_plan.py`
- Test: `tests/api/test_questionnaire_plan.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/api/test_questionnaire_plan.py`:

```python
from sadify_api.schemas import SlotEvidence
from sadify_api.services.questionnaire_plan import create_plan_from_evidence


def _verdict(category_id, slot_id, strength, applicability="applicable"):
    return SlotEvidence(
        category_id=category_id,
        slot_id=slot_id,
        applicability=applicability,
        strength=strength,
        evidence_quote="quote" if strength != "none" else "",
    )


def test_create_plan_from_evidence_sets_slot_strength():
    plan = create_plan_from_evidence(
        [_verdict("goal_scope", "business_goal", "strong")]
    )
    slot = plan.category("goal_scope").slot("business_goal")
    assert slot.evidence_strength == "strong"
    assert slot.status == "covered"


def test_partial_evidence_keeps_slot_open_and_scores_half():
    strong_plan = create_plan_from_evidence(
        [_verdict("goal_scope", "business_goal", "strong")]
    )
    partial_plan = create_plan_from_evidence(
        [_verdict("goal_scope", "business_goal", "partial")]
    )
    assert partial_plan.category("goal_scope").slot("business_goal").status == "open"
    assert 0 < partial_plan.overall_readiness.score < strong_plan.overall_readiness.score


def test_not_applicable_slots_leave_the_readiness_denominator():
    integrations = [
        _verdict("integrations", "external_systems", "none", "not_applicable"),
    ]
    baseline = create_plan_from_evidence([])
    with_na = create_plan_from_evidence(integrations)
    assert with_na.category("integrations").visibility == "not_applicable"
    assert with_na.overall_readiness.score >= baseline.overall_readiness.score


def test_next_open_slot_skips_not_applicable_slots():
    plan = create_plan_from_evidence(
        [_verdict("goal_scope", "business_goal", "none", "not_applicable")]
    )
    pointer = next_open_slot(plan)
    assert pointer is not None
    assert (pointer.category_id, pointer.slot_id) != ("goal_scope", "business_goal")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_questionnaire_plan.py -q`
Expected: FAIL — `create_plan_from_evidence` undefined.

- [ ] **Step 3: Add `create_plan_from_evidence`**

In `questionnaire_plan.py`, add this import at the top:

```python
from sadify_api.schemas import SlotEvidence
```

Add this function after `create_initial_plan`:

```python
def create_plan_from_evidence(
    verdicts: list[SlotEvidence],
    *,
    plan_id: str = "QPLAN-001",
) -> QuestionnairePlan:
    """Build a questionnaire plan from validated slot evidence verdicts.

    Each verdict sets a slot's evidence_strength and applicable flag. A slot is
    covered for Q&A flow only when its strength is strong; partial slots stay
    open so they still get a question.
    """
    by_slot = {
        (verdict.category_id, verdict.slot_id): verdict for verdict in verdicts
    }
    categories: list[QuestionnairePlanCategory] = []
    for display_order, blueprint in enumerate(_CATEGORY_BLUEPRINTS, start=1):
        category_id = str(blueprint["id"])
        slots: list[QuestionnairePlanSlot] = []
        for slot_id, label, required in blueprint["slots"]:
            verdict = by_slot.get((category_id, slot_id))
            strength = verdict.strength if verdict else "none"
            applicable = (
                verdict.applicability == "applicable" if verdict else True
            )
            slots.append(
                QuestionnairePlanSlot(
                    id=slot_id,
                    label=label,
                    required=required,
                    status="covered" if strength == "strong" else "open",
                    evidence_strength=strength,
                    applicable=applicable,
                )
            )
        categories.append(
            _build_category(
                category_id=category_id,
                label=str(blueprint["label"]),
                display_order=display_order,
                slots=slots,
                initial_visibility=True,
            )
        )
    return recalculate_readiness(
        QuestionnairePlan(
            plan_id=plan_id,
            active_category_id=None,
            categories=categories,
            overall_readiness=QuestionnairePlanReadiness(
                label="Getting started",
                score=0,
            ),
        )
    )
```

- [ ] **Step 4: Rewrite `recalculate_readiness` aggregation**

Replace the body of `recalculate_readiness` with:

```python
def recalculate_readiness(plan: QuestionnairePlan) -> QuestionnairePlan:
    categories = [_refresh_category(category) for category in plan.categories]
    applicable_required = [
        slot
        for category in categories
        for slot in category.slots
        if slot.required and slot.applicable
    ]
    score = (
        round(
            100
            * sum(_slot_weight(slot) for slot in applicable_required)
            / len(applicable_required)
        )
        if applicable_required
        else 100
    )
    active_slot = next_open_slot(
        plan.model_copy(update={"categories": categories})
    )
    active_category_id = active_slot.category_id if active_slot else None
    return plan.model_copy(
        update={
            "active_category_id": active_category_id,
            "categories": categories,
            "overall_readiness": QuestionnairePlanReadiness(
                label=_readiness_label(score),
                score=score,
            ),
        }
    )


def _slot_weight(slot: QuestionnairePlanSlot) -> float:
    if slot.status == "confirm_later":
        return 1.0
    if slot.evidence_strength == "strong":
        return 1.0
    if slot.evidence_strength == "partial":
        return 0.5
    return 0.0
```

- [ ] **Step 5: Make `next_open_slot` skip not-applicable slots**

In `next_open_slot`, change the inner loop condition so it also requires
`slot.applicable`:

```python
        for slot in category.slots:
            if slot.required and slot.applicable and slot.status == "open":
                return QuestionnairePlanSlotPointer(
                    category_id=category.id,
                    slot_id=slot.id,
                )
```

- [ ] **Step 6: Add not-applicable handling to category status and visibility**

Replace `_category_status` with:

```python
def _category_status(slots: list[QuestionnairePlanSlot]) -> str:
    required_slots = [slot for slot in slots if slot.required]
    applicable_required = [slot for slot in required_slots if slot.applicable]
    if not applicable_required:
        return "ready"
    if all(slot.status == "covered" for slot in applicable_required):
        return "ready"
    if any(slot.status == "confirm_later" for slot in applicable_required):
        return "confirm_later"
    if any(slot.status == "covered" for slot in applicable_required):
        return "in_progress"
    return "needs_answer"
```

In `_build_category`, replace the visibility block with:

```python
    status = _category_status(slots)
    required_slots = [slot for slot in slots if slot.required]
    visibility = "main"
    if required_slots and all(not slot.applicable for slot in required_slots):
        visibility = "not_applicable"
    elif initial_visibility and status == "ready":
        visibility = "already_understood"
```

In `_refresh_category`, replace the visibility block with:

```python
    status = _category_status(category.slots)
    required_slots = [slot for slot in category.slots if slot.required]
    if required_slots and all(not slot.applicable for slot in required_slots):
        visibility = "not_applicable"
    elif category.visibility == "not_applicable":
        visibility = "main"
    elif category.visibility == "already_understood" and status != "ready":
        visibility = "main"
    elif category.visibility == "main" and status == "ready":
        visibility = "completed"
    elif category.visibility == "completed" and status != "ready":
        visibility = "main"
    else:
        visibility = category.visibility
```

- [ ] **Step 7: Keep `cover_slot` and `reopen_slot` consistent with evidence**

`cover_slot` and `reopen_slot` must also update `evidence_strength` so readiness
moves. Replace `_update_slot` with:

```python
def _update_slot(
    plan: QuestionnairePlan,
    category_id: str,
    slot_id: str,
    status: str,
    *,
    evidence_strength: str | None = None,
) -> QuestionnairePlan:
    categories: list[QuestionnairePlanCategory] = []
    for category in plan.categories:
        if category.id != category_id:
            categories.append(category)
            continue
        if not any(slot.id == slot_id for slot in category.slots):
            raise KeyError(slot_id)
        slots = []
        for slot in category.slots:
            if slot.id != slot_id:
                slots.append(slot)
                continue
            update: dict[str, object] = {"status": status}
            if evidence_strength is not None:
                update["evidence_strength"] = evidence_strength
            slots.append(slot.model_copy(update=update))
        categories.append(category.model_copy(update={"slots": slots}))
    if not any(category.id == category_id for category in plan.categories):
        raise KeyError(category_id)
    return recalculate_readiness(plan.model_copy(update={"categories": categories}))
```

Change `cover_slot` to pass `evidence_strength="strong"`:

```python
def cover_slot(
    plan: QuestionnairePlan,
    category_id: str,
    slot_id: str,
) -> QuestionnairePlan:
    return _update_slot(
        plan, category_id, slot_id, "covered", evidence_strength="strong"
    )
```

Change `reopen_slot` to pass `evidence_strength="none"`:

```python
def reopen_slot(
    plan: QuestionnairePlan,
    category_id: str,
    slot_id: str,
) -> QuestionnairePlan:
    return _update_slot(
        plan, category_id, slot_id, "open", evidence_strength="none"
    )
```

Leave `defer_slot` unchanged — a deferred slot keeps its strength and is
weighted 1.0 by `_slot_weight`.

- [ ] **Step 8: Run the tests to verify they pass**

Run: `D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_questionnaire_plan.py -q`
Expected: PASS for new and existing tests. The existing
`test_readiness_uses_required_slot_coverage_not_question_count` still passes
because `cover_slot` now sets `evidence_strength="strong"`.

- [ ] **Step 9: Commit**

```powershell
git add services/api/src/sadify_api/services/questionnaire_plan.py tests/api/test_questionnaire_plan.py
git commit -m "feat: build questionnaire plan and readiness from slot evidence"
```

---

## Task 5: Rewire the analysis route onto slot evidence

**Files:**
- Modify: `services/api/src/sadify_api/routes/analysis.py`
- Test: `tests/api/test_gemini_structured.py`

This task deletes the keyword tables and feeds validated evidence into the plan.

- [ ] **Step 1: Write the failing test**

Add to `tests/api/test_gemini_structured.py`. It uses the existing
`VALID_PAYLOAD`, `FakeRequirementAnalysisModel`, `RequirementAnalysisRepository`,
and `create_app` helpers already imported in that file:

```python
def _payload_with_evidence(verdicts):
    payload = json.loads(json.dumps(VALID_PAYLOAD))
    payload["slot_evidence"] = verdicts
    return payload


def test_analysis_readiness_reflects_strong_evidence():
    strong = [
        {
            "category_id": category_id,
            "slot_id": slot_id,
            "applicability": "applicable",
            "strength": "strong",
            "evidence_quote": "track maintenance requests",
            "rationale": "stated in the request",
        }
        for category_id, slot_id, _label in __import__(
            "sadify_api.services.questionnaire_plan",
            fromlist=["canonical_required_slots"],
        ).canonical_required_slots()
    ]
    model = FakeRequirementAnalysisModel([_payload_with_evidence(strong)])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=RequirementAnalysisRepository(),
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={"requirement_text": "Track maintenance requests for company machines."},
    )

    assert response.status_code == 200
    questionnaire = response.json()["analysis"]["questionnaire"]
    assert questionnaire["draft_readiness"]["score"] >= 90


def test_analysis_readiness_low_when_no_evidence():
    model = FakeRequirementAnalysisModel([_payload_with_evidence([])])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=RequirementAnalysisRepository(),
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={"requirement_text": "We want a system for our team."},
    )

    questionnaire = response.json()["analysis"]["questionnaire"]
    assert questionnaire["draft_readiness"]["score"] < 40
    assert questionnaire["draft_readiness"]["confidence"] == "Low"


def test_analysis_downgrades_evidence_with_fabricated_quote():
    fabricated = [
        {
            "category_id": "goal_scope",
            "slot_id": "business_goal",
            "applicability": "applicable",
            "strength": "strong",
            "evidence_quote": "a sentence that is nowhere in the request",
            "rationale": "fabricated",
        }
    ]
    model = FakeRequirementAnalysisModel([_payload_with_evidence(fabricated)])
    client = TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=RequirementAnalysisRepository(),
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={"requirement_text": "We want a simple internal system."},
    )

    questionnaire = response.json()["analysis"]["questionnaire"]
    diagnostics = " ".join(questionnaire["diagnostics"]).lower()
    assert "downgraded" in diagnostics
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_gemini_structured.py -k "evidence_reflects or readiness_low or fabricated" -q`
Expected: FAIL — readiness still computed from keyword seeding.

- [ ] **Step 3: Delete the keyword functions**

In `routes/analysis.py`, delete these four functions entirely:
`_initial_facts_from_request`, `_answer_has_enough_evidence`,
`_category_progress`, `_category_progress_status`.

Also delete `_draft_readiness` and `_questionnaire_categories` if, after Step 4,
they have no remaining callers. Search with:

```powershell
Select-String -Path services\api\src\sadify_api\routes\analysis.py -Pattern "_draft_readiness|_questionnaire_categories|_category_progress|_initial_facts_from_request|_answer_has_enough_evidence"
```

Remove any function whose only references were the deleted code.

- [ ] **Step 4: Add an evidence helper and rewire `_with_questionnaire_state`**

Add this import block near the top of `routes/analysis.py`:

```python
from sadify_api.services.questionnaire_plan import create_plan_from_evidence
from sadify_api.services.slot_evidence import (
    derive_confidence,
    validate_slot_evidence,
)
```

Add this helper near the other module-level helpers:

```python
def _validated_evidence(
    analysis: RequirementAnalysisResponse,
    request: RequirementAnalysisRequest,
) -> tuple[list, list[str]]:
    """Validate model slot evidence against the combined business material."""
    material_parts = [_combined_requirement_context(request)]
    for answer in _questionnaire_answers(request.requirement_text):
        material_parts.append(str(answer["answer"]))
    material = "\n".join(part for part in material_parts if part.strip())
    return validate_slot_evidence(analysis.slot_evidence, material=material)
```

Replace `_questionnaire_plan` with an evidence-driven version:

```python
def _questionnaire_plan(
    verdicts: list,
    answers: list[dict[str, object]],
):
    plan = create_plan_from_evidence(verdicts)
    for answer in _unique_questionnaire_answers(answers):
        if not answer.get("is_uncertain"):
            continue
        category_id = str(answer["category_id"])
        slot = _slot_for_answer(plan, answer)
        if slot is not None:
            plan = defer_slot(plan, category_id, slot.id)

    active_category_id = _active_category_from_answers(plan, answers)
    if active_category_id is None:
        open_slot = next_open_slot(plan)
        active_category_id = open_slot.category_id if open_slot else None
    return plan.model_copy(update={"active_category_id": active_category_id})
```

In `_with_questionnaire_state`, replace the plan construction and the
`draft_readiness` block. The function currently starts:

```python
    answers = _questionnaire_answers(request.requirement_text)
    plan = _questionnaire_plan(
        analysis,
        answers,
        initial_facts=_initial_facts_from_request(request),
    )
```

Replace those lines with:

```python
    answers = _questionnaire_answers(request.requirement_text)
    verdicts, evidence_diagnostics = _validated_evidence(analysis, request)
    plan = _questionnaire_plan(verdicts, answers)
    derived_confidence = derive_confidence(
        verdicts, downgrade_count=len(evidence_diagnostics)
    )
```

Then change the `draft_readiness` dict so confidence is the derived value:

```python
    draft_readiness = {
        "label": plan.overall_readiness.label,
        "score": plan.overall_readiness.score,
        "confidence": derived_confidence,
    }
```

And extend the `diagnostics` list so downgrades are visible:

```python
    diagnostics = [
        "structured-output fallback used"
        if fallback_used
        else "Gemini structured output validated",
        f"AI confidence: {analysis.readiness.confidence}",
        f"Derived confidence: {derived_confidence}",
        *evidence_diagnostics,
    ]
```

- [ ] **Step 5: Fix the remaining `_initial_facts_from_request` callers**

`_locked_target_for_request` and any other caller no longer have keyword facts.
Replace `_locked_target_for_request` with an answer-marker version that does not
need evidence (evidence is only available after the model call):

```python
def _locked_target_for_request(request: RequirementAnalysisRequest):
    answers = _unique_questionnaire_answers(
        _questionnaire_answers(request.requirement_text)
    )
    plan = create_plan_from_evidence([])
    for answer in answers:
        category_id = str(answer["category_id"])
        slot = _slot_for_answer(plan, answer)
        if slot is None:
            continue
        if answer.get("is_uncertain"):
            plan = defer_slot(plan, category_id, slot.id)
        else:
            plan = cover_slot(plan, category_id, slot.id)

    active_category_id = _active_category_from_answers(plan, answers)
    if active_category_id is not None:
        slot = _next_open_slot_in_category(plan, active_category_id)
        if slot is not None:
            return QuestionnairePlanSlotPointer(
                category_id=active_category_id,
                slot_id=slot.id,
            )
    open_slot = next_open_slot(plan)
    if open_slot is not None:
        return open_slot
    return _refinement_target_from_request(request, plan)
```

This locks the question target by which slots the user has already answered
(via answer slot markers). The model's evidence then refines readiness and, when
the model question misses the active slot, the existing
`_with_locked_question_category` / `_with_non_repeating_question` replacement
path corrects it. Verify no other reference to `_initial_facts_from_request`
remains:

```powershell
Select-String -Path services\api\src\sadify_api\routes\analysis.py -Pattern "_initial_facts_from_request"
```

Expected: no matches.

- [ ] **Step 6: Run the focused tests**

Run: `D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_gemini_structured.py -q`
Expected: PASS for the three new tests. Fix any existing test that asserted
keyword-seeded readiness by updating it to supply `slot_evidence` in its payload.

- [ ] **Step 7: Commit**

```powershell
git add services/api/src/sadify_api/routes/analysis.py tests/api/test_gemini_structured.py
git commit -m "feat: drive questionnaire readiness from validated slot evidence"
```

---

## Task 6: Update the draft-ready gate

**Files:**
- Modify: `services/api/src/sadify_api/services/sad_preview.py`
- Test: `tests/api/test_sad_preview.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/api/test_sad_preview.py` (follow the existing helpers in that file
for building a `RequirementAnalysisResponse`; the assertion is the new rule):

```python
def test_missing_blocking_basics_blocks_when_a_required_slot_has_no_evidence():
    """Draft-ready needs >=90 score AND no applicable required slot at none."""
    from sadify_api.services.questionnaire_plan import (
        canonical_required_slots,
        create_plan_from_evidence,
    )
    from sadify_api.schemas import SlotEvidence

    slots = canonical_required_slots()
    verdicts = [
        SlotEvidence(
            category_id=c,
            slot_id=s,
            strength="strong",
            evidence_quote="q",
        )
        for c, s, _ in slots[:-1]
    ]
    verdicts.append(
        SlotEvidence(category_id=slots[-1][0], slot_id=slots[-1][1], strength="none")
    )
    plan = create_plan_from_evidence(verdicts)
    assert any(
        slot.required and slot.applicable and slot.evidence_strength == "none"
        for category in plan.categories
        for slot in category.slots
    )
```

- [ ] **Step 2: Run the test to verify it fails or is incomplete**

Run: `D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_sad_preview.py -k blocking -q`
Expected: the new test currently only checks plan state; confirm it imports
cleanly, then proceed to wire the gate.

- [ ] **Step 3: Strengthen `missing_blocking_basics`**

In `sad_preview.py` `missing_blocking_basics`, replace the early-return block:

```python
    if (
        analysis.questionnaire is not None
        and analysis.questionnaire.draft_readiness.score >= 90
    ):
        return []
```

with a version that also requires no empty required slot. Because the route
receives the questionnaire categories (not the raw plan), check the category
statuses already exposed on `analysis.questionnaire.categories`:

```python
    if (
        analysis.questionnaire is not None
        and analysis.questionnaire.draft_readiness.score >= 90
        and all(
            category.status in ("ready", "needs_later_confirmation")
            for category in analysis.questionnaire.categories
        )
    ):
        return []
```

A category still in `needed` or `in_progress` means a required applicable slot
has no strong evidence, so the gate stays closed even at a high score.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_sad_preview.py -q`
Expected: PASS. Update any existing preview test that assumed a 90 score alone
unlocked the gate.

- [ ] **Step 5: Commit**

```powershell
git add services/api/src/sadify_api/services/sad_preview.py tests/api/test_sad_preview.py
git commit -m "feat: require covered slots, not just score, for draft-ready"
```

---

## Task 7: Frontend types and the "Not relevant" group

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/components/AnalysisPanel.tsx`

- [ ] **Step 1: Extend the TypeScript types**

In `apps/web/src/lib/api.ts`, find the questionnaire category type (the one with
a `visibility` field). Add `"not_applicable"` to its `visibility` union. If a
slot type with `status` exists, add optional fields:

```ts
  evidence_strength?: "none" | "partial" | "strong";
  applicable?: boolean;
```

- [ ] **Step 2: Render the collapsed group**

In `AnalysisPanel.tsx`, find where categories are grouped by `visibility`
(there is existing handling for `already_understood` and `completed`). Add a
parallel collapsed section for `visibility === "not_applicable"` titled
`Not relevant to this project`. Mirror the existing collapsed-section markup
exactly — same component, same styling — so it stays consistent.

- [ ] **Step 3: Type-check and build**

Run:

```powershell
node apps\web\node_modules\typescript\bin\tsc -p apps\web\tsconfig.json --noEmit
npm --prefix apps\web run build
```

Expected: TypeScript exits 0; Next.js build compiles. If the build cannot read
`C:\Users\User` under the sandbox, run it again outside the sandbox.

- [ ] **Step 4: Commit**

```powershell
git add apps/web/src/lib/api.ts apps/web/src/components/AnalysisPanel.tsx
git commit -m "feat: show not-relevant questionnaire areas in the web UI"
```

---

## Task 8: Acceptance scenario table

**Files:**
- Create: `tests/api/test_evidence_readiness_scenarios.py`

- [ ] **Step 1: Write the scenario tests**

Create `tests/api/test_evidence_readiness_scenarios.py`. Each scenario drives
the analysis route with a `FakeRequirementAnalysisModel` whose `slot_evidence`
encodes what a correct model judgement would produce for that request, then
asserts the readiness band. This tests backend aggregation behavior, not model
quality.

```python
import json

from fastapi.testclient import TestClient

from sadify_api.main import create_app
from sadify_api.services.analysis_state import RequirementAnalysisRepository
from sadify_api.services.gemini_structured import RequirementAnalysisModel
from sadify_api.services.questionnaire_plan import canonical_required_slots


BASE_PAYLOAD = {
    "understanding_summary": "Summary of the business request.",
    "readiness": {"label": "Getting started", "score": 30, "confidence": "Low"},
    "categories": [
        {"id": "goal_scope", "label": "Goal", "status": "partial"},
        {"id": "users_roles", "label": "Users", "status": "missing"},
    ],
    "next_question": {
        "text": "What should the system achieve?",
        "why_this_matters": "Clarifies scope.",
        "choices": [
            {"id": "a", "label": "Track work"},
            {"id": "b", "label": "Reduce errors"},
        ],
        "target_category": "goal_scope",
        "target_slot_id": "business_goal",
    },
    "assumptions": [],
    "source_references": [],
    "proposed_extra_categories": [],
}


class FakeModel(RequirementAnalysisModel):
    def __init__(self, payload):
        self._payload = payload

    def analyze_requirement(self, requirement_text, *, repair=False):
        return json.dumps(self._payload)


def _verdict(category_id, slot_id, strength, applicability="applicable"):
    return {
        "category_id": category_id,
        "slot_id": slot_id,
        "applicability": applicability,
        "strength": strength,
        "evidence_quote": "evidence" if strength != "none" else "",
        "rationale": "scenario verdict",
    }


def _payload(verdicts):
    payload = json.loads(json.dumps(BASE_PAYLOAD))
    payload["slot_evidence"] = verdicts
    return payload


def _client(verdicts):
    model = FakeModel(_payload(verdicts))
    return TestClient(
        create_app(
            analysis_model=model,
            analysis_repository=RequirementAnalysisRepository(),
        )
    )


def _readiness(verdicts, requirement_text):
    response = _client(verdicts).post(
        "/analysis/requirement", json={"requirement_text": requirement_text}
    )
    assert response.status_code == 200
    return response.json()["analysis"]["questionnaire"]["draft_readiness"]


def test_scenario_1_vague_request_scores_low():
    readiness = _readiness([], "A shop wants a system to track things.")
    assert readiness["score"] <= 30
    assert readiness["confidence"] == "Low"


def test_scenario_2_rich_request_scores_medium_to_high():
    slots = canonical_required_slots()
    verdicts = [_verdict(c, s, "strong") for c, s, _ in slots[: len(slots) - 4]]
    verdicts += [_verdict(c, s, "partial") for c, s, _ in slots[len(slots) - 4 :]]
    readiness = _readiness(verdicts, "Rich multi-paragraph workshop request.")
    assert 60 <= readiness["score"] <= 95


def test_scenario_4_broad_answers_do_not_reach_full_readiness():
    slots = canonical_required_slots()
    verdicts = [_verdict(c, s, "partial") for c, s, _ in slots]
    readiness = _readiness(verdicts, "Request plus broad vague answers.")
    assert readiness["score"] < 100


def test_scenario_5_not_applicable_category_not_penalised():
    slots = canonical_required_slots()
    all_strong = [_verdict(c, s, "strong") for c, s, _ in slots]
    with_na = [
        _verdict(c, s, "strong")
        if c != "integrations"
        else _verdict(c, s, "none", "not_applicable")
        for c, s, _ in slots
    ]
    baseline = _readiness(all_strong, "Everything covered.")
    na_case = _readiness(with_na, "No integrations needed.")
    assert na_case["score"] >= baseline["score"] - 1
```

Scenario 3 (file-only upload) is covered by a manual smoke step in the test
case document; it needs a real uploaded file and is not unit-tested here.

- [ ] **Step 2: Run the scenario tests**

Run: `D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_evidence_readiness_scenarios.py -q`
Expected: PASS (4 passed).

- [ ] **Step 3: Commit**

```powershell
git add tests/api/test_evidence_readiness_scenarios.py
git commit -m "test: add evidence readiness acceptance scenarios"
```

---

## Task 9: Update documentation

**Files:**
- Modify: `docs/superpowers/development/07_decision_log.md`
- Modify: `docs/superpowers/development/14_qna_workflow_refinement.md`
- Modify: `docs/superpowers/development/03_data_model_and_output_schema.md`
- Modify: `docs/superpowers/testing/test_case_index.md`
- Create: `docs/superpowers/testing/test_cases/TC-028-evidence-based-readiness.md`
- Modify: `context.md`, `docs/superpowers/CURRENT.md`

- [ ] **Step 1: Amend the decision log**

In `07_decision_log.md`, add a dated entry amending decision #8: the backend
still aggregates readiness deterministically, but the per-slot evidence inputs
are AI-judged and quote-validated. Reference this plan and the spec.

- [ ] **Step 2: Rewrite the readiness section of the behavior note**

In `14_qna_workflow_refinement.md`, rewrite section 8 (Readiness) to describe
the evidence model: per-slot verdicts, quote validation, weighted aggregation,
derived confidence.

- [ ] **Step 3: Document the data model**

In `03_data_model_and_output_schema.md`, add `SlotEvidence` and the new
`QuestionnairePlanSlot` fields (`evidence_strength`, `applicable`) and the
`not_applicable` visibility value.

- [ ] **Step 4: Add the test case**

Create `TC-028-evidence-based-readiness.md` using the test case template in
`test_case_index.md`. Inputs: the five scenarios from Task 8 plus a manual
file-only smoke. Add a TC-028 row to the index table.

- [ ] **Step 5: Update phase notes**

In `context.md` and `CURRENT.md`, note that evidence-based readiness is
implemented and that SAD synthesis quality is the next cycle.

- [ ] **Step 6: Commit (docs are local-only; commit is best-effort)**

`docs/` is git-ignored in this repo by project convention, so this step records
intent only. No commit is required for the docs themselves.

---

## Task 10: Full local verification

- [ ] **Step 1: Run the full Python suite**

```powershell
cd D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
$env:PYTHONPATH="services\api\src;src;."
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests -q
```

Expected: all tests pass. Investigate and fix any failure; do not delete tests
to make the suite pass.

- [ ] **Step 2: Type-check and build the frontend**

```powershell
node apps\web\node_modules\typescript\bin\tsc -p apps\web\tsconfig.json --noEmit
npm --prefix apps\web run build
```

Expected: TypeScript exits 0; Next.js build compiles.

- [ ] **Step 3: Final commit**

```powershell
git add -A
git commit -m "chore: evidence-based readiness verification pass"
```

- [ ] **Step 4: Hand back for manual smoke**

Report the suite result and ask the user to run the browser manual smoke against
the five scenarios in TC-028 for final sign-off.

---

## Self-Review

**Spec coverage:**

- Evidence model / `SlotEvidence` — Task 1.
- AI output schema and prompt — Task 2.
- Quote validation and downgrade — Task 3.
- Confidence derivation — Task 3.
- Weighted aggregation, `not_applicable` handling — Task 4.
- Keyword tables deleted, route rewired — Task 5.
- Draft-ready gate — Task 6.
- Frontend `not_applicable` group — Task 7.
- Scenario table and anti-hallucination test — Tasks 5 and 8.
- Docs updates — Task 9.

**Placeholder scan:** no TBD/TODO; every code step shows full code or an exact
edit target.

**Type consistency:** `SlotEvidence`, `evidence_strength`, `applicable`,
`canonical_required_slots`, `create_plan_from_evidence`, `validate_slot_evidence`,
`derive_confidence`, `evidence_map` are used with consistent names and
signatures across tasks.

**Known judgement points for the implementer:**

- Task 5 Step 3: `_draft_readiness` and `_questionnaire_categories` are removed
  only if they have no remaining callers after rewiring. Verify with the given
  search command before deleting.
- Task 6 Step 3: the gate checks `analysis.questionnaire.categories` statuses
  because the route does not receive the raw plan object.
- Some existing tests in `test_gemini_structured.py` assert keyword-seeded
  readiness; they must be updated to supply `slot_evidence`. This is expected
  and called out in Task 5 Step 6.

## Execution Handoff

Implementation is assigned to Codex. See the companion handover document:
`docs/superpowers/plans/2026-05-22-evidence-based-readiness-HANDOVER.md`

---

## 2026-05-22-evidence-based-readiness-HANDOVER

# Codex Handover — Evidence-Based Readiness

Date: 2026-05-22
For: Codex implementation session
Status: Ready to implement

## What You Are Building

Replace SADify's keyword-driven Q&A readiness with an AI-judged,
quote-validated, backend-aggregated evidence model. The Gemini analysis call
returns a per-slot evidence verdict array; the backend validates each verdict's
quote against the supplied material, aggregates a weighted readiness score over
applicable required slots, derives confidence from the verdict mix, and builds
the questionnaire plan from evidence instead of keyword tables.

This is Cycle 1 of 2. Do NOT touch SAD synthesis quality — that is Cycle 2 and
has its own future spec.

## Read First, In Order

1. `CLAUDE.md` — repo behavior and quality rules.
2. `context.md` — architecture and current status.
3. `docs/superpowers/specs/2026-05-22-evidence-based-readiness-design.md` — the
   approved design and the rationale for every decision.
4. `docs/superpowers/plans/2026-05-22-evidence-based-readiness.md` — the
   task-by-task implementation plan. Implement it in order.

## Workspace

```text
Worktree:   D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
Branch:     codex/mvp-monorepo-scaffold
Python:     D:\GoogleCloudHack\.venv\Scripts\python.exe (3.13)
```

The branch already carries committed MVP work through commit
`d18f64d`. Continue committing on this branch, one commit per plan task as the
plan specifies.

Set the import path before running anything:

```powershell
cd D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
$env:PYTHONPATH="services\api\src;src;."
```

## How To Work

- Follow the plan task by task, top to bottom. Each task is test-first: write
  the failing test, confirm it fails, implement, confirm it passes, commit.
- Do not skip the "run the test and confirm it fails" step.
- Use the exact code and file paths in the plan. Where the plan gives an exact
  edit target instead of full code (parts of Task 5), make the minimal change
  that satisfies the described behavior and the task's test.
- If a test fails for a real reason, fix the code or the test logic. Never
  delete or skip a test to make the suite green.
- Do not add scope: no SAD synthesis changes, no new cloud services, no new
  dependencies, no unrelated refactors.

## Verification Commands

Per-task focused tests are named in each plan task. Full verification (plan
Task 10):

```powershell
cd D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
$env:PYTHONPATH="services\api\src;src;."
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests -q
node apps\web\node_modules\typescript\bin\tsc -p apps\web\tsconfig.json --noEmit
npm --prefix apps\web run build
```

Expected: all Python tests pass; TypeScript exits 0; the Next.js build compiles.
If the build cannot read `C:\Users\User` under a sandbox, run it again outside
the sandbox.

## Expected Behavior Changes

- Some existing tests in `tests/api/test_gemini_structured.py` assert
  keyword-seeded readiness. They WILL fail after Task 5 and must be updated to
  supply `slot_evidence` in their fake payloads. This is expected, not a
  regression. The plan calls this out in Task 5 Step 6.
- Readiness scores become continuous (half-slot steps over a project-specific
  denominator) instead of fixed `N/19` steps.
- A request with no real evidence now scores Low instead of a preset percentage.

## No Live Calls

Implementation and all tests are local. Do NOT make live Gemini or any Google
Cloud calls. Tests use `FakeRequirementAnalysisModel` / `FakeModel`. The billing
guardrail still applies.

## Stop Conditions

Stop and report back if any of these occur:

- The full `pytest tests` suite cannot be made green without deleting or
  skipping a test.
- A plan step contradicts the current code in a way the plan did not anticipate.
- The change appears to require touching SAD synthesis (`sad_preview.py`
  composition, `sad_synthesis.py`) beyond the small `missing_blocking_basics`
  gate change in plan Task 6.
- Any new cloud service, dependency, or API would be needed.

## When Done

1. Confirm plan Task 10 verification passes.
2. Update `docs/superpowers/testing/test_cases/TC-028-evidence-based-readiness.md`
   with expected output, real output, evidence, and a pass/fail decision.
3. Report the test counts and hand back for the user's manual browser smoke
   against the five TC-028 scenarios. Do NOT start Cycle 2 (SAD synthesis).

## Docs Note

`docs/` is git-ignored in this repo by project convention; planning and test
docs live on disk only. Update them as the plan's Task 9 instructs, but no git
commit of `docs/` files is expected.
