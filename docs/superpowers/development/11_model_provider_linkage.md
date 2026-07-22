# Checkpoint 3: Flexible LLM Provider Linkage

Date: 2026-05-04
Status: Implemented as routing metadata/readiness foundation

## Decision

Keep the current Google Gemini route as the default for the prototype:

```env
SADIFY_MODEL_PROVIDER=google
SADIFY_MODEL=gemini-2.5-flash
SADIFY_FINAL_SAD_PROVIDER=google
SADIFY_FINAL_SAD_MODEL=gemini-2.5-flash
```

This preserves the Google for Startups AI Agents Challenge Track 1 story while leaving the architecture ready for multi-model routing.

Development evidence:

```text
Commit: 0ce2b68 feat: add flexible model routing foundation
Verification: .\.venv\Scripts\pytest.exe -> 17 passed
```

## Provider Bases To Support

The prototype now records these provider bases in code and environment configuration:

1. `google` - Gemini through Vertex AI or Google API key mode.
2. `openai` - GPT-family models through `OPENAI_API_KEY`.
3. `anthropic` - Claude-family models through `ANTHROPIC_API_KEY`.
4. `openai_compatible` - hosted or self-hosted endpoints that expose an OpenAI-compatible API.
5. `ollama` - local/open-source models through a local Ollama server.
6. `huggingface` - Hugging Face inference providers through `HF_TOKEN`.

## Current Implementation Scope

Implemented in development code:

- Provider-neutral model route metadata.
- Default requirement-analysis route: `google / gemini-2.5-flash`.
- Final SAD route override variables.
- Optional fallback route variables.
- Provider readiness reporting without exposing API keys.
- Streamlit sidebar visibility for model provider, model route, and provider readiness.

Implementation files:

```text
src/sadify/config.py
src/sadify/models/__init__.py
src/sadify/models/routing.py
src/sadify/app.py
tests/test_model_router.py
```

Not yet implemented:

- Live calls to OpenAI, Anthropic, Hugging Face, OpenAI-compatible endpoints, or Ollama.
- Runtime switching from the UI.
- Automatic fallback execution when a model call fails.

Those should be built after the requirement-analysis workflow is active, so each provider adapter can be tested against a real SADify task instead of a disconnected demo call.

## Environment Variables

Tracked example values live in `.env.example`. Local secrets live only in ignored `.env`.

```env
SADIFY_MODEL_PROVIDER=google
SADIFY_MODEL=gemini-2.5-flash
SADIFY_FINAL_SAD_PROVIDER=google
SADIFY_FINAL_SAD_MODEL=gemini-2.5-flash
SADIFY_FALLBACK_PROVIDER=
SADIFY_FALLBACK_MODEL=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
HF_TOKEN=
OPENAI_COMPATIBLE_BASE_URL=
OPENAI_COMPATIBLE_API_KEY=
OLLAMA_BASE_URL=
```

## Recommended Next Step

Keep developing with `google / gemini-2.5-flash` until the requirement-analysis flow is working. After that, add provider adapters in this order:

1. Google Gemini live adapter.
2. OpenAI and Anthropic adapters.
3. OpenAI-compatible and Ollama adapters.
4. Hugging Face adapter.

Do not add real non-Google calls just to prove routing exists. The route layer is useful only when it is connected to real SADify tasks: requirement analysis, final SAD generation, and fallback behavior.
