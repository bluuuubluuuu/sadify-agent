# TC-032 Gemini Model Picker Design

Date: 2026-06-03
Status: Approved - ready for implementation planning

## Traceability Sources

- `CLAUDE.md` and `context.md` - Google/Gemini default, local-first discipline, doc discipline.
- `docs/superpowers/CURRENT.md` - TC-027 production MVP status and deployed Cloud Run URLs.
- `docs/superpowers/development/07_decision_log.md` - D-022, D-023, D-052, D-053, D-066, P-009, P-017.
- `docs/superpowers/specs/2026-06-03-tc033-sadify-layer2-technical-model-design.md` - Layer 2 will consume the same optional model field later.
- Official Vertex AI model docs for the approved model IDs:
  - `gemini-2.5-flash`
  - `gemini-2.5-pro`
  - `gemini-2.5-flash-lite`

## Goal

Add a single global Gemini model picker so a user can choose which approved
Gemini model powers SADify's Q&A and SAD preview calls at runtime. The default
behavior remains unchanged: missing, invalid, or unavailable choices fall back
to the backend default `gemini-2.5-flash`.

This resolves P-009 by making Pro an explicit user-selected quality/cost tradeoff
instead of a deploy-time switch. Non-Google providers remain deferred under P-017.

## Non-Goals

- No live OpenAI, Anthropic, Ollama, Hugging Face, or OpenAI-compatible adapters.
- No dynamic Vertex model discovery in the user-facing request path.
- No per-route picker; the UI exposes one global selected model.
- No deploy in this slice without explicit user approval.

## Approved Catalog

The backend owns one editable constant for the Gemini allowlist. Initial values:

```text
gemini-2.5-flash       default, balanced
gemini-2.5-pro         slower, higher quality
gemini-2.5-flash-lite  fastest / lower cost
```

`gemini-2.5-pro` has a published discontinuation date, so availability must not
be assumed forever. The implementation plan must include a live probe against
project `sadify`, Vertex AI, location `global`, after model-resolution code
lands. Any ID that does not return success for this project must be removed from
the shipped catalog before final verification.

## Backend Design

Add a small model-catalog unit, for example
`services/api/src/sadify_api/services/model_catalog.py`, with:

- `GEMINI_MODEL_CATALOG`: the single editable allowlist constant.
- `DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"`.
- `list_gemini_models(config) -> ModelCatalogResponse`.
- `resolve_gemini_model(requested_model, config) -> str`.

`GET /models` returns:

```json
{
  "default": "gemini-2.5-flash",
  "models": [
    {
      "id": "gemini-2.5-flash",
      "label": "Gemini 2.5 Flash",
      "description": "Balanced default for SADify.",
      "hint": ""
    }
  ]
}
```

Add optional fields:

- `RequirementAnalysisRequest.model: str | None = None`
- `SadPreviewRequest.model: str | None = None`
- Later Layer 2: `TechnicalModelRequest.model: str | None = None`

Update the Protocols additively:

```python
class RequirementAnalysisModel(Protocol):
    def analyze_requirement(
        self,
        requirement_text: str,
        *,
        repair: bool = False,
        model: str | None = None,
    ) -> str: ...


class SadPreviewModel(Protocol):
    def generate_preview(
        self,
        context: str,
        *,
        repair: bool = False,
        model: str | None = None,
    ) -> str: ...
```

Existing fake models and tests must keep passing because `model` is keyword-only
and defaulted. The route passes `request.model`; the Gemini implementation
resolves it to an allowed ID before calling `client.models.generate_content`.

## Unavailable Model Fail-Safe

The fail-safe has two layers:

1. Invalid or missing IDs are resolved to `config.sadify_model` when that value
   is allowed, otherwise to `gemini-2.5-flash`.
2. An ID that is still in `GEMINI_MODEL_CATALOG` but no longer served by Vertex
   must retry with the backend default and must not return a 500/502 solely
   because the selected model disappeared.

