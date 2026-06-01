"use client";

import { onAuthStateChanged } from "firebase/auth";
import { useEffect, useState } from "react";
import { getDriveRepoStatus, type DriveRepoRecord } from "../lib/api";
import { getFirebaseAuth } from "../lib/firebaseClient";
import { isFirebaseConfigured } from "../lib/firebaseConfig";
import { deriveStage } from "../lib/stage";
import { useAuth } from "../lib/hooks/useAuth";
import { useDriveRepo } from "../lib/hooks/useDriveRepo";
import { useSources } from "../lib/hooks/useSources";
import { useQnA } from "../lib/hooks/useQnA";
import { AppShell } from "./shell/AppShell";
import { Sidebar } from "./shell/Sidebar";
import { ConnectDriveBanner } from "./shell/ConnectDriveBanner";
import { ChatPanel } from "./chat/ChatPanel";
import { ReadinessPane, PreviewPlaceholder } from "./chat/ReadinessPane";
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
  const [historyRefreshKey] = useState(0);
  const [analysisSessionId, setAnalysisSessionId] = useState(() => crypto.randomUUID());
  const [startText, setStartText] = useState("");

  const sources = useSources();
  const driveActions = useDriveRepo(setDriveRepo);
  const qna = useQnA({
    sourceContext: sources.analysisContext,
    sourceReferences: sources.sourceReferences,
    analysisSessionId,
    onAnalysisSaved: () => {},
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
    hasPreview: false,
  });
  const connected = Boolean(driveRepo && !driveRepo.saves_blocked);

  const sidebar = (
    <Sidebar
      displayName={auth.displayName}
      email={auth.email}
      isSignedIn={auth.isSignedIn}
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
      onGenerate={() => undefined}
      banner={
        !connected ? <ConnectDriveBanner onConnect={() => driveActions.connect()} /> : undefined
      }
    />
  ) : (
    <StartBox
      value={startText}
      busy={qna.isBusy}
      isSignedIn={auth.isSignedIn}
      onChange={setStartText}
      onStart={() => qna.startAnalysis(startText)}
      onSignIn={() => {
        void auth.signIn().catch(() => undefined);
      }}
    />
  );

  const preview =
    stage === "clarify" && qna.analysis ? (
      <ReadinessPane
        score={readinessScore}
        label={qna.analysis.readiness.label}
        confidence={qna.analysis.readiness.confidence}
        categories={qna.analysis.categories}
        understandingSummary={qna.analysis.understanding_summary}
      />
    ) : (
      <PreviewPlaceholder text="Your SAD preview will appear here" />
    );

  return (
    <AppShell
      stage={stage}
      sidebar={sidebar}
      chat={chat}
      preview={preview}
      previewLabel={`Preview ${readinessScore}%`}
    />
  );
}

function StartBox({
  value,
  busy,
  isSignedIn,
  onChange,
  onStart,
  onSignIn,
}: {
  value: string;
  busy: boolean;
  isSignedIn: boolean;
  onChange: (value: string) => void;
  onStart: () => void;
  onSignIn: () => void;
}) {
  return (
    <div
      style={{
        flex: 1,
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
        <textarea
          value={value}
          rows={3}
          placeholder="e.g. We manage grooming appointments from booking to pickup."
          onChange={(event) => onChange(event.target.value)}
          style={{
            font: "inherit",
            fontSize: 14,
            color: "var(--c-fg)",
            background: "var(--c-surface)",
            border: "2px solid var(--c-secondary)",
            borderRadius: 13,
            padding: 13,
            resize: "none",
          }}
        />
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
