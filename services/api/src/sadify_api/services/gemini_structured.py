from typing import Protocol

from sadify_api.config import ApiConfig
from sadify_api.schemas import RequirementAnalysisResponse, SadPreviewResponse


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
        },
        "required": [
            "understanding_summary",
            "readiness",
            "categories",
            "next_question",
            "assumptions",
            "source_references",
            "proposed_extra_categories",
        ],
        "propertyOrdering": [
            "understanding_summary",
            "readiness",
            "categories",
            "next_question",
            "assumptions",
            "source_references",
            "proposed_extra_categories",
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
                "max_output_tokens": 1800,
                "response_mime_type": "application/json",
                "response_schema": requirement_analysis_schema(),
            },
        )
        return response.text or ""


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
                "max_output_tokens": 3000,
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
