# SADify Layer 2 — Technical Model & Diagrams Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in "Layer 2" that extracts a structured technical model (entities, relationships, workflow states, permissions) from the confirmed SAD facts and renders ERD / state / permissions diagrams from it, without changing the existing Q&A → SAD → save → wiki flow.

**Architecture:** New, isolated backend units (`schemas.TechnicalModel`, `services/technical_model.py` extraction, `services/diagram_render.py` deterministic Mermaid) behind two new routes on the existing `/sad` router via the established Protocol-based model injection. Frontend adds one "Technical design" tab inside the existing `PreviewPane`, fed by the state the workspace already holds. Save reuses the existing Doc/wiki plumbing.

**Tech Stack:** Python 3.13 / FastAPI / Pydantic v2 / google-genai (Vertex Gemini); Next.js 16 / React 19 / TypeScript; mermaid.js (new frontend dep). Verification: `pytest` via `D:\GoogleCloudHack\.venv`, `tsc --noEmit`, `next build`, static UI tests.

**Worktree:** `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`, branch `codex/mvp-monorepo-scaffold`. Spec: `docs/superpowers/specs/2026-06-03-tc033-sadify-layer2-technical-model-design.md`.

**Test runner note:** run backend tests with `..\..\.venv\Scripts\python.exe -m pytest` from the worktree root (the bare `python` lacks deps). Frontend "tests" are Python static-file assertions under `tests/` (no JS runner).

---

## Non-Breaking Guardrails (apply to EVERY task)

- Do NOT modify existing fields on `SadPreviewResponse`, `SadPreviewRequest`, `SadSaveRequest`, or any existing route signature in a way that changes current behavior. New schemas/params are ADDITIVE and optional with defaults.
- After any backend task: `..\..\.venv\Scripts\python.exe -m pytest tests/ -q` must stay green (currently 471 passed, 4 skipped).
- After any frontend task: `cd apps/web && npx tsc --noEmit` clean and the static UI suite green.
- New DI params on `create_app` / `create_sad_router` MUST default to `None` and fall back to the Gemini impl, so all existing `create_app(...)` test call sites keep working unchanged.

---

## File Structure

Backend (`services/api/src/sadify_api/`):
- `schemas.py` — ADD `TechnicalModel` and sub-models + `TechnicalModelResponse`, `TechnicalModelRequest`, `TechnicalRenderRequest`. (modify, append-only)
- `services/diagram_render.py` — CREATE. Pure model→Mermaid/table strings.
- `services/technical_model.py` — CREATE. Context build + parse + fallback + confirmations.
- `services/gemini_structured.py` — ADD `TechnicalModelProvider` Protocol + `GeminiTechnicalModel`. (modify, append-only)
- `services/sad_preview.py` — MODIFY `_draft_ready_it_readiness` to accept an optional `has_technical_model` flag.
- `services/sad_save.py` / `services/wiki_compose.py` — MODIFY to carry the optional technical artifact/note.
- `routes/sad.py` — ADD `POST /sad/technical` and `POST /sad/technical/render`; ADD `technical_model` param to `create_sad_router`. (modify)
- `main.py` — ADD `technical_model` param to `create_app`, default `GeminiTechnicalModel`, pass into `create_sad_router`. (modify)

Frontend (`apps/web/src/`):
- `lib/api.ts` — ADD `TechnicalModel*` types + `generateTechnicalModel()` + `renderTechnicalModel()`. (modify)
- `lib/hooks/useTechnicalModel.ts` — CREATE.
- `components/preview/TechnicalDesignTab.tsx` (+ `.module.css`) — CREATE.
- `components/preview/PreviewPane.tsx` — MODIFY to host a tab switch (Document | Technical design).
- `components/WorkspaceV2.tsx` — MODIFY to pass the technical-model props.
- `package.json` — ADD `mermaid` dependency.

Tests (`tests/` and `tests/api/`):
- `tests/api/test_diagram_render.py`, `tests/api/test_technical_model.py`, `tests/api/test_technical_routes.py` — CREATE.
- `tests/test_mvp_layer2_ui.py` — CREATE (static UI assertions).

---

## Task 1: TechnicalModel schemas

**Files:**
- Modify: `services/api/src/sadify_api/schemas.py` (append after the SAD preview models)
- Test: `tests/api/test_technical_model.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/api/test_technical_model.py
from sadify_api.schemas import (
    TechnicalModel, TechnicalEntity, TechnicalField, TechnicalRelationship,
    TechnicalWorkflow, TechnicalState, TechnicalTransition, TechnicalActor,
    TechnicalPermission, TechnicalRule, TechnicalConfirmation,
)


def test_technical_model_minimal_defaults():
    model = TechnicalModel(
        entities=[
            TechnicalEntity(
                name="Appointment",
                description="A grooming booking.",
                fields=[
                    TechnicalField(name="appointment_id", type="string", key="pk",
                                   required=True, provenance="inferred",
                                   source_refs=["Data and records"]),
                ],
                provenance="stated", source_refs=["Data and records"],
            )
        ],
        relationships=[],
        workflow=TechnicalWorkflow(states=[], transitions=[]),
        actors=[], permissions=[], rules=[], confirmations=[],
    )
    assert model.entities[0].fields[0].key == "pk"
    assert model.workflow.states == []


def test_technical_field_rejects_bad_key():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        TechnicalField(name="x", type="string", key="primary",  # not in literal
                       required=True, provenance="stated", source_refs=[])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_technical_model.py -q`
Expected: FAIL — `ImportError: cannot import name 'TechnicalModel'`.

- [ ] **Step 3: Append the schema to `schemas.py`**

```python
# --- Layer 2: technical model (additive; does not touch SAD preview models) ---
class TechnicalField(ApiModel):
    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    key: Literal["pk", "fk", "none"]
    required: bool
    provenance: Literal["stated", "inferred"]
    source_refs: list[str] = Field(default_factory=list)


class TechnicalEntity(ApiModel):
    name: str = Field(min_length=1)
    description: str = ""
    fields: list[TechnicalField] = Field(default_factory=list)
    provenance: Literal["stated", "inferred"]
    source_refs: list[str] = Field(default_factory=list)


class TechnicalRelationship(ApiModel):
    from_entity: str = Field(min_length=1)
    to_entity: str = Field(min_length=1)
    cardinality: Literal["1-1", "1-many", "many-many"]
    label: str = ""
    provenance: Literal["stated", "inferred"]
    source_refs: list[str] = Field(default_factory=list)


class TechnicalState(ApiModel):
    name: str = Field(min_length=1)
    description: str = ""
    provenance: Literal["stated", "inferred"]
    source_refs: list[str] = Field(default_factory=list)


class TechnicalTransition(ApiModel):
    from_state: str = Field(min_length=1)
    to_state: str = Field(min_length=1)
    trigger: str = ""
    actor: str = ""
    condition: str = ""
    provenance: Literal["stated", "inferred"]
    source_refs: list[str] = Field(default_factory=list)


class TechnicalWorkflow(ApiModel):
    states: list[TechnicalState] = Field(default_factory=list)
    transitions: list[TechnicalTransition] = Field(default_factory=list)


class TechnicalActor(ApiModel):
    name: str = Field(min_length=1)
    type: Literal["frontline", "approver", "viewer", "external"]
    responsibilities: list[str] = Field(default_factory=list)
    provenance: Literal["stated", "inferred"]
    source_refs: list[str] = Field(default_factory=list)


class TechnicalPermission(ApiModel):
    actor: str = Field(min_length=1)
    action: str = Field(min_length=1)
    mode: Literal["allow", "requires_approval", "deny"]
    approver: str = ""
    provenance: Literal["stated", "inferred"]
    source_refs: list[str] = Field(default_factory=list)


class TechnicalRule(ApiModel):
    condition: str = Field(min_length=1)
    action: str = Field(min_length=1)
    approver: str = ""
    provenance: Literal["stated", "inferred"]
    source_refs: list[str] = Field(default_factory=list)


class TechnicalConfirmation(ApiModel):
    id: str = Field(min_length=1)
    target_kind: Literal[
        "relationship", "field_type", "entity_key", "state_set", "permission"
    ]
    target_ref: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    current_inference: str = ""
    options: list[str] = Field(default_factory=list)


class TechnicalModel(ApiModel):
    entities: list[TechnicalEntity] = Field(default_factory=list)
    relationships: list[TechnicalRelationship] = Field(default_factory=list)
    workflow: TechnicalWorkflow = Field(default_factory=TechnicalWorkflow)
    actors: list[TechnicalActor] = Field(default_factory=list)
    permissions: list[TechnicalPermission] = Field(default_factory=list)
    rules: list[TechnicalRule] = Field(default_factory=list)
    confirmations: list[TechnicalConfirmation] = Field(default_factory=list)


class TechnicalDiagrams(ApiModel):
    erd_mermaid: str = ""
    state_mermaid: str = ""
    permissions_markdown: str = ""


class TechnicalModelRequest(ApiModel):
    requirement_text: str = Field(min_length=5)
    analysis_id: str | None = None
    analysis: RequirementAnalysisResponse
    sad_sections: list[SadPreviewSection] = Field(default_factory=list)
    source_context: str | None = None
    source_references: list[str] = Field(default_factory=list)


class TechnicalRenderRequest(ApiModel):
    model: TechnicalModel


class TechnicalModelResponse(ApiModel):
    model: TechnicalModel
    diagrams: TechnicalDiagrams
    fallback_used: bool = False
```

