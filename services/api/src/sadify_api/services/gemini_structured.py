from collections.abc import Callable
import logging
from typing import Protocol

from sadify_api.config import ApiConfig

logger = logging.getLogger(__name__)
from sadify_api.schemas import (
    DevTaskExtractionResponse,
    RequirementAnalysisResponse,
    SadPreviewResponse,
    SadReviewResponse,
)
from sadify_api.services.model_catalog import backend_default_model, resolve_gemini_model
from sadify_api.services.questionnaire_plan import canonical_required_slots


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


class SadReviewModel(Protocol):
    def review_sad(
        self,
        context: str,
        *,
        model: str | None = None,
    ) -> str:
        """Return structured self-audit output as raw JSON text."""


class DevTaskExtractionModel(Protocol):
    def extract_dev_tasks(
        self,
        context: str,
        *,
        model: str | None = None,
    ) -> str:
        """Return structured developer-task output as raw JSON text."""


def parse_requirement_analysis(raw_json: str) -> RequirementAnalysisResponse:
    return RequirementAnalysisResponse.model_validate_json(raw_json)


def parse_sad_preview(raw_json: str) -> SadPreviewResponse:
    return SadPreviewResponse.model_validate_json(raw_json)


def parse_sad_review(raw_json: str) -> SadReviewResponse:
    return SadReviewResponse.model_validate_json(raw_json)


def parse_dev_task_extraction(raw_json: str) -> DevTaskExtractionResponse:
    return DevTaskExtractionResponse.model_validate_json(raw_json)


def requirement_analysis_schema() -> dict[str, object]:
    return {
        "type": "OBJECT",
        "properties": {
            "understanding_summary": {
                "type": "STRING",
            },
            "readiness": {
                "type": "OBJECT",
                "properties": {
                    "label": {"type": "STRING"},
                    "score": {
                        "type": "INTEGER",
                        "minimum": 0,
                        "maximum": 100,
                    },
                    "confidence": {
                        "type": "STRING",
                        "enum": ["Low", "Medium", "High"],
                    },
                },
                "required": ["label", "score", "confidence"],
                "propertyOrdering": ["label", "score", "confidence"],
            },
            "categories": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "id": {"type": "STRING"},
                        "label": {"type": "STRING"},
                        "status": {
                            "type": "STRING",
                            "enum": ["complete", "partial", "missing"],
                        },
                    },
                    "required": ["id", "label", "status"],
                    "propertyOrdering": ["id", "label", "status"],
                },
            },
            "next_question": {
                "type": "OBJECT",
                "properties": {
                    "text": {"type": "STRING"},
                    "why_this_matters": {"type": "STRING"},
                    "choices": {
                        "type": "ARRAY",
                        "minItems": 2,
                        "maxItems": 6,
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "id": {"type": "STRING"},
                                "label": {"type": "STRING"},
                                "is_disabled": {"type": "BOOLEAN"},
                                "status_label": {"type": "STRING"},
                            },
                            "required": ["id", "label"],
                            "propertyOrdering": [
                                "id",
                                "label",
                                "is_disabled",
                                "status_label",
                            ],
                        },
                    },
                    "target_category": {"type": "STRING"},
                    "target_slot_id": {"type": "STRING"},
                    "selection_mode": {
                        "type": "STRING",
                        "enum": ["single", "multiple"],
                    },
                },
                "required": [
                    "text",
                    "why_this_matters",
                    "choices",
                    "target_category",
                    "target_slot_id",
                ],
                "propertyOrdering": [
                    "text",
                    "why_this_matters",
                    "choices",
                    "target_category",
                    "target_slot_id",
                    "selection_mode",
                ],
            },
            "assumptions": {"type": "ARRAY", "items": {"type": "STRING"}},
            "source_references": {"type": "ARRAY", "items": {"type": "STRING"}},
            "proposed_extra_categories": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "id": {"type": "STRING"},
                        "label": {"type": "STRING"},
                        "reason": {"type": "STRING"},
                    },
                    "required": ["id", "label", "reason"],
                    "propertyOrdering": ["id", "label", "reason"],
                },
            },
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
        },
        "required": [
            "understanding_summary",
            "readiness",
            "categories",
            "next_question",
            "assumptions",
            "source_references",
            "proposed_extra_categories",
            "slot_evidence",
        ],
        "propertyOrdering": [
            "understanding_summary",
            "readiness",
            "categories",
            "next_question",
            "assumptions",
            "source_references",
            "proposed_extra_categories",
            "slot_evidence",
        ],
    }


