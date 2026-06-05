from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from google.adk.tools import FunctionTool

from sadify_api.schemas import RequirementAnalysisRequest, SadPreviewRequest
from sadify_api.services.analysis_flow import run_analysis_turn
from sadify_api.services.analysis_state import RequirementAnalysisRepository
from sadify_api.services.gemini_structured import (
    RequirementAnalysisModel,
    SadPreviewModel,
)
from sadify_api.services.sad_flow import SadPreviewBlockedError, run_sad_preview
from sadify_api.services.sad_preview import SadPreviewRepository


ToolPayload = dict[str, Any]


@dataclass(frozen=True)
class AgentDeps:
    analysis_repository: RequirementAnalysisRepository
    sad_preview_repository: SadPreviewRepository
    analysis_model: RequirementAnalysisModel
    sad_preview_model: SadPreviewModel
    selected_model: str | None = None


@dataclass(frozen=True)
class AgentToolFunctions:
    get_readiness: Callable[[str], ToolPayload]
    ask_clarification: Callable[[str], ToolPayload]
    generate_sad: Callable[[str], ToolPayload]


def build_agent_tools(deps: AgentDeps) -> list[FunctionTool]:
    tool_functions = build_agent_tool_functions(deps)
    return [
        FunctionTool(tool_functions.get_readiness),
        FunctionTool(tool_functions.ask_clarification),
        FunctionTool(tool_functions.generate_sad),
    ]


def build_agent_tool_functions(deps: AgentDeps) -> AgentToolFunctions:
    def get_readiness(analysis_id: str) -> ToolPayload:
        """Return draft readiness for a saved analysis before deciding next action."""
        record = deps.analysis_repository.get_analysis(analysis_id)
        if record is None:
            return {
                "analysis_id": analysis_id,
                "score": 0,
                "confidence": "Low",
                "label": "Analysis not found",
                "gaps": [
                    {
                        "id": "analysis_not_found",
                        "label": "Analysis not found",
                        "status": "missing",
                    }
                ],
            }

        analysis = record.analysis
        readiness = (
            analysis.questionnaire.draft_readiness
            if analysis.questionnaire is not None
            else analysis.readiness
        )
        return {
            "analysis_id": record.analysis_id,
            "score": readiness.score,
            "confidence": readiness.confidence,
            "label": readiness.label,
            "gaps": _readiness_gaps(analysis),
        }

    def ask_clarification(analysis_session_id: str) -> ToolPayload:
        """Ask one clarification using SADify's existing locked-slot engine."""
        prior = deps.analysis_repository.latest_for_session(analysis_session_id)
        if prior is None:
            return {
                "analysis_id": "",
                "question": "I need a saved analysis session before asking the next clarification.",
                "why": "The questionnaire engine needs prior context to choose the right slot.",
                "choices": [],
                "target_category": "",
                "target_slot_id": "",
            }

        record = run_analysis_turn(
            request=RequirementAnalysisRequest(
                requirement_text=prior.requirement_text,
                guest_draft_id=prior.guest_draft_id,
                analysis_session_id=analysis_session_id,
                model=deps.selected_model,
                source_references=prior.analysis.source_references,
            ),
            model=deps.analysis_model,
            repository=deps.analysis_repository,
        )
        question = record.analysis.next_question
        return {
            "analysis_id": record.analysis_id,
            "question": question.text,
            "why": question.why_this_matters,
            "choices": [
                {"id": choice.id, "label": choice.label}
                for choice in question.choices
            ],
            "target_category": question.target_category,
            "target_slot_id": question.target_slot_id,
        }

    def generate_sad(analysis_id: str) -> ToolPayload:
        """Generate a SAD preview from a saved analysis when readiness is sufficient."""
        record = deps.analysis_repository.get_analysis(analysis_id)
        if record is None:
            return {
                "preview_id": "",
                "sections": [],
                "assumptions": [],
                "open_questions": ["Run analysis before generating a SAD preview."],
                "error": "analysis_not_found",
            }

        try:
            preview_record = run_sad_preview(
                request=SadPreviewRequest(
                    requirement_text=record.requirement_text,
                    analysis_id=record.analysis_id,
                    analysis=record.analysis,
                    model=deps.selected_model,
                    source_references=record.analysis.source_references,
                ),
                model=deps.sad_preview_model,
                repository=deps.sad_preview_repository,
            )
        except SadPreviewBlockedError as exc:
            return {
                "preview_id": "",
                "sections": [],
                "assumptions": [
                    "SAD preview is blocked until the missing basics are clarified."
                ],
                "open_questions": [
                    f"Clarify missing basic: {missing_basic}"
                    for missing_basic in exc.missing_basics
                ],
                "error": "sad_preview_blocked",
                "missing_basics": exc.missing_basics,
            }

        preview = preview_record.preview
        return {
            "preview_id": preview_record.preview_id,
            "sections": [section.model_dump() for section in preview.sections],
            "assumptions": list(preview.assumptions),
            "open_questions": list(preview.open_questions),
        }

    return AgentToolFunctions(
        get_readiness=get_readiness,
        ask_clarification=ask_clarification,
        generate_sad=generate_sad,
    )


def _readiness_gaps(analysis) -> list[dict[str, str]]:
    if analysis.questionnaire is not None:
        return [
            {
                "id": category.id,
                "label": category.label,
                "status": category.status,
            }
            for category in analysis.questionnaire.categories
            if category.status != "ready"
        ]
    return [
        {
            "id": category.id,
            "label": category.label,
            "status": category.status,
        }
        for category in analysis.categories
        if category.status != "complete"
    ]
