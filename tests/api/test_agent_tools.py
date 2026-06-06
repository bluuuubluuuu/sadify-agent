import json

from google.adk.tools import FunctionTool

from sadify_api.agent.approval import WriteApproval, WriteApprovalRequiredError
from sadify_api.agent.instruction import SADIFY_AGENT_INSTRUCTION
from sadify_api.agent.tools import (
    AgentDeps,
    build_agent_tool_functions,
    build_agent_tools,
)
from sadify_api.config import ApiConfig
from sadify_api.schemas import (
    DriveRepoConnectRequest,
    RequirementAnalysisResponse,
    SadPreviewResponse,
)
from sadify_api.services.analysis_state import RequirementAnalysisRepository
from sadify_api.services.drive_repo import DriveRepoRepository
from sadify_api.services.projects import ProjectRepository
from sadify_api.services.sad_preview import SadPreviewRepository
from sadify_api.services.sad_save import SadSaveRepository
from sadify_api.services.source_uploads import SourceRepository
from sadify_api.services.wiki_state import WikiStateRepository
from tests.api.test_gemini_structured import (
    FakeRequirementAnalysisModel,
    VALID_PAYLOAD,
)
from tests.api.test_sad_preview import (
    FakeSadPreviewModel,
    VALID_PREVIEW,
    _analysis_with_blocking_basics,
)


def test_agent_instruction_mirrors_behavior_contract_guardrails():
    instruction = SADIFY_AGENT_INSTRUCTION.lower()

    assert "clarify first" in instruction
    assert "judge readiness" in instruction
    assert "assumptions" in instruction
    assert "open questions" in instruction
    assert "without explicit approval" in instruction
    assert "traceable" in instruction
    assert "do not call extract_dev_tasks during normal sad finalization" in instruction
    assert "low-confidence" in instruction


def test_build_agent_tools_exposes_adk_function_tools():
    deps, *_ = _agent_deps()

    tools = build_agent_tools(deps)

    assert [tool.name for tool in tools] == [
        "get_readiness",
        "ask_clarification",
        "generate_sad",
        "review_sad",
        "extract_dev_tasks",
        "save_to_drive",
        "update_wiki",
    ]
    assert all(isinstance(tool, FunctionTool) for tool in tools)
    assert all(tool.description for tool in tools)


def test_get_readiness_returns_documented_shape_from_saved_analysis():
    deps, analysis_repository, *_ = _agent_deps()
    record = _save_analysis(analysis_repository)
    tool_functions = build_agent_tool_functions(deps)

    result = tool_functions.get_readiness(record.analysis_id)

    assert result == {
        "analysis_id": "AN-000001",
        "score": 35,
        "confidence": "Medium",
        "label": "Getting started",
        "gaps": [
            {"id": "problem", "label": "Problem", "status": "partial"},
            {"id": "users_roles", "label": "Users/Roles", "status": "missing"},
        ],
    }


def test_ask_clarification_uses_existing_analysis_engine_shape():
    deps, analysis_repository, _preview_repository, analysis_model, _preview_model = (
        _agent_deps(analysis_outputs=[_analysis_payload()])
    )
    _save_analysis(analysis_repository, analysis_session_id="session-001")
    tool_functions = build_agent_tool_functions(deps)

    result = tool_functions.ask_clarification("session-001")

    assert result == {
        "analysis_id": "AN-000002",
        "question": "What business goal should this request help achieve?",
        "why": "This clarifies the business goal.",
        "choices": [
            {"id": "reduce_delay", "label": "Reduce delays"},
            {"id": "reduce_errors", "label": "Reduce errors"},
            {"id": "not_sure", "label": "Not sure"},
        ],
        "target_category": "goal_scope",
        "target_slot_id": "business_goal",
    }
    assert [repair for _text, repair in analysis_model.requests] == [False]


def test_generate_sad_uses_preview_flow_shape():
    deps, analysis_repository, preview_repository, _analysis_model, preview_model = (
        _agent_deps(preview_outputs=[_preview_payload()])
    )
    analysis = RequirementAnalysisResponse.model_validate(
        _analysis_with_blocking_basics()
    )
    record = analysis_repository.save_analysis(
        requirement_text="Need to validate an operational workflow.",
        analysis_session_id="session-001",
        analysis=analysis,
    )
    tool_functions = build_agent_tool_functions(deps)

    result = tool_functions.generate_sad(record.analysis_id)

    assert result["preview_id"] == "SP-000001"
    assert result["sections"] == [
        {
            "title": section["title"],
            "body": section["body"],
            "source_references": section["source_references"],
        }
        for section in VALID_PREVIEW["sections"]
    ]
    assert result["assumptions"] == VALID_PREVIEW["assumptions"]
    assert result["open_questions"] == VALID_PREVIEW["open_questions"]
    assert preview_repository.get_preview("SP-000001") is not None
    assert [repair for _text, repair in preview_model.requests] == [False]


