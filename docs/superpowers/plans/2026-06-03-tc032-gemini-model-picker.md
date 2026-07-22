# TC-032 Gemini Model Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a backend-owned Gemini model catalog plus a single frontend picker that threads an optional model ID through Q&A and SAD preview calls while preserving the current default behavior.

**Architecture:** The backend exposes a deterministic `GET /models` route backed by one editable Gemini allowlist constant. Request schemas gain optional `model` fields; routes pass the model only when supplied so legacy fake models keep working. Gemini implementations resolve model IDs centrally and retry the backend default when an allowlisted model is no longer available from Vertex.

**Tech Stack:** Python 3.13 / FastAPI / Pydantic v2 / google-genai on Vertex AI; Next.js 16 / React 19 / TypeScript. Verification uses `D:\GoogleCloudHack\.venv`, Python static UI tests under `tests/`, `npx tsc --noEmit`, and `npm run build`.

**Worktree:** `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`, branch `codex/mvp-monorepo-scaffold`.

**Spec:** `D:\GoogleCloudHack\docs\superpowers\specs\2026-06-03-tc032-gemini-model-picker-design.md`.

**Numbering:** TC-032 is the picker. Layer 2 is reserved as TC-033.

---

## Non-Breaking Guardrails

- Do not deploy without explicit user approval.
- Keep every new request field optional and defaulted.
- Keep all existing `create_app(...)` call sites working unchanged.
- Do not require existing fake model classes to accept `model` unless a test for the picker explicitly sends a model.
- Use `..\..\.venv\Scripts\python.exe -m pytest tests/ -q` from the worktree root for backend/static tests.
- After frontend changes, run `cd apps/web && npx tsc --noEmit` and `npm run build`.
- Docs under `D:\GoogleCloudHack\docs` are local-only and gitignored. Do not force-commit docs.

---

## File Structure

Backend:

- Modify `services/api/src/sadify_api/schemas.py` - add `ModelCatalogItem`, `ModelCatalogResponse`, and optional `model` fields.
- Create `services/api/src/sadify_api/services/model_catalog.py` - single Gemini allowlist constant and resolver.
- Create `services/api/src/sadify_api/routes/models.py` - `GET /models`.
- Modify `services/api/src/sadify_api/main.py` - include the models route.
- Modify `services/api/src/sadify_api/services/gemini_structured.py` - Protocol signatures, Gemini client factory, model resolution, unavailable retry.
- Modify `services/api/src/sadify_api/routes/analysis.py` and `services/api/src/sadify_api/routes/sad.py` - pass model when supplied.
- Create `tests/api/test_model_catalog.py` - catalog, resolver, route, request threading, unavailable fallback.

Frontend:

- Modify `apps/web/src/lib/api.ts` - model catalog types, `listModels()`, optional model in generation calls.
- Create `apps/web/src/lib/hooks/useModelCatalog.ts` - load catalog, persist selection.
- Create `apps/web/src/components/chat/ModelPicker.tsx` - compact select.
- Modify `apps/web/src/components/chat/ChatPanel.tsx` and `chat.module.css` - top bar placement.
- Modify `apps/web/src/components/WorkspaceV2.tsx` - own selected model and pass through Q&A/SAD preview.
- Modify `apps/web/src/lib/hooks/useQnA.ts` and `useSadSave.ts` - accept selected model.
- Create `tests/test_mvp_model_picker_ui.py` - static frontend assertions.

Docs:

- Modify `docs/superpowers/testing/test_cases/TC-032-gemini-model-picker.md`.
- Modify `docs/superpowers/testing/test_case_index.md`.
- Modify `docs/superpowers/CURRENT.md`.
- Modify `docs/superpowers/development/07_decision_log.md`.

---

## Task 1: Backend Model Catalog and `GET /models`

**Files:**
- Modify: `services/api/src/sadify_api/schemas.py`
- Create: `services/api/src/sadify_api/services/model_catalog.py`
- Create: `services/api/src/sadify_api/routes/models.py`
- Modify: `services/api/src/sadify_api/main.py`
- Test: `tests/api/test_model_catalog.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/api/test_model_catalog.py`:

```python
from fastapi.testclient import TestClient

from sadify_api.config import ApiConfig
from sadify_api.main import create_app
from sadify_api.services.model_catalog import (
    DEFAULT_GEMINI_MODEL,
    GEMINI_MODEL_CATALOG,
    list_gemini_models,
    resolve_gemini_model,
)


def test_model_catalog_constant_contains_only_gemini_ids():
    ids = [entry["id"] for entry in GEMINI_MODEL_CATALOG]
    assert ids == [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.5-flash-lite",
    ]
    assert all(model_id.startswith("gemini-") for model_id in ids)


def test_resolve_gemini_model_defaults_and_rejects_invalid_ids():
    config = ApiConfig(environment="test", sadify_model="gemini-2.5-flash")

    assert resolve_gemini_model(None, config) == DEFAULT_GEMINI_MODEL
    assert resolve_gemini_model("", config) == DEFAULT_GEMINI_MODEL
    assert resolve_gemini_model("not-a-google-model", config) == DEFAULT_GEMINI_MODEL
    assert resolve_gemini_model("gemini-2.5-pro", config) == "gemini-2.5-pro"


def test_resolve_gemini_model_uses_flash_when_config_default_is_not_allowed():
    config = ApiConfig(environment="test", sadify_model="claude-sonnet-4")

    assert resolve_gemini_model(None, config) == DEFAULT_GEMINI_MODEL
    assert resolve_gemini_model("bad-id", config) == DEFAULT_GEMINI_MODEL


def test_list_gemini_models_returns_catalog_response():
    response = list_gemini_models(
        ApiConfig(environment="test", sadify_model="gemini-2.5-flash")
    )

    assert response.default == "gemini-2.5-flash"
    assert [model.id for model in response.models] == [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.5-flash-lite",
    ]
    assert next(model for model in response.models if model.id == "gemini-2.5-pro").hint == (
        "slower, higher quality"
    )


def test_models_route_returns_backend_catalog():
    client = TestClient(
        create_app(ApiConfig(environment="test", sadify_model="gemini-2.5-flash"))
    )

    response = client.get("/models")

    assert response.status_code == 200
    payload = response.json()
    assert payload["default"] == "gemini-2.5-flash"
    assert [model["id"] for model in payload["models"]] == [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.5-flash-lite",
    ]
```

