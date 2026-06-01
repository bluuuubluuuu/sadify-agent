"use client";

import styles from "./chat.module.css";

type Choice = {
  id: string;
  label: string;
  is_disabled: boolean;
  status_label: string;
};

export function AnswerChips({
  choices,
  selectedIds,
  selectionMode,
  disabled,
  onToggle,
}: {
  choices: Choice[];
  selectedIds: string[];
  selectionMode: "single" | "multiple";
  disabled?: boolean;
  onToggle: (id: string) => void;
}) {
  if (!choices.length) {
    return null;
  }
  return (
    <div>
      {selectionMode === "multiple" ? (
        <p className={styles.selectHint}>Select all that apply.</p>
      ) : null}
      <div className={styles.chips} role="group" aria-label="Answer choices">
        {choices.map((choice) => {
          const selected = selectedIds.includes(choice.id);
          return (
            <button
              key={choice.id}
              type="button"
              className={[
                styles.chip,
                selected ? styles.chipSelected : "",
                choice.is_disabled ? styles.chipDisabled : "",
              ]
                .filter(Boolean)
                .join(" ")}
              aria-pressed={selected}
              disabled={disabled || choice.is_disabled}
              onClick={() => onToggle(choice.id)}
            >
              <span>{choice.label}</span>
              {choice.status_label ? (
                <span className={styles.chipStatus}>{choice.status_label}</span>
              ) : null}
            </button>
          );
        })}
      </div>
    </div>
  );
}
