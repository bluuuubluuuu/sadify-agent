export type AuthenticatedUser = {
  uid: string;
  email: string | null;
  display_name: string | null;
  provider: string;
};

export type AuthSessionResponse = {
  status: "authenticated";
  user: AuthenticatedUser;
};

export type ModelCatalogItem = {
  id: string;
  label: string;
  description: string;
  hint: string;
};

export type ModelCatalogResponse = {
  default: string;
  models: ModelCatalogItem[];
};

export type GuestDraftRecord = {
  guest_draft_id: string;
  owner_kind: "guest";
  guest_session_id: string;
  status: "active" | "migrated" | "abandoned";
  requirement_text: string | null;
  migrated_to_project_id: string | null;
  created_at: string;
  updated_at: string;
};

export type SignedInProjectRecord = {
  project_id: string;
  owner_kind: "signed_in";
  owner_uid: string;
  owner_email: string | null;
  source_guest_draft_id: string;
  requirement_text: string | null;
  status: "active";
  created_at: string;
  updated_at: string;
};

export type GuestDraftMigrationResponse = {
  status: "copied";
  guest_draft: GuestDraftRecord;
  project: SignedInProjectRecord;
  message: string;
};

export type RequirementAnalysis = {
  understanding_summary: string;
  readiness: {
    label: string;
    score: number;
    confidence: "Low" | "Medium" | "High";
  };
  categories: Array<{
    id: string;
    label: string;
    status: "complete" | "partial" | "missing";
  }>;
  next_question: {
    text: string;
    why_this_matters: string;
    choices: Array<{
      id: string;
      label: string;
      is_disabled: boolean;
      status_label: string;
    }>;
    target_category: string;
    target_slot_id: string;
    selection_mode: "single" | "multiple";
  };
  questionnaire: {
    draft_readiness: {
      label: string;
      score: number;
      confidence: "Low" | "Medium" | "High";
    };
    active_category_id: string;
    active_slot_id: string | null;
    active_slot_label: string | null;
    categories: Array<{
      id: string;
      label: string;
      status: "ready" | "in_progress" | "needed" | "needs_later_confirmation";
      visibility:
        | "main"
        | "already_understood"
        | "completed"
        | "suggested"
        | "not_applicable";
      progress: number;
      questions_total: number;
      questions_answered: number;
      is_active: boolean;
    }>;
    answers: Array<{
      category_id: string;
      slot_id: string | null;
      question: string;
      answer: string;
      is_uncertain: boolean;
    }>;
    diagnostics: string[];
  } | null;
  assumptions: string[];
  source_references: string[];
  proposed_extra_categories: Array<{
    id: string;
    label: string;
    reason: string;
  }>;
};

export type RequirementAnalysisApiResponse = {
  analysis_id: string;
  saved: boolean;
  analysis: RequirementAnalysis;
};

export type ProjectSessionSnapshot = {
  clean_requirement_text: string;
  analysis_response: RequirementAnalysisApiResponse | null;
  answer_history: string[];
  source_context: string;
  source_references: string[];
  selected_model: string | null;
  status: "in_progress";
  updated_at?: string | null;
};

export type ItReadinessCheck = {
  id: string;
  label: string;
  status: "ready" | "needs_input" | "risk";
  reason: string;
};

export type SadPreviewResponse = {
  title: string;
  temporary_notice: string;
  it_readiness: {
    label: string;
    score: number;
    confidence: "Low" | "Medium" | "High";
    checklist: ItReadinessCheck[];
  };
  sections: Array<{
    title: string;
    body: string;
    source_references: string[];
  }>;
  assumptions: string[];
  open_questions: string[];
  source_references: string[];
  change_tracking: {
    summary: string;
    paths: string[];
  };
};

export type SadPreviewApiResponse = {
  preview_id: string;
  saved: boolean;
  preview: SadPreviewResponse;
};