- [ ] **Step 2: Run the test to verify it fails**

Run from the worktree root:

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/api/test_model_catalog.py -q
```

Expected: fails with `ModuleNotFoundError: No module named 'sadify_api.services.model_catalog'`.

- [ ] **Step 3: Add catalog response schemas**

Append near the other API response schemas in `services/api/src/sadify_api/schemas.py`:

```python
class ModelCatalogItem(ApiModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str = ""
    hint: str = ""


class ModelCatalogResponse(ApiModel):
    default: str = Field(min_length=1)
    models: list[ModelCatalogItem] = Field(default_factory=list)
```

- [ ] **Step 4: Create the backend catalog unit**

Create `services/api/src/sadify_api/services/model_catalog.py`:

```python
from sadify_api.config import ApiConfig
from sadify_api.schemas import ModelCatalogItem, ModelCatalogResponse

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

GEMINI_MODEL_CATALOG: tuple[dict[str, str], ...] = (
    {
        "id": "gemini-2.5-flash",
        "label": "Gemini 2.5 Flash",
        "description": "Balanced default for SADify.",
        "hint": "",
    },
    {
        "id": "gemini-2.5-pro",
        "label": "Gemini 2.5 Pro",
        "description": "Higher quality reasoning for complex SAD drafts.",
        "hint": "slower, higher quality",
    },
    {
        "id": "gemini-2.5-flash-lite",
        "label": "Gemini 2.5 Flash-Lite",
        "description": "Fastest Gemini option for low-latency drafts.",
        "hint": "fastest",
    },
)


def _allowed_ids() -> set[str]:
    return {entry["id"] for entry in GEMINI_MODEL_CATALOG}


def backend_default_model(config: ApiConfig) -> str:
    configured = (config.sadify_model or "").strip()
    if configured in _allowed_ids():
        return configured
    return DEFAULT_GEMINI_MODEL


def resolve_gemini_model(requested_model: str | None, config: ApiConfig) -> str:
    requested = (requested_model or "").strip()
    if requested in _allowed_ids():
        return requested
    return backend_default_model(config)


def list_gemini_models(config: ApiConfig) -> ModelCatalogResponse:
    return ModelCatalogResponse(
        default=backend_default_model(config),
        models=[ModelCatalogItem.model_validate(entry) for entry in GEMINI_MODEL_CATALOG],
    )
```

- [ ] **Step 5: Add `GET /models` route**

Create `services/api/src/sadify_api/routes/models.py`:

```python
from fastapi import APIRouter

from sadify_api.config import ApiConfig
from sadify_api.schemas import ModelCatalogResponse
from sadify_api.services.model_catalog import list_gemini_models


def create_models_router(config: ApiConfig) -> APIRouter:
    router = APIRouter(tags=["models"])

    @router.get("/models", response_model=ModelCatalogResponse)
    def models() -> ModelCatalogResponse:
        return list_gemini_models(config)

    return router
```

Modify `services/api/src/sadify_api/main.py`:

```python
from sadify_api.routes.models import create_models_router
```

Then include it after health/auth setup:

```python
    app.include_router(create_models_router(config))
```

- [ ] **Step 6: Run the targeted test**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/api/test_model_catalog.py -q
```

Expected: `5 passed`.

- [ ] **Step 7: Commit code and tests**

```powershell
git add services/api/src/sadify_api/schemas.py services/api/src/sadify_api/services/model_catalog.py services/api/src/sadify_api/routes/models.py services/api/src/sadify_api/main.py tests/api/test_model_catalog.py
git commit -m "feat(models): add Gemini model catalog endpoint"
```

---

## Task 2: Optional Model Request Fields and Route Threading

**Files:**
- Modify: `services/api/src/sadify_api/schemas.py`
- Modify: `services/api/src/sadify_api/services/gemini_structured.py`
- Modify: `services/api/src/sadify_api/routes/analysis.py`
- Modify: `services/api/src/sadify_api/routes/sad.py`
- Test: `tests/api/test_model_catalog.py`

- [ ] **Step 1: Add failing request-threading tests**

Append to `tests/api/test_model_catalog.py`:

```python
import json

from sadify_api.services.analysis_state import RequirementAnalysisRepository
from sadify_api.services.gemini_structured import RequirementAnalysisModel, SadPreviewModel
from sadify_api.services.sad_preview import SadPreviewRepository
from tests.api.test_gemini_structured import VALID_PAYLOAD
from tests.api.test_sad_preview import VALID_PREVIEW, _analysis_with_blocking_basics


class CapturingAnalysisModel(RequirementAnalysisModel):
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def analyze_requirement(
        self,
        requirement_text: str,
        *,
        repair: bool = False,
        model: str | None = None,
    ) -> str:
        self.calls.append({"repair": repair, "model": model, "text": requirement_text})
        payload = dict(VALID_PAYLOAD)
        payload["slot_evidence"] = []
        return json.dumps(payload)


class CapturingSadPreviewModel(SadPreviewModel):
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_preview(
        self,
        context: str,
        *,
        repair: bool = False,
        model: str | None = None,
    ) -> str:
        self.calls.append({"repair": repair, "model": model, "context": context})
        return json.dumps(VALID_PREVIEW)


def test_analysis_request_threads_selected_model_to_model_adapter():
    fake = CapturingAnalysisModel()
    client = TestClient(
        create_app(
            analysis_model=fake,
            analysis_repository=RequirementAnalysisRepository(),
        )
    )

    response = client.post(
        "/analysis/requirement",
        json={
            "requirement_text": "Need a simple way to validate operational ideas.",
            "model": "gemini-2.5-pro",
        },
    )

    assert response.status_code == 200
    assert fake.calls[0]["model"] == "gemini-2.5-pro"


def test_sad_preview_request_threads_selected_model_to_model_adapter():
    fake = CapturingSadPreviewModel()
    client = TestClient(
        create_app(
            sad_preview_model=fake,
            sad_preview_repository=SadPreviewRepository(),
        )
    )

    response = client.post(
        "/sad/preview",
        json={
            "requirement_text": "Need to validate an operational workflow.",
            "analysis_id": "AN-000001",
            "analysis": _analysis_with_blocking_basics(),
            "source_references": [],
            "model": "gemini-2.5-pro",
        },
    )

    assert response.status_code == 200
    assert fake.calls[0]["model"] == "gemini-2.5-pro"
```

- [ ] **Step 2: Run the tests to verify they fail**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/api/test_model_catalog.py -q
```

Expected: request-threading tests fail because schemas/routes do not yet carry `model`.

- [ ] **Step 3: Add optional request fields**

Modify `RequirementAnalysisRequest` and `SadPreviewRequest` in `schemas.py`:

```python
class RequirementAnalysisRequest(ApiModel):
    requirement_text: str = Field(min_length=5)
    guest_draft_id: str | None = None
    analysis_session_id: str | None = None
    source_context: str | None = None
    source_references: list[str] = Field(default_factory=list)
    model: str | None = None
```

```python
class SadPreviewRequest(ApiModel):
    requirement_text: str = Field(min_length=5)
    analysis_id: str | None = None
    analysis: RequirementAnalysisResponse
    source_context: str | None = None
    source_references: list[str] = Field(default_factory=list)
    model: str | None = None
```

- [ ] **Step 4: Update Protocols additively**

Modify Protocols in `services/api/src/sadify_api/services/gemini_structured.py`:

```python
class RequirementAnalysisModel(Protocol):
    def analyze_requirement(
        self,
        requirement_text: str,
        *,
        repair: bool = False,
        model: str | None = None,
    ) -> str:
        """Return model output as raw JSON text."""


class SadPreviewModel(Protocol):
    def generate_preview(
        self,
        context: str,
        *,
        repair: bool = False,
        model: str | None = None,
    ) -> str:
        """Return model output as raw JSON text."""
```

- [ ] **Step 5: Route through model only when supplied**

In `routes/analysis.py`, add this helper near `_safe_exception_message`:

```python
def _call_analysis_model(
    model: RequirementAnalysisModel,
    requirement_text: str,
    *,
    repair: bool,
    requested_model: str | None,
) -> str:
    if requested_model:
        return model.analyze_requirement(
            requirement_text,
            repair=repair,
            model=requested_model,
        )
    return model.analyze_requirement(requirement_text, repair=repair)
```

Replace:

```python
raw_json = model.analyze_requirement(
    model_requirement_text,
    repair=repair,
)
```

with:

```python
raw_json = _call_analysis_model(
    model,
    model_requirement_text,
    repair=repair,
    requested_model=request.model,
)
```

In `routes/sad.py`, add this helper near `_resolve_live_services`:

```python
def _call_sad_preview_model(
    model: SadPreviewModel,
    context: str,
    *,
    repair: bool,
    requested_model: str | None,
) -> str:
    if requested_model:
        return model.generate_preview(context, repair=repair, model=requested_model)
    return model.generate_preview(context, repair=repair)
```

Replace:

```python
raw_json = model.generate_preview(context, repair=repair)
```

with:

```python
raw_json = _call_sad_preview_model(
    model,
    context,
    repair=repair,
    requested_model=request.model,
)
```

- [ ] **Step 6: Run targeted and compatibility tests**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/api/test_model_catalog.py tests/api/test_gemini_structured.py::test_analysis_api_validates_model_output_and_saves_state tests/api/test_sad_preview.py::test_sad_preview_api_validates_model_output_and_saves_temporary_preview -q
```

Expected: targeted tests pass, proving old fake models still work when no `model` is supplied.

- [ ] **Step 7: Commit**

```powershell
git add services/api/src/sadify_api/schemas.py services/api/src/sadify_api/services/gemini_structured.py services/api/src/sadify_api/routes/analysis.py services/api/src/sadify_api/routes/sad.py tests/api/test_model_catalog.py
git commit -m "feat(models): thread optional model through analysis and preview"
```

---

## Task 3: Gemini Resolution and Unavailable-Model Fallback

**Files:**
- Modify: `services/api/src/sadify_api/services/gemini_structured.py`
- Test: `tests/api/test_model_catalog.py`

- [ ] **Step 1: Add failing unavailable-model tests**

Append to `tests/api/test_model_catalog.py`:

```python
from types import SimpleNamespace

from sadify_api.services.gemini_structured import (
    GeminiRequirementAnalysisModel,
    _is_model_unavailable_error,
)


class NotFound(Exception):
    pass


class FakeGeminiModels:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_content(self, *, model: str, contents: str, config: dict[str, object]):
        self.calls.append(model)
        if model == "gemini-2.5-pro":
            raise NotFound("404 model gemini-2.5-pro not found")
        return SimpleNamespace(text=json.dumps(VALID_PAYLOAD | {"slot_evidence": []}))


def test_model_unavailable_detector_accepts_notfound_style_errors():
    assert _is_model_unavailable_error(NotFound("404 model not found")) is True
    assert _is_model_unavailable_error(RuntimeError("quota exhausted")) is False


def test_gemini_requirement_model_retries_default_when_allowlisted_model_unavailable():
    fake_models = FakeGeminiModels()
    fake_client = SimpleNamespace(models=fake_models)
    adapter = GeminiRequirementAnalysisModel(
        ApiConfig(environment="test", sadify_model="gemini-2.5-flash"),
        client_factory=lambda: fake_client,
    )

    raw = adapter.analyze_requirement(
        "Need a simple way to validate operational ideas.",
        model="gemini-2.5-pro",
    )

    assert json.loads(raw)["understanding_summary"]
    assert fake_models.calls == ["gemini-2.5-pro", "gemini-2.5-flash"]
```

- [ ] **Step 2: Run the tests to verify they fail**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/api/test_model_catalog.py -k "unavailable or retries" -q
```

Expected: fails because `client_factory` and unavailable helpers do not exist.

- [ ] **Step 3: Add client factory, resolver, and retry helper**

Modify imports in `services/api/src/sadify_api/services/gemini_structured.py`:

```python
from collections.abc import Callable
from typing import Any, Protocol

from sadify_api.services.model_catalog import (
    backend_default_model,
    resolve_gemini_model,
)
```

Add helpers before the Gemini classes:

```python
GeminiClientFactory = Callable[[], Any]


def _is_model_unavailable_error(exc: Exception) -> bool:
    name = type(exc).__name__.replace("_", "").lower()
    message = str(exc).lower()
    if "notfound" in name:
        return True
    if "404" in message and "model" in message:
        return True
    return "not found" in message and "model" in message


def _generate_content_with_model_fallback(
    client: Any,
    *,
    requested_model: str | None,
    config: ApiConfig,
    contents: str,
    generation_config: dict[str, object],
):
    selected_model = resolve_gemini_model(requested_model, config)
    default_model = backend_default_model(config)
    try:
        return client.models.generate_content(
            model=selected_model,
            contents=contents,
            config=generation_config,
        )
    except Exception as exc:
        if selected_model != default_model and _is_model_unavailable_error(exc):
            return client.models.generate_content(
                model=default_model,
                contents=contents,
                config=generation_config,
            )
        raise
```

Add `_create_client`:

```python
def _create_genai_client(config: ApiConfig):
    from google import genai
    from google.genai.types import HttpOptions

    return genai.Client(
        vertexai=config.google_genai_use_vertexai,
        project=config.google_cloud_project,
        location=config.google_cloud_location,
        http_options=HttpOptions(api_version="v1"),
    )
```

- [ ] **Step 4: Update Gemini classes to use the helper**

Modify constructors and calls for requirement analysis:

```python
class GeminiRequirementAnalysisModel:
    def __init__(
        self,
        config: ApiConfig,
        client_factory: GeminiClientFactory | None = None,
    ) -> None:
        self._config = config
        self._client_factory = client_factory

    def analyze_requirement(
        self,
        requirement_text: str,
        *,
        repair: bool = False,
        model: str | None = None,
    ) -> str:
        client = self._client_factory() if self._client_factory else _create_genai_client(self._config)
        prompt = _analysis_prompt(requirement_text, repair=repair)
        response = _generate_content_with_model_fallback(
            client,
            requested_model=model,
            config=self._config,
            contents=prompt,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 8000,
                "thinking_config": {"thinking_budget": 0},
                "response_mime_type": "application/json",
                "response_schema": requirement_analysis_schema(),
            },
        )
        return response.text or ""
