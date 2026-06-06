from sadify_api.schemas import DevTask, SadPreviewResponse
from sadify_api.services.gemini_structured import (
    DevTaskExtractionModel,
    parse_dev_task_extraction,
)


class DevTaskGroundingError(Exception):
    pass


def extract_dev_tasks(
    *,
    preview: SadPreviewResponse,
    model: DevTaskExtractionModel,
    selected_model: str | None = None,
) -> list[DevTask]:
    response = parse_dev_task_extraction(
        model.extract_dev_tasks(
            _dev_task_context(preview),
            model=selected_model,
        )
    )
    return validate_dev_tasks(response.tasks, preview)


def validate_dev_tasks(
    tasks: list[DevTask],
    preview: SadPreviewResponse,
) -> list[DevTask]:
    allowed_refs = _allowed_source_references(preview)
    validated: list[DevTask] = []
    for task in tasks:
        refs = [ref for ref in task.source_references if ref in allowed_refs]
        if not refs:
            raise DevTaskGroundingError(
                f"Developer task has no valid source references: {task.title}"
            )
        validated.append(task.model_copy(update={"source_references": refs}))
    return validated


def _allowed_source_references(preview: SadPreviewResponse) -> set[str]:
    refs = set(preview.source_references)
    for section in preview.sections:
        refs.update(section.source_references)
    return refs


def _dev_task_context(preview: SadPreviewResponse) -> str:
    return (
        "Create developer implementation tasks from the SAD only.\n"
        "Each task must include at least one source_references value copied "
        "from the SAD section or preview source references.\n"
        "Do not invent tasks that are not supported by the SAD.\n"
        "If a useful task cannot be grounded to a source reference, omit it.\n\n"
        "SAD preview JSON:\n"
        f"{preview.model_dump_json()}"
    )