def test_review_sad_returns_structured_advisory_verdict():
    deps, analysis_repository, _preview_repository, _analysis_model, _preview_model = (
        _agent_deps(
            preview_outputs=[_preview_payload()],
            review_outputs=[
                {
                    "verdict": "regenerate",
                    "issues": [
                        {
                            "severity": "high",
                            "category": "workflow",
                            "message": "Workflow is too vague for a useful SAD.",
                        }
                    ],
                }
            ],
        )
    )
    analysis = RequirementAnalysisResponse.model_validate(
        _analysis_with_blocking_basics()
    )
    record = analysis_repository.save_analysis(
        requirement_text="Need to validate an operational workflow.",
        analysis_session_id="session-001",
        analysis=analysis,
    )
    tool_functions = build_agent_tool_functions(deps)
    preview = tool_functions.generate_sad(record.analysis_id)

    result = tool_functions.review_sad(preview["preview_id"])

    assert result == {
        "preview_id": "SP-000001",
        "verdict": "regenerate",
        "issues": [
            {
                "severity": "high",
                "category": "workflow",
                "message": "Workflow is too vague for a useful SAD.",
            }
        ],
    }


def test_extract_dev_tasks_returns_traceable_task_list():
    deps, analysis_repository, _preview_repository, _analysis_model, _preview_model = (
        _agent_deps(
            preview_outputs=[_preview_payload()],
            dev_task_outputs=[
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
            ],
            write_approval=_preview_write_approval("SP-000001"),
        )
    )
    analysis = RequirementAnalysisResponse.model_validate(
        _analysis_with_blocking_basics()
    )
    record = analysis_repository.save_analysis(
        requirement_text="Need to validate an operational workflow.",
        analysis_session_id="session-001",
        analysis=analysis,
    )
    tool_functions = build_agent_tool_functions(deps)
    preview = tool_functions.generate_sad(record.analysis_id)

    result = tool_functions.extract_dev_tasks(preview["preview_id"])

    assert result == {
        "status": "ready",
        "preview_id": "SP-000001",
        "tasks": [
            {
                "priority": "high",
                "title": "Build order intake",
                "description": "Capture the order details described in the SAD.",
                "source_references": ["SRC-000001"],
            }
        ],
    }


def test_extract_dev_tasks_requires_approved_preview_before_model_call():
    deps, analysis_repository, _preview_repository, _analysis_model, _preview_model = (
        _agent_deps(
            preview_outputs=[_preview_payload()],
            dev_task_outputs=[
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
            ],
        )
    )
    analysis = RequirementAnalysisResponse.model_validate(
        _analysis_with_blocking_basics()
    )
    record = analysis_repository.save_analysis(
        requirement_text="Need to validate an operational workflow.",
        analysis_session_id="session-001",
        analysis=analysis,
    )
    tool_functions = build_agent_tool_functions(deps)
    preview = tool_functions.generate_sad(record.analysis_id)

    result = tool_functions.extract_dev_tasks(preview["preview_id"])

    assert result == {
        "status": "error",
        "code": "DEV_TASKS_APPROVAL_REQUIRED",
        "message": "Approve this SAD preview before extracting developer tasks.",
    }
    assert deps.dev_task_model is not None
    assert deps.dev_task_model.requests == []


def test_extract_dev_tasks_rejects_ungrounded_model_tasks():
    deps, analysis_repository, _preview_repository, _analysis_model, _preview_model = (
        _agent_deps(
            preview_outputs=[_preview_payload()],
            dev_task_outputs=[
                {
                    "tasks": [
                        {
                            "priority": "medium",
                            "title": "Invent loyalty points",
                            "description": "Add a loyalty program not present in the SAD.",
                            "source_references": ["SRC-MISSING"],
                        }
                    ]
                }
            ],
            write_approval=_preview_write_approval("SP-000001"),
        )
    )
    analysis = RequirementAnalysisResponse.model_validate(
        _analysis_with_blocking_basics()
    )
    record = analysis_repository.save_analysis(
        requirement_text="Need to validate an operational workflow.",
        analysis_session_id="session-001",
        analysis=analysis,
    )
    tool_functions = build_agent_tool_functions(deps)
    preview = tool_functions.generate_sad(record.analysis_id)

    result = tool_functions.extract_dev_tasks(preview["preview_id"])

    assert result == {
        "status": "error",
        "code": "DEV_TASKS_UNGROUNDED",
        "message": "Developer task has no valid source references: Invent loyalty points",
    }


