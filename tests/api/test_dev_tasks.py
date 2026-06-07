import json

import pytest

from sadify_api.schemas import (
    DevTask,
    DevTaskExtractionResponse,
    SadPreviewResponse,
)
from sadify_api.services.dev_tasks import (
    DevTaskGroundingError,
    extract_dev_tasks,
    validate_dev_tasks,
)
from tests.api.test_sad_preview import VALID_PREVIEW


def test_validate_dev_tasks_rejects_task_without_source_refs():
    preview = SadPreviewResponse.model_validate(VALID_PREVIEW)
    task = DevTask(
        priority="high",
        title="Build appointment scheduling",
        description="Create the appointment scheduling workflow.",
        source_references=[],
    )

    with pytest.raises(DevTaskGroundingError):
        validate_dev_tasks([task], preview)


def test_validate_dev_tasks_rejects_unknown_source_refs():
    preview = SadPreviewResponse.model_validate(VALID_PREVIEW)
    task = DevTask(
        priority="medium",
        title="Invent loyalty points",
        description="Add loyalty points even though the SAD does not mention them.",
        source_references=["SRC-DOES-NOT-EXIST"],
    )

    with pytest.raises(DevTaskGroundingError):
        validate_dev_tasks([task], preview)


def test_validate_dev_tasks_keeps_only_known_source_refs():
    preview = SadPreviewResponse.model_validate(VALID_PREVIEW)
    task = DevTask(
        priority="high",
        title="Build order intake",
        description="Capture the order details described in the SAD.",
        source_references=["SRC-000001", "SRC-DOES-NOT-EXIST"],
    )

    validated = validate_dev_tasks([task], preview)

    assert validated == [
        DevTask(
            priority="high",
            title="Build order intake",
            description="Capture the order details described in the SAD.",
            source_references=["SRC-000001"],
        )
    ]


def test_validate_dev_tasks_drops_ungrounded_task_but_keeps_grounded():
    preview = SadPreviewResponse.model_validate(VALID_PREVIEW)
    tasks = [
        DevTask(
            priority="high",
            title="Define detailed system architecture",
            description="Generic task the model could not ground.",
            source_references=[],
        ),
        DevTask(
            priority="high",
            title="Build order intake",
            description="Capture the order details described in the SAD.",
            source_references=["SRC-000001"],
        ),
    ]

    validated = validate_dev_tasks(tasks, preview)

    assert [t.title for t in validated] == ["Build order intake"]


def test_validate_dev_tasks_caps_to_eight_highest_priority():
    preview = SadPreviewResponse.model_validate(VALID_PREVIEW)
    tasks = (
        [
            DevTask(
                priority="low",
                title=f"Low task {i}",
                description="Grounded low task.",
                source_references=["SRC-000001"],
            )
            for i in range(15)
        ]
        + [
            DevTask(
                priority="high",
                title=f"High task {i}",
                description="Grounded high task.",
                source_references=["SRC-000001"],
            )
            for i in range(4)
        ]
    )

    validated = validate_dev_tasks(tasks, preview)

    assert len(validated) == 8
    # All four high-priority tasks survive the cap.
    assert sum(1 for t in validated if t.priority == "high") == 4
    assert [t.title for t in validated if t.priority == "high"] == [
        "High task 0",
        "High task 1",
        "High task 2",
        "High task 3",
    ]


def test_extract_dev_tasks_calls_model_and_validates_grounding():
    preview = SadPreviewResponse.model_validate(VALID_PREVIEW)
    model = FakeDevTaskModel(
        [
            {
                "tasks": [
                    {
                        "priority": "high",
                        "title": "Build order intake",
                        "description": "Capture the order details described in the SAD.",
                        "source_references": ["SRC-000001"],
                    }
                ]
            }
        ]
    )

    tasks = extract_dev_tasks(
        preview=preview,
        model=model,
        selected_model="gemini-2.5-pro",
    )

    assert tasks[0].title == "Build order intake"
    assert tasks[0].source_references == ["SRC-000001"]
    assert model.requests[0][1] == "gemini-2.5-pro"
    assert "SAD preview JSON" in model.requests[0][0]
    assert "Do not invent" in model.requests[0][0]


class FakeDevTaskModel:
    def __init__(self, outputs: list[dict[str, object]]) -> None:
        self.outputs = list(outputs)
        self.requests: list[tuple[str, str | None]] = []

    def extract_dev_tasks(self, context: str, *, model: str | None = None) -> str:
        self.requests.append((context, model))
        return json.dumps(self.outputs.pop(0))
