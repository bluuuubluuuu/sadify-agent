# TC-013 Model Provider Routing

Date Created: 2026-05-04
Last Updated: 2026-05-04
Status: Passed

## Purpose

Verify that SADify can keep Google/Gemini as the default model route while recording separate provider/model choices for requirement analysis, final SAD generation, and optional fallback behavior.

## Traceability Sources

- `docs/superpowers/development/05_development_workflow.md` - Checkpoint 2A
- `docs/superpowers/development/11_model_provider_linkage.md`
- `docs/superpowers/development/07_decision_log.md` - D-052 and D-053
- `src/sadify/models/routing.py`

## Inputs

Environment-style configuration values:

```text
SADIFY_MODEL_PROVIDER=google
SADIFY_MODEL=gemini-2.5-flash
SADIFY_FINAL_SAD_PROVIDER=anthropic
SADIFY_FINAL_SAD_MODEL=claude-sonnet-4
SADIFY_FALLBACK_PROVIDER=openai
SADIFY_FALLBACK_MODEL=gpt-5-mini
```

Provider readiness variables:

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
HF_TOKEN
OPENAI_COMPATIBLE_BASE_URL
OLLAMA_BASE_URL
```

## Preconditions

- Local `.venv` exists.
- `pytest` is installed.
- `src/sadify/models/routing.py` exists.
- `.env.example` contains provider route placeholders.

## Steps

1. Load default app configuration with no route overrides.
2. Build model routes.
3. Confirm requirement-analysis route is `google / gemini-2.5-flash`.
4. Confirm final-SAD route defaults to `google / gemini-2.5-flash`.
5. Load route overrides for final SAD and fallback.
6. Confirm final-SAD and fallback route metadata changes.
7. Simulate configured provider secret environment variables.
8. Confirm provider readiness is reported without exposing secret values.

## Expected Output

- Supported provider IDs include:
  - `google`
  - `openai`
  - `anthropic`
  - `openai_compatible`
  - `ollama`
  - `huggingface`
- Default routes use Google/Gemini.
- Final-SAD route can be configured separately from requirement analysis.
- Fallback route is optional.
- Provider readiness output does not expose API key values.
- No live external provider call is made.

## Real Output

- `supported_provider_ids()` returns the expected provider list.
- `build_model_routes()` keeps `google / gemini-2.5-flash` as the default route.
- `build_model_routes()` supports final-SAD override to `anthropic / claude-sonnet-4`.
- `build_model_routes()` supports fallback override to `openai / gpt-5-mini`.
- `build_provider_statuses()` reports configured status for providers without including secret values.
- Streamlit page model exposes model route and provider readiness data.

## Differences / Issues

- The route layer is metadata/readiness only.
- Live OpenAI, Anthropic, Hugging Face, Ollama, and OpenAI-compatible calls are not implemented yet by design.
- UI runtime switching is not implemented yet.

## Evidence

```text
Command: .\.venv\Scripts\pytest.exe tests/test_model_router.py -q
Result: 4 passed
```

```text
Command: .\.venv\Scripts\pytest.exe
Result: 17 passed in 4.44s
```

Covered files:

```text
src/sadify/config.py
src/sadify/models/__init__.py
src/sadify/models/routing.py
src/sadify/app.py
tests/test_model_router.py
tests/test_config.py
tests/test_app_shell.py
```

## Decision

Passed for the model provider routing foundation.

Continue to Checkpoint 3: requirement text input and standard first-response UI.