def test_write_tools_raise_without_matching_approval():
    deps, *_ = _agent_deps()
    tool_functions = build_agent_tool_functions(deps)

    try:
        tool_functions.save_to_drive("SP-000001")
    except WriteApprovalRequiredError as exc:
        assert exc.preview_id == "SP-000001"
        assert [action["id"] for action in exc.proposed_actions] == [
            "save_to_drive",
            "update_wiki",
        ]
    else:
        raise AssertionError("save_to_drive must refuse without approval")


def test_write_tool_accepts_matching_approval_and_runs_injected_save():
    calls = []

    def fake_save_runner(**kwargs):
        calls.append(kwargs)
        return FakeSaveRecord(
            save_id="SV-AGENT",
            preview_id=kwargs["request"].preview_id,
        )

    deps, *_ = _agent_deps(
        write_approval=WriteApproval(
            approval_id="AP-test",
            actions=[
                {
                    "id": "save_to_drive",
                    "label": "Save SAD to Google Drive",
                    "preview_id": "SP-000001",
                }
            ],
        ),
        sad_save_runner=fake_save_runner,
    )
    tool_functions = build_agent_tool_functions(deps)

    result = tool_functions.save_to_drive("SP-000001")

    assert result == {
        "status": "saved",
        "save_id": "SV-AGENT",
        "preview_id": "SP-000001",
        "doc_url": "https://docs.example/SV-AGENT",
        "doc_path": "SAD/SV-AGENT",
    }
    assert len(calls) == 1


def test_agent_wiki_update_resolves_live_drive_services_without_injected_deps(
    monkeypatch,
):
    from sadify_api.services import live_drive

    contexts = []

    class FakeSecretStore:
        def get_oauth_client_secret(self) -> str:
            return "client-secret"

        def get_user_refresh_token(self, uid: str) -> str:
            assert uid == "firebase-uid-001"
            return "refresh-token"

    class FakeDriveClient:
        def __init__(self, *, client_id: str, client_secret: str) -> None:
            assert client_id == "client-id"
            assert client_secret == "client-secret"

        def refresh_access_token(self, refresh_token: str) -> str:
            assert refresh_token == "refresh-token"
            return "access-token"

    class FakeWikiUpdateResponse:
        files = [object(), object()]

    def fake_wiki_update_runner(**kwargs):
        contexts.append(kwargs["context"])
        return FakeWikiUpdateResponse()

    monkeypatch.setattr(
        live_drive,
        "get_secret_store",
        lambda **_kwargs: FakeSecretStore(),
    )
    monkeypatch.setattr(live_drive, "DriveClient", FakeDriveClient)

    drive_repo_repository = DriveRepoRepository()
    project_repository = ProjectRepository()
    preview_repository = SadPreviewRepository()
    sad_save_repository = SadSaveRepository()
    repo = drive_repo_repository.connect_repo(
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        request=DriveRepoConnectRequest(
            authorization_code="unused-local-code",
            create_new_repo=True,
            project_id="PR-000001",
            repo_folder_name="SADify Projects",
        ),
    )
    project = project_repository.create_project(
        grant_id=repo.grant_id,
        name="Repair Shop Job Tracker",
        drive_folder_id="PROJECT-FOLDER-001",
    )
    drive_repo_repository.set_active_project(grant_id=repo.grant_id, project=project)
    preview_record = preview_repository.save_preview(
        requirement_text="Need to validate an operational workflow.",
        analysis_id="AN-000001",
        preview=SadPreviewResponse.model_validate(VALID_PREVIEW),
    )
    sad_save_repository.save_preview(
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        repo=repo,
        project_id=project.project_id,
        preview_record=preview_record,
        sources=[],
    )
    deps, *_ = _agent_deps(
        write_approval=WriteApproval(
            approval_id="AP-test",
            actions=[
                {
                    "id": "update_wiki",
                    "label": "Update project wiki",
                    "preview_id": preview_record.preview_id,
                }
            ],
        ),
        drive_repo_repository=drive_repo_repository,
        project_repository=project_repository,
        sad_save_repository=sad_save_repository,
        source_repository=SourceRepository(),
        wiki_state_repository=WikiStateRepository(),
        config=ApiConfig(
            environment="test",
            google_cloud_project="sadify",
            google_oauth_client_id="client-id",
            drive_mode="live",
            drive_live_enabled=True,
        ),
        wiki_update_runner=fake_wiki_update_runner,
    )
    tool_functions = build_agent_tool_functions(deps)

    result = tool_functions.update_wiki(False)

    assert result == {"status": "updated", "file_count": 2}
    assert contexts[0].access_token == "access-token"
    assert contexts[0].drive_client.__class__.__name__ == "FakeDriveClient"