Confirm `Literal` and `RequirementAnalysisResponse` are already imported in `schemas.py` (they are — used by existing models). If not, add `from typing import Literal`.

- [ ] **Step 4: Run test to verify it passes**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_technical_model.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Regression + commit**

```bash
..\..\.venv\Scripts\python.exe -m pytest tests/ -q   # expect 473 passed, 4 skipped
git add services/api/src/sadify_api/schemas.py tests/api/test_technical_model.py
git commit -m "feat(layer2): TechnicalModel schemas"
```

---

## Task 2: ERD renderer (deterministic)

**Files:**
- Create: `services/api/src/sadify_api/services/diagram_render.py`
- Test: `tests/api/test_diagram_render.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/api/test_diagram_render.py
from sadify_api.schemas import (
    TechnicalModel, TechnicalEntity, TechnicalField, TechnicalRelationship,
    TechnicalWorkflow,
)
from sadify_api.services.diagram_render import render_erd


def _model_with_two_entities():
    return TechnicalModel(
        entities=[
            TechnicalEntity(name="Owner", provenance="stated", source_refs=[],
                fields=[TechnicalField(name="owner_id", type="string", key="pk",
                        required=True, provenance="inferred", source_refs=[])]),
            TechnicalEntity(name="Pet", provenance="stated", source_refs=[],
                fields=[TechnicalField(name="pet_id", type="string", key="pk",
                        required=True, provenance="stated", source_refs=[])]),
        ],
        relationships=[TechnicalRelationship(from_entity="Owner", to_entity="Pet",
            cardinality="1-many", label="owns", provenance="inferred", source_refs=[])],
        workflow=TechnicalWorkflow(),
    )


def test_render_erd_emits_entities_and_crowsfoot():
    md = render_erd(_model_with_two_entities())
    assert md.startswith("erDiagram")
    assert "Owner {" in md and "Pet {" in md
    assert "string owner_id PK" in md
    assert 'Owner ||--o{ Pet : "owns (inferred)"' in md


def test_render_erd_empty_is_safe():
    md = render_erd(TechnicalModel(workflow=TechnicalWorkflow()))
    assert md.startswith("erDiagram")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_diagram_render.py -q`
Expected: FAIL — module not found.

- [ ] **Step 3: Create `diagram_render.py` (ERD only for now)**

```python
"""Pure, deterministic Mermaid/Markdown renderers for the Layer-2 model.

No model call. Each renderer takes a TechnicalModel and returns a string.
"""
from sadify_api.schemas import TechnicalModel

_CARD = {"1-1": "||--||", "1-many": "||--o{", "many-many": "}o--o{"}
_KEY = {"pk": " PK", "fk": " FK", "none": ""}


def _safe_token(name: str) -> str:
    token = "".join(ch if ch.isalnum() else "_" for ch in name.strip())
    return token or "Unnamed"


def render_erd(model: TechnicalModel) -> str:
    lines = ["erDiagram"]
    for entity in model.entities:
        lines.append(f"  {_safe_token(entity.name)} {{")
        for field in entity.fields:
            field_type = _safe_token(field.type)
            lines.append(f"    {field_type} {_safe_token(field.name)}{_KEY[field.key]}")
        lines.append("  }")
    for rel in model.relationships:
        symbol = _CARD[rel.cardinality]
        label = rel.label or "relates"
        if rel.provenance == "inferred":
            label = f"{label} (inferred)"
        lines.append(
            f'  {_safe_token(rel.from_entity)} {symbol} '
            f'{_safe_token(rel.to_entity)} : "{label}"'
        )
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_diagram_render.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add services/api/src/sadify_api/services/diagram_render.py tests/api/test_diagram_render.py
git commit -m "feat(layer2): deterministic ERD renderer"
```

---

## Task 3: State-diagram renderer

**Files:**
- Modify: `services/api/src/sadify_api/services/diagram_render.py`
- Test: `tests/api/test_diagram_render.py`

- [ ] **Step 1: Add the failing test**

```python
from sadify_api.schemas import TechnicalState, TechnicalTransition
from sadify_api.services.diagram_render import render_state


def test_render_state_emits_transitions_with_trigger_actor():
    model = TechnicalModel(workflow=TechnicalWorkflow(
        states=[TechnicalState(name="Booked", provenance="stated", source_refs=[]),
                TechnicalState(name="Checked In", provenance="stated", source_refs=[])],
        transitions=[TechnicalTransition(from_state="Booked", to_state="Checked In",
            trigger="pet arrives", actor="Reception", condition="",
            provenance="stated", source_refs=[])],
    ))
    md = render_state(model)
    assert md.startswith("stateDiagram-v2")
    assert "Booked --> Checked_In : pet arrives [Reception]" in md


def test_render_state_empty_is_safe():
    md = render_state(TechnicalModel(workflow=TechnicalWorkflow()))
    assert md.startswith("stateDiagram-v2")
```

- [ ] **Step 2: Run to verify it fails**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_diagram_render.py -k state -q`
Expected: FAIL — `render_state` undefined.

- [ ] **Step 3: Append `render_state` to `diagram_render.py`**

```python
def render_state(model: TechnicalModel) -> str:
    lines = ["stateDiagram-v2"]
    for state in model.workflow.states:
        lines.append(f"  state \"{state.name}\" as {_safe_token(state.name)}")
    for tr in model.workflow.transitions:
        parts = []
        if tr.trigger:
            parts.append(tr.trigger)
        if tr.actor:
            parts.append(f"[{tr.actor}]")
        label = " ".join(parts)
        suffix = f" : {label}" if label else ""
        lines.append(
            f"  {_safe_token(tr.from_state)} --> {_safe_token(tr.to_state)}{suffix}"
        )
    return "\n".join(lines)
```

- [ ] **Step 4: Run to verify it passes**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_diagram_render.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/api/src/sadify_api/services/diagram_render.py tests/api/test_diagram_render.py
git commit -m "feat(layer2): state-diagram renderer"
```

---

## Task 4: Permissions-matrix renderer

**Files:**
- Modify: `services/api/src/sadify_api/services/diagram_render.py`
- Test: `tests/api/test_diagram_render.py`

- [ ] **Step 1: Add the failing test**

```python
from sadify_api.schemas import TechnicalActor, TechnicalPermission
from sadify_api.services.diagram_render import render_permissions


def test_render_permissions_matrix_cells():
    model = TechnicalModel(
        actors=[TechnicalActor(name="Manager", type="approver", provenance="stated", source_refs=[]),
                TechnicalActor(name="Groomer", type="frontline", provenance="stated", source_refs=[])],
        permissions=[
            TechnicalPermission(actor="Manager", action="Approve refund", mode="allow",
                                provenance="stated", source_refs=[]),
            TechnicalPermission(actor="Groomer", action="Approve refund", mode="deny",
                                provenance="stated", source_refs=[]),
        ],
        workflow=TechnicalWorkflow(),
    )
    md = render_permissions(model)
    assert "| Action | Manager | Groomer |" in md
    assert "| Approve refund | allow | deny |" in md
```

