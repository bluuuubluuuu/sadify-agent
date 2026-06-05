from dataclasses import dataclass, field
from uuid import uuid4


ProposedAction = dict[str, object]


@dataclass(frozen=True)
class WriteApproval:
    approval_id: str
    actions: list[ProposedAction] = field(default_factory=list)

    def allows(self, action_id: str, *, preview_id: str | None = None) -> bool:
        for action in self.actions:
            if action.get("id") != action_id:
                continue
            action_preview_id = action.get("preview_id")
            if preview_id is not None and action_preview_id not in (None, preview_id):
                continue
            return True
        return False


class ApprovalStore:
    def __init__(self) -> None:
        self._approvals: dict[tuple[str, str], WriteApproval] = {}

    def create(
        self,
        analysis_session_id: str,
        actions: list[ProposedAction],
    ) -> str:
        approval_id = f"AP-{uuid4().hex[:12]}"
        self._approvals[(analysis_session_id, approval_id)] = WriteApproval(
            approval_id=approval_id,
            actions=actions,
        )
        return approval_id

    def get(
        self,
        analysis_session_id: str,
        approval_id: str,
    ) -> WriteApproval | None:
        return self._approvals.get((analysis_session_id, approval_id))

    def consume(
        self,
        analysis_session_id: str,
        approval_id: str,
    ) -> WriteApproval | None:
        return self._approvals.pop((analysis_session_id, approval_id), None)


class WriteApprovalRequiredError(Exception):
    def __init__(
        self,
        *,
        tool_name: str,
        preview_id: str | None = None,
        proposed_actions: list[ProposedAction],
        message: str = "Approval is required before this write can run.",
        changed_files: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.tool_name = tool_name
        self.preview_id = preview_id
        self.proposed_actions = proposed_actions
        self.message = message
        self.changed_files = changed_files


class ApprovalTokenInvalidError(Exception):
    pass