The unavailable-model path is treated the same as an invalid ID from the user's
point of view: SADify uses the backend default model. The implementation must
catch model-not-found style errors from the Gemini SDK for the selected model,
retry once with the default model, and only let the existing route-level failure
path run if the default model also fails.

Required backend test: simulate a configured-but-unavailable allowlisted model
by using a fake Gemini client/model that raises `NotFound` for the selected ID
and succeeds for the default ID. Assert that the route returns 200 and that the
default ID was used on retry.

## Frontend Design

Add model-catalog types and `listModels()` to `apps/web/src/lib/api.ts`.

`WorkspaceV2` owns:

- `modelCatalog`
- `selectedModel`
- initialization from `GET /models`
- persistence in `localStorage`

If `localStorage` contains a model that the backend no longer lists, the
frontend resets to the server default.

Add a compact `ModelPicker` in the chat area top bar. It is a normal select
control, not a large settings panel. The Pro option includes the hint:
`slower, higher quality`.

Thread `selectedModel` into:

- `useQnA` -> `analyzeRequirement()` for first analysis and answer continuation.
- `useSadSave` -> `generateSadPreview()`.

The picker affects future model calls only. It does not mutate stored analysis
records or saved previews.

## Data Flow

```text
WorkspaceV2 loads GET /models
  -> selectedModel = localStorage value if still listed, else server default
  -> ChatPanel renders ModelPicker
  -> user selects model, localStorage updates
  -> Q&A calls send model
  -> SAD preview call sends model
  -> backend resolves model against allowlist
  -> Gemini call uses resolved ID
  -> if selected ID is unavailable, retry backend default
```

## Error Handling

- `GET /models` is deterministic and does not call Vertex.
- Invalid requested model IDs silently resolve to default.
- Allowlisted but unavailable model IDs retry default and do not fail the user
  request when the default succeeds.
- If the default model itself fails, existing route-level behavior remains:
  analysis may use the established fallback path after structured validation
  failures, and SAD preview may use its safe fallback after invalid structured
  responses. True transport failures from the default model remain operational
  failures.

## Testing

Backend:

- Catalog response includes the default and all shipped model IDs.
- `resolve_gemini_model(None, config)` returns backend default.
- `resolve_gemini_model("bad-id", config)` returns backend default.
- Requests pass selected model into fake analysis and SAD preview models.
- Configured-but-unavailable allowlisted ID retries default and returns 200.
- Existing `create_app(...)` call sites and fake models remain compatible.

Frontend:

- `listModels()` calls `/models`.
- `ModelPicker` renders all catalog entries and the Pro hint.
- `WorkspaceV2` uses `localStorage` and resets stale selections to the server default.
- `useQnA` sends `model` on start and continuation calls.
- `useSadSave` sends `model` on SAD preview generation.

Verification:

- Backend: `..\..\.venv\Scripts\python.exe -m pytest tests/ -q`
- Frontend static tests: `..\..\.venv\Scripts\python.exe -m pytest tests/ -q`
- Frontend typecheck/build: `cd apps/web && npx tsc --noEmit` and `npm run build`
- Live probe: after model-resolution code lands, probe each allowlist ID against
  project `sadify`, Vertex AI, location `global`, and drop non-working IDs before
  final regression.

## Documentation

This slice uses:

- Spec: `docs/superpowers/specs/2026-06-03-tc032-gemini-model-picker-design.md`
- Plan: `docs/superpowers/plans/2026-06-03-tc032-gemini-model-picker.md`
- Test case: `docs/superpowers/testing/test_cases/TC-032-gemini-model-picker.md`

Layer 2 shifts to TC-033:

- Spec: `docs/superpowers/specs/2026-06-03-tc033-sadify-layer2-technical-model-design.md`
- Plan: `docs/superpowers/plans/2026-06-03-tc033-sadify-layer2-technical-model.md`
- Test case: `docs/superpowers/testing/test_cases/TC-033-layer2-technical-design.md`
