"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { SourceRecord } from "../../lib/api";
import type { useQnA } from "../../lib/hooks/useQnA";
import { Button } from "../ui/Button";
import { Icon } from "../ui/Icon";
import { PhaseStepper } from "../ui/PhaseStepper";
import { ChatThread, type ChatMessage } from "./ChatThread";
import { AnswerChips } from "./AnswerChips";
import { AttachChips } from "./AttachChips";
import { Composer } from "./Composer";
import styles from "./chat.module.css";

type QnA = ReturnType<typeof useQnA>;

const GEN_PHASES = ["Reading", "Drafting", "Finalising"];

export function ChatPanel({
  qna,
  sources,
  attaching,
  onAttachAdd,
  onAttachRemove,
  generating,
  onGenerate,
  banner,
}: {
  qna: QnA;
  sources: SourceRecord[];
  attaching?: boolean;
  onAttachAdd: (files: File[]) => void;
  onAttachRemove: (fileName: string) => void;
  generating?: boolean;
  onGenerate: () => void;
  banner?: ReactNode;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [genPhase, setGenPhase] = useState(0);

  useEffect(() => {
    if (!generating) {
      setGenPhase(0);
      return;
    }
    const timer = window.setInterval(
      () => setGenPhase((phase) => (phase + 1) % GEN_PHASES.length),
      800,
    );
    return () => window.clearInterval(timer);
  }, [generating]);

  const messages = useMemo<ChatMessage[]>(() => {
    const out: ChatMessage[] = [];
    const analysis = qna.analysis;
    if (qna.requirementText.trim()) {
      out.push({ id: "req", role: "user", text: qna.requirementText });
    }
    const answers = analysis?.questionnaire?.answers ?? [];
    answers.forEach((answer, index) => {
      out.push({ id: `q-${index}`, role: "assistant", text: answer.question });
      out.push({ id: `a-${index}`, role: "user", text: answer.answer });
    });
    if (analysis && !qna.isQuestionnaireReady) {
      out.push({
        id: "current",
        role: "assistant",
        text: analysis.next_question.text,
        why: analysis.next_question.why_this_matters,
      });
    }
    return out;
  }, [qna.analysis, qna.requirementText, qna.isQuestionnaireReady]);

  const placeholder = qna.hasSelectedAnswer
    ? "Add optional details…"
    : qna.isOtherSelected
      ? "Other / not listed needs details before continuing."
      : qna.selectionMode === "multiple"
        ? "Tap one or more answers above…"
        : "Tap an answer above, or pick Other to type your own…";

  const footer = qna.isQuestionnaireReady ? (
    <div className={styles.ready}>
      <span className={styles.readyText}>
        <Icon name="checkCircle" size={18} color="var(--c-accent)" />
        All required areas confirmed — your SAD is ready to draft.
      </span>
      {generating ? (
        <PhaseStepper phases={GEN_PHASES} active={genPhase} />
      ) : (
        <Button
          variant="primary"
          leftIcon={<Icon name="arrowRight" size={16} color="#fff" />}
          onClick={onGenerate}
        >
          Generate SAD preview
        </Button>
      )}
    </div>
  ) : qna.analysis ? (
    <>
      {banner}
      <AnswerChips
        choices={qna.analysis.next_question.choices}
        selectedIds={qna.selectedChoiceIds}
        selectionMode={qna.selectionMode}
        disabled={qna.isBusy}
        onToggle={qna.toggleChoice}
      />
      <Composer
        value={qna.amendmentText}
        onChange={qna.setAmendmentText}
        onSubmit={qna.continueWithAnswer}
        onAttachClick={() => fileRef.current?.click()}
        attaching={attaching}
        disabled={qna.isBusy}
        canSubmit={qna.hasSelectedAnswer && !qna.isBusy}
        placeholder={placeholder}
        chips={
          <AttachChips
            sources={sources}
            busy={attaching}
            onRemove={onAttachRemove}
            onAdd={() => fileRef.current?.click()}
          />
        }
      />
    </>
  ) : null;

  return (
    <>
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
      <ChatThread
        messages={messages}
        thinking={qna.isBusy && !qna.isQuestionnaireReady}
        footer={footer}
      />
    </>
  );
}
