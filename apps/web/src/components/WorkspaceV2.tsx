"use client";

import { onAuthStateChanged } from "firebase/auth";
import { useEffect, useRef, useState } from "react";
import {
  getDriveRepoStatus,
  type CreateProjectResponse,
  type DriveRepoRecord,
  type ModelCatalogResponse,
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
import { useAgentFinalize } from "../lib/hooks/useAgentFinalize";
import { AppShell } from "./shell/AppShell";
import { Sidebar } from "./shell/Sidebar";
import { ConnectDriveBanner } from "./shell/ConnectDriveBanner";
import { CreateProjectDialog } from "./shell/CreateProjectDialog";
import { ChatPanel } from "./chat/ChatPanel";
import { ModelPicker } from "./chat/ModelPicker";
import { ReadinessPane, PreviewPlaceholder } from "./chat/ReadinessPane";
import { PreviewPane } from "./preview/PreviewPane";
import { WikiDialog } from "./preview/WikiDialog";
import { AgentTimeline } from "./agent/AgentTimeline";
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

  const models = useModelCatalog();
  const sources = useSources();
  const driveActions = useDriveRepo(setDriveRepo);
  const qna = useQnA({
    sourceContext: sources.analysisContext,
    sourceReferences: sources.sourceReferences,
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

  const sadSave = useSadSave({
    requirementText: qna.requirementText,
    analysisResponse: qna.analysisResponse,
    sourceContext: sources.analysisContext,
    sourceReferences: sources.sourceReferences,
    selectedModel: models.isLoaded ? models.selectedModel : undefined,
    onProjectCreated: handleProjectCreated,
    onHistoryRefresh: () => setHistoryRefreshKey((key) => key + 1),
  });

  const agent = useAgentFinalize({
    analysisSessionId,
    selectedModel: models.isLoaded ? models.selectedModel : undefined,
  });

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
        saveMessage={sadSave.saveMessage}
        wikiMessage={sadSave.wikiMessage}
        onSave={() => sadSave.save()}
        onUpdateWiki={() => sadSave.updateWiki()}
        onRefine={() => sadSave.dismissPreview()}
        onFinalizeWithAgent={() => agent.finalize()}
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
      {agent.isOpen ? (
        <AgentTimeline
          events={agent.events}
          status={agent.status}
          result={agent.result}
          isStreaming={agent.isStreaming}
          isApproving={agent.isApproving}
          error={agent.error}
          onApprove={() => agent.approve()}
          onContinueInChat={agent.close}
          onClose={agent.close}
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