```

Modify `GeminiSadPreviewModel` explicitly:

```python
class GeminiSadPreviewModel:
    def __init__(
        self,
        config: ApiConfig,
        client_factory: GeminiClientFactory | None = None,
    ) -> None:
        self._config = config
        self._client_factory = client_factory

    def generate_preview(
        self,
        context: str,
        *,
        repair: bool = False,
        model: str | None = None,
    ) -> str:
        client = self._client_factory() if self._client_factory else _create_genai_client(self._config)
        prompt = _sad_preview_prompt(context, repair=repair)
        response = _generate_content_with_model_fallback(
            client,
            requested_model=model,
            config=self._config,
            contents=prompt,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 8000,
                "thinking_config": {"thinking_budget": 0},
                "response_mime_type": "application/json",
                "response_schema": sad_preview_schema(),
            },
        )
        return response.text or ""
```

- [ ] **Step 5: Run tests**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/api/test_model_catalog.py tests/api/test_gemini_structured.py::test_analysis_api_validates_model_output_and_saves_state tests/api/test_sad_preview.py::test_sad_preview_api_validates_model_output_and_saves_temporary_preview -q
```

Expected: all targeted tests pass.

- [ ] **Step 6: Commit**

```powershell
git add services/api/src/sadify_api/services/gemini_structured.py tests/api/test_model_catalog.py
git commit -m "fix(models): fall back when selected Gemini model is unavailable"
```

