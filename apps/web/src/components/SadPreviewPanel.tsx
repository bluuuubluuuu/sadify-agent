"use client";

import { useEffect, useState } from "react";
import {
  BackendApiError,
  commitWikiUpdate,
  createProject,
  generateSadPreview,
  previewWikiUpdate,
  saveSadPreview,
  type CreateProjectResponse,
  type RequirementAnalysisApiResponse,
  type SadPreviewApiResponse,
  type SadSaveApiResponse,
  type WikiPreviewResponse,
  type WikiUpdateResponse,
} from "../lib/api";
import { getFirebaseAuth } from "../lib/firebaseClient";
import { isGoogleOAuthConfigured } from "../lib/googleOAuth";
import { CreateProjectDialog } from "./CreateProjectDialog";
import { WikiUpdateDialog } from "./WikiUpdateDialog";

type Props = {
  analysisResponse: RequirementAnalysisApiResponse | null;
  requirementText: string;
  sourceContext?: string;
  sourceReferences?: string[];
  onPreviewSaved: (response: SadPreviewApiResponse) => void;
  onSadSaved: (response: SadSaveApiResponse) => void;
  onProjectCreated?: (response: CreateProjectResponse) => void;
};

type PendingProjectAction = "save" | "wiki" | null;

const readinessLabel: Record<string, string> = {
  ready: "Ready",
  needs_input: "Needs input",
  risk: "Risk",
};

function expectedRemoteHashes(
  response: WikiPreviewResponse,
): Record<string, string | null> {
  return Object.fromEntries(
    response.files.map((file) => [file.name, file.remote_hash]),
  );
}