- [ ] **Step 2: Run to verify it fails**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_diagram_render.py -k permissions -q`
Expected: FAIL.

- [ ] **Step 3: Append `render_permissions`**

```python
def render_permissions(model: TechnicalModel) -> str:
    actors = [a.name for a in model.actors]
    actions: list[str] = []
    for perm in model.permissions:
        if perm.action not in actions:
            actions.append(perm.action)
    if not actors or not actions:
        return "_No permission matrix derived._"
    cell: dict[tuple[str, str], str] = {}
    for perm in model.permissions:
        text = perm.mode
        if perm.mode == "requires_approval" and perm.approver:
            text = f"approval: {perm.approver}"
        cell[(perm.action, perm.actor)] = text
    header = "| Action | " + " | ".join(actors) + " |"
    divider = "| --- | " + " | ".join("---" for _ in actors) + " |"
    rows = [header, divider]
    for action in actions:
        cells = [cell.get((action, actor), "-") for actor in actors]
        rows.append(f"| {action} | " + " | ".join(cells) + " |")
    return "\n".join(rows)


def render_all(model: TechnicalModel):
    from sadify_api.schemas import TechnicalDiagrams
    return TechnicalDiagrams(
        erd_mermaid=render_erd(model),
        state_mermaid=render_state(model),
        permissions_markdown=render_permissions(model),
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_diagram_render.py -q`
Expected: PASS (all render tests).

- [ ] **Step 5: Commit**

```bash
git add services/api/src/sadify_api/services/diagram_render.py tests/api/test_diagram_render.py
git commit -m "feat(layer2): permissions-matrix renderer + render_all"
```

---

## Task 5: Confirmations derivation from inferred elements

**Files:**
- Create: `services/api/src/sadify_api/services/technical_model.py`
- Test: `tests/api/test_technical_model.py`

- [ ] **Step 1: Add the failing test**

```python
from sadify_api.services.technical_model import derive_confirmations


def test_derive_confirmations_flags_inferred_relationship_and_field_type():
    from sadify_api.schemas import (
        TechnicalModel, TechnicalEntity, TechnicalField, TechnicalRelationship,
        TechnicalWorkflow,
    )
    model = TechnicalModel(
        entities=[TechnicalEntity(name="Pet", provenance="stated", source_refs=[],
            fields=[TechnicalField(name="size", type="enum", key="none",
                required=False, provenance="inferred", source_refs=[])])],
        relationships=[TechnicalRelationship(from_entity="Owner", to_entity="Pet",
            cardinality="1-many", label="owns", provenance="inferred", source_refs=[])],
        workflow=TechnicalWorkflow(),
    )
    confs = derive_confirmations(model)
    kinds = {c.target_kind for c in confs}
    assert "relationship" in kinds
    assert "field_type" in kinds
    assert all(c.id and c.statement for c in confs)
```

- [ ] **Step 2: Run to verify it fails**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_technical_model.py -k confirmations -q`
Expected: FAIL — module/function missing.

- [ ] **Step 3: Create `technical_model.py` with `derive_confirmations`**

```python
"""Layer-2 extraction support: context build, parse, fallback, confirmations.

The Gemini call itself is injected via a TechnicalModelProvider (see
gemini_structured.py). This module is deterministic and unit-testable.
"""
from sadify_api.schemas import (
    TechnicalConfirmation, TechnicalModel,
)


def derive_confirmations(model: TechnicalModel) -> list[TechnicalConfirmation]:
    out: list[TechnicalConfirmation] = []
    counter = 0

    def _next_id() -> str:
        nonlocal counter
        counter += 1
        return f"TC-CONF-{counter:03d}"

    for rel in model.relationships:
        if rel.provenance == "inferred":
            out.append(TechnicalConfirmation(
                id=_next_id(), target_kind="relationship",
                target_ref=f"{rel.from_entity}->{rel.to_entity}",
                statement=(f"Inferred: {rel.from_entity} {rel.cardinality} "
                           f"{rel.to_entity} ({rel.label or 'relates'}). Correct?"),
                current_inference=rel.cardinality,
                options=["1-1", "1-many", "many-many"],
            ))
    for entity in model.entities:
        for field in entity.fields:
            if field.provenance == "inferred":
                out.append(TechnicalConfirmation(
                    id=_next_id(), target_kind="field_type",
                    target_ref=f"{entity.name}.{field.name}",
                    statement=(f"Inferred type for {entity.name}.{field.name} "
                               f"= {field.type}. Correct?"),
                    current_inference=field.type, options=[],
                ))
                if field.key != "none":
                    out.append(TechnicalConfirmation(
                        id=_next_id(), target_kind="entity_key",
                        target_ref=f"{entity.name}.{field.name}",
                        statement=(f"Inferred {field.key.upper()} on "
                                   f"{entity.name}.{field.name}. Correct?"),
                        current_inference=field.key, options=["pk", "fk", "none"],
                    ))
    return out
```

- [ ] **Step 4: Run to verify it passes**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_technical_model.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/api/src/sadify_api/services/technical_model.py tests/api/test_technical_model.py
git commit -m "feat(layer2): derive confirmations from inferred elements"
```

---

## Task 6: Context builder, parse, and safe fallback

**Files:**
- Modify: `services/api/src/sadify_api/services/technical_model.py`
- Test: `tests/api/test_technical_model.py`

- [ ] **Step 1: Add failing tests**

```python
import json
from sadify_api.services.technical_model import (
    build_technical_context, parse_technical_model, build_safe_fallback_model,
)
from sadify_api.schemas import (
    RequirementAnalysisResponse, SadPreviewSection,
)


def _analysis():
    return RequirementAnalysisResponse(
        understanding_summary="A pet grooming shop wants appointment tracking.",
        readiness={"label": "Ready for draft", "score": 100, "confidence": "High"},
        categories=[{"id": "data_records", "label": "Data", "status": "complete"}],
        next_question={"text": "?", "why_this_matters": "x",
                       "choices": [{"id": "a", "label": "a"}, {"id": "b", "label": "b"}],
                       "target_category": "data_records", "target_slot_id": "fields"},
        assumptions=[], source_references=[],
    )


def test_build_context_includes_sections_and_summary():
    ctx = build_technical_context(
        requirement_text="track grooming appointments",
        analysis=_analysis(),
        sad_sections=[SadPreviewSection(title="Data and records",
            body="pet name, owner contact, payment amount", source_references=["SRC-000001"])],
        source_context="raw source", source_references=["SRC-000001"],
    )
    assert "Data and records" in ctx
    assert "pet grooming shop" in ctx


def test_parse_valid_model_json():
    payload = {"entities": [], "relationships": [],
               "workflow": {"states": [], "transitions": []},
               "actors": [], "permissions": [], "rules": [], "confirmations": []}
    model = parse_technical_model(json.dumps(payload))
    assert model.entities == []


def test_fallback_model_marks_everything_inferred():
    model = build_safe_fallback_model(
        analysis=_analysis(),
        sad_sections=[SadPreviewSection(title="Users and roles",
            body="reception staff, groomers, manager", source_references=["SRC-000001"])],
    )
    assert model.actors  # derived deterministically
    assert all(a.provenance == "inferred" for a in model.actors)
```

- [ ] **Step 2: Run to verify it fails**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_technical_model.py -q`
Expected: FAIL — functions undefined.

- [ ] **Step 3: Append to `technical_model.py`**

```python
import json

from pydantic import ValidationError

from sadify_api.schemas import (
    RequirementAnalysisResponse, SadPreviewSection, TechnicalActor,
    TechnicalModel, TechnicalWorkflow,
)

_INSTRUCTION = (
    "You are SADify's technical-design extractor. From the confirmed SAD "
    "sections, Q&A answers, and source, output ONLY JSON matching the "
    "TechnicalModel schema (entities[], relationships[], workflow{states,"
    "transitions}, actors[], permissions[], rules[]). For every element set "
    "provenance to 'stated' only when a quote/answer supports it, else "
    "'inferred'. Infer reasonable field types, keys, and relationship "
    "cardinalities, but mark them 'inferred'. Do not invent facts absent from "
    "the inputs. Do not include the 'confirmations' field; the backend derives it."
)


def build_technical_context(
    *, requirement_text: str, analysis: RequirementAnalysisResponse,
    sad_sections: list[SadPreviewSection], source_context: str | None,
    source_references: list[str],
) -> str:
    parts = [_INSTRUCTION, "", f"# Business request\n{requirement_text}", ""]
    parts.append(f"# Understanding summary\n{analysis.understanding_summary}")
    if analysis.questionnaire and analysis.questionnaire.answers:
        parts.append("\n# Confirmed answers")
        for ans in analysis.questionnaire.answers:
            parts.append(f"- ({ans.category_id}/{ans.slot_id or '-'}) "
                         f"{ans.question} => {ans.answer}")
    parts.append("\n# Confirmed SAD sections")
    for section in sad_sections:
        refs = ", ".join(section.source_references) or "-"
        parts.append(f"## {section.title} [refs: {refs}]\n{section.body}")
    if source_context:
        parts.append(f"\n# Source extract\n{source_context}")
    if source_references:
        parts.append(f"\n# Source ids\n{', '.join(source_references)}")
    return "\n".join(parts)


def parse_technical_model(raw_json: str) -> TechnicalModel:
    data = json.loads(raw_json)
    data.pop("confirmations", None)  # backend owns confirmations
    return TechnicalModel.model_validate(data)


def build_safe_fallback_model(
    *, analysis: RequirementAnalysisResponse,
    sad_sections: list[SadPreviewSection],
) -> TechnicalModel:
    """Deterministic minimal model when Gemini output is unusable.

    Derives actors from the 'Users and roles' section text and leaves the rest
    empty; everything is 'inferred' so the confirm panel makes the limits clear.
    """
    actors: list[TechnicalActor] = []
    seen: set[str] = set()
    role_terms = ["reception", "groomer", "manager", "owner", "staff", "admin"]
    for section in sad_sections:
        if "user" in section.title.lower() or "actor" in section.title.lower():
            for term in role_terms:
                if term in section.body.lower() and term not in seen:
                    seen.add(term)
                    actors.append(TechnicalActor(
                        name=term.capitalize(),
                        type="approver" if term == "manager" else "frontline",
                        responsibilities=[], provenance="inferred",
                        source_refs=section.source_references,
                    ))
    return TechnicalModel(
        entities=[], relationships=[], workflow=TechnicalWorkflow(),
        actors=actors, permissions=[], rules=[], confirmations=[],
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_technical_model.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/api/src/sadify_api/services/technical_model.py tests/api/test_technical_model.py
git commit -m "feat(layer2): context builder, parse, safe fallback"
```

---

## Task 7: Gemini provider Protocol + impl + DI wiring

**Files:**
- Modify: `services/api/src/sadify_api/services/gemini_structured.py` (append a Protocol + Gemini impl mirroring `GeminiSadPreviewModel`)
- Modify: `services/api/src/sadify_api/main.py`
- Modify: `services/api/src/sadify_api/routes/sad.py` (add param to `create_sad_router`, default not required here)
- Test: `tests/api/test_technical_routes.py`

- [ ] **Step 1: Write the failing route-wiring test (fake model)**

```python
# tests/api/test_technical_routes.py
import json
from fastapi.testclient import TestClient
from sadify_api.main import create_app
from sadify_api.services.analysis_state import RequirementAnalysisRepository

_VALID_MODEL = {
    "entities": [{"name": "Appointment", "description": "", "provenance": "stated",
                  "source_refs": ["Data and records"],
                  "fields": [{"name": "appointment_id", "type": "string", "key": "pk",
                              "required": True, "provenance": "inferred", "source_refs": []}]}],
    "relationships": [], "workflow": {"states": [], "transitions": []},
    "actors": [], "permissions": [], "rules": [],
}


class FakeTechnicalModel:
    def generate_technical_model(self, context, *, repair=False):
        return json.dumps(_VALID_MODEL)


def _client():
    return TestClient(create_app(
        analysis_repository=RequirementAnalysisRepository(),
        technical_model=FakeTechnicalModel(),
    ))


def _ready_analysis():
    return {
        "understanding_summary": "Pet grooming appointment tracking.",
        "readiness": {"label": "Ready for draft", "score": 100, "confidence": "High"},
        "categories": [{"id": "data_records", "label": "Data", "status": "complete"}],
        "next_question": {"text": "?", "why_this_matters": "x",
            "choices": [{"id": "a", "label": "a"}, {"id": "b", "label": "b"}],
            "target_category": "data_records", "target_slot_id": "fields"},
        "assumptions": [], "source_references": [],
    }


def test_technical_route_returns_model_and_diagrams():
    resp = _client().post("/sad/technical", json={
        "requirement_text": "track grooming appointments",
        "analysis": _ready_analysis(),
        "sad_sections": [{"title": "Data and records", "body": "pet name, owner",
                          "source_references": ["SRC-000001"]}],
        "source_references": ["SRC-000001"],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["model"]["entities"][0]["name"] == "Appointment"
    assert body["diagrams"]["erd_mermaid"].startswith("erDiagram")
```

- [ ] **Step 2: Run to verify it fails**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_technical_routes.py -q`
Expected: FAIL — `create_app() got an unexpected keyword argument 'technical_model'`.

- [ ] **Step 3a: Append Protocol + Gemini impl to `gemini_structured.py`**

```python
class TechnicalModelProvider(Protocol):
    def generate_technical_model(self, context: str, *, repair: bool = False) -> str:
        ...


class GeminiTechnicalModel:
    def __init__(self, config):
        self._config = config

    def generate_technical_model(self, context: str, *, repair: bool = False) -> str:
        from google import genai
        from google.genai.types import HttpOptions

        client = genai.Client(
            vertexai=self._config.google_genai_use_vertexai,
            project=self._config.google_cloud_project,
            location=self._config.google_cloud_location,
            http_options=HttpOptions(api_version="v1"),
        )
        prompt = context if not repair else (
            context + "\n\nYour previous output was not valid JSON. "
            "Return ONLY the JSON object, no prose."
        )
        response = client.models.generate_content(
            model=self._config.sadify_model,
            contents=prompt,
            config={"temperature": 0.2, "max_output_tokens": 8000,
                    "response_mime_type": "application/json"},
        )
        return response.text or ""
```

(`Protocol` is already imported at the top of this file — it defines the existing Protocols.)

- [ ] **Step 3b: Wire `create_sad_router` (`routes/sad.py`)** — add the param (defaulted) near the other model params:

```python
def create_sad_router(
    model: SadPreviewModel,
    repository: SadPreviewRepository,
    token_verifier: TokenVerifier,
    drive_repo_repository: DriveRepoRepository,
    source_repository: SourceRepository,
    sad_save_repository: SadSaveRepository,
    config: ApiConfig | None = None,
    drive_client: DriveClient | None = None,
    secret_store: SecretStore | None = None,
    wiki_state_repository: WikiStateRepository | None = None,
    project_repository: ProjectRepository | None = None,
    technical_model: "TechnicalModelProvider | None" = None,
) -> APIRouter:
```

Add the import at the top of `routes/sad.py`:
```python
from sadify_api.services.gemini_structured import TechnicalModelProvider
```

- [ ] **Step 3c: Wire `create_app` (`main.py`)** — add the param + default + pass-through:

```python
# in the create_app signature, near sad_preview_model:
    technical_model: TechnicalModelProvider | None = None,
# after sad_preview_model default:
    technical_model = technical_model or GeminiTechnicalModel(config)
# in the create_sad_router(...) call, add:
        technical_model=technical_model,
```

Add imports in `main.py`:
```python
from sadify_api.services.gemini_structured import (
    GeminiTechnicalModel, TechnicalModelProvider,
)
```

(The `/sad/technical` route itself is added in Task 8; this task only wires the dependency so existing call sites still pass. The route test will still fail until Task 8 — that's expected; this task's deliverable is the wiring compiling and the FULL existing suite staying green.)

- [ ] **Step 4: Verify wiring compiles + no regression**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/ -q`
Expected: existing suite green; `test_technical_routes.py` may still FAIL (route added next task) — that is acceptable for this task.

- [ ] **Step 5: Commit**

```bash
git add services/api/src/sadify_api/services/gemini_structured.py services/api/src/sadify_api/main.py services/api/src/sadify_api/routes/sad.py
git commit -m "feat(layer2): technical-model provider Protocol + DI wiring"
```

---

## Task 8: `POST /sad/technical` route (repair→fallback)

**Files:**
- Modify: `services/api/src/sadify_api/routes/sad.py`
- Test: `tests/api/test_technical_routes.py`

- [ ] **Step 1: Add failing tests (gating + fallback)**

```python
def test_technical_route_409_when_not_ready():
    analysis = _ready_analysis()
    analysis["readiness"] = {"label": "Mostly ready", "score": 70, "confidence": "Medium"}
    resp = _client().post("/sad/technical", json={
        "requirement_text": "track grooming appointments",
        "analysis": analysis, "sad_sections": [], "source_references": []})
    assert resp.status_code == 409


class FakeBadModel:
    def generate_technical_model(self, context, *, repair=False):
        return "not json"


def test_technical_route_falls_back_safely():
    client = TestClient(create_app(
        analysis_repository=RequirementAnalysisRepository(),
        technical_model=FakeBadModel()))
    resp = client.post("/sad/technical", json={
        "requirement_text": "track grooming appointments",
        "analysis": _ready_analysis(),
        "sad_sections": [{"title": "Users and roles", "body": "reception, groomers, manager",
                          "source_references": ["SRC-000001"]}],
        "source_references": ["SRC-000001"]})
    assert resp.status_code == 200
    assert resp.json()["fallback_used"] is True
```

- [ ] **Step 2: Run to verify it fails**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_technical_routes.py -q`
Expected: FAIL — route 404 / not present.

- [ ] **Step 3: Add the route inside `create_sad_router` (after the `/preview` route)**

```python
    @router.post("/technical", response_model=TechnicalModelResponse)
    def generate_technical(request: TechnicalModelRequest) -> TechnicalModelResponse:
        readiness = request.analysis.readiness
        if readiness.score < 90:
            raise HTTPException(
                status_code=409,
                detail={"message": "Generate the SAD draft (90%+) before the technical design.",
                        "code": "TECHNICAL_NOT_READY"},
            )
        if technical_model is None:
            raise HTTPException(status_code=503, detail="Technical model unavailable.")
        context = build_technical_context(
            requirement_text=request.requirement_text,
            analysis=request.analysis,
            sad_sections=request.sad_sections,
            source_context=request.source_context,
            source_references=request.source_references,
        )
        for repair in (False, True):
            raw = ""
            try:
                raw = technical_model.generate_technical_model(context, repair=repair)
                model_obj = parse_technical_model(raw)
            except (ValueError, ValidationError, json.JSONDecodeError):
                logger.warning("sadify_technical parse_failed repair=%s len=%d", repair, len(raw))
                continue
            except Exception as exc:
                logger.exception("sadify_technical call_failed repair=%s", repair)
                raise HTTPException(status_code=502, detail="Gemini technical model failed.") from exc
            model_obj = model_obj.model_copy(update={"confirmations": derive_confirmations(model_obj)})
            return TechnicalModelResponse(
                model=model_obj, diagrams=render_all(model_obj), fallback_used=False)
        fallback = build_safe_fallback_model(
            analysis=request.analysis, sad_sections=request.sad_sections)
        fallback = fallback.model_copy(update={"confirmations": derive_confirmations(fallback)})
        return TechnicalModelResponse(
            model=fallback, diagrams=render_all(fallback), fallback_used=True)
```

Add imports at the top of `routes/sad.py`:
```python
import json
from pydantic import ValidationError
from sadify_api.schemas import (
    TechnicalModelRequest, TechnicalModelResponse, TechnicalRenderRequest,
)
from sadify_api.services.technical_model import (
    build_safe_fallback_model, build_technical_context, derive_confirmations,
    parse_technical_model,
)
from sadify_api.services.diagram_render import render_all
```

(Some of these — `json`, `ValidationError` — may already be imported; do not duplicate.)

- [ ] **Step 4: Run to verify it passes**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_technical_routes.py -q`
Expected: PASS (all technical-route tests).

- [ ] **Step 5: Regression + commit**

```bash
..\..\.venv\Scripts\python.exe -m pytest tests/ -q   # full suite green
git add services/api/src/sadify_api/routes/sad.py tests/api/test_technical_routes.py
git commit -m "feat(layer2): POST /sad/technical with repair->fallback"
```

---

## Task 9: `POST /sad/technical/render` (confirm-loop re-render)

**Files:**
- Modify: `services/api/src/sadify_api/routes/sad.py`
- Test: `tests/api/test_technical_routes.py`

- [ ] **Step 1: Add the failing test**

```python
def test_technical_render_route_is_deterministic_no_model():
    resp = _client().post("/sad/technical/render", json={"model": _VALID_MODEL})
    assert resp.status_code == 200
    assert resp.json()["erd_mermaid"].startswith("erDiagram")
```

- [ ] **Step 2: Run to verify it fails**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_technical_routes.py -k render -q`
Expected: FAIL — route 404.

- [ ] **Step 3: Add the render route (after `/technical`)**

```python
    @router.post("/technical/render", response_model=TechnicalDiagrams)
    def render_technical(request: TechnicalRenderRequest) -> TechnicalDiagrams:
        return render_all(request.model)
```

Add `TechnicalDiagrams` to the schema import line in `routes/sad.py`.

- [ ] **Step 4: Run to verify it passes**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_technical_routes.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/api/src/sadify_api/routes/sad.py tests/api/test_technical_routes.py
git commit -m "feat(layer2): POST /sad/technical/render for confirm-loop edits"
```

---

## Task 10: Flip the it_readiness Layer-2 stub when a model exists

**Files:**
- Modify: `services/api/src/sadify_api/services/sad_preview.py` (`_draft_ready_it_readiness`)
- Test: `tests/api/test_sad_preview.py`

- [ ] **Step 1: Add the failing test**

```python
def test_it_readiness_layer2_reflects_technical_model_flag():
    from sadify_api.services.sad_preview import _draft_ready_it_readiness
    analysis = _draft_ready_analysis()  # existing helper in this test module
    without = _draft_ready_it_readiness(analysis)
    with_model = _draft_ready_it_readiness(analysis, has_technical_model=True)
    l2_without = next(c for c in without.checklist if c.id == "layer_two_review")
    l2_with = next(c for c in with_model.checklist if c.id == "layer_two_review")
    assert l2_without.status == "needs_input"
    assert l2_with.status == "ready"
```

(If `_draft_ready_analysis` isn't present in `test_sad_preview.py`, construct a ready `RequirementAnalysisResponse` inline as in Task 6.)

- [ ] **Step 2: Run to verify it fails**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_sad_preview.py -k layer2 -q`
Expected: FAIL — unexpected keyword `has_technical_model`.

- [ ] **Step 3: Make the flag optional (default preserves current behavior)**

In `sad_preview.py`, change the signature and the `layer_two_review` item:

```python
def _draft_ready_it_readiness(
    analysis: RequirementAnalysisResponse,
    *, has_technical_model: bool = False,
) -> ItReadinessSummary:
    is_ready = _is_draft_ready(analysis)
    ...
            {
                "id": "layer_two_review",
                "label": "Later implementation review",
                "status": "ready" if has_technical_model else "needs_input",
                "reason": (
                    "Technical model and diagrams generated (Layer 2)."
                    if has_technical_model
                    else "Detailed technical design remains a later MVP refinement step."
                ),
            },
```

The default `False` keeps every existing caller and test byte-identical.

- [ ] **Step 4: Run to verify it passes + regression**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_sad_preview.py -q`
Expected: PASS, existing preview tests unchanged.

- [ ] **Step 5: Commit**

```bash
git add services/api/src/sadify_api/services/sad_preview.py tests/api/test_sad_preview.py
git commit -m "feat(layer2): it_readiness Layer-2 status reflects technical model"
```

---

## Task 11: Frontend API types + functions

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Test: `tests/test_mvp_layer2_ui.py`

- [ ] **Step 1: Write the failing static test**

```python
# tests/test_mvp_layer2_ui.py
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web" / "src"


def test_api_exposes_technical_model_contract():
    api = (WEB / "lib" / "api.ts").read_text(encoding="utf-8")
    assert "export type TechnicalModel" in api
    assert "export type TechnicalModelResponse" in api
    assert "export type TechnicalDiagrams" in api
    assert "export async function generateTechnicalModel" in api
    assert "export async function renderTechnicalModel" in api
    assert "/sad/technical" in api
    assert "/sad/technical/render" in api
```

- [ ] **Step 2: Run to verify it fails**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/test_mvp_layer2_ui.py -q`
Expected: FAIL.

- [ ] **Step 3: Append types + functions to `api.ts`** (mirror the `SadPreviewResponse` / `generateSadPreview` shapes already in the file)

```typescript
export type TechnicalField = {
  name: string; type: string; key: "pk" | "fk" | "none";
  required: boolean; provenance: "stated" | "inferred"; source_refs: string[];
};
export type TechnicalEntity = {
  name: string; description: string; fields: TechnicalField[];
  provenance: "stated" | "inferred"; source_refs: string[];
};
export type TechnicalRelationship = {
  from_entity: string; to_entity: string;
  cardinality: "1-1" | "1-many" | "many-many"; label: string;
  provenance: "stated" | "inferred"; source_refs: string[];
};
export type TechnicalState = { name: string; description: string; provenance: "stated" | "inferred"; source_refs: string[] };
export type TechnicalTransition = {
  from_state: string; to_state: string; trigger: string; actor: string;
  condition: string; provenance: "stated" | "inferred"; source_refs: string[];
};
export type TechnicalWorkflow = { states: TechnicalState[]; transitions: TechnicalTransition[] };
export type TechnicalActor = {
  name: string; type: "frontline" | "approver" | "viewer" | "external";
  responsibilities: string[]; provenance: "stated" | "inferred"; source_refs: string[];
};
export type TechnicalPermission = {
  actor: string; action: string; mode: "allow" | "requires_approval" | "deny";
  approver: string; provenance: "stated" | "inferred"; source_refs: string[];
};
export type TechnicalRule = {
  condition: string; action: string; approver: string;
  provenance: "stated" | "inferred"; source_refs: string[];
};
export type TechnicalConfirmation = {
  id: string;
  target_kind: "relationship" | "field_type" | "entity_key" | "state_set" | "permission";
  target_ref: string; statement: string; current_inference: string; options: string[];
};
export type TechnicalModel = {
  entities: TechnicalEntity[]; relationships: TechnicalRelationship[];
  workflow: TechnicalWorkflow; actors: TechnicalActor[];
  permissions: TechnicalPermission[]; rules: TechnicalRule[];
  confirmations: TechnicalConfirmation[];
};
export type TechnicalDiagrams = {
  erd_mermaid: string; state_mermaid: string; permissions_markdown: string;
};
export type TechnicalModelResponse = {
  model: TechnicalModel; diagrams: TechnicalDiagrams; fallback_used: boolean;
};

export async function generateTechnicalModel(input: {
  idToken?: string; requirementText: string; analysis: RequirementAnalysis;
  analysisId?: string | null; sadSections: SadPreviewResponse["sections"];
  sourceContext?: string | null; sourceReferences: string[];
}): Promise<TechnicalModelResponse> {
  const response = await fetch(`${baseUrl}/sad/technical`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      requirement_text: input.requirementText, analysis: input.analysis,
      analysis_id: input.analysisId ?? null, sad_sections: input.sadSections,
      source_context: input.sourceContext ?? null,
      source_references: input.sourceReferences,
    }),
  });
  if (!response.ok) throw await readBackendError(response);
  return (await response.json()) as TechnicalModelResponse;
}

