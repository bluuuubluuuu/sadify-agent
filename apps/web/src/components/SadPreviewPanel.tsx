"use client";

import { useEffect, useState } from "react";
import {
  generateSadPreview,
  saveSadPreview,
  type RequirementAnalysisApiResponse,
  type SadPreviewApiResponse,
  type SadSaveApiResponse,
} from "../lib/api";
import { getFirebaseAuth } from "../lib/firebaseClient";

type Props = {
  analysisResponse: RequirementAnalysisApiResponse | null;
  requirementText: string;
  sourceContext?: string;
  sourceReferences?: string[];
  onPreviewSaved: (response: SadPreviewApiResponse) => void;
  onSadSaved: (response: SadSaveApiResponse) => void;
};

const readinessLabel: Record<string, string> = {
  ready: "Ready",
  needs_input: "Needs input",
  risk: "Risk",
};

export function SadPreviewPanel({
  analysisResponse,
  requirementText,
  sourceContext = "",
  sourceReferences = [],
  onPreviewSaved,
  onSadSaved,
}: Props) {
  const [previewResponse, setPreviewResponse] =
    useState<SadPreviewApiResponse | null>(null);
  const [saveResponse, setSaveResponse] = useState<SadSaveApiResponse | null>(null);
  const [message, setMessage] = useState(
    "Temporary preview only. No Google Doc or Drive file is saved here.",
  );
  const [saveMessage, setSaveMessage] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const analysisId = analysisResponse?.analysis_id;

  useEffect(() => {
    setPreviewResponse(null);
    setSaveResponse(null);
    setSaveMessage("");
    setMessage("Temporary preview only. No Google Doc or Drive file is saved here.");
  }, [analysisId, requirementText]);

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
      setSaveMessage("");
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

  async function savePreviewToProjectRepo() {
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
      onSadSaved(response);
      setSaveMessage("Saved to project repo.");
    } catch (error) {
      setSaveMessage(
        error instanceof Error
          ? error.message
          : "SADify could not save this SAD preview yet.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  const preview = previewResponse?.preview;
  const record = saveResponse?.record;
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
          onClick={savePreviewToProjectRepo}
        >
          Save to project repo
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
    </section>
  );
}
