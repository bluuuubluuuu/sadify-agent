from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(ApiModel):
    status: str
    service: str
    environment: str


class ConfigDiagnosticsResponse(HealthResponse):
    diagnostics_enabled: bool
    secrets: str


class AuthenticatedUser(ApiModel):
    uid: str
    email: str | None = None
    display_name: str | None = None
    provider: str


class AuthSessionResponse(ApiModel):
    status: str
    user: AuthenticatedUser


class GuestDraftCreateRequest(ApiModel):
    guest_session_id: str
    requirement_text: str | None = None


class GuestDraftRecord(ApiModel):
    guest_draft_id: str
    owner_kind: Literal["guest"]
    guest_session_id: str
    status: Literal["active", "migrated", "abandoned"]
    requirement_text: str | None = None
    migrated_to_project_id: str | None = None
    created_at: datetime
    updated_at: datetime


class SignedInProjectRecord(ApiModel):
    project_id: str
    owner_kind: Literal["signed_in"]
    owner_uid: str
    owner_email: str | None = None
    source_guest_draft_id: str
    requirement_text: str | None = None
    status: Literal["active"]
    created_at: datetime
    updated_at: datetime


class GuestDraftMigrationResponse(ApiModel):
    status: Literal["copied"]
    guest_draft: GuestDraftRecord
    project: SignedInProjectRecord
    message: str


class ReadinessSummary(ApiModel):
    label: str = Field(min_length=1)
    score: int = Field(ge=0, le=100)
    confidence: Literal["Low", "Medium", "High"]