def _agent_deps(
    *,
    analysis_outputs: list[dict[str, object]] | None = None,
    preview_outputs: list[dict[str, object]] | None = None,
    review_outputs: list[dict[str, object]] | None = None,
    dev_task_outputs: list[dict[str, object]] | None = None,
    write_approval: WriteApproval | None = None,
    sad_save_runner=None,
    drive_repo_repository=None,
    source_repository=None,
    sad_save_repository=None,
    config=None,
    wiki_state_repository=None,
    project_repository=None,
    wiki_update_runner=None,
):
    analysis_repository = RequirementAnalysisRepository()
    preview_repository = SadPreviewRepository()
    analysis_model = FakeRequirementAnalysisModel(
        analysis_outputs or [_analysis_payload()]
    )
    preview_model = FakeSadPreviewModel(preview_outputs or [_preview_payload()])
    review_model = FakeSadReviewModel(review_outputs or [_review_payload()])
    dev_task_model = FakeDevTaskModel(dev_task_outputs or [_dev_task_payload()])
    return (
        AgentDeps(
            analysis_repository=analysis_repository,
            sad_preview_repository=preview_repository,
            analysis_model=analysis_model,
            sad_preview_model=preview_model,
            sad_review_model=review_model,
            dev_task_model=dev_task_model,
            user=FakeUser(),
            write_approval=write_approval,
            sad_save_runner=sad_save_runner,
            drive_repo_repository=drive_repo_repository,
            source_repository=source_repository,
            sad_save_repository=sad_save_repository,
            config=config,
            wiki_state_repository=wiki_state_repository,
            project_repository=project_repository,
            wiki_update_runner=wiki_update_runner,
        ),
        analysis_repository,
        preview_repository,
        analysis_model,
        preview_model,
    )


def _save_analysis(
    repository: RequirementAnalysisRepository,
    *,
    analysis_session_id: str = "session-001",
):
    return repository.save_analysis(
        requirement_text="Need a simple way to validate operational ideas.",
        analysis_session_id=analysis_session_id,
        analysis=RequirementAnalysisResponse.model_validate(_analysis_payload()),
    )


def _analysis_payload() -> dict[str, object]:
    return json.loads(json.dumps(VALID_PAYLOAD))


def _preview_payload() -> dict[str, object]:
    return json.loads(json.dumps(VALID_PREVIEW))


def _review_payload() -> dict[str, object]:
    return {"verdict": "proceed", "issues": []}


def _dev_task_payload() -> dict[str, object]:
    return {"tasks": []}


def _preview_write_approval(preview_id: str) -> WriteApproval:
    return WriteApproval(
        approval_id="AP-test",
        actions=[
            {
                "id": "save_to_drive",
                "label": "Save SAD to Google Drive",
                "preview_id": preview_id,
            }
        ],
    )


class FakeSadReviewModel:
    def __init__(self, outputs: list[dict[str, object]]) -> None:
        self.outputs = list(outputs)
        self.requests: list[tuple[str, str | None]] = []

    def review_sad(self, context: str, *, model: str | None = None) -> str:
        self.requests.append((context, model))
        return json.dumps(self.outputs.pop(0))


class FakeDevTaskModel:
    def __init__(self, outputs: list[dict[str, object]]) -> None:
        self.outputs = list(outputs)
        self.requests: list[tuple[str, str | None]] = []

    def extract_dev_tasks(self, context: str, *, model: str | None = None) -> str:
        self.requests.append((context, model))
        return json.dumps(self.outputs.pop(0))


class FakeUser:
    uid = "firebase-uid-001"
    email = "owner@example.com"


class FakeArtifact:
    def __init__(self, save_id: str) -> None:
        self.url = f"https://docs.example/{save_id}"
        self.path = f"SAD/{save_id}"


class FakeSaveRecord:
    def __init__(self, *, save_id: str, preview_id: str) -> None:
        self.save_id = save_id
        self.preview_id = preview_id
        self.sad_doc = FakeArtifact(save_id)
