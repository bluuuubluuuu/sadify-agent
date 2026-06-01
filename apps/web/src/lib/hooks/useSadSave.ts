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
} from "../api";
import { getFirebaseAuth } from "../firebaseClient";
import { isGoogleOAuthConfigured } from "../googleOAuth";

type PendingProjectAction = "save" | "wiki" | null;

function expectedRemoteHashes(response: WikiPreviewResponse): Record<string, string | null> {
  return Object.fromEntries(response.files.map((file) => [file.name, file.remote_hash]));
}

function isProjectRequiredError(error: unknown) {
  return (
    error instanceof BackendApiError &&
    (error.code === "PROJECT_REQUIRED" || error.code === "WIKI_PROJECT_REQUIRED")
  );
}

/**
 * Preview / save / wiki / project-required engine extracted from SadPreviewPanel
 * with identical API calls, error-code handling, and pending-action retry.
 */
export function useSadSave({
  requirementText,
  analysisResponse,
  sourceContext = "",
  sourceReferences = [],
  onProjectCreated,
  onHistoryRefresh,
}: {
  requirementText: string;
  analysisResponse: RequirementAnalysisApiResponse | null;
  sourceContext?: string;
  sourceReferences?: string[];
  onProjectCreated?: (response: CreateProjectResponse) => void;
  onHistoryRefresh?: () => void;
}) {
  const [previewResponse, setPreviewResponse] = useState<SadPreviewApiResponse | null>(null);
  const [saveResponse, setSaveResponse] = useState<SadSaveApiResponse | null>(null);
  const [wikiPreviewResponse, setWikiPreviewResponse] = useState<WikiPreviewResponse | null>(null);
  const [wikiUpdateResponse, setWikiUpdateResponse] = useState<WikiUpdateResponse | null>(null);
  const [wikiDialogOpen, setWikiDialogOpen] = useState(false);
  const [projectDialogOpen, setProjectDialogOpen] = useState(false);
  const [pendingProjectAction, setPendingProjectAction] = useState<PendingProjectAction>(null);
  const [message, setMessage] = useState("");
  const [saveMessage, setSaveMessage] = useState("");
  const [wikiMessage, setWikiMessage] = useState("");
  const [generating, setGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isWikiBusy, setIsWikiBusy] = useState(false);
  const [isProjectBusy, setIsProjectBusy] = useState(false);

  const analysisId = analysisResponse?.analysis_id;

  // Reset preview/save/wiki when the underlying analysis changes (refine in chat).
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
    setMessage("");
  }, [analysisId, requirementText]);

  function suggestProjectName() {
    const fromPreview = previewResponse?.preview.title.trim();
    if (fromPreview) {
      return fromPreview.slice(0, 80);
    }
    const cleaned = requirementText.replace(/\s+/g, " ").trim();
    return cleaned ? cleaned.slice(0, 60) : "Untitled Project";
  }

  async function generate() {
    if (!analysisResponse) {
      setMessage("Start analysis first, then generate a SAD preview.");
      return;
    }
    setGenerating(true);
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
      setMessage(`Temporary preview ${response.preview_id} saved in backend state.`);
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "SADify could not generate the SAD preview yet.",
      );
    } finally {
      setGenerating(false);
    }
  }

  async function save(skipProjectDialog = false) {
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
      onHistoryRefresh?.();
      setSaveMessage("Saved to project repo.");
    } catch (error) {
      if (!skipProjectDialog && isProjectRequiredError(error)) {
        setPendingProjectAction("save");
        setProjectDialogOpen(true);
        setSaveMessage("Create a project before saving this SAD preview.");
        return;
      }
      setSaveMessage(
        error instanceof Error ? error.message : "SADify could not save this SAD preview yet.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  async function updateWiki(skipProjectDialog = false) {
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
        setPendingProjectAction("wiki");
        setProjectDialogOpen(true);
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

  async function confirmWiki(forceOverwrite: boolean) {
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
        setPendingProjectAction("wiki");
        setProjectDialogOpen(true);
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

  async function createProjectForPending(name: string) {
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
      if (action === "save") {
        await save(true);
      } else if (action === "wiki") {
        await updateWiki(true);
      }
    } catch (error) {
      setSaveMessage(error instanceof Error ? error.message : "Could not create this project.");
    } finally {
      setIsProjectBusy(false);
    }
  }

  function dismissPreview() {
    setPreviewResponse(null);
    setSaveResponse(null);
    setWikiPreviewResponse(null);
    setWikiUpdateResponse(null);
    setWikiDialogOpen(false);
    setSaveMessage("");
    setWikiMessage("");
  }

  const canUpdateWiki = Boolean(saveResponse) && isGoogleOAuthConfigured();

  return {
    dismissPreview,
    preview: previewResponse?.preview ?? null,
    previewId: previewResponse?.preview_id ?? null,
    hasPreview: Boolean(previewResponse),
    record: saveResponse?.record ?? null,
    wikiRecord: wikiUpdateResponse,
    wikiPreview: wikiPreviewResponse,
    canUpdateWiki,
    message,
    saveMessage,
    wikiMessage,
    generating,
    isSaving,
    isWikiBusy,
    isProjectBusy,
    wikiDialogOpen,
    projectDialogOpen,
    suggestProjectName,
    generate,
    save,
    updateWiki,
    confirmWiki,
    createProjectForPending,
    cancelWiki: () => {
      setWikiDialogOpen(false);
      setWikiMessage("Wiki update canceled.");
    },
    cancelProject: () => {
      setProjectDialogOpen(false);
      setPendingProjectAction(null);
      setSaveMessage("Project creation canceled.");
    },
  };
}
