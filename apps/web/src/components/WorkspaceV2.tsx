"use client";

import { onAuthStateChanged } from "firebase/auth";
import { useEffect, useRef, useState } from "react";
import {
  deleteProject,
  getDriveRepoStatus,
  setProjectGithubRepo,
  type CreateProjectResponse,
  type DriveRepoRecord,
  type ModelCatalogResponse,
  type ProjectSessionSnapshot,
  type ProjectSummary,
  type SadSaveSummary,
  type SourceRecord,
} from "../lib/api";
import { getFirebaseAuth } from "../lib/firebaseClient";
import { isFirebaseConfigured } from "../lib/firebaseConfig";
import { deriveStage } from "../lib/stage";
import { useAuth } from "../lib/hooks/useAuth";
import { useDriveRepo } from "../lib/hooks/useDriveRepo";
import { useSources } from "../lib/hooks/useSources";
import { useQnA } from "../lib/hooks/useQnA";
import { useSadSave } from "../lib/hooks/useSadSave";
import { useModelCatalog } from "../lib/hooks/useModelCatalog";
import { useProjectSession } from "../lib/hooks/useProjectSession";
import { useAgentFinalize } from "../lib/hooks/useAgentFinalize";
import { useAgentGithubIssues } from "../lib/hooks/useAgentGithubIssues";
import { shouldWriteSnapshot } from "../lib/sessionSnapshot";
import { AppShell } from "./shell/AppShell";
import { Sidebar } from "./shell/Sidebar";
import { ConnectDriveBanner } from "./shell/ConnectDriveBanner";
import { CreateProjectDialog } from "./shell/CreateProjectDialog";
import { ConfirmDialog } from "./shell/ConfirmDialog";
import { ChatPanel } from "./chat/ChatPanel";
import { ModelPicker } from "./chat/ModelPicker";
import { ReadinessPane, PreviewPlaceholder } from "./chat/ReadinessPane";
import { PreviewPane } from "./preview/PreviewPane";
import { WikiDialog } from "./preview/WikiDialog";
import { AgentTimeline } from "./agent/AgentTimeline";
import { ConnectGithubModal } from "./agent/ConnectGithubModal";
import { AttachChips } from "./chat/AttachChips";
import { AutoTextarea } from "./ui/AutoTextarea";
import { Button } from "./ui/Button";
import { Icon } from "./ui/Icon";

/**
 * Wired workspace on the new shell. Holds the shell-level state and effects
 * preserved from WorkspaceShell (drive-status fetch on auth; analysisSessionId
 * regeneration on source/project change — TC-029). Becomes the production shell
 * at the Phase 5 flip. Preview/save/wiki land in Phase 4.
 */