export type SadSaveArtifact = {
  artifact_id: string;
  artifact_type: "google_doc" | "manifest" | "change_log" | "source_reference";
  title: string;
  path: string;
  file_id: string | null;
  url: string | null;
  mime_type: string | null;
  source_ids: string[];
  created_at: string;
};

export type SadSaveManifest = {
  manifest_id: string;
  repo_grant_id: string;
  repo_folder_id: string;
  repo_folder_name: string;
  preview_id: string;
  preview_revision: string;
  analysis_id: string | null;
  requirement_text: string;
  sad_title: string;
  preview_section_count: number;
  preview_assumption_count: number;
  preview_open_question_count: number;
  preview_source_references: string[];
  source_ids: string[];
  artifact_paths: string[];
  saved_at: string;
};

export type SadSaveRecord = {
  save_id: string;
  idempotency_key: string;
  owner_uid: string;
  owner_email: string | null;
  project_id: string;
  repo_grant_id: string;
  repo_folder_id: string;
  repo_folder_name: string;
  preview_id: string;
  preview_revision: string;
  status: "saved";
  sad_doc: SadSaveArtifact;
  artifacts: SadSaveArtifact[];
  manifest: SadSaveManifest;
  change_summary: string;
  source_artifact_references: SadSaveArtifact[];
  created_at: string;
  updated_at: string;
};

export type SadSaveApiResponse = {
  saved: boolean;
  record: SadSaveRecord;
  message: string;
};

export type WikiFileCategory =
  | "index"
  | "requirements"
  | "actors"
  | "workflows"
  | "entities"
  | "decisions"
  | "reports"
  | "sources";

export type WikiFilePreview = {
  relative_path: string;
  name: string;
  category: WikiFileCategory;
  proposed_markdown: string;
  remote_hash: string | null;
  last_known_hash: string | null;
  remote_exists: boolean;
  requires_confirmation: boolean;
  remote_markdown: string | null;
};

export type WikiFileResult = {
  relative_path: string;
  name: string;
  category: WikiFileCategory;
  file_id: string;
  web_view_link: string;
  hash: string;
  created_new_file: boolean;
};

export type WikiBackupInfo = {
  created: boolean;
  path: string;
  file_count: number;
};

export type WikiPreviewResponse = {
  files: WikiFilePreview[];
  requires_confirmation: boolean;
  changed_files: string[];
  first_time_write: boolean;
};

export type WikiUpdateResponse = {
  files: WikiFileResult[];
  backup: WikiBackupInfo;
  updated_at: string;
};

export type TraceabilityUnit = {
  unit_type: string;
  unit_name: string | null;
  columns: string[];
  metadata: Record<string, unknown>;
};

export type SourceRecord = {
  source_id: string;
  source_item_id: string;
  source_type: string;
  original_file_name: string;
  mime_type: string | null;
  file_size_bytes: number;
  drive_file_id: string | null;
  extraction_status: "extracted";
  extracted_text_preview: string;
  extracted_text: string;
  extraction_summary: string;
  traceability_units: TraceabilityUnit[];
  created_at: string;
  updated_at: string;
};

export type SourceUploadResponse = {
  sources: SourceRecord[];
  errors: Array<{
    filename: string;
    message: string;
  }>;
  analysis_context: string;
};

export type ProjectSummary = {
  project_id: string;
  name: string;
  drive_folder_id: string;
  created_at: string;
  github_repo?: string | null;
};

export type ProjectListResponse = {
  active_project_id: string | null;
  active_project_name: string | null;
  projects: ProjectSummary[];
};

export type CreateProjectResponse = {
  project: ProjectSummary;
  active_project_id: string;
};

export type SwitchProjectResponse = {
  active_project_id: string;
  active_project_name: string;
};

export type SadSaveSummary = {
  save_id: string;
  preview_id: string;
  doc_url: string | null;
  doc_path: string;
  title: string;
  change_summary: string;
  source_ids: string[];
  created_at: string;
};

export type ProjectSavesResponse = {
  project_id: string;
  project_name: string;
  saves: SadSaveSummary[];
};