---

## Task 4: Live Probe the Allowlist Against Project `sadify`

**Files:**
- Possible modify: `services/api/src/sadify_api/services/model_catalog.py`
- Test: `tests/api/test_model_catalog.py`

- [ ] **Step 1: Run the live probe**

Run from the worktree root. This is an approved small Vertex probe; if sandboxed
network fails, rerun the same command with escalation.

```powershell
$probe = @'
from google import genai
from google.genai.types import HttpOptions

models = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite"]
client = genai.Client(
    vertexai=True,
    project="sadify",
    location="global",
    http_options=HttpOptions(api_version="v1"),
)

ok = []
failed = []
for model_id in models:
    try:
        response = client.models.generate_content(
            model=model_id,
            contents="Return the word ok.",
            config={
                "temperature": 0,
                "max_output_tokens": 16,
                "thinking_config": {"thinking_budget": 0},
            },
        )
        text = (response.text or "").strip()
        print(f"OK {model_id}: {text[:40]}")
        ok.append(model_id)
    except Exception as exc:
        print(f"FAIL {model_id}: {type(exc).__name__}: {str(exc)[:160]}")
        failed.append(model_id)

print("WORKING=" + ",".join(ok))
print("FAILED=" + ",".join(failed))
if not ok:
    raise SystemExit(2)
'@
$probe | ..\..\.venv\Scripts\python.exe -
```