export async function renderTechnicalModel(model: TechnicalModel): Promise<TechnicalDiagrams> {
  const response = await fetch(`${baseUrl}/sad/technical/render`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model }),
  });
  if (!response.ok) throw await readBackendError(response);
  return (await response.json()) as TechnicalDiagrams;
}
```

(Verify `readBackendError`, `RequirementAnalysis`, `SadPreviewResponse` are already exported in `api.ts` — they are.)

- [ ] **Step 4: Run static test + typecheck**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/test_mvp_layer2_ui.py -q` → PASS
Run: `cd apps/web && npx tsc --noEmit` → clean

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/lib/api.ts tests/test_mvp_layer2_ui.py
git commit -m "feat(layer2): frontend technical-model API types + calls"
```

---

## Task 12: `useTechnicalModel` hook

**Files:**
- Create: `apps/web/src/lib/hooks/useTechnicalModel.ts`
- Test: `tests/test_mvp_layer2_ui.py`

- [ ] **Step 1: Add the failing static test**

```python
def test_use_technical_model_hook_contract():
    hook = (WEB / "lib" / "hooks" / "useTechnicalModel.ts").read_text(encoding="utf-8")
    assert "generateTechnicalModel" in hook
    assert "renderTechnicalModel" in hook
    assert "applyConfirmation" in hook
    assert "fallbackUsed" in hook
