# SADify Layer 2 — Technical Model & Diagrams Design

Date: 2026-06-03
Status: Draft - awaiting user spec review
Reserved test case: TC-033

## Traceability Sources

- `docs/superpowers/development/01_product_scope.md` (SAD/wiki core, future direction)
- `docs/superpowers/development/02_agent_behavior_contract.md` (expose gaps, don't fake completeness)
- `docs/superpowers/development/03_data_model_and_output_schema.md` (canonical records, relationships)
- `docs/superpowers/testing/test_cases/TC-024-mvp-sad-preview-it-readiness.md` (Layer-1/Layer-2 readiness)
- `docs/superpowers/testing/test_cases/TC-031-readiness-confidence-semantics.md` (provenance/evidence pattern)
- Deployed MVP (TC-027): the existing Q&A → SAD preview → save → wiki flow

## Goal

Turn the **Layer 2 "later implementation review"** placeholder (already advertised
in the SAD preview's IT-readiness checklist) into a real artifact: a **structured
technical model** extracted from the confirmed requirement facts, plus
**diagrams rendered from that model**. Layer 2 is the correlation foundation —
entities, relationships, states, permissions — and diagrams are deterministic
*views* over it, so diagram quality is bounded by model quality.

## Non-goals (v1)

Deferred to a later version: API/endpoint surface, architecture/component
diagrams, tech-stack recommendations, deployment topology. v1 covers the data
model (ERD), workflow/state machine, and the permissions matrix only.

## Scope (v1)

1. `TechnicalModel` extraction (Gemini structured output) from input model (c).
2. Provenance tagging (`stated` vs `inferred`) + an **inferred→confirm loop**.
3. Mermaid renderers: ERD, state diagram, permissions matrix (Markdown table).
4. On-demand generation in a new preview "Technical design" tab, gated on
   Layer-1 ready.
5. Save the confirmed Layer-2 artifacts into the existing Drive Doc + wiki.

## Input model (decision "c")

Layer 2 consumes BOTH organized and granular inputs:

- **Layer-1 SAD sections** (`SadPreviewResponse.sections`) — organized,
  business-validated structure.
- **Confirmed Q&A answers** (`analysis.questionnaire.answers`, incl. user
  amendments — the field-level detail) — granular primitives.
- **Source context + references** (`source_context`, `source_references`).
- **`understanding_summary`**.

This is the same context `build_sad_preview_context` already assembles, plus the
generated SAD sections. No new data is required from the user.

## TechnicalModel schema

```
TechnicalModel:
  entities: [
    { name, description,
      fields: [ { name, type, key: "pk"|"fk"|"none", required: bool,
                  provenance: "stated"|"inferred", source_refs: [str] } ],
      provenance, source_refs } ]
  relationships: [
    { from_entity, to_entity, cardinality: "1-1"|"1-many"|"many-many",
      label, provenance, source_refs } ]
  workflow:
    states: [ { name, description, provenance, source_refs } ]
    transitions: [ { from_state, to_state, trigger, actor, condition,
                     provenance, source_refs } ]
  actors: [ { name, type: "frontline"|"approver"|"viewer"|"external",
              responsibilities: [str], provenance, source_refs } ]
  permissions: [
    { actor, action, mode: "allow"|"requires_approval"|"deny",
      approver, provenance, source_refs } ]
  rules: [ { condition, action, approver, provenance, source_refs } ]
  confirmations: [
    { id, target_kind: "relationship"|"field_type"|"entity_key"|"state_set"|...,
      target_ref, statement, current_inference, options: [str] } ]
```

Every element carries `provenance` + `source_refs` (a SAD section title and/or
`SRC-`/answer id). `confirmations[]` is the derived list of inferred items the
user should confirm (see below).

## Grounding — the inferred→confirm loop

Layer 2 is inference-heavy (cardinalities, datatypes, keys, closed state sets
are rarely stated). Per the behaviour contract ("expose gaps, don't fake
completeness"), the model does not pretend certainty:

- The extraction prompt must label each element `stated` (grounded in a quote/
  answer) or `inferred` (SADify's reasonable default).
- The backend derives `confirmations[]` from the `inferred` elements — each a
  short confirmable statement (e.g. *"Inferred: one Owner has many Pets — is that
  right?"*, *"Inferred `payment_amount` as decimal"*).
- The UI shows the model + diagrams with inferred items visually distinct
  (dashed ERD edges, an "inferred" badge on rows) and a **"Confirm technical
  assumptions"** panel listing `confirmations`.
- The user can **accept all**, or edit/correct specific items. Confirmed/edited
  values are written back into the model; the diagrams re-render.
- This mirrors the existing assumptions / open-questions / wiki-approval pattern —
  no new interaction paradigm.

v1 keeps the confirm loop **client-side editing of the returned model** (no extra
Gemini call); re-rendering Mermaid after an edit is a deterministic backend
render call (no model call). See data flow.

## Rendering — Mermaid (deterministic, no image API)

`diagram_render.py` is pure (model in → strings out), unit-tested, no model call:

- **ERD** ← `erDiagram` from `entities` + `relationships` (cardinality → Mermaid
  crow's-foot; inferred edges annotated).
- **State diagram** ← `stateDiagram-v2` from `workflow.states` + `transitions`
  (trigger/actor as labels).
- **Permissions matrix** ← Markdown table (actor × action, cells allow /
  requires-approval(approver) / deny).

Mermaid is text: it renders in the SAD Doc, the wiki (Obsidian/GitHub), and the
preview UI (mermaid.js), costs nothing extra, and is itself a developer artifact.

## Architecture & modules (isolated units)

New backend (MVP `services/api`), each with one purpose:

- `services/technical_model.py` — `generate_technical_model(context)` → Gemini
  structured output → `TechnicalModel`; mirrors `sad_preview.py`'s
  repair-then-fallback discipline. Builds `context` from input model (c).
- `services/diagram_render.py` — `render_erd/ render_state/ render_permissions`
  (pure, deterministic, fully unit-tested).
- `schemas.py` — `TechnicalModel` + sub-models + `TechnicalModelResponse`.
- `gemini_structured.py` — add a `generate_technical_model(...)` method on the
  model class (same client/Vertex path already deployed).

New backend routes (alongside `/sad/preview`, `/sad/save`, `/sad/wiki/*`):

- `POST /sad/technical` — body: requirement_text, analysis, source_context,
  source_references, **sad_sections** (the Layer-1 preview). Returns
  `TechnicalModelResponse` (model + provenance + confirmations + rendered
  Mermaid). On-demand; gated: 409 if Layer-1 not draft-ready.
- `POST /sad/technical/render` — body: a (possibly edited) `TechnicalModel`.
  Returns re-rendered Mermaid. No Gemini call. Backs the confirm-loop edits.

Frontend:

- `lib/api.ts` — `TechnicalModel` types + `generateTechnicalModel()` +
  `renderTechnicalModel()`.
- `lib/hooks/useTechnicalModel.ts` — generate / edit / confirm / re-render state.
- `components/preview/TechnicalDesignTab.tsx` — renders Mermaid (mermaid.js) +
  the entity/permission tables + the confirm panel. Added as a **tab inside the
  existing `PreviewPane`**, not a new screen.

## Integration into the existing (streamlined) MVP

Layer 2 is **additive and opt-in** — the deployed Q&A → SAD → save → wiki flow is
unchanged. Concrete hook points:

1. **Trigger / gating.** The "Technical design" tab appears in `PreviewPane`
   only once a Layer-1 preview exists and `readiness >= 90` (same gate as the
   "Draft-ready" pill / `it_readiness`). Generation is on-demand (button), so no
   extra Gemini call or latency on the main path.
2. **Inputs reuse.** `POST /sad/technical` is fed from the *same* state the
   preview already holds in `WorkspaceV2`/`useSadSave` (`qna.analysisResponse`,
   `sources.analysisContext/sourceReferences`, `sadSave.preview.sections`). No new
   uploads, no new Q&A.
3. **IT-readiness stub becomes real.** `sad_preview._draft_ready_it_readiness`
   currently emits a placeholder `layer_two_review = needs_input`. Once a
   technical model is generated/confirmed, that checklist item flips to
   `in_progress`/`ready`, closing the loop the UI already advertises. (Small edit
   to the it_readiness composer to read a "has technical model" flag.)
4. **Save path reuse.** On save, the confirmed model's Mermaid + tables are
   appended to the existing SAD Google Doc as a **"Technical Design (Layer 2)"**
   section, via the current `sad_save` Doc path — no new Drive plumbing. The
   structured `TechnicalModel` JSON is stored as an additional `_SADify` artifact
   alongside the existing manifest/change-log.
5. **Wiki path reuse.** `wiki_compose` gains a **`technical-design` note** (or
   injects Mermaid into the existing `entities`/`workflows` notes) so the
   knowledge graph carries the diagrams. Reuses the existing
   preview→update→approve wiki flow and conflict/backup handling.
6. **No schema break.** `TechnicalModel` is a new, separate response; existing
   `SadPreviewResponse`, save, and wiki contracts are untouched (`lib/api.ts`
   shapes preserved), so all current tests/flows stay green.
7. **Deployment.** Additive to the already-deployed two-service app: new backend
   module + 2 routes, new frontend tab. Ship by rebuilding/redeploying both
   Cloud Run services (same `--source .` / `cloudbuild.yaml` path from TC-027).
   No new APIs, IAM, or secrets — the Vertex Gemini + Drive + Firestore wiring is
   already live.

## Data flow

```
[preview ready] → user clicks "Generate technical design"
  → POST /sad/technical (SAD sections + Q&A answers + source)
  → Gemini structured → TechnicalModel (stated/inferred) + confirmations
  → diagram_render → Mermaid → TechnicalModelResponse
  → tab shows diagrams + tables + "Confirm technical assumptions"
  → user accepts-all / edits inferred items (client state)
  → (on edit) POST /sad/technical/render → fresh Mermaid
  → on Save: confirmed model + Mermaid appended to SAD Doc + wiki note,
     TechnicalModel JSON saved as _SADify artifact; it_readiness Layer-2 → ready
```

## Error handling

Same discipline as `sad_preview`: Gemini structured output is parsed/validated;
on invalid JSON, one repair retry, then a **safe minimal fallback** model
(entities/actors derived deterministically from the SAD section titles + answers,
everything marked `inferred`) so the tab never 502s. Diagram rendering never
calls the model, so it cannot fail on model errors.

## Testing

- `diagram_render.py`: pure unit tests — model fixtures → exact Mermaid strings
  (ERD cardinality, state transitions, permission cells, inferred annotations).
- `technical_model.py`: structured-output parse/validate + repair + fallback
  tests with a fake model (mirrors `test_sad_preview` / `test_gemini_structured`).
- Provenance: inferred elements produce matching `confirmations[]`.
- Route tests: `/sad/technical` 200 + 409-when-not-ready; `/sad/technical/render`
  deterministic.
- Frontend static UI tests: TechnicalDesignTab renders Mermaid + confirm panel;
  gated on readiness; `lib/api.ts` exports the new types/functions.
- Integration: a TC-0xx deployed smoke case appended to the TC-027 flow.

## Build order (quality-first, diagrams follow the model)

1. `TechnicalModel` schema + `technical_model.py` extraction + fallback.
2. Quality-tune extraction (relationships/types/provenance) on the pet-grooming
   and catering cases until the model is faithful.
3. `diagram_render.py` (ERD, state, permissions) + unit tests.
4. `/sad/technical` + `/sad/technical/render` routes.
5. Frontend "Technical design" tab + confirm loop + mermaid.js.
6. Save integration (Doc section + wiki note + `_SADify` artifact) + it_readiness
   stub flip.
7. Deploy + smoke case.

## Open items (resolve at plan time)

- Mermaid.js delivery on the frontend (npm dep vs CDN) — prefer a bundled dep to
  keep the image self-contained; confirm Next standalone compatibility.
- Whether the wiki carries a dedicated `technical-design` note vs injecting
  Mermaid into existing `entities`/`workflows` notes (lean: dedicated note).
- Exact `it_readiness` Layer-2 status mapping once a model exists.
