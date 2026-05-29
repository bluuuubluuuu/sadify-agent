"use client";

import { useState } from "react";
import {
  analyzeRequirement,
  type RequirementAnalysisApiResponse,
} from "../lib/api";

type Props = {
  onAnalysisSaved: (
    response: RequirementAnalysisApiResponse,
    requirementText: string,
  ) => void;
  onAnswerSubmitted?: (
    response: RequirementAnalysisApiResponse,
    answerText: string,
  ) => void;
  onAnswerKeptForPreview?: (
    response: RequirementAnalysisApiResponse,
    requirementText: string,
    answerText: string,
  ) => void;
  sourceContext?: string;
  sourceReferences?: string[];
  analysisSessionId: string;
};

export function AnalysisPanel({
  onAnalysisSaved,
  onAnswerSubmitted,
  onAnswerKeptForPreview,
  sourceContext = "",
  sourceReferences = [],
  analysisSessionId,
}: Props) {
  const [requirementText, setRequirementText] = useState(
    "Need a simple way to validate an operational workflow idea.",
  );
  const [cleanRequirementText, setCleanRequirementText] = useState(
    "Need a simple way to validate an operational workflow idea.",
  );
  const [analysisResponse, setAnalysisResponse] =
    useState<RequirementAnalysisApiResponse | null>(null);
  const [selectedChoiceIds, setSelectedChoiceIds] = useState<string[]>([]);
  const [amendmentText, setAmendmentText] = useState("");
  const [answerHistory, setAnswerHistory] = useState<string[]>([]);
  const [message, setMessage] = useState(
    "No project files are written by this step.",
  );
  const [isBusy, setIsBusy] = useState(false);

  async function startAnalysis() {
    const cleanText = requirementText.trim();
    setIsBusy(true);
    setMessage("Asking Gemini for one validated question...");
    try {
      const response = await analyzeRequirement({
        requirementText: cleanText,
        analysisSessionId,
        sourceContext: sourceContext || undefined,
        sourceReferences,
      });
      setRequirementText(cleanText);
      setCleanRequirementText(cleanText);
      setAnalysisResponse(response);
      setSelectedChoiceIds([]);
      setAmendmentText("");
      setAnswerHistory([]);
      onAnalysisSaved(response, cleanText);
      setMessage(
        isFallbackAnalysis(response)
          ? "Fallback question shown because Gemini output was invalid."
          : `Analysis ${response.analysis_id} saved in backend Q&A state.`,
      );
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "SADify could not start the question flow.",
      );
    } finally {
      setIsBusy(false);
    }
  }

  async function continueWithAnswer() {
    const currentResponse = analysisResponse;
    const analysis = currentResponse?.analysis;
    if (!currentResponse || !analysis) {
      setMessage("Start analysis first.");
      return;
    }

    const selectedChoices = analysis.next_question.choices.filter((choice) =>
      selectedChoiceIds.includes(choice.id),
    );
    const cleanAmendment = amendmentText.trim();
    const isOtherSelected = selectedChoiceIds.includes("other");
    if (isOtherSelected && !cleanAmendment) {
      setMessage("Other / not listed needs details before continuing.");
      return;
    }
    const answerText = [
      selectedChoices.map((choice) => choice.label).join(", "),
      cleanAmendment,
    ]
      .filter(Boolean)
      .join(" | Details: ");
    if (!answerText) {
      setMessage("Choose an answer or add details first.");
      return;
    }

    const nextRequirementText = [
      cleanRequirementText,
      ...answerHistory,
      `Previous question: [category: ${analysis.next_question.target_category}][slot: ${analysis.next_question.target_slot_id}] ${analysis.next_question.text}`,
      `Previous answer: ${answerText}`,
      `Previous readiness: ${currentReadinessScore(analysis)}`,
    ].join("\n\n");

    setIsBusy(true);
    setMessage("Saving answer and asking the next question...");
    try {
      const response = await analyzeRequirement({
        requirementText: nextRequirementText,
        analysisSessionId,
        sourceContext: sourceContext || undefined,
        sourceReferences,
      });
      setAnalysisResponse(response);
      setAnswerHistory((current) => [
        ...current,
        `Previous question: [category: ${analysis.next_question.target_category}][slot: ${analysis.next_question.target_slot_id}] ${analysis.next_question.text}\nPrevious answer: ${answerText}\n\nPrevious readiness: ${currentReadinessScore(analysis)}`,
      ]);
      setSelectedChoiceIds([]);
      setAmendmentText("");
      onAnalysisSaved(response, cleanRequirementText);
      onAnswerSubmitted?.(response, answerText);
      setMessage(
        isFallbackAnalysis(response)
          ? "Answer saved. Fallback question shown because Gemini output was invalid."
          : "Answer saved. Next question refreshed from Gemini.",
      );
    } catch (error) {
      const keptAnswerResponse = appendKeptAnswer(
        currentResponse,
        answerText,
        selectedChoices.some((choice) =>
          choice.label.toLowerCase().includes("not sure") ||
          choice.label.toLowerCase().includes("unsure"),
        ),
      );
      setAnalysisResponse(keptAnswerResponse);
      setAnswerHistory((current) => [
        ...current,
        `Previous question: [category: ${analysis.next_question.target_category}][slot: ${analysis.next_question.target_slot_id}] ${analysis.next_question.text}\nPrevious answer: ${answerText}\n\nPrevious readiness: ${currentReadinessScore(analysis)}`,
      ]);
      setSelectedChoiceIds([]);
      setAmendmentText("");
      onAnswerKeptForPreview?.(keptAnswerResponse, cleanRequirementText, answerText);
      setMessage(
        error instanceof Error
          ? `Answer kept for SAD preview. Gemini could not prepare the next question: ${error.message}`
          : "Answer kept for SAD preview. Gemini could not prepare the next question.",
      );
    } finally {
      setIsBusy(false);
    }
  }

  const analysis = analysisResponse?.analysis;
  const questionnaire = analysis?.questionnaire ?? null;
  const activeCategory = questionnaire?.categories.find(
    (category) => category.id === questionnaire.active_category_id,
  );
  const activeAnswers =
    questionnaire?.answers.filter(
      (answer) => answer.category_id === questionnaire.active_category_id,
    ) ?? [];
  const unresolvedCategories =
    questionnaire?.categories.filter((category) => category.visibility === "main") ?? [];
  const alreadyUnderstoodCategories =
    questionnaire?.categories.filter(
      (category) => category.visibility === "already_understood",
    ) ?? [];
  const completedCategories =
    questionnaire?.categories.filter((category) => category.visibility === "completed") ??
    [];
  const notApplicableCategories =
    questionnaire?.categories.filter(
      (category) => category.visibility === "not_applicable",
    ) ?? [];
  const suggestedAdditions = analysis?.proposed_extra_categories ?? [];
  const isQuestionnaireReady =
    Boolean(questionnaire) &&
    (questionnaire?.draft_readiness.score === 100 ||
      unresolvedCategories.length === 0);
  const selectionMode =
    analysis?.next_question.selection_mode === "multiple" ? "multiple" : "single";
  const selectedChoices =
    analysis?.next_question.choices.filter((choice) =>
      selectedChoiceIds.includes(choice.id),
    ) ?? [];
  const isOtherSelected = selectedChoiceIds.includes("other");
  const canUseAmendment = selectedChoiceIds.length > 0;
  const selectedAnswerLabel = [
    selectedChoices.map((choice) => choice.label).join(", "),
    canUseAmendment ? amendmentText.trim() : "",
  ]
    .filter(Boolean)
    .join(" | Details: ");
  const hasSelectedAnswer =
    selectedChoiceIds.length > 0 && (!isOtherSelected || amendmentText.trim().length > 0);

  function toggleChoice(choiceId: string) {
    const choice = analysis?.next_question.choices.find(
      (candidate) => candidate.id === choiceId,
    );
    if (!choice || choice.is_disabled) {
      return;
    }
    setSelectedChoiceIds((current) => {
      if (current.includes(choiceId)) {
        return current.filter((id) => id !== choiceId);
      }
      if (selectionMode === "multiple") {
        return [...current, choiceId];
      }
      return [choiceId];
    });
  }

  const answerControls = analysis ? (
    <>
      {selectionMode === "multiple" ? (
        <p className="selection-mode-hint">Select all that apply.</p>
      ) : null}

      <div className="choice-grid" aria-label="Gemini question choices">
        {analysis.next_question.choices.map((choice) => (
          <button
            key={choice.id}
            type="button"
            className={`choice-button ${
              selectionMode === "multiple" ? "multi-select " : ""
            }${selectedChoiceIds.includes(choice.id) ? "selected" : ""}${
              choice.is_disabled ? " disabled-choice" : ""
            }`}
            aria-pressed={selectedChoiceIds.includes(choice.id)}
            disabled={isBusy || choice.is_disabled}
            onClick={() => toggleChoice(choice.id)}
          >
            {selectionMode === "multiple" ? (
              <span className="choice-check" aria-hidden="true" />
            ) : null}
            <span>{choice.label}</span>
            {choice.status_label ? <small>{choice.status_label}</small> : null}
          </button>
        ))}
      </div>

      <label className="amend-field">
        <span>Amend answer</span>
        <textarea
          placeholder={
            canUseAmendment
              ? isOtherSelected
                ? "Other / not listed needs details before continuing."
                : "Add optional details for the selected answer."
              : "Add details after choosing an answer."
          }
          rows={4}
          value={amendmentText}
          disabled={!canUseAmendment || isBusy}
          onChange={(event) => setAmendmentText(event.target.value)}
        />
      </label>

      <div className="answer-action-row">
        <p className="selected-answer">
          {hasSelectedAnswer
            ? `Selected answer: ${selectedAnswerLabel}`
            : isOtherSelected
              ? "Other / not listed needs details before continuing."
              : selectionMode === "multiple"
                ? "Choose one or more options to continue."
                : "Choose one option to continue."}
        </p>
        <button
          type="button"
          className={`primary-button answer-button ${
            hasSelectedAnswer ? "ready" : ""
          }`}
          disabled={isBusy || !hasSelectedAnswer}
          aria-label="Continue with answer"
          onClick={continueWithAnswer}
        >
          {isBusy
            ? "Sending answer..."
            : hasSelectedAnswer
              ? "Save answer and ask next question"
              : "Continue with answer"}
        </button>
      </div>
    </>
  ) : null;

  return (
    <section className="analysis-panel" aria-label="Live Gemini Q&A">
      <div className="analysis-copy">
        <p className="eyebrow">Question flow</p>
        <h2>Ask one easy question next.</h2>
        <p>{message}</p>
        <p className="source-hint">
          {sourceReferences.length
            ? `${sourceReferences.length} source reference(s) attached.`
            : "No source references attached yet."}
        </p>
      </div>

      <label className="analysis-input">
        <span>Business request</span>
        <textarea
          value={requirementText}
          onChange={(event) => setRequirementText(event.target.value)}
        />
      </label>

      <button
        type="button"
        className="primary-button"
        disabled={isBusy || requirementText.trim().length < 5}
        onClick={startAnalysis}
      >
        Start analysis
      </button>

      {analysis ? (
        <div className="analysis-result" aria-live="polite">
          {!isQuestionnaireReady ? (
            <>
              <h3>{analysis.next_question.text}</h3>
              <p>{analysis.next_question.why_this_matters}</p>
              {analysis.source_references.length > 0 ? (
                <p className="source-reference-row">
                  Source refs: {analysis.source_references.join(", ")}
                </p>
              ) : null}
            </>
          ) : null}

          {questionnaire ? (
            <section className="questionnaire-state" aria-label="Question areas">
              <div className="questionnaire-header">
                <div>
                  <p className="eyebrow">Overall readiness</p>
                  <strong>
                    {questionnaire.draft_readiness.label} -{" "}
                    {questionnaire.draft_readiness.score}%
                  </strong>
                </div>
                <details className="analysis-diagnostics">
                  <summary>Tracking / diagnostics</summary>
                  <p className="eyebrow">Analysis diagnostics</p>
                  <p>AI check: {confidenceToBadge(analysis.readiness.confidence)}</p>
                  {questionnaire.diagnostics.length ? (
                    <ul>
                      {questionnaire.diagnostics.map((diagnostic) => (
                        <li key={diagnostic}>{diagnostic}</li>
                      ))}
                    </ul>
                  ) : null}
                </details>
              </div>

              {isQuestionnaireReady ? (
                <div className="ready-handoff">
                  <p className="eyebrow">Required analysis complete</p>
                  <strong>Ready to draft</strong>
                  <p>All required answers are covered. You can generate the SAD now.</p>
                </div>
              ) : (
                <div className="category-progress-row" aria-label="Question categories">
                  <p className="eyebrow">Question areas</p>
                  {unresolvedCategories.map((category) => (
                    <div
                      key={category.id}
                      className={`category-progress ${
                        category.is_active ? "active" : ""
                      }`}
                    >
                      <span>{category.label}</span>
                      <small>{questionAreaStatusLabel(category.status)}</small>
                    </div>
                  ))}
                </div>
              )}

              <details className="questionnaire-bucket">
                <summary>Current understanding</summary>
                <p>{analysis.understanding_summary}</p>
              </details>

              {alreadyUnderstoodCategories.length ? (
                <details className="questionnaire-bucket">
                  <summary>Already understood</summary>
                  <ul>
                    {alreadyUnderstoodCategories.map((category) => (
                      <li key={category.id}>{category.label}</li>
                    ))}
                  </ul>
                </details>
              ) : null}

              {completedCategories.length ? (
                <details className="questionnaire-bucket">
                  <summary>Completed areas</summary>
                  <ul>
                    {completedCategories.map((category) => (
                      <li key={category.id}>{category.label}</li>
                    ))}
                  </ul>
                </details>
              ) : null}

              {notApplicableCategories.length ? (
                <details className="questionnaire-bucket">
                  <summary>Not relevant to this project</summary>
                  <ul>
                    {notApplicableCategories.map((category) => (
                      <li key={category.id}>{category.label}</li>
                    ))}
                  </ul>
                </details>
              ) : null}

              {isQuestionnaireReady ? (
                <details className="questionnaire-bucket">
                  <summary>Optional refinements</summary>
                  <p>
                    These extra details can improve the SAD, but they do not block
                    drafting.
                  </p>
                  <div className="optional-refinement-question">
                    <strong>{analysis.next_question.text}</strong>
                    <p>{analysis.next_question.why_this_matters}</p>
                    {analysis.source_references.length > 0 ? (
                      <p className="source-reference-row">
                        Source refs: {analysis.source_references.join(", ")}
                      </p>
                    ) : null}
                  </div>
                  {answerControls}
                </details>
              ) : null}

              {suggestedAdditions.length ? (
                <details className="questionnaire-bucket">
                  <summary>Suggested additions</summary>
                  <ul>
                    {suggestedAdditions.map((category) => (
                      <li key={category.id}>
                        <strong>{category.label}</strong>
                        <span>{category.reason}</span>
                      </li>
                    ))}
                  </ul>
                </details>
              ) : null}

              {!isQuestionnaireReady && activeCategory ? (
                <div className="active-category">
                  <p className="eyebrow">Active category</p>
                  <strong>{activeCategory.label}</strong>
                  <span>
                    Working on: {questionnaire.active_slot_label ?? "Current requirement"}
                  </span>
                </div>
              ) : null}

              {activeAnswers.length ? (
                <details className="questionnaire-bucket answer-history">
                  <summary>Answered so far</summary>
                  <ol>
                    {activeAnswers.map((answer, index) => (
                      <li key={`${answer.category_id}-${index}`}>
                        <span>{answer.question}</span>
                        <strong>{answer.answer}</strong>
                        {answer.is_uncertain ? <small>Needs later confirmation</small> : null}
                      </li>
                    ))}
                  </ol>
                </details>
              ) : null}
            </section>
          ) : null}

          {!isQuestionnaireReady ? answerControls : null}
        </div>
      ) : null}
    </section>
  );
}