```

- [ ] **Step 2: Run to verify it fails**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/test_mvp_layer2_ui.py -k hook -q` → FAIL

- [ ] **Step 3: Create `useTechnicalModel.ts`**

```typescript
"use client";
import { useState } from "react";
import {
  generateTechnicalModel, renderTechnicalModel,
  type RequirementAnalysis, type SadPreviewResponse,
  type TechnicalDiagrams, type TechnicalModel,
} from "../api";

export function useTechnicalModel(input: {
  requirementText: string; analysis: RequirementAnalysis | null;
  analysisId: string | null; sections: SadPreviewResponse["sections"];
  sourceContext: string | null; sourceReferences: string[];
}) {
  const [model, setModel] = useState<TechnicalModel | null>(null);
  const [diagrams, setDiagrams] = useState<TechnicalDiagrams | null>(null);
  const [fallbackUsed, setFallbackUsed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function generate() {
    if (!input.analysis) return;
    setBusy(true); setMessage("");
    try {
      const res = await generateTechnicalModel({
        requirementText: input.requirementText, analysis: input.analysis,
        analysisId: input.analysisId, sadSections: input.sections,
        sourceContext: input.sourceContext, sourceReferences: input.sourceReferences,
      });
      setModel(res.model); setDiagrams(res.diagrams); setFallbackUsed(res.fallback_used);
    } catch {
      setMessage("Could not generate the technical design. Try again.");
    } finally { setBusy(false); }
  }

  // Confirm-loop: replace the inferred value, drop the resolved confirmation,
  // mark the element 'stated', then re-render diagrams deterministically.
  async function applyConfirmation(id: string, value: string) {
    if (!model) return;
    const next = applyToModel(model, id, value);
    setModel(next);
    try { setDiagrams(await renderTechnicalModel(next)); } catch { /* keep old diagrams */ }
  }

  return { model, diagrams, fallbackUsed, busy, message, generate, applyConfirmation };
}

function applyToModel(model: TechnicalModel, id: string, value: string): TechnicalModel {
  const conf = model.confirmations.find((c) => c.id === id);
  if (!conf) return model;
  const remaining = model.confirmations.filter((c) => c.id !== id);
  // v1: relationship cardinality + field type/key edits.
  const relationships = model.relationships.map((r) =>
    conf.target_kind === "relationship" && `${r.from_entity}->${r.to_entity}` === conf.target_ref
      ? { ...r, cardinality: value as TechnicalModel["relationships"][number]["cardinality"], provenance: "stated" as const }
      : r);
  const entities = model.entities.map((e) => ({
    ...e,
    fields: e.fields.map((f) => {
      const ref = `${e.name}.${f.name}`;
      if (ref !== conf.target_ref) return f;
      if (conf.target_kind === "field_type") return { ...f, type: value, provenance: "stated" as const };
      if (conf.target_kind === "entity_key") return { ...f, key: value as TechnicalField["key"], provenance: "stated" as const };
      return f;
    }),
  }));
  return { ...model, relationships, entities, confirmations: remaining };
}
```