export type DriveRepoRecord = {
  grant_id: string;
  project_id: string;
  owner_uid: string;
  owner_email: string | null;
  status: "connected" | "disconnected";
  repo_folder_id: string;
  repo_folder_name: string;
  repo_url: string;
  requested_scopes: string[];
  folder_structure: Array<{
    name: string;
    purpose: string;
  }>;
  token_store:
    | "local_metadata_only"
    | "secret_manager_pending"
    | "secret_manager";
  saves_blocked: boolean;
  active_project_id: string | null;
  active_project_name: string | null;
  available_projects: ProjectSummary[];
  created_at: string;
  updated_at: string;
  disconnected_at: string | null;
};

export type DriveRepoDisconnectResponse = {
  status: "disconnected";
  saves_blocked: boolean;
  repo: DriveRepoRecord | null;
};

export type AgentEvent = {
  type: "tool" | "message" | "status";
  tool: string | null;
  summary: string;
  reasoning: string | null;
};

export type AgentGithubIssue = {
  title: string;
  body: string;
  labels?: string[];
};

export type AgentProposedAction = {
  id: string;
  label: string;
  preview_id?: string;
  changed_files?: string[];
  repo?: string;
  issue_count?: number;
  issues?: AgentGithubIssue[];
};

export type AgentFinalizeStatus =
  | "asked_clarification"
  | "awaiting_approval"
  | "completed";

export type AgentFinalizeApiResponse = {
  status: AgentFinalizeStatus;
  events: AgentEvent[];
  result: Record<string, unknown> | null;
};

const baseUrl = process.env.NEXT_PUBLIC_SADIFY_API_BASE_URL ?? "http://localhost:8000";

export class BackendApiError extends Error {
  code: string | null;
  status: number;

  constructor(message: string, code: string | null, status: number) {
    super(message);
    this.name = "BackendApiError";
    this.code = code;
    this.status = status;
  }
}

async function readBackendError(
  response: Response,
  fallbackMessage: string,
): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.trim()) {
      return payload.detail;
    }
    if (
      payload.detail &&
      typeof payload.detail === "object" &&
      "message" in payload.detail &&
      typeof payload.detail.message === "string"
    ) {
      return payload.detail.message;
    }
  } catch {
    return fallbackMessage;
  }
  return fallbackMessage;
}

async function readBackendErrorDetail(
  response: Response,
  fallbackMessage: string,
): Promise<{ message: string; code: string | null }> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.trim()) {
      return { message: payload.detail, code: null };
    }
    if (payload.detail && typeof payload.detail === "object") {
      const detail = payload.detail as { message?: unknown; code?: unknown };
      return {
        message:
          typeof detail.message === "string" && detail.message.trim()
            ? detail.message
            : fallbackMessage,
        code: typeof detail.code === "string" ? detail.code : null,
      };
    }
  } catch {
    return { message: fallbackMessage, code: null };
  }
  return { message: fallbackMessage, code: null };
}

export async function verifyAuthSession(idToken: string): Promise<AuthSessionResponse> {
  const response = await fetch(`${baseUrl}/auth/session`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${idToken}`,
    },
  });

  if (!response.ok) {
    throw new Error(await readBackendError(response, "Backend could not verify this session."));
  }

  return response.json();
}

export async function listModels(): Promise<ModelCatalogResponse> {
  const response = await fetch(`${baseUrl}/models`);

  if (!response.ok) {
    throw new Error("Could not load the available AI models.");
  }

  return response.json();
}

export async function createGuestDraft(input: {
  guestSessionId: string;
  requirementText?: string;
}): Promise<GuestDraftRecord> {
  const response = await fetch(`${baseUrl}/drafts/guest`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      guest_session_id: input.guestSessionId,
      requirement_text: input.requirementText || null,
    }),
  });

  if (!response.ok) {
    throw new Error("Could not create this guest draft.");
  }

  return response.json();
}

export async function migrateGuestDraft(
  guestDraftId: string,
  idToken: string,
): Promise<GuestDraftMigrationResponse> {
  const response = await fetch(`${baseUrl}/drafts/guest/${guestDraftId}/migrate`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${idToken}`,
    },
  });

  if (!response.ok) {
    throw new Error("Could not copy this guest draft to your signed-in project.");
  }

  return response.json();
}