function isFallbackAnalysis(response: RequirementAnalysisApiResponse) {
  return response.analysis.assumptions.some((assumption) =>
    assumption.toLowerCase().includes("fallback was used"),
  );
}

function confidenceToBadge(confidenceLabel: "Low" | "Medium" | "High") {
  if (confidenceLabel === "High") {
    return "strong";
  }
  if (confidenceLabel === "Medium") {
    return "usable";
  }
  return "needs review";
}

function currentReadinessScore(
  analysis: RequirementAnalysisApiResponse["analysis"],
) {
  return analysis.questionnaire?.draft_readiness.score ?? analysis.readiness.score;
}

function appendKeptAnswer(
  response: RequirementAnalysisApiResponse,
  answerText: string,
  isUncertain: boolean,
): RequirementAnalysisApiResponse {
  const questionnaire = response.analysis.questionnaire;
  if (!questionnaire) {
    return response;
  }
  const question = response.analysis.next_question;
  return {
    ...response,
    analysis: {
      ...response.analysis,
      questionnaire: {
        ...questionnaire,
        answers: [
          ...questionnaire.answers,
          {
            category_id: question.target_category,
            slot_id: question.target_slot_id,
            question: question.text,
            answer: answerText,
            is_uncertain: isUncertain,
          },
        ],
      },
    },
  };
}

function questionAreaStatusLabel(
  status: "ready" | "in_progress" | "needed" | "needs_later_confirmation",
) {
  if (status === "ready") {
    return "Ready";
  }
  if (status === "in_progress") {
    return "In progress";
  }
  if (status === "needs_later_confirmation") {
    return "Confirm later";
  }
  return "Needs answer";
}