Add `type TechnicalField` to the import from `../api`.

- [ ] **Step 4: Static test + typecheck**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/test_mvp_layer2_ui.py -q` → PASS
Run: `cd apps/web && npx tsc --noEmit` → clean

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/lib/hooks/useTechnicalModel.ts tests/test_mvp_layer2_ui.py
git commit -m "feat(layer2): useTechnicalModel hook with confirm loop"
```

---

## Task 13: `TechnicalDesignTab` component (mermaid + confirm panel)

**Files:**
- Create: `apps/web/src/components/preview/TechnicalDesignTab.tsx` (+ `TechnicalDesignTab.module.css`)
- Test: `tests/test_mvp_layer2_ui.py`

- [ ] **Step 1: Add the failing static test**

```python
def test_technical_design_tab_renders_diagrams_and_confirmations():
    tab = (WEB / "components" / "preview" / "TechnicalDesignTab.tsx").read_text(encoding="utf-8")
    assert "erd_mermaid" in tab
    assert "state_mermaid" in tab
    assert "permissions_markdown" in tab
    assert "Confirm technical assumptions" in tab
    assert "applyConfirmation" in tab
    assert "Generate technical design" in tab
    assert "mermaid" in tab.lower()
```

- [ ] **Step 2: Run to verify it fails**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/test_mvp_layer2_ui.py -k tab -q` → FAIL

- [ ] **Step 3: Create `TechnicalDesignTab.tsx`**

```tsx
"use client";
import { useEffect, useRef } from "react";
import mermaid from "mermaid";
import { Button } from "../ui/Button";
import type { TechnicalDiagrams, TechnicalModel } from "../../lib/api";
import styles from "./TechnicalDesignTab.module.css";

