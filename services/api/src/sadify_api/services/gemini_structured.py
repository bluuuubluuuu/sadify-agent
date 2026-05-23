from typing import Protocol

from sadify_api.config import ApiConfig
from sadify_api.schemas import RequirementAnalysisResponse, SadPreviewResponse
from sadify_api.services.questionnaire_plan import canonical_required_slots


class RequirementAnalysisModel(Protocol):
    def analyze_requirement(self, requirement_text: str, *, repair: bool = False) -> str:
        """Return model output as raw JSON text."""


class SadPreviewModel(Protocol):
    def generate_preview(self, context: str, *, repair: bool = False) -> str:
        """Return model output as raw JSON text."""


def parse_requirement_analysis(raw_json: str) -> RequirementAnalysisResponse:
    return RequirementAnalysisResponse.model_validate_json(raw_json)


def parse_sad_preview(raw_json: str) -> SadPreviewResponse:
    return SadPreviewResponse.model_validate_json(raw_json)


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


class GeminiRequirementAnalysisModel:
    def __init__(self, config: ApiConfig) -> None:
        self._config = config

    def analyze_requirement(self, requirement_text: str, *, repair: bool = False) -> str:
        from google import genai
        from google.genai.types import HttpOptions

        client = genai.Client(
            vertexai=self._config.google_genai_use_vertexai,
            project=self._config.google_cloud_project,
            location=self._config.google_cloud_location,
            http_options=HttpOptions(api_version="v1"),
        )
        prompt = _analysis_prompt(requirement_text, repair=repair)
        response = client.models.generate_content(
            model=self._config.sadify_model,
            contents=prompt,
            config={
                "temperature": 0.2,
                "max_output_tokens": 8000,
                # gemini-2.5-flash thinking tokens share the output budget and
                # were silently consuming most of it, leaving JSON truncated
                # mid-property. Structured output does not benefit from
                # thinking, so disable it.
                "thinking_config": {"thinking_budget": 0},
                "response_mime_type": "application/json",
                "response_schema": requirement_analysis_schema(),
            },
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
    def __init__(self, config: ApiConfig) -> None:
        self._config = config

    def generate_preview(self, context: str, *, repair: bool = False) -> str:
        from google import genai
        from google.genai.types import HttpOptions

        client = genai.Client(
            vertexai=self._config.google_genai_use_vertexai,
            project=self._config.google_cloud_project,
            location=self._config.google_cloud_location,
            http_options=HttpOptions(api_version="v1"),
        )
        prompt = _sad_preview_prompt(context, repair=repair)
        response = client.models.generate_content(
            model=self._config.sadify_model,
            contents=prompt,
            config={
                "temperature": 0.2,
                "max_output_tokens": 8000,
                # See analysis call: 2.5-flash thinking shares the output
                # budget and starves the JSON response.
                "thinking_config": {"thinking_budget": 0},
                "response_mime_type": "application/json",
                "response_schema": sad_preview_schema(),
            },
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
        "users and useful for IT. Include assumptions and open questions. "
        "Confirmed request facts are authoritative. Confirmed questionnaire "
        "answers refine or override ambiguity. Open questions must come only "
        "from unresolved items. Do not turn internal diagnostics into SAD "
        "assumptions. Layer 1 draft readiness and Layer 2 IT readiness are "
        "different; if IT readiness is lower, explain it as deeper "
        "implementation detail still to refine, not as missing draft basics. "
        "Use source references only when the provided context includes source IDs. "
        "Do not include Drive links or claim files were saved.\n\n"
        "Current project context:\n"
        f"{context}"
    )
