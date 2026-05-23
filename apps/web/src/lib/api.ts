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
  token_store: "local_metadata_only" | "secret_manager_pending";
  saves_blocked: boolean;
  created_at: string;
  updated_at: string;
  disconnected_at: string | null;
};

export type DriveRepoDisconnectResponse = {
  status: "disconnected";
  saves_blocked: boolean;
  repo: DriveRepoRecord | null;
};

const baseUrl = process.env.NEXT_PUBLIC_SADIFY_API_BASE_URL ?? "http://localhost:8000";

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
  sourceContext?: string;
  sourceReferences?: string[];
}): Promise<RequirementAnalysisApiResponse> {
  const response = await fetch(`${baseUrl}/analysis/requirement`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      requirement_text: input.requirementText,
      guest_draft_id: input.guestDraftId ?? null,
      source_context: input.sourceContext ?? null,
      source_references: input.sourceReferences ?? [],
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
