"use client";

import { useState } from "react";
import { analyzeRequirement, type RequirementAnalysisApiResponse } from "../api";

const DEFAULT_REQUIREMENT = "Need a simple way to validate an operational workflow idea.";

/**
 * Q&A engine extracted VERBATIM from AnalysisPanel. The carry-forward transport
 * string ("Previous question/answer/readiness") and the kept-answer fallback are
 * byte-identical to preserve backend parsing + TC-029 session behavior.
 */
export function useQnA({
  sourceContext = "",
  sourceReferences = [],
  analysisSessionId,
  onAnalysisSaved,
  onAnswerSubmitted,
  onAnswerKeptForPreview,
}: {
  sourceContext?: string;
  sourceReferences?: string[];
  analysisSessionId: string;
  onAnalysisSaved: (response: RequirementAnalysisApiResponse, requirementText: string) => void;
  onAnswerSubmitted?: (response: RequirementAnalysisApiResponse, answerText: string) => void;
  onAnswerKeptForPreview?: (
    response: RequirementAnalysisApiResponse,
    requirementText: string,
    answerText: string,
  ) => void;
}) {
  const [requirementText, setRequirementText] = useState(DEFAULT_REQUIREMENT);
  const [cleanRequirementText, setCleanRequirementText] = useState(DEFAULT_REQUIREMENT);
  const [analysisResponse, setAnalysisResponse] =
    useState<RequirementAnalysisApiResponse | null>(null);
  const [selectedChoiceIds, setSelectedChoiceIds] = useState<string[]>([]);
  const [amendmentText, setAmendmentText] = useState("");
  const [answerHistory, setAnswerHistory] = useState<string[]>([]);
  const [message, setMessage] = useState("No project files are written by this step.");
  const [isBusy, setIsBusy] = useState(false);

  async function startAnalysis(text?: string) {
    const cleanText = (text ?? requirementText).trim();
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
        error instanceof Error ? error.message : "SADify could not start the question flow.",
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
        selectedChoices.some(
          (choice) =>
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
  const unresolvedCategories =
    questionnaire?.categories.filter((category) => category.visibility === "main") ?? [];
  const isQuestionnaireReady =
    Boolean(questionnaire) &&
    (questionnaire?.draft_readiness.score === 100 || unresolvedCategories.length === 0);
  const selectionMode: "single" | "multiple" =
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

  return {
    requirementText,
    setRequirementText,
    analysisResponse,
    analysis,
    questionnaire,
    isBusy,
    message,
    selectedChoiceIds,
    amendmentText,
    setAmendmentText,
    selectionMode,
    isOtherSelected,
    canUseAmendment,
    hasSelectedAnswer,
    selectedAnswerLabel,
    isQuestionnaireReady,
    startAnalysis,
    continueWithAnswer,
    toggleChoice,
  };
}

function isFallbackAnalysis(response: RequirementAnalysisApiResponse) {
  return response.analysis.assumptions.some((assumption) =>
    assumption.toLowerCase().includes("fallback was used"),
  );
}

function currentReadinessScore(analysis: RequirementAnalysisApiResponse["analysis"]) {
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