export async function analyzeRequirement(input: {
  requirementText: string;
  guestDraftId?: string;
  analysisSessionId?: string;
  sourceContext?: string;
  sourceReferences?: string[];
  model?: string;
}): Promise<RequirementAnalysisApiResponse> {
  const response = await fetch(`${baseUrl}/analysis/requirement`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      requirement_text: input.requirementText,
      guest_draft_id: input.guestDraftId ?? null,
      analysis_session_id: input.analysisSessionId ?? null,
      source_context: input.sourceContext ?? null,
      source_references: input.sourceReferences ?? [],
      model: input.model ?? null,
    }),
  });

  if (!response.ok) {
    throw new Error(
      await readBackendError(
        response,
        "SADify could not generate a validated question yet.",
      ),
    );
  }

  return response.json();
}

export async function generateSadPreview(input: {
  requirementText: string;
  analysisId?: string;
  analysis: RequirementAnalysis;
  sourceContext?: string;
  sourceReferences?: string[];
  model?: string;
}): Promise<SadPreviewApiResponse> {
  const response = await fetch(`${baseUrl}/sad/preview`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      requirement_text: input.requirementText,
      analysis_id: input.analysisId ?? null,
      analysis: input.analysis,
      source_context: input.sourceContext ?? null,
      source_references: input.sourceReferences ?? [],
      model: input.model ?? null,
    }),
  });

  if (response.status === 409) {
    throw new Error(
      await readBackendError(
        response,
        "Answer the blocking basics before generating a SAD preview.",
      ),
    );
  }

  if (!response.ok) {
    throw new Error(
      await readBackendError(response, "SADify could not generate the SAD preview yet."),
    );
  }

  return response.json();
}

export async function saveSadPreview(
  previewId: string,
  idToken: string,
): Promise<SadSaveApiResponse> {
  const response = await fetch(`${baseUrl}/sad/save`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${idToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      preview_id: previewId,
    }),
  });

  if (!response.ok) {
    const detail = await readBackendErrorDetail(
      response,
      "SADify could not save this SAD preview yet.",
    );
    throw new BackendApiError(detail.message, detail.code, response.status);
  }

  return response.json();
}

export async function previewWikiUpdate(
  idToken: string,
): Promise<WikiPreviewResponse> {
  const response = await fetch(`${baseUrl}/sad/wiki/preview`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${idToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({}),
  });

  if (!response.ok) {
    const detail = await readBackendErrorDetail(
      response,
      "SADify could not prepare the wiki update yet.",
    );
    throw new BackendApiError(detail.message, detail.code, response.status);
  }

  return response.json();
}

export async function commitWikiUpdate(
  idToken: string,
  expectedRemoteHashes: Record<string, string | null>,
  forceOverwrite: boolean,
): Promise<WikiUpdateResponse> {
  const response = await fetch(`${baseUrl}/sad/wiki/update`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${idToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      expected_remote_hashes: expectedRemoteHashes,
      force_overwrite: forceOverwrite,
    }),
  });

  if (!response.ok) {
    const detail = await readBackendErrorDetail(
      response,
      "SADify could not update the wiki yet.",
    );
    throw new BackendApiError(detail.message, detail.code, response.status);
  }

  return response.json();
}

