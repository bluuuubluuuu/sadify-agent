"use client";

import { useState } from "react";
import { AnalysisPanel } from "./AnalysisPanel";
import { AuthPanel } from "./AuthPanel";
import type {
  CreateProjectResponse,
  DriveRepoRecord,
  RequirementAnalysisApiResponse,
  SadPreviewApiResponse,
  SadSaveApiResponse,
  SourceUploadResponse,
} from "../lib/api";
import type { CategoryStatus, WorkspaceState } from "../lib/mockState";
import { ChangeSummary } from "./ChangeSummary";
import { DraftPanel } from "./DraftPanel";
import { DriveRepoPanel } from "./DriveRepoPanel";
import { ProjectPanel } from "./ProjectPanel";
import { SadPreviewPanel } from "./SadPreviewPanel";
import { SourceUploadPanel } from "./SourceUploadPanel";

type Props = {
  state: WorkspaceState;
};

export function WorkspaceShell({ state }: Props) {
  const [workspaceState, setWorkspaceState] = useState(state);
  const [sourceUpload, setSourceUpload] = useState<SourceUploadResponse | null>(null);
  const [analysisResponse, setAnalysisResponse] =
    useState<RequirementAnalysisApiResponse | null>(null);
  const [analysisRequirementText, setAnalysisRequirementText] = useState("");
  const [driveRepo, setDriveRepo] = useState<DriveRepoRecord | null>(null);

  function applyAnalysis(
    response: RequirementAnalysisApiResponse,
    cleanRequirementText: string,
  ) {
    const analysis = response.analysis;
    const draftReadiness = analysis.questionnaire?.draft_readiness ?? analysis.readiness;
    const categoryProgress = analysis.questionnaire?.categories.map((category) => ({
      label: category.label,
      status: category.status as CategoryStatus,
      progress: category.progress,
      questionsAnswered: category.questions_answered,
      questionsTotal: category.questions_total,
      isActive: category.is_active,
    }));
    setAnalysisResponse(response);
    setAnalysisRequirementText(cleanRequirementText);
    setWorkspaceState((current) => ({
      ...current,
      readinessLabel: draftReadiness.label,
      readinessScore: draftReadiness.score,
      confidenceLabel: analysis.readiness.confidence,
      currentQuestion: {
        text: analysis.next_question.text,
        whyThisMatters: analysis.next_question.why_this_matters,
        choices: analysis.next_question.choices,
      },
      categories:
        categoryProgress ??
        analysis.categories.map((category) => ({
          label: category.label,
          status: category.status as CategoryStatus,
        })),
      changeSummary: `Analysis ${response.analysis_id} saved. Next question refreshed from Gemini.`,
      projectStatus: [
        `Analysis state saved: ${response.analysis_id}`,
        "Question choices ready",
        "SAD preview not generated yet",
        "Project repo not connected",
      ],
    }));
  }

  function applySadPreview(response: SadPreviewApiResponse) {
    setWorkspaceState((current) => ({
      ...current,
      changeSummary: response.preview.change_tracking.summary,
      projectStatus: [
        `Temporary SAD preview saved: ${response.preview_id}`,
        `IT readiness: ${response.preview.it_readiness.score}%`,
        response.preview.open_questions.length
          ? `${response.preview.open_questions.length} open question(s) visible`
          : "No open questions returned",
        "Project files not saved to Drive yet",
      ],
    }));
  }

  function applySadSaved(response: SadSaveApiResponse) {
    setWorkspaceState((current) => ({
      ...current,
      changeSummary: response.record.change_summary,
      projectStatus: [
        `SAD saved: ${response.record.save_id}`,
        `Google Doc placeholder: ${response.record.sad_doc.path}`,
        `Repo: ${response.record.repo_folder_name}`,
        response.record.source_artifact_references.length
          ? `${response.record.source_artifact_references.length} source reference(s) linked`
          : "No uploaded source references linked",
      ],
    }));
  }

  function applyProjectCreated(response: CreateProjectResponse) {
    setDriveRepo((current) => {
      if (!current) {
        return current;
      }
      const otherProjects = current.available_projects.filter(
        (project) => project.project_id !== response.project.project_id,
      );
      return {
        ...current,
        active_project_id: response.active_project_id,
        active_project_name: response.project.name,
        available_projects: [...otherProjects, response.project],
      };
    });
    setWorkspaceState((current) => ({
      ...current,
      projectStatus: [
        `Active project: ${response.project.name}`,
        "Project folder selected",
        "SAD and wiki saves will use this project",
      ],
    }));
  }

  function applyAnswerSubmitted(
    response: RequirementAnalysisApiResponse,
    answerText: string,
  ) {
    setWorkspaceState((current) => ({
      ...current,
      changeSummary: "Answer saved. Next question refreshed from Gemini.",
      projectStatus: [
        `Answer added to analysis: ${response.analysis_id}`,
        `Latest answer: ${answerText}`,
        "Question choices ready",
        "SAD preview can be regenerated",
      ],
    }));
  }

  function applyAnswerKeptForPreview(
    response: RequirementAnalysisApiResponse,
    cleanRequirementText: string,
    answerText: string,
  ) {
    setAnalysisResponse(response);
    setAnalysisRequirementText(cleanRequirementText);
    setWorkspaceState((current) => ({
      ...current,
      changeSummary: "Answer kept for preview. Next question needs retry.",
      projectStatus: [
        `Answer kept with analysis: ${response.analysis_id}`,
        `Latest answer: ${answerText}`,
        "Next question did not refresh",
        "SAD preview can use the kept answer",
      ],
    }));
  }

  function applySourceUpload(response: SourceUploadResponse) {
    setSourceUpload(response);
    const sourceIds = response.sources.map((source) => source.source_id);
    setWorkspaceState((current) => ({
      ...current,
      changeSummary: `${response.sources.length} source file(s) extracted for traceability.`,
      projectStatus: [
        sourceIds.length
          ? `Source context ready: ${sourceIds.join(", ")}`
          : "No valid source files yet",
        response.errors.length
          ? `${response.errors.length} file(s) need a supported format`
          : "All uploaded source files readable",
        "SAD preview not generated yet",
        "Project repo not connected",
      ],
    }));
  }

  const sourceContext = sourceUpload?.analysis_context ?? "";
  const sourceReferences =
    sourceUpload?.sources.map((source) => source.source_id) ?? [];

  return (
    <main className="workspace">
      <header className="workspace-header">
        <div>
          <p className="eyebrow">SADify</p>
          <h1>{workspaceState.projectTitle}</h1>
        </div>
        <span className="mode-pill">
          {workspaceState.mode === "guest" ? "Guest draft" : "Signed in"}
        </span>
      </header>

      <AuthPanel />

      <ProjectPanel repo={driveRepo} onRepoChanged={setDriveRepo} />

      <DraftPanel />

      <DriveRepoPanel repo={driveRepo} onRepoChanged={setDriveRepo} />

      <SourceUploadPanel onSourcesUploaded={applySourceUpload} />

      <AnalysisPanel
        onAnalysisSaved={applyAnalysis}
        onAnswerSubmitted={applyAnswerSubmitted}
        onAnswerKeptForPreview={applyAnswerKeptForPreview}
        sourceContext={sourceContext}
        sourceReferences={sourceReferences}
      />

      <SadPreviewPanel
        analysisResponse={analysisResponse}
        requirementText={analysisRequirementText}
        sourceContext={sourceContext}
        sourceReferences={sourceReferences}
        onPreviewSaved={applySadPreview}
        onSadSaved={applySadSaved}
        onProjectCreated={applyProjectCreated}
      />

      <ChangeSummary
        summary={workspaceState.changeSummary}
        projectStatus={workspaceState.projectStatus}
      />

      {analysisResponse ? null : (
        <section className="analysis-empty-state" aria-label="Analysis status">
          <p className="eyebrow">Analysis status</p>
          <strong>No analysis yet</strong>
          <p>Start analysis to build the questionnaire for this draft.</p>
        </section>
      )}
    </main>
  );
}