def sad_preview_schema() -> dict[str, object]:
    return {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING"},
            "temporary_notice": {"type": "STRING"},
            "it_readiness": {
                "type": "OBJECT",
                "properties": {
                    "label": {"type": "STRING"},
                    "score": {
                        "type": "INTEGER",
                        "minimum": 0,
                        "maximum": 100,
                    },
                    "confidence": {
                        "type": "STRING",
                        "enum": ["Low", "Medium", "High"],
                    },
                    "checklist": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "id": {"type": "STRING"},
                                "label": {"type": "STRING"},
                                "status": {
                                    "type": "STRING",
                                    "enum": ["ready", "needs_input", "risk"],
                                },
                                "reason": {"type": "STRING"},
                            },
                            "required": ["id", "label", "status", "reason"],
                            "propertyOrdering": [
                                "id",
                                "label",
                                "status",
                                "reason",
                            ],
                        },
                    },
                },
                "required": ["label", "score", "confidence", "checklist"],
                "propertyOrdering": ["label", "score", "confidence", "checklist"],
            },
            "sections": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "title": {"type": "STRING"},
                        "body": {"type": "STRING"},
                        "source_references": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                        },
                    },
                    "required": ["title", "body", "source_references"],
                    "propertyOrdering": ["title", "body", "source_references"],
                },
            },
            "assumptions": {"type": "ARRAY", "items": {"type": "STRING"}},
            "open_questions": {"type": "ARRAY", "items": {"type": "STRING"}},
            "source_references": {"type": "ARRAY", "items": {"type": "STRING"}},
            "change_tracking": {
                "type": "OBJECT",
                "properties": {
                    "summary": {"type": "STRING"},
                    "paths": {"type": "ARRAY", "items": {"type": "STRING"}},
                },
                "required": ["summary", "paths"],
                "propertyOrdering": ["summary", "paths"],
            },
        },
        "required": [
            "title",
            "temporary_notice",
            "it_readiness",
            "sections",
            "assumptions",
            "open_questions",
            "source_references",
            "change_tracking",
        ],
        "propertyOrdering": [
            "title",
            "temporary_notice",
            "it_readiness",
            "sections",
            "assumptions",
            "open_questions",
            "source_references",
            "change_tracking",
        ],
    }


def sad_review_schema() -> dict[str, object]:
    return {
        "type": "OBJECT",
        "properties": {
            "verdict": {
                "type": "STRING",
                "enum": ["proceed", "tighten", "regenerate", "ask"],
            },
            "issues": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "severity": {
                            "type": "STRING",
                            "enum": ["low", "medium", "high"],
                        },
                        "category": {"type": "STRING"},
                        "message": {"type": "STRING"},
                    },
                    "required": ["severity", "category", "message"],
                    "propertyOrdering": ["severity", "category", "message"],
                },
            },
        },
        "required": ["verdict", "issues"],
        "propertyOrdering": ["verdict", "issues"],
    }


def dev_task_extraction_schema() -> dict[str, object]:
    return {
        "type": "OBJECT",
        "properties": {
            "tasks": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "priority": {
                            "type": "STRING",
                            "enum": ["high", "medium", "low"],
                        },
                        "title": {"type": "STRING"},
                        "description": {"type": "STRING"},
                        "source_references": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                        },
                    },
                    "required": [
                        "priority",
                        "title",
                        "description",
                        "source_references",
                    ],
                    "propertyOrdering": [
                        "priority",
                        "title",
                        "description",
                        "source_references",
                    ],
                },
            },
        },
        "required": ["tasks"],
        "propertyOrdering": ["tasks"],
    }


ClientFactory = Callable[[], object]


def _create_genai_client(config: ApiConfig) -> object:
    from google import genai
    from google.genai.types import HttpOptions

    return genai.Client(
        vertexai=config.google_genai_use_vertexai,
        project=config.google_cloud_project,
        location=config.google_cloud_location,
        http_options=HttpOptions(api_version="v1"),
    )


def _is_model_unavailable_error(exc: Exception) -> bool:
    message = str(exc).lower()
    has_not_found_signal = (
        exc.__class__.__name__ == "NotFound"
        or "404" in message
        or "not found" in message
    )
    return has_not_found_signal and "model" in message and "not found" in message