export async function uploadSources(files: File[]): Promise<SourceUploadResponse> {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });

  const response = await fetch(`${baseUrl}/sources/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("SADify could not read these source files yet.");
  }

  return response.json();
}

export async function connectDriveRepo(input: {
  idToken: string;
  projectId: string;
  authorizationCode: string;
  repoFolderName: string;
  repoFolderId?: string;
  createNewRepo?: boolean;
}): Promise<DriveRepoRecord> {
  const response = await fetch(`${baseUrl}/drive/repo/connect`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${input.idToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      project_id: input.projectId,
      authorization_code: input.authorizationCode,
      repo_folder_id: input.repoFolderId ?? null,
      repo_folder_name: input.repoFolderName,
      create_new_repo: input.createNewRepo ?? false,
    }),
  });

  if (!response.ok) {
    throw new Error("Could not connect this Google Drive project repo.");
  }

  return response.json();
}

export async function getDriveRepoStatus(
  idToken: string,
): Promise<DriveRepoRecord | null> {
  const response = await fetch(`${baseUrl}/drive/repo/status`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${idToken}`,
    },
  });

  if (!response.ok) {
    throw new Error("Could not load the current Drive repo status.");
  }

  return response.json();
}

export async function listProjects(idToken: string): Promise<ProjectListResponse> {
  const response = await fetch(`${baseUrl}/projects`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${idToken}`,
    },
  });

  if (!response.ok) {
    const detail = await readBackendErrorDetail(
      response,
      "Could not load projects for this repo.",
    );
    throw new BackendApiError(detail.message, detail.code, response.status);
  }

  return response.json();
}

export async function createProject(
  idToken: string,
  name: string,
): Promise<CreateProjectResponse> {
  const response = await fetch(`${baseUrl}/projects`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${idToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name }),
  });

  if (!response.ok) {
    const detail = await readBackendErrorDetail(
      response,
      "Could not create this project.",
    );
    throw new BackendApiError(detail.message, detail.code, response.status);
  }

  return response.json();
}

export async function switchProject(
  idToken: string,
  projectId: string,
): Promise<SwitchProjectResponse> {
  const response = await fetch(`${baseUrl}/projects/switch`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${idToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      project_id: projectId,
    }),
  });

  if (!response.ok) {
    const detail = await readBackendErrorDetail(
      response,
      "Could not switch projects.",
    );
    throw new BackendApiError(detail.message, detail.code, response.status);
  }

  return response.json();
}

export async function deleteProject(
  idToken: string,
  projectId: string,
): Promise<ProjectListResponse> {
  const response = await fetch(
    `${baseUrl}/projects/${encodeURIComponent(projectId)}`,
    {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${idToken}`,
      },
    },
  );

  if (!response.ok) {
    const detail = await readBackendErrorDetail(
      response,
      "Could not delete this project.",
    );
    throw new BackendApiError(detail.message, detail.code, response.status);
  }

  return response.json();
}

export async function putProjectSession(
  idToken: string,
  projectId: string,
  snapshot: ProjectSessionSnapshot,
): Promise<void> {
  const response = await fetch(
    `${baseUrl}/projects/${encodeURIComponent(projectId)}/session`,
    {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${idToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(snapshot),
    },
  );

  if (!response.ok) {
    const detail = await readBackendErrorDetail(
      response,
      "Could not save this project session.",
    );
    throw new BackendApiError(detail.message, detail.code, response.status);
  }
}

export async function getProjectSession(
  idToken: string,
  projectId: string,
): Promise<ProjectSessionSnapshot | null> {
  const response = await fetch(
    `${baseUrl}/projects/${encodeURIComponent(projectId)}/session`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${idToken}`,
      },
    },
  );

  if (response.status === 204) {
    return null;
  }
  if (!response.ok) {
    const detail = await readBackendErrorDetail(
      response,
      "Could not restore this project session.",
    );
    throw new BackendApiError(detail.message, detail.code, response.status);
  }
  return response.json();
}

export async function setProjectGithubRepo(
  idToken: string,
  projectId: string,
  repo: string,
): Promise<ProjectSummary> {
  const response = await fetch(
    `${baseUrl}/projects/${encodeURIComponent(projectId)}/github`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${idToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ repo }),
    },
  );

  if (!response.ok) {
    const detail = await readBackendErrorDetail(
      response,
      "Could not link the GitHub repository.",
    );
    throw new BackendApiError(detail.message, detail.code, response.status);
  }

  return response.json();
}

export async function listProjectSaves(
  idToken: string,
  projectId: string,
): Promise<ProjectSavesResponse> {
  const response = await fetch(`${baseUrl}/projects/${projectId}/saves`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${idToken}`,
    },
  });

  if (!response.ok) {
    const detail = await readBackendErrorDetail(
      response,
      "Could not load saved SAD history for this project.",
    );
    throw new BackendApiError(detail.message, detail.code, response.status);
  }

  return response.json();
}