class QuestionnaireCategory(ApiModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    status: Literal["complete", "partial", "missing"]


class SlotEvidence(ApiModel):
    category_id: str = Field(min_length=1)
    slot_id: str = Field(min_length=1)
    applicability: Literal["applicable", "not_applicable"] = "applicable"
    strength: Literal["none", "partial", "strong"] = "none"
    evidence_quote: str = ""
    rationale: str = ""


class QuestionnaireProgressCategory(ApiModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    status: Literal["ready", "in_progress", "needed", "needs_later_confirmation"]
    visibility: Literal[
        "main", "already_understood", "completed", "suggested", "not_applicable"
    ] = "main"
    progress: int = Field(ge=0, le=100)
    questions_total: int = Field(ge=1)
    questions_answered: int = Field(ge=0)
    is_active: bool = False
    # Weakest evidence among required applicable slots. Lets the SAD-preview
    # gate distinguish "in_progress (partial-only)" from "in_progress (has
    # a slot with no evidence)" without changing slot data on the wire.
    weakest_slot_strength: Literal["none", "partial", "strong"] = "strong"


class QuestionnaireAnswer(ApiModel):
    category_id: str = Field(min_length=1)
    slot_id: str | None = None
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    is_uncertain: bool = False


class QuestionnaireState(ApiModel):
    draft_readiness: ReadinessSummary
    active_category_id: str = Field(min_length=1)
    active_slot_id: str | None = None
    active_slot_label: str | None = None
    categories: list[QuestionnaireProgressCategory] = Field(min_length=1)
    answers: list[QuestionnaireAnswer] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class QuestionnairePlanReadiness(ApiModel):
    label: str = Field(min_length=1)
    score: int = Field(ge=0, le=100)


class QuestionnairePlanSlot(ApiModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    required: bool = True
    status: Literal["open", "covered", "confirm_later"] = "open"
    evidence_strength: Literal["none", "partial", "strong"] = "none"
    applicable: bool = True


class QuestionnairePlanCategory(ApiModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    display_order: int = Field(ge=1)
    visibility: Literal[
        "main", "already_understood", "completed", "suggested", "not_applicable"
    ] = "main"
    status: Literal["needs_answer", "in_progress", "ready", "confirm_later"]
    slots: list[QuestionnairePlanSlot] = Field(min_length=1)

    def slot(self, slot_id: str) -> QuestionnairePlanSlot:
        for slot in self.slots:
            if slot.id == slot_id:
                return slot
        raise KeyError(slot_id)


class QuestionnairePlanSlotPointer(ApiModel):
    category_id: str = Field(min_length=1)
    slot_id: str = Field(min_length=1)


class QuestionnairePlan(ApiModel):
    plan_id: str = Field(min_length=1)
    active_category_id: str | None = None
    categories: list[QuestionnairePlanCategory] = Field(min_length=1)
    suggested_additions: list[QuestionnairePlanCategory] = Field(default_factory=list)
    overall_readiness: QuestionnairePlanReadiness

    def category(self, category_id: str) -> QuestionnairePlanCategory:
        for category in self.categories:
            if category.id == category_id:
                return category
        raise KeyError(category_id)


class QuestionChoice(ApiModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    is_disabled: bool = False
    status_label: str = ""


class NextQuestion(ApiModel):
    text: str = Field(min_length=1)
    why_this_matters: str = Field(min_length=1)
    choices: list[QuestionChoice] = Field(min_length=2, max_length=6)
    target_category: str = Field(min_length=1)
    target_slot_id: str = Field(min_length=1)
    selection_mode: Literal["single", "multiple"] = "single"


class ProposedExtraCategory(ApiModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class RequirementAnalysisResponse(ApiModel):
    understanding_summary: str = Field(min_length=1)
    readiness: ReadinessSummary
    categories: list[QuestionnaireCategory] = Field(min_length=1)
    next_question: NextQuestion
    assumptions: list[str]
    source_references: list[str]
    proposed_extra_categories: list[ProposedExtraCategory] = Field(default_factory=list)
    slot_evidence: list[SlotEvidence] = Field(default_factory=list)
    questionnaire: QuestionnaireState | None = None


class RequirementAnalysisRequest(ApiModel):
    requirement_text: str = Field(min_length=5)
    guest_draft_id: str | None = None
    source_context: str | None = None
    source_references: list[str] = Field(default_factory=list)


class RequirementAnalysisRecord(ApiModel):
    analysis_id: str
    guest_draft_id: str | None = None
    requirement_text: str
    analysis: RequirementAnalysisResponse
    created_at: datetime


class RequirementAnalysisApiResponse(ApiModel):
    analysis_id: str
    saved: bool
    analysis: RequirementAnalysisResponse


class ItReadinessCheck(ApiModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    status: Literal["ready", "needs_input", "risk"]
    reason: str = Field(min_length=1)


class ItReadinessSummary(ApiModel):
    label: str = Field(min_length=1)
    score: int = Field(ge=0, le=100)
    confidence: Literal["Low", "Medium", "High"]
    checklist: list[ItReadinessCheck] = Field(min_length=1)


class SadPreviewSection(ApiModel):
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    source_references: list[str] = Field(default_factory=list)


class SadPreviewChangeTracking(ApiModel):
    summary: str = Field(min_length=1)
    paths: list[str] = Field(default_factory=list)


class SadPreviewResponse(ApiModel):
    title: str = Field(min_length=1)
    temporary_notice: str = Field(min_length=1)
    it_readiness: ItReadinessSummary
    sections: list[SadPreviewSection] = Field(min_length=1)
    assumptions: list[str]
    open_questions: list[str]
    source_references: list[str]
    change_tracking: SadPreviewChangeTracking


class SadPreviewRequest(ApiModel):
    requirement_text: str = Field(min_length=5)
    analysis_id: str | None = None
    analysis: RequirementAnalysisResponse
    source_context: str | None = None
    source_references: list[str] = Field(default_factory=list)


class SadPreviewRecord(ApiModel):
    preview_id: str
    analysis_id: str | None = None
    requirement_text: str
    preview: SadPreviewResponse
    created_at: datetime


class SadPreviewApiResponse(ApiModel):
    preview_id: str
    saved: bool
    preview: SadPreviewResponse


class TraceabilityUnit(ApiModel):
    unit_type: str = Field(min_length=1)
    unit_name: str | None = None
    columns: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceRecord(ApiModel):
    source_id: str
    source_item_id: str
    source_type: str
    original_file_name: str
    mime_type: str | None = None
    file_size_bytes: int
    drive_file_id: str | None = None
    extraction_status: Literal["extracted"]
    extracted_text_preview: str
    extracted_text: str
    extraction_summary: str
    traceability_units: list[TraceabilityUnit]
    created_at: datetime
    updated_at: datetime


class SourceUploadError(ApiModel):
    filename: str
    message: str


class SourceUploadResponse(ApiModel):
    sources: list[SourceRecord]
    errors: list[SourceUploadError]
    analysis_context: str


class DriveRepoFolder(ApiModel):
    name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)


class DriveRepoConnectRequest(ApiModel):
    project_id: str = Field(min_length=1)
    authorization_code: str = Field(min_length=1)
    repo_folder_id: str | None = None
    repo_folder_name: str = Field(min_length=1)
    create_new_repo: bool = False


class DriveRepoRecord(ApiModel):
    grant_id: str
    project_id: str
    owner_uid: str
    owner_email: str | None = None
    status: Literal["connected", "disconnected"]
    repo_folder_id: str
    repo_folder_name: str
    repo_url: str
    requested_scopes: list[str]
    folder_structure: list[DriveRepoFolder]
    token_store: Literal["local_metadata_only", "secret_manager_pending"]
    saves_blocked: bool
    created_at: datetime
    updated_at: datetime
    disconnected_at: datetime | None = None


class DriveRepoDisconnectResponse(ApiModel):
    status: Literal["disconnected"]
    saves_blocked: bool
    repo: DriveRepoRecord | None = None