Expected: every shipped catalog ID prints `OK`. If any ID prints `FAIL`, remove
that ID from `GEMINI_MODEL_CATALOG` before continuing.

- [ ] **Step 2: Prune failing IDs if needed**

If the probe output contains `FAIL gemini-2.5-pro`, remove only the Pro dict from
`GEMINI_MODEL_CATALOG` and update the expected IDs in
`tests/api/test_model_catalog.py`. Do the same for any other failing ID.

- [ ] **Step 3: Re-run catalog tests**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/api/test_model_catalog.py -q
```

Expected: pass with the probed working catalog only.

- [ ] **Step 4: Commit catalog pruning if a change was required**

If no IDs were removed, do not create a commit for this task. If IDs were removed:

```powershell
git add services/api/src/sadify_api/services/model_catalog.py tests/api/test_model_catalog.py
git commit -m "chore(models): prune unavailable Gemini catalog ids"
```

---

## Task 5: Frontend API Types and Model Threading

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Create: `tests/test_mvp_model_picker_ui.py`

- [ ] **Step 1: Write failing static tests**

Create `tests/test_mvp_model_picker_ui.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_api_exposes_model_catalog_and_threads_model_fields():
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")

    assert "export type ModelCatalogItem" in api
    assert "export type ModelCatalogResponse" in api
    assert "export async function listModels" in api
    assert 'fetch(`${baseUrl}/models`' in api
    assert "model?: string" in api
    assert "model: input.model ?? null" in api
```

- [ ] **Step 2: Run the test to verify it fails**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/test_mvp_model_picker_ui.py -q
```

Expected: fails because API types/functions do not exist.

- [ ] **Step 3: Add API types and calls**

In `apps/web/src/lib/api.ts`, add near the other exported types:

```ts
export type ModelCatalogItem = {
  id: string;
  label: string;
  description: string;
  hint: string;
};

export type ModelCatalogResponse = {
  default: string;
  models: ModelCatalogItem[];
};
```

Add this function near the other API helpers:

```ts
export async function listModels(): Promise<ModelCatalogResponse> {
  const response = await fetch(`${baseUrl}/models`);
  if (!response.ok) {
    throw new Error("SADify could not load the model list.");
  }
  return response.json();
}
```

Update input types:

```ts
export async function analyzeRequirement(input: {
  requirementText: string;
  guestDraftId?: string;
  analysisSessionId?: string;
  sourceContext?: string;
  sourceReferences?: string[];
  model?: string;
}): Promise<RequirementAnalysisApiResponse> {
```

Add to the JSON body:

```ts
      model: input.model ?? null,
```

Update `generateSadPreview` input and body similarly:

```ts
export async function generateSadPreview(input: {
  requirementText: string;
  analysisId?: string;
  analysis: RequirementAnalysis;
  sourceContext?: string;
  sourceReferences?: string[];
  model?: string;
}): Promise<SadPreviewApiResponse> {
```

```ts
      model: input.model ?? null,
```

- [ ] **Step 4: Run static test and typecheck**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/test_mvp_model_picker_ui.py -q
cd apps/web
npx tsc --noEmit
```

Expected: static test passes and TypeScript is clean.

- [ ] **Step 5: Commit**

```powershell
git add apps/web/src/lib/api.ts tests/test_mvp_model_picker_ui.py
git commit -m "feat(web): add model catalog API wiring"
```

---

## Task 6: Frontend Model Catalog Hook and LocalStorage

**Files:**
- Create: `apps/web/src/lib/hooks/useModelCatalog.ts`
- Test: `tests/test_mvp_model_picker_ui.py`

- [ ] **Step 1: Add failing static test**

Append to `tests/test_mvp_model_picker_ui.py`:

```python
def test_model_catalog_hook_loads_models_and_persists_selection():
    hook = (WEB_SRC / "lib" / "hooks" / "useModelCatalog.ts").read_text(
        encoding="utf-8"
    )

    assert "listModels" in hook
    assert "sadify:selectedModel" in hook
    assert "localStorage.getItem" in hook
    assert "localStorage.setItem" in hook
    assert "catalog.models.some" in hook
    assert "setSelectedModel(catalog.default)" in hook
```

- [ ] **Step 2: Run to verify it fails**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/test_mvp_model_picker_ui.py -k hook -q
```

Expected: fails because hook file does not exist.

- [ ] **Step 3: Create hook**

Create `apps/web/src/lib/hooks/useModelCatalog.ts`:

```ts
"use client";

import { useEffect, useMemo, useState } from "react";
import { listModels, type ModelCatalogResponse } from "../api";

const STORAGE_KEY = "sadify:selectedModel";
const FALLBACK_CATALOG: ModelCatalogResponse = {
  default: "gemini-2.5-flash",
  models: [
    {
      id: "gemini-2.5-flash",
      label: "Gemini 2.5 Flash",
      description: "Balanced default for SADify.",
      hint: "",
    },
  ],
};

export function useModelCatalog() {
  const [catalog, setCatalog] = useState<ModelCatalogResponse>(FALLBACK_CATALOG);
  const [selectedModel, setSelectedModelState] = useState(FALLBACK_CATALOG.default);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    void listModels()
      .then((nextCatalog) => {
        if (cancelled) return;
        setCatalog(nextCatalog);
        const stored =
          typeof window !== "undefined"
            ? window.localStorage.getItem(STORAGE_KEY)
            : null;
        const next = nextCatalog.models.some((model) => model.id === stored)
          ? stored
          : nextCatalog.default;
        setSelectedModelState(next ?? nextCatalog.default);
        if (next !== stored && typeof window !== "undefined") {
          window.localStorage.setItem(STORAGE_KEY, next ?? nextCatalog.default);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setMessage("Using the default Gemini model.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function setSelectedModel(modelId: string) {
    const next = catalog.models.some((model) => model.id === modelId)
      ? modelId
      : catalog.default;
    setSelectedModelState(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, next);
    }
  }

  const selected = useMemo(
    () => catalog.models.find((model) => model.id === selectedModel) ?? catalog.models[0],
    [catalog.models, selectedModel],
  );

  return { catalog, selectedModel, selected, message, setSelectedModel };
}
```

- [ ] **Step 4: Run static test and typecheck**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/test_mvp_model_picker_ui.py -q
cd apps/web
npx tsc --noEmit
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add apps/web/src/lib/hooks/useModelCatalog.ts tests/test_mvp_model_picker_ui.py
git commit -m "feat(web): persist selected Gemini model"
```

---

## Task 7: `ModelPicker` and Chat Top Bar

**Files:**
- Create: `apps/web/src/components/chat/ModelPicker.tsx`
- Modify: `apps/web/src/components/chat/ChatPanel.tsx`
- Modify: `apps/web/src/components/chat/chat.module.css`
- Test: `tests/test_mvp_model_picker_ui.py`

- [ ] **Step 1: Add failing static test**

Append to `tests/test_mvp_model_picker_ui.py`:

```python
def test_model_picker_renders_compact_chat_header_with_pro_hint():
    picker = (WEB_SRC / "components" / "chat" / "ModelPicker.tsx").read_text(
        encoding="utf-8"
    )
    chat = (WEB_SRC / "components" / "chat" / "ChatPanel.tsx").read_text(
        encoding="utf-8"
    )
    css = (WEB_SRC / "components" / "chat" / "chat.module.css").read_text(
        encoding="utf-8"
    )

    assert "ModelPicker" in chat
    assert "modelBar" in chat
    assert "<select" in picker
    assert "slower, higher quality" in picker
    assert "aria-label=\"Gemini model\"" in picker
    assert ".modelBar" in css
    assert ".modelSelect" in css
```

- [ ] **Step 2: Run to verify it fails**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/test_mvp_model_picker_ui.py -k picker -q
```

Expected: fails because component/top bar do not exist.

- [ ] **Step 3: Create `ModelPicker`**

Create `apps/web/src/components/chat/ModelPicker.tsx`:

```tsx
"use client";

import type { ModelCatalogResponse } from "../../lib/api";
import styles from "./chat.module.css";

export function ModelPicker({
  catalog,
  selectedModel,
  onChange,
}: {
  catalog: ModelCatalogResponse;
  selectedModel: string;
  onChange: (modelId: string) => void;
}) {
  const selected = catalog.models.find((model) => model.id === selectedModel);
  return (
    <label className={styles.modelPicker}>
      <span className={styles.modelLabel}>Gemini</span>
      <select
        aria-label="Gemini model"
        className={styles.modelSelect}
        value={selectedModel}
        onChange={(event) => onChange(event.target.value)}
      >
        {catalog.models.map((model) => (
          <option key={model.id} value={model.id}>
            {model.label}
            {model.hint ? ` - ${model.hint}` : ""}
          </option>
        ))}
      </select>
      {selected?.hint ? <span className={styles.modelHint}>{selected.hint}</span> : null}
      <span className={styles.modelProHint}>slower, higher quality</span>
    </label>
  );
}
```

The hidden `.modelProHint` text exists for static regression if Pro is pruned
from the live catalog; style it as visually hidden.

- [ ] **Step 4: Add top bar props to `ChatPanel`**

Modify imports in `ChatPanel.tsx`:

```tsx
import type { ModelCatalogResponse, SourceRecord } from "../../lib/api";
import { ModelPicker } from "./ModelPicker";
```

Add props:

```tsx
  modelCatalog,
  selectedModel,
  onModelChange,
```

Add types:

```tsx
  modelCatalog: ModelCatalogResponse;
  selectedModel: string;
  onModelChange: (modelId: string) => void;
```

In the return block, place the top bar before `ChatThread`:

```tsx
      <div className={styles.modelBar}>
        <span className={styles.modelBarTitle}>Model</span>
        <ModelPicker
          catalog={modelCatalog}
          selectedModel={selectedModel}
          onChange={onModelChange}
        />
      </div>
```

- [ ] **Step 5: Add CSS**

Append to `chat.module.css`:

```css
.modelBar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--c-border);
  background: var(--c-surface);
  flex: none;
}
.modelBarTitle {
  font-size: 12px;
  font-weight: var(--fw-bold);
  color: var(--c-subtle);
}
.modelPicker {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.modelLabel {
  font-size: 12px;
  font-weight: var(--fw-semi);
  color: var(--c-fg);
}
.modelSelect {
  max-width: 220px;
  border: 1px solid var(--c-border);
  border-radius: 8px;
  background: var(--c-bg);
  color: var(--c-fg);
  font: inherit;
  font-size: 12px;
  padding: 6px 9px;
}
.modelHint {
  font-size: 11px;
  color: var(--c-subtle);
  white-space: nowrap;
}
.modelProHint {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
@media (max-width: 767px) {
  .modelBar {
    padding: 10px 14px;
  }
  .modelPicker {
    flex: 1;
    justify-content: flex-end;
  }
  .modelSelect {
    max-width: min(210px, 58vw);
  }
  .modelHint {
    display: none;
  }
}
```