export async function streamAgentFinalize(
  input: { analysisSessionId: string; model?: string },
  onEvent: (event: AgentEvent & { status?: AgentFinalizeStatus; result?: Record<string, unknown> | null }) => void,
): Promise<void> {
  const response = await fetch(`${baseUrl}/agent/finalize/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      analysis_session_id: input.analysisSessionId,
      model: input.model ?? null,
    }),
  });

  if (!response.ok || !response.body) {
    throw new Error(
      await readBackendError(response, "SADify agent could not finalize this draft yet."),
    );
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const flush = (chunk: string) => {
    const line = chunk.trim();
    if (line) {
      onEvent(JSON.parse(line));
    }
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    let newlineIndex = buffer.indexOf("\n");
    while (newlineIndex >= 0) {
      flush(buffer.slice(0, newlineIndex));
      buffer = buffer.slice(newlineIndex + 1);
      newlineIndex = buffer.indexOf("\n");
    }
  }
  flush(buffer);
}

export async function approveAgentActions(
  input: { analysisSessionId: string; approvalId: string; model?: string },
  idToken: string,
): Promise<AgentFinalizeApiResponse> {
  const response = await fetch(`${baseUrl}/agent/approve`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${idToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      analysis_session_id: input.analysisSessionId,
      approval_id: input.approvalId,
      model: input.model ?? null,
    }),
  });

  if (!response.ok) {
    const detail = await readBackendErrorDetail(
      response,
      "SADify agent could not run the approved save yet.",
    );
    throw new BackendApiError(detail.message, detail.code, response.status);
  }

  return response.json();
}

export async function prepareAgentGithubIssues(input: {
  analysisSessionId: string;
  previewId: string;
  repo?: string;
  model?: string;
}): Promise<AgentFinalizeApiResponse> {
  const response = await fetch(`${baseUrl}/agent/github/issues/prepare`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      analysis_session_id: input.analysisSessionId,
      preview_id: input.previewId,
      repo: input.repo ?? null,
      model: input.model ?? null,
    }),
  });

  if (!response.ok) {
    const detail = await readBackendErrorDetail(
      response,
      "SADify agent could not prepare GitHub issues yet.",
    );
    throw new BackendApiError(detail.message, detail.code, response.status);
  }

  return response.json();
}

export async function approveAgentGithubIssues(
  input: {
    analysisSessionId: string;
    approvalId: string;
    githubToken?: string;
    model?: string;
  },
  idToken: string,
): Promise<AgentFinalizeApiResponse> {
  const response = await fetch(`${baseUrl}/agent/github/issues/approve`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${idToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      analysis_session_id: input.analysisSessionId,
      approval_id: input.approvalId,
      github_token: input.githubToken ?? null,
      model: input.model ?? null,
    }),
  });

  if (!response.ok) {
    const detail = await readBackendErrorDetail(
      response,
      "SADify agent could not create GitHub issues yet.",
    );
    throw new BackendApiError(detail.message, detail.code, response.status);
  }

  return response.json();
}

export async function disconnectDriveRepo(
  idToken: string,
): Promise<DriveRepoDisconnectResponse> {
  const response = await fetch(`${baseUrl}/drive/repo/disconnect`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${idToken}`,
    },
  });

  if (!response.ok) {
    throw new Error("Could not disconnect Google Drive.");
  }

  return response.json();
}
