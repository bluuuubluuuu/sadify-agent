from sadify_api.schemas import DevTask, SadPreviewResponse
from sadify_api.services.gemini_structured import (
    DevTaskExtractionModel,
    parse_dev_task_extraction,
)


class DevTaskGroundingError(Exception):
    pass


MAX_DEV_TASKS = 8
_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


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
            # Drop an individual ungrounded task instead of failing the whole
            # batch — only grounded tasks become issues (no fabrication).
            continue
        validated.append(task.model_copy(update={"source_references": refs}))
    if not validated:
        raise DevTaskGroundingError(
            "No developer tasks could be grounded to SAD source references."
        )
    if len(validated) > MAX_DEV_TASKS:
        # Keep the highest-priority tasks so the UI/approval payload stays
        # demo-sized and reviewable; stable sort preserves order within a tier.
        validated = sorted(validated, key=_priority_rank)[:MAX_DEV_TASKS]
    return validated


def _priority_rank(task: DevTask) -> int:
    priority = task.priority.lower() if isinstance(task.priority, str) else ""
    return _PRIORITY_ORDER.get(priority, 1)


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