mermaid.initialize({ startOnLoad: false, theme: "neutral" });

function Diagram({ code }: { code: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current || !code) return;
    const id = `m-${Math.random().toString(36).slice(2)}`;
    mermaid.render(id, code).then(({ svg }) => {
      if (ref.current) ref.current.innerHTML = svg;
    }).catch(() => { if (ref.current) ref.current.textContent = code; });
  }, [code]);
  return <div className={styles.diagram} ref={ref} />;
}

export function TechnicalDesignTab({
  model, diagrams, fallbackUsed, busy, message, onGenerate, onConfirm,
}: {
  model: TechnicalModel | null; diagrams: TechnicalDiagrams | null;
  fallbackUsed: boolean; busy: boolean; message: string;
  onGenerate: () => void; onConfirm: (id: string, value: string) => void;
}) {
  if (!model) {
    return (
      <div className={styles.empty}>
        <p>Generate the engineering view — entities, relationships, workflow states, and permissions — from your confirmed SAD.</p>
        <Button variant="primary" loading={busy} onClick={onGenerate}>
          Generate technical design
        </Button>
        {message ? <p className={styles.err}>{message}</p> : null}
      </div>
    );
  }
  return (
    <div className={styles.wrap}>
      {fallbackUsed ? <div className={styles.warn}>Showing a minimal model — refine the SAD for richer detail.</div> : null}
      <h4>Data model (ERD)</h4>
      {diagrams ? <Diagram code={diagrams.erd_mermaid} /> : null}
      <h4>Workflow states</h4>
      {diagrams ? <Diagram code={diagrams.state_mermaid} /> : null}
      <h4>Permissions</h4>
      <pre className={styles.matrix}>{diagrams?.permissions_markdown}</pre>
      {model.confirmations.length ? (
        <details className={styles.confirm} open>
          <summary>Confirm technical assumptions ({model.confirmations.length})</summary>
          <ul>
            {model.confirmations.map((c) => (
              <li key={c.id}>
                <span>{c.statement}</span>
                {c.options.length ? (
                  <span className={styles.opts}>
                    {c.options.map((opt) => (
                      <button key={opt} type="button" onClick={() => onConfirm(c.id, opt)}>{opt}</button>
                    ))}
                  </span>
                ) : (
                  <button type="button" onClick={() => onConfirm(c.id, c.current_inference)}>Confirm</button>
                )}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}
```

Create a minimal `TechnicalDesignTab.module.css` with `.wrap/.empty/.diagram/.matrix/.confirm/.warn/.err/.opts` (plain CSS, match the preview pane tokens).

- [ ] **Step 4: Static test + typecheck** (typecheck needs Task 16's mermaid dep installed; if running before Task 16, expect a missing-module type error — do Task 16 first if so, or accept the static test passing and defer tsc to Task 16).

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/test_mvp_layer2_ui.py -q` → PASS

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components/preview/TechnicalDesignTab.tsx apps/web/src/components/preview/TechnicalDesignTab.module.css tests/test_mvp_layer2_ui.py
git commit -m "feat(layer2): TechnicalDesignTab with mermaid + confirm panel"
```

---

## Task 14: Host the tab in `PreviewPane` + wire `WorkspaceV2`

**Files:**
- Modify: `apps/web/src/components/preview/PreviewPane.tsx` (add a Document | Technical design tab switch above `styles.doc`)
- Modify: `apps/web/src/components/WorkspaceV2.tsx` (instantiate `useTechnicalModel`, pass props)
- Test: `tests/test_mvp_layer2_ui.py`

- [ ] **Step 1: Add the failing static test**

```python
def test_preview_pane_hosts_technical_tab_and_workspace_wires_it():
    pane = (WEB / "components" / "preview" / "PreviewPane.tsx").read_text(encoding="utf-8")
    workspace = (WEB / "components" / "WorkspaceV2.tsx").read_text(encoding="utf-8")
    assert "TechnicalDesignTab" in pane
    assert "Technical design" in pane
    assert "useTechnicalModel" in workspace
    assert "isDraftReady" in pane  # the tab is gated on draft-ready
```

- [ ] **Step 2: Run to verify it fails** → FAIL

- [ ] **Step 3a: `PreviewPane.tsx`** — add a local `tab` state and a switch; render the existing document body when `tab === "doc"`, the new tab when `tab === "tech"`. Keep all existing markup for the doc view. Add to the props:

```tsx
  technical,  // { model, diagrams, fallbackUsed, busy, message, onGenerate, onConfirm }
```

Insert directly under `<div className={styles.head}>...</div>`:

```tsx
      {isDraftReady ? (
        <div className={styles.tabs}>
          <button type="button" className={tab === "doc" ? styles.tabOn : styles.tab}
                  onClick={() => setTab("doc")}>Document</button>
          <button type="button" className={tab === "tech" ? styles.tabOn : styles.tab}
                  onClick={() => setTab("tech")}>Technical design</button>
        </div>
      ) : null}
```

Wrap the existing `<div className={styles.doc}>…</div>` so it only renders when `tab === "doc"`, and after it add:

```tsx
      {tab === "tech" ? <TechnicalDesignTab {...technical} /> : null}
```

Add `import { useState } from "react";` (if not present), `const [tab, setTab] = useState<"doc" | "tech">("doc");`, and `import { TechnicalDesignTab } from "./TechnicalDesignTab";`. Add `.tabs/.tab/.tabOn` to `PreviewPane.module.css`.

- [ ] **Step 3b: `WorkspaceV2.tsx`** — instantiate the hook from existing state and pass it down:

```tsx
  const technical = useTechnicalModel({
    requirementText: qna.requirementText,
    analysis: qna.analysisResponse,
    analysisId: qna.analysis?.analysis_id ?? null,
    sections: sadSave.preview?.sections ?? [],
    sourceContext: sources.analysisContext,
    sourceReferences: sources.sourceReferences,
  });
```

Pass `technical={{ model: technical.model, diagrams: technical.diagrams, fallbackUsed: technical.fallbackUsed, busy: technical.busy, message: technical.message, onGenerate: technical.generate, onConfirm: technical.applyConfirmation }}` into the existing `<PreviewPane … />`. (Confirm `qna.analysisResponse` / `qna.requirementText` exist on the hook — they are used by `useSadSave` already; if a field name differs, use the actual one.)

- [ ] **Step 4: Static test + typecheck**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/test_mvp_layer2_ui.py -q` → PASS
Run: `cd apps/web && npx tsc --noEmit` → clean (after Task 16 mermaid dep)

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components/preview/PreviewPane.tsx apps/web/src/components/preview/PreviewPane.module.css apps/web/src/components/WorkspaceV2.tsx tests/test_mvp_layer2_ui.py
git commit -m "feat(layer2): host technical tab in preview, wire workspace state"
```

---

## Task 15: Save integration — Doc section + wiki note + artifact

**Files:**
- Modify: `services/api/src/sadify_api/services/wiki_compose.py` (add a `technical-design` note from optional Mermaid)
- Modify: `services/api/src/sadify_api/services/sad_save.py` (append a "Technical Design (Layer 2)" section to the Doc markdown + a `_SADify` technical artifact) — only when a model is supplied; default behavior unchanged.
- Modify: `services/api/src/sadify_api/routes/sad.py` (`/sad/save` and `/sad/wiki/*` accept an optional `technical` payload)
- Test: `tests/api/test_wiki_compose.py`, `tests/api/test_sad_save.py`

- [ ] **Step 1: Add failing tests**

```python
# tests/api/test_wiki_compose.py
def test_compose_adds_technical_note_when_diagrams_present():
    from sadify_api.services.wiki_compose import compose_wiki_files
    files = compose_wiki_files(... existing required args ...,
        technical_diagrams={"erd_mermaid": "erDiagram\n  A {\n  }",
                            "state_mermaid": "stateDiagram-v2",
                            "permissions_markdown": "| Action |"})
    paths = [f.relative_path for f in files]
    assert any("technical-design" in p for p in paths)
    note = next(f for f in files if "technical-design" in f.relative_path)
    assert "```mermaid" in note.content and "erDiagram" in note.content
```

(Fill the existing required `compose_wiki_files` args from the current signature; `technical_diagrams` is a NEW optional keyword defaulting to `None`, so existing calls are unaffected. Mirror an analogous optional-arg test in `test_sad_save.py` for the appended Doc section + artifact.)

- [ ] **Step 2: Run to verify it fails** → FAIL

- [ ] **Step 3: Implement additively**

- `wiki_compose.compose_wiki_files(..., technical_diagrams: dict | None = None)`: when present, append one `WikiFile` at `Wiki/technical-design.md` containing the three blocks (```mermaid fences for ERD/state, raw markdown for permissions) + frontmatter; add `- [[technical-design]]` to the index note's links. When `None`, output is byte-identical to today.
- `sad_save`: add optional `technical_markdown: str | None = None`; when present, append a `\n\n## Technical Design (Layer 2)\n` + the markdown to the Doc body, and write an extra `_SADify` artifact `technical-model` (the JSON). When `None`, unchanged.
- `routes/sad.py`: `/sad/save` and `/sad/wiki/preview|update` request models gain an optional `technical: TechnicalModelResponse | None = None`; pass its `diagrams`/markdown through. Default `None` preserves the current contract and all existing tests.

- [ ] **Step 4: Run targeted + full regression**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_wiki_compose.py tests/api/test_sad_save.py tests/ -q`
Expected: new tests PASS; full suite green (no existing wiki/save test changed).

- [ ] **Step 5: Commit**

```bash
git add services/api/src/sadify_api/services/wiki_compose.py services/api/src/sadify_api/services/sad_save.py services/api/src/sadify_api/routes/sad.py tests/api/test_wiki_compose.py tests/api/test_sad_save.py
git commit -m "feat(layer2): save diagrams into Doc section + wiki note (additive)"
```

(Frontend wiring of the optional `technical` payload into `useSadSave.save()/updateWiki()` is a small follow-on edit in the same task: pass `technical.model ? { model, diagrams, fallback_used } : undefined`. Add a static assertion in `tests/test_mvp_layer2_ui.py` that `useSadSave` references `technical`. Keep it optional so save without Layer 2 is unchanged.)

---

## Task 16: mermaid.js dependency + frontend build

**Files:**
- Modify: `apps/web/package.json`, `apps/web/package-lock.json`
- Test: build

- [ ] **Step 1: Install mermaid (pinned)**

Run: `cd apps/web && npm install mermaid@^11`
Expected: `mermaid` added to `dependencies`; lockfile updated.

- [ ] **Step 2: Typecheck + build**

Run: `cd apps/web && npx tsc --noEmit` → clean
Run: `cd apps/web && npm run build` → succeeds, single `/` route, standalone output produced.

- [ ] **Step 3: Verify standalone bundles mermaid** — confirm `npm run build` completes without "module not found: mermaid" and the standalone server starts locally (`node .next/standalone/server.js` then GET `/` 200). Stop the server after the check.

- [ ] **Step 4: Commit**

```bash
git add apps/web/package.json apps/web/package-lock.json
git commit -m "chore(layer2): add mermaid.js frontend dependency"
```

---

## Task 17: Full regression, deploy, and deployed smoke (TC-033)

**Files:**
- Create: `docs/superpowers/testing/test_cases/TC-033-layer2-technical-design.md`
- Modify: `docs/superpowers/testing/test_case_index.md`, `docs/superpowers/CURRENT.md`, `docs/superpowers/development/07_decision_log.md`

- [ ] **Step 1: Full local regression**

Run: `..\..\.venv\Scripts\python.exe -m pytest tests/ -q`
Expected: all green (existing 471/4-skipped + the new Layer-2 tests). Record the count.
Run: `cd apps/web && npx tsc --noEmit && npm run build` → clean.

- [ ] **Step 2: Redeploy both services (same TC-027 path)**

Backend (from worktree root):
```cmd
gcloud run deploy sadify-api --source . --project sadify --region asia-southeast1 --service-account sadify-agent-sa@sadify.iam.gserviceaccount.com --allow-unauthenticated --min-instances 0 --set-env-vars "GOOGLE_CLOUD_PROJECT=sadify,FIREBASE_PROJECT_ID=sadify,SADIFY_PERSISTENCE=firestore,SADIFY_DRIVE_MODE=live,SADIFY_DRIVE_LIVE_ENABLED=1,SADIFY_GOOGLE_OAUTH_CLIENT_ID=594758969655-0md22e7bs1hvjjg1ihpokvvtpuarq6pp.apps.googleusercontent.com,SADIFY_ENV=prod,SADIFY_ALLOWED_ORIGINS=https://sadify-web-594758969655.asia-southeast1.run.app"
```
Frontend:
```cmd
gcloud builds submit apps/web --config apps/web/cloudbuild.yaml --project sadify --substitutions=_NEXT_PUBLIC_SADIFY_API_BASE_URL=https://sadify-api-594758969655.asia-southeast1.run.app,_NEXT_PUBLIC_FIREBASE_API_KEY=<key>,_NEXT_PUBLIC_FIREBASE_APP_ID=<appId>
gcloud run deploy sadify-web --image asia-southeast1-docker.pkg.dev/sadify/cloud-run-source-deploy/sadify-web:latest --project sadify --region asia-southeast1 --allow-unauthenticated --min-instances 0
```

- [ ] **Step 3: Deployed smoke (browser)** — after a SAD is ready: open the **Technical design** tab → Generate → confirm ERD + state diagram render and the permissions table shows → resolve one inferred confirmation → diagram re-renders → Save → confirm the Doc gains a "Technical Design (Layer 2)" section and the wiki gains `technical-design.md`. Confirm `/sad/technical 200` in Cloud Logging.

- [ ] **Step 4: Close docs** — author TC-033 (expected/real/evidence/decision), add the index row, update CURRENT.md + decision log (new D-entry).

- [ ] **Step 5: Commit (docs are local per convention; commit the worktree test if any)**

```bash
git add tests/
git commit -m "test(layer2): TC-033 deployed smoke notes"
```

---

## Self-Review

- **Spec coverage:** input model (c) → Task 6; TechnicalModel schema → Task 1; provenance + confirm loop → Tasks 5/12/13; Mermaid ERD/state/permissions → Tasks 2-4; on-demand gated route → Task 8; render endpoint → Task 9; it_readiness flip → Task 10; tab integration → Tasks 13-14; save into Doc/wiki → Task 15; deploy → Task 17. All covered.
- **Non-breaking:** every backend signature change is an optional defaulted param (Tasks 7/10/15); every task ends on the full suite green; frontend additions are new files/tabs gated on `isDraftReady`.
- **Type consistency:** `TechnicalModelProvider.generate_technical_model`, `TechnicalModelResponse{model,diagrams,fallback_used}`, `render_all`, `derive_confirmations`, `build_technical_context`, `parse_technical_model`, `build_safe_fallback_model` used identically across backend tasks; `generateTechnicalModel`/`renderTechnicalModel`/`useTechnicalModel`/`TechnicalDesignTab` consistent across frontend tasks.
- **Open items (from spec):** mermaid delivery resolved in Task 16 (npm dep); dedicated `technical-design` wiki note chosen (Task 15); it_readiness mapping resolved (Task 10).

## Verification commands (quick reference)

- Backend unit: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_diagram_render.py tests/api/test_technical_model.py tests/api/test_technical_routes.py -q`
- Full backend: `..\..\.venv\Scripts\python.exe -m pytest tests/ -q`
- Frontend: `cd apps/web && npx tsc --noEmit && npm run build`
- Static UI: `..\..\.venv\Scripts\python.exe -m pytest tests/test_mvp_layer2_ui.py -q`