export function SadPreviewPanel({
  analysisResponse,
  requirementText,
  sourceContext = "",
  sourceReferences = [],
  onPreviewSaved,
  onSadSaved,
  onProjectCreated,
}: Props) {
  const [previewResponse, setPreviewResponse] =
    useState<SadPreviewApiResponse | null>(null);
  const [saveResponse, setSaveResponse] = useState<SadSaveApiResponse | null>(null);
  const [wikiPreviewResponse, setWikiPreviewResponse] =
    useState<WikiPreviewResponse | null>(null);
  const [wikiUpdateResponse, setWikiUpdateResponse] =
    useState<WikiUpdateResponse | null>(null);
  const [wikiDialogOpen, setWikiDialogOpen] = useState(false);
  const [projectDialogOpen, setProjectDialogOpen] = useState(false);
  const [message, setMessage] = useState(
    "Temporary preview only. No Google Doc or Drive file is saved here.",
  );
  const [saveMessage, setSaveMessage] = useState("");
  const [wikiMessage, setWikiMessage] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isWikiBusy, setIsWikiBusy] = useState(false);
  const [isProjectBusy, setIsProjectBusy] = useState(false);
  const [pendingProjectAction, setPendingProjectAction] =
    useState<PendingProjectAction>(null);
  const analysisId = analysisResponse?.analysis_id;

  useEffect(() => {
    setPreviewResponse(null);
    setSaveResponse(null);
    setWikiPreviewResponse(null);
    setWikiUpdateResponse(null);
    setWikiDialogOpen(false);
    setProjectDialogOpen(false);
    setPendingProjectAction(null);
    setSaveMessage("");
    setWikiMessage("");
    setMessage("Temporary preview only. No Google Doc or Drive file is saved here.");
  }, [analysisId, requirementText]);

  function suggestProjectName() {
    const fromPreview = previewResponse?.preview.title.trim();
    if (fromPreview) {
      return fromPreview.slice(0, 80);
    }
    const cleaned = requirementText.replace(/\s+/g, " ").trim();
    if (cleaned) {
      return cleaned.slice(0, 60);
    }
    return "Untitled Project";
  }

  function isProjectRequiredError(error: unknown) {
    return (
      error instanceof BackendApiError &&
      (error.code === "PROJECT_REQUIRED" ||
        error.code === "WIKI_PROJECT_REQUIRED")
    );
  }

  function openProjectDialogFor(action: PendingProjectAction) {
    setPendingProjectAction(action);
    setProjectDialogOpen(true);
  }

  async function retryPendingProjectAction(action: PendingProjectAction) {
    if (action === "save") {
      await savePreviewToProjectRepo(true);
      return;
    }
    if (action === "wiki") {
      await prepareWikiUpdate(true);
    }
  }

  async function createProjectForPendingAction(name: string) {
    const user = getFirebaseAuth().currentUser;
    if (!user) {
      setSaveMessage("Sign in before creating a project.");
      return;
    }
    const action = pendingProjectAction;
    setIsProjectBusy(true);
    setSaveMessage("Creating project folder...");
    try {
      const idToken = await user.getIdToken();
      const response = await createProject(idToken, name);
      onProjectCreated?.(response);
      setProjectDialogOpen(false);
      setPendingProjectAction(null);
      setSaveMessage("Project created. Retrying the requested save action.");
      await retryPendingProjectAction(action);
    } catch (error) {
      setSaveMessage(
        error instanceof Error ? error.message : "Could not create this project.",
      );
    } finally {
      setIsProjectBusy(false);
    }
  }

  async function createPreview() {
    if (!analysisResponse) {
      setMessage("Start analysis first, then generate a SAD preview.");
      return;
    }

    setIsBusy(true);
    setMessage("Preparing temporary SAD preview...");
    try {
      const response = await generateSadPreview({
        requirementText,
        analysisId: analysisResponse.analysis_id,
        analysis: analysisResponse.analysis,
        sourceContext: sourceContext || undefined,
        sourceReferences,
      });
      setPreviewResponse(response);
      setSaveResponse(null);
      setWikiPreviewResponse(null);
      setWikiUpdateResponse(null);
      setWikiDialogOpen(false);
      setProjectDialogOpen(false);
      setPendingProjectAction(null);
      setSaveMessage("");
      setWikiMessage("");
      onPreviewSaved(response);
      setMessage(`Temporary preview ${response.preview_id} saved in backend state.`);
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "SADify could not generate the SAD preview yet.",
      );
    } finally {
      setIsBusy(false);
    }
  }

  async function savePreviewToProjectRepo(skipProjectDialog = false) {
    if (!previewResponse) {
      setSaveMessage("Generate a SAD preview before saving.");
      return;
    }
    const user = getFirebaseAuth().currentUser;
    if (!user) {
      setSaveMessage("Sign in before saving the SAD preview.");
      return;
    }

    setIsSaving(true);
    setSaveMessage("Saving SAD preview to project repo...");
    try {
      const idToken = await user.getIdToken();
      const response = await saveSadPreview(previewResponse.preview_id, idToken);
      setSaveResponse(response);
      setWikiPreviewResponse(null);
      setWikiUpdateResponse(null);
      setWikiDialogOpen(false);
      setWikiMessage("");
      onSadSaved(response);
      setSaveMessage("Saved to project repo.");
    } catch (error) {
      if (!skipProjectDialog && isProjectRequiredError(error)) {
        openProjectDialogFor("save");
        setSaveMessage("Create a project before saving this SAD preview.");
        return;
      }
      setSaveMessage(
        error instanceof Error
          ? error.message
          : "SADify could not save this SAD preview yet.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  async function prepareWikiUpdate(skipProjectDialog = false) {
    if (!saveResponse) {
      setWikiMessage("Save the SAD preview before updating the wiki.");
      return;
    }
    const user = getFirebaseAuth().currentUser;
    if (!user) {
      setWikiMessage("Sign in before updating the wiki.");
      return;
    }

    setIsWikiBusy(true);
    setWikiMessage("Checking the current Drive wiki...");
    try {
      const idToken = await user.getIdToken();
      const response = await previewWikiUpdate(idToken);
      setWikiPreviewResponse(response);
      if (response.requires_confirmation) {
        setWikiDialogOpen(true);
        setWikiMessage("Review the Drive wiki changes before overwriting.");
        return;
      }
      const update = await commitWikiUpdate(idToken, expectedRemoteHashes(response), false);
      setWikiUpdateResponse(update);
      setWikiDialogOpen(false);
      setWikiMessage("Wiki updated.");
    } catch (error) {
      if (!skipProjectDialog && isProjectRequiredError(error)) {
        openProjectDialogFor("wiki");
        setWikiMessage("Create a project before updating the wiki.");
        return;
      }
      setWikiMessage(
        error instanceof Error ? error.message : "SADify could not update the wiki yet.",
      );
    } finally {
      setIsWikiBusy(false);
    }
  }

  async function confirmWikiUpdate(forceOverwrite: boolean) {
    if (!wikiPreviewResponse) {
      setWikiDialogOpen(false);
      setWikiMessage("Prepare the wiki update again before confirming.");
      return;
    }
    const user = getFirebaseAuth().currentUser;
    if (!user) {
      setWikiMessage("Sign in before updating the wiki.");
      return;
    }

    setIsWikiBusy(true);
    setWikiMessage("Updating wiki files...");
    try {
      const idToken = await user.getIdToken();
      const update = await commitWikiUpdate(
        idToken,
        expectedRemoteHashes(wikiPreviewResponse),
        forceOverwrite,
      );
      setWikiUpdateResponse(update);
      setWikiDialogOpen(false);
      setWikiMessage("Wiki updated.");
    } catch (error) {
      if (isProjectRequiredError(error)) {
        openProjectDialogFor("wiki");
        setWikiMessage("Create a project before updating the wiki.");
        return;
      }
      setWikiMessage(
        error instanceof Error ? error.message : "SADify could not update the wiki yet.",
      );
    } finally {
      setIsWikiBusy(false);
    }
  }

  const preview = previewResponse?.preview;
  const record = saveResponse?.record;
  const wikiRecord = wikiUpdateResponse;
  const canUpdateWiki = saveResponse && isGoogleOAuthConfigured();
  const visibleTrackingPaths =
    preview?.change_tracking.paths.filter(
      (path) => !path.startsWith("_SADify/"),
    ) ?? [];
  const draftReadiness = analysisResponse?.analysis.questionnaire?.draft_readiness;
  const isDraftReadyPreview = (draftReadiness?.score ?? 0) >= 90;

  return (
    <section className="sad-preview-panel" aria-label="SAD preview and IT readiness">
      <div className="sad-preview-copy">
        <p className="eyebrow">SAD preview</p>
        <h2>Generate SAD preview</h2>
        <p>{message}</p>
      </div>

      <button
        type="button"
        className="primary-button"
        disabled={isBusy || !analysisResponse}
        onClick={createPreview}
      >
        Generate SAD preview
      </button>

      {previewResponse ? (
        <button
          type="button"
          className="secondary-button"
          disabled={isSaving}
          onClick={() => savePreviewToProjectRepo()}
        >
          Save to project repo
        </button>
      ) : null}

      {canUpdateWiki ? (
        <button
          type="button"
          className="secondary-button"
          disabled={isWikiBusy}
          onClick={() => prepareWikiUpdate()}
        >
          Update wiki
        </button>
      ) : null}

      {!analysisResponse ? (
        <small className="sad-preview-note">
          Start analysis before creating a temporary preview.
        </small>
      ) : null}

      {saveMessage ? (
        <small className="sad-preview-note">{saveMessage}</small>
      ) : null}

      {wikiMessage ? (
        <small className="sad-preview-note">{wikiMessage}</small>
      ) : null}

      {preview ? (
        <div className="sad-preview-result" aria-live="polite">
          <div className="sad-preview-title">
            <div>
              <p className="eyebrow">Temporary preview</p>
              <h3>{preview.title}</h3>
              <p>{preview.temporary_notice}</p>
            </div>
            <div className="it-score">
              {isDraftReadyPreview ? (
                <>
                  <span>Draft-ready</span>
                  <small>Layer 1 preview</small>
                </>
              ) : (
                <>
                  <span>{preview.it_readiness.score}%</span>
                  <small>{preview.it_readiness.confidence} confidence</small>
                </>
              )}
            </div>
          </div>

          {record ? (
            <div className="sad-save-result">
              <p className="eyebrow">Saved to project repo</p>
              <strong>{record.sad_doc.title}</strong>
              <p>{record.sad_doc.path}</p>
              {record.sad_doc.url ? (
                <a href={record.sad_doc.url}>{record.sad_doc.url}</a>
              ) : null}
              <p>{record.change_summary}</p>
            </div>
          ) : null}

          {wikiRecord ? (
            <div className="sad-save-result">
              <p className="eyebrow">Wiki updated</p>
              <strong>{wikiRecord.files.length} wiki files written</strong>
              <ul>
                {wikiRecord.files.map((file) => (
                  <li key={file.relative_path}>
                    <span>{file.relative_path}</span>
                    <small>{file.created_new_file ? "Created" : "Updated"}</small>
                    <a href={file.web_view_link}>{file.web_view_link}</a>
                    <p>{file.hash}</p>
                  </li>
                ))}
              </ul>
              {wikiRecord.backup.created ? (
                <p>Backup: {wikiRecord.backup.path}</p>
              ) : (
                <p>No backup needed.</p>
              )}
            </div>
          ) : null}

          <details className="it-readiness">
            <summary>Later implementation review</summary>
            <p>{preview.it_readiness.label}</p>
            <div className="it-checks">
              {preview.it_readiness.checklist.map((item) => (
                <article key={item.id}>
                  <strong>{item.label}</strong>
                  <small>{readinessLabel[item.status]}</small>
                  <p>{item.reason}</p>
                </article>
              ))}
            </div>
          </details>

          <div className="sad-section-list">
            {preview.sections.map((section) => (
              <article key={section.title}>
                <h4>{section.title}</h4>
                <p>{section.body}</p>
              </article>
            ))}
          </div>

          <div className="sad-preview-details">
            <details open>
              <summary>Assumptions</summary>
              <ul>
                {preview.assumptions.map((assumption) => (
                  <li key={assumption}>{assumption}</li>
                ))}
              </ul>
            </details>
            <details open>
              <summary>Open questions</summary>
              <ul>
                {preview.open_questions.map((question) => (
                  <li key={question}>{question}</li>
                ))}
              </ul>
            </details>
            <details>
              <summary>Source refs</summary>
              <p>
                {preview.source_references.length
                  ? preview.source_references.join(", ")
                  : "No source refs attached."}
              </p>
            </details>
            <details>
              <summary>Tracking status</summary>
              <p>{preview.change_tracking.summary}</p>
              <ul>
                {visibleTrackingPaths.length ? (
                  visibleTrackingPaths.map((path) => <li key={path}>{path}</li>)
                ) : (
                  <li>Temporary draft state saved.</li>
                )}
              </ul>
            </details>
          </div>
        </div>
      ) : null}

      {wikiDialogOpen && wikiPreviewResponse ? (
        <WikiUpdateDialog
          preview={wikiPreviewResponse}
          isBusy={isWikiBusy}
          onConfirm={confirmWikiUpdate}
          onCancel={() => {
            setWikiDialogOpen(false);
            setWikiMessage("Wiki update canceled.");
          }}
        />
      ) : null}

      {projectDialogOpen ? (
        <CreateProjectDialog
          suggestedName={suggestProjectName()}
          isBusy={isProjectBusy}
          onSubmit={createProjectForPendingAction}
          onCancel={() => {
            setProjectDialogOpen(false);
            setPendingProjectAction(null);
            setSaveMessage("Project creation canceled.");
          }}
        />
      ) : null}
    </section>
  );
}