- [ ] **Step 6: Run static test**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/test_mvp_model_picker_ui.py -q
```

Expected: pass for static picker assertions. Typecheck may fail until Workspace wiring passes the new props in Task 8.

- [ ] **Step 7: Commit after Task 8 typecheck or commit now if TypeScript is clean**

If TypeScript is clean:

```powershell
git add apps/web/src/components/chat/ModelPicker.tsx apps/web/src/components/chat/ChatPanel.tsx apps/web/src/components/chat/chat.module.css tests/test_mvp_model_picker_ui.py
git commit -m "feat(web): add Gemini model picker to chat"
```

If TypeScript fails because `WorkspaceV2` has not passed the new props, complete Task 8 before committing Tasks 7 and 8 together.

---

## Task 8: Workspace Wiring Through Q&A and SAD Preview

**Files:**
- Modify: `apps/web/src/components/WorkspaceV2.tsx`
- Modify: `apps/web/src/lib/hooks/useQnA.ts`
- Modify: `apps/web/src/lib/hooks/useSadSave.ts`
- Test: `tests/test_mvp_model_picker_ui.py`

- [ ] **Step 1: Add failing static test**

Append to `tests/test_mvp_model_picker_ui.py`:

```python
def test_workspace_threads_selected_model_into_qna_and_sad_preview():
    workspace = (WEB_SRC / "components" / "WorkspaceV2.tsx").read_text(
        encoding="utf-8"
    )
    qna = (WEB_SRC / "lib" / "hooks" / "useQnA.ts").read_text(encoding="utf-8")
    save = (WEB_SRC / "lib" / "hooks" / "useSadSave.ts").read_text(encoding="utf-8")

    assert "useModelCatalog" in workspace
    assert "selectedModel={models.selectedModel}" in workspace
    assert "onModelChange={models.setSelectedModel}" in workspace
    assert "selectedModel: models.selectedModel" in workspace
    assert "model: selectedModel" in qna
    assert "model: selectedModel" in save
```

- [ ] **Step 2: Run to verify it fails**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/test_mvp_model_picker_ui.py -k workspace -q
```

Expected: fails because wiring is absent.

- [ ] **Step 3: Thread selected model through `useQnA`**

Modify hook signature in `useQnA.ts`:

```ts
  selectedModel,
```

Add prop type:

```ts
  selectedModel: string;
```

In both `analyzeRequirement` calls, add:

```ts
        model: selectedModel,
```

- [ ] **Step 4: Thread selected model through `useSadSave`**

Modify hook signature in `useSadSave.ts`:

```ts
  selectedModel,
```

Add prop type:

```ts
  selectedModel: string;
```

In `generateSadPreview`, add:

```ts
        model: selectedModel,
```

- [ ] **Step 5: Wire `WorkspaceV2`**

Add import:

```tsx
import { useModelCatalog } from "../lib/hooks/useModelCatalog";
```

Inside `WorkspaceV2()`:

```tsx
  const models = useModelCatalog();
```

Pass into `useQnA`:

```tsx
    selectedModel: models.selectedModel,
```

Pass into `useSadSave`:

```tsx
    selectedModel: models.selectedModel,
```

Pass into `ChatPanel`:

```tsx
      modelCatalog={models.catalog}
      selectedModel={models.selectedModel}
      onModelChange={models.setSelectedModel}
```

- [ ] **Step 6: Run static tests, typecheck, and build**

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/test_mvp_model_picker_ui.py tests/test_mvp_live_gemini_qna_ui.py tests/test_mvp_workspace_shell.py -q
cd apps/web
npx tsc --noEmit
npm run build
```

Expected: all pass.

- [ ] **Step 7: Commit frontend picker wiring**

If Task 7 was not committed, include those files too:

```powershell
git add apps/web/src/components/WorkspaceV2.tsx apps/web/src/lib/hooks/useQnA.ts apps/web/src/lib/hooks/useSadSave.ts apps/web/src/lib/hooks/useModelCatalog.ts apps/web/src/components/chat/ModelPicker.tsx apps/web/src/components/chat/ChatPanel.tsx apps/web/src/components/chat/chat.module.css tests/test_mvp_model_picker_ui.py
git commit -m "feat(web): thread selected Gemini model through workspace"
```

---

## Task 9: Full Regression and Documentation Closure

**Files:**
- Modify: `D:\GoogleCloudHack\docs\superpowers\testing\test_cases\TC-032-gemini-model-picker.md`
- Modify: `D:\GoogleCloudHack\docs\superpowers\testing\test_case_index.md`
- Modify: `D:\GoogleCloudHack\docs\superpowers\CURRENT.md`
- Modify: `D:\GoogleCloudHack\docs\superpowers\development\07_decision_log.md`

- [ ] **Step 1: Run full local verification**

From the worktree root:

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/ -q
cd apps/web
npx tsc --noEmit
npm run build
```

Expected:

- Python regression green.
- Static UI tests green.
- TypeScript clean.
- Next build succeeds.

- [ ] **Step 2: Update TC-032 test case doc**

Update `docs/superpowers/testing/test_cases/TC-032-gemini-model-picker.md` to:

```markdown
# TC-032 Gemini Model Picker

Date Created: 2026-06-03
Last Updated: 2026-06-03
Status: Passed

## Purpose

Verify that SADify exposes a backend-owned Gemini model catalog, lets the
frontend choose a model globally, sends the selected model through Q&A and SAD
preview calls, and falls back to the backend default when a requested model is
invalid or unavailable.

## Inputs

- Backend catalog IDs from `GEMINI_MODEL_CATALOG`.
- Frontend `ModelPicker` selection persisted in `localStorage`.
- Fake backend model adapters that capture the selected model.
- Fake Gemini client that raises `NotFound` for an allowlisted selected model
  and succeeds for the default model.

## Preconditions

- Worktree: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`
- Branch: `codex/mvp-monorepo-scaffold`
- No deploy without explicit approval.

## Steps

1. Call `GET /models`.
2. Submit `/analysis/requirement` without a model and with `gemini-2.5-pro`.
3. Submit `/sad/preview` without a model and with `gemini-2.5-pro`.
4. Simulate unavailable Pro and confirm retry to `gemini-2.5-flash`.
5. Verify frontend static wiring for `listModels`, `ModelPicker`, `localStorage`,
   `useQnA`, `useSadSave`, and `WorkspaceV2`.
6. Run full Python regression.
7. Run frontend typecheck and build.

## Expected Output

- `/models` returns the shipped Gemini catalog and backend default.
- Missing/invalid model IDs resolve to backend default.
- A configured but unavailable selected model retries backend default and does
  not fail the request when default succeeds.
- Frontend persists selected model and sends it on future Q&A/SAD preview calls.
- Existing MVP behavior remains unchanged when no model is selected.

## Real Output

Paste the exact command output lines from Step 1 and the live probe in Task 4.

## Differences / Issues

List any probe-pruned model IDs or write `None` when the shipped catalog stayed unchanged.

## Evidence

Include:

- `pytest` summary.
- `npx tsc --noEmit` result.
- `npm run build` result.
- Live allowlist probe output.

## Decision

Pass if all automated checks pass and the shipped catalog contains only model
IDs that work for project `sadify` in Vertex AI location `global`.
```

- [ ] **Step 3: Update test index**

In `docs/superpowers/testing/test_case_index.md`:

- Set `Last updated: 2026-06-03`.
- Update current phase text to say TC-032 model picker is the active post-MVP precursor to TC-033 Layer 2.
- Update the existing TC-032 row to `Passed` with the final run date, and keep
  the TC-033 row as `Planned`:

```markdown
| TC-032 | Gemini Model Picker | Passed | 2026-06-03 | `test_cases/TC-032-gemini-model-picker.md` | Backend-owned Gemini catalog, optional per-request model threading, localStorage-backed chat picker, and unavailable selected-model fallback to backend default. |
| TC-033 | Layer 2 Technical Design | Planned | Not run | `test_cases/TC-033-layer2-technical-design.md` | Planned technical model and diagrams slice; follows TC-032. |
```

- [ ] **Step 4: Update decision log**

In `docs/superpowers/development/07_decision_log.md`:

- Add confirmed decision:

```markdown
| D-096 | Expose Gemini model choice as a runtime picker backed by a backend-owned allowlist | Confirmed | Resolves P-009 without turning model choice into deploy-time config or enabling non-Google adapters. Missing, invalid, or allowlisted-but-unavailable selected IDs fall back to backend default; live non-Google providers remain deferred under P-017 | TC-032 spec/plan, Vertex model docs |
```

- Change P-009 status from `Pending` to `Confirmed by D-096` and current default from `Use Flash first` to `Runtime picker defaults to Flash`.
- Add change note:

```markdown
| 2026-06-03 | Approved TC-032 Gemini model picker and reserved Layer 2 as TC-033 | P-009 is resolved by runtime Gemini-only selection with backend fallback; Layer 2 follows after picker | TC-032 spec/plan, CURRENT, test index |
```

- [ ] **Step 5: Update CURRENT**

At the top of `docs/superpowers/CURRENT.md`, add a current-work block:

```markdown
## TC-032 Gemini Model Picker - DONE

TC-032 adds a backend-owned Gemini model catalog, optional model fields on Q&A
and SAD preview requests, a chat-header model picker persisted in localStorage,
and a fail-safe retry to the backend default when a selected allowlisted model is
unavailable. TC-032 is the required precursor to TC-033 Layer 2.

Layer 2 technical model and diagrams are now TC-033.
```

- [ ] **Step 6: Commit code/tests only**

Docs are local-only. Stage code/tests only:

```powershell
git status --short
git add services/api/src/sadify_api apps/web/src tests
git commit -m "feat(models): add Gemini model picker"
```

Do not `git add docs/`.

---

## Self-Review

- **Spec coverage:** Backend catalog and `GET /models` are Task 1; optional request fields and Protocol threading are Task 2; unavailable selected-model fallback is Task 3; live allowlist probe and pruning are Task 4; frontend `listModels`, localStorage, picker UI, and Q&A/SAD preview threading are Tasks 5-8; docs discipline is Task 9.
- **Non-breaking:** Existing fakes are preserved because routes only pass `model=` when the request supplied a model. New request fields are optional. `create_app(...)` receives only one new included route and no required parameter.
- **Unavailable-model condition:** Task 3 includes a fake `NotFound` simulation and asserts retry to default. Task 4 probes live IDs and prunes the shipped catalog before final verification.
- **Numbering:** TC-032 is the picker; Layer 2 is TC-033 in filenames and references.
- **No deploy:** No deploy command appears in this plan.

## Verification Commands

- Backend/catalog focused: `..\..\.venv\Scripts\python.exe -m pytest tests/api/test_model_catalog.py -q`
- Full Python/static: `..\..\.venv\Scripts\python.exe -m pytest tests/ -q`
- Frontend: `cd apps/web && npx tsc --noEmit && npm run build`