export function WorkspaceV2() {
  const auth = useAuth();
  const [driveRepo, setDriveRepo] = useState<DriveRepoRecord | null>(null);
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);
  const [analysisSessionId, setAnalysisSessionId] = useState(() => crypto.randomUUID());
  const [startText, setStartText] = useState("");
  const [restoredSourceContext, setRestoredSourceContext] = useState("");
  const [restoredSourceReferences, setRestoredSourceReferences] = useState<string[]>([]);
  const [deletingProject, setDeletingProject] = useState<ProjectSummary | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const activeProjectRef = useRef<string | null>(null);
  const restoringRef = useRef(false);
  const pendingModelRef = useRef<string | null>(null);

  const models = useModelCatalog();
  const sources = useSources();
  const session = useProjectSession();
  const driveActions = useDriveRepo(setDriveRepo);
  const activeProjectId = driveRepo?.active_project_id ?? null;
  const effectiveSourceContext = sources.files.length
    ? sources.analysisContext
    : restoredSourceContext;
  const effectiveSourceReferences = sources.files.length
    ? sources.sourceReferences
    : restoredSourceReferences;
  const qna = useQnA({
    sourceContext: effectiveSourceContext,
    sourceReferences: effectiveSourceReferences,
    analysisSessionId,
    selectedModel: models.isLoaded ? models.selectedModel : undefined,
    onAnalysisSaved: () => {},
  });

  function handleProjectCreated(response: CreateProjectResponse) {
    setDriveRepo((current) => {
      if (!current) {
        return current;
      }
      const others = current.available_projects.filter(
        (project) => project.project_id !== response.project.project_id,
      );
      return {
        ...current,
        active_project_id: response.active_project_id,
        active_project_name: response.project.name,
        available_projects: [...others, response.project],
      };
    });
  }

  async function handleDeleteProject() {
    const project = deletingProject;
    const user = getFirebaseAuth().currentUser;
    if (!project || !user) {
      return;
    }

    const deletedActiveProject =
      project.project_id === driveRepo?.active_project_id;
    setDeleteBusy(true);
    setDeleteError("");
    try {
      const idToken = await user.getIdToken();
      await deleteProject(idToken, project.project_id);
      const updatedRepo = await getDriveRepoStatus(idToken);
      setDriveRepo(updatedRepo);
      setDeletingProject(null);
      if (deletedActiveProject) {
        session.cancel();
        qna.reset();
        sources.reset();
        sadSave.dismissPreview();
        setStartText("");
        setRestoredSourceContext("");
        setRestoredSourceReferences([]);
      }
    } catch (caught) {
      setDeleteError(
        caught instanceof Error ? caught.message : "Could not delete this project.",
      );
    } finally {
      setDeleteBusy(false);
    }
  }

  const sadSave = useSadSave({
    requirementText: qna.requirementText,
    analysisResponse: qna.analysisResponse,
    sourceContext: effectiveSourceContext,
    sourceReferences: effectiveSourceReferences,
    selectedModel: models.isLoaded ? models.selectedModel : undefined,
    onProjectCreated: handleProjectCreated,
    onHistoryRefresh: () => setHistoryRefreshKey((key) => key + 1),
  });

  const agent = useAgentFinalize({
    analysisSessionId,
    selectedModel: models.isLoaded ? models.selectedModel : undefined,
    onSaved: (savedSad) => {
      setHistoryRefreshKey((key) => key + 1);
      if (savedSad) {
        sadSave.adoptAgentSave(savedSad);
      }
    },
  });
  const githubIssues = useAgentGithubIssues({
    analysisSessionId,
    selectedModel: models.isLoaded ? models.selectedModel : undefined,
  });
  const [githubConnectOpen, setGithubConnectOpen] = useState(false);
  const [githubConnectBusy, setGithubConnectBusy] = useState(false);
  const [githubConnectError, setGithubConnectError] = useState("");
  const [githubResumeRepo, setGithubResumeRepo] = useState<string | null>(null);

  const activeProject =
    driveRepo?.available_projects.find(
      (project) => project.project_id === driveRepo?.active_project_id,
    ) ?? null;
  const activeGithubRepo = activeProject?.github_repo ?? null;

  function handlePrepareGithubIssues() {
    if (activeGithubRepo && githubIssues.hasToken) {
      githubIssues.prepare(sadSave.record?.save_id ?? null, activeGithubRepo);
      return;
    }
    setGithubConnectError("");
    setGithubConnectOpen(true);
  }

  async function handleGithubConnect(token: string, repo: string) {
    if (githubResumeRepo) {
      githubIssues.setGithubToken(token);
      setGithubConnectOpen(false);
      setGithubResumeRepo(null);
      return;
    }
    const projectId = driveRepo?.active_project_id;
    const user = getFirebaseAuth().currentUser;
    if (!projectId || !user) {
      setGithubConnectError("Connect a project and sign in before linking GitHub.");
      return;
    }
    setGithubConnectBusy(true);
    setGithubConnectError("");
    try {
      const idToken = await user.getIdToken();
      const updated = await setProjectGithubRepo(idToken, projectId, repo);
      setDriveRepo((current) =>
        current
          ? {
              ...current,
              available_projects: current.available_projects.map((project) =>
                project.project_id === updated.project_id ? updated : project,
              ),
            }
          : current,
      );
      githubIssues.setGithubToken(token);
      setGithubConnectOpen(false);
      githubIssues.prepare(sadSave.record?.save_id ?? null, updated.github_repo);
    } catch (caught) {
      setGithubConnectError(
        caught instanceof Error ? caught.message : "Could not link the GitHub repository.",
      );
    } finally {
      setGithubConnectBusy(false);
    }
  }

  async function handleResumeGithubIssues(save: SadSaveSummary) {
    const result = await githubIssues.relaunch(save.save_id);
    const lockedRepo = result?.repo;
    if (!lockedRepo) {
      return;
    }
    if (!githubIssues.hasToken) {
      setGithubResumeRepo(lockedRepo);
      setGithubConnectError("");
      setGithubConnectOpen(true);
    } else {
      setGithubResumeRepo(null);
    }
  }

  // Preserve WorkspaceShell: fetch Drive status when a user is present.
  useEffect(() => {
    if (!isFirebaseConfigured()) {
      return;
    }
    const firebaseAuth = getFirebaseAuth();
    return onAuthStateChanged(firebaseAuth, async (user) => {
      if (!user) {
        setDriveRepo(null);
        return;
      }
      try {
        const idToken = await user.getIdToken();
        setDriveRepo(await getDriveRepoStatus(idToken));
      } catch {
        setDriveRepo(null);
      }
    });
  }, []);

  // TC-029: regenerate the analysis session on new sources / project switch.
  useEffect(() => {
    setAnalysisSessionId(crypto.randomUUID());
  }, [sources.sourceReferences.join(","), driveRepo?.active_project_id]);

  useEffect(() => {
    session.cancel();
    const previousProjectId = activeProjectRef.current;
    activeProjectRef.current = activeProjectId;
    pendingModelRef.current = null;
    setRestoredSourceContext("");
    setRestoredSourceReferences([]);

    const switchedProjects =
      previousProjectId !== null && previousProjectId !== activeProjectId;
    if (switchedProjects) {
      qna.reset();
      sources.reset();
      setStartText("");
    }

    if (!auth.isSignedIn || !activeProjectId) {
      restoringRef.current = false;
      return session.cancel;
    }

    restoringRef.current = true;
    void session
      .restore(activeProjectId)
      .then((result) => {
        if (result.projectId !== activeProjectRef.current) {
          return;
        }
        const snapshot = result.snapshot;
        if (!snapshot) {
          return;
        }
        qna.hydrate({
          requirementText: snapshot.clean_requirement_text,
          analysisResponse: snapshot.analysis_response,
          answerHistory: snapshot.answer_history,
        });
        setStartText(snapshot.clean_requirement_text);
        setRestoredSourceContext(snapshot.source_context);
        setRestoredSourceReferences(snapshot.source_references);

        pendingModelRef.current = snapshot.selected_model;
        if (
          snapshot.selected_model &&
          models.isLoaded &&
          models.catalog.models.some((model) => model.id === snapshot.selected_model)
        ) {
          models.setSelectedModel(snapshot.selected_model);
          pendingModelRef.current = null;
        }
      })
      .catch((error) => {
        if (activeProjectRef.current !== activeProjectId) {
          return;
        }
        qna.reset();
        setStartText("");
        setRestoredSourceContext("");
        setRestoredSourceReferences([]);
        console.warn("Could not restore the project session snapshot.", error);
      })
      .finally(() => {
        if (activeProjectRef.current === activeProjectId) {
          restoringRef.current = false;
        }
      });

    return session.cancel;
  }, [activeProjectId, auth.isSignedIn]);

  useEffect(() => {
    const pendingModel = pendingModelRef.current;
    if (!models.isLoaded || !pendingModel) {
      return;
    }
    pendingModelRef.current = null;
    if (models.catalog.models.some((model) => model.id === pendingModel)) {
      models.setSelectedModel(pendingModel);
    }
  }, [models.catalog.models, models.isLoaded, models.setSelectedModel]);

  useEffect(() => {
    if (sources.files.length > 0) {
      setRestoredSourceContext("");
      setRestoredSourceReferences([]);
    }
  }, [sources.files.length]);

  useEffect(() => {
    const scheduledProjectId = activeProjectId;
    if (
      !shouldWriteSnapshot({
        isSignedIn: auth.isSignedIn,
        activeProjectId,
        scheduledProjectId,
        hasAnalysis: qna.analysisResponse !== null,
        restoring: restoringRef.current,
      }) ||
      !scheduledProjectId ||
      !qna.analysisResponse
    ) {
      return;
    }

    const snapshot: ProjectSessionSnapshot = {
      clean_requirement_text: qna.cleanRequirementText,
      analysis_response: qna.analysisResponse,
      answer_history: qna.answerHistory,
      source_context: effectiveSourceContext,
      source_references: effectiveSourceReferences,
      selected_model: models.selectedModel || null,
      status: "in_progress",
    };
    session.writeDebounced(
      scheduledProjectId,
      snapshot,
      (projectId) => projectId === activeProjectRef.current,
    );
    return session.cancel;
  }, [
    activeProjectId,
    auth.isSignedIn,
    effectiveSourceContext,
    effectiveSourceReferences,
    models.selectedModel,
    qna.analysisResponse,
    qna.answerHistory,
    qna.cleanRequirementText,
  ]);

  const readinessScore =
    qna.analysis?.questionnaire?.draft_readiness.score ?? qna.analysis?.readiness.score ?? 0;
  const stage = deriveStage({
    hasAnalysis: Boolean(qna.analysis),
    readinessScore,
    hasPreview: sadSave.hasPreview,
  });
  const connected = Boolean(driveRepo && !driveRepo.saves_blocked);

  const sidebar = (
    <Sidebar
      displayName={auth.displayName}
      email={auth.email}
      repo={driveRepo}
      onRepoChanged={setDriveRepo}
      historyRefreshKey={historyRefreshKey}
      onNewSad={() => {
        qna.reset();
        sources.reset();
        setStartText("");
      }}
      onDeleteProject={(projectId) => {
        const project = driveRepo?.available_projects.find(
          (candidate) => candidate.project_id === projectId,
        );
        if (project) {
          setDeleteError("");
          setDeletingProject(project);
        }
      }}
      onCreateGithubIssues={(save) => void handleResumeGithubIssues(save)}
      onSignIn={() => void auth.signIn().catch(() => undefined)}
      onSignOut={() => auth.signOut()}
    />
  );

  const chat = qna.analysis ? (
    <ChatPanel
      qna={qna}
      sources={sources.sources}
      attaching={sources.isBusy}
      onAttachAdd={(files) => sources.add(files)}
      onAttachRemove={(name) => sources.remove(name)}
      modelCatalog={models.catalog}
      selectedModel={models.selectedModel}
      onModelChange={models.setSelectedModel}
      generating={sadSave.generating}
      onGenerate={() => sadSave.generate()}
      onFinalizeWithAgent={() => agent.finalize()}
      actionsDisabled={sadSave.hasPreview}
      banner={
        !connected ? <ConnectDriveBanner onConnect={() => driveActions.connect()} /> : undefined
      }
    />
  ) : (
    <StartBox
      value={startText}
      busy={qna.isBusy}
      isSignedIn={auth.isSignedIn}
      sources={sources.sources}
      attaching={sources.isBusy}
      onAttachAdd={(files) => sources.add(files)}
      onAttachRemove={(name) => sources.remove(name)}
      onChange={setStartText}
      onStart={() => qna.startAnalysis(startText)}
      modelCatalog={models.catalog}
      selectedModel={models.selectedModel}
      onModelChange={models.setSelectedModel}
      onSignIn={() => {
        void auth.signIn().catch(() => undefined);
      }}
    />
  );

  const preview =
    sadSave.hasPreview && sadSave.preview ? (
      <PreviewPane
        preview={sadSave.preview}
        record={sadSave.record}
        wikiRecord={sadSave.wikiRecord}
        isDraftReady={readinessScore >= 90}
        canUpdateWiki={sadSave.canUpdateWiki}
        isSaving={sadSave.isSaving}
        isWikiBusy={sadSave.isWikiBusy}
        isGithubPreparing={githubIssues.isPreparing}
        githubLinked={Boolean(activeGithubRepo)}
        saveMessage={sadSave.saveMessage}
        wikiMessage={sadSave.wikiMessage}
        githubSetupNotice={githubIssues.setupNotice}
        onSave={() => sadSave.save()}
        onUpdateWiki={() => sadSave.updateWiki()}
        onPrepareGithubIssues={handlePrepareGithubIssues}
        onRefine={() => sadSave.dismissPreview()}
      />
    ) : stage === "clarify" && qna.analysis ? (
      <ReadinessPane
        score={readinessScore}
        label={qna.analysis.questionnaire?.draft_readiness.label ?? qna.analysis.readiness.label}
        confidence={
          qna.analysis.questionnaire?.draft_readiness.confidence ??
          qna.analysis.readiness.confidence
        }
        categories={qna.analysis.questionnaire?.categories ?? qna.analysis.categories}
        understandingSummary={qna.analysis.understanding_summary}
      />
    ) : (
      <PreviewPlaceholder text="Your SAD preview will appear here" />
    );

  return (
    <>
      <AppShell
        stage={stage}
        sidebar={sidebar}
        chat={chat}
        preview={preview}
        previewLabel={`Preview ${readinessScore}%`}
      />
      {sadSave.wikiDialogOpen && sadSave.wikiPreview ? (
        <WikiDialog
          preview={sadSave.wikiPreview}
          isBusy={sadSave.isWikiBusy}
          onConfirm={(force) => sadSave.confirmWiki(force)}
          onCancel={sadSave.cancelWiki}
        />
      ) : null}
      {sadSave.projectDialogOpen ? (
        <CreateProjectDialog
          suggestedName={sadSave.suggestProjectName()}
          isBusy={sadSave.isProjectBusy}
          onSubmit={(name) => sadSave.createProjectForPending(name)}
          onCancel={sadSave.cancelProject}
        />
      ) : null}
      {deletingProject ? (
        <ConfirmDialog
          title={`Delete ${deletingProject.name}?`}
          message={
            deleteError ||
            "This removes the project and its saved SAD data. Its Drive folder will move to Trash."
          }
          confirmLabel="Delete project"
          busy={deleteBusy}
          onConfirm={() => void handleDeleteProject()}
          onCancel={() => {
            setDeleteError("");
            setDeletingProject(null);
          }}
        />
      ) : null}
      {agent.isOpen ? (
        <AgentTimeline
          events={agent.events}
          status={agent.status}
          result={agent.result}
          isStreaming={agent.isStreaming}
          isApproving={agent.isApproving}
          error={agent.error}
          onApprove={() => agent.approve()}
          onViewSavedSad={agent.close}
          onContinueInChat={agent.close}
          onClose={agent.close}
        />
      ) : null}
      {githubConnectOpen ? (
        <ConnectGithubModal
          initialRepo={githubResumeRepo ?? activeGithubRepo}
          repoLocked={Boolean(githubResumeRepo)}
          busy={githubConnectBusy}
          error={githubConnectError}
          onSubmit={handleGithubConnect}
          onClose={() => {
            setGithubConnectOpen(false);
            setGithubResumeRepo(null);
          }}
        />
      ) : null}
      {githubIssues.isOpen ? (
        <AgentTimeline
          mode="github"
          events={githubIssues.events}
          status={githubIssues.status}
          result={githubIssues.result}
          isStreaming={githubIssues.isPreparing}
          isApproving={githubIssues.isApproving}
          error={githubIssues.error}
          onApprove={() => githubIssues.approve()}
          onContinueInChat={githubIssues.close}
          onClose={githubIssues.close}
        />
      ) : null}
    </>
  );
}