def _build_generation_config(
    model: str,
    response_schema: dict[str, object],
) -> dict[str, object]:
    """Model-aware generation config.

    Built per the model actually being called, because Pro and Flash have
    incompatible thinking settings — see the branch comments. Always recompute
    this from the resolved model (including on the fallback retry) so that a
    Pro -> Flash fallback uses Flash's config, not Pro's.
    """
    config: dict[str, object] = {
        "temperature": 0.2,
        "response_mime_type": "application/json",
        "response_schema": response_schema,
    }
    if model == "gemini-2.5-pro":
        # Gemini 2.5 Pro is a thinking model and rejects thinking_budget=0.
        # Leave thinking enabled and raise the output ceiling so reasoning
        # tokens do not starve the structured JSON response.
        config["max_output_tokens"] = 24000
    else:
        # Flash / Flash-Lite: thinking tokens share the output budget and were
        # silently consuming most of it, leaving JSON truncated mid-property.
        # Structured output does not benefit from thinking, so disable it and
        # keep the original 8000-token ceiling. Preserves prior behavior.
        config["max_output_tokens"] = 8000
        config["thinking_config"] = {"thinking_budget": 0}
    return config


def _generate_content_with_model_fallback(
    *,
    client: object,
    requested_model: str | None,
    config: ApiConfig,
    contents: str,
    response_schema: dict[str, object],
) -> object:
    selected_model = resolve_gemini_model(requested_model, config)
    try:
        response = client.models.generate_content(
            model=selected_model,
            contents=contents,
            config=_build_generation_config(selected_model, response_schema),
        )
        _log_token_usage(selected_model, response)
        return response
    except Exception as exc:
        default_model = backend_default_model(config)
        if selected_model == default_model or not _is_model_unavailable_error(exc):
            raise
        response = client.models.generate_content(
            model=default_model,
            contents=contents,
            config=_build_generation_config(default_model, response_schema),
        )
        _log_token_usage(default_model, response)
        return response


def _log_token_usage(model: str, response: object) -> None:
    """Emit per-call token counts so cost-per-SAD is measurable in logs.

    One SAD fans out into several model calls (per-turn analysis, preview,
    self-review, up to two regenerations, dev-task extraction). Grep these
    lines for an analysis/session id in the surrounding log context to sum a
    document's true token cost. Never raises — instrumentation must not break
    generation.
    """
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return
    try:
        logger.info(
            "gemini_token_usage model=%s prompt_tokens=%s output_tokens=%s "
            "total_tokens=%s",
            model,
            getattr(usage, "prompt_token_count", None),
            getattr(usage, "candidates_token_count", None),
            getattr(usage, "total_token_count", None),
        )
    except Exception:  # pragma: no cover - logging must never break generation
        pass