function StartBox({
  value,
  busy,
  isSignedIn,
  sources,
  attaching,
  onAttachAdd,
  onAttachRemove,
  onChange,
  onStart,
  modelCatalog,
  selectedModel,
  onModelChange,
  onSignIn,
}: {
  value: string;
  busy: boolean;
  isSignedIn: boolean;
  sources: SourceRecord[];
  attaching: boolean;
  onAttachAdd: (files: File[]) => void;
  onAttachRemove: (fileName: string) => void;
  onChange: (value: string) => void;
  onStart: () => void;
  modelCatalog: ModelCatalogResponse;
  selectedModel: string;
  onModelChange: (modelId: string) => void;
  onSignIn: () => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  return (
    <div
      style={{
        flex: 1,
        minHeight: 0,
        overflowY: "auto",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
    >
      <div
        style={{
          maxWidth: 460,
          width: "100%",
          textAlign: "center",
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <div style={{ display: "flex", justifyContent: "center" }}>
          <ModelPicker
            catalog={modelCatalog}
            selectedModel={selectedModel}
            onChange={onModelChange}
          />
        </div>
        <div
          style={{
            width: 46,
            height: 46,
            borderRadius: 13,
            margin: "0 auto",
            background: "linear-gradient(135deg,var(--c-primary),var(--c-secondary))",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Icon name="sparkle" size={24} color="#fff" />
        </div>
        <h2 style={{ margin: 0, fontSize: 21, fontWeight: 800, color: "var(--c-fg)" }}>
          Turn messy operations into a developer-ready spec
        </h2>
        <p style={{ margin: 0, fontSize: 13, color: "var(--c-subtle)" }}>
          Describe the problem in plain words — SADify asks a few questions, then drafts the SAD.
        </p>
        <input
          ref={fileRef}
          type="file"
          multiple
          accept=".md,.markdown,.txt,.pdf,.docx,.xlsx,.csv"
          style={{ display: "none" }}
          onChange={(event) => {
            const files = Array.from(event.target.files ?? []);
            if (files.length) {
              onAttachAdd(files);
            }
            event.target.value = "";
          }}
        />
        <AttachChips
          sources={sources}
          busy={attaching}
          onRemove={onAttachRemove}
          onAdd={() => fileRef.current?.click()}
        />
        <div
          style={{
            display: "flex",
            gap: 10,
            alignItems: "flex-end",
            border: "2px solid var(--c-secondary)",
            borderRadius: 13,
            background: "var(--c-surface)",
            padding: 10,
          }}
        >
          <button
            type="button"
            aria-label="Attach files"
            disabled={attaching}
            onClick={() => fileRef.current?.click()}
            style={{
              width: 36,
              height: 36,
              borderRadius: 9,
              background: "var(--c-muted)",
              border: "1px solid var(--c-border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flex: "none",
              cursor: "pointer",
              color: "var(--c-primary)",
            }}
          >
            <Icon name="paperclip" size={18} />
          </button>
          <AutoTextarea
            value={value}
            maxHeight={200}
            placeholder="e.g. We manage grooming appointments from booking to pickup."
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                if (value.trim().length >= 5 && !busy) {
                  onStart();
                }
              }
            }}
            style={{
              flex: 1,
              font: "inherit",
              fontSize: 14,
              color: "var(--c-fg)",
              background: "transparent",
              border: "none",
              resize: "none",
              outline: "none",
              textAlign: "left",
            }}
          />
        </div>
        <Button
          variant="primary"
          loading={busy}
          disabled={value.trim().length < 5}
          onClick={onStart}
        >
          Start
        </Button>
        {!isSignedIn ? (
          <button
            type="button"
            onClick={onSignIn}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--c-secondary)",
              fontFamily: "inherit",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Sign in with Google to save
          </button>
        ) : null}
      </div>
    </div>
  );
}