class GeminiRequirementAnalysisModel:
    def __init__(
        self,
        config: ApiConfig,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self._config = config
        self._client_factory = client_factory or (lambda: _create_genai_client(config))

    def analyze_requirement(
        self,
        requirement_text: str,
        *,
        repair: bool = False,
        model: str | None = None,
    ) -> str:
        client = self._client_factory()
        prompt = _analysis_prompt(requirement_text, repair=repair)
        response = _generate_content_with_model_fallback(
            client=client,
            requested_model=model,
            config=self._config,
            contents=prompt,
            response_schema=requirement_analysis_schema(),
        )
        return response.text or ""


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


def _analysis_prompt(requirement_text: str, *, repair: bool) -> str:
    repair_instruction = (
        "Your previous answer failed validation. Return corrected JSON only. "
        if repair
        else ""
    )
    return (
        f"{repair_instruction}"
        "You are SADify, a system analyst for early requirement validation. "
        "Analyze the business request without assuming hidden details. "
        "Ask exactly one next question in simple everyday language. "
        "If the business request includes a locked questionnaire target, use that "
        "exact active_category_id and target_slot_id. "
        "The wording of the question and every meaningful answer choice must stay "
        "inside that exact slot intent; do not reuse a question from another slot "
        "under a new slot ID. "
        "Do not rename, reorder, or invent visible question categories. Put any "
        "truly distinct extra category ideas only in proposed_extra_categories. "
        "Always provide clear answer choices, including an unsure option when useful. "
        "Set selection_mode to single unless the user may reasonably choose more "
        "than one answer. "
        "Keep assumptions visible and short. "
        "Use source_references only for business source labels such as uploaded "
        "files or Business Request. Never cite Previous Answer as a source.\n\n"
        f"{_slot_evidence_instructions()}\n\n"
        "Business request:\n"
        f"{requirement_text}"
    )


class GeminiSadPreviewModel:
    def __init__(
        self,
        config: ApiConfig,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self._config = config
        self._client_factory = client_factory or (lambda: _create_genai_client(config))

    def generate_preview(
        self,
        context: str,
        *,
        repair: bool = False,
        model: str | None = None,
    ) -> str:
        client = self._client_factory()
        prompt = _sad_preview_prompt(context, repair=repair)
        response = _generate_content_with_model_fallback(
            client=client,
            requested_model=model,
            config=self._config,
            contents=prompt,
            response_schema=sad_preview_schema(),
        )
        return response.text or ""


class GeminiSadReviewModel:
    def __init__(
        self,
        config: ApiConfig,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self._config = config
        self._client_factory = client_factory or (lambda: _create_genai_client(config))

    def review_sad(
        self,
        context: str,
        *,
        model: str | None = None,
    ) -> str:
        client = self._client_factory()
        response = _generate_content_with_model_fallback(
            client=client,
            requested_model=model,
            config=self._config,
            contents=_sad_review_prompt(context),
            response_schema=sad_review_schema(),
        )
        return response.text or ""


class GeminiDevTaskExtractionModel:
    def __init__(
        self,
        config: ApiConfig,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self._config = config
        self._client_factory = client_factory or (lambda: _create_genai_client(config))

    def extract_dev_tasks(
        self,
        context: str,
        *,
        model: str | None = None,
    ) -> str:
        client = self._client_factory()
        response = _generate_content_with_model_fallback(
            client=client,
            requested_model=model,
            config=self._config,
            contents=_dev_task_extraction_prompt(context),
            response_schema=dev_task_extraction_schema(),
        )
        return response.text or ""


def _sad_preview_prompt(context: str, *, repair: bool) -> str:
    repair_instruction = (
        "Your previous SAD preview failed validation. Return corrected JSON only. "
        if repair
        else ""
    )
    return (
        f"{repair_instruction}"
        "You are SADify, a system analyst preparing a temporary SAD preview. "
        "Do not pretend the preview is final. Keep the language clear for business "
        "users and useful for IT.\n\n"
        "SECTION COVERAGE: emit exactly one section for each cleared category "
        "listed in 'Cleared categories' below. Skip none. Use the category "
        "label as the section title (you may add a short qualifier).\n\n"
        "ASSUMPTIONS: populate the assumptions array from the 'Partial-evidence "
        "slots' list. Phrase each as a business-facing assumption referencing "
        "the quoted answer text. If the list is 'none', return an empty array.\n\n"
        "OPEN QUESTIONS: populate the open_questions array from the 'Deferred "
        "or unsure slots' list. Phrase each as a clear follow-up question for "
        "the business. If the list is 'none', return an empty array.\n\n"
        "SOURCE REFERENCES: for every section whose content draws on the "
        "uploaded source, include the relevant source ID (e.g. SRC-000001) "
        "in that section's source_references array. Also include every used "
        "source ID in the top-level source_references array.\n\n"
        "PARAPHRASING: do NOT paste questionnaire answer text verbatim into "
        "section bodies. Rewrite the user's answers as proper SAD prose, "
        "fixing partial sentences, typos, and clarifying truncated phrasing.\n\n"
        "Confirmed request facts are authoritative. Confirmed questionnaire "
        "answers refine or override ambiguity. Do not turn internal diagnostics "
        "into SAD assumptions. Layer 1 draft readiness and Layer 2 IT readiness "
        "are different; if IT readiness is lower, explain it as deeper "
        "implementation detail still to refine, not as missing draft basics. "
        "Use source references only when the provided context includes source IDs. "
        "Do not include Drive links or claim files were saved.\n\n"
        "Current project context:\n"
        f"{context}"
    )


def _sad_review_prompt(context: str) -> str:
    return (
        "You are SADify's internal SAD reviewer. Review the temporary SAD draft "
        "before it is treated as ready for user approval. Return JSON only.\n\n"
        "Choose exactly one verdict:\n"
        "- proceed: the draft is good enough for approval.\n"
        "- tighten: the draft can proceed but should surface advisory issues.\n"
        "- regenerate: the draft has fixable quality problems and should be "
        "regenerated before proceeding.\n"
        "- ask: the draft depends on a human clarification before proceeding.\n\n"
        "Flag missing sections, vague functional requirements, unsupported or "
        "weakly grounded claims, missing assumptions, and open questions. This is "
        "an advisory self-audit; do not perform sentence-level traceability. Keep "
        "issue messages concise and business-readable.\n\n"
        "SAD draft context:\n"
        f"{context}"
    )


def _dev_task_extraction_prompt(context: str) -> str:
    return (
        "You are SADify's developer-task planner. Create concise implementation "
        "tasks from the SAD preview only. Return Priority/Task/Description style "
        "items using priority values high, medium, or low. Every task must include "
        "at least one source_references value copied exactly from the SAD section "
        "or preview source references. Do not invent tasks, systems, integrations, "
        "roles, reports, or scope that are not supported by the SAD. If a useful "
        "task cannot be grounded to an existing source_references value, omit it. "
        "Return JSON only.\n\n"
        f"{context}"
    )
